"""Recovery protects live work, saved outcomes and human interrupts."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session
from redis.exceptions import ConnectionError

from agent import recovery, worker
from agent.queue import get_redis_pool
from main import app
from models.customer import Customer
from models.ticket import Ticket, TicketStatus
from models.ticket_event import TicketEvent, TicketEventType
from models.agent_draft import AgentDraft, DraftStatus
from models.ticket_resolution import TicketResolution
from models.user import UserRole
from tickets import router


@pytest.fixture
def ticket(db_session):
    customer = Customer(
        name="Recovery customer", email="recovery@example.com", email_verified=True
    )
    db_session.add(customer)
    db_session.flush()
    old = datetime.now(timezone.utc) - timedelta(days=19)
    row = Ticket(
        customer_id=customer.id,
        subject="Interrupted payment complaint",
        description="Please investigate the payment.",
        status=TicketStatus.PROCESSING,
        created_at=old,
        updated_at=old,
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.fixture
def queue(monkeypatch):
    redis = SimpleNamespace(enqueue_job=AsyncMock(return_value=object()))
    app.dependency_overrides[get_redis_pool] = lambda: redis
    monkeypatch.setattr(router, "publish_persisted_events", lambda events: None)
    return redis


@pytest.fixture
def worker_db(db_session, monkeypatch):
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(bind=db_session.get_bind())
    )
    monkeypatch.setattr(worker, "publish_persisted_events", lambda events: None)

    @asynccontextmanager
    async def lease(ticket_id):
        yield True

    monkeypatch.setattr(worker, "ticket_run", lease)


def graph_snapshot(*, values=None, next=(), interrupts=()):
    graph = SimpleNamespace(
        aget_state=AsyncMock(
            return_value=SimpleNamespace(
                values=values or {}, next=next, interrupts=interrupts
            )
        ),
        ainvoke=AsyncMock(
            return_value={
                "draft_text": "Recovered response",
                "analysis": "Checked existing context",
            }
        ),
    )
    return graph


def test_stale_ticket_can_be_requeued_once(
    client, db_session, ticket, queue, auth_headers
):
    headers = auth_headers()
    response = client.post(f"/tickets/{ticket.id}/retry", headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["recovery_available"] is False
    queue.enqueue_job.assert_awaited_once()
    args, kwargs = queue.enqueue_job.call_args
    assert args == ("process_ticket", ticket.id)
    assert kwargs["_job_id"].startswith(f"ticket-recovery:{ticket.id}:")
    assert (
        client.post(f"/tickets/{ticket.id}/retry", headers=headers).status_code == 409
    )
    assert (
        db_session.query(TicketEvent)
        .filter_by(ticket_id=ticket.id, event_type=TicketEventType.QUEUED)
        .count()
        == 1
    )


def test_recent_event_protects_old_ticket_from_retry(
    client, db_session, ticket, queue, auth_headers
):
    db_session.add(
        TicketEvent(ticket_id=ticket.id, event_type=TicketEventType.TOOL_CALLED)
    )
    db_session.commit()
    headers = auth_headers()
    response = client.get("/tickets/", headers=headers)
    row = next(row for row in response.json() if row["id"] == ticket.id)
    assert row["recovery_available"] is False
    assert (
        client.post(f"/tickets/{ticket.id}/retry", headers=headers).status_code == 409
    )
    queue.enqueue_job.assert_not_awaited()


@pytest.mark.parametrize(
    "status",
    [
        TicketStatus.RESOLVED,
        TicketStatus.AWAITING_APPROVAL,
        TicketStatus.AWAITING_CLARIFICATION,
        TicketStatus.NEEDS_MANUAL_REVIEW,
    ],
)
def test_human_and_completed_states_are_not_retried(
    client, db_session, ticket, queue, auth_headers, status
):
    ticket.status = status
    db_session.commit()
    assert (
        client.post(f"/tickets/{ticket.id}/retry", headers=auth_headers()).status_code
        == 409
    )
    queue.enqueue_job.assert_not_awaited()


def test_viewer_cannot_retry(client, ticket, queue, auth_headers):
    assert (
        client.post(
            f"/tickets/{ticket.id}/retry", headers=auth_headers(UserRole.VIEWER)
        ).status_code
        == 403
    )
    queue.enqueue_job.assert_not_awaited()


def test_agent_cannot_retry_another_agents_ticket(
    client, db_session, ticket, queue, auth_headers, make_user
):
    ticket.assigned_agent_id = make_user(username="other_owner").id
    db_session.commit()
    assert (
        client.post(f"/tickets/{ticket.id}/retry", headers=auth_headers()).status_code
        == 403
    )
    queue.enqueue_job.assert_not_awaited()


def test_queue_outage_leaves_retryable_failure(
    client, db_session, ticket, queue, auth_headers
):
    queue.enqueue_job.side_effect = ConnectionError("unavailable")
    response = client.post(f"/tickets/{ticket.id}/retry", headers=auth_headers())
    assert response.status_code == 503
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.FAILED


def test_active_worker_lock_blocks_retry(
    client, ticket, queue, auth_headers, monkeypatch
):
    monkeypatch.setattr(router, "reserve_recovery", lambda *args: False)
    assert (
        client.post(f"/tickets/{ticket.id}/retry", headers=auth_headers()).status_code
        == 409
    )
    queue.enqueue_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_postgres_lease_blocks_duplicate_worker_and_api_and_releases(
    db_session, ticket, monkeypatch
):
    engine = db_session.get_bind().engine
    monkeypatch.setattr(recovery, "engine", engine)
    async with recovery.ticket_run(ticket.id) as acquired:
        assert acquired
        async with recovery.ticket_run(ticket.id) as duplicate:
            assert not duplicate
        with Session(bind=engine) as other:
            assert not recovery.reserve_recovery(other, ticket.id)
    async with recovery.ticket_run(ticket.id) as acquired_after_release:
        assert acquired_after_release


@pytest.mark.asyncio
async def test_checkpoint_continues_without_replaying_initial_input(
    db_session, ticket, worker_db
):
    graph = graph_snapshot(
        values={"ticket_id": ticket.id, "context": ["existing"]}, next=("SQL-node",)
    )
    await worker.process_ticket({"graph": graph}, ticket.id)
    graph.ainvoke.assert_awaited_once_with(
        None, config={"configurable": {"thread_id": str(ticket.id)}}
    )
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_APPROVAL
    assert db_session.query(AgentDraft).filter_by(ticket_id=ticket.id).count() == 1
    await worker.process_ticket({"graph": graph}, ticket.id)
    assert graph.ainvoke.await_count == 1
    assert db_session.query(AgentDraft).filter_by(ticket_id=ticket.id).count() == 1


@pytest.mark.asyncio
async def test_finished_checkpoint_saves_missing_draft_without_ai(
    db_session, ticket, worker_db
):
    graph = graph_snapshot(
        values={
            "draft_text": "Previously generated reply",
            "analysis": "Finished analysis",
        }
    )
    await worker.process_ticket({"graph": graph}, ticket.id)
    graph.ainvoke.assert_not_awaited()
    draft = db_session.query(AgentDraft).filter_by(ticket_id=ticket.id).one()
    assert draft.draft_text == "Previously generated reply"


@pytest.mark.asyncio
async def test_saved_human_question_is_restored_without_auto_answer(
    db_session, ticket, worker_db
):
    graph = graph_snapshot(
        values={"clarification_question": "Which payment?"},
        next=("Human-assistance-node",),
        interrupts=(object(),),
    )
    await worker.process_ticket({"graph": graph}, ticket.id)
    graph.ainvoke.assert_not_awaited()
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_CLARIFICATION
    assert db_session.query(AgentDraft).filter_by(ticket_id=ticket.id).count() == 0


@pytest.mark.asyncio
async def test_saved_draft_restores_review_without_ai(db_session, ticket, worker_db):
    db_session.add(
        AgentDraft(
            ticket_id=ticket.id,
            draft_text="Existing reply",
            status=DraftStatus.PENDING_REVIEW,
        )
    )
    db_session.commit()
    graph = graph_snapshot()
    await worker.process_ticket({"graph": graph}, ticket.id)
    graph.aget_state.assert_not_awaited()
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_saved_resolution_restores_resolved_without_ai(
    db_session, ticket, worker_db, make_user
):
    owner = make_user()
    db_session.add(
        TicketResolution(
            ticket_id=ticket.id,
            resolution_text="Existing resolution",
            resolved_by=owner.id,
            embedding=[0.0] * 384,
        )
    )
    db_session.commit()
    graph = graph_snapshot()
    await worker.process_ticket({"graph": graph}, ticket.id)
    graph.aget_state.assert_not_awaited()
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.RESOLVED


@pytest.mark.asyncio
async def test_no_checkpoint_starts_fresh(db_session, ticket, worker_db):
    graph = graph_snapshot()
    await worker.process_ticket({"graph": graph}, ticket.id)
    assert graph.ainvoke.call_args.args[0]["ticket_id"] == ticket.id
    assert graph.ainvoke.call_args.args[0]["context"] == []


@pytest.mark.asyncio
async def test_cancellation_is_visible_as_failure(db_session, ticket, worker_db):
    import asyncio

    graph = graph_snapshot()
    graph.ainvoke.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await worker.process_ticket({"graph": graph}, ticket.id)
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.FAILED


@pytest.mark.asyncio
async def test_real_langgraph_checkpoint_resumes_only_failed_node(
    db_session, ticket, worker_db
):
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    from agent.state import AgentState

    calls = {"collect": 0, "draft": 0}

    def collect(state):
        calls["collect"] += 1
        return {"context": [{"source": "policy", "content": ["saved context"]}]}

    def draft(state):
        calls["draft"] += 1
        if calls["draft"] == 1:
            raise RuntimeError("Simulated interrupted tool")
        assert len(state["context"]) == 1
        return {"draft_text": "Continued reply", "analysis": "Existing context reused"}

    builder = StateGraph(AgentState)
    builder.add_node("collect", collect)
    builder.add_node("draft", draft)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "draft")
    builder.add_edge("draft", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    with pytest.raises(RuntimeError, match="Simulated interrupted"):
        await worker.process_ticket({"graph": graph}, ticket.id)
    ticket.status = TicketStatus.QUEUED
    db_session.commit()
    await worker.process_ticket({"graph": graph}, ticket.id)
    assert calls == {"collect": 1, "draft": 2}
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_real_langgraph_human_interrupt_survives_recovery(
    db_session, ticket, worker_db
):
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import interrupt
    from agent.state import AgentState

    def ask(state):
        return {"clarification_question": "Which transaction?"}

    def human(state):
        answer = interrupt({"question": state["clarification_question"]})
        return {"draft_text": f"Checked {answer}", "analysis": "Human answer received"}

    builder = StateGraph(AgentState)
    builder.add_node("ask", ask)
    builder.add_node("human", human)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", "human")
    builder.add_edge("human", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    await worker.process_ticket({"graph": graph}, ticket.id)
    await worker.process_ticket({"graph": graph}, ticket.id)
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_CLARIFICATION
    await worker.resume_ticket({"graph": graph}, ticket.id, "transaction 123")
    assert (
        db_session.query(AgentDraft).filter_by(ticket_id=ticket.id).one().draft_text
        == "Checked transaction 123"
    )


@pytest.mark.asyncio
async def test_fast_clarification_waits_for_worker_lease_instead_of_losing_answer(
    ticket, worker_db, monkeypatch
):
    from arq import Retry

    @asynccontextmanager
    async def busy(ticket_id):
        yield False

    monkeypatch.setattr(worker, "ticket_run", busy)
    graph = graph_snapshot()
    with pytest.raises(Retry):
        await worker.resume_ticket({"graph": graph}, ticket.id, "transaction 123")
    graph.ainvoke.assert_not_awaited()


def test_queue_error_does_not_overwrite_outcome_saved_by_an_existing_job(
    client, db_session, ticket, queue, auth_headers
):
    async def raced_job(*args, **kwargs):
        ticket.status = TicketStatus.AWAITING_APPROVAL
        db_session.commit()
        raise ConnectionError("ambiguous queue response")

    queue.enqueue_job.side_effect = raced_job
    response = client.post(f"/tickets/{ticket.id}/retry", headers=auth_headers())
    assert response.status_code == 503
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_APPROVAL
    assert (
        db_session.query(TicketEvent)
        .filter_by(ticket_id=ticket.id, event_type=TicketEventType.FAILED)
        .count()
        == 0
    )
