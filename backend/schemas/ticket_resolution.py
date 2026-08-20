from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TicketResolutionResponse(BaseModel):
    id: int
    ticket_id: int
    resolved_by: Optional[int]
    resolution_text: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
    