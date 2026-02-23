"""Pipeline tracking collector. Full implementation in Phase 4."""

from __future__ import annotations

import logging
from src.config import VeraConfig
from src.notion import NotionClient

logger = logging.getLogger(__name__)


async def collect_pipeline(notion: NotionClient, config: VeraConfig) -> list[dict]:
    """Fetch active pipeline items."""
    fields = config.pipeline.fields
    groups = config.pipeline.status_groups

    status_filters = [
        {"property": fields.status, "select": {"equals": s}}
        for s in groups.active
    ]

    raw = await notion.query_database(
        config.pipeline.database_id,
        filter={"or": status_filters} if len(status_filters) > 1 else status_filters[0],
    )

    items = []
    for page in raw:
        props = page.get("properties", {})
        items.append({
            "page_id": page["id"],
            "title": NotionClient.extract_title(props, fields.title),
            "status": NotionClient.extract_select(props, fields.status),
            "value": NotionClient.extract_number(props, fields.value),
            "next_action": NotionClient.extract_rich_text(props, fields.next_action),
            "deadline": NotionClient.extract_date(props, fields.deadline),
        })

    logger.info(f"Collected {len(items)} active pipeline items")
    return items
