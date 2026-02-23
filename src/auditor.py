"""
Audit engine — detects gaps, patterns, and risks in the user's data.

Things Vera catches that the user might miss:
- Tasks without deadlines
- Tasks stuck too long in one status
- Missing daily check-ins
- Energy trends (declining patterns)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config import VeraConfig

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Collection of detected gaps and observations."""
    warnings: list[str] = field(default_factory=list)    # Needs attention
    observations: list[str] = field(default_factory=list)  # Nice to know
    suggestions: list[str] = field(default_factory=list)   # Improvement ideas


def audit_gaps(collected: dict, config: VeraConfig) -> AuditResult:
    """
    Analyze collected data for gaps and patterns.

    Returns an AuditResult with categorized findings.
    """
    result = AuditResult()
    tasks = collected.get("tasks", [])

    if not tasks:
        return result

    # --- Tasks without deadlines ---
    no_deadline = [t for t in tasks if not t.deadline]
    if len(no_deadline) > 3:
        result.warnings.append(
            f"{len(no_deadline)} tasks have no deadline set. "
            f"Top ones: {', '.join(t.title[:30] for t in no_deadline[:3])}"
        )

    # --- Tasks stale for 7+ days ---
    tz = ZoneInfo(config.timezone)
    now = datetime.now(tz)
    stale_tasks = []
    for t in tasks:
        if t.last_edited:
            try:
                last = datetime.fromisoformat(t.last_edited.replace("Z", "+00:00"))
                if (now - last).days >= 7:
                    stale_tasks.append(t)
            except (ValueError, TypeError):
                pass

    if stale_tasks:
        result.warnings.append(
            f"{len(stale_tasks)} tasks haven't been touched in 7+ days: "
            f"{', '.join(t.title[:30] for t in stale_tasks[:3])}"
        )

    # --- Missing daily check-ins ---
    checks = collected.get("daily_check")
    if checks is not None and isinstance(checks, list):
        if len(checks) < 3:
            result.observations.append(
                f"Only {len(checks)} check-ins in the last 7 days. "
                f"Consistent tracking helps Vera give better insights."
            )

        # Energy trend detection
        if len(checks) >= 3:
            energies = [c.energy for c in checks if c.energy is not None]
            if len(energies) >= 3:
                recent = energies[:3]  # most recent (sorted desc)
                if all(r <= 2 for r in recent):
                    result.warnings.append(
                        "Energy has been low (≤2) for the last 3 days. "
                        "Consider adjusting workload or rest."
                    )
                elif len(energies) >= 5:
                    first_half = sum(energies[len(energies)//2:]) / len(energies[len(energies)//2:])
                    second_half = sum(energies[:len(energies)//2]) / len(energies[:len(energies)//2])
                    if second_half < first_half - 0.5:
                        result.observations.append(
                            f"Energy trending down: {first_half:.1f} → {second_half:.1f} avg."
                        )

    # --- High urgency overload ---
    high_urgency = [t for t in tasks if t.computed_urgency >= 70]
    if len(high_urgency) > 5:
        result.suggestions.append(
            f"{len(high_urgency)} tasks have urgency ≥70. "
            f"Consider deferring or delegating some."
        )

    total = len(result.warnings) + len(result.observations) + len(result.suggestions)
    logger.info(f"Audit: {total} findings ({len(result.warnings)} warnings)")

    return result
