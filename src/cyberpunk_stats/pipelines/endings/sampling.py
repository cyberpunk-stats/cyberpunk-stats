"""Sampling-bias checks: private vs public reviewers and hidden modded finishers."""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from ...domain.constants import MAIN_ORDER
from .common import pct

PLAYTIME_BANDS_H = [0, 10, 30, 60, 100, 200, 500]


def _band(h: float) -> int:
    return max(i for i, lo in enumerate(PLAYTIME_BANDS_H) if h >= lo)


def sampling_bias(candidate_summary: dict[str, Any], recs: list[dict[str, Any]], devil_total: dict[str, Any],
                  strict_n: int) -> dict[str, Any]:
    """Private vs public reviewers (only review playtime is visible for private ones), and how far
    hidden modded finishers could move The Devil."""
    pt = candidate_summary["playtime_h"]
    nb = len(PLAYTIME_BANDS_H)
    share = {st: [sum(1 for h in xs if _band(h) == i) / len(xs) if xs else 0.0 for i in range(nb)]
             for st, xs in pt.items()}
    w = [share["private"][i] / share["public"][i] if share["public"][i] else 0.0 for i in range(nb)]
    wt = lambda r: w[_band(r["playtime_forever"] / 60)]
    main = [r for r in recs if r["main_completed"] and not r["main_offline_sync_tie"]]

    def mix(weight):
        tot, acc = sum(weight(r) for r in main), Counter()
        for r in main:
            acc[r["main_first_ending"]] += weight(r)
        return {e: round(100 * acc[e] / tot, 2) if tot else None for e in MAIN_ORDER}

    fin = lambda weight: (round(100 * sum(weight(r) for r in recs if r["main_completed"])
                                / sum(weight(r) for r in recs), 2) if recs and sum(weight(r) for r in recs) else None)
    hp_long = sum(1 for r in recs if r["raw_achievements"].get("TheHightPriestess") and not r["main_completed"]
                  and r["playtime_forever"] / 60 >= 100)
    d = devil_total["total_count"]
    labels = [f"{lo}-{hi}h" for lo, hi in zip(PLAYTIME_BANDS_H, PLAYTIME_BANDS_H[1:])] + [f"{PLAYTIME_BANDS_H[-1]}h+"]
    med = lambda xs: round(statistics.median(xs), 1) if xs else None
    return {
        "playtime_bands": {lab: {"public_pct": round(100 * share["public"][i], 2),
                                 "private_pct": round(100 * share["private"][i], 2)} for i, lab in enumerate(labels)},
        "median_playtime_h": {"public": med(pt["public"]), "private": med(pt["private"])},
        "first_ending_public": mix(lambda r: 1.0),
        "first_ending_reweighted_to_private": mix(wt),
        "finish_rate_public_pct": fin(lambda r: 1.0),
        "finish_rate_reweighted_pct": fin(wt),
        "hanako_no_finish_100h": hp_long,
        "devil_if_hidden_finishers_none_devil_pct": pct(d, strict_n + hp_long),
        "devil_if_hidden_finishers_all_devil_pct": pct(d + hp_long, strict_n + hp_long),
    }
