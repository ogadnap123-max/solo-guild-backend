"""
main.py — FastAPI entry point for the Solo Leveling Guild API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from passlib.context import CryptContext
=======
from fastapi.middleware.trustedhost import TrustedHostMiddleware
>>>>>>> afc1b29b1cf068c5111c89cc7f41f1f6cea44e0b
from sqlalchemy.orm import Session

import models
import database as db_module
from database import get_db
from schemas import UserCreate, UserLogin, UserOut, GuildCreate, GuildOut
from routers.guilds import router as guild_router

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Users router
# ---------------------------------------------------------------------------

users_router = APIRouter(prefix="/users", tags=["🗡️ Hunters"])


@users_router.post("/", response_model=UserOut, status_code=201, summary="Register a hunter")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is taken.")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail=f"Email '{payload.email}' is already registered.")

    data = payload.model_dump()
    plain_password = data.pop("password")           # remove plain text
    data["password_hash"] = hash_password(plain_password)

    user = models.User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@users_router.post("/login", response_model=UserOut, summary="Login a hunter")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.username == payload.username
    ).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return user


@users_router.get("/{user_id}", response_model=UserOut, summary="Get a hunter by id")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} not found.")
    return user


# ---------------------------------------------------------------------------
# Guild seed router (POST /guilds/)
# ---------------------------------------------------------------------------

guilds_seed_router = APIRouter(prefix="/guilds", tags=["⚔️ Guilds"])


@guilds_seed_router.post("/", response_model=GuildOut, status_code=201, summary="Create a guild")
def create_guild(payload: GuildCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Guild).filter(models.Guild.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Guild name '{payload.name}' is taken.")
    guild = models.Guild(**payload.model_dump())
    db.add(guild)
    db.commit()
    db.refresh(guild)
    return guild


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=db_module.engine)
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="⚔️ Solo Leveling — Guild System API",
    description="Backend for managing hunter guilds.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all hosts — required for Railway's proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(guilds_seed_router)
app.include_router(guild_router)


@app.get("/", tags=["System"], summary="Health check")
def root():
    return {
        "status": "SYSTEM ONLINE",
        "message": "I alone level up.",
        "docs": "/docs",
    }
