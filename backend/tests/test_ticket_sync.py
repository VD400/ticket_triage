"""Shared queue visibility and live notifications after committed changes."""

import pytest
from sqlalchemy.orm import Session
from models.customer import Customer
from models.ticket import Ticket, TicketStatus
from models.ticket_event import TicketEvent, TicketEventType
from models.agent_draft import AgentDraft, DraftStatus
from models.user import UserRole
from agent.queue import get_redis_pool
from main import app
from tickets import router as ticket_router
from agent import worker


def make_ticket(db, **fields):
    customer = db.query(Customer).filter_by(email="customer@sync.test").first()
    if not customer:
        customer = Customer(
            name="Customer", email="customer@sync.test", email_verified=True
        )
        db.add(customer)
        db.flush()
    ticket = Ticket(
        customer_id=customer.id,
        subject="Missing refund",
        description="Please check my refund.",
        **fields,
    )
    db.add(ticket)
    db.commit()
    return ticket


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.VIEWER])
def test_shared_queue_and_closed_history_visible(
    client, db_session, auth_headers, make_user, role
):
    headers = auth_headers(role)
    other = make_user(username="another_agent")
    queued = make_ticket(db_session)
    processing = make_ticket(db_session, status=TicketStatus.PROCESSING)
    closed = make_ticket(
        db_session, status=TicketStatus.RESOLVED, assigned_agent_id=other.id
    )
    private = make_ticket(
        db_session, status=TicketStatus.PROCESSING, assigned_agent_id=other.id
    )
    response = client.get("/tickets/", headers=headers)
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert {queued.id, processing.id, closed.id} <= ids
    assert private.id not in ids


def test_submission_publishes_persisted_queue_event(client, db_session, monkeypatch):
    customer = Customer(name="Customer", email="new@sync.test", email_verified=True)
    db_session.add(customer)
    db_session.commit()
    published, jobs = [], []

    class Queue:
        async def enqueue_job(self, name, ticket_id):
            jobs.append((name, ticket_id))

    app.dependency_overrides[get_redis_pool] = lambda: Queue()
    monkeypatch.setattr(
        ticket_router,
        "publish_persisted_events",
        lambda events: published.extend(events),
    )
    response = client.post(
        "/tickets/",
        json={
            "customer_id": customer.id,
            "subject": "Refund",
            "description": "Where is my refund?",
        },
    )
    assert response.status_code == 201
    ticket_id = response.json()["id"]
    assert jobs == [("process_ticket", ticket_id)]
    assert len(published) == 1
    assert published[0].id is not None
    assert published[0].event_type == TicketEventType.QUEUED
    assert db_session.get(TicketEvent, published[0].id) is not None


def test_worker_publishes_draft_and_status_after_commit(db_session, monkeypatch):
    ticket = make_ticket(db_session, status=TicketStatus.PROCESSING)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(bind=db_session.get_bind())
    )
    seen = []

    def capture(events):
        with Session(bind=db_session.get_bind()) as db:
            assert db.get(Ticket, ticket.id).status == TicketStatus.AWAITING_APPROVAL
            seen.extend((event.id, event.event_type) for event in events)

    monkeypatch.setattr(worker, "publish_persisted_events", capture)
    worker._save_draft(
        ticket.id,
        {"draft_text": "We are checking your refund.", "analysis": "Refund request"},
    )
    assert [kind for _, kind in seen] == [
        TicketEventType.DRAFT_CREATED,
        TicketEventType.AWAITING_APPROVAL,
    ]
    assert all(event_id is not None for event_id, _ in seen)


@pytest.mark.parametrize(
    "action,expected",
    [
        ("approve", TicketStatus.RESOLVED),
        ("edit", TicketStatus.RESOLVED),
        ("reject", TicketStatus.NEEDS_MANUAL_REVIEW),
    ],
)
def test_review_publishes_final_status(
    client, db_session, auth_headers, monkeypatch, action, expected
):
    headers = auth_headers()
    ticket = make_ticket(db_session, status=TicketStatus.AWAITING_APPROVAL)
    draft = AgentDraft(
        ticket_id=ticket.id,
        draft_text="Refund approved",
        analysis="Checked policy",
        status=DraftStatus.PENDING_REVIEW,
    )
    db_session.add(draft)
    db_session.commit()
    monkeypatch.setattr(
        ticket_router, "embed_text", lambda *args, **kwargs: [0.0] * 384
    )
    seen = []
    monkeypatch.setattr(
        ticket_router, "publish_persisted_events", lambda events: seen.extend(events)
    )
    response = client.post(
        f"/tickets/{ticket.id}/drafts/{draft.id}/review",
        headers=headers,
        json={"action": action, "edited_text": "Edited response"},
    )
    assert response.status_code == 200
    db_session.refresh(ticket)
    assert ticket.status == expected
    assert seen and all(event.id is not None for event in seen)
    assert seen[-1].event_type == (
        TicketEventType.DRAFT_REJECTED
        if action == "reject"
        else TicketEventType.RESOLVED
    )


def test_failed_worker_remains_visible_with_history(db_session, monkeypatch):
    ticket = make_ticket(db_session, status=TicketStatus.PROCESSING)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(bind=db_session.get_bind())
    )
    seen = []
    monkeypatch.setattr(
        worker,
        "publish_persisted_events",
        lambda events: seen.extend((event.id, event.event_type) for event in events),
    )
    worker._mark_failed(ticket.id)
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.FAILED
    assert seen[0][1] == TicketEventType.FAILED
    assert seen[0][0] is not None


def test_manual_resolution_publishes_committed_event(
    client, db_session, auth_headers, monkeypatch
):
    ticket = make_ticket(db_session, status=TicketStatus.FAILED)
    headers = auth_headers()
    monkeypatch.setattr(
        ticket_router, "embed_text", lambda *args, **kwargs: [0.0] * 384
    )
    seen = []
    monkeypatch.setattr(
        ticket_router, "publish_persisted_events", lambda events: seen.extend(events)
    )
    response = client.post(
        f"/tickets/{ticket.id}/resolve-manually",
        headers=headers,
        json={"resolution_text": "We verified the account and resolved the issue."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert seen[0].event_type == TicketEventType.RESOLVED
    assert seen[0].id is not None


def test_notification_outage_preserves_committed_history(db_session, monkeypatch):
    from agent import events
    import redis

    ticket = make_ticket(db_session, status=TicketStatus.PROCESSING)
    monkeypatch.setattr(
        worker, "SessionLocal", lambda: Session(bind=db_session.get_bind())
    )

    def unavailable(*args, **kwargs):
        raise redis.ConnectionError("temporary outage")

    monkeypatch.setattr(events.redis_client, "publish", unavailable)
    worker._save_draft(
        ticket.id, {"draft_text": "Response ready", "analysis": "Policy checked"}
    )
    db_session.refresh(ticket)
    assert ticket.status == TicketStatus.AWAITING_APPROVAL
    assert (
        db_session.query(TicketEvent)
        .filter_by(ticket_id=ticket.id, event_type=TicketEventType.DRAFT_CREATED)
        .count()
        == 1
    )
