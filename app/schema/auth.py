from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

from app.schema.user import User

class TokenRefresh(BaseModel):
    refresh_token: str

class UserRegisterResponse(User):
    access_token: str
    token_type: str

class SignupStatus(BaseModel):
    """Response schema for signup status endpoint."""
    allowed: bool
    env_default: bool
    runtime_override: Optional[bool] = None
    message: str

class SignupToggle(BaseModel):
    """Request schema for toggling signup allowance."""
    enabled: bool

class SignupToggleResponse(BaseModel):
    """Response schema after toggling signup status."""
    allowed: bool
    message: str
    changed_by: str
