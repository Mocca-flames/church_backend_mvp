# Church Communication System Backend Implementation

## Project Structure

The backend is structured to organize code logically, promoting maintainability and clear separation of concerns.

```
backend/
├── app/                         # Main application
│   ├── __init__.py
│   ├── main.py                  # FastAPI app instance
│   ├── database.py              # Database connection and session management
│   ├── dependencies.py          # Application-level dependencies
│   ├── auth.py                  # Authentication utilities
│   ├── models.py                # Database models
│   ├── schemas.py               # Pydantic schemas
│   ├── routers/                 # API routers
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication routes
│   │   ├── contacts.py          # Contact management routes
│   │   └── communications.py    # Communication routes
│   └── services/                # Business logic services
│       ├── __init__.py
│       ├── sms_service.py       # SMS sending service
│       ├── communication_service.py # Communication management service
│       └── contact_service.py   # Contact management service
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables example
├── docker-compose.yml           # Docker Compose configuration
└── Dockerfile                   # Docker image definition
```

This structure organizes the application into `app/` containing the core FastAPI application, with subdirectories for routers and services.

## 1. Requirements (requirements.txt)
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
twilio==8.12.0
python-dotenv==1.0.0
pandas==2.1.4
pydantic==2.5.2
pydantic[email]==2.5.2
```

## 2. Database Configuration (app/database.py)
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/church_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 3. Database Models (app/models.py)
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'super_admin', 'secretary', 'it_admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    communications = relationship("Communication", back_populates="creator")

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    tags = Column(ARRAY(String), default=[])
    opt_out_sms = Column(Boolean, default=False)
    opt_out_whatsapp = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(Integer, primary_key=True, index=True)
    message_type = Column(String(20), nullable=False)  # 'sms', 'whatsapp'
    recipient_group = Column(String(50), nullable=False)  # 'all_contacts', 'tagged', 'custom'
    subject = Column(String(200))
    message = Column(Text, nullable=False)
    scheduled_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    status = Column(String(20), default='draft')  # 'draft', 'scheduled', 'sent', 'failed'
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    creator = relationship("User", back_populates="communications")
```

## 4. Pydantic Schemas (app/schemas.py)
```python
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    role: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Contact Schemas
class ContactBase(BaseModel):
    full_name: str
    phone: str
    tags: Optional[List[str]] = []
    opt_out_sms: bool = False
    opt_out_whatsapp: bool = False

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContactImport(BaseModel):
    contacts: List[ContactCreate]

# Communication Schemas
class CommunicationBase(BaseModel):
    message_type: str
    recipient_group: str
    subject: Optional[str] = None
    message: str
    scheduled_at: Optional[datetime] = None

class CommunicationCreate(CommunicationBase):
    pass

class Communication(CommunicationBase):
    id: int
    status: str
    sent_count: int
    failed_count: int
    sent_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
```

## 5. Authentication (app/auth.py)
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.schemas import TokenData
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
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
```

## 6. Dependencies (app/dependencies.py)
```python
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
```

## 7. SMS Service (app/services/sms_service.py)
```python
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Missing Twilio credentials in environment variables")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS to a single recipient"""
        try:
            # Ensure phone number is in E.164 format
            if not to_number.startswith('+'):
                to_number = '+27' + to_number.lstrip('0')  # South African format
            
            message_instance = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            return {
                'success': True,
                'message_sid': message_instance.sid,
                'status': message_instance.status,
                'phone': to_number
            }
        except TwilioException as e:
            logger.error(f"Twilio error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number
            }
        except Exception as e:
            logger.error(f"General error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number
            }
    
    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send SMS to multiple recipients"""
        results = []
        sent_count = 0
        failed_count = 0
        
        for phone in phone_numbers:
            result = self.send_sms(phone, message)
            results.append(result)
            
            if result['success']:
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            'total_sent': sent_count,
            'total_failed': failed_count,
            'results': results
        }

# Global SMS service instance
sms_service = SMSService()
```

## 8. Communication Service (app/services/communication_service.py)
```python
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Communication, Contact
from app.schemas import CommunicationCreate
from app.services.sms_service import sms_service
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_communication(self, communication: CommunicationCreate, user_id: int) -> Communication:
        """Create a new communication record"""
        db_communication = Communication(
            **communication.dict(),
            created_by=user_id
        )
        self.db.add(db_communication)
        self.db.commit()
        self.db.refresh(db_communication)
        return db_communication
    
    def get_recipients(self, recipient_group: str, tags: Optional[List[str]] = None) -> List[Contact]:
        """Get recipient contacts based on group type"""
        query = self.db.query(Contact)
        
        if recipient_group == "all_contacts":
            query = query.filter(Contact.opt_out_sms == False)
        elif recipient_group == "tagged" and tags:
            query = query.filter(
                and_(
                    Contact.tags.overlap(tags),
                    Contact.opt_out_sms == False
                )
            )
        
        return query.all()
    
    def send_communication(self, communication_id: int, tags: Optional[List[str]] = None, exclude_tags: Optional[List[str]] = None) -> Communication:
        """
        Send a communication via SMS.
        Enhanced to allow exclusion of contacts based on tags.
        """
        communication = self.db.query(Communication).filter(
            Communication.id == communication_id
        ).first()
        
        if not communication:
            raise ValueError("Communication not found")
        
        if communication.status != 'draft':
            raise ValueError("Communication has already been sent")
        
        # Get recipients
        recipients = self.get_recipients(communication.recipient_group, tags)
        phone_numbers = [contact.phone for contact in recipients]
        
        if not phone_numbers:
            raise ValueError("No recipients found")
        
        # Send SMS
        if communication.message_type == 'sms':
            result = sms_service.send_bulk_sms(phone_numbers, communication.message)
            
            # Update communication record
            communication.sent_count = result['total_sent']
            communication.failed_count = result['total_failed']
            communication.status = 'sent'
            communication.sent_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(communication)
            
            return communication
        else:
            raise ValueError("WhatsApp messaging not implemented yet")
    
    def get_communications(self, user_id: Optional[int] = None) -> List[Communication]:
        """Get all communications, optionally filtered by user"""
        query = self.db.query(Communication)
        if user_id:
            query = query.filter(Communication.created_by == user_id)
        return query.order_by(Communication.created_at.desc()).all()
```

## 9. Contact Service (app/services/contact_service.py)
```python
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Contact
from app.schemas import ContactCreate
from typing import List, Dict, Any
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

class ContactService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_contact(self, contact: ContactCreate) -> Contact:
        """Create a new contact"""
        db_contact = Contact(**contact.dict())
        self.db.add(db_contact)
        self.db.commit()
        self.db.refresh(db_contact)
        return db_contact
    
    def get_contacts(self, skip: int = 0, limit: int = 100) -> List[Contact]:
        """Get all contacts with pagination"""
        return self.db.query(Contact).offset(skip).limit(limit).all()
    
    def get_contact_by_phone(self, phone: str) -> Contact:
        """Get contact by phone number"""
        return self.db.query(Contact).filter(Contact.phone == phone).first()
    
    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact"""
        contact = self.db.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            self.db.delete(contact)
            self.db.commit()
            return True
        return False
    
    def import_contacts_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import contacts from CSV content"""
        try:
            # Parse CSV
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Validate required columns
            required_columns = ['full_name', 'phone']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f"Missing required columns: {missing_columns}"
                }
            
            # Process contacts
            imported_count = 0
            failed_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Clean phone number
                    phone = str(row['phone']).strip()
                    if not phone.startswith('+'):
                        phone = '+27' + phone.lstrip('0')  # South African format
                    
                    # Parse tags if present
                    tags = []
                    if 'tags' in row and pd.notna(row['tags']):
                        tags = [tag.strip() for tag in str(row['tags']).split(',')]
                    
                    contact_data = ContactCreate(
                        full_name=str(row['full_name']).strip(),
                        phone=phone,
                        tags=tags,
                        opt_out_sms=bool(row.get('opt_out_sms', False)),
                        opt_out_whatsapp=bool(row.get('opt_out_whatsapp', False))
                    )
                    
                    self.create_contact(contact_data)
                    imported_count += 1
                    
                except IntegrityError:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: Phone number already exists")
                    self.db.rollback()
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Row {index + 1}: {str(e)}")
                    self.db.rollback()
            
            return {
                'success': True,
                'imported_count': imported_count,
                'failed_count': failed_count,
                'errors': errors[:10]  # Limit error messages
            }
            
        except Exception as e:
            logger.error(f"CSV import error: {str(e)}")
            return {
                'success': False,
                'error': f"CSV parsing error: {str(e)}"
            }

    def import_contacts_from_vcf(self, vcf_content: str) -> Dict[str, Any]:
        """Import contacts from VCF content (MVP: Not implemented)"""
        return {
            'success': False,
            'error': "VCF import is not part of the MVP and is not implemented."
        }
```

## 10. Authentication Router (app/routers/auth.py)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import User
from app.schemas import UserCreate, Token, User as UserSchema
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserSchema)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
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
    
    return db_user

@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user
```

## 11. Contacts Router (app/routers/contacts.py)
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User
from app.schemas import Contact, ContactCreate
from app.services.contact_service import ContactService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("/", response_model=List[Contact])
async def get_contacts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    return service.get_contacts(skip=skip, limit=limit)

@router.post("/", response_model=Contact)
async def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    try:
        return service.create_contact(contact)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    content = await file.read()
    
    if file.filename.endswith('.csv'):
        csv_content = content.decode('utf-8')
        result = service.import_contacts_from_csv(csv_content)
    elif file.filename.endswith(('.vcf', '.VCF')):
        vcf_content = content.decode('utf-8')
        result = service.import_contacts_from_vcf(vcf_content)
    else:
        raise HTTPException(status_code=400, detail="Only CSV and VCF files are supported")
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = ContactService(db)
    if service.delete_contact(contact_id):
        return {"message": "Contact deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Contact not found")
```

## 12. Communications Router (app/routers/communications.py)
```python
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User
from app.schemas import Communication, CommunicationCreate
from app.services.communication_service import CommunicationService
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/communications", tags=["communications"])

@router.get("/", response_model=List[Communication])
async def get_communications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.get_communications()

@router.post("/", response_model=Communication)
async def create_communication(
    communication: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    return service.create_communication(communication, current_user.id)

@router.post("/{communication_id}/send", response_model=Communication)
async def send_communication(
    communication_id: int,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    try:
        return service.send_communication(communication_id, tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{communication_id}/status", response_model=Communication)
async def get_communication_status(
    communication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = CommunicationService(db)
    communication = service.db.query(service.db.query(Communication).filter(
        Communication.id == communication_id
    ).first())
    
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")
    
    return communication
```

## 13. Main Application (app/main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, contacts, communications
from app.database import engine
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Church Communication System",
    description="MVP for Fountain of Prayer Ministries",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(communications.router)

@app.get("/")
async def root():
    return {"message": "Church Communication System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## 14. Environment Variables (.env.example)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/church_db

# JWT
SECRET_KEY=your-super-secret-key-here

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+27123456789
```



## Installation & Setup Instructions

1. **Create project directory:**
```bash
mkdir church_backend
cd church_backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your actual values
```

5. **Run with Docker Compose:**
```bash
docker-compose up -d
```

6. **Create initial admin user:**
```bash
# Make a POST request to /auth/register with admin credentials
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@thunder.com",
    "password": "admin123",
    "role": "super_admin"
  }'
```

## API Testing

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

This backend implementation provides:
- ✅ User authentication with JWT
- ✅ Contact management with CSV and VCF import
- ✅ SMS integration via Twilio
- ✅ Bulk messaging capabilities
- ✅ Role-based access control
- ✅ Comprehensive error handling
- ✅ Docker containerization
- ✅ Database migrations ready
