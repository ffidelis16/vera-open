"""
Prioritization methodology.

Sorts tasks by computed urgency and groups them into actionable tiers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config import VeraConfig

logger = logging.getLogger(__name__)


@dataclass
class PriorityList:
    """Prioritized task groups for the briefing."""
    top_3: list          # Must-do today
    should_do: list      # Important but not critical
    blocked: list        # Waiting on something
    overdue: list        # Past deadline


def prioritize(tasks: list, config: VeraConfig) -> PriorityList:
    """
    Group and sort tasks into priority tiers.

    Tier logic:
    - overdue: urgency >= 95 (past deadline)
    - top_3: highest urgency among non-overdue active tasks
    - should_do: next tier
    - blocked: tasks in blocked status group
    """
    blocked_statuses = set(s.lower() for s in config.tasks.status_groups.blocked)

    overdue = []
    blocked = []
    active = []

    for task in tasks:
        if task.status.lower() in blocked_statuses:
            blocked.append(task)
        elif task.computed_urgency >= 95:
            overdue.append(task)
        else:
            active.append(task)

    # Sort active by urgency descending
    active.sort(key=lambda t: t.computed_urgency, reverse=True)
    overdue.sort(key=lambda t: t.computed_urgency, reverse=True)

    result = PriorityList(
        top_3=active[:3],
        should_do=active[3:8],
        blocked=blocked,
        overdue=overdue,
    )

    logger.info(
        f"Priorities: top_3={len(result.top_3)}, "
        f"should_do={len(result.should_do)}, "
        f"overdue={len(result.overdue)}, "
        f"blocked={len(result.blocked)}"
    )

    return result
