from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from agent.state import AgentState
from dotenv import load_dotenv
from .nodes import (classify_ticket, rag_event_resolution_node, 
                    rag_over_policies_node, sql_node, human_assistance_node, 
                    supervisor_node, synthesizer_node)

load_dotenv()

def build_graph(checkpointer):
    graphbuilder = StateGraph(AgentState)
    
    graphbuilder.add_node("Classify-ticket-node", classify_ticket)
    graphbuilder.add_node("Rag-past-event-node", rag_event_resolution_node)
    graphbuilder.add_node("Rag-policy-node", rag_over_policies_node)
    graphbuilder.add_node("SQL-node", sql_node)
    graphbuilder.add_node("Human-assistance-node", human_assistance_node)
    graphbuilder.add_node("Supervisor-node", supervisor_node)
    graphbuilder.add_node("Synthesizer-node", synthesizer_node)
    
    graphbuilder.add_edge(START, "Classify-ticket-node")
    graphbuilder.add_edge("Classify-ticket-node", "Rag-past-event-node")
    graphbuilder.add_edge("Rag-past-event-node", "Supervisor-node")
    graphbuilder.add_conditional_edges(
        "Supervisor-node", 
        lambda state: state['next_action'],
        {'POLICY_RAG' : 'Rag-policy-node', 'SQL' : 'SQL-node', 'HUMAN_CLARIFICATION' : 'Human-assistance-node', 'SYNTHESIS' : 'Synthesizer-node'}
    )
    graphbuilder.add_edge("Rag-policy-node", "Supervisor-node")
    graphbuilder.add_edge("SQL-node", "Supervisor-node")
    graphbuilder.add_edge("Human-assistance-node", "Supervisor-node")
    graphbuilder.add_edge("Synthesizer-node", END)
    
    return graphbuilder.compile(checkpointer=checkpointer)

    