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
