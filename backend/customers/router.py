from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from schemas.customer import EmailVerificationRequest
from database import get_db
from models import Customer, VerificationToken
from .email_verification import generate_verification_token

router = APIRouter(prefix="/customers", tags=["customers"])

@router.post("/request-verification")
def request_verification(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if not customer:
        customer = Customer(
            name=payload.email.split("@")[0][:50],
            email=payload.email,
            email_verified=False
        )
        db.add(Customer)
        db.commit()
        db.refesh(customer)
    token_str = generate_verification_token()
    token = VerificationToken(
        customer_id=customer.id,
        token=token_str,
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=30)
    )
    db.add(token)
    db.commit()
    print(f"[MOCK EMAIL] Verification link: http://localhost:8000/customers/verify-email?token={token_str}")
    return {"message": "Verification email sent"}

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    token_row = db.query(VerificationToken).filter(VerificationToken.token == token).first()
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if token_row.used:
        raise HTTPException(status_code=400, detail="This token has already been used")
    if token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This token has expired, please generate a new token")
    
    customer = db.query(Customer).filter(Customer.id == token_row.customer_id).first()
    customer.email_verified = True
    token_row.used = True
    db.commit()

    return {"message" : "Email verified successfully", "customer_id" : customer.id}

