"""
main.py — FastAPI entry point for the Solo Leveling Guild API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
import database as db_module
from database import get_db
from schemas import UserCreate, UserLogin, UserOut, GuildCreate, GuildOut
from routers.guilds import router as guild_router

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

users_router = APIRouter(prefix="/users", tags=["Hunters"])

@users_router.post("/", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is taken.")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail=f"Email '{payload.email}' is already registered.")
    data = payload.model_dump()
    plain_password = data.pop("password")
    data["password_hash"] = hash_password(plain_password)
    user = models.User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@users_router.post("/login", response_model=UserOut)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return user

@users_router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} not found.")
    return user

guilds_seed_router = APIRouter(prefix="/guilds", tags=["Guilds"])

@guilds_seed_router.post("/", response_model=GuildOut, status_code=201)
def create_guild(payload: GuildCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Guild).filter(models.Guild.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Guild name '{payload.name}' is taken.")
    guild = models.Guild(**payload.model_dump())
    db.add(guild)
    db.commit()
    db.refresh(guild)
    return guild

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL    = "admin@shadowsystem.local"

def seed_admin(db: Session) -> None:
    """Create or update the admin account on startup."""
    admin = db.query(models.User).filter(models.User.username == ADMIN_USERNAME).first()
    
    if admin:
        # Enforce these values every time the app starts
        admin.is_admin = True
        admin.hunter_rank = "S"
        admin.hunter_class = "Shadow Monarch"
        db.commit()
        db.refresh(admin)
    else:
        # Create only if it doesn't exist
        admin = models.User(
            username      = ADMIN_USERNAME,
            email         = ADMIN_EMAIL,
            password_hash = hash_password(ADMIN_PASSWORD),
            is_admin      = True,
            hunter_rank   = "S",
            hunter_class  = "Shadow Monarch",
            level         = 1,
            total_xp      = 0,
        )
        db.add(admin)
        db.commit()
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=db_module.engine)
    # Seed admin account (idempotent — safe to run on every restart)
    db = next(get_db())
    try:
        seed_admin(db)
    finally:
        db.close()
    yield

app = FastAPI(title="Solo Leveling Guild API", version="1.0.0", lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(users_router)
app.include_router(guilds_seed_router)
app.include_router(guild_router)

@app.get("/")
def root():
    return {"status": "SYSTEM ONLINE", "message": "I alone level up.", "docs": "/docs"}
