from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_token, get_user
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token, credentials_exception)
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_contact_manager(current_user: User = Depends(get_current_active_user)):
    # Role restrictions removed as per user request.
    # Any active user can now manage contacts.
    return current_user

def get_current_super_admin(current_user: User = Depends(get_current_active_user)):
    """Verify the current user has super_admin role."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Super admin access required."
        )
    return current_user

def get_current_admin(current_user: User = Depends(get_current_active_user)):
    """Verify the current user has an admin role (super_admin or it_admin)."""
    if current_user.role not in ("super_admin", "it_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin access required."
        )
    return current_user

def require_signups_enabled():
    """Dependency that raises an exception if signups are disabled."""
    from app.config import are_signups_allowed
    if not are_signups_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New user registrations are currently disabled. Please contact an administrator."
        )
