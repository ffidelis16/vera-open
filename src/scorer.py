"""
Scoring engine — calculates daily scores and streaks.

Full implementation in Phase 3. Currently returns structured placeholder data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.config import VeraConfig

logger = logging.getLogger(__name__)


@dataclass
class DailyScores:
    """Computed scores for today's briefing."""
    productivity_score: float = 0.0       # 0-100
    consistency_streak: int = 0           # days
    tasks_completed_today: int = 0
    tasks_completed_week: int = 0
    overdue_count: int = 0
    avg_energy_7d: Optional[float] = None
    avg_mood_7d: Optional[float] = None
    avg_focus_7d: Optional[float] = None
    trends: dict = field(default_factory=dict)


def calculate_scores(collected: dict, config: VeraConfig) -> DailyScores:
    """
    Calculate daily scores from collected data.

    Args:
        collected: Dict of {database_name: data} from collectors.
        config: Vera configuration.

    Returns:
        DailyScores with computed metrics.
    """
    scores = DailyScores()

    tasks = collected.get("tasks", [])
    if tasks:
        scores.overdue_count = sum(
            1 for t in tasks
            if t.deadline and t.computed_urgency >= 95
        )

    checks = collected.get("daily_check")
    if checks and isinstance(checks, list) and len(checks) > 0:
        energies = [c.energy for c in checks if c.energy is not None]
        moods = [c.mood for c in checks if c.mood is not None]
        focuses = [c.focus for c in checks if c.focus is not None]

        if energies:
            scores.avg_energy_7d = round(sum(energies) / len(energies), 1)
        if moods:
            scores.avg_mood_7d = round(sum(moods) / len(moods), 1)
        if focuses:
            scores.avg_focus_7d = round(sum(focuses) / len(focuses), 1)

    logger.info(f"Scores: overdue={scores.overdue_count}, streak={scores.consistency_streak}")
    return scores
