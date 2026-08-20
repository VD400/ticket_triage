from sqlalchemy import Column, Enum as SQLEnum, Text, Integer, String, DateTime, ForeignKey, UniqueConstraint
import enum
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from .base import Base
from pgvector.sqlalchemy import Vector

class TicketResolution(Base):
    __tablename__ = "ticket_resolutions"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_ticket_resolution_ticket_id"),)
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    ticket = relationship("Ticket", back_populates="resolution")
    resolver = relationship("User", back_populates="resolutions")
    