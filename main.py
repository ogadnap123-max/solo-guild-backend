"""
main.py — FastAPI entry point for the Solo Leveling Guild API.

Run locally:
    uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import database as db_module
from database import get_db
from schemas import UserCreate, UserOut, GuildCreate, GuildOut
from routers.guilds import router as guild_router

# ---------------------------------------------------------------------------
# Users router
# ---------------------------------------------------------------------------

users_router = APIRouter(prefix="/users", tags=["🗡️ Hunters"])


@users_router.post("/", response_model=UserOut, status_code=201, summary="Register a hunter")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is taken.")
    user = models.User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
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
# App lifecycle — always uses db_module.engine so tests can swap it
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use the engine from the module directly (tests patch db_module.engine)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(guilds_seed_router)  # POST /guilds/ — must come BEFORE guild_router
app.include_router(guild_router)        # POST /guilds/join  GET /guilds/{id}/members  GET /guilds/rankings


@app.get("/", tags=["System"], summary="Health check")
def root():
    return {
        "status": "SYSTEM ONLINE",
        "message": "I alone level up.",
        "docs": "/docs",
    }
