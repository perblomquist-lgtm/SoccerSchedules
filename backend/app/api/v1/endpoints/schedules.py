"""Schedules API endpoints for querying games"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Event, Division, Game
from app.schemas.schemas import (
    GameDetailResponse,
    DivisionResponse,
    EventResponse,
    ScheduleResponse,
)

router = APIRouter()


@router.get("/{event_id}", response_model=ScheduleResponse)
async def get_event_schedule(
    event_id: int,
    division_id: Optional[int] = Query(None, description="Filter by division ID"),
    date_from: Optional[datetime] = Query(None, description="Filter games from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter games until this date"),
    field_name: Optional[str] = Query(None, description="Filter by field name"),
    team_name: Optional[str] = Query(None, description="Filter by team name (home or away)"),
    status: Optional[str] = Query(None, description="Filter by game status"),
    db: AsyncSession = Depends(get_db),
):
    """Get schedule for an event with optional filters"""
    # Get event
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    # Get divisions
    divisions_result = await db.execute(
        select(Division).where(Division.event_id == event_id).order_by(Division.name)
    )
    divisions = divisions_result.scalars().all()
    
    # Build games query
    query = (
        select(Game, Division)
        .join(Division)
        .where(Division.event_id == event_id)
    )
    
    # Apply filters
    if division_id:
        query = query.where(Game.division_id == division_id)
    
    if date_from:
        query = query.where(Game.game_date >= date_from)
    
    if date_to:
        query = query.where(Game.game_date <= date_to)
    
    if field_name:
        query = query.where(Game.field_name.ilike(f"%{field_name}%"))
    
    if team_name:
        query = query.where(
            or_(
                Game.home_team_name.ilike(f"%{team_name}%"),
                Game.away_team_name.ilike(f"%{team_name}%")
            )
        )
    
    if status:
        query = query.where(Game.status == status)
    
    # Order by date and time
    query = query.order_by(Game.game_date.asc(), Game.game_time.asc())
    
    # Execute query
    games_result = await db.execute(query)
    games_with_divisions = games_result.all()
    
    # Build response
    games_response = []
    for game, division in games_with_divisions:
        game_detail = GameDetailResponse(
            **game.__dict__,
            division_name=division.name,
            event_name=event.name,
        )
        games_response.append(game_detail)
    
    return ScheduleResponse(
        event=EventResponse(**event.__dict__),
        divisions=[DivisionResponse(**div.__dict__) for div in divisions],
        games=games_response,
        total_games=len(games_response),
    )


@router.get("/division/{division_id}/games", response_model=List[GameDetailResponse])
async def get_division_games(
    division_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all games for a specific division"""
    # Verify division exists
    div_result = await db.execute(
        select(Division).where(Division.id == division_id)
    )
    division = div_result.scalar_one_or_none()
    
    if not division:
        raise HTTPException(status_code=404, detail=f"Division {division_id} not found")
    
    # Get games
    games_result = await db.execute(
        select(Game)
        .where(Game.division_id == division_id)
        .order_by(Game.game_date.asc(), Game.game_time.asc())
    )
    games = games_result.scalars().all()
    
    # Get event for context
    event_result = await db.execute(
        select(Event).where(Event.id == division.event_id)
    )
    event = event_result.scalar_one()
    
    return [
        GameDetailResponse(
            **game.__dict__,
            division_name=division.name,
            event_name=event.name,
        )
        for game in games
    ]
