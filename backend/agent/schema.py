table_schema = """
Table: customers (id: integer(primarykey), name: string(50), email: string(100), email_verified: boolean, created_at: timestamptz)
Table: transactions (id: integer(primarykey), customer_id: integer(foreignkey(customers.id)), amount: numeric(10,2), status: string('SUCCESS'|'FAILED'), transaction_type: string('SUBSCRIPTION'|'ONE_TIME_PURCHASE'|'UPGRADE'|'OTHER'), refund_status: string('PENDING'|'COMPLETED'|'FAILED', nullable), created_at: timestamptz)
Table: tickets (id: integer(primarykey), customer_id: integer(foreignkey(customers.id)), subject: string(150), description: text, category: string, priority: string, status: string, created_at: timestamptz)

Notes:
- A refunded charge has refund_status set on the ORIGINAL transaction row — there is no separate refund transaction.
- Enum values (status, transaction_type, refund_status, category, priority) are stored in UPPERCASE — always match this exact casing in WHERE clauses.
"""

