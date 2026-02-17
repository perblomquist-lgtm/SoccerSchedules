"""Cleanup script to remove Unknown Bracket standings for an event."""
import argparse
import asyncio

from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models.models import BracketStanding, Division


async def cleanup_unknown_brackets(event_id: int, dry_run: bool) -> None:
    async with AsyncSessionLocal() as session:
        division_ids = (
            await session.execute(
                select(Division.id).where(Division.event_id == event_id)
            )
        ).scalars().all()

        if not division_ids:
            print(f"No divisions found for event {event_id}.")
            return

        filter_clause = (
            BracketStanding.bracket_name == "Unknown Bracket",
            BracketStanding.division_id.in_(division_ids),
        )

        count = await session.scalar(
            select(func.count()).select_from(BracketStanding).where(*filter_clause)
        )
        count = int(count or 0)

        if dry_run:
            print(
                f"Dry run: would delete {count} Unknown Bracket standings for event {event_id}."
            )
            return

        result = await session.execute(
            delete(BracketStanding).where(*filter_clause)
        )
        await session.commit()

        deleted = result.rowcount if result.rowcount is not None else count
        print(
            f"Deleted {deleted} Unknown Bracket standings for event {event_id}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete Unknown Bracket standings for an event."
    )
    parser.add_argument("--event-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(cleanup_unknown_brackets(args.event_id, args.dry_run))
