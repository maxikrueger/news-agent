from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    sources: Mapped[list["Source"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="sources")
    articles: Mapped[list["Article"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    schedules: Mapped[list["Schedule"]] = relationship(secondary="schedule_sources", back_populates="sources")

    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_sources_active_user", "is_active", "user_id"),
        UniqueConstraint("user_id", "url", name="uq_source_user_url"),
    )


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    cron_expression: Mapped[str] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(100), server_default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_articles: Mapped[int] = mapped_column(Integer, server_default=text("7"))
    profile: Mapped[str] = mapped_column(String(500), server_default="Allgemeine Nachrichten")
    language: Mapped[str] = mapped_column(String(50), server_default="Deutsch")

    user: Mapped["User"] = relationship(back_populates="schedules")
    sources: Mapped[list["Source"]] = relationship(secondary="schedule_sources", back_populates="schedules")
    digests: Mapped[list["Digest"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")
    delivery_channels: Mapped[list["DeliveryChannel"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_user_next_run", "user_id", "next_run_at"),)


class ScheduleSource(Base):
    __tablename__ = "schedule_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))

    __table_args__ = (
        Index("idx_schedule_sources_source_id", "source_id"),
        UniqueConstraint("schedule_id", "source_id"),
    )


class Article(TimestampMixin, Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped["Source"] = relationship(back_populates="articles")

    __table_args__ = (
        Index("idx_source_published", "source_id", "published_at"),
        UniqueConstraint("source_id", "url", name="uq_article_source_url"),
    )


class Digest(TimestampMixin, Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), index=True)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_html: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), server_default="generated")

    schedule: Mapped["Schedule"] = relationship(back_populates="digests")

    __table_args__ = (Index("idx_schedule_created", "schedule_id", "created_at"),)


class DeliveryChannel(TimestampMixin, Base):
    __tablename__ = "delivery_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50))  # discord, email
    config: Mapped[str] = mapped_column(Text)  # JSON-encoded
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    schedule: Mapped["Schedule"] = relationship(back_populates="delivery_channels")


class Job(TimestampMixin, Base):
    """Execution record table created by the initial migration (reserved for job tracking)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedules.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(50), server_default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("idx_schedule_status", "schedule_id", "status"),)
