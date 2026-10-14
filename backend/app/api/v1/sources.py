"""Source management endpoints"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.schemas.source import (
    AVAILABLE_CATEGORIES,
    CategoriesResponse,
    FeedTestRequest,
    FeedTestResponse,
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from app.services.source import SourceService

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    user_id: int = Depends(get_current_user), db: Session = Depends(get_db), skip: int = 0, limit: int = 100
):
    """List all RSS sources for authenticated user"""
    sources = SourceService.list_sources(db, user_id, skip, limit)
    return sources


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    source_create: SourceCreate, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a new RSS source"""
    source = SourceService.create_source(db, user_id, source_create)
    return source


@router.get("/categories", response_model=CategoriesResponse)
async def get_categories():
    """Get available RSS feed categories"""
    return CategoriesResponse(categories=AVAILABLE_CATEGORIES)


@router.post("/test", response_model=FeedTestResponse)
async def test_feed(request: FeedTestRequest, user_id: int = Depends(get_current_user)):
    """Test if a URL is a valid RSS feed (auth required to prevent SSRF)"""
    result = SourceService.test_feed(request.url)
    return result


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get source details (only if owned by user)"""
    source = SourceService.get_source(db, user_id, source_id)
    return source


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_update: SourceUpdate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update source details"""
    source = SourceService.update_source(db, user_id, source_id, source_update)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a source"""
    SourceService.delete_source(db, user_id, source_id)
    return None
