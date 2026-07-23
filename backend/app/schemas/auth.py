from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
import uuid

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    is_gmail_connected: bool = False
    
    class Config:
        from_attributes = True

class GoogleOAuthState(BaseModel):
    state: str
    redirect_url: str
