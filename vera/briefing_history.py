"""Histórico de briefings — array circular para evitar repetição."""

import json
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = _REPO_ROOT / "state" / "briefing_history.json"
MAX_ENTRIES = 5
MAX_WORDS_PER_ENTRY = 200


def _truncate(text: str, max_words: int = MAX_WORDS_PER_ENTRY) -> str:
    """Trunca texto para max_words palavras."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def load_history(path: Path | None = None) -> list[dict]:
    """Carrega histórico de briefings."""
    p = path or HISTORY_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(briefing_text: str, path: Path | None = None) -> None:
    """Adiciona briefing ao histórico (circular, max MAX_ENTRIES)."""
    p = path or HISTORY_PATH
    history = load_history(p)

    now = datetime.now(timezone.utc)
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
        "text": _truncate(briefing_text),
    }

    history.append(entry)
    if len(history) > MAX_ENTRIES:
        history = history[-MAX_ENTRIES:]

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def format_for_prompt(path: Path | None = None, max_entries: int = 3) -> str:
    """Formata histórico para injeção no contexto do LLM."""
    history = load_history(path)
    if not history:
        return ""

    recent = history[-max_entries:]
    lines = ["=== BRIEFINGS ANTERIORES (não repita frases nem estrutura) ==="]
    for entry in recent:
        lines.append(f"[{entry['date']}] {entry['text']}")
    lines.append("")

    return "\n".join(lines)
