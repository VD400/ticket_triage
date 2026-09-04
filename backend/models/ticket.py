from sqlalchemy import Enum as SQLEnum, Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base
import enum

class TicketCategory(str, enum.Enum):
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    REFUND = "refund"
    GENERAL_INQUIRY = "general_inquiry"
    OTHER = "other"
 
class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent" 

class TicketStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    RESOLVED = "resolved"
    FAILED = "failed"

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(TicketCategory), nullable=True)
    priority = Column(SQLEnum(TicketPriority), nullable=True)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.QUEUED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    customer = relationship("Customer", back_populates="tickets")
    assigned_agent = relationship("User", back_populates="assigned_tickets")
    events = relationship("TicketEvent", back_populates="ticket")
    resolution = relationship("TicketResolution", back_populates="ticket", uselist=False)
    drafts = relationship("AgentDraft", back_populates="ticket")

