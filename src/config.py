"""
Configuration system for Vera Open.

Loads config.yaml → validates with Pydantic → merges with env vars.
Any config error is caught at startup, not at runtime.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# ============================================================
# Field Mapping Models
# ============================================================


class TaskFields(BaseModel):
    """Maps user's Notion property names to Vera's internal names."""
    title: str = "Name"
    status: str = "Status"
    deadline: str = "Deadline"
    priority: str = "Priority"
    urgency: str = "Urgência Real"
    project: str = ""
    tags: str = ""


class TaskStatusGroups(BaseModel):
    """Groups status values into semantic categories."""
    active: list[str] = ["To Do", "Doing", "In Progress"]
    done: list[str] = ["Done", "Complete"]
    blocked: list[str] = ["Blocked", "Waiting"]


class DailyCheckFields(BaseModel):
    date: str = "Date"
    energy: str = "Energy"
    mood: str = "Mood"
    focus: str = "Focus"
    sleep_quality: str = "Sleep"
    notes: str = "Notes"


class PipelineFields(BaseModel):
    title: str = "Name"
    status: str = "Status"
    value: str = "Value"
    next_action: str = "Next Action"
    deadline: str = "Deadline"


class PipelineStatusGroups(BaseModel):
    active: list[str] = ["Lead", "Proposal", "Negotiation"]
    won: list[str] = ["Won", "Closed"]
    lost: list[str] = ["Lost"]


class EnergyTimingFields(BaseModel):
    time_block: str = "Time Block"
    energy_level: str = "Energy"
    best_for: str = "Best For"


# ============================================================
# Database Models
# ============================================================


class TasksConfig(BaseModel):
    """Tasks database — REQUIRED."""
    database_id: str
    fields: TaskFields = TaskFields()
    status_groups: TaskStatusGroups = TaskStatusGroups()

    @field_validator("database_id")
    @classmethod
    def validate_database_id(cls, v: str) -> str:
        v = v.strip().replace("-", "")
        if not v:
            raise ValueError(
                "tasks.database_id is required. "
                "Open your Tasks database in Notion, copy the URL, "
                "and paste the 32-character ID."
            )
        if len(v) != 32:
            raise ValueError(
                f"tasks.database_id should be 32 hex characters, got {len(v)}. "
                f"Check your Notion URL — the ID comes before '?v='."
            )
        return v


class DailyCheckConfig(BaseModel):
    """Daily check-in database — REQUIRED but can be disabled."""
    enabled: bool = True
    database_id: str = ""
    fields: DailyCheckFields = DailyCheckFields()

    @model_validator(mode="after")
    def validate_enabled_has_id(self) -> "DailyCheckConfig":
        if self.enabled and not self.database_id.strip():
            raise ValueError(
                "daily_check is enabled but database_id is empty. "
                "Either set the database_id or set enabled: false."
            )
        return self


class PipelineConfig(BaseModel):
    """Pipeline tracking — OPTIONAL."""
    enabled: bool = False
    database_id: str = ""
    fields: PipelineFields = PipelineFields()
    status_groups: PipelineStatusGroups = PipelineStatusGroups()

    @model_validator(mode="after")
    def validate_enabled_has_id(self) -> "PipelineConfig":
        if self.enabled and not self.database_id.strip():
            raise ValueError(
                "pipeline is enabled but database_id is empty. "
                "Either set the database_id or set enabled: false."
            )
        return self


class EnergyTimingConfig(BaseModel):
    """Energy timing — OPTIONAL."""
    enabled: bool = False
    database_id: str = ""
    fields: EnergyTimingFields = EnergyTimingFields()

    @model_validator(mode="after")
    def validate_enabled_has_id(self) -> "EnergyTimingConfig":
        if self.enabled and not self.database_id.strip():
            raise ValueError(
                "energy_timing is enabled but database_id is empty. "
                "Either set the database_id or set enabled: false."
            )
        return self


# ============================================================
# Top-Level Config Sections
# ============================================================


class PersonaConfig(BaseModel):
    preset: Literal["executive", "coach", "custom"] = "executive"
    custom_prompt: Optional[str] = None

    @model_validator(mode="after")
    def validate_custom_has_prompt(self) -> "PersonaConfig":
        if self.preset == "custom" and not self.custom_prompt:
            raise ValueError(
                "persona.preset is 'custom' but no custom_prompt provided."
            )
        return self


class ScheduleConfig(BaseModel):
    daily_briefing: str = "09:00"
    weekly_review_day: str = "saturday"
    weekly_review_time: str = "10:00"

    @field_validator("weekly_review_day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        valid = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if v.lower() not in valid:
            raise ValueError(f"weekly_review_day must be one of {valid}, got '{v}'")
        return v.lower()


class UrgencyWeights(BaseModel):
    deadline_proximity: float = 0.4
    priority_level: float = 0.3
    staleness: float = 0.2
    dependency_count: float = 0.1

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "UrgencyWeights":
        total = (
            self.deadline_proximity
            + self.priority_level
            + self.staleness
            + self.dependency_count
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Urgency weights must sum to 1.0, got {total:.2f}. "
                f"Adjust the values in scoring.urgency_weights."
            )
        return self


class StreakConfig(BaseModel):
    enabled: bool = True
    metric: str = "tasks_completed"


class ScoringConfig(BaseModel):
    urgency_weights: UrgencyWeights = UrgencyWeights()
    streak: StreakConfig = StreakConfig()


class DebugConfig(BaseModel):
    dry_run: bool = False
    verbose: bool = False


# ============================================================
# Secrets — loaded from environment variables
# ============================================================


class Secrets(BaseModel):
    """Loaded exclusively from environment variables. Never in config.yaml."""
    notion_token: str
    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str

    @field_validator("notion_token")
    @classmethod
    def validate_notion_token(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("ntn_", "secret_")):
            logger.warning(
                "NOTION_TOKEN doesn't start with 'ntn_' or 'secret_'. "
                "Make sure you're using an integration token, not a session cookie."
            )
        return v

    @field_validator("telegram_chat_id")
    @classmethod
    def validate_chat_id(cls, v: str) -> str:
        v = v.strip()
        if not v.lstrip("-").isdigit():
            raise ValueError(
                f"TELEGRAM_CHAT_ID must be numeric, got '{v}'. "
                f"Send /start to your bot, then check getUpdates."
            )
        return v


# ============================================================
# Root Config
# ============================================================


class VeraConfig(BaseModel):
    """Root configuration model. Single source of truth."""
    name: str = "Vera"
    language: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    persona: PersonaConfig = PersonaConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    tasks: TasksConfig
    daily_check: DailyCheckConfig = DailyCheckConfig(enabled=False)
    pipeline: PipelineConfig = PipelineConfig()
    energy_timing: EnergyTimingConfig = EnergyTimingConfig()
    scoring: ScoringConfig = ScoringConfig()
    debug: DebugConfig = DebugConfig()
    secrets: Optional[Secrets] = None

    @property
    def enabled_databases(self) -> list[str]:
        """Returns list of enabled database names."""
        dbs = ["tasks"]
        if self.daily_check.enabled:
            dbs.append("daily_check")
        if self.pipeline.enabled:
            dbs.append("pipeline")
        if self.energy_timing.enabled:
            dbs.append("energy_timing")
        return dbs


# ============================================================
# Loaders
# ============================================================


def load_secrets() -> Secrets:
    """Load secrets from environment variables."""
    env_map = {
        "notion_token": "NOTION_TOKEN",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
    }
    values = {}
    missing = []
    for field, env_var in env_map.items():
        val = os.environ.get(env_var, "").strip()
        if not val:
            missing.append(env_var)
        values[field] = val

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env (local) or GitHub Secrets (CI)."
        )

    return Secrets(**values)


def load_config(path: str | Path = "config.yaml") -> VeraConfig:
    """
    Load and validate configuration from YAML file + environment.

    Returns a fully validated VeraConfig with secrets attached.
    Raises descriptive errors if anything is wrong.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found at '{path}'. "
            f"Copy config.example.yaml to config.yaml and fill in your values."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or not isinstance(raw, dict):
        raise ValueError(
            f"Config file '{path}' is empty or not valid YAML. "
            f"Check for syntax errors."
        )

    # Parse config (Pydantic validates everything)
    config = VeraConfig(**raw)

    # Load and attach secrets
    config.secrets = load_secrets()

    logger.info(
        f"Config loaded: {config.name} | "
        f"Databases: {', '.join(config.enabled_databases)} | "
        f"Persona: {config.persona.preset}"
    )

    return config


def validate_only(path: str | Path = "config.yaml") -> bool:
    """
    Validate config without running anything.
    Returns True if valid, raises with details if not.
    """
    try:
        config = load_config(path)
        print(f"✅ Config válida!")
        print(f"   Nome: {config.name}")
        print(f"   Idioma: {config.language}")
        print(f"   Timezone: {config.timezone}")
        print(f"   Persona: {config.persona.preset}")
        print(f"   Databases ativos: {', '.join(config.enabled_databases)}")
        print(f"   Dry run: {config.debug.dry_run}")
        return True
    except Exception as e:
        print(f"❌ Erro na configuração:\n   {e}")
        return False
