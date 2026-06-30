"""
routers/admin.py — Protected admin API for viewing/editing the database directly.

Auth model: HTTP Basic Auth, re-verified against the `users` table on every
single call (no session/token). The caller's username must belong to a user
with is_admin=True and the password must match that user's password_hash.

This intentionally re-checks credentials per-request rather than issuing a
token, per project decision — simplest mental model, no token to leak/expire,
at the cost of sending credentials on every call (mitigated by HTTPS, which
Railway provides by default on its public domains).
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_security = HTTPBasic()


def verify_admin(
    credentials: HTTPBasicCredentials = Depends(_security),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency that re-verifies username+password on every admin call and
    confirms the account has is_admin=True. Raises 401 on any failure —
    deliberately the same error for "no such user" and "wrong password" and
    "not an admin" so the response can't be used to enumerate valid usernames.
    """
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials.",
        headers={"WWW-Authenticate": "Basic"},
    )
    if not user or not _pwd_context.verify(credentials.password, user.password_hash):
        raise unauthorized
    if not user.is_admin:
        raise unauthorized
    return user


# ─────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────

class AdminUserSummary(BaseModel):
    id: int
    username: str
    email: str
    hunter_rank: str
    hunter_class: str
    level: int
    total_xp: int
    is_admin: bool
    profile_updated_at: float

    model_config = {"from_attributes": True}


class AdminUserDetail(AdminUserSummary):
    player_profile: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    total: int
    users: List[AdminUserSummary]


class AdminUserUpdate(BaseModel):
    """
    All fields optional — only the ones provided are changed.
    player_profile is the full game-state JSON blob; sending it here
    overwrites the entire cloud save for that user, same as the
    PUT /users/{id}/profile route does.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    hunter_rank: Optional[str] = None
    hunter_class: Optional[str] = None
    level: Optional[int] = None
    total_xp: Optional[int] = None
    is_admin: Optional[bool] = None
    player_profile: Optional[Dict[str, Any]] = None
    new_password: Optional[str] = None  # set to reset the user's password


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(verify_admin),
):
    """List all hunters (summary only — no player_profile blob, keeps it light)."""
    total = db.query(models.User).count()
    users = db.query(models.User).order_by(models.User.id).offset(skip).limit(limit).all()
    return AdminUserListResponse(total=total, users=users)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(verify_admin),
):
    """Full detail for one hunter, including their entire cloud-save JSON."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} not found.")
    return user


@router.put("/users/{user_id}", response_model=AdminUserDetail)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(verify_admin),
):
    """
    Patch any subset of a hunter's row, including their raw player_profile
    JSON. Only fields explicitly included in the request body are touched.
    """
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} not found.")

    data = payload.model_dump(exclude_unset=True)

    if "username" in data and data["username"] != user.username:
        clash = db.query(models.User).filter(models.User.username == data["username"]).first()
        if clash:
            raise HTTPException(status_code=409, detail=f"Username '{data['username']}' is taken.")

    if "email" in data and data["email"] != user.email:
        clash = db.query(models.User).filter(models.User.email == data["email"]).first()
        if clash:
            raise HTTPException(status_code=409, detail=f"Email '{data['email']}' is already registered.")

    new_password = data.pop("new_password", None)
    if new_password:
        user.password_hash = _pwd_context.hash(new_password)

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(verify_admin),
):
    """Delete a hunter account and their guild membership (cascades)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own admin account through this route.")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Hunter id={user_id} not found.")
    db.delete(user)
    db.commit()
    return None
