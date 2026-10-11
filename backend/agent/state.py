from typing import TypedDict, Optional, List, Annotated
import operator

class ContextItems(TypedDict):
    source: str
    content: list[str]
    

class AgentState(TypedDict):
    
    # ticket identity
    ticket_id: int
    ticket_text: str # subject desc 
    
    # classification results
    category: Optional[str]
    priority: Optional[str]
    
    # supervisor loop bookkeeping
    tool_calls_made: Annotated[List[str], operator.add] # to put a hard cap on no of tool uses
    context: Annotated[List[ContextItems], operator.add]  # tool results + clarification
    next_action: Optional[str] # supervisor's decision - rag/sql/policy/clarify/synthesis
    
    clarification_question: Optional[str]
    clarification_answer: Optional[str]
    
    # final output
    analysis: Optional[str]
    draft_text: Optional[str]
    
    
    