from sqlalchemy import Column, Integer, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
import enum
from .base import Base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class TicketEventType(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING_STARTED = "processing_started"
    AWAITING_APPROVAL = "awaiting_approval"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    FAILED = "failed"
    
    CLASSIFIED = "classified"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    DRAFT_CREATED = "draft_created"
    DRAFT_EDITED = "draft_edited"
    
    
class TicketEvent(Base):
    __tablename__ = "ticket_events"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    event_type = Column(SQLEnum(TicketEventType), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    ticket = relationship("Ticket", back_populates="events")