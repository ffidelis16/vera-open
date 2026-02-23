"""
Tasks collector and urgency score calculator.

Collects active tasks from Notion, calculates urgency scores (0-100),
and writes them back to each task's urgency field.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

from src.config import VeraConfig
from src.notion import NotionClient

logger = logging.getLogger(__name__)


# ============================================================
# Data model
# ============================================================

class Task:
    """Parsed task from Notion, with computed urgency."""

    def __init__(
        self,
        page_id: str,
        title: str,
        status: str,
        deadline: Optional[str],
        priority: Optional[float],
        project: str,
        tags: list[str],
        last_edited: str,
        current_urgency: Optional[float],
    ):
        self.page_id = page_id
        self.title = title
        self.status = status
        self.deadline = deadline
        self.priority = priority
        self.project = project
        self.tags = tags
        self.last_edited = last_edited
        self.current_urgency = current_urgency
        self.computed_urgency: float = 0.0

    def __repr__(self):
        return f"Task({self.title!r}, urgency={self.computed_urgency:.0f})"


# ============================================================
# Collector
# ============================================================

async def collect_tasks(notion: NotionClient, config: VeraConfig) -> list[Task]:
    """
    Fetch active tasks from Notion and parse into Task objects.
    Only fetches tasks with status in active or blocked groups.
    """
    fields = config.tasks.fields
    groups = config.tasks.status_groups
    all_statuses = groups.active + groups.blocked

    # Build OR filter for active statuses
    status_filters = [
        {"property": fields.status, "select": {"equals": s}}
        for s in all_statuses
    ]

    notion_filter = {"or": status_filters} if len(status_filters) > 1 else status_filters[0]

    raw_pages = await notion.query_database(
        config.tasks.database_id,
        filter=notion_filter,
    )

    tasks = []
    for page in raw_pages:
        props = page.get("properties", {})

        # Extract tags (multi_select) if field configured
        tags = []
        if fields.tags:
            tags = NotionClient.extract_multi_select(props, fields.tags)

        task = Task(
            page_id=page["id"],
            title=NotionClient.extract_title(props, fields.title),
            status=NotionClient.extract_select(props, fields.status),
            deadline=NotionClient.extract_date(props, fields.deadline),
            priority=NotionClient.extract_number(props, fields.priority),
            project=NotionClient.extract_rich_text(props, fields.project) if fields.project else "",
            tags=tags,
            last_edited=page.get("last_edited_time", ""),
            current_urgency=NotionClient.extract_number(props, fields.urgency),
        )
        tasks.append(task)

    logger.info(f"Collected {len(tasks)} active tasks")
    return tasks


# ============================================================
# Urgency Calculator
# ============================================================

def calculate_urgency(task: Task, config: VeraConfig) -> float:
    """
    Calculate urgency score (0-100) for a single task.

    Components (configurable weights):
    - deadline_proximity: 0-100 based on how close/past the deadline is
    - priority_level: maps user priority (1-5) to 0-100
    - staleness: how long since the task was last edited
    - dependency_count: placeholder (0 for v1.0)
    """
    weights = config.scoring.urgency_weights
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz).date()

    # --- Deadline proximity ---
    deadline_score = 0.0
    if task.deadline:
        try:
            dl = date.fromisoformat(task.deadline[:10])
            days_until = (dl - now).days

            if days_until < 0:
                # Past deadline — maximum urgency
                deadline_score = 100.0
            elif days_until == 0:
                deadline_score = 95.0
            elif days_until == 1:
                deadline_score = 85.0
            elif days_until <= 3:
                deadline_score = 70.0
            elif days_until <= 7:
                deadline_score = 50.0
            elif days_until <= 14:
                deadline_score = 30.0
            elif days_until <= 30:
                deadline_score = 15.0
            else:
                deadline_score = 5.0
        except (ValueError, TypeError):
            deadline_score = 25.0  # Unparseable deadline → moderate urgency
    else:
        deadline_score = 25.0  # No deadline → moderate baseline

    # --- Priority level ---
    priority_score = 0.0
    if task.priority is not None:
        # Assume priority 1-5 where 5 = highest
        priority_score = min(max(task.priority, 1), 5) * 20  # 1→20, 5→100
    else:
        priority_score = 40.0  # No priority set → moderate

    # --- Staleness ---
    staleness_score = 0.0
    if task.last_edited:
        try:
            last_edit = datetime.fromisoformat(
                task.last_edited.replace("Z", "+00:00")
            ).date()
            days_stale = (now - last_edit).days

            if days_stale <= 1:
                staleness_score = 10.0
            elif days_stale <= 3:
                staleness_score = 30.0
            elif days_stale <= 7:
                staleness_score = 50.0
            elif days_stale <= 14:
                staleness_score = 70.0
            else:
                staleness_score = 90.0
        except (ValueError, TypeError):
            staleness_score = 40.0
    else:
        staleness_score = 40.0

    # --- Dependency count (v1.0: always 0) ---
    dependency_score = 0.0

    # --- Weighted sum ---
    urgency = (
        weights.deadline_proximity * deadline_score
        + weights.priority_level * priority_score
        + weights.staleness * staleness_score
        + weights.dependency_count * dependency_score
    )

    return round(min(max(urgency, 0), 100), 1)


# ============================================================
# Batch update urgency back to Notion
# ============================================================

async def update_urgency_scores(
    notion: NotionClient,
    config: VeraConfig,
    tasks: list[Task],
) -> None:
    """
    Calculate urgency for all tasks and write back to Notion.
    Only updates tasks whose urgency actually changed.
    """
    urgency_field = config.tasks.fields.urgency
    if not urgency_field:
        logger.info("No urgency field configured, skipping urgency update")
        return

    updates = []
    for task in tasks:
        task.computed_urgency = calculate_urgency(task, config)

        # Only update if changed (avoids unnecessary API calls)
        if task.current_urgency != task.computed_urgency:
            updates.append((
                task.page_id,
                {urgency_field: NotionClient.prop_number(task.computed_urgency)},
            ))

    if updates:
        logger.info(f"Updating urgency for {len(updates)}/{len(tasks)} tasks")
        await notion.batch_update_pages(updates)
    else:
        logger.info("All urgency scores up to date")
