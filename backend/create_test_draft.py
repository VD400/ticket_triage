# backend/create_test_draft.py
from database import SessionLocal
from models import Ticket
from models.agent_draft import AgentDraft, DraftStatus

def main():
    db = SessionLocal()

    # grab any existing ticket that's still QUEUED (one of your seeded ones)
    ticket = db.query(Ticket).filter(Ticket.status == "QUEUED").first()
    if not ticket:
        print("No queued ticket found — check your seed data.")
        return

    draft = AgentDraft(
        ticket_id=ticket.id,
        draft_text="Hi, I can see you were charged twice this month. I've issued a refund "
                    "for the duplicate charge, which should appear within 3-5 business days.",
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    print(f"Created draft id={draft.id} for ticket id={ticket.id} (subject: '{ticket.subject}')")
    db.close()

if __name__ == "__main__":
    main()