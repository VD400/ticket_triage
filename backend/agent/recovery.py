"""Recovery eligibility and a PostgreSQL lease shared by API and workers.

A separate transaction holds an advisory lock for the whole worker job. It
rolls back when its connection closes, including after an abrupt process exit.
Redis data can disappear independently; PostgreSQL remains the source of ticket history.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, text
from database import engine
from models.ticket import TicketStatus
from models.ticket_event import TicketEvent

JOB_TIMEOUT_SECONDS = 300
STALE_AFTER = timedelta(seconds=JOB_TIMEOUT_SECONDS * 2)
LOCK_NAMESPACE = 1414678849


def last_activity(db, tickets):
    ids = [ticket.id for ticket in tickets]
    if not ids:
        return {}
    recorded = dict(
        db.query(TicketEvent.ticket_id, func.max(TicketEvent.created_at))
        .filter(TicketEvent.ticket_id.in_(ids))
        .group_by(TicketEvent.ticket_id)
        .all()
    )
    return {
        ticket.id: max(ticket.updated_at, recorded.get(ticket.id) or ticket.updated_at)
        for ticket in tickets
    }


def can_recover(ticket, activity, now=None):
    if ticket.status == TicketStatus.FAILED:
        return True
    if ticket.status not in (TicketStatus.QUEUED, TicketStatus.PROCESSING):
        return False
    return (now or datetime.now(timezone.utc)) - activity >= STALE_AFTER


def annotate_recovery(db, tickets):
    activity = last_activity(db, tickets)
    for ticket in tickets:
        ticket.last_activity_at = activity[ticket.id]
        ticket.recovery_available = can_recover(ticket, ticket.last_activity_at)
    return tickets


def reserve_recovery(db, ticket_id):
    """Transaction lock: rejects recovery while a worker owns this ticket."""
    return db.execute(
        text("SELECT pg_try_advisory_xact_lock(:namespace, :ticket)"),
        {"namespace": LOCK_NAMESPACE, "ticket": ticket_id},
    ).scalar()


def _open_run(ticket_id):
    connection = engine.connect()
    try:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_xact_lock(:namespace, :ticket)"),
            {"namespace": LOCK_NAMESPACE, "ticket": ticket_id},
        ).scalar()
        return connection, acquired
    except BaseException:
        connection.close()
        raise


@asynccontextmanager
async def ticket_run(ticket_id):
    # Shield acquisition so a timeout cannot abandon a connection in its thread.
    pending = asyncio.create_task(asyncio.to_thread(_open_run, ticket_id))
    try:
        connection, acquired = await asyncio.shield(pending)
    except asyncio.CancelledError:
        connection, _ = await pending
        await asyncio.to_thread(connection.close)
        raise
    try:
        yield acquired
    finally:
        # Rollback releases the lease even when the pool reuses this connection.
        await asyncio.shield(asyncio.to_thread(connection.close))
