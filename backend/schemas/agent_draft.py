from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, Any
from models.agent_draft import DraftStatus
from datetime import datetime

class AgentDraftResponse(BaseModel):
    id : int
    ticket_id : int
    reviewed_by : Optional[int]
    draft_text : str
    status : DraftStatus
    reviewed_at : Optional[datetime]
    analysis: Optional[dict[str, Any]]
    created_at : datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class AgentDraftRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_text: Optional[str] = None