from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Ticket, Customer, VerificationToken
from models.user import UserRole
from models.ticket import TicketStatus
from schemas.ticket import TicketCreateRequest, TicketResponse, ManualResolutionRequest, ClarificationAnswerRequest
from models.ticket_event import TicketEvent, TicketEventType
from schemas.ticket_event import TicketEventResponse, TicketEventCreate
from models.ticket_resolution import TicketResolution
from schemas.ticket_resolution import TicketResolutionResponse
from models.agent_draft import AgentDraft, DraftStatus
from schemas.agent_draft import AgentDraftRequest, AgentDraftResponse
from auth.dependencies import get_current_user, require_role
from datetime import datetime, timezone
from agent.embeddings import embed_text
from agent.queue import get_redis_pool
from .services import record_ticket_event as record_ticket_event_service
from arq.connections import ArqRedis
from sqlalchemy import or_
from agent.events import publish_persisted_events
from agent.recovery import annotate_recovery, reserve_recovery
from redis.exceptions import RedisError


router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db), redis: ArqRedis=Depends(get_redis_pool)):
    verified = db.query(VerificationToken).join(Customer).filter(
        VerificationToken.token == payload.verification_token,
        VerificationToken.customer_id == payload.customer_id,
        VerificationToken.used.is_(True),
        VerificationToken.expires_at >= datetime.now(timezone.utc),
        Customer.email_verified.is_(True),
    ).first() if payload.verification_token else None
    if not verified:
        raise HTTPException(status_code=403, detail="Verify your email again before submitting a complaint")
    new_ticket = Ticket(
        customer_id=payload.customer_id,
        subject=payload.subject,
        description=payload.description
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    event = TicketEvent(ticket_id=new_ticket.id, event_type=TicketEventType.QUEUED)
    db.add(event)
    db.commit()
    publish_persisted_events([event])
    
    await redis.enqueue_job("process_ticket", new_ticket.id)
    return new_ticket


@router.get("/", response_model=List[TicketResponse])
def list_tickets(db: Session = Depends(get_db), user = Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    if user.role == UserRole.ADMIN:
        return annotate_recovery(db, db.query(Ticket).order_by(Ticket.created_at.desc()).all())
    else:
        # New complaints belong to the shared queue until someone owns them.
        # Closed tickets are shared history, consistent with /completed.
        return annotate_recovery(db, db.query(Ticket).filter(or_(
            Ticket.assigned_agent_id.is_(None),
            Ticket.assigned_agent_id == user.id,
            Ticket.status == TicketStatus.RESOLVED,
        )).order_by(Ticket.created_at.desc(), Ticket.id.desc()).all())

@router.get("/completed",response_model=List[TicketResponse])
def list_completed_tickets(db: Session = Depends(get_db),user=Depends(require_role(UserRole.ADMIN,UserRole.AGENT,UserRole.VIEWER))):
    return (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.RESOLVED)
        .order_by(Ticket.created_at.desc())
        .all()
    )

@router.post("/ticket", response_model=TicketEventCreate)
def create_ticket_event(payload: TicketEventCreate, db: Session = Depends(get_db), user = Depends(require_role(UserRole.ADMIN, UserRole.AGENT))):
    return record_ticket_event_service(db=db, ticket_id=payload.ticket_id, event_type=payload.event_type)



@router.get("/event", response_model=List[TicketEventResponse])
def list_ticket_events(db: Session = Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket_events = db.query(TicketEvent).order_by(TicketEvent.created_at.desc()).all()
    return ticket_events


@router.get("/resolution", response_model=List[TicketResolutionResponse])
def list_ticket_resolutions(db: Session = Depends(get_db),user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket_resolutions = db.query(TicketResolution).order_by(TicketResolution.created_at.desc()).all()
    return ticket_resolutions



@router.get("/{ticket_id}", response_model= TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user = Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return annotate_recovery(db, [ticket])[0]


@router.post("/{ticket_id}/retry", response_model=TicketResponse, status_code=202)
async def retry_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT)),
    redis: ArqRedis = Depends(get_redis_pool),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if user.role != UserRole.ADMIN and ticket.assigned_agent_id not in (None, user.id):
        raise HTTPException(status_code=403, detail="This ticket belongs to another agent")
    if not reserve_recovery(db, ticket_id):
        raise HTTPException(
            status_code=409,
            detail="A worker is still running this ticket. Please wait.",
        )
    db.refresh(ticket)
    annotate_recovery(db, [ticket])
    if not ticket.recovery_available:
        raise HTTPException(
            status_code=409,
            detail=("Retry is available for failed tickets or queued/processing tickets "
                    "with no activity for 10 minutes. Tickets waiting for review or "
                    "clarification should be handled in their respective pages."),
        )
    previous_status = ticket.status.value
    ticket.status = TicketStatus.QUEUED
    event = TicketEvent(
        ticket_id=ticket_id,
        event_type=TicketEventType.QUEUED,
        payload={"reason": "Recovery requested", "previous_status": previous_status,
                 "requested_by": user.id},
    )
    db.add(event)
    db.commit()  # Release the recovery lock before the worker can pick up its job.
    publish_persisted_events([event])
    try:
        await redis.enqueue_job(
            "process_ticket", ticket_id,
            _job_id=f"ticket-recovery:{ticket_id}:{event.id}",
        )
    except (RedisError, OSError, TimeoutError):
        # A legacy queued job may already have picked this ticket up. Preserve
        # its active work or saved outcome if the queue request was ambiguous.
        if reserve_recovery(db, ticket_id):
            db.refresh(ticket)
            if ticket.status in (TicketStatus.QUEUED, TicketStatus.PROCESSING):
                ticket.status = TicketStatus.FAILED
                failed = TicketEvent(
                    ticket_id=ticket_id, event_type=TicketEventType.FAILED,
                    payload={"message": "Recovery could not reach the queue. Check Redis and try again."},
                )
                db.add(failed)
                db.commit()
                publish_persisted_events([failed])
        raise HTTPException(
            status_code=503, detail="Could not queue recovery. Check Redis and try again."
        )
    db.refresh(ticket)
    return annotate_recovery(db, [ticket])[0]


@router.post("/{ticket_id}/clarify")
async def submit_clarification(ticket_id: int, payload: ClarificationAnswerRequest, user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT)), redis: ArqRedis = Depends(get_redis_pool)):
    await redis.enqueue_job("resume_ticket", ticket_id, payload.answer)
    return {"message" : "Submitted - the agent will resume shortly"}


@router.get("/{ticket_id}/event", response_model=List[TicketEventResponse])
def get_ticket_events(ticket_id: int, db: Session=Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket = db.query(Ticket).filter(Ticket.id==ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket_events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at.asc()).all()
    return ticket_events


@router.get("/{ticket_id}/resolution", response_model=TicketResolutionResponse)
def get_ticket_resolution(ticket_id: int, db: Session = Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket_resolution = db.query(TicketResolution).filter(TicketResolution.ticket_id == ticket_id).first()
    if not ticket_resolution:
        raise HTTPException(status_code=404, detail="Ticket resolution not found")
    return ticket_resolution


@router.get("/{ticket_id}/drafts", response_model=List[AgentDraftResponse])
def get_ticket_draft(ticket_id: int, db: Session=Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    drafts = db.query(AgentDraft).filter(AgentDraft.ticket_id == ticket_id).order_by(AgentDraft.created_at.desc()).all()
    return drafts


@router.post("/{ticket_id}/drafts/{draft_id}/review", response_model=AgentDraftResponse)
def review_draft(ticket_id: int, draft_id: int, payload: AgentDraftRequest, db: Session=Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT))):
    draft = (
        db.query(AgentDraft)
        .filter(AgentDraft.id == draft_id, AgentDraft.ticket_id == ticket_id).first()
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found for this ticket")
    if draft.status != DraftStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="This draft has already been reviewed")
    events = []
    if payload.action == "approve":
        draft.status = DraftStatus.APPROVED
        embedding = embed_text(draft.draft_text, input_type="search_document")
        db.add(TicketResolution(
                            ticket_id=ticket_id,
                            resolved_by=user.id,
                            resolution_text=draft.draft_text,
                            embedding=embedding,
                ))
        
    elif payload.action == "edit":
        if not payload.edited_text:
            raise HTTPException(status_code=400, detail="edited_text is required when action is 'edit")
        draft.status = DraftStatus.EDITED
        draft.draft_text = payload.edited_text
        embedding = embed_text(payload.edited_text, input_type="search_document")
        db.add(TicketResolution(
                    ticket_id=ticket_id,
                    resolved_by=user.id,
                    resolution_text=payload.edited_text,
                    embedding=embedding,
                ))
                
    if payload.action in ("approve", "edit"):
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        ticket.status = TicketStatus.RESOLVED
        events.append(TicketEvent(ticket_id=ticket_id,
                           event_type=TicketEventType.DRAFT_APPROVED if payload.action == 'approve' else TicketEventType.DRAFT_EDITED,
                           payload={"draft_id" : draft.id, "reviewed_by": user.id}))
        events.append(TicketEvent(ticket_id=ticket_id,
                           event_type=TicketEventType.RESOLVED,
                           payload={'draft_id': draft_id, "reviewed_by": user.id}))
        
    elif payload.action == "reject":
        draft.status = DraftStatus.REJECTED
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        ticket.status = TicketStatus.NEEDS_MANUAL_REVIEW
        events.append(TicketEvent(ticket_id=ticket_id,
                           event_type=TicketEventType.DRAFT_REJECTED,
                           payload={"draft_id": draft_id, "reviewed_by": user.id}))
        
    draft.reviewed_by = user.id
    draft.reviewed_at = datetime.now(timezone.utc)    
    db.add_all(events)
    db.commit()
    publish_persisted_events(events)
    db.refresh(draft)
    return draft


@router.post("/{ticket_id}/resolve-manually", response_model=TicketResponse)
def resolve_manually(ticket_id: int, payload: ManualResolutionRequest, db: Session = Depends(get_db), user = Depends(require_role(UserRole.ADMIN, UserRole.AGENT))):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    embedding = embed_text(payload.resolution_text, input_type="search_document")
    resolution = TicketResolution(
        ticket_id=ticket_id,
        resolved_by=user.id,
        resolution_text=payload.resolution_text,
        embedding=embedding,
    )
    events = []
    db.add(resolution)
    db.flush()
    ticket.status = TicketStatus.RESOLVED
    ticket.assigned_agent_id = user.id

    events.append(TicketEvent(ticket_id=ticket_id, event_type=TicketEventType.RESOLVED,
                        payload={ "resolution_id": resolution.id,
                                  "resolved_by": user.id,
                                  "resolution_text_preview": payload.resolution_text[:100],}))
    db.add_all(events)
    db.commit()
    publish_persisted_events(events)
    db.refresh(ticket)
    return ticket

