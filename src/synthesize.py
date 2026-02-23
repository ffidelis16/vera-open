"""
Briefing synthesis — builds structured prompt from collected data,
sends to Claude API, and returns formatted HTML for Telegram.
"""

from __future__ import annotations

import logging
from pathlib import Path

import anthropic

from src.config import VeraConfig
from src.scorer import DailyScores
from src.methodology import PriorityList
from src.auditor import AuditResult

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500

# ============================================================
# Preset loader
# ============================================================

PRESETS_DIR = Path(__file__).parent / "presets"


def load_persona_prompt(config: VeraConfig) -> str:
    """Load persona system prompt from preset or custom config."""
    if config.persona.preset == "custom":
        return config.persona.custom_prompt or ""

    preset_path = PRESETS_DIR / f"{config.persona.preset}.txt"
    if preset_path.exists():
        return preset_path.read_text(encoding="utf-8").strip()

    logger.warning(f"Preset '{config.persona.preset}' not found, using executive")
    fallback = PRESETS_DIR / "executive.txt"
    return fallback.read_text(encoding="utf-8").strip() if fallback.exists() else ""


# ============================================================
# Workspace loader
# ============================================================

WORKSPACE_DIR = Path(__file__).parent.parent / "workspace"


def load_user_context() -> str:
    """
    Load workspace/USER.md if it exists.

    This file contains free-form context about the user — who they are,
    what they do, what matters to them. Injected into the system prompt
    so Claude can personalize the briefing without any code changes.

    Returns empty string if file doesn't exist (graceful skip).
    """
    user_file = WORKSPACE_DIR / "USER.md"
    if not user_file.exists():
        logger.debug("No workspace/USER.md found, skipping user context")
        return ""

    content = user_file.read_text(encoding="utf-8").strip()
    if not content:
        return ""

    logger.info(f"Loaded user context: {len(content)} chars from workspace/USER.md")
    return content


# ============================================================
# Prompt builder
# ============================================================

def build_data_block(
    collected: dict,
    scores: DailyScores,
    priorities: PriorityList,
    gaps: AuditResult,
    config: VeraConfig,
) -> str:
    """Build the structured data block that goes into the user message."""
    sections = []

    # --- Tasks overview ---
    tasks = collected.get("tasks", [])
    sections.append(f"## Active Tasks: {len(tasks)}")

    if priorities.overdue:
        overdue_lines = [
            f"  - ⚠️ {t.title} (urgency: {t.computed_urgency:.0f})"
            for t in priorities.overdue[:5]
        ]
        sections.append("### Overdue:\n" + "\n".join(overdue_lines))

    if priorities.top_3:
        top_lines = [
            f"  - {t.title} (urgency: {t.computed_urgency:.0f}, "
            f"deadline: {t.deadline or 'none'}, "
            f"status: {t.status})"
            for t in priorities.top_3
        ]
        sections.append("### Top 3 Today:\n" + "\n".join(top_lines))

    if priorities.should_do:
        should_lines = [
            f"  - {t.title} (urgency: {t.computed_urgency:.0f})"
            for t in priorities.should_do
        ]
        sections.append("### Should Do:\n" + "\n".join(should_lines))

    if priorities.blocked:
        blocked_lines = [
            f"  - {t.title} (status: {t.status})"
            for t in priorities.blocked[:5]
        ]
        sections.append("### Blocked:\n" + "\n".join(blocked_lines))

    # --- Scores ---
    score_parts = [f"Overdue: {scores.overdue_count}"]
    if scores.avg_energy_7d is not None:
        score_parts.append(f"Energy (7d avg): {scores.avg_energy_7d}")
    if scores.avg_mood_7d is not None:
        score_parts.append(f"Mood (7d avg): {scores.avg_mood_7d}")
    if scores.avg_focus_7d is not None:
        score_parts.append(f"Focus (7d avg): {scores.avg_focus_7d}")
    if scores.consistency_streak > 0:
        score_parts.append(f"Streak: {scores.consistency_streak} days")
    sections.append("## Scores\n" + " | ".join(score_parts))

    # --- Daily check (latest) ---
    checks = collected.get("daily_check")
    if checks and isinstance(checks, list) and len(checks) > 0:
        latest = checks[0]
        check_parts = []
        if latest.energy is not None:
            check_parts.append(f"Energy: {latest.energy}/5")
        if latest.mood is not None:
            check_parts.append(f"Mood: {latest.mood}/5")
        if latest.focus is not None:
            check_parts.append(f"Focus: {latest.focus}/5")
        if check_parts:
            sections.append(f"## Latest Check-in ({latest.date})\n" + " | ".join(check_parts))
            if latest.notes:
                sections.append(f"Notes: {latest.notes[:200]}")

    # --- Pipeline ---
    pipeline = collected.get("pipeline")
    if pipeline and isinstance(pipeline, list) and len(pipeline) > 0:
        pipe_lines = [
            f"  - {p['title']} ({p['status']})"
            + (f" — next: {p['next_action'][:50]}" if p.get('next_action') else "")
            for p in pipeline[:5]
        ]
        sections.append("## Pipeline\n" + "\n".join(pipe_lines))

    # --- Audit findings ---
    if gaps.warnings or gaps.observations or gaps.suggestions:
        finding_parts = []
        for w in gaps.warnings:
            finding_parts.append(f"  ⚠️ {w}")
        for o in gaps.observations:
            finding_parts.append(f"  📊 {o}")
        for s in gaps.suggestions:
            finding_parts.append(f"  💡 {s}")
        sections.append("## Audit Findings\n" + "\n".join(finding_parts))

    return "\n\n".join(sections)


def build_user_message(
    data_block: str,
    config: VeraConfig,
) -> str:
    """Build the full user message for the AI."""
    return f"""Generate today's daily briefing based on this data.

{data_block}

---

FORMATTING RULES:
- Output in HTML for Telegram (use <b>, <i>, <code> only — no markdown)
- Language: {config.language}
- Keep under 4000 characters (Telegram limit)
- Structure: greeting → top priorities → context → audit findings → closing
- Be specific: reference actual task names, scores, patterns
- If energy/mood is low, acknowledge it and adapt tone
- No generic motivation — every sentence should reference actual data
"""


# ============================================================
# AI Call
# ============================================================

async def generate_briefing(
    config: VeraConfig,
    collected: dict,
    scores: DailyScores,
    priorities: PriorityList,
    gaps: AuditResult,
) -> str:
    """
    Generate daily briefing via Claude API.

    Returns HTML-formatted string ready for Telegram.
    """
    persona_prompt = load_persona_prompt(config)
    user_context = load_user_context()
    data_block = build_data_block(collected, scores, priorities, gaps, config)
    user_message = build_user_message(data_block, config)

    # Build user context block for system prompt
    user_block = ""
    if user_context:
        user_block = f"""

=== ABOUT THE USER ===
{user_context}
=== END USER CONTEXT ===
"""

    system_prompt = f"""You are {config.name}, a daily briefing assistant.

{persona_prompt}
{user_block}
Your job is to synthesize the user's Notion data into a concise, actionable
morning briefing. Every claim must reference actual data provided.
Use the user context above to personalize tone, references, and priorities.
Output format: HTML for Telegram (only <b>, <i>, <code>, <a> tags).
Language: {config.language}.
"""

    logger.info(f"Calling Claude ({MODEL})...")
    logger.debug(f"System prompt: {len(system_prompt)} chars")
    logger.debug(f"User message: {len(user_message)} chars")

    client = anthropic.AsyncAnthropic(api_key=config.secrets.anthropic_api_key)

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        briefing = ""
        for block in response.content:
            if block.type == "text":
                briefing += block.text

        logger.info(
            f"Briefing generated: {len(briefing)} chars, "
            f"tokens: {response.usage.input_tokens}in/{response.usage.output_tokens}out"
        )

        return briefing.strip()

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        raise
