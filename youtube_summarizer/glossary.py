from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_GLOSSARY_FILE = "data/glossary_terms.json"
_ROLLING_DAYS = 7
_MAX_EVER = 3


def _path(root: Path) -> Path:
    p = root / _GLOSSARY_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(root: Path) -> dict:
    p = _path(root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_skip_terms(root: Path) -> list[str]:
    """Return terms that should be skipped: defined within 7 days OR 3+ times ever."""
    terms = _load(root)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=_ROLLING_DAYS)
    skip = []
    for term, info in terms.items():
        if info.get("count", 0) >= _MAX_EVER:
            skip.append(term)
            continue
        try:
            last = datetime.fromisoformat(info["last_defined_iso"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last >= cutoff:
                skip.append(term)
        except Exception:
            pass
    return skip


def save_new_terms(root: Path, new_terms: list[str]) -> None:
    """Increment count and update timestamp for each newly defined term."""
    if not new_terms:
        return
    terms = _load(root)
    now = datetime.now(timezone.utc).isoformat()
    for term in new_terms:
        key = term.strip()
        if not key:
            continue
        if key in terms:
            terms[key]["count"] = terms[key].get("count", 0) + 1
            terms[key]["last_defined_iso"] = now
        else:
            terms[key] = {"count": 1, "last_defined_iso": now}
    _path(root).write_text(json.dumps(terms, indent=2, ensure_ascii=False), encoding="utf-8")
