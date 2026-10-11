from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from pathlib import Path
import sys

# Make `backend/` imports work whether the script is run as
# `uv run python seed_realistic_test_data.py` from backend/ or by absolute path.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth.security import hash_password
from agent.embeddings import embed_texts_batch
from database import SessionLocal
from models import (
    AgentDraft,
    CompanyPolicy,
    Customer,
    Ticket,
    TicketEvent,
    TicketResolution,
    Transaction,
    User,
    VerificationToken,
)
from models.agent_draft import DraftStatus
from models.ticket import TicketCategory, TicketPriority, TicketStatus
from models.ticket_event import TicketEventType
from models.transaction import RefundStatus, TransactionStatus, TransactionType
from models.user import UserRole


LOCAL_TZ = ZoneInfo("Asia/Kolkata")
LOCAL_NOW = datetime.now(LOCAL_TZ)
NOW = LOCAL_NOW.astimezone(timezone.utc)


CUSTOMERS = [
    ("Priya Shah", "priya.shah@example.com", True),
    ("Daniel Cho", "daniel.cho@example.com", True),
    ("Amara Okafor", "amara.okafor@example.com", True),
    ("Sofia Ramirez", "sofia.ramirez@example.com", True),
    ("Kenji Watanabe", "kenji.w@example.com", True),
    ("Nadia Husain", "nadia.husain@example.com", False),
    ("Liam Fitzgerald", "liam.fitz@example.com", True),
    ("Tomas Novak", "tomas.novak@example.com", True),
]


POLICIES = [
    (
        "Refund Policy",
        "Card refunds are normally processed within 5-7 business days. Failed transactions "
        "are automatically reversed within 3 business days. Manual refunds require payment verification.",
    ),
    (
        "Duplicate Charge Policy",
        "A duplicate charge may reflect a temporary authorization hold rather than an actual "
        "second capture. Two successful captures for the same customer and amount on the same day "
        "should be investigated as a possible duplicate charge. Authorization holds are normally "
        "released within 3-5 business days if not captured.",
    ),
    (
        "Failed Payment Policy",
        "A failed payment should not result in a completed purchase. A failed transaction may be "
        "reversed automatically by the payment provider within 3 business days if a temporary hold exists.",
    ),
    (
        "Account Lockout Policy",
        "Accounts are automatically locked after 5 failed login attempts within 15 minutes. "
        "Locked accounts are automatically unlocked after 30 minutes, or can be manually unlocked "
        "by an agent after identity verification.",
    ),
    (
        "Escalation Policy",
        "Tickets involving an actual duplicate successful charge, an unauthorized transaction, or "
        "a refund failure after the normal processing window should be reviewed carefully using the "
        "customer's transaction history before a final response is sent.",
    ),
]


def reset_data(db) -> None:
    """Delete application data in FK-safe order."""
    # Children first because the project migrations do not define ON DELETE CASCADE.
    for model in (
        TicketResolution,
        TicketEvent,
        AgentDraft,
        VerificationToken,
        Ticket,
        Transaction,
        Customer,
        CompanyPolicy,
        User,
    ):
        deleted = db.query(model).delete(synchronize_session=False)
        print(f"Deleted {deleted:>3} rows from {model.__tablename__}")
    db.commit()


def seed_users(db):
    """Create real loginable users rather than placeholder password hashes."""
    users = [
        User(
            username="admin1",
            email="admin1@company.com",
            hashed_password=hash_password("Admin123!"),
            role=UserRole.ADMIN,
        ),
        User(
            username="agent1",
            email="agent1@company.com",
            hashed_password=hash_password("Agent123!"),
            role=UserRole.AGENT,
        ),
        User(
            username="agent2",
            email="agent2@company.com",
            hashed_password=hash_password("Agent456!"),
            role=UserRole.AGENT,
        ),
        User(
            username="viewer1",
            email="viewer1@company.com",
            hashed_password=hash_password("Viewer123!"),
            role=UserRole.VIEWER,
        ),
    ]
    db.add_all(users)
    db.commit()
    for user in users:
        db.refresh(user)
    print(f"Seeded {len(users)} users.")
    return users


def seed_customers(db):
    customers = [
        Customer(name=name, email=email, email_verified=verified)
        for name, email, verified in CUSTOMERS
    ]
    db.add_all(customers)
    db.commit()
    for customer in customers:
        db.refresh(customer)
    print(f"Seeded {len(customers)} customers.")
    return customers


def add_transaction(db, customer, amount, status, tx_type, created_at, refund_status=None):
    tx = Transaction(
        customer_id=customer.id,
        amount=Decimal(amount),
        status=status,
        transaction_type=tx_type,
        created_at=created_at,
        refund_status=refund_status,
    )
    db.add(tx)
    return tx


def seed_transactions(db, customers):
    p, d, a, s, k, n, l, t = customers
    # "Yesterday" is based on the application/user timezone (Asia/Kolkata),
    # then stored as UTC in PostgreSQL.
    yesterday = (LOCAL_NOW - timedelta(days=1)).astimezone(timezone.utc)

    transactions = []

    # 1) EXACT duplicate successful captures for Priya yesterday.
    # Ticket #1 explicitly claims she paid twice yesterday. The agent can verify it.
    transactions += [
        add_transaction(
            db, p, "1299.00", TransactionStatus.SUCCESS,
            TransactionType.ONE_TIME_PURCHASE,
            yesterday.replace(hour=11, minute=14, second=22, microsecond=0),
        ),
        add_transaction(
            db, p, "1299.00", TransactionStatus.SUCCESS,
            TransactionType.ONE_TIME_PURCHASE,
            yesterday.replace(hour=11, minute=15, second=7, microsecond=0),
        ),
    ]

    # A normal older successful purchase for comparison.
    transactions.append(
        add_transaction(
            db, p, "799.00", TransactionStatus.SUCCESS,
            TransactionType.SUBSCRIPTION,
            NOW - timedelta(days=30),
        )
    )

    # 2) Daniel: failed payment yesterday. Useful for a "payment failed but money moved" complaint.
    transactions.append(
        add_transaction(
            db, d, "2499.00", TransactionStatus.FAILED,
            TransactionType.ONE_TIME_PURCHASE,
            yesterday.replace(hour=16, minute=42, second=10, microsecond=0),
        )
    )
    # Later successful retry, showing the two attempts are not duplicates.
    transactions.append(
        add_transaction(
            db, d, "2499.00", TransactionStatus.SUCCESS,
            TransactionType.ONE_TIME_PURCHASE,
            yesterday.replace(hour=17, minute=3, second=41, microsecond=0),
        )
    )

    # 3) Amara: refund pending, 5 days old.
    transactions.append(
        add_transaction(
            db, a, "4999.00", TransactionStatus.SUCCESS,
            TransactionType.UPGRADE,
            NOW - timedelta(days=5),
            RefundStatus.PENDING,
        )
    )

    # 4) Sofia: refund completed.
    transactions.append(
        add_transaction(
            db, s, "7999.00", TransactionStatus.SUCCESS,
            TransactionType.ONE_TIME_PURCHASE,
            NOW - timedelta(days=12),
            RefundStatus.COMPLETED,
        )
    )

    # 5) Kenji: normal upgrade purchase.
    transactions.append(
        add_transaction(
            db, k, "14999.00", TransactionStatus.SUCCESS,
            TransactionType.UPGRADE,
            NOW - timedelta(days=3),
        )
    )

    # 6) Nadia: recurring subscription payment failure.
    transactions.append(
        add_transaction(
            db, n, "899.00", TransactionStatus.FAILED,
            TransactionType.SUBSCRIPTION,
            NOW - timedelta(days=2),
        )
    )

    # 7) Liam: no transaction history on purpose; useful for an account-access ticket.

    # 8) Tomas: failed refund attempt on an otherwise successful upgrade.
    transactions.append(
        add_transaction(
            db, t, "3499.00", TransactionStatus.SUCCESS,
            TransactionType.UPGRADE,
            NOW - timedelta(days=9),
            RefundStatus.FAILED,
        )
    )

    # 9) Amara: older successful subscription, to give the AI additional context.
    transactions.append(
        add_transaction(
            db, a, "599.00", TransactionStatus.SUCCESS,
            TransactionType.SUBSCRIPTION,
            NOW - timedelta(days=30),
        )
    )

    db.commit()
    for tx in transactions:
        db.refresh(tx)
    print(f"Seeded {len(transactions)} transactions.")
    return transactions


def add_event(db, ticket, event_type, created_at, payload=None):
    event = TicketEvent(
        ticket_id=ticket.id,
        event_type=event_type,
        created_at=created_at,
        payload=payload,
    )
    db.add(event)
    return event


def seed_tickets(db, customers, users):
    p, d, a, s, k, n, l, t = customers
    admin, agent1, agent2, viewer = users

    tickets = []

    # QUEUED: exact database-verifiable duplicate charge case.
    tickets.append(
        Ticket(
            customer_id=p.id,
            assigned_agent_id=agent1.id,
            subject="Charged twice yesterday for the same purchase",
            description=(
                "I paid ₹1,299 yesterday for my purchase and it looks like I was charged twice. "
                "There should only have been one payment. Please check my transaction history and "
                "confirm whether both charges actually went through."
            ),
            category=TicketCategory.BILLING,
            priority=TicketPriority.HIGH,
            status=TicketStatus.QUEUED,
            created_at=NOW - timedelta(minutes=20),
        )
    )

    # QUEUED: failed payment + retry in transaction history.
    tickets.append(
        Ticket(
            customer_id=d.id,
            assigned_agent_id=agent1.id,
            subject="Payment failed but I am not sure what happened",
            description=(
                "I tried to pay ₹2,499 yesterday and the first payment appeared to fail. "
                "I then tried again and received a success message. Please check the transaction "
                "history and tell me whether I was charged twice or only once."
            ),
            category=TicketCategory.BILLING,
            priority=TicketPriority.HIGH,
            status=TicketStatus.QUEUED,
            created_at=NOW - timedelta(minutes=15),
        )
    )

    # QUEUED: refund pending.
    tickets.append(
        Ticket(
            customer_id=a.id,
            assigned_agent_id=agent2.id,
            subject="Refund still pending after five days",
            description=(
                "I requested a refund for the ₹4,999 upgrade I paid for five days ago. "
                "I can still see the original successful transaction and the refund has not arrived. "
                "Please check the transaction and tell me what is happening."
            ),
            category=TicketCategory.REFUND,
            priority=TicketPriority.MEDIUM,
            status=TicketStatus.QUEUED,
            created_at=NOW - timedelta(minutes=10),
        )
    )

    # AWAITING APPROVAL: agent draft exists and points to the real successful/refunded transaction.
    approval_ticket = Ticket(
        customer_id=s.id,
        assigned_agent_id=agent2.id,
        subject="Can you confirm my refund was processed?",
        description=(
            "I returned my purchase and was told the ₹7,999 refund was processed. "
            "Please check the payment records and confirm the current status."
        ),
        category=TicketCategory.REFUND,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.AWAITING_APPROVAL,
        created_at=NOW - timedelta(hours=3),
    )
    tickets.append(approval_ticket)

    # NEEDS MANUAL REVIEW: rejected draft path.
    manual_ticket = Ticket(
        customer_id=t.id,
        assigned_agent_id=agent1.id,
        subject="My refund failed even though the original payment succeeded",
        description=(
            "I paid ₹3,499 for an upgrade nine days ago and was told it would be refunded. "
            "The refund has still not arrived. Please investigate the failed refund."
        ),
        category=TicketCategory.REFUND,
        priority=TicketPriority.HIGH,
        status=TicketStatus.NEEDS_MANUAL_REVIEW,
        created_at=NOW - timedelta(hours=5),
    )
    tickets.append(manual_ticket)

    # AWAITING CLARIFICATION: deliberately lacks identifying payment details.
    clarification_ticket = Ticket(
        customer_id=n.id,
        assigned_agent_id=agent2.id,
        subject="My subscription payment keeps failing",
        description=(
            "My subscription payment failed again and I need help. I am not sure which transaction "
            "was affected, and I do not know whether I was charged."
        ),
        category=TicketCategory.BILLING,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.AWAITING_CLARIFICATION,
        created_at=NOW - timedelta(hours=6),
    )
    tickets.append(clarification_ticket)

    # RESOLVED: account-access example with no transaction required.
    resolved_account = Ticket(
        customer_id=l.id,
        assigned_agent_id=agent1.id,
        subject="Locked out of my account",
        description=(
            "I have been unable to log into my account since this morning. "
            "Please help me regain access."
        ),
        category=TicketCategory.ACCOUNT_ACCESS,
        priority=TicketPriority.HIGH,
        status=TicketStatus.RESOLVED,
        created_at=NOW - timedelta(days=2),
    )
    tickets.append(resolved_account)

    # RESOLVED: resolved billing example to populate the ticket-resolution RAG store.
    resolved_billing = Ticket(
        customer_id=a.id,
        assigned_agent_id=agent2.id,
        subject="Older subscription billing question",
        description="I had a billing question about my monthly subscription charge.",
        category=TicketCategory.BILLING,
        priority=TicketPriority.LOW,
        status=TicketStatus.RESOLVED,
        created_at=NOW - timedelta(days=7),
    )
    tickets.append(resolved_billing)

    db.add_all(tickets)
    db.commit()
    for ticket in tickets:
        db.refresh(ticket)
    print(f"Seeded {len(tickets)} tickets.")
    return tickets


def seed_events_and_drafts(db, tickets, users):
    by_subject = {ticket.subject: ticket for ticket in tickets}
    _, agent1, agent2, _ = users

    # 1) Queued duplicate-charge ticket: enough trace to see initial processing when worker picks it up.
    duplicate = by_subject["Charged twice yesterday for the same purchase"]
    add_event(db, duplicate, TicketEventType.QUEUED, duplicate.created_at)

    # 2) Queued failed/retry ticket.
    payment = by_subject["Payment failed but I am not sure what happened"]
    add_event(db, payment, TicketEventType.QUEUED, payment.created_at)

    # 3) Queued refund.
    pending_refund = by_subject["Refund still pending after five days"]
    add_event(db, pending_refund, TicketEventType.QUEUED, pending_refund.created_at)

    # 4) Awaiting approval ticket with a realistic trace + pending draft.
    approval = by_subject["Can you confirm my refund was processed?"]
    t = approval.created_at
    add_event(db, approval, TicketEventType.QUEUED, t)
    add_event(db, approval, TicketEventType.PROCESSING_STARTED, t + timedelta(minutes=1))
    add_event(
        db,
        approval,
        TicketEventType.CLASSIFIED,
        t + timedelta(minutes=2),
        {"category": "REFUND", "priority": "MEDIUM"},
    )
    add_event(
        db,
        approval,
        TicketEventType.TOOL_CALLED,
        t + timedelta(minutes=3),
        {"tool": "generate_sql_tool", "purpose": "verify refund transaction status"},
    )
    add_event(
        db,
        approval,
        TicketEventType.TOOL_RESULT,
        t + timedelta(minutes=3, seconds=2),
        {
            "tool": "execute_readonly_query_tool",
            "rows": [
                {
                    "amount": 7999.0,
                    "status": "SUCCESS",
                    "refund_status": "COMPLETED",
                }
            ],
        },
    )
    draft = AgentDraft(
        ticket_id=approval.id,
        reviewed_by=None,
        draft_text=(
            "I checked your transaction history and confirmed that the ₹7,999 payment was successful "
            "and its refund status is marked as completed. Please allow your bank's normal processing "
            "time for the refunded amount to appear."
        ),
        status=DraftStatus.PENDING_REVIEW,
        analysis={
            "verified": True,
            "transaction_status": "SUCCESS",
            "refund_status": "COMPLETED",
            "source": "transactions table",
        },
        created_at=t + timedelta(minutes=4),
    )
    db.add(draft)
    db.flush()
    add_event(
        db,
        approval,
        TicketEventType.DRAFT_CREATED,
        t + timedelta(minutes=4),
        {"draft_id": draft.id},
    )
    add_event(db, approval, TicketEventType.AWAITING_APPROVAL, t + timedelta(minutes=4, seconds=1))

    # 5) Needs manual review: a rejected draft.
    manual = by_subject["My refund failed even though the original payment succeeded"]
    t = manual.created_at
    add_event(db, manual, TicketEventType.QUEUED, t)
    add_event(db, manual, TicketEventType.PROCESSING_STARTED, t + timedelta(minutes=1))
    add_event(
        db,
        manual,
        TicketEventType.CLASSIFIED,
        t + timedelta(minutes=2),
        {"category": "REFUND", "priority": "HIGH"},
    )
    bad_draft = AgentDraft(
        ticket_id=manual.id,
        reviewed_by=agent1.id,
        draft_text=(
            "Your refund has been handled and should arrive shortly. There is nothing else required."
        ),
        status=DraftStatus.REJECTED,
        analysis={
            "verified": False,
            "issue": "refund transaction status requires manual investigation",
        },
        reviewed_at=t + timedelta(minutes=10),
        created_at=t + timedelta(minutes=4),
    )
    db.add(bad_draft)
    db.flush()
    add_event(db, manual, TicketEventType.DRAFT_CREATED, t + timedelta(minutes=4), {"draft_id": bad_draft.id})
    add_event(db, manual, TicketEventType.AWAITING_APPROVAL, t + timedelta(minutes=4, seconds=1))
    add_event(
        db,
        manual,
        TicketEventType.DRAFT_REJECTED,
        t + timedelta(minutes=10),
        {"draft_id": bad_draft.id, "reviewed_by": agent1.id, "reason": "Refund failure needs manual investigation."},
    )

    # 6) Awaiting clarification.
    clarify = by_subject["My subscription payment keeps failing"]
    t = clarify.created_at
    add_event(db, clarify, TicketEventType.QUEUED, t)
    add_event(db, clarify, TicketEventType.PROCESSING_STARTED, t + timedelta(minutes=1))
    add_event(
        db,
        clarify,
        TicketEventType.CLARIFICATION_REQUESTED,
        t + timedelta(minutes=2),
        {"question": "Can you provide the approximate date and amount of the subscription charge you mean?"},
    )

    # 7) Resolved account ticket.
    resolved_account = by_subject["Locked out of my account"]
    t = resolved_account.created_at
    add_event(db, resolved_account, TicketEventType.QUEUED, t)
    add_event(db, resolved_account, TicketEventType.PROCESSING_STARTED, t + timedelta(minutes=1))
    add_event(
        db,
        resolved_account,
        TicketEventType.CLASSIFIED,
        t + timedelta(minutes=2),
        {"category": "ACCOUNT_ACCESS", "priority": "HIGH"},
    )
    add_event(db, resolved_account, TicketEventType.RESOLVED, t + timedelta(minutes=8))

    # 8) Resolved billing ticket with resolution for RAG.
    resolved_billing = by_subject["Older subscription billing question"]
    t = resolved_billing.created_at
    add_event(db, resolved_billing, TicketEventType.QUEUED, t)
    add_event(db, resolved_billing, TicketEventType.PROCESSING_STARTED, t + timedelta(minutes=1))
    add_event(
        db,
        resolved_billing,
        TicketEventType.CLASSIFIED,
        t + timedelta(minutes=2),
        {"category": "BILLING", "priority": "LOW"},
    )
    add_event(db, resolved_billing, TicketEventType.RESOLVED, t + timedelta(minutes=6))

    db.commit()
    print("Seeded ticket events and draft workflow state.")
    return {
        "approval_draft": draft,
        "rejected_draft": bad_draft,
    }


def seed_resolutions(db, tickets, users):
    by_subject = {ticket.subject: ticket for ticket in tickets}
    _, agent1, agent2, _ = users

    resolution_rows = [
        (
            by_subject["Locked out of my account"],
            agent1.id,
            "Verified the account-access issue and cleared the stale session/lock state. The customer was able to sign in again.",
        ),
        (
            by_subject["Older subscription billing question"],
            agent2.id,
            "Checked the customer's billing history and confirmed the subscription charge was a single successful transaction. No duplicate successful capture was found for that billing period.",
        ),
    ]

    texts = [row[2] for row in resolution_rows]
    embeddings = embed_texts_batch(texts, input_type="search_document")

    resolutions = []
    for (ticket, resolver_id, text), embedding in zip(resolution_rows, embeddings):
        resolutions.append(
            TicketResolution(
                ticket_id=ticket.id,
                resolved_by=resolver_id,
                resolution_text=text,
                embedding=embedding,
                created_at=ticket.created_at + timedelta(minutes=8),
            )
        )
    db.add_all(resolutions)
    db.commit()
    print(f"Seeded {len(resolutions)} ticket resolutions with embeddings.")


def seed_policies(db):
    texts = [text for _, text in POLICIES]
    embeddings = embed_texts_batch(texts, input_type="search_document")
    rows = [
        CompanyPolicy(title=title, policy_text=text, embedding=embedding)
        for (title, text), embedding in zip(POLICIES, embeddings)
    ]
    db.add_all(rows)
    db.commit()
    print(f"Seeded {len(rows)} company policies with embeddings.")


async def enqueue_queued_tickets(ticket_ids):
    """Optionally enqueue seeded QUEUED tickets so the ARQ worker processes them."""
    from agent.queue import get_redis

    redis = await get_redis()
    try:
        for ticket_id in ticket_ids:
            job = await redis.enqueue_job("process_ticket", ticket_id)
            print(f"Enqueued ticket {ticket_id} -> job {job.job_id}")
    finally:
        await redis.aclose()


def print_summary(db):
    print("\n=== TEST LOGIN ACCOUNTS ===")
    print("admin1  / Admin123!  (ADMIN)")
    print("agent1  / Agent123!  (AGENT)")
    print("agent2  / Agent456!  (AGENT)")
    print("viewer1 / Viewer123! (VIEWER)")

    print("\n=== IMPORTANT TEST CASES ===")
    print("1. Priya Shah: two SUCCESS transactions for ₹1299 yesterday (Asia/Kolkata local date).")
    print("   Ticket: 'Charged twice yesterday for the same purchase'")
    print("2. Daniel Cho: FAILED ₹2499 transaction followed by SUCCESS retry yesterday.")
    print("   Ticket asks whether he was charged twice.")
    print("3. Amara Okafor: ₹4999 SUCCESS transaction with PENDING refund 5 days ago.")
    print("4. Sofia Ramirez: ₹7999 SUCCESS transaction with COMPLETED refund.")
    print("5. Tomas Novak: ₹3499 SUCCESS upgrade with FAILED refund.")
    print("6. Nadia Husain: FAILED ₹899 subscription transaction 2 days ago; ticket is awaiting clarification.")
    print("7. Liam Fitzgerald: account-access ticket intentionally has no transaction history.")

    print("\n=== ROW COUNTS ===")
    for model in (
        User,
        Customer,
        Transaction,
        Ticket,
        TicketEvent,
        AgentDraft,
        TicketResolution,
        CompanyPolicy,
        VerificationToken,
    ):
        print(f"{model.__tablename__:22s} {db.query(model).count():>3}")


def main():
    import asyncio

    db = SessionLocal()
    try:
        print(f"Resetting application data at {LOCAL_NOW.isoformat()} ...")
        reset_data(db)

        users = seed_users(db)
        customers = seed_customers(db)
        seed_transactions(db, customers)
        tickets = seed_tickets(db, customers, users)
        seed_events_and_drafts(db, tickets, users)
        seed_resolutions(db, tickets, users)
        seed_policies(db)
        print_summary(db)

        if "--enqueue" in sys.argv:
            queued_ids = [
                ticket.id
                for ticket in tickets
                if ticket.status == TicketStatus.QUEUED
            ]
            if not queued_ids:
                print("No QUEUED tickets found to enqueue.")
            else:
                print("\nEnqueuing QUEUED tickets...")
                asyncio.run(enqueue_queued_tickets(queued_ids))

        print("\nSeed complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
