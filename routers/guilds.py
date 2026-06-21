"""
routers/guilds.py — Guild action endpoints for the Solo Leveling Guild API.

Endpoints
---------
POST /guilds/join               — Hunter joins a guild
GET  /guilds/{guild_id}/members — View roster (sorted by level desc, filterable by role)
GET  /guilds/rankings           — Global leaderboard ranked by avg member level
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import get_db
from schemas import (
    JoinGuildRequest,
    GuildMemberOut,
    GuildMembersResponse,
    MemberEntry,
    RankingsResponse,
    GuildRankEntry,
)

router = APIRouter(prefix="/guilds", tags=["⚔️ Guilds"])


# ---------------------------------------------------------------------------
# POST /guilds/join
# ---------------------------------------------------------------------------

@router.post("/join", response_model=GuildMemberOut, status_code=201, summary="Join a guild")
def join_guild(payload: JoinGuildRequest, db: Session = Depends(get_db)):
    # Validate user exists
    user = db.get(models.User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={payload.user_id} not found.")

    # Validate guild exists
    guild = db.get(models.Guild, payload.guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail=f"Guild id={payload.guild_id} not found.")

    # Check user is not already in a guild
    existing = (
        db.query(models.GuildMember)
        .filter(models.GuildMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Hunter id={payload.user_id} is already a member of a guild.")

    # Check guild capacity
    current_count = (
        db.query(func.count(models.GuildMember.id))
        .filter(models.GuildMember.guild_id == payload.guild_id)
        .scalar()
    )
    if current_count >= guild.max_members:
        raise HTTPException(
            status_code=409,
            detail=f"Guild '{guild.name}' is at full capacity ({guild.max_members} members).",
        )

    member = models.GuildMember(
        user_id=payload.user_id,
        guild_id=payload.guild_id,
        role=payload.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


# ---------------------------------------------------------------------------
# GET /guilds/{guild_id}/members
# ---------------------------------------------------------------------------

@router.get(
    "/{guild_id}/members",
    response_model=GuildMembersResponse,
    summary="View guild roster",
)
def get_guild_members(
    guild_id: int,
    role: str | None = Query(None, description="Filter by role (Member / Officer / Master)"),
    db: Session = Depends(get_db),
):
    guild = db.get(models.Guild, guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail=f"Guild id={guild_id} not found.")

    query = (
        db.query(models.GuildMember)
        .filter(models.GuildMember.guild_id == guild_id)
        .join(models.User, models.GuildMember.user_id == models.User.id)
        .order_by(models.User.level.desc())
    )

    if role:
        query = query.filter(models.GuildMember.role == role)

    memberships = query.all()

    members_out = [
        MemberEntry(
            user_id=m.user_id,
            username=m.user.username,
            hunter_rank=m.user.hunter_rank,
            hunter_class=m.user.hunter_class,
            level=m.user.level,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]

    return GuildMembersResponse(
        guild_id=guild_id,
        guild_name=guild.name,
        total_members=len(members_out),
        members=members_out,
    )


# ---------------------------------------------------------------------------
# GET /guilds/rankings
# ---------------------------------------------------------------------------

@router.get("/rankings", response_model=RankingsResponse, summary="Global guild leaderboard")
def get_rankings(
    limit: int = Query(20, ge=1, le=100, description="Max number of guilds to return"),
    db: Session = Depends(get_db),
):
    # Subquery: avg level per guild (0 if no members)
    avg_subq = (
        db.query(
            models.GuildMember.guild_id,
            func.avg(models.User.level).label("avg_level"),
            func.count(models.GuildMember.id).label("member_count"),
        )
        .join(models.User, models.GuildMember.user_id == models.User.id)
        .group_by(models.GuildMember.guild_id)
        .subquery()
    )

    # Left join guilds to subquery so empty guilds appear with avg=0
    rows = (
        db.query(
            models.Guild,
            func.coalesce(avg_subq.c.avg_level, 0.0).label("avg_level"),
            func.coalesce(avg_subq.c.member_count, 0).label("member_count"),
        )
        .outerjoin(avg_subq, models.Guild.id == avg_subq.c.guild_id)
        .order_by(func.coalesce(avg_subq.c.avg_level, 0.0).desc())
        .limit(limit)
        .all()
    )

    total_guilds = db.query(func.count(models.Guild.id)).scalar()

    rankings = [
        GuildRankEntry(
            rank=idx + 1,
            guild_id=guild.id,
            guild_name=guild.name,
            guild_rank=guild.guild_rank,
            emblem=guild.emblem,
            total_members=member_count,
            avg_level=round(float(avg_level), 2),
        )
        for idx, (guild, avg_level, member_count) in enumerate(rows)
    ]

    return RankingsResponse(total_guilds=total_guilds, rankings=rankings)


# ---------------------------------------------------------------------------
# DELETE /guilds/leave — remove a hunter from their current guild
# ---------------------------------------------------------------------------

@router.delete("/leave", summary="Leave current guild")
def leave_guild(user_id: int, db: Session = Depends(get_db)):
    """Pass user_id as a query param: DELETE /guilds/leave?user_id=3"""
    membership = (
        db.query(models.GuildMember)
        .filter(models.GuildMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} is not in any guild.")
    db.delete(membership)
    db.commit()
    return {"ok": True, "message": f"Hunter id={user_id} has left the guild."}
