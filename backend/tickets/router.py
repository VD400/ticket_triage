from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Ticket
from models.user import UserRole
from schemas.ticket import TicketCreateRequest, TicketResponse
from models.ticket_event import TicketEvent
from schemas.ticket_event import TicketEventResponse
from models.ticket_resolution import TicketResolution
from schemas.ticket_resolution import TicketResolutionResponse
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db)):
    new_ticket = Ticket(
        customer_id=payload.customer_id,
        subject=payload.subject,
        description=payload.description
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    return new_ticket


@router.get("/", response_model=List[TicketResponse])
def list_tickets(db: Session = Depends(get_db), user = Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()



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
    return ticket


@router.get("/{ticket_id}/event", response_model=TicketEventResponse)
def get_ticket_event(ticket_id: int, db: Session=Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket_event = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).first()
    if not ticket_event:
        raise HTTPException(status_code=404, detail="Ticket event not present")
    return ticket_event


@router.get("/{ticket_id}/resolution", response_model=TicketResolutionResponse)
def get_ticket_resolution(ticket_id: int, db: Session = Depends(get_db), user=Depends(require_role(UserRole.ADMIN, UserRole.AGENT, UserRole.VIEWER))):
    ticket_resolution = db.query(TicketResolution).filter(TicketResolution.ticket_id == ticket_id).first()
    if not ticket_resolution:
        raise HTTPException(status_code=404, detail="Ticket resolution not found")
    return ticket_resolution





