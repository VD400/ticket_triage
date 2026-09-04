from pydantic import BaseModel, ConfigDict
from models.ticket_event import TicketEventType
from typing import Optional, Any
from datetime import datetime

class TicketEventResponse(BaseModel):
    id: int
    ticket_id: int
    event_type: TicketEventType
    payload: Optional[dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

    
class TicketEventCreate(BaseModel):
    ticket_id: int
    event_type: TicketEventType
    payload: Optional[dict[str, Any]]
    created_at: datetime
    