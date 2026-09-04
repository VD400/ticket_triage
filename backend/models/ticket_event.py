from sqlalchemy import Column, Integer, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
import enum
from .base import Base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class TicketEventType(str, enum.Enum):
    # ticket lifestyle
    QUEUED = "queued"
    PROCESSING_STARTED = "processing_started"
    AWAITING_APPROVAL = "awaiting_approval"
    RESOLVED = "resolved"
    FAILED = "failed"
    
    # agent reasoning trace
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_ANSWERED = "clarification_answered"
    CLASSIFIED = "classified"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    SUPERVISOR_DECISION = "supervisor_decision"
    
    # draft-specific events
    DRAFT_CREATED = "draft_created"
    DRAFT_REJECTED = "draft_rejected"
    DRAFT_EDITED = "draft_edited"
    DRAFT_APPROVED = "draft_approved"
    
    
class TicketEvent(Base):
    __tablename__ = "ticket_events"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    event_type = Column(SQLEnum(TicketEventType), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    ticket = relationship("Ticket", back_populates="events")