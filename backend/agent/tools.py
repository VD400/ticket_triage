from .embeddings import embed_text
from database import SessionLocal
from .readonly_db import readonly_session
from sqlalchemy.orm import Session
from .llm import groq_llm
from sqlalchemy import text
from models.ticket_resolution import TicketResolution
from models.company_policy import CompanyPolicy
from agent.schema import table_schema 
import re
from decimal import Decimal
from datetime import date, datetime

def rag_over_tickets(query: str,top_k: int = 3) -> list[str]:
    query_embedding = embed_text(query, input_type="search_query")
    db = SessionLocal()
    try:
        matches = db.query(TicketResolution).order_by(TicketResolution.embedding.cosine_distance(query_embedding)).limit(top_k).all()
    finally:
        db.close()
    return [row.resolution_text for row in matches]

def  rag_over_policies_tool(query: str, top_k: int = 2):
    query_embedding = embed_text(query, input_type="search_query")
    db = SessionLocal()
    try:
        matches = db.query(CompanyPolicy).order_by(CompanyPolicy.embedding.cosine_distance(query_embedding)).limit(top_k).all()
    finally:
        db.close()
    return [row.policy_text for row in matches]

_DISALLOWED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|GRANT|REVOKE|ALTER|CREATE)\b",
    re.IGNORECASE,
)

def generate_sql_tool(question: str) -> str:
    prompt = f"""The table schema of a relational database written in postgresql is as follows:
    {table_schema}
    
    Claim:
    {question}
    
    Based on this table schema and the claim, create a SELECT postgresql query that correctly answers or verifies the content claimed. Follow these strict rules:
    1. Never generate INSERT, UPDATE, DELETE, DROP, TRUNCATE, GRANT, REVOKE, or ALTER.
    2. Never generate any query that edits, deletes, or changes data in any way.
    3. If the question requires changing or deleting data, refuse and say so instead of generating SQL.
    4. Return only a valid PostgreSQL query starting with SELECT.
    5. Enum-like columns (status, category, priority, transaction_type, refund_status) are stored in UPPERCASE — match this exact casing.
    6. When filtering by name-like text fields, use ILIKE with wildcards instead of exact equality.

    POSTGRESQL query:
    """
    response = groq_llm.invoke(prompt)
    sql = response.content.strip()
    sql = re.sub(r"^```sql\s*|```$", "", sql, flags=re.IGNORECASE).strip()
    if not sql.upper().startswith("SELECT"):
        raise ValueError(f"Refusing non-SELECT SQL from generate_sql_tool: {sql!r}")
    if ";" in sql.rstrip(";"):
        # A second statement after the first — classic injection pattern.
        raise ValueError(f"Refusing multi-statement SQL: {sql!r}")
    if _DISALLOWED_SQL.search(sql):
        raise ValueError(f"Refusing SQL containing a disallowed keyword: {sql!r}")
    return sql

def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value    

def execute_readonly_query_tool(sql : str) -> list[dict]:
    db = readonly_session()
    try:
        result = db.execute(text(sql))
        return [
            {k: _json_safe(v) for k,v in dict(row).items()}
            for row in result.mappings()
        ]
    finally:
        db.close()
        