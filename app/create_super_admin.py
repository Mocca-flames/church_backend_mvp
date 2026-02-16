import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash
from dotenv import load_dotenv

load_dotenv()

def create_tables():
    Base.metadata.create_all(bind=engine)

def create_super_admin_user():
    db: Session = SessionLocal()
    try:
        # Tables should be created by Alembic migrations, not by create_tables()
        # create_tables() 
        
        email = os.getenv("SUPER_ADMIN_EMAIL", "admin@thunder")
        password = os.getenv("SUPER_ADMIN_PASSWORD", "admin@1234")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Super admin user '{email}' already exists. Skipping creation.")
            return

        hashed_password = get_password_hash(password)
        
        super_admin = User(
            email=email,
            password_hash=hashed_password,
            role="super_admin",
            is_active=True
        )
        
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        print(f"Super admin user '{email}' created successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error creating super admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin_user()
