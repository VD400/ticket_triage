from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from models.user import UserRole
from .jwtToken import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

http_bearer = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    print("Payload: ", payload)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user

def require_role(*allowed_roles: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker