import os
import sys

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Required settings must exist before the app is imported
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-outside-the-test-suite")

from app.db.database import Base, get_db
from app.main import app


# Create in-memory test database
def create_test_engine():
    """Create a fresh in-memory database engine"""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# Initialize test engine and session maker at import time
test_engine = create_test_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    """Override get_db to use test database"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Set override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    """Database session fixture"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client():
    """FastAPI test client"""
    from starlette.testclient import TestClient

    return TestClient(app)


@pytest.fixture(scope="function")
def authenticated_client(client, db):
    """FastAPI test client with authenticated user"""
    import uuid

    from app.core.security import create_access_token, hash_password
    from app.db.models import User

    # Create a test user with unique email
    unique_email = f"test+{uuid.uuid4().hex[:8]}@example.com"
    user = User(email=unique_email, password_hash=hash_password("TestPassword123"))
    db.add(user)
    db.commit()

    # Create token for this user
    token = create_access_token(user_id=user.id)

    # Add auth header to all requests
    client.headers = {"Authorization": f"Bearer {token}"}
    return client
