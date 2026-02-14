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
                
                # Clean up any duplicates that might have been created
                duplicates_removed = await self._cleanup_duplicate_games(event)
                if duplicates_removed > 0:
                    logger.info(f"Removed {duplicates_removed} duplicate games")
                    stats['duplicates_removed'] = duplicates_removed
                
                # Update event start/end dates based on game dates
                await self._update_event_dates_from_games(event)
                
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
            await self.db.commit()  # Commit immediately to release locks
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
            await self.db.commit()  # Commit updates immediately
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
            
            divisions_map[div_name] = division
        
        # Commit all divisions at once to release locks
        await self.db.commit()
        logger.info(f"Processed {len(divisions_map)} divisions for event {event.name}")
        return divisions_map
    
    async def _store_games(self, event: Event, divisions_map: Dict[str, Division], games_data: List[Dict]) -> Dict[str, int]:
        """Store or update games with batched commits to reduce lock time"""
        stats = {'total': 0, 'created': 0, 'updated': 0, 'skipped': 0}
        
        # PERFORMANCE: Bulk load all existing games for this event (1 query instead of 1000+)
        division_ids = [div.id for div in divisions_map.values()]
        if division_ids:
            result = await self.db.execute(
                select(Game).where(Game.division_id.in_(division_ids))
            )
            existing_games = result.scalars().all()
            
            # Build multiple lookup dictionaries for O(1) access with fallback strategies
            games_by_gotsport_id = {
                g.gotsport_game_id: g 
                for g in existing_games 
                if g.gotsport_game_id
            }
            # NEW: Lookup by game_number + division (more stable than teams/time)
            games_by_game_number = {
                (g.division_id, g.game_number): g
                for g in existing_games
                if g.game_number
            }
            games_by_signature = {
                (g.division_id, g.home_team_name, g.away_team_name, 
                 g.game_date, g.game_time): g
                for g in existing_games
            }
        else:
            games_by_gotsport_id = {}
            games_by_game_number = {}
            games_by_signature = {}
        
        # Process games in batches to avoid long-running transactions
        BATCH_SIZE = 200
        batch_count = 0
        
        for game_data in games_data:
            stats['total'] += 1
            
            # Get division
            div_name = game_data.get('division_name')
            division = divisions_map.get(div_name)
            
            if not division:
                logger.warning(f"No division found for game: {game_data}")
                stats['skipped'] += 1
                continue
            
            # Check if game exists using multiple strategies to prevent duplicates
            gotsport_game_id = game_data.get('gotsport_game_id')
            game_number = game_data.get('game_number')
            home_team = game_data.get('home_team_name')
            away_team = game_data.get('away_team_name')
            game_date = game_data.get('game_date')
            game_time = game_data.get('game_time')
            game = None
            
            # Strategy 1: Match by gotsport_game_id (most reliable)
            if gotsport_game_id and gotsport_game_id in games_by_gotsport_id:
                game = games_by_gotsport_id[gotsport_game_id]
            
            # Strategy 2: Match by game_number + division (stable across schedule changes)
            if not game and game_number:
                game = games_by_game_number.get((division.id, game_number))
            
            # Strategy 3: Match by exact signature (teams + date + time)
            if not game and home_team and away_team and game_date and game_time:
                signature = (division.id, home_team, away_team, game_date, game_time)
                game = games_by_signature.get(signature)
            
            if game:
                # Update existing game
                self._update_game_from_data(game, game_data)
                stats['updated'] += 1
            else:
                # Create new game
                game = self._create_game_from_data(division.id, game_data)
                self.db.add(game)
                stats['created'] += 1
                
                # Add to lookup dictionaries to prevent duplicates within this scrape
                if gotsport_game_id:
                    games_by_gotsport_id[gotsport_game_id] = game
                if game_number:
                    games_by_game_number[(division.id, game_number)] = game
                if home_team and away_team and game_date and game_time:
                    signature = (division.id, home_team, away_team, game_date, game_time)
                    games_by_signature[signature] = game
            
            batch_count += 1
            
            # Commit in batches to reduce lock time (critical for performance!)
            if batch_count >= BATCH_SIZE:
                await self.db.commit()
                batch_count = 0
                logger.debug(f"Committed batch: {stats['created']} created, {stats['updated']} updated so far")
        
        # Commit any remaining games
        if batch_count > 0:
            await self.db.commit()
        
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
    
    async def _update_event_dates_from_games(self, event: Event):
        """Update event start_date and end_date based on the earliest and latest game dates"""
        try:
            from sqlalchemy import func
            
            # Skip if this isn't the first scrape and dates are already set
            # (dates rarely change after initial scrape)
            if event.start_date and event.end_date and event.last_scraped_at:
                logger.debug(f"Event {event.name} already has dates, skipping update")
                return
            
            logger.info(f"Starting date update for event {event.name} (ID: {event.id})")
            
            # Query for min and max game_date for this event's games
            result = await self.db.execute(
                select(
                    func.min(Game.game_date),
                    func.max(Game.game_date)
                ).join(Division).where(
                    Division.event_id == event.id,
                    Game.game_date.isnot(None)
                )
            )
            
            min_date, max_date = result.one()
            
            logger.info(f"Query result - min_date: {min_date}, max_date: {max_date}")
            
            if min_date and max_date:
                # Only update if dates are actually different
                if event.start_date != min_date or event.end_date != max_date:
                    event.start_date = min_date
                    event.end_date = max_date
                    await self.db.commit()  # Commit immediately to release locks
                    logger.info(f"✅ Updated event {event.name} dates: {min_date.date()} to {max_date.date()}")
                else:
                    logger.debug(f"Event {event.name} dates unchanged, skipping commit")
            else:
                logger.warning(f"⚠️ No game dates found for event {event.name}")
        except Exception as e:
            logger.error(f"❌ Error updating event dates: {e}", exc_info=True)
    
    async def _cleanup_duplicate_games(self, event: Event) -> int:
        """
        Detect and remove duplicate games after scraping using window functions.
        Keeps the most recently updated game when duplicates are found.
        Single SQL query for better performance.
        """
        from sqlalchemy import text
        
        duplicates_removed = 0
        
        try:
            # Use window functions to identify duplicates and delete all but the most recent
            # This is much faster than the N-query approach
            delete_query = text("""
                WITH ranked_games AS (
                    SELECT g.id,
                           ROW_NUMBER() OVER (
                               PARTITION BY g.division_id, g.home_team_name, g.away_team_name, g.game_date
                               ORDER BY g.updated_at DESC, g.id DESC
                           ) as rn
                    FROM games g
                    JOIN divisions d ON g.division_id = d.id
                    WHERE d.event_id = :event_id
                )
                DELETE FROM games
                WHERE id IN (
                    SELECT id FROM ranked_games WHERE rn > 1
                )
            """)
            
            result = await self.db.execute(delete_query, {"event_id": event.id})
            duplicates_removed = result.rowcount
            
            if duplicates_removed > 0:
                await self.db.commit()
                logger.info(f"Cleaned up {duplicates_removed} duplicate games for event {event.name}")
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicates: {e}", exc_info=True)
        
        return duplicates_removed
