"""
Database configuration for Messaging Service.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Lazily create engine/sessionmaker so tests can set DATABASE_URL before use.
_engine = None
_SessionLocal = None


def _build_engine_and_session():
    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return _engine, _SessionLocal

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/platform_db",
    )

    engine_kwargs = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    _engine = create_engine(DATABASE_URL, **engine_kwargs)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal


def get_engine():
    engine, _ = _build_engine_and_session()
    return engine


def get_sessionmaker():
    _, SessionLocal = _build_engine_and_session()
    return SessionLocal


def get_db():
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
