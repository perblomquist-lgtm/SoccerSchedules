import asyncio
from app.core.database import AsyncSessionLocal
from app.models.models import BracketStanding
from sqlalchemy import select, func

async def check_duplicates():
    async with AsyncSessionLocal() as db:
        # Check for Ballers Den 2014B specifically
        result = await db.execute(
            select(BracketStanding)
            .where(BracketStanding.team_name == 'Ballers Den 2014B')
            .order_by(BracketStanding.division_id, BracketStanding.bracket_name, BracketStanding.points.desc())
        )
        ballers = result.scalars().all()
        print(f'Ballers Den 2014B entries: {len(ballers)}')
        for b in ballers:
            print(f'  ID:{b.id} Div:{b.division_id} Bracket:"{b.bracket_name}" PTS:{b.points} GD:{b.goal_difference}')

asyncio.run(check_duplicates())
