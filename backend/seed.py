import sys
from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import Customer, User, Ticket, Transaction, TicketResolution
from models.user import UserRole
from models.transaction import TransactionType, TransactionStatus, RefundStatus
from models.ticket import TicketCategory, TicketPriority, TicketStatus
from decimal import Decimal
from agent.embeddings import embed_texts_batch
from models import CompanyPolicy

def seed_company_policies(db):
    policies = [
        ("Refund Policy",
         "Card refunds are normally processed within 5-7 business days. Failed transactions "
         "are automatically reversed within 3 business days. Manual refunds require payment verification."),

        ("OTP and SMS Policy",
         "Customers may request a maximum of 5 OTPs per hour. OTP delivery to international "
         "phone numbers may be delayed or unsupported depending on carrier agreements."),

        ("Duplicate Charge Policy",
         "A duplicate charge may reflect a temporary authorization hold rather than an actual "
         "second capture. Authorization holds are automatically released within 3-5 business days "
         "if not confirmed as a real charge."),

        ("Account Lockout Policy",
         "Accounts are automatically locked after 5 failed login attempts within 15 minutes. "
         "Locked accounts are automatically unlocked after 30 minutes, or can be manually unlocked "
         "by an agent after identity verification."),

        ("Shipment Delay Escalation Policy",
         "If a shipment has no carrier scan update for more than 48 hours past the expected "
         "delivery date, the ticket should be escalated to the logistics team for investigation."),
    ]
    texts = [p[1] for p in policies]
    embeddings = embed_texts_batch(texts, input_type="search_document")
    for (title, text), embedding in zip(policies, embeddings):
        db.add(CompanyPolicy(title=title, policy_text=text, embedding=embedding))

    db.commit()
    print(f"Seeded {len(policies)} company policies.")
    

def reset_data(db):
    db.query(TicketResolution).delete()
    db.query(Ticket).delete()
    db.query(Transaction).delete()
    db.query(Customer).delete()
    db.query(User).delete()
    db.commit()
    print("Exisiting data cleared.")

def seed_users(db):
    users = [
        User(username="admin1", email="admin1@company.com", hashed_password="placeholder", role=UserRole.ADMIN),
        User(username="agent1", email="agent1@company.com", hashed_password="placeholder", role=UserRole.AGENT),
        User(username="agent2", email="agent2@company.com", hashed_password="placeholder", role=UserRole.AGENT),
        User(username="viewer1", email="viewer1@company.com", hashed_password="placeholder", role=UserRole.VIEWER),
    ]
    db.add_all(users)
    db.commit()
    print(f"Seeded {len(users)} users.")
    return users
    
def seed_customers(db):
    customers = [
        Customer(name="Priya Shah", email="priya.shah@example.com", email_verified=True),
        Customer(name="Daniel Cho", email="daniel.cho@example.com", email_verified=True),
        Customer(name="Amara Okafor", email="amara.okafor@example.com", email_verified=True),
        Customer(name="Liam Fitzgerald", email="liam.fitz@example.com", email_verified=False),
        Customer(name="Sofia Ramirez", email="sofia.ramirez@example.com", email_verified=True),
        Customer(name="Kenji Watanabe", email="kenji.w@example.com", email_verified=True),
        Customer(name="Nadia Husain", email="nadia.husain@example.com", email_verified=False),
        Customer(name="Tomas Novak", email="tomas.novak@example.com", email_verified=True),
    ]
    db.add_all(customers)
    db.commit()
    print(f"Seeded {len(customers)} customers.")
    return customers

def seed_transactions(db, customers):
    now = datetime.now(timezone.utc)
    transactions = [
        Transaction(customer_id=customers[0].id, amount=Decimal("29.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=30)),
        Transaction(customer_id=customers[0].id, amount=Decimal("29.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=30),
                    refund_status=None),
        # duplicate charge scenario for customer[0] — same day, same amount
        Transaction(customer_id=customers[0].id, amount=Decimal("29.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=2)),
        Transaction(customer_id=customers[0].id, amount=Decimal("29.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=2)),

        Transaction(customer_id=customers[1].id, amount=Decimal("99.00"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.UPGRADE, created_at=now - timedelta(days=15)),
        Transaction(customer_id=customers[1].id, amount=Decimal("15.00"), status=TransactionStatus.FAILED,
                    transaction_type=TransactionType.ONE_TIME_PURCHASE, created_at=now - timedelta(days=5)),

        Transaction(customer_id=customers[2].id, amount=Decimal("49.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=45),
                    refund_status=RefundStatus.COMPLETED),
        Transaction(customer_id=customers[3].id, amount=Decimal("9.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.ONE_TIME_PURCHASE, created_at=now - timedelta(days=10)),

        Transaction(customer_id=customers[4].id, amount=Decimal("199.00"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.UPGRADE, created_at=now - timedelta(days=7),
                    refund_status=RefundStatus.PENDING),

        Transaction(customer_id=customers[5].id, amount=Decimal("29.99"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=60)),

        Transaction(customer_id=customers[6].id, amount=Decimal("29.99"), status=TransactionStatus.FAILED,
                    transaction_type=TransactionType.SUBSCRIPTION, created_at=now - timedelta(days=1)),

        Transaction(customer_id=customers[7].id, amount=Decimal("299.00"), status=TransactionStatus.SUCCESS,
                    transaction_type=TransactionType.UPGRADE, created_at=now - timedelta(days=20),
                    refund_status=RefundStatus.FAILED),
    ]
    db.add_all(transactions)
    db.commit()
    print(f"Seeded {len(transactions)} transactions.")
    return transactions

def seed_tickets(db, customers, users):
    now = datetime.now(timezone.utc)
    agent_ids = [u.id for u in users if u.role == UserRole.AGENT]

    tickets = [
        # -- resolved tickets (will get a TicketResolution row) --
        Ticket(customer_id=customers[0].id, subject="Charged twice for subscription",
               description="I was charged twice this week for my monthly plan, please refund the duplicate.",
               category=TicketCategory.BILLING, priority=TicketPriority.HIGH,
               status=TicketStatus.RESOLVED, assigned_agent_id=agent_ids[0],
               created_at=now - timedelta(days=2)),

        Ticket(customer_id=customers[2].id, subject="Refund never received",
               description="I cancelled last month and was told I'd get a refund, but I don't see it in my account.",
               category=TicketCategory.REFUND, priority=TicketPriority.MEDIUM,
               status=TicketStatus.RESOLVED, assigned_agent_id=agent_ids[1],
               created_at=now - timedelta(days=40)),

        Ticket(customer_id=customers[5].id, subject="Can't log into my account",
               description="I've tried resetting my password three times and still can't get in.",
               category=TicketCategory.ACCOUNT_ACCESS, priority=TicketPriority.HIGH,
               status=TicketStatus.RESOLVED, assigned_agent_id=agent_ids[0],
               created_at=now - timedelta(days=12)),

        Ticket(customer_id=customers[3].id, subject="App crashes when uploading files",
               description="Every time I try to upload a PDF larger than 5MB the app crashes completely.",
               category=TicketCategory.BUG_REPORT, priority=TicketPriority.URGENT,
               status=TicketStatus.RESOLVED, assigned_agent_id=agent_ids[1],
               created_at=now - timedelta(days=8)),

        # -- in-flight / not yet resolved, for testing the agent pipeline later --
        Ticket(customer_id=customers[1].id, subject="Failed payment for one-time purchase",
               description="My card was declined but I was still notified the purchase went through. Confused.",
               status=TicketStatus.QUEUED, created_at=now - timedelta(hours=3)),
        
        Ticket(customer_id=customers[4].id, subject="Requesting refund status update",
               description="I requested a refund for my upgrade a week ago and haven't heard anything.",
               status=TicketStatus.QUEUED, created_at=now - timedelta(hours=1)),

        Ticket(customer_id=customers[6].id, subject="Subscription payment keeps failing",
               description="My card is valid but the subscription charge keeps failing every month now.",
               status=TicketStatus.QUEUED, created_at=now - timedelta(minutes=30)),

        Ticket(customer_id=customers[7].id, subject="Refund for upgrade failed on your end",
               description="I was told my upgrade would be refunded but it says the refund itself failed.",
               status=TicketStatus.QUEUED, created_at=now - timedelta(minutes=10)),

        Ticket(customer_id=customers[3].id, subject="Feature request: dark mode",
               description="Would love to see a dark mode option added to the dashboard.",
               status=TicketStatus.QUEUED, created_at=now - timedelta(days=1)),
    ]
    db.add_all(tickets)
    db.commit()
    print(f"Seeded {len(tickets)} tickets.")
    return tickets

def seed_resolutions(db, tickets, users):
    agent_ids = [u.id for u in users if u.role == UserRole.AGENT]
    resolved = [t for t in tickets if t.status == TicketStatus.RESOLVED]

    resolution_texts = [
        "Confirmed duplicate charge in transaction history. Issued a refund for the extra charge; "
        "customer notified it will appear within 3-5 business days.",

        "Checked refund records and found the original refund had failed silently. Reprocessed the refund "
        "manually and confirmed with the customer via email.",

        "Reset the customer's password manually and cleared a stale session token that was blocking login. "
        "Customer confirmed access restored.",

        "Identified the crash was caused by file size validation happening after upload instead of before. "
        "Escalated to engineering; provided customer a workaround of compressing files under 5MB in the meantime.",
    ]

    resolutions = []
    embeddings = embed_texts_batch(resolution_texts, input_type="search_document")
    for ticket, text, embedding, agent_id in zip(resolved, resolution_texts, embeddings, agent_ids * 2):
        resolutions.append(
            TicketResolution(
                ticket_id=ticket.id,
                resolved_by=agent_id,
                resolution_text=text,
                embedding=embedding,
            )
        )

    db.add_all(resolutions)
    db.commit()
    print(f"Seeded {len(resolutions)} ticket resolutions (with embeddings).")



def main():
    db = SessionLocal()
    if "--reset" in sys.argv:
        reset_data(db)

    # users = seed_users(db)
    # customers = seed_customers(db)
    # seed_transactions(db, customers)
    # tickets = seed_tickets(db, customers, users)
    # seed_resolutions(db, tickets, users)
    seed_company_policies(db)
    db.close()
    print("Seeding complete.")


if __name__ == "__main__":
    main()