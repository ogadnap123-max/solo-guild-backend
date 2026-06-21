"""
schemas.py — Pydantic v2 request/response schemas for the Solo Leveling Guild API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., max_length=64)
    email: str = Field(..., max_length=128)
    hunter_rank: str = Field("E", max_length=32)
    hunter_class: str = Field("Fighter", max_length=64)
    level: int = Field(1, ge=1)
    total_xp: int = Field(0, ge=0)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    hunter_rank: str
    hunter_class: str
    level: int
    total_xp: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Guild schemas
# ---------------------------------------------------------------------------

class GuildCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    emblem: str = Field("⚔️", max_length=8)
    guild_rank: str = Field("Bronze Guild", max_length=64)
    max_members: int = Field(50, ge=1)


class GuildOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    emblem: str
    guild_rank: str
    max_members: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GuildMember schemas
# ---------------------------------------------------------------------------

class JoinGuildRequest(BaseModel):
    user_id: int
    guild_id: int
    role: str = Field("Member", max_length=32)


class GuildMemberOut(BaseModel):
    id: int
    user_id: int
    guild_id: int
    role: str
    joined_at: Optional[datetime] = None
    user: UserOut
    guild: GuildOut

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Guild member list response
# ---------------------------------------------------------------------------

class MemberEntry(BaseModel):
    user_id: int
    username: str
    hunter_rank: str
    hunter_class: str
    level: int
    role: str
    joined_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GuildMembersResponse(BaseModel):
    guild_id: int
    guild_name: str
    total_members: int
    members: list[MemberEntry]


# ---------------------------------------------------------------------------
# Rankings schemas
# ---------------------------------------------------------------------------

class GuildRankEntry(BaseModel):
    rank: int
    guild_id: int
    guild_name: str
    guild_rank: str
    emblem: str
    total_members: int
    avg_level: float


class RankingsResponse(BaseModel):
    total_guilds: int
    rankings: list[GuildRankEntry]
