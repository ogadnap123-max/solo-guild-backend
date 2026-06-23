"""
models.py — SQLAlchemy ORM models for the Solo Leveling Guild system.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from database import Base

HUNTER_RANKS = ("E", "D", "C", "B", "A", "S", "National-Level", "Monarch")

GUILD_RANKS = (
    "Bronze Guild", "Silver Guild", "Gold Guild", "Platinum Guild",
    "Diamond Guild", "S-Rank Guild", "Shadow Monarch Guild",
)


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    email         = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False, default="")
    is_admin      = Column(Boolean, nullable=False, default=False)   # ← admin flag

    # RPG stats
    hunter_rank  = Column(String(32), nullable=False, default="E")
    hunter_class = Column(String(64), nullable=False, default="Fighter")
    level        = Column(Integer, nullable=False, default=1)
    total_xp     = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

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
    __tablename__ = "guilds"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    emblem      = Column(String(8), nullable=False, default="⚔️")
    guild_rank  = Column(String(64), nullable=False, default="Bronze Guild")
    max_members = Column(Integer, nullable=False, default=50)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    members = relationship(
        "GuildMember", back_populates="guild", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("max_members >= 1", name="ck_guild_max_members_positive"),
    )

    def __repr__(self):
        return f"<Guild id={self.id} name={self.name!r} rank={self.guild_rank}>"


class GuildMember(Base):
    __tablename__ = "guild_members"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    guild_id  = Column(Integer, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False)
    role      = Column(String(32), nullable=False, default="Member")
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user  = relationship("User",  back_populates="membership")
    guild = relationship("Guild", back_populates="members")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_guild_member_user"),
    )

    def __repr__(self):
        return f"<GuildMember user_id={self.user_id} guild_id={self.guild_id} role={self.role}>"
