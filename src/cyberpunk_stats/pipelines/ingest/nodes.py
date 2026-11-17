"""Turn the checkpoint's SQLite tables into plain Python structures for the rest of the pipeline."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pandas as pd

from ...domain.constants import TRACKED


def decode_state(state: pd.DataFrame) -> dict[str, Any]:
    """The collector's key/value `state` table (JSON-encoded values) as a dict."""
    return {k: json.loads(v) for k, v in zip(state["key"].tolist(), state["value"].tolist())}


def achievement_mapping(run_state: dict[str, Any]) -> dict[str, str]:
    """Canonical name -> Steam apiname, as resolved by the collector from the game schema."""
    mapping = run_state.get("achievement_mapping")
    if not mapping:
        raise ValueError("No achievement mapping in checkpoint; run cyberpunk-stats-collect first.")
    missing = [c for c in TRACKED if c not in mapping]
    if missing:
        raise ValueError(f"Checkpoint mapping lacks {missing}; run cyberpunk-stats-collect --resume to refresh the schema.")
    return mapping


def summarize_candidates(candidates: pd.DataFrame) -> dict[str, Any]:
    """Lookup status counts, and review playtimes (hours) of public vs private profiles."""
    status = candidates["status"].tolist()
    playtime = candidates["playtime_forever"].tolist()
    return {
        "status_counts": dict(Counter(status)),
        "playtime_h": {st: [p / 60 for s, p in zip(status, playtime) if s == st and not pd.isna(p)]
                       for st in ("public", "private")},
    }
