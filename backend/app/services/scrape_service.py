"""Service for managing scraping operations and data persistence"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Event, Division, Team, Game, ScrapeLog, ScrapeStatus, GameStatus
from app.scraper.gotsport import GotsportScraper

logger = logging.getLogger(__name__)


class ScrapeService:
    """Service for handling scraping operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def scrape_and_store_event(self, event_url: str, force: bool = False) -> Tuple[Event, ScrapeLog]:
        """
        Scrape an event and store data in the database
        
        Args:
            event_url: URL of the Gotsport event
            force: Force scrape even if recently scraped
            
        Returns:
            Tuple of (Event, ScrapeLog)
        """
        scraper = GotsportScraper()
        
        try:
            # Start scraping
            await scraper.start()
            
            # Extract event ID from URL
            event_id = scraper._extract_event_id_from_url(event_url)
            if not event_id:
                raise ValueError(f"Invalid event URL: {event_url}")
            
            # Check if event exists
            event = await self._get_event_by_gotsport_id(event_id)
            
            if event and not force:
                # Check when it was last scraped
                if event.last_scraped_at:
                    now = datetime.now(timezone.utc)
                    last_scraped = event.last_scraped_at
                    if last_scraped.tzinfo is None:
                        last_scraped = last_scraped.replace(tzinfo=timezone.utc)
                    
                    hours_since_scrape = (now - last_scraped).total_seconds() / 3600
                    if hours_since_scrape < 1:  # Don't scrape more than once per hour
                        logger.info(f"Event {event_id} was scraped {hours_since_scrape:.1f} hours ago, skipping")
                        # Return existing event without creating new scrape log
                        return event, None
            
            # Create scrape log
            scrape_log = ScrapeLog(
                event_id=event.id if event else None,
                status=ScrapeStatus.IN_PROGRESS,
                scrape_started_at=datetime.now(timezone.utc),
            )
            
            try:
                # Perform the scrape
                logger.info(f"Starting scrape of event {event_id}")
                scraped_data = await scraper.scrape_event(event_url)
                
                # Store or update event
                event = await self._store_event_data(event, scraped_data, event_url)
                
                # Update scrape log with event ID if it's new
                if not scrape_log.event_id:
                    scrape_log.event_id = event.id
                
                # Store divisions
                divisions_map = await self._store_divisions(event, scraped_data.get('divisions', []))
                
                # Store schedules/games
                stats = await self._store_games(event, divisions_map, scraped_data.get('schedules', []))
                
                # Update scrape log with success
                scrape_log.status = ScrapeStatus.SUCCESS
                scrape_log.scrape_completed_at = datetime.now(timezone.utc)
                scrape_log.games_scraped = stats['total']
                scrape_log.games_created = stats['created']
                scrape_log.games_updated = stats['updated']
                
                # Update event last scraped time
                event.last_scraped_at = datetime.now(timezone.utc)
                
                self.db.add(scrape_log)
                await self.db.commit()
                await self.db.refresh(event)
                
                logger.info(f"Successfully scraped event {event_id}: {stats}")
                logger.info(f"Committed scrape data to database: {stats['total']} games, {len(divisions_map)} divisions")
                
                return event, scrape_log
                
            except Exception as e:
                logger.error(f"Error scraping event {event_id}: {e}", exc_info=True)
                scrape_log.status = ScrapeStatus.FAILED
                scrape_log.scrape_completed_at = datetime.now(timezone.utc)
                scrape_log.error_message = str(e)
                self.db.add(scrape_log)
                await self.db.commit()
                raise
                
        finally:
            await scraper.stop()
    
    async def _get_event_by_gotsport_id(self, gotsport_event_id: str) -> Optional[Event]:
        """Get event by Gotsport event ID"""
        result = await self.db.execute(
            select(Event).where(Event.gotsport_event_id == gotsport_event_id)
        )
        return result.scalar_one_or_none()
    
    async def _store_event_data(self, event: Optional[Event], scraped_data: Dict, event_url: str) -> Event:
        """Store or update event data"""
        event_data = scraped_data.get('event', {})
        gotsport_event_id = scraped_data.get('event_id', '')
        
        if not event:
            # Create new event
            event = Event(
                gotsport_event_id=gotsport_event_id,
                name=event_data.get('name', f'Event {gotsport_event_id}'),
                location=event_data.get('location'),
                start_date=event_data.get('start_date'),
                end_date=event_data.get('end_date'),
                url=event_url,
                status='active',
            )
            self.db.add(event)
            await self.db.flush()  # Get the ID
            logger.info(f"Created new event: {event.name}")
        else:
            # Update existing event
            if event_data.get('name'):
                event.name = event_data['name']
            if event_data.get('location'):
                event.location = event_data['location']
            if event_data.get('start_date'):
                event.start_date = event_data['start_date']
            if event_data.get('end_date'):
                event.end_date = event_data['end_date']
            event.url = event_url
            event.updated_at = datetime.now(timezone.utc)
            logger.info(f"Updated existing event: {event.name}")
        
        return event
    
    async def _store_divisions(self, event: Event, divisions_data: List[Dict]) -> Dict[str, Division]:
        """Store or update divisions, return mapping of division name to Division object"""
        divisions_map = {}
        
        # Get existing divisions for this event
        result = await self.db.execute(
            select(Division).where(Division.event_id == event.id)
        )
        existing_divisions = {div.name: div for div in result.scalars().all()}
        
        for div_data in divisions_data:
            div_name = div_data.get('name')
            if not div_name:
                continue
            
            if div_name in existing_divisions:
                # Update existing division
                division = existing_divisions[div_name]
                if div_data.get('age_group'):
                    division.age_group = div_data['age_group']
                if div_data.get('gender'):
                    division.gender = div_data['gender']
                if div_data.get('gotsport_division_id'):
                    division.gotsport_division_id = div_data['gotsport_division_id']
                division.updated_at = datetime.now(timezone.utc)
            else:
                # Create new division
                division = Division(
                    event_id=event.id,
                    name=div_name,
                    age_group=div_data.get('age_group'),
                    gender=div_data.get('gender'),
                    gotsport_division_id=div_data.get('gotsport_division_id'),
                )
                self.db.add(division)
                await self.db.flush()
            
            divisions_map[div_name] = division
        
        logger.info(f"Processed {len(divisions_map)} divisions for event {event.name}")
        return divisions_map
    
    async def _store_games(self, event: Event, divisions_map: Dict[str, Division], games_data: List[Dict]) -> Dict[str, int]:
        """Store or update games"""
        stats = {'total': 0, 'created': 0, 'updated': 0, 'skipped': 0}
        
        for game_data in games_data:
            stats['total'] += 1
            
            # Get division
            div_name = game_data.get('division_name')
            division = divisions_map.get(div_name)
            
            if not division and div_name:
                # Create division on the fly if it doesn't exist
                division = Division(
                    event_id=event.id,
                    name=div_name,
                )
                self.db.add(division)
                await self.db.flush()
                divisions_map[div_name] = division
            
            if not division:
                logger.warning(f"No division found for game: {game_data}")
                stats['skipped'] += 1
                continue
            
            # Check if game exists
            gotsport_game_id = game_data.get('gotsport_game_id')
            game = None
            
            if gotsport_game_id:
                result = await self.db.execute(
                    select(Game).where(
                        Game.division_id == division.id,
                        Game.gotsport_game_id == gotsport_game_id
                    )
                )
                game = result.scalar_one_or_none()
            
            if game:
                # Update existing game
                self._update_game_from_data(game, game_data)
                stats['updated'] += 1
            else:
                # Create new game
                game = self._create_game_from_data(division.id, game_data)
                self.db.add(game)
                stats['created'] += 1
        
        await self.db.flush()
        logger.info(f"Processed {stats['total']} games: {stats['created']} created, {stats['updated']} updated, {stats['skipped']} skipped")
        return stats
    
    def _create_game_from_data(self, division_id: int, game_data: Dict) -> Game:
        """Create a new Game object from scraped data"""
        return Game(
            division_id=division_id,
            gotsport_game_id=game_data.get('gotsport_game_id'),
            game_number=game_data.get('game_number'),
            home_team_name=game_data.get('home_team_name'),
            away_team_name=game_data.get('away_team_name'),
            game_date=game_data.get('game_date'),
            game_time=game_data.get('game_time'),
            field_name=game_data.get('field_name'),
            field_location=game_data.get('field_location'),
            home_score=game_data.get('home_score'),
            away_score=game_data.get('away_score'),
            status=game_data.get('status', GameStatus.SCHEDULED),
        )
    
    def _update_game_from_data(self, game: Game, game_data: Dict):
        """Update an existing Game object with scraped data"""
        if game_data.get('game_number'):
            game.game_number = game_data['game_number']
        if game_data.get('home_team_name'):
            game.home_team_name = game_data['home_team_name']
        if game_data.get('away_team_name'):
            game.away_team_name = game_data['away_team_name']
        if game_data.get('game_date'):
            game.game_date = game_data['game_date']
        if game_data.get('game_time'):
            game.game_time = game_data['game_time']
        if game_data.get('field_name'):
            game.field_name = game_data['field_name']
        if game_data.get('field_location'):
            game.field_location = game_data['field_location']
        if game_data.get('home_score') is not None:
            game.home_score = game_data['home_score']
        if game_data.get('away_score') is not None:
            game.away_score = game_data['away_score']
        if game_data.get('status'):
            game.status = game_data['status']
        game.updated_at = datetime.now(timezone.utc)
