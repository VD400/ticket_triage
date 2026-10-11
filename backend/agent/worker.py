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
from arq import Retry
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from agent.graph import build_graph
from agent.state import AgentState
from database import SessionLocal  # sync session factory
from models.ticket import Ticket, TicketStatus
from models.agent_draft import AgentDraft, DraftStatus
from models.ticket_event import TicketEvent, TicketEventType
from agent.events import publish_persisted_events
from agent.recovery import ticket_run, JOB_TIMEOUT_SECONDS
from models.ticket_resolution import TicketResolution

# ASYNC_DATABASE_URL is only for the psycopg checkpointer and uses a plain
# postgresql://... URL, without SQLAlchemy's +psycopg suffix. SessionLocal stays sync —
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
            "id": ticket.id,
            "description": ticket.description,
            "status": ticket.status,
        }
    finally:
        db.close()


REDIS_SETTINGS = RedisSettings.from_dsn(os.environ["REDIS_URL"])


async def on_startup(ctx: dict) -> None:
    # AsyncPostgresSaver manages its own connection pool internally.
    saver_cm = AsyncPostgresSaver.from_conn_string(os.environ["ASYNC_DATABASE_URL"])
    checkpointer = await saver_cm.__aenter__()

    ctx["checkpointer_cm"] = saver_cm
    ctx["checkpointer"] = checkpointer
    ctx["graph"] = build_graph(checkpointer)


async def on_shutdown(ctx: dict) -> None:
    saver_cm = ctx.get("checkpointer_cm")

    if saver_cm is not None:
        await saver_cm.__aexit__(None, None, None)


def _restore_saved_output(ticket_id: int) -> bool:
    """Restore an already persisted outcome instead of generating another draft."""
    with SessionLocal() as db:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            return True
        if db.query(TicketResolution).filter_by(ticket_id=ticket_id).first():
            if ticket.status != TicketStatus.RESOLVED:
                ticket.status = TicketStatus.RESOLVED
                event = TicketEvent(
                    ticket_id=ticket_id,
                    event_type=TicketEventType.RESOLVED,
                    payload={"reason": "Recovered saved resolution"},
                )
                db.add(event)
                db.commit()
                publish_persisted_events([event])
            return True
        draft = (
            db.query(AgentDraft)
            .filter_by(ticket_id=ticket_id, status=DraftStatus.PENDING_REVIEW)
            .first()
        )
        if draft:
            if ticket.status != TicketStatus.AWAITING_APPROVAL:
                ticket.status = TicketStatus.AWAITING_APPROVAL
                event = TicketEvent(
                    ticket_id=ticket_id,
                    event_type=TicketEventType.AWAITING_APPROVAL,
                    payload={"reason": "Recovered saved draft", "draft_id": draft.id},
                )
                db.add(event)
                db.commit()
                publish_persisted_events([event])
            return True
        return ticket.status in (
            TicketStatus.RESOLVED,
            TicketStatus.AWAITING_APPROVAL,
            TicketStatus.NEEDS_MANUAL_REVIEW,
        )


def _record_status(ticket_id, ticket_status, event_type, payload):
    with SessionLocal() as db:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            return
        ticket.status = ticket_status
        event = TicketEvent(ticket_id=ticket_id, event_type=event_type, payload=payload)
        db.add(event)
        db.commit()
        publish_persisted_events([event])


async def process_ticket(ctx: dict, ticket_id: int) -> None:
    """Run a new ticket, or continue an interrupted checkpoint without replaying input."""
    async with ticket_run(ticket_id) as acquired:
        if not acquired:
            return  # Another worker already owns this ticket.
        ticket = await asyncio.to_thread(_fetch_ticket, ticket_id)
        if ticket is None or await asyncio.to_thread(_restore_saved_output, ticket_id):
            return
        graph = ctx["graph"]
        config = {"configurable": {"thread_id": str(ticket_id)}}
        try:
            snapshot = await graph.aget_state(config)
            # A paused human question must not be answered automatically.
            if snapshot.interrupts:
                question = snapshot.values.get("clarification_question")
                await asyncio.to_thread(
                    _record_status,
                    ticket_id,
                    TicketStatus.AWAITING_CLARIFICATION,
                    TicketEventType.CLARIFICATION_REQUESTED,
                    {"question": question, "reason": "Recovered saved clarification"},
                )
                return
            if ticket["status"] == TicketStatus.AWAITING_CLARIFICATION:
                return
            if (
                snapshot.values
                and not snapshot.next
                and snapshot.values.get("draft_text")
            ):
                await asyncio.to_thread(_save_draft, ticket_id, snapshot.values)
                return
            if snapshot.next:
                # Passing initial input again would append duplicate reducer context.
                graph_input = None
                await asyncio.to_thread(
                    _record_status,
                    ticket_id,
                    TicketStatus.PROCESSING,
                    TicketEventType.PROCESSING_STARTED,
                    {"reason": "Continuing saved progress"},
                )
            elif snapshot.values:
                # No remaining work and no draft: keep this visible for human handling.
                await asyncio.to_thread(_mark_failed, ticket_id)
                return
            else:
                graph_input: AgentState = {
                    "ticket_id": ticket_id,
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
            result = await graph.ainvoke(graph_input, config=config)
            if "__interrupt__" not in result:
                await asyncio.to_thread(_save_draft, ticket_id, result)
        except Exception:
            await asyncio.to_thread(_mark_failed, ticket_id)
            raise
        except asyncio.CancelledError:
            # ARQ timeouts and orderly shutdowns should leave a recoverable state.
            await asyncio.to_thread(_mark_failed, ticket_id)
            raise


async def resume_ticket(ctx: dict, ticket_id: int, human_feedback: str) -> None:
    """Resume the same thread after an explicit human answer."""
    async with ticket_run(ticket_id) as acquired:
        if not acquired:
            # A fast answer can arrive while the interrupting job is releasing its lease.
            raise Retry(defer=1)
        if await asyncio.to_thread(_restore_saved_output, ticket_id):
            return
        graph = ctx["graph"]
        config = {"configurable": {"thread_id": str(ticket_id)}}
        try:
            snapshot = await graph.aget_state(config)
            if not snapshot.interrupts:
                return  # Ignore duplicate or outdated clarification jobs.
            result = await graph.ainvoke(Command(resume=human_feedback), config=config)
            if "__interrupt__" not in result:
                await asyncio.to_thread(_save_draft, ticket_id, result)
        except Exception:
            await asyncio.to_thread(_mark_failed, ticket_id)
            raise
        except asyncio.CancelledError:
            await asyncio.to_thread(_mark_failed, ticket_id)
            raise


def _mark_failed(ticket_id: int) -> None:
    with SessionLocal() as db:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None or ticket.status in (
            TicketStatus.RESOLVED,
            TicketStatus.AWAITING_APPROVAL,
        ):
            return
        ticket.status = TicketStatus.FAILED
        event = TicketEvent(
            ticket_id=ticket_id,
            event_type=TicketEventType.FAILED,
            payload={
                "message": "The agent could not complete this ticket. Please review it manually."
            },
        )
        db.add(event)
        db.commit()
        publish_persisted_events([event])


def _save_draft(ticket_id: int, result: dict) -> None:
    if _restore_saved_output(ticket_id):
        return
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
        events = []
        events.append(
            TicketEvent(
                ticket_id=ticket_id,
                event_type=TicketEventType.DRAFT_CREATED,
                payload={"draft_id": draft.id, "draft_content": result["draft_text"]},
            )
        )
        events.append(
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

        db.add_all(events)
        db.commit()
        publish_persisted_events(events)

    except Exception:
        db.rollback()
        _mark_failed(ticket_id)
        raise

    finally:
        db.close()


class WorkerSettings:
    functions = [process_ticket, resume_ticket]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = REDIS_SETTINGS
    max_jobs = 2
    job_timeout = JOB_TIMEOUT_SECONDS  # seconds — LLM calls + retrieval can be slow
