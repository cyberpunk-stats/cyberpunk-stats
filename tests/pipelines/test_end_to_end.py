"""Full ingest -> classification -> endings runs on small checkpoints written by the collector's Checkpoint."""
import pytest

from cyberpunk_stats.domain.constants import PL_RELEASE_TS, TRACKED
from cyberpunk_stats.pipelines.ingest.nodes import achievement_mapping
from tests.conftest import H


def test_summary_end_to_end(checkpoint):
    db, run = checkpoint
    mapping = {c: f"ACH_{c.upper()}" for c in TRACKED}
    db.put("achievement_mapping", mapping)
    players = {
        "1": {"TheStar": 1000, "TheWorld": 1005, "TheSun": 1000 + H, "KingOfTheCups": 900},
        "2": {"TheSun": 1000, "TheWorld": 1001, "KingOfTheWands": 5000, "KingOfTheCups": 5000 + H},
        "3": {"TheStar": 1000, "TheWorld": 1001},
        "4": {},  # public, never finished
        "5": {"TheStar": 1000, "TheSun": 1000},  # main tie, excluded from main strict
    }
    db.add_candidates([(s, 2000) for s in [*players, "6"]], "recent")
    for sid, ach in players.items():
        db.record(sid, 2000, "public", None, {mapping[k]: v for k, v in ach.items()} | {"OTHER": 1})
    db.record("6", 2000, "private", "Profile is not public", None)

    s = run()
    rm, main, pl = s["run_metrics"], s["tracks"]["main"], s["tracks"]["pl"]
    assert (rm["ids_queried"], rm["private_profiles"], rm["completed_any"]) == (6, 1, 4)
    assert (main["completed_runs"], main["strict_sample_n"]) == (4, 3)
    assert main["first_ending_distribution"]["TheStar"]["count"] == 2
    assert main["first_vs_unlock_gap"]["TheSun"] == {"first_ending_pct": 33.33, "unlock_pct": 66.67,
                                                    "inflation_pp": 33.34, "inflation_ratio": 2.0}
    assert main["transitions"]["TheStar"]["unlocked_within_4h_of_first"]["TheSun"]["count"] == 1
    assert pl["strict_sample_n"] == 2
    assert pl["first_ending_distribution"] == {"KingOfTheCups": {"count": 1, "pct": 50.0},
                                               "KingOfTheWands": {"count": 1, "pct": 50.0}}
    assert pl["first_vs_unlock_gap"]["KingOfTheCups"]["unlock_pct"] == 100.0
    assert "steamid" not in str(s) and "OTHER" not in str(s)  # aggregates only


def test_devil_total(checkpoint):
    db, run = checkpoint
    db.put("achievement_mapping", {c: c for c in TRACKED})
    players = {"1": {"TheDevil": 1000, "TheWorld": 1001}, "2": {"TheWorld": 1000},
               "3": {"TheStar": 1000, "TheWorld": 1001}, "4": {"TheSun": 1000, "TheWorld": 1001}}
    db.add_candidates([(s, 0) for s in players], "recent")
    for sid, ach in players.items():
        db.record(sid, 0, "public", None, ach)
    s = run()
    d = s["tracks"]["main"]["devil_total"]
    assert {k: d[k] for k in ["achievement_count", "achievement_pct", "no_achievement_count",
                              "no_achievement_pct", "total_count", "total_pct"]} == {
        "achievement_count": 1, "achievement_pct": 25.0, "no_achievement_count": 1,
        "no_achievement_pct": 25.0, "total_count": 2, "total_pct": 50.0}
    assert "devil_total" not in s["tracks"]["pl"]


def test_flags_and_unmarked_breakdown(checkpoint):
    db, run = checkpoint
    db.put("achievement_mapping", {c: c for c in TRACKED})
    burst = {f"Other{i}": 5000 + i for i in range(10)} | {"TheStar": 5005, "TheWorld": 5006}
    players = {
        "legit": (3000, {"TheSun": 1000, "TheWorld": 1001}),
        "burst": (3000, burst),
        "lowpt": (300, {"TheStar": 1000, "TheWorld": 1001}),
        "u_none": (3000, {"TheWorld": 1000}),
        "u_named": (3000, {"TheWorld": 1000, "TheSun": 1000 + H}),
        "u_devil_fast": (3000, {"TheWorld": 1000, "TheDevil": 1000 + H}),
        "u_devil_day": (3000, {"TheWorld": 1000, "TheDevil": 1000 + 10 * H}),
        "u_devil_late": (300, {"TheWorld": 1000, "TheDevil": 1000 + 48 * H}),
    }
    db.add_candidates([(s, pt) for s, (pt, _) in players.items()], "recent")
    for sid, (pt, ach) in players.items():
        db.record(sid, pt, "public", None, ach)
    s = run()
    rm = s["run_metrics"]
    assert (rm["flag_burst"], rm["flag_low_playtime"], rm["flagged_any"]) == (1, 2, 3)
    assert s["tracks"]["main"]["strict_sample_n"] == 8
    assert s["tracks_clean"]["main"]["strict_sample_n"] == 5
    assert s["tracks_clean"]["main"]["first_ending_distribution"].get("TheStar") is None
    ub = s["unmarked_breakdown"]
    assert ub["n"] == 5
    assert {k: v["count"] for k, v in ub["buckets"].items()} == {
        "no_named_ending": 1, "named_not_devil": 1, "devil_lt_4h": 1, "devil_4h_to_24h": 1, "devil_ge_24h": 1}
    assert ub["buckets"]["devil_ge_24h"]["flagged"] == 1
    assert s["tracks"]["main"]["devil_total"]["total_count"] == 5
    assert s["tracks_clean"]["main"]["devil_total"]["total_count"] == 4


def test_pl_vs_main_groups(checkpoint):
    db, run = checkpoint
    db.put("achievement_mapping", {c: c for c in TRACKED})
    T = PL_RELEASE_TS + 100 * H
    players = {
        "1": {"KingOfTheWands": T, "TheSun": T + 20 * H, "TheWorld": T + 20 * H + 1},   # PL before
        "2": {"TheStar": T, "TheWorld": T + 1, "KingOfTheCups": T + 50 * H},            # PL after
        "3": {"TheWorld": T},                                                           # no PL ending
        "4": {"KingOfTheSwords": T, "TheTower": T + 2 * H},                             # PL before, Tower
    }
    db.add_candidates([(sid, 600) for sid in players], "recent")
    for sid, ach in players.items():
        db.record(sid, 600, "public", None, ach)
    s = run()
    pv = s["pl_vs_main"]
    assert {g: v["n"] for g, v in pv["by_pl_status"].items()} == {"pl_before": 2, "pl_after": 1, "no_pl_ending": 1}
    assert pv["by_pl_status_no_tower"]["pl_before"]["n"] == 1
    assert pv["king_to_main_pl_before"]["KingOfTheSwords"]["pct"]["TheTower"] == 100.0
    assert pv["main_to_king_pl_after"]["TheStar"]["pct"]["KingOfTheCups"] == 100.0
    assert s["sampling_bias"]["median_playtime_h"]["public"] == 10.0


def test_mapping_must_be_complete():
    with pytest.raises(ValueError, match="No achievement mapping"):
        achievement_mapping({})
    with pytest.raises(ValueError, match="lacks"):
        achievement_mapping({"achievement_mapping": {"TheStar": "TheStar"}})
