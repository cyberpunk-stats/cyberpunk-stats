"""Player groups: Phantom Liberty timing vs main ending, rushers, and their playtime."""
from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

from ...domain.constants import (CO_SYNC_ENDINGS, MAIN_ORDER, PANAM_MARKER, PL_ENDINGS, PL_RELEASE_TS,
                                 ROGUE_MARKER, SYNC_GRACE_S, UNMARKED)
from .common import pct

PL_GROUPS = {"pl_before": "PL finished before first main ending", "pl_after": "PL finished after first main ending",
             "no_pl_ending": "No PL ending"}
ROUTE_GROUPS = {"both": "Both questlines", "panam_only": "Panam only", "rogue_only": "Rogue only",
                "neither": "Neither"}


def _routes(r: dict[str, Any]) -> str:
    ft, ra = r["main_first_ending_time"], r["raw_achievements"]
    had = lambda a: bool(ra.get(a)) and ra[a] <= ft + SYNC_GRACE_S
    return {(True, True): "both", (True, False): "panam_only", (False, True): "rogue_only",
            (False, False): "neither"}[(had(PANAM_MARKER), had(ROGUE_MARKER))]


def _pl_group(r: dict[str, Any]) -> str:
    if not r["pl_completed"] or r["pl_first_ending_time"] is None:
        return "no_pl_ending"
    return "pl_before" if r["pl_first_ending_time"] < r["main_first_ending_time"] else "pl_after"


def _dist(rs: list[dict[str, Any]], key: str, cols: list[str]) -> dict[str, Any]:
    c, n = Counter(r[key] for r in rs), len(rs)
    out = {"n": n, "pct": {k: pct(c[k], n) for k in cols}}
    if key == "main_first_ending":
        out["devil_plus_world_only"] = pct(c["TheDevil"] + c[UNMARKED], n)
    return out


def _is_rusher(r: dict[str, Any]) -> bool:
    """TheWorld-only first ending, neither side questline done before it, no main ending afterwards."""
    return (r["main_first_ending"] == UNMARKED and _routes(r) == "neither" and r["main_second_ending"] is None)


def _mann_whitney_less(a: list[float], b: list[float]) -> dict[str, Any]:
    """P(random a < random b), ties counted half, with a one-sided normal-approximation p-value."""
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return {"p_less": None, "p_value": None}
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i = [0.0] * len(allv), 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        i = j + 1
    r1 = sum(rk for rk, (_, g) in zip(ranks, allv) if g == 0)
    u_a = r1 - n1 * (n1 + 1) / 2              # count of (a > b) pairs + half ties
    z = (u_a - n1 * n2 / 2) / math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    return {"p_less": round(1 - u_a / (n1 * n2), 3), "p_value": 0.5 * math.erfc(-z / math.sqrt(2))}


def rusher_playtime(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Lifetime playtime of rushers vs other finishers. Single-ending groups are the fair comparison,
    since replays inflate lifetime hours."""
    main = [r for r in recs if r["main_completed"] and not r["main_offline_sync_tie"]]
    single = lambda r: r["main_second_ending"] is None
    groups = {
        "rushers": [r for r in main if _is_rusher(r)],
        "everyone_else": [r for r in main if not _is_rusher(r)],
        "single_ending_not_rushers": [r for r in main if single(r) and not _is_rusher(r)],
        "single_ending_thedevil": [r for r in main if single(r) and r["main_first_ending"] == "TheDevil"],
        "single_ending_star_sun_temperance": [r for r in main if single(r)
                                              and r["main_first_ending"] in CO_SYNC_ENDINGS],
    }
    hours = {k: sorted(r["playtime_forever"] / 60 for r in rs) for k, rs in groups.items()}
    def summ(h):
        if len(h) < 2:
            return {"n": len(h), "mean_h": round(h[0], 1) if h else None, "median_h": round(h[0], 1) if h else None,
                    "p25_h": None, "p75_h": None}
        q = statistics.quantiles(h, n=4)
        return {"n": len(h), "mean_h": round(statistics.mean(h), 1), "median_h": round(statistics.median(h), 1),
                "p25_h": round(q[0], 1), "p75_h": round(q[2], 1)}
    return {"groups": {k: summ(h) for k, h in hours.items()},
            "vs_everyone_else": _mann_whitney_less(hours["rushers"], hours["everyone_else"]),
            "vs_single_ending": _mann_whitney_less(hours["rushers"], hours["single_ending_not_rushers"])}


def pl_vs_main(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Main-game first ending split by whether (and when) the player finished Phantom Liberty."""
    main = [r for r in recs if r["main_completed"] and not r["main_offline_sync_tie"]]
    no_tower = [r for r in main if r["main_first_ending"] != "TheTower"]
    cols_nt = [e for e in MAIN_ORDER if e != "TheTower"]
    grouped = lambda rs, cols: {g: _dist([r for r in rs if _pl_group(r) == g], "main_first_ending", cols)
                                for g in PL_GROUPS}
    era = [r for r in no_tower if r["main_first_ending_time"] >= PL_RELEASE_TS]
    kings = [r for r in main if r["pl_completed"] and not r["pl_offline_sync_tie"]
             and r["pl_first_ending"] in PL_ENDINGS]
    before = [r for r in kings if _pl_group(r) == "pl_before"]
    after = [r for r in kings if _pl_group(r) == "pl_after"]
    return {
        "by_pl_status": grouped(main, MAIN_ORDER),
        "by_pl_status_no_tower": grouped(no_tower, cols_nt),
        "pl_era_no_tower": grouped(era, cols_nt),
        "pl_era_by_routes": {rt: grouped([r for r in era if _routes(r) == rt], cols_nt) for rt in ROUTE_GROUPS},
        "pl_era_both_routes_pct": {g: pct(sum(1 for r in era if _pl_group(r) == g and _routes(r) == "both"),
                                          sum(1 for r in era if _pl_group(r) == g)) for g in PL_GROUPS},
        "king_to_main_pl_before": {k: _dist([r for r in before if r["pl_first_ending"] == k],
                                            "main_first_ending", MAIN_ORDER) for k in PL_ENDINGS},
        "king_to_main_pl_before_no_tower": {k: _dist([r for r in before if r["pl_first_ending"] == k
                                                      and r["main_first_ending"] != "TheTower"],
                                                     "main_first_ending", cols_nt) for k in PL_ENDINGS},
        "main_to_king_pl_after": {e: _dist([r for r in after if r["main_first_ending"] == e],
                                           "pl_first_ending", PL_ENDINGS) for e in cols_nt},
        "rusher_kings": rusher_kings(main, kings),
    }


RUSHER_KING_GROUPS = {"rushers": "Rushers", "world_only_not_rushers": "TheWorld-only, not rushers",
                      "everyone_else": "All other finishers"}


def rusher_kings(main: list[dict[str, Any]], kings: list[dict[str, Any]]) -> dict[str, Any]:
    """First King ending and PL finish rate for rushers vs other main-game finishers."""
    def group(r: dict[str, Any]) -> str:
        if _is_rusher(r):
            return "rushers"
        return "world_only_not_rushers" if r["main_first_ending"] == UNMARKED else "everyone_else"
    finish = {}
    for g in RUSHER_KING_GROUPS:
        base = [r for r in main if group(r) == g]
        done = sum(1 for r in base if r["pl_completed"] and r["pl_first_ending"] in PL_ENDINGS)
        finish[g] = {"n": len(base), "finished_pl": done, "finished_pl_pct": pct(done, len(base))}
    return {"finish_rate": finish,
            "all": {g: _dist([r for r in kings if group(r) == g], "pl_first_ending", PL_ENDINGS)
                    for g in RUSHER_KING_GROUPS},
            "by_order": {o: {g: _dist([r for r in kings if group(r) == g and _pl_group(r) == o],
                                      "pl_first_ending", PL_ENDINGS) for g in RUSHER_KING_GROUPS}
                         for o in ("pl_before", "pl_after")}}
