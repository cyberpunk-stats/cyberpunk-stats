"""Per-player ending classification from achievement unlock timestamps."""
from __future__ import annotations

from typing import Any

from .constants import (COMPLETION, MAIN_ENDINGS, PL_ENDINGS, SWEEP_WINDOW_S, SYNC_GRACE_S, TRACKED, TRACKS,
                        UNMARKED)

def classify_track(t: dict[str, int], endings: list[str], world: int | None = None) -> dict[str, Any]:
    """First/second ending for one track. `world` enables unmarked-ending detection (main game only)."""
    ending_times = {k: t[k] for k in endings if t.get(k)}
    out: dict[str, Any] = {"completed": bool(ending_times) or world is not None, "first_ending": None,
                           "first_ending_time": None, "second_ending": None, "second_ending_time": None,
                           "delta_seconds": None, "transition_type": None, "offline_sync_tie": False}
    if not out["completed"]:
        return out

    # Identical timestamps between two ending achievements can't come from real play
    # (credits + reload take minutes), so they indicate an offline batch sync.
    vals = list(ending_times.values())
    out["offline_sync_tie"] = len(vals) != len(set(vals))
    min_named = min(vals) if vals else None

    if world is not None and (min_named is None or world < min_named - SYNC_GRACE_S):
        first, ft = UNMARKED, world
    else:
        ft = min_named
        tied = sorted(k for k, v in ending_times.items() if v == ft)
        first = tied[0] if len(tied) == 1 else "Tie:" + "+".join(tied)
    out["first_ending"], out["first_ending_time"] = first, ft

    rest = sorted((v, k) for k, v in ending_times.items() if v > ft)
    if rest:
        st, sk = rest[0]
        out["second_ending"], out["second_ending_time"] = sk, st
        out["delta_seconds"] = st - ft
        out["transition_type"] = "save_reload_sweep" if st - ft < SWEEP_WINDOW_S else "separate_playthrough"
    return out


def classify(t: dict[str, int]) -> dict[str, Any]:
    """t: canonical achievement name -> unlocktime (0/missing = locked). Returns flat main_*/pl_* fields."""
    t = {k: v for k, v in t.items() if k in TRACKED and v}
    world = t.get(COMPLETION)
    if world is not None:
        near = lambda names: any(abs(world - t[k]) <= SYNC_GRACE_S for k in names if k in t)
        # King endings never unlock TheWorld (Phantom Liberty ends mid-game), so a TheWorld timestamp
        # within the grace window of one, with no main ending nearby, is an offline batch sync, not a
        # TheWorld-only main-game ending.
        if near(PL_ENDINGS) and not near(MAIN_ENDINGS):
            world = None
    out: dict[str, Any] = {}
    for track, cfg in TRACKS.items():
        res = classify_track(t, cfg["endings"], world if track == "main" else None)
        out.update({f"{track}_{k}": v for k, v in res.items()})
    out["completed"] = out["main_completed"] or out["pl_completed"]
    return out


def to_canonical(raw: dict[str, int], mapping: dict[str, str]) -> dict[str, int]:
    """Steam apinames -> canonical names, using the mapping resolved from the game schema."""
    return {c: raw[api] for c, api in mapping.items() if api in raw}
