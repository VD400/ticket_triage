import {useEffect, useState} from 'react';
import {API_BASE, toWsUrl} from "../components/dashboard/api";

const TOOL_TO_NODE = {
  past_tickets_rag: "Rag-past-event-node",
  policies_rag: "Rag-policy-node",
  sql: "SQL-node",
};
 
const ACTION_TO_NODE = {
  POLICY_RAG: "Rag-policy-node",
  SQL: "SQL-node",
  HUMAN_CLARIFICATION: "Human-assistance-node",
  SYNTHESIS: "Synthesizer-node",
};

function applyEvent(incoming, state){
    let activeNode = state.activeNode;
    let completedNodes = [...state.completedNodes]; 
    const markDone = (node) => {
        if(node && !completedNodes.includes(node)){
            completedNodes.push(node);
        }
    };

    switch(incoming.event_type){
            case "processing_started":
                activeNode = 'Classify-ticket-node';
                break;
            
            case "classified":
                markDone("Classify-ticket-node");
                activeNode = "Rag-past-event-node";
                break;

            case "tool_called":
                activeNode = TOOL_TO_NODE[incoming.payload?.tool_used] ?? null;
                break;

            case "tool_result":
                markDone(TOOL_TO_NODE[incoming.payload?.tool_used] ?? null);
                activeNode = "Supervisor-node";
                break;
                
            case "supervisor_decision":
                markDone("Supervisor-node");
                activeNode =ACTION_TO_NODE[incoming.payload?.next_action] ?? null;
                break;

            case "clarification_requested":
                activeNode = "Human-assistance-node";
                break;

            case "clarification_answered":
                markDone("Human-assistance-node");
                activeNode = "Supervisor-node";
                break;

            case "draft_created":
                markDone("Synthesizer-node");
                activeNode = null;
                break;
                
            default:
                break;
    }
    return {activeNode, completedNodes};
}

function buildExecutionState(events){
    let state = {
        activeNode: null,
        completedNodes: [],
    };
    for(const incoming of events){
        state = applyEvent(incoming, state);
    }
    return state;
}

export default function useTicketWebSocket(ticketId){
    const [events, setEvents] = useState([]);
    const [executionState, setExecutionState] =  useState({activeNode: null, completedNodes: []});
    const [connectionStatus, setConnectionStatus] = useState('connecting');
 
    useEffect(() => {
        if(!ticketId) return;
        setEvents([]);
        setConnectionStatus("connecting");
        setExecutionState({activeNode: null, completedNodes: []});
        const token = localStorage.getItem("token");
        if(!token){
            setConnectionStatus("error");
            return;
        }
        const socket = new WebSocket(
            `${toWsUrl(API_BASE)}/tickets/${ticketId}/stream?token=${encodeURIComponent(token)}`);
       
        socket.onopen = () => {
            console.log("Websocket connected");
            setConnectionStatus("connected");
        };

        socket.onclose = () => {
            setConnectionStatus((prev) => (prev === 'error' ? prev : "closed"));
        };

        socket.onerror = () => {
            setConnectionStatus("error");
        };

        socket.onmessage = (message) => {
            const incoming = JSON.parse(message.data);  // JSON.parse converts string to Javascript object
            if(incoming.type === "history"){
                setEvents(incoming.events);
                const executionSt = buildExecutionState(incoming.events);
                setExecutionState(executionSt);
                return;
            }

            console.log("Recieved event: ", incoming);
            setEvents((prev) => [...prev, incoming]);
            setExecutionState((prev) => applyEvent(incoming, prev));
        };
        return () => {
            socket.close();
        };
    }, [ticketId]);
    return {events, activeNode: executionState.activeNode, completedNodes: executionState.completedNodes, connectionStatus};
} 