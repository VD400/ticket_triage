from models.ticket_event import TicketEvent, TicketEventType
from database import SessionLocal


def record_ticket_event(
    ticket_id: int,
    event_type: TicketEventType,
    payload: dict | None = None,
):
    db = SessionLocal()

    try:
        event = TicketEvent(
            ticket_id=ticket_id,
            event_type=event_type,
            payload=payload,
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return event

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()