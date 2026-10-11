from sqlalchemy import Column, Integer, String, Text, DateTime
from pgvector.sqlalchemy import Vector
from .base import Base
from datetime import datetime, timezone

class CompanyPolicy(Base):
    __tablename__ = "company_policies"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    policy_text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    