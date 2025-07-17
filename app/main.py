from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, contacts, communications, stats
from app.database import engine
from app.models import Base

app = FastAPI(
    title="Church Communication System",
    description="MVP for Fountain of Prayer Ministries",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(communications.router)
app.include_router(stats.router)

@app.get("/")
async def root():
    return {"message": "Church Communication System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
