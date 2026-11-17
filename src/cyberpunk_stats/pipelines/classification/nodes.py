"""One record per public profile: classified endings plus flags for tool-assisted-looking unlocks."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from ...domain.classify import classify, to_canonical
from ...domain.constants import TRACKED


def max_burst(times: list[int], anchors: list[int], window_s: int) -> int:
    """Most achievements unlocked within `window_s` seconds, over windows that contain an anchor."""
    ts = sorted(times)
    best, j = 0, 0
    for i in range(len(ts)):
        while ts[i] - ts[j] > window_s:
            j += 1
        if any(ts[j] <= a <= ts[i] for a in anchors):
            best = max(best, i - j + 1)
    return best


def build_records(players: pd.DataFrame, mapping: dict[str, str], flags: dict[str, int]) -> list[dict[str, Any]]:
    """`flags`: burst_count achievements within burst_window_s seconds (with an ending or TheWorld among
    them), or an ending on an account with under low_playtime_mins lifetime playtime, mark a record suspect."""
    recs = []
    for sid, pt, raw_json in zip(players["steamid"].tolist(), players["playtime_forever"].tolist(),
                                 players["achievements_json"].tolist()):
        pt = None if pd.isna(pt) else int(pt)
        raw = json.loads(raw_json)
        canon = to_canonical(raw, mapping)
        cls = classify(canon)
        anchors = [v for k, v in canon.items() if k in TRACKED and v]
        burst = max_burst([v for v in raw.values() if v], anchors, flags["burst_window_s"])
        flag_burst = burst >= flags["burst_count"]
        flag_low = cls["completed"] and (pt or 0) < flags["low_playtime_mins"]
        recs.append({"steamid": sid, "playtime_forever": pt,
                     "unlock_timestamps": {k: canon.get(k) for k in TRACKED}, **cls,
                     "max_burst": burst, "flag_burst": flag_burst, "flag_low_playtime": flag_low,
                     "suspect": flag_burst or flag_low, "raw_achievements": raw})
    return recs


def clean_records(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in recs if not r["suspect"]]
