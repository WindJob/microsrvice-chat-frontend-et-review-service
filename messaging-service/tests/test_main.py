import pytest
from fastapi.testclient import TestClient
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# For CI/local tests: override explicite pour s'assurer d'utiliser SQLite
os.environ["DATABASE_URL"] = "sqlite:///./dev_messaging.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"

# Injecter un module 'shared.db_postgresql' factice avant d'importer main
import types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

_engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
_Base = declarative_base()

def _get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

fake_mod = types.ModuleType("shared.db_postgresql")
fake_mod.engine = _engine
fake_mod.SessionLocal = _SessionLocal
fake_mod.Base = _Base
fake_mod.get_db = _get_db
fake_mod.get_engine = lambda: _engine
fake_mod.get_sessionmaker = lambda: _SessionLocal
sys.modules["shared.db_postgresql"] = fake_mod

import main


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"
