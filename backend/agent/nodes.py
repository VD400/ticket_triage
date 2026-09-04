from .llm import groq_llm
from .state import AgentState
from .tools import rag_over_tickets, rag_over_policies_tool, generate_sql_tool, execute_readonly_query_tool
import json
from langgraph.types import interrupt
from models.ticket_event import TicketEvent, TicketEventType
from tickets.services import record_ticket_event
from  database import SessionLocal
from models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus

max_tool_calls_allowed = 4

def _update_ticket(ticket_id: int, **fields):
    db = SessionLocal()
    try:
        db.query(Ticket).filter(Ticket.id == ticket_id).update(fields)
        db.commit()
    finally:
        db.close()
    

def classify_ticket(agent_state: AgentState):
    record_ticket_event(ticket_id=agent_state['ticket_id'], 
                        event_type=TicketEventType.PROCESSING_STARTED)
    
    prompt = f'''You are an AI support-ticket triage assistant.

    Your task is to analyze a customer support ticket and assign:

    1. Exactly one category
    2. Exactly one priority

    You MUST choose ONLY from the allowed uppercase values below.

    TICKET CATEGORIES

    - BILLING: Charges, invoices, payments, subscriptions, pricing, or unexpected charges.
    - ACCOUNT_ACCESS: Login problems, password resets, authentication failures, locked accounts, access issues, or inability to access an account.
    - BUG_REPORT: Something in the product is not working as expected, including errors, crashes, broken functionality, or incorrect behavior.
    - FEATURE_REQUEST: The customer is requesting a new feature, enhancement, integration, or change to existing product behavior.
    - REFUND: The customer is requesting, asking about, or reporting a missing, refused, or failed refund or reimbursement.
    - GENERAL_INQUIRY: A general question or request for information that does not primarily fall into another category.
    - OTHER: The ticket does not clearly fit any of the categories above.

    PRIORITY LEVELS

    - LOW: Non-urgent issue with little or no immediate impact. The customer can continue using the product normally, or is making a general request/question.
    - MEDIUM: A meaningful problem affecting the customer, but there is a reasonable workaround or limited impact. The issue does not require immediate attention.
    - HIGH: Significant impact on the customer or business. The customer may be unable to use an important feature, may have lost money, or the issue may require prompt investigation.
    - URGENT: Severe or time-critical impact. Examples include suspected unauthorized financial activity, major financial loss, inability to access a critical service, widespread service failure, security-related concerns, or an issue requiring immediate human intervention.

    CLASSIFICATION RULES

    1. Choose exactly one category and exactly one priority.
    2. The category MUST be one of:
    BILLING, ACCOUNT_ACCESS, BUG_REPORT, FEATURE_REQUEST, REFUND, GENERAL_INQUIRY, OTHER.
    3. The priority MUST be one of:
    LOW, MEDIUM, HIGH, URGENT.
    4. Always return category and priority in UPPERCASE.
    5. Base your decision only on the information contained in the ticket.
    6. Do not invent facts, causes, or technical details that are not stated.
    7. Category describes WHAT the customer is contacting support about.
    8. Priority describes HOW IMPORTANT or TIME-SENSITIVE the issue is.
    9. Do not automatically assign HIGH or URGENT priority just because the ticket involves money.
    10. If multiple categories appear, choose the customer's primary reason for contacting support.
    11. A refund request should normally be classified as REFUND, even though it may also involve billing.
    12. A payment problem without a refund request should normally be classified as BILLING.
    13. A product malfunction should normally be classified as BUG_REPORT, even if the customer is frustrated.
    14. A request for something the product does not currently provide should normally be FEATURE_REQUEST.
    15. If there is insufficient information to justify a higher priority, choose the lower reasonable priority.
    16. If the ticket is ambiguous and does not clearly fit the available categories, choose OTHER.
    17. If the ticket contains a possible security issue or unauthorized transaction, consider URGENT priority.
    18. Do not assume the root cause of the problem.

    For example, if a customer says:
    "My payment failed but I was charged."

    Do NOT claim:
    "The payment gateway failed."

    The ticket only establishes that the payment appears to have failed from the customer's perspective and that they were charged.

    OUTPUT REQUIREMENTS

    Return ONLY valid JSON.

    The "category" value MUST be one of:
    "BILLING"
    "ACCOUNT_ACCESS"
    "BUG_REPORT"
    "FEATURE_REQUEST"
    "REFUND"
    "GENERAL_INQUIRY"
    "OTHER"

    The "priority" value MUST be one of:
    "LOW"
    "MEDIUM"
    "HIGH"
    "URGENT"

    The values MUST be uppercase exactly as written above.

    Use this exact JSON structure:

    {{
    "category": "BILLING",
    "priority": "HIGH",
    "reason": "Brief explanation of why this category and priority were chosen."
    }}

    Do not include markdown, code fences, additional fields, or any text outside the JSON object.

    Customer ticket:
    {agent_state['ticket_text']}

    Response:
    '''
        
    payload = groq_llm.invoke(prompt)
    
    result = json.loads(payload.content)
    category = result["category"]
    priority = result["priority"]
    if category not in {"BILLING", "ACCOUNT_ACCESS", "BUG_REPORT",
                    "FEATURE_REQUEST", "REFUND",
                    "GENERAL_INQUIRY", "OTHER"}:
        raise ValueError(f"Invalid category: {category}")

    if priority not in {"LOW", "MEDIUM", "HIGH", "URGENT"}:
        raise ValueError(f"Invalid priority: {priority}")
    
    _update_ticket(
        agent_state['ticket_id'],
        category=TicketCategory[category],
        priority=TicketPriority[priority],
        status=TicketStatus.PROCESSING
    )
    
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.CLASSIFIED,
                        payload={
                            "category": category,
                            "priority": priority,
                            "reason": result["reason"]
                        })
    return {
        "category": category,
        "priority": priority
    }
    

def rag_event_resolution_node(agent_state: AgentState):
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_CALLED,
                        payload={
                            "tool_used" : "past_tickets_rag"
                        })
    query = agent_state["ticket_text"]
    similar_res = rag_over_tickets(query)
    res = "\n\n".join(r for r in similar_res)
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_RESULT,
                        payload={
                            "tool_used" : "past_tickets_rag",
                            "content" : res
                        })
    return {
        "context": [{"source" : "past_tickets_rag",
                     "content" : res}],
        "tool_calls_made" : ['past_tickets_rag']
    }
    
def rag_over_policies_node(agent_state: AgentState):
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_CALLED,
                        payload={
                            "tool_used" : "policies_rag"
                        })
    query = agent_state['ticket_text']
    relevant_policies = rag_over_policies_tool(query)
    policies = "\n\n".join(p for p in relevant_policies)
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_RESULT,
                        payload={
                            "tool_used" : "policies_rag",
                            "content": policies
                        })
    return {
        "context" : [{"source" : "policies_rag",
                      "content" : policies}],
        "tool_calls_made" : ['policies_rag']
    }
    
def sql_node(agent_state: AgentState):
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_CALLED,
                        payload={
                            "tool_used" : "sql"
                        })
    query = agent_state['ticket_text']
    relevant_sql = generate_sql_tool(query)
    relevant_context = execute_readonly_query_tool(relevant_sql)
    context = "\n\n".join(f"Row {i + 1}: {row}" for i, row in enumerate(relevant_context))
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.TOOL_RESULT,
                        payload={
                            "tool_used" : "sql",
                            "content": context
                        })
    return {
        "context" : [{"source" : "sql",
                      "content" : context}],
        "tool_calls_made" : ['sql']
    }
    
def human_assistance_node(agent_state : AgentState):
    # record_ticket_event(ticket_id=agent_state['ticket_id'],
    #                     event_type=TicketEventType.TOOL_CALLED,
    #                     payload={
    #                         'tool_used': "human_clarification",
    #                         "question": agent_state['clarification_question']
    #                     })
    question = agent_state["clarification_question"]
    _update_ticket(agent_state["ticket_id"], status=TicketStatus.AWAITING_CLARIFICATION)
    
    answer = interrupt({
        "type" : "human_clarification",
        "question" : question,
        "ticket_id" : agent_state["ticket_id"]
    })
    
    _update_ticket(agent_state['ticket_id'], status=TicketStatus.PROCESSING)
    
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.CLARIFICATION_ANSWERED,
                        payload={
                            "tool_used" : "human_clarification",
                            "question": question,
                            "answer": answer
                        })
    return {
        "clarification_answer" : answer,
        "tool_calls_made" : ['human_clarification'],
        "context" : [{"source" : "human_clarification",
                      "content" : answer}]
    }
    
def supervisor_node(agent_state: AgentState):
    prompt = f"""
    You are the Supervisor of an AI-assisted customer support ticket resolution system.

    Your job is NOT to answer the customer and NOT to write the final response.

    Your only responsibility is to examine the ticket, the classification, the information already retrieved, and the actions already taken, then decide the SINGLE best next action required to resolve the ticket safely and accurately.

    AVAILABLE ACTIONS

    1. POLICY_RAG
    Use this when you need company-specific policies, procedures, rules, SLAs, refund rules, escalation rules, troubleshooting procedures, or other internal knowledge.

    2. SQL
    Use this when you need to verify facts about the customer's actual data or current system state, such as:
    - transaction status
    - refund status
    - account status
    - ticket history
    - subscription state
    - other information stored in the database

    Do NOT use SQL merely because it is available. Use it only when the customer's actual data must be verified.

    3. HUMAN_CLARIFICATION
    Use this when required information is missing and cannot reasonably be obtained from the available database or knowledge base.

    Examples:
    - Missing transaction ID when it is required to identify the transaction
    - Ambiguous information that cannot be resolved from existing data
    - A decision requiring human judgment or confirmation

    If selecting HUMAN_CLARIFICATION, also provide a concise question that should be presented to the human.

    4. SYNTHESIS
    Use this when enough reliable information has been collected and no additional action is necessary.

    The next step after SYNTHESIS is for another node to generate:
    - an internal analysis for the support employee
    - a customer-facing response draft

    EVIDENCE PRIORITY

    When information conflicts, use this priority:

    1. Current verified database information from SQL
    2. Current company policies retrieved through POLICY_RAG
    3. Human-provided clarification
    4. Historical resolved tickets retrieved through RAG

    Historical tickets are examples of previous cases and should NOT be treated as authoritative facts about the current customer.

    IMPORTANT REASONING RULES

    1. Do not assume a root cause that has not been verified.
    2. Distinguish between:
    - facts explicitly supported by evidence
    - plausible explanations
    - unknown information
    3. Do not use a tool simply because it exists.
    4. Choose the minimum number of actions necessary to obtain enough reliable information.
    5. If the available context is already sufficient, choose SYNTHESIS.
    6. Do not repeat an action that has already been performed unless there is a clear reason that another call is necessary.
    7. If SQL can directly verify a claim about the customer's account or transaction, prefer SQL over guessing from historical tickets.
    8. Use POLICY_RAG when the correct response depends on company rules rather than customer-specific state.
    9. Use HUMAN_CLARIFICATION when the missing information cannot be obtained through SQL or company knowledge.
    10. Never claim that a transaction succeeded, failed, was refunded, or was reversed unless the available evidence supports that conclusion.
    11. Do not generate the customer-facing response yourself.
    12. Do not modify the category or priority. Those were already assigned by the classifier.
    13. If the action budget has been reached, choose SYNTHESIS unless human clarification is absolutely necessary.
    14. Do not select an action that has already been performed unless the existing result is clearly insufficient.

    ACTION BUDGET

    Maximum number of actions allowed:
    {max_tool_calls_allowed}

    Actions already performed:
    {agent_state['tool_calls_made']}

    If the number of actions already performed is equal to or greater than the maximum, normally choose SYNTHESIS.

    CURRENT TICKET

    {agent_state['ticket_text']}

    CLASSIFICATION

    Category: {agent_state['category']}
    Priority: {agent_state['priority']}

    CONTEXT COLLECTED SO FAR

    {agent_state['context']}

    HUMAN CLARIFICATION ANSWER, IF ANY

    {agent_state['clarification_answer']}

    DECISION EXAMPLE

    Customer ticket:
    "My payment failed but ₹5,000 was deducted from my account."

    Category:
    BILLING

    Priority:
    HIGH

    Previous ticket RAG:
    - Similar cases involved either temporary authorization holds or a successful payment where order creation failed.
    - Historical tickets alone do not determine what happened to this customer.

    Actions already performed:
    ["past_ticket_rag"]

    Reasoning:
    The historical tickets provide possible explanations, but they do not establish the current customer's transaction state. The actual transaction should be verified before drafting a response.

    Correct decision in this case:

    {{
        "next_action": "SQL",
        "reason": "The customer's transaction status must be verified from the database before determining the appropriate resolution.",
        "clarification_question": null
    }}

    OUTPUT REQUIREMENTS

    Return ONLY valid JSON.

    "next_action" MUST be exactly one of:

    "POLICY_RAG"
    "SQL"
    "HUMAN_CLARIFICATION"
    "SYNTHESIS"

    "reason" must briefly explain why the selected action is necessary.

    "clarification_question" must be:
    - a concise question if next_action is HUMAN_CLARIFICATION
    - null for every other action

    Use exactly this structure:

    {{
        "next_action": "SQL",
        "reason": "The customer's transaction status must be verified.",
        "clarification_question": null
    }}

    Do not include markdown, code fences, additional fields, or any text outside the JSON object."""
    
    tool_calls_made = len(agent_state['tool_calls_made'])
    if tool_calls_made >= max_tool_calls_allowed:
        reason = "Maximum tool/action budget reached."

        record_ticket_event(
            ticket_id=agent_state["ticket_id"],
            event_type=TicketEventType.SUPERVISOR_DECISION,
            payload={
                "next_action": "SYNTHESIS",
                "reason": reason,
                "tool_calls_made": agent_state["tool_calls_made"],
            },
        )
        return {
            "next_action": "SYNTHESIS"
        }
    
    path_taken = groq_llm.invoke(prompt)
    result = json.loads(path_taken.content)

    allowed_actions = {
        "POLICY_RAG",
        "SQL",
        "HUMAN_CLARIFICATION",
        "SYNTHESIS",
    }

    if result["next_action"] not in allowed_actions:
        raise ValueError(f"Invalid supervisor action: {result['next_action']}")
    record_ticket_event(ticket_id=agent_state['ticket_id'],
                        event_type=TicketEventType.SUPERVISOR_DECISION,
                        payload={
                            "next_action" : result['next_action'],
                            "reason": result['reason'],
                            "tool_calls_made": agent_state['tool_calls_made']
                        })
    if(result["next_action"] == 'HUMAN_CLARIFICATION'):
        record_ticket_event(ticket_id=agent_state['ticket_id'],
                            event_type=TicketEventType.CLARIFICATION_REQUESTED,
                            payload={
                                "question": result["clarification_question"]
                            })
        
    return {
        "next_action": result["next_action"],
        "clarification_question": result.get("clarification_question"),
    }


def synthesizer_node(agent_state: AgentState):
    context_text = "\n\n".join(f"[SOURCE: {c['source']}]\n{c['content']}" for c in agent_state['context'])
    prompt = f'''You are the final synthesis assistant for an AI-assisted customer support system.

Your task is to take the customer's original ticket, its classification, and all evidence gathered by the support workflow and produce TWO outputs:

1. An INTERNAL ANALYSIS for the support employee.
2. A CUSTOMER-FACING DRAFT that can be reviewed and then sent to the customer.

You are NOT the final decision-maker. The support employee will review your analysis and draft before sending anything to the customer.

IMPORTANT PRINCIPLES

1. Base your conclusions only on the ticket and the supplied context.
2. Do not invent facts, transaction states, causes, policies, actions, or resolutions.
3. Clearly distinguish between:
   - facts directly verified from the database,
   - information from company policies,
   - information from historical resolved tickets,
   - information provided by the human,
   - reasonable possibilities that are NOT confirmed.
4. Historical tickets are examples of previous cases. They are NOT proof of what happened to the current customer.
5. Database verification is authoritative for the current customer's actual state when available.
6. Company policies should be followed when relevant.
7. If the root cause cannot be established from the available information, explicitly say that it is unknown.
8. Do not tell the customer that something was fixed, refunded, approved, reversed, escalated, or completed unless the provided evidence confirms that it actually happened.
9. Never expose internal database details, internal reasoning, internal tool information, or confidential company information in the customer-facing draft unless it is appropriate and safe to disclose.
10. The customer-facing draft should be helpful, professional, empathetic, and concise.
11. Do not repeat questions that have already been answered by the customer or by the collected context.
12. Do not promise a specific outcome or timeline unless the available evidence or company policy supports it.

INPUT INFORMATION

CUSTOMER TICKET
{agent_state['ticket_text']}

CLASSIFICATION

Category: {agent_state['category']}
Priority: {agent_state['priority']}

CONTEXT AND EVIDENCE

{context_text}

HUMAN CLARIFICATION QUESTION, IF ANY

{agent_state['clarification_question']}

HUMAN CLARIFICATION ANSWER, IF ANY
This information was provided by a human during the support workflow.
Use it as evidence, but do not treat it as system-verified unless corroborated by the database or another authoritative source.
{agent_state['clarification_answer']}

INTERNAL ANALYSIS REQUIREMENTS

Create an internal analysis for the support employee containing the following sections:

1. TICKET
Briefly restate the customer's actual issue based on the original ticket.

2. CLASSIFICATION
State the assigned category and priority.

3. VERIFIED FACTS
List facts that are directly supported by the available evidence.

4. RELEVANT CONTEXT
Summarize the most useful information from:
- similar historical resolutions,
- company policies,
- database verification,
- human clarification.

Clearly indicate the source when useful.

5. WHAT IS NOT VERIFIED
Identify important facts or root causes that remain unknown.

6. RECOMMENDED ACTION
Explain what the employee should do next to resolve the ticket.
Use the available evidence and company procedures.
Do not recommend an action that conflicts with verified information.

7. RESPONSE GUIDANCE
Briefly explain what the customer should be told and what should NOT be claimed.

The internal analysis should help an employee resolve the ticket efficiently. It should be practical rather than verbose.

CUSTOMER-FACING DRAFT REQUIREMENTS

Create a separate response that can be sent to the customer after employee review.

The draft should:

- Directly address the customer's complaint.
- Acknowledge the customer's frustration when appropriate.
- Explain the verified situation clearly.
- State the action already taken if it is actually verified.
- If the issue is still under investigation, say so clearly.
- Ask the customer for additional information only when necessary.
- Provide the relevant next step.
- Reassure the customer without making unsupported promises.
- Follow relevant company policy.
- Never mention the AI, RAG, database, tools, internal analysis, historical tickets, or supervisor.
- Never claim a root cause that has not been verified.
- Never fabricate transaction IDs, refund dates, ticket numbers, actions, or resolutions.
- Do not infer that the customer's desired outcome has been achieved merely because a recommended action exists.

IMPORTANT:

The internal analysis and customer-facing draft serve different purposes.

INTERNAL ANALYSIS:
Detailed enough to help the employee understand and resolve the issue.

CUSTOMER DRAFT:
Only information that is appropriate to communicate to the customer.

EXAMPLE

CUSTOMER TICKET:
"My payment failed but ₹5,000 was deducted from my account."

CATEGORY:
BILLING

PRIORITY:
HIGH

CONTEXT:
[past_ticket_rag]
Similar cases included temporary authorization holds and cases where payment succeeded but order creation failed.

[sql]
Transaction status: FAILED
Refund status: PENDING

[policy_rag]
Failed transactions are normally reversed within 3 business days.

SYNTHESIZED INTERNAL ANALYSIS:

TICKET:
Customer reports that a payment failed but ₹5,000 was deducted.

CLASSIFICATION:
Category: BILLING
Priority: HIGH

VERIFIED FACTS:
- The transaction is recorded as FAILED.
- The refund/reversal status is currently PENDING.
- Company policy states failed transactions are normally reversed within 3 business days.

RELEVANT CONTEXT:
Historical tickets show that similar payment issues have occurred, but they do not establish the cause of this customer's transaction.

WHAT IS NOT VERIFIED:
- The exact technical reason for the failed transaction is not established.
- The final reversal has not yet been completed.

RECOMMENDED ACTION:
- Verify that the pending reversal is progressing normally.
- Monitor or escalate the transaction if it exceeds the company's stated reversal window.
- Do not tell the customer that the refund has already been completed.

RESPONSE GUIDANCE:
Inform the customer that the transaction is recorded as failed and that the amount is currently pending reversal. Do not claim a specific technical cause.

CUSTOMER-FACING DRAFT:
Hi,

I'm sorry for the trouble with your payment. We checked the transaction and it is currently showing as failed, with the amount still pending reversal.

According to our normal processing policy, failed transactions are typically reversed within 3 business days. We'll continue to monitor the transaction, and if the reversal does not complete within that timeframe, we can investigate it further.

Thank you for your patience.

OUTPUT REQUIREMENTS

Return ONLY valid JSON.

Return exactly these two fields:

{{
    "analysis": "Internal analysis for the support employee.",
    "draft_text": "Customer-facing response."
}}

Do not include markdown code fences.
Do not include any fields other than "analysis" and "draft_text".
Do not include any text outside the JSON object.'''

    response = groq_llm.invoke(prompt)
    res = response.content
    result = json.loads(res)
    if not isinstance(result, dict):
        raise ValueError("Synthesier returned invalid JSON.")
    if "analysis" not in result or "draft_text" not in result:
        raise ValueError("Synthesizer response missing required fields.")

    if not isinstance(result["analysis"], str):
        raise ValueError("Analysis must be a string.")

    if not isinstance(result["draft_text"], str):
        raise ValueError("Draft text must be a string.")
    
    return {
        "analysis" : result['analysis'],
        'draft_text' : result['draft_text']
    }


    
     
