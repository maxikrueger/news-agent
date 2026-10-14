from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


# Lazy initialization of database engine (only create if DATABASE_URL is set)
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None and settings.DATABASE_URL:
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.SQLALCHEMY_ECHO,
            poolclass=NullPool if "sqlite" in settings.DATABASE_URL else None,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db():
    SessionLocal = get_session_factory()
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
