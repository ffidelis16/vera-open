"""Energy timing collector. Full implementation in Phase 4."""

from __future__ import annotations

import logging
from src.config import VeraConfig
from src.notion import NotionClient

logger = logging.getLogger(__name__)


async def collect_timing(notion: NotionClient, config: VeraConfig) -> list[dict]:
    """Fetch energy timing data."""
    fields = config.energy_timing.fields

    raw = await notion.query_database(config.energy_timing.database_id)

    items = []
    for page in raw:
        props = page.get("properties", {})
        items.append({
            "time_block": NotionClient.extract_select(props, fields.time_block),
            "energy_level": NotionClient.extract_number(props, fields.energy_level),
            "best_for": NotionClient.extract_rich_text(props, fields.best_for),
        })

    logger.info(f"Collected {len(items)} energy timing blocks")
    return items
