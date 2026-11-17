"""Completionists and the story-progress funnel."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

from ...domain.constants import MAIN_ENDINGS, PL_ENDINGS, SWEEP_WINDOW_S
from .common import pct

COMPLETION_SETS = {
    "main_all": ("All 5 main endings", "main", MAIN_ENDINGS),
    "main_base_four": ("All 4 base-game endings (TheTower excluded)", "main",
                       [e for e in MAIN_ENDINGS if e != "TheTower"]),
    "pl_all": ("All 4 King endings", "pl", PL_ENDINGS),
    "everything": ("All 9 endings", "both", MAIN_ENDINGS + PL_ENDINGS),
}


def completionists(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Players who unlocked every ending achievement in a set. Base = finishers of that track (both tracks
    for the combined set). `span` = first to last unlock in the set: under SWEEP_WINDOW_S means one
    save-reload sweep, not separate playthroughs."""
    bases = {"main": [r for r in recs if r["main_completed"]],
             "pl": [r for r in recs if r["pl_completed"]]}
    bases["both"] = [r for r in bases["main"] if r["pl_completed"]]
    out: dict[str, Any] = {"endings_unlocked": {}}
    for track, endings in (("main", MAIN_ENDINGS), ("pl", PL_ENDINGS)):
        c = Counter(sum(1 for e in endings if r["unlock_timestamps"][e]) for r in bases[track])
        out["endings_unlocked"][track] = {"n": len(bases[track]),
                                          "counts": {k: {"count": c[k], "pct": pct(c[k], len(bases[track]))}
                                                     for k in range(len(endings) + 1)}}
    sets = {}
    for key, (_, track, endings) in COMPLETION_SETS.items():
        base = bases[track]
        done = [r for r in base if all(r["unlock_timestamps"][e] for e in endings)]
        clean_base = [r for r in base if not r["suspect"]]
        clean = [r for r in done if not r["suspect"]]
        spans = [max(r["unlock_timestamps"][e] for e in endings) - min(r["unlock_timestamps"][e] for e in endings)
                 for r in clean]
        hours = [r["playtime_forever"] / 60 for r in clean]
        sets[key] = {"base_n": len(base), "count": len(done), "pct": pct(len(done), len(base)),
                     "flagged": len(done) - len(clean), "flagged_pct": pct(len(done) - len(clean), len(done)),
                     "clean_base_n": len(clean_base), "clean_count": len(clean),
                     "clean_pct": pct(len(clean), len(clean_base)),
                     "median_playtime_h": round(statistics.median(hours), 1) if hours else None,
                     "one_sweep_pct": pct(sum(1 for x in spans if x < SWEEP_WINDOW_S), len(spans)),
                     "median_span_days": round(statistics.median(spans) / 86400, 1) if spans else None}
    out["sets"] = sets
    return out


def story_funnel(recs: list[dict[str, Any]], milestones: list[tuple[str, str]], track: str,
                 finish_label: str) -> dict[str, Any]:
    """How far players got. `base` = public profiles for the main game; for PL (DLC ownership isn't
    visible) it's players who reached the first milestone. Non-finishers are bucketed by the furthest
    milestone they reached."""
    if track == "main":
        base = recs
    else:
        base = [r for r in recs if r["raw_achievements"].get(milestones[0][1]) or r[f"{track}_completed"]]
    stages = [(lbl, lambda r, a=a: bool(r["raw_achievements"].get(a)), a) for lbl, a in milestones]
    stages.append((finish_label, lambda r: r[f"{track}_completed"], None))
    out_stages, prev = [], len(base)
    for lbl, hit, a in stages:
        k = sum(1 for r in base if hit(r))
        out_stages.append({"stage": lbl, "achievement": a, "reached": k, "pct_of_base": pct(k, len(base)),
                           "pct_of_previous": pct(k, prev)})
        prev = k
    drop = defaultdict(list)
    for r in base:
        if r[f"{track}_completed"]:
            continue
        furthest = "No story milestone"
        for lbl, hit, _ in stages[:-1]:
            if hit(r):
                furthest = lbl
        drop[furthest].append(r)
    nd = sum(len(v) for v in drop.values())
    order = ["No story milestone"] + [lbl for lbl, _, _ in stages[:-1]]
    dropouts = {}
    for lbl in order:
        rs = drop.get(lbl, [])
        pts = [r["playtime_forever"] / 60 for r in rs if r["playtime_forever"]]
        dropouts[lbl] = {"count": len(rs), "pct_of_non_finishers": pct(len(rs), nd),
                         "median_playtime_h": round(statistics.median(pts), 1) if pts else None}
    return {"base_n": len(base), "finished": out_stages[-1]["reached"], "not_finished": nd,
            "stages": out_stages, "stopped_after": dropouts,
            "most_common_stop": max(dropouts, key=lambda k: dropouts[k]["count"]) if nd else None}
