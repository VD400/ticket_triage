from .base import Base
from sqlalchemy import Enum as SQLEnum, Column, Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AGENT = "agent"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique = True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VIEWER)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    assigned_tickets = relationship("Ticket", back_populates="assigned_agent")
    resolutions = relationship("TicketResolution", back_populates="resolver")
    reviewed_drafts = relationship("AgentDraft", back_populates="reviewer")