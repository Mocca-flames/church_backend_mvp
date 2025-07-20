from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.schema.auth import TokenData
import os
from typing import Optional

SECRET_KEY = "your-super-secret-key-here" # Directly setting for debugging, should be loaded from .env
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

import logging

logging.basicConfig(level=logging.INFO)

def authenticate_user(db: Session, email: str, password: str):
    # MVP: Bypass password check for easy testing
    logging.info(f"Authenticating user: {email}")
    user = get_user(db, email)
    if not user or not verify_password(password, user.password_hash):
        logging.warning(f"Authentication failed for {email}: Incorrect password or user not found.")
        return None
    logging.info(f"User {email} authenticated successfully.")
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    return token_data
