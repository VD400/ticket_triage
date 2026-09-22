"""arq worker for ticket processing.

Run with:  arq agent.worker.WorkerSettings

Design notes:
- Only ticket_id travels through Redis. The job payload is intentionally
  tiny; all real ticket data lives in Postgres and is fetched fresh when
  the worker picks the job up. Keeps jobs cheap and avoids staleness if a
  ticket is edited between enqueue and pickup.
- thread_id for the graph's checkpointer is set to the ticket_id. This is
  what lets human_interrupt_node's interrupt() survive across process
  boundaries — the paused state is persisted in Postgres under that
  thread_id, so a *separate* resume call later (see resume_ticket below)
  can pick the same run back up, even from a different worker process.
- The checkpointer and DB engine are created once per worker process in
  on_startup and torn down in on_shutdown, not per-job — creating a fresh
  connection pool for every ticket would be wasteful and slow.
"""
from __future__ import annotations

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from arq.connections import RedisSettings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from agent.graph import build_graph
from agent.state import AgentState
from database import SessionLocal  # sync session factory
from models.ticket import Ticket, TicketStatus
from models.agent_draft import AgentDraft, DraftStatus
from models.ticket_event import TicketEvent, TicketEventType

# ASYNC_DATABASE_URL is only for the checkpointer (needs an async driver,
# e.g. postgresql+psycopg://... with async mode). SessionLocal stays sync —
# see _fetch_ticket / _save_result below, which offload it to a thread so
# it doesn't block the event loop.


def _fetch_ticket(ticket_id: int) -> dict | None:
    """Sync DB read — called via asyncio.to_thread so it doesn't block
    the event loop other jobs are running on."""
    db = SessionLocal()
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            print("Given ID not found")
            return None
        return {
            "id" : ticket.id,
            "description" : ticket.description
        }
    finally:
        db.close()

REDIS_SETTINGS = RedisSettings.from_dsn(
    os.environ["REDIS_URL"]
)

async def on_startup(ctx: dict) -> None:
    # AsyncPostgresSaver manages its own connection pool internally.
    saver_cm = AsyncPostgresSaver.from_conn_string(os.environ['ASYNC_DATABASE_URL'])
    checkpointer = await saver_cm.__aenter__()

    ctx["checkpointer_cm"] = saver_cm
    ctx["checkpointer"] = checkpointer
    ctx["graph"] = build_graph(checkpointer)


async def on_shutdown(ctx: dict) -> None:
    saver_cm = ctx.get("checkpointer_cm")

    if saver_cm is not None:
        await saver_cm.__aexit__(None, None, None)


async def process_ticket(ctx: dict, ticket_id: int) -> None:
    """Enqueued when a ticket is created. Runs the graph from scratch."""
    graph = ctx["graph"]

    ticket = await asyncio.to_thread(_fetch_ticket, ticket_id)
    if ticket is None:
        # Ticket was deleted between enqueue and pickup — nothing to do.
        return

    initial_state: AgentState = {
        "ticket_id": ticket["id"],
        "ticket_text": ticket["description"],
        "category": None,
        "priority": None,
        "tool_calls_made": [],
        "context": [],
        "next_action": None,
        "clarification_question": None,
        "clarification_answer": None,
        "analysis": None,
        "draft_text": None,
    }

    # AgentState.ticket_id is an int, but LangGraph's checkpointer expects
    # thread_id as a string.
    config = {"configurable": {"thread_id": str(ticket_id)}}
    result = await graph.ainvoke(initial_state, config=config)
    if '__interrupt__' in result:
        return
    
    await asyncio.to_thread(
        _save_draft,
        ticket_id, 
        result
    )


async def resume_ticket(ctx: dict, ticket_id: int, human_feedback: str) -> None:
    """Enqueued when an employee submits feedback for a ticket that's
    paused on human_interrupt_node. Resumes the SAME thread_id."""
    graph = ctx["graph"]
    config = {"configurable": {"thread_id": str(ticket_id)}}
    result = await graph.ainvoke(Command(resume=human_feedback), config=config)
    if '__interrupt__' in result:
        return 
    await asyncio.to_thread(
        _save_draft,
        ticket_id,
        result
    )

def _save_draft(ticket_id: int, result: dict) -> None:
    db = SessionLocal()
    try:
        draft = AgentDraft(
            ticket_id=ticket_id,
            draft_text=result["draft_text"],
            analysis=result["analysis"],
            status=DraftStatus.PENDING_REVIEW,
        )
        db.add(draft)
        db.flush()
        db.add(
            TicketEvent(
                ticket_id=ticket_id,
                event_type=TicketEventType.DRAFT_CREATED,
                payload={
                    "draft_id": draft.id,
                    "draft_content": result['draft_text']
                },
            )
        )
        db.add(
            TicketEvent(
                ticket_id=ticket_id,
                event_type=TicketEventType.AWAITING_APPROVAL,
                payload={
                    "draft_id": draft.id,
                },
            ) 
        )
        ticket = db.get(Ticket, ticket_id)
        if ticket:
            ticket.status = TicketStatus.AWAITING_APPROVAL
            
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
        

class WorkerSettings:
    functions = [process_ticket, resume_ticket]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = REDIS_SETTINGS
    max_jobs = 2
    job_timeout = 300  # seconds — LLM calls + retrieval can be slow