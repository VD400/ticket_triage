from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship 
from .base import Base
from datetime import datetime, timezone
import enum

class DraftStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    
class AgentDraft(Base):
    __tablename__ = "agent_drafts"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    draft_text = Column(Text, nullable=False)
    status = Column(SQLEnum(DraftStatus), default=DraftStatus.PENDING_REVIEW, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    ticket = relationship("Ticket", back_populates="drafts")
    reviewer = relationship("User", back_populates="reviewed_drafts")