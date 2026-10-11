from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from models.ticket import TicketCategory, TicketPriority, TicketStatus


class TicketCreateRequest(BaseModel):
    customer_id: int
    subject: str
    description: str


class TicketResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    assigned_agent_id: Optional[int]
    subject: str
    description: str
    category: Optional[TicketCategory]
    priority: Optional[TicketPriority]
    status: Optional[TicketStatus]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualResolutionRequest(BaseModel):
    resolution_text: str


class ClarificationAnswerRequest(BaseModel):
    answer: str
