"""Node functions that need more than one module of the endings pipeline, or that assemble the final summary."""
from __future__ import annotations

import time
from typing import Any

from ...domain.constants import (APPID, COMPLETION, MAIN_ENDINGS, MAIN_MILESTONES, PL_MILESTONES, TRACKS,
                                 UNMARKED)
from .common import pct
from .completion import story_funnel
from .first_endings import add_devil_total, track_stats
from .sampling import sampling_bias


def compute_tracks(recs: list[dict[str, Any]], routes: dict[str, Any]) -> dict[str, Any]:
    """Per-track stats over all records, with the Devil total and its conservative floors."""
    tracks = {t: track_stats(recs, t) for t in TRACKS}
    add_devil_total(tracks["main"], recs)
    u, d = routes.get(UNMARKED, {}), tracks["main"]["devil_total"]
    n_main = tracks["main"]["strict_sample_n"]
    if u.get("n"):
        f_rush = d["achievement_count"] + u["neither_no_later_ending"]["count"]
        f_neither = d["achievement_count"] + u["neither"]["count"]
        d["floors"] = {"rushers_count": f_rush, "rushers_pct": pct(f_rush, n_main),
                       "neither_questline_count": f_neither, "neither_questline_pct": pct(f_neither, n_main)}
    return tracks


def compute_tracks_clean(clean: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-track stats with flagged (suspect) records excluded."""
    tracks = {t: track_stats(clean, t) for t in TRACKS}
    add_devil_total(tracks["main"], clean)
    return tracks


def story_funnels(recs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "main": story_funnel(recs, MAIN_MILESTONES, "main", "Finished the main story (any main ending)"),
        "pl": story_funnel(recs, PL_MILESTONES, "pl", "Finished Phantom Liberty (any King ending)"),
    }


def compute_sampling_bias(candidate_summary: dict[str, Any], recs: list[dict[str, Any]],
                          tracks: dict[str, Any]) -> dict[str, Any]:
    main = tracks["main"]
    return sampling_bias(candidate_summary, recs, main["devil_total"], main["strict_sample_n"])


def run_metrics(run_state: dict[str, Any], candidate_summary: dict[str, Any],
                recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Collection funnel (reviews -> lookups -> public -> completed) and flag counts."""
    sc = candidate_summary["status_counts"]
    queried = sum(v for k, v in sc.items() if k != "pending")
    completed = [r for r in recs if r["completed"]]
    completed_any = len(completed)
    return {
        "reviews_seen": run_state.get("reviews_seen", 0),
        "review_pages": run_state.get("review_pages", 0),
        "filtered_low_playtime": run_state.get("filtered_low_playtime", 0),
        "duplicate_reviewers": run_state.get("duplicate_reviewers", 0),
        "candidates_discovered": sum(sc.values()),
        "ids_queried": queried,
        "pending": sc.get("pending", 0),
        "private_profiles": sc.get("private", 0),
        "private_pct_of_queried": pct(sc.get("private", 0), queried),
        "no_stats": sc.get("no_stats", 0),
        "errors": sc.get("error", 0),
        "public_profiles": sc.get("public", 0),
        "never_finished_either": sc.get("public", 0) - completed_any,
        "completed_any": completed_any,
        "no_world_late_story": sum(1 for r in recs if not r["main_completed"]
                                   and r["raw_achievements"].get("TheHightPriestess")),
        # TheTower is excluded: it never unlocks TheWorld.
        "base_ending_no_world": sum(1 for r in recs if r["unlock_timestamps"][COMPLETION] is None
                                    and any(r["unlock_timestamps"][e] for e in MAIN_ENDINGS if e != "TheTower")),
        "flag_burst": sum(r["flag_burst"] for r in completed),
        "flag_low_playtime": sum(r["flag_low_playtime"] for r in completed),
        "flagged_any": sum(r["suspect"] for r in completed),
    }


def assemble_summary(mapping: dict[str, str], metrics: dict[str, Any], flags: dict[str, int],
                     tracks: dict[str, Any], tracks_clean: dict[str, Any], cosync: dict[str, Any],
                     unmarked: dict[str, Any], routes: dict[str, Any], pl_main: dict[str, Any],
                     rusher_pt: dict[str, Any], complete: dict[str, Any], bias: dict[str, Any],
                     funnel: dict[str, Any]) -> dict[str, Any]:
    """endings_summary.json. Aggregates only: no SteamIDs or per-player rows."""
    return {
        "appid": APPID,
        "generated_at": int(time.time()),
        "achievement_mapping": mapping,
        "run_metrics": metrics,
        "flag_config": {k: flags[k] for k in ("burst_count", "burst_window_s", "low_playtime_mins")},
        "tracks": tracks,
        "tracks_clean": tracks_clean,
        "world_cosync": cosync,
        "unmarked_breakdown": unmarked,
        "route_availability": routes,
        "pl_vs_main": pl_main,
        "rusher_playtime": rusher_pt,
        "completionists": complete,
        "sampling_bias": bias,
        "story_funnel": funnel,
    }
