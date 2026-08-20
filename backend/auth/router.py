from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from schemas.user import RegisterRequest, UserResponse, LoginResponse, LoginRequest
from database import get_db
from models import User
from .security import hash_password, verify_password  
from .jwtToken import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

    
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        ((User.email == payload.email) | (User.username == payload.username))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )   
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username==payload.username)
    ).first()
    if not existing:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    else:
        if verify_password(payload.password, existing.hashed_password):
            token = create_access_token({"sub":str(existing.id), "role": existing.role.value})
            return {"access_token": token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=400, detail="Invalid username or password")
