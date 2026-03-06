"""last_run.json — observabilidade de cada execução."""

import json
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
LAST_RUN_PATH = _REPO_ROOT / "state" / "last_run.json"


def save_last_run(mode: str, stats: dict, path: Path | None = None) -> None:
    """Grava snapshot da última execução."""
    p = path or LAST_RUN_PATH

    entry = {
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **stats,
    }

    # Carrega histórico existente (por modo)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data[mode] = entry

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   [last_run] Salvo em {p.name} ({mode})")
