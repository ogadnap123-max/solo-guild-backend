"""
database.py — SQLite engine + session dependency for the Solo Leveling Guild API.
Uses an environment variable DATABASE_URL when set (for Railway/production),
falls back to a local SQLite file for development.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Railway sets DATABASE_URL automatically if you add a Postgres plugin.
# For SQLite (default), we use a /tmp path on the server so it's writable.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:////tmp/solo_guild.db"   # /tmp is always writable on Railway
)

# Railway/Heroku-style URLs sometimes use postgres:// — SQLAlchemy 1.4+/2.x requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"[database] Connecting via dialect: {DATABASE_URL.split('://')[0]}")
# SQLite needs check_same_thread=False; Postgres doesn't need it but it's harmless
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
