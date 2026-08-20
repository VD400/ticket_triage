from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime
from datetime import datetime, timezone

class EmailVerificationRequest(BaseModel):
    email: EmailStr




