"""Events API endpoints"""
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Event, Division, Game
from app.schemas.schemas import EventResponse, EventCreate, EventUpdate, EventWithStats
from app.services.scrape_service import ScrapeService
from app.scheduler import get_scheduler

router = APIRouter()


@router.get("/", response_model=List[EventWithStats])
async def list_events(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all events with statistics"""
    # Get events
    result = await db.execute(
        select(Event)
        .order_by(Event.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    events = result.scalars().all()
    
    if not events:
        return []
    
    # Get counts for all events in a single query (fixes N+1 problem)
    event_ids = [e.id for e in events]
    
    # Count divisions per event
    div_counts = await db.execute(
        select(Division.event_id, func.count(Division.id))
        .where(Division.event_id.in_(event_ids))
        .group_by(Division.event_id)
    )
    div_counts_map = {event_id: count for event_id, count in div_counts}
    
    # Count games per event
    game_counts = await db.execute(
        select(Division.event_id, func.count(Game.id))
        .join(Game)
        .where(Division.event_id.in_(event_ids))
        .group_by(Division.event_id)
    )
    game_counts_map = {event_id: count for event_id, count in game_counts}
    
    # Get scheduler for next scrape times
    scheduler = await get_scheduler()
    
    # Build response with stats
    response = []
    for event in events:
        next_scrape_hours = scheduler.get_hours_until_next_scrape(event)
        
        response.append(EventWithStats(
            **event.__dict__,
            total_divisions=div_counts_map.get(event.id, 0),
            total_teams=0,  # TODO: implement when we track teams properly
            total_games=game_counts_map.get(event.id, 0),
            next_scrape_in_hours=next_scrape_hours,
        ))
    
    return response


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new event (will be scraped automatically)"""
    # Check if event already exists
    result = await db.execute(
        select(Event).where(Event.gotsport_event_id == event.gotsport_event_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with gotsport_event_id {event.gotsport_event_id} already exists"
        )
    
    # Create event
    db_event = Event(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    
    # Trigger initial scrape in the background
    scheduler = await get_scheduler()
    asyncio.create_task(scheduler.trigger_manual_scrape(db_event.id, force=True))
    
    return db_event


@router.get("/{event_id}", response_model=EventWithStats)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific event by ID"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Count related entities (still better than original N+1 as these are simple aggregates)
    div_count = await db.scalar(
        select(func.count(Division.id)).where(Division.event_id == event.id)
    )
    game_count = await db.scalar(
        select(func.count(Game.id))
        .join(Division)
        .where(Division.event_id == event.id)
    )
    
    scheduler = await get_scheduler()
    next_scrape_hours = scheduler.get_hours_until_next_scrape(event)
    
    return EventWithStats(
        **event.__dict__,
        total_divisions=div_count or 0,
        total_teams=0,
        total_games=game_count or 0,
        next_scrape_in_hours=next_scrape_hours,
    )


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_update: EventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an event"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    # Update fields
    update_data = event_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
    
    await db.commit()
    await db.refresh(event)
    
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an event and all related data"""
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    await db.delete(event)
    await db.commit()
    
    return None
