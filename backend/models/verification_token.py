from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from .base import Base
from datetime import datetime, timezone
from sqlalchemy.orm import relationship

class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    customer = relationship("Customer", back_populates="verification_tokens")