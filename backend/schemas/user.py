from pydantic import BaseModel, EmailStr, ConfigDict
from models.user import UserRole

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str


