"""
Daily Check-in collector.

Reads the last 7 days of check-in data (energy, mood, focus, sleep)
to provide context for briefing personalization.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from src.config import VeraConfig
from src.notion import NotionClient

logger = logging.getLogger(__name__)


class DailyCheck:
    """Single day's check-in data."""

    def __init__(
        self,
        date: str,
        energy: Optional[float],
        mood: Optional[float],
        focus: Optional[float],
        sleep_quality: Optional[float],
        notes: str,
    ):
        self.date = date
        self.energy = energy
        self.mood = mood
        self.focus = focus
        self.sleep_quality = sleep_quality
        self.notes = notes

    @property
    def average_score(self) -> Optional[float]:
        """Average of all non-None dimensions."""
        values = [v for v in [self.energy, self.mood, self.focus, self.sleep_quality] if v is not None]
        return round(sum(values) / len(values), 1) if values else None

    def __repr__(self):
        return f"DailyCheck({self.date}, avg={self.average_score})"


async def collect_daily_checks(
    notion: NotionClient, config: VeraConfig
) -> list[DailyCheck]:
    """Fetch last 7 days of daily check-in data."""
    fields = config.daily_check.fields
    tz = ZoneInfo(config.timezone)
    cutoff = (datetime.now(tz) - timedelta(days=7)).strftime("%Y-%m-%d")

    raw_pages = await notion.query_database(
        config.daily_check.database_id,
        filter={
            "property": fields.date,
            "date": {"on_or_after": cutoff},
        },
        sorts=[{"property": fields.date, "direction": "descending"}],
    )

    checks = []
    for page in raw_pages:
        props = page.get("properties", {})
        checks.append(DailyCheck(
            date=NotionClient.extract_date(props, fields.date) or "",
            energy=NotionClient.extract_number(props, fields.energy),
            mood=NotionClient.extract_number(props, fields.mood),
            focus=NotionClient.extract_number(props, fields.focus),
            sleep_quality=NotionClient.extract_number(props, fields.sleep_quality),
            notes=NotionClient.extract_rich_text(props, fields.notes),
        ))

    logger.info(f"Collected {len(checks)} daily check-ins (last 7 days)")
    return checks
