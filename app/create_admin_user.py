import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"

def create_tables():
    Base.metadata.create_all(bind=engine)

def create_admin_user():
    db: Session = SessionLocal()
    try:
        # Tables should be created by Alembic migrations, not by create_tables()
        # create_tables()

        email = os.getenv("ADMIN_EMAIL", LOGIN_EMAIL)
        password = os.getenv("ADMIN_PASSWORD", LOGIN_PASSWORD)

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Admin user '{email}' already exists. Skipping creation.")
            return

        hashed_password = get_password_hash(password)

        admin_user = User(
            email=email,
            password_hash=hashed_password,
            role="it_admin",
            is_active=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Admin user '{email}' created successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()