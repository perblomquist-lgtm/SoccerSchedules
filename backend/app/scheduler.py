"""Smart scheduler for scraping events based on tournament timing"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import engine
from app.models.models import Event
from app.services.scrape_service import ScrapeService

logger = logging.getLogger(__name__)


class SmartScheduler:
    """
    Smart scheduler that adjusts scraping frequency based on tournament timing:
    - Daily (24h) by default
    - Hourly (1h) starting the day before first game until tournament ends
    - Back to daily after tournament ends
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.session_maker = async_sessionmaker(engine, expire_on_commit=False)
        self.scheduled_jobs: Dict[int, str] = {}  # event_id -> job_id mapping
    
    async def start(self):
        """Start the scheduler"""
        logger.info("Starting smart scheduler...")
        self.scheduler.start()
        
        # Schedule the job that checks and updates all event schedules
        self.scheduler.add_job(
            self._check_and_scrape_events,
            trigger=IntervalTrigger(minutes=30),  # Check every 30 minutes
            id='check_events',
            name='Check and scrape events',
            replace_existing=True,
        )
        
        logger.info("Smart scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping smart scheduler...")
        self.scheduler.shutdown()
    
    async def _check_and_scrape_events(self):
        """Check all active events and scrape if needed"""
        logger.info("Checking events for scraping...")
        
        async with self.session_maker() as session:
            # Get all active events
            result = await session.execute(
                select(Event).where(Event.status == 'active')
            )
            events = result.scalars().all()
            
            logger.info(f"Found {len(events)} active events to check")
            
            for event in events:
                try:
                    should_scrape = await self._should_scrape_event(event)
                    
                    if should_scrape:
                        logger.info(f"Scraping event {event.id}: {event.name}")
                        await self._scrape_event(event.id, event.url)
                    else:
                        interval = self._get_scrape_interval(event)
                        logger.debug(f"Skipping event {event.id}, interval: {interval}h")
                        
                except Exception as e:
                    logger.error(f"Error checking event {event.id}: {e}", exc_info=True)
    
    async def _should_scrape_event(self, event: Event) -> bool:
        """Determine if an event should be scraped now"""
        if not event.last_scraped_at:
            # Never scraped, should scrape
            return True
        
        # Calculate how long since last scrape (make both timezone-aware)
        now = datetime.now(timezone.utc)
        last_scraped = event.last_scraped_at
        if last_scraped.tzinfo is None:
            last_scraped = last_scraped.replace(tzinfo=timezone.utc)
        
        hours_since_scrape = (now - last_scraped).total_seconds() / 3600
        
        # Get the appropriate interval for this event
        interval_hours = self._get_scrape_interval(event)
        
        # Scrape if enough time has passed
        return hours_since_scrape >= interval_hours
    
    def _get_scrape_interval(self, event: Event) -> int:
        """
        Get scrape interval in hours based on tournament timing
        - Daily (24h) by default
        - Hourly (1h) from day before first game until tournament ends
        - Daily (24h) after tournament ends
        """
        if not event.start_date or not event.end_date:
            # No dates available, use default daily interval
            return settings.DEFAULT_SCRAPE_INTERVAL_HOURS
        
        now = datetime.now(timezone.utc)
        
        # Convert date objects to datetime objects at midnight UTC
        start_date = event.start_date
        if isinstance(start_date, datetime):
            # It's already a datetime
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            # It's a date object, convert to datetime at midnight UTC
            start_date = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        
        end_date = event.end_date
        if isinstance(end_date, datetime):
            # It's already a datetime
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            # It's a date object, convert to datetime at end of day UTC (23:59:59)
            end_date = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        
        # Calculate day before tournament starts
        day_before_start = start_date - timedelta(days=1)
        
        # Logic:
        # - Before (day before tournament): daily (24h)
        # - From (day before) through (end date): hourly (1h)
        # - After tournament: daily (24h)
        
        if now < day_before_start:
            # Before tournament window
            logger.debug(f"Event {event.id}: Before tournament window (now: {now}, day_before: {day_before_start})")
            return settings.DEFAULT_SCRAPE_INTERVAL_HOURS
        elif now <= end_date:
            # During tournament window (including day before)
            logger.info(f"Event {event.id}: IN TOURNAMENT WINDOW - using hourly interval (now: {now}, start: {start_date}, end: {end_date})")
            return settings.TOURNAMENT_SCRAPE_INTERVAL_HOURS
        else:
            # After tournament
            logger.debug(f"Event {event.id}: After tournament (now: {now}, end: {end_date})")
            return settings.DEFAULT_SCRAPE_INTERVAL_HOURS
    
    def get_next_scrape_time(self, event: Event) -> Optional[datetime]:
        """Calculate when the event will be scraped next"""
        if not event.last_scraped_at:
            return datetime.now(timezone.utc)  # Scrape ASAP
        
        interval_hours = self._get_scrape_interval(event)
        last_scraped = event.last_scraped_at
        if last_scraped.tzinfo is None:
            last_scraped = last_scraped.replace(tzinfo=timezone.utc)
        
        next_scrape = last_scraped + timedelta(hours=interval_hours)
        
        # If next scrape is in the past (e.g., interval changed from 24h to 1h), schedule for now
        now = datetime.now(timezone.utc)
        if next_scrape < now:
            return now
        
        return next_scrape
    
    def get_hours_until_next_scrape(self, event: Event) -> Optional[float]:
        """Get hours until next scrape for an event"""
        next_scrape = self.get_next_scrape_time(event)
        if not next_scrape:
            return None
        
        now = datetime.now(timezone.utc)
        if next_scrape.tzinfo is None:
            next_scrape = next_scrape.replace(tzinfo=timezone.utc)
        
        hours = (next_scrape - now).total_seconds() / 3600
        return max(0, round(hours, 1))  # Return float with 1 decimal place
    
    async def _scrape_event(self, event_id: int, event_url: str):
        """Scrape a single event"""
        async with self.session_maker() as session:
            try:
                scrape_service = ScrapeService(session)
                await scrape_service.scrape_and_store_event(event_url, force=False)
                logger.info(f"Successfully scraped event {event_id}")
            except Exception as e:
                logger.error(f"Error scraping event {event_id}: {e}", exc_info=True)
    
    async def trigger_manual_scrape(self, event_id: int, force: bool = False) -> bool:
        """Manually trigger a scrape for a specific event"""
        async with self.session_maker() as session:
            result = await session.execute(
                select(Event).where(Event.id == event_id)
            )
            event = result.scalar_one_or_none()
            
            if not event:
                logger.error(f"Event {event_id} not found")
                return False
            
            try:
                scrape_service = ScrapeService(session)
                await scrape_service.scrape_and_store_event(event.url, force=force)
                logger.info(f"Manual scrape completed for event {event_id}")
                return True
            except Exception as e:
                logger.error(f"Error in manual scrape for event {event_id}: {e}", exc_info=True)
                return False


# Global scheduler instance
scheduler_instance: Optional[SmartScheduler] = None


async def get_scheduler() -> SmartScheduler:
    """Get the global scheduler instance"""
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = SmartScheduler()
        await scheduler_instance.start()
    return scheduler_instance


async def start_scheduler():
    """Start the global scheduler"""
    await get_scheduler()


def stop_scheduler():
    """Stop the global scheduler"""
    global scheduler_instance
    if scheduler_instance:
        scheduler_instance.stop()
