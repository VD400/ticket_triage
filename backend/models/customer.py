from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from .base import Base
from sqlalchemy.orm import relationship

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    tickets = relationship("Ticket", back_populates="customer")
    transactions = relationship("Transaction", back_populates="customer")
    verification_tokens = relationship("VerificationToken", back_populates="customer")
