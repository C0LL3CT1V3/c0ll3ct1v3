from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.accounts import router as accounts_router
from .api.auth import router as auth_router
from .database import engine
from .models import account, wallet, ledger, document, user

app = FastAPI(title="C0ll3CT1V3 Business Management System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts_router)
app.include_router(auth_router)

# Create database tables
from .database import Base
Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "C0ll3CT1V3 Business Management SystemAPI"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
