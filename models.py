"""
models.py — SQLAlchemy ORM models for the Solo Leveling Guild system.

Tables
------
users        — hunters/players (rank, level, class, XP)
guilds       — named guilds with a rank emblem and description
guild_members — join table that links a user to exactly one guild
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


# ---------------------------------------------------------------------------
# Hunter ranks — mirrors the Solo Leveling rank system
# ---------------------------------------------------------------------------
HUNTER_RANKS = ("E", "D", "C", "B", "A", "S", "National-Level", "Monarch")

GUILD_RANKS = (
    "Bronze Guild",
    "Silver Guild",
    "Gold Guild",
    "Platinum Guild",
    "Diamond Guild",
    "S-Rank Guild",
    "Shadow Monarch Guild",
)


class User(Base):
    """A registered hunter (player account)."""

    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(64), unique=True, nullable=False, index=True)
    email      = Column(String(128), unique=True, nullable=False)

    # RPG stats
    hunter_rank  = Column(String(32), nullable=False, default="E")   # E → Monarch
    hunter_class = Column(String(64), nullable=False, default="Fighter")
    level        = Column(Integer, nullable=False, default=1)
    total_xp     = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship back to membership (a user can only be in one guild)
    membership = relationship(
        "GuildMember", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("level >= 1", name="ck_user_level_positive"),
        CheckConstraint("total_xp >= 0", name="ck_user_xp_non_negative"),
    )

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r} rank={self.hunter_rank}>"


class Guild(Base):
    """A guild that hunters can join."""

    __tablename__ = "guilds"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    emblem      = Column(String(8), nullable=False, default="⚔️")   # emoji emblem
    guild_rank  = Column(String(64), nullable=False, default="Bronze Guild")
    max_members = Column(Integer, nullable=False, default=50)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to membership records
    members = relationship(
        "GuildMember", back_populates="guild", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("max_members >= 1", name="ck_guild_max_members_positive"),
    )

    def __repr__(self):
        return f"<Guild id={self.id} name={self.name!r} rank={self.guild_rank}>"


class GuildMember(Base):
    """
    Association table — one row per hunter-in-guild.
    A hunter can only belong to ONE guild at a time (UniqueConstraint on user_id).
    """

    __tablename__ = "guild_members"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    guild_id = Column(Integer, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False)
    role     = Column(String(32), nullable=False, default="Member")  # Member | Officer | Master
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user  = relationship("User",  back_populates="membership")
    guild = relationship("Guild", back_populates="members")

    __table_args__ = (
        # A hunter can only be in one guild
        UniqueConstraint("user_id", name="uq_guild_member_user"),
    )

    def __repr__(self):
        return f"<GuildMember user_id={self.user_id} guild_id={self.guild_id} role={self.role}>"
