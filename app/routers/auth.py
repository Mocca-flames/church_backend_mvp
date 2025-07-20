import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import authenticate_user, create_access_token, create_refresh_token, get_password_hash, verify_token
from app.models import User
from app.schema.user import UserCreate, User as UserSchema, UserLogin
from app.dependencies import get_current_active_user
from app.schema.auth import Token, TokenRefresh, TokenData, UserRegisterResponse

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
