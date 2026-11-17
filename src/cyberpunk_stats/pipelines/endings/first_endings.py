"""First-ending distributions, TheWorld co-unlocks, route availability, and the Devil total."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ...domain.constants import (CO_SYNC_ENDINGS, COMPLETION, MAIN_ENDINGS, PANAM_MARKER, PL_ENDINGS,
                                 ROGUE_MARKER, SWEEP_WINDOW_S, SYNC_GRACE_S, TRACKS, UNMARKED)
from .common import pct


def track_stats(recs: list[dict[str, Any]], track: str) -> dict[str, Any]:
    cfg, p = TRACKS[track], f"{track}_"
    endings = cfg["endings"]
    completed = [r for r in recs if r[p + "completed"]]
    strict = [r for r in completed if not r[p + "offline_sync_tie"]]
    n = len(strict)

    first_counts = Counter(r[p + "first_ending"] for r in strict)
    unlock_counts = {a: sum(1 for r in strict if r["unlock_timestamps"][a]) for a in endings + cfg["extra"]}
    gap = {}
    for a in endings:
        fp, up = pct(first_counts[a], n), pct(unlock_counts[a], n)
        gap[a] = {"first_ending_pct": fp, "unlock_pct": up,
                  "inflation_pp": round(up - fp, 2) if fp is not None else None,
                  "inflation_ratio": round(up / fp, 2) if fp else None}

    trans: dict[str, Any] = {}
    by_first = defaultdict(list)
    for r in strict:
        by_first[r[p + "first_ending"]].append(r)
    for f, rs in sorted(by_first.items()):
        tt = Counter(r[p + "transition_type"] or "no_second_ending" for r in rs)
        within = {}
        for e in endings:
            if e == f:
                continue
            k = sum(1 for r in rs if r["unlock_timestamps"][e] is not None
                    and 0 < r["unlock_timestamps"][e] - r[p + "first_ending_time"] < SWEEP_WINDOW_S)
            within[e] = {"count": k, "pct": pct(k, len(rs))}
        trans[f] = {"n": len(rs),
                    "transition_types": {k: {"count": v, "pct": pct(v, len(rs))} for k, v in tt.items()},
                    "second_ending": dict(Counter(r[p + "second_ending"] for r in rs if r[p + "second_ending"])),
                    "unlocked_within_4h_of_first": within}

    return {"title": cfg["title"], "completed_runs": len(completed), "offline_sync_ties": len(completed) - n,
            "strict_sample_n": n,
            "first_ending_distribution": {k: {"count": v, "pct": pct(v, n)} for k, v in first_counts.most_common()},
            "unlock_rates": {a: {"count": c, "pct": pct(c, n)} for a, c in unlock_counts.items()},
            "first_vs_unlock_gap": gap, "transitions": trans}


def world_cosync(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Does each ending unlock TheWorld? For players whose first ending is E, bucket where TheWorld
    sits relative to E. A real trigger shows ~100% within_grace.

    Main endings: first among main endings only (The Tower always follows a PL ending, so "first of
    all" would leave its row empty). King endings: first of all nine, so TheWorld can't already
    exist from a main ending."""
    all_endings = MAIN_ENDINGS + PL_ENDINGS
    out = {}
    for e in all_endings:
        rivals = MAIN_ENDINGS if e in MAIN_ENDINGS else all_endings
        b = Counter()
        for r in recs:
            ts = r["unlock_timestamps"]
            et = ts[e]
            if et is None:
                continue
            others = [ts[o] for o in rivals if o != e and ts[o] is not None]
            if others and min(others) <= et:  # not this player's first ending (or tied)
                continue
            w = ts[COMPLETION]
            b["no_world" if w is None else "within_grace" if abs(w - et) <= SYNC_GRACE_S
              else "world_earlier" if w < et
              else "world_later_lt_2h" if w - et < 7200 else "world_later_ge_2h"] += 1
        n = sum(b.values())
        out[e] = {"n": n, **{k: {"count": b[k], "pct": pct(b[k], n)}
                             for k in ["within_grace", "world_later_lt_2h", "world_later_ge_2h",
                                       "world_earlier", "no_world"]}}
    return out


def route_availability(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Had the player finished Panam's / Rogue's questlines before their first main ending?
    Without Panam's, TheStar wasn't available; without either, nearly all players end on The Devil."""
    out: dict[str, Any] = {}
    by_first = defaultdict(list)
    for r in recs:
        if r["main_completed"] and not r["main_offline_sync_tie"]:
            by_first[r["main_first_ending"]].append(r)
    for f in MAIN_ENDINGS + [UNMARKED]:
        rs = by_first.get(f, [])
        c = Counter()
        for r in rs:
            ft = r["main_first_ending_time"]
            had = lambda a: bool(r["raw_achievements"].get(a)) and r["raw_achievements"][a] <= ft + SYNC_GRACE_S
            pm, rg = had(PANAM_MARKER), had(ROGUE_MARKER)
            c["panam"] += pm
            c["rogue"] += rg
            c["neither"] += not (pm or rg)
            if not (pm or rg) and r["main_second_ending"] is None:
                c["neither_no_later_ending"] += 1
        out[f] = {"n": len(rs), **{k: {"count": c[k], "pct": pct(c[k], len(rs))}
                                   for k in ["panam", "rogue", "neither", "neither_no_later_ending"]}}
    return out


UNMARKED_BUCKETS = ["no_named_ending", "named_not_devil", "devil_lt_4h", "devil_4h_to_24h", "devil_ge_24h"]


def unmarked_breakdown(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """What follows an unmarked first ending? Takemura-dead Devil players can reload into the other
    named endings but never TheDevil from that save, so a later TheDevil points to a different save,
    a tool-assisted unlock, or something other than Takemura-dead Devil."""
    rs = [r for r in recs if r["main_first_ending"] == UNMARKED and not r["main_offline_sync_tie"]]
    b, flagged = Counter(), Counter()
    for r in rs:
        ts, ft = r["unlock_timestamps"], r["main_first_ending_time"]
        if ts["TheDevil"] is not None:
            gap = ts["TheDevil"] - ft
            k = "devil_lt_4h" if gap < SWEEP_WINDOW_S else "devil_4h_to_24h" if gap < 86400 else "devil_ge_24h"
        elif any(ts[e] is not None for e in MAIN_ENDINGS):
            k = "named_not_devil"
        else:
            k = "no_named_ending"
        b[k] += 1
        flagged[k] += r["suspect"]
    return {"n": len(rs), "buckets": {k: {"count": b[k], "pct": pct(b[k], len(rs)), "flagged": flagged[k]}
                                       for k in UNMARKED_BUCKETS}}


def glitch_estimate(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure how often an achievement silently fails, from two cases where one is guaranteed:
    TheWorld alongside a TheStar/TheSun/Temperance credits roll, and Life of the Road (PANAM_MARKER)
    before TheStar, which requires Panam's questline."""
    main = [r for r in recs if r["main_completed"] and not r["main_offline_sync_tie"]]
    co = [r for r in main if r["main_first_ending"] in CO_SYNC_ENDINGS]
    world_miss = lambda r: (r["unlock_timestamps"][COMPLETION] is None
                            or abs(r["unlock_timestamps"][COMPLETION] - r["main_first_ending_time"]) > SYNC_GRACE_S)
    ss = [r for r in co if r["main_first_ending"] in ("TheStar", "TheSun")]
    star = [r for r in co if r["main_first_ending"] == "TheStar"]
    p_never = sum(1 for r in star if not r["raw_achievements"].get(PANAM_MARKER))
    p_later = sum(1 for r in star if r["raw_achievements"].get(PANAM_MARKER)
                  and r["raw_achievements"][PANAM_MARKER] > r["main_first_ending_time"] + SYNC_GRACE_S)
    miss_all, miss_ss = sum(map(world_miss, co)), sum(map(world_miss, ss))
    rate = lambda k, n: k / n if n else 0.0
    low, high = rate(miss_ss, len(ss)), rate(p_never + p_later, len(star))
    return {"co_sync_first_endings": len(co),
            "world_missing_star_sun": {"count": miss_ss, "n": len(ss), "pct": pct(miss_ss, len(ss))},
            "world_missing_star_sun_temperance": {"count": miss_all, "n": len(co), "pct": pct(miss_all, len(co))},
            "star_without_panam": {"never": p_never, "later": p_later, "n": len(star),
                                   "pct": pct(p_never + p_later, len(star))},
            "failure_rate_low_pct": round(100 * low, 2), "failure_rate_high_pct": round(100 * high, 2),
            "expected_glitched_low": round(low * len(co)), "expected_glitched_high": round(high * len(co))}


def add_devil_total(main: dict[str, Any], recs: list[dict[str, Any]]) -> None:
    # The Devil with Takemura dead doesn't unlock TheDevil, so its players land in UNMARKED.
    # UNMARKED also holds ending achievements that failed to pop; glitch_estimate() bounds how many.
    fd, n = main["first_ending_distribution"], main["strict_sample_n"]
    devil = fd.get("TheDevil", {}).get("count", 0)
    no_ach = fd.get(UNMARKED, {}).get("count", 0)
    g = glitch_estimate(recs)
    total = devil + no_ach
    lo = max(devil, total - g["expected_glitched_high"])
    hi = max(devil, total - g["expected_glitched_low"])
    main["devil_total"] = {"achievement_count": devil, "achievement_pct": pct(devil, n),
                           "no_achievement_count": no_ach, "no_achievement_pct": pct(no_ach, n),
                           "total_count": total, "total_pct": pct(total, n),
                           "glitch_estimate": g,
                           "adjusted_low_count": lo, "adjusted_low_pct": pct(lo, n),
                           "adjusted_high_count": hi, "adjusted_high_pct": pct(hi, n)}
