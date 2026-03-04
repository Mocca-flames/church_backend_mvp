import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import authenticate_user, create_access_token, create_refresh_token, get_password_hash, verify_token
from app.models import User
from app.schema.user import UserCreate, User as UserSchema, UserLogin
from app.dependencies import get_current_active_user, get_current_admin, require_signups_enabled
from app.schema.auth import SignupToggleResponse, Token, TokenRefresh, TokenData, UserRegisterResponse, SignupStatus, SignupToggle
from app.config import are_signups_allowed, set_signups_allowed, get_signup_status

router = APIRouter(prefix="/auth", tags=["authentication"])

logging.basicConfig(level=logging.INFO)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logging.info(f"Attempting login for email: {form_data.username}")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logging.warning(f"Authentication failed for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.email}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    logging.info(f"Login successful for email: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

@router.post("/register", response_model=UserRegisterResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    logging.info(f"Attempting registration for email: {user.email}")
    
    # Check if signups are allowed
    if not are_signups_allowed():
        logging.warning(f"Registration rejected: Signups are currently disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New user registrations are currently disabled. Please contact an administrator."
        )
    
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        logging.warning(f"Registration failed: Email already registered: {user.email}")
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(
        data={"sub": db_user.email}
    )
    
    logging.info(f"Registration successful for email: {user.email}")
    return {**db_user.__dict__, "access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(token_refresh: TokenRefresh, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token_refresh.refresh_token, credentials_exception)
    
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    
    access_token = create_access_token(
        data={"sub": user.email}
    )
    logging.info(f"Token refreshed for email: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/settings/signups", response_model=SignupStatus)
async def get_signup_settings(current_user: User = Depends(get_current_active_user)):
    """Get the current signup registration status. Any authenticated user can view this."""
    status_info = get_signup_status()
    allowed = status_info["allowed"]
    message = "New user registrations are currently enabled." if allowed else "New user registrations are currently disabled."
    
    return SignupStatus(
        allowed=allowed,
        env_default=status_info["env_default"],
        runtime_override=status_info["runtime_override"],
        message=message
    )

@router.post("/settings/signups", response_model=SignupToggleResponse)
async def toggle_signup_settings(
    toggle: SignupToggle,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Enable or disable new user registrations.
    Only super_admin and it_admin users can modify this setting.
    This is a runtime change that doesn't persist across server restarts.
    To make it permanent, update the ALLOW_SIGNUPS environment variable.
    """
    previous_status = are_signups_allowed()
    set_signups_allowed(toggle.enabled)
    new_status = are_signups_allowed()
    
    action = "enabled" if new_status else "disabled"
    logging.info(f"Signups {action} by {current_user.email} (role: {current_user.role})")
    
    message = f"New user registrations have been {action}."
    if new_status != previous_status:
        message += f" Changed from {'enabled' if previous_status else 'disabled'}."
    else:
        message += " Status unchanged."
    
    return SignupToggleResponse(
        allowed=new_status,
        message=message,
        changed_by=current_user.email
    )
