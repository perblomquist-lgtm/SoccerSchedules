"""
Script to identify and remove duplicate games from the database.
Keeps the oldest game record for each unique combination of:
- division_id
- home_team_name  
- away_team_name
- game_date
- game_time
"""
import asyncio
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import create_async_session_maker, async_sessionmaker
from app.core.database import get_engine
from app.models.models import Game
import os


async def find_and_remove_duplicates():
    """Find and remove duplicate games"""
    engine = get_engine()
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Find all games
        result = await db.execute(select(Game).order_by(Game.created_at))
        all_games = result.scalars().all()
        
        print(f"Total games in database: {len(all_games)}")
        
        # Group games by unique key
        game_groups = {}
        for game in all_games:
            key = (
                game.division_id,
                game.home_team_name,
                game.away_team_name,
                game.game_date,
                game.game_time
            )
            if key not in game_groups:
                game_groups[key] = []
            game_groups[key].append(game)
        
        # Find duplicates
        duplicates_to_delete = []
        for key, games in game_groups.items():
            if len(games) > 1:
                # Keep the oldest (first created), delete the rest
                games_sorted = sorted(games, key=lambda g: g.created_at)
                duplicates_to_delete.extend(games_sorted[1:])  # All except the first
        
        print(f"Found {len(duplicates_to_delete)} duplicate games to remove")
        
        if duplicates_to_delete:
            # Show some examples
            print("\nExample duplicates:")
            for game in duplicates_to_delete[:5]:
                print(f"  ID {game.id}: {game.home_team_name} vs {game.away_team_name} at {game.game_time} on {game.game_date}")
            
            # Ask for confirmation
            response = input(f"\nDelete {len(duplicates_to_delete)} duplicate games? (yes/no): ")
            
            if response.lower() == 'yes':
                for game in duplicates_to_delete:
                    await db.delete(game)
                
                await db.commit()
                print(f"Successfully deleted {len(duplicates_to_delete)} duplicate games")
            else:
                print("Cancelled - no games deleted")
        else:
            print("No duplicates found!")


if __name__ == "__main__":
    asyncio.run(find_and_remove_duplicates())
