"""Source management service"""

import feedparser
import requests
from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Source
from app.schemas.source import FeedTestResponse, SourceCreate, SourceUpdate


class SourceService:
    @staticmethod
    def create_source(db: Session, user_id: int, source_create: SourceCreate) -> Source:
        """Create a new source for user"""
        # Check if URL already exists for this user
        existing = (
            db.query(Source).filter(and_(Source.user_id == user_id, Source.url == source_create.url)).first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="This URL is already added to your sources"
            )

        # Validate the RSS feed
        feed_test = SourceService.test_feed(source_create.url)
        if not feed_test.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid RSS feed: {feed_test.error}"
            )

        source = Source(
            user_id=user_id, name=source_create.name, url=source_create.url, category=source_create.category
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def get_source(db: Session, user_id: int, source_id: int) -> Source:
        """Get a source by ID (only if owned by user)"""
        source = db.query(Source).filter(and_(Source.id == source_id, Source.user_id == user_id)).first()

        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

        return source

    @staticmethod
    def list_sources(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Source]:
        """List all sources for a user"""
        return db.query(Source).filter(Source.user_id == user_id).offset(skip).limit(limit).all()

    @staticmethod
    def update_source(db: Session, user_id: int, source_id: int, source_update: SourceUpdate) -> Source:
        """Update a source (only if owned by user)"""
        source = SourceService.get_source(db, user_id, source_id)

        update_data = source_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(source, key, value)

        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def delete_source(db: Session, user_id: int, source_id: int) -> None:
        """Delete a source (only if owned by user)"""
        source = SourceService.get_source(db, user_id, source_id)
        db.delete(source)
        db.commit()

    @staticmethod
    def test_feed(url: str) -> FeedTestResponse:
        """Test if a URL is a valid RSS feed"""
        try:
            # Fetch the feed with timeout
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            # Check if it's a valid feed
            if not feed.entries:
                return FeedTestResponse(valid=False, error="Feed contains no entries", entries=0)

            return FeedTestResponse(
                valid=True, title=feed.feed.get("title", "Unknown"), entries=len(feed.entries)
            )

        except requests.Timeout:
            return FeedTestResponse(valid=False, error="Request timeout", entries=0)
        except requests.RequestException as e:
            return FeedTestResponse(valid=False, error=f"Connection error: {str(e)[:50]}", entries=0)
        except Exception as e:
            return FeedTestResponse(valid=False, error=f"Invalid feed format: {str(e)[:50]}", entries=0)
