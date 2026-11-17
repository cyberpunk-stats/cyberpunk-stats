from cyberpunk_stats.domain.constants import (MAIN_ENDINGS, MAIN_MILESTONES, PANAM_MARKER, PL_ENDINGS,
                                             PL_MILESTONES, ROGUE_MARKER, TRACKED, UNMARKED)
from cyberpunk_stats.pipelines.endings.completion import completionists, story_funnel
from cyberpunk_stats.pipelines.endings.first_endings import (add_devil_total, glitch_estimate, route_availability,
                                                       track_stats, world_cosync)
from cyberpunk_stats.pipelines.endings.groups import _mann_whitney_less, rusher_kings, rusher_playtime
from tests.conftest import H, make_rec as rec


def test_world_cosync():
    recs = []
    for ach in [
        {"TheTower": 1000, "TheWorld": 1010},          # Tower triggers TheWorld
        {"TheTower": 1000},                             # Tower, no TheWorld
        {"TheStar": 1000, "TheWorld": 1001, "TheTower": 50000},  # Tower not first main ending -> excluded
        {"KingOfTheSwords": 500, "TheTower": 3000, "TheWorld": 3005},  # usual Tower route: PL ending first
        {"TheWorld": 100, "TheSun": 9000},              # TheWorld earlier (unmarked first)
        {"KingOfTheCups": 1000, "TheWorld": 90000},     # King ending, TheWorld much later
    ]:
        recs.append({"unlock_timestamps": {k: ach.get(k) for k in TRACKED}})
    d = world_cosync(recs)
    assert d["TheTower"]["n"] == 3
    assert d["TheTower"]["within_grace"]["count"] == 2 and d["TheTower"]["no_world"]["count"] == 1
    assert d["KingOfTheSwords"]["world_later_lt_2h"]["count"] == 1
    assert d["TheStar"]["within_grace"]["pct"] == 100.0
    assert d["TheSun"]["world_earlier"]["count"] == 1
    assert d["KingOfTheCups"]["world_later_ge_2h"]["count"] == 1
    assert d["TheDevil"]["n"] == 0 and d["TheDevil"]["within_grace"]["pct"] is None


def test_route_availability():
    recs = [
        rec({"QueenOfTheHighway": 500, "TheStar": 1000, "TheWorld": 1001}),
        rec({"TheWorld": 1000}),                                   # rushed: neither, nothing later
        rec({"TheWorld": 1000, "TheSun": 1000 + 50 * H}),          # neither before, later ending
        rec({"BushidoAndChill": 500, "TheWorld": 1000}),           # had Rogue's questline
        rec({"TheWorld": 1000, "QueenOfTheHighway": 5000}),        # marker after first ending doesn't count
    ]
    ra = route_availability(recs)
    assert ra["TheStar"]["panam"]["count"] == 1 and ra["TheStar"]["neither"]["count"] == 0
    u = ra[UNMARKED]
    assert u["n"] == 4
    assert (u["neither"]["count"], u["rogue"]["count"], u["neither_no_later_ending"]["count"]) == (3, 1, 2)


def test_story_funnel():
    recs = [
        rec({}),                                                         # never reached a milestone
        rec({"TheFool": 1}),                                             # stopped after prologue
        rec({"TheFool": 1, "TheLovers": 2}, playtime=1200),              # stopped after Act 1
        rec({"TheFool": 1, "TheLovers": 2, "TheWheelOfFortune": 3, "TheHightPriestess": 4}),
        rec({"TheFool": 1, "TheLovers": 2, "TheWheelOfFortune": 3, "TheHightPriestess": 4,
             "TheWorld": 5, "AllThePresidentsMen": 6}),                  # finished main, started PL
        rec({"TheFool": 1, "TheLovers": 2, "TheWheelOfFortune": 3, "TheHightPriestess": 4, "TheWorld": 5,
             "AllThePresidentsMen": 5 + 10 * H, "IHateSpider": 5 + 11 * H, "KingOfTheWands": 5 + 20 * H}),
    ]
    f = story_funnel(recs, MAIN_MILESTONES, "main", "done")
    assert (f["base_n"], f["finished"], f["not_finished"]) == (6, 2, 4)
    assert [st["reached"] for st in f["stages"]] == [5, 4, 3, 3, 2]
    assert f["stages"][1]["pct_of_previous"] == 80.0
    stops = {k: v["count"] for k, v in f["stopped_after"].items()}
    assert stops == {"No story milestone": 1, "Became a mercenary (end of prologue)": 1,
                     "Stole the Relic (end of Act 1)": 1, "Interrogated Hellman (Act 2)": 0,
                     "Talked with Hanako (end of Act 2)": 1}
    assert f["stopped_after"]["Stole the Relic (end of Act 1)"]["median_playtime_h"] == 20.0
    p = story_funnel(recs, PL_MILESTONES, "pl", "done")
    assert (p["base_n"], p["finished"], p["not_finished"]) == (2, 1, 1)
    assert p["most_common_stop"] == "Saved President Myers (start)"


def test_glitch_margin():
    P = PANAM_MARKER
    recs = (
        [rec({P: 10, "TheStar": 1000, "TheWorld": 1001}) for _ in range(8)]
        + [rec({P: 1000 + 50 * H, "TheStar": 1000, "TheWorld": 1001})]   # Life of the Road failed, came later
        + [rec({"TheStar": 1000, "TheWorld": 1001})]                     # never had it
        + [rec({"TheSun": 1000, "TheWorld": 1001}) for _ in range(9)]
        + [rec({"TheSun": 1000})]                                        # TheWorld failed
        + [rec({"TheWorld": 1000}) for _ in range(5)]
        + [rec({"TheDevil": 1000, "TheWorld": 1000 + 1800})]
    )
    g = glitch_estimate(recs)
    assert g["world_missing_star_sun"] == {"count": 1, "n": 20, "pct": 5.0}
    assert g["star_without_panam"] == {"never": 1, "later": 1, "n": 10, "pct": 20.0}
    assert (g["failure_rate_low_pct"], g["failure_rate_high_pct"]) == (5.0, 20.0)
    assert (g["expected_glitched_low"], g["expected_glitched_high"]) == (1, 4)
    main = track_stats(recs, "main")
    add_devil_total(main, recs)
    d = main["devil_total"]
    assert (d["total_count"], d["adjusted_low_count"], d["adjusted_high_count"]) == (6, 2, 5)


def test_rusher_playtime_and_mann_whitney():
    mw = _mann_whitney_less([1, 2, 3], [4, 5, 6])
    assert mw["p_less"] == 1.0 and mw["p_value"] < 0.05
    assert _mann_whitney_less([1, 2], [1, 2])["p_less"] == 0.5
    recs = [rec({"TheWorld": 1000}, h * 60) for h in (30, 40, 50)]                    # rushers
    recs += [rec({ROGUE_MARKER: 10, "TheSun": 1000, "TheWorld": 1001}, h * 60)
             for h in (90, 100, 110)]
    recs += [rec({"TheWorld": 1000, "TheStar": 1000 + 100 * H}, 300 * 60)]           # not a rusher: later ending
    rp = rusher_playtime(recs)
    g = rp["groups"]
    assert (g["rushers"]["n"], g["rushers"]["median_h"]) == (3, 40.0)
    assert g["everyone_else"]["n"] == 4 and g["single_ending_not_rushers"]["n"] == 3
    assert rp["vs_single_ending"]["p_less"] == 1.0


def test_rusher_kings():
    recs = [rec({"TheWorld": 1000, "KingOfTheCups": 1000 + 50 * H}),                  # rusher, PL after
            rec({"TheWorld": 1000}),                                                   # rusher, no PL
            rec({PANAM_MARKER: 10, "TheWorld": 1000, "KingOfTheSwords": 1000 + 50 * H}),  # world-only
            rec({"KingOfTheWands": 10, "TheSun": 1000, "TheWorld": 1001})]             # other, PL before
    main = [r for r in recs if r["main_completed"]]
    rk = rusher_kings(main, [r for r in main if r["pl_completed"]])
    assert rk["finish_rate"]["rushers"] == {"n": 2, "finished_pl": 1, "finished_pl_pct": 50.0}
    assert rk["all"]["rushers"]["pct"]["KingOfTheCups"] == 100.0
    assert rk["by_order"]["pl_after"]["world_only_not_rushers"]["pct"]["KingOfTheSwords"] == 100.0
    assert rk["by_order"]["pl_before"]["everyone_else"]["n"] == 1
    assert rk["by_order"]["pl_before"]["rushers"]["n"] == 0


def test_completionists():
    all_main = {e: 1000 + i * 10 * H for i, e in enumerate(MAIN_ENDINGS)}
    sweep_kings = {k: 5000 + i * 600 for i, k in enumerate(PL_ENDINGS)}
    recs = [rec({**all_main, "TheWorld": 1001, **sweep_kings}, 6000),                 # all 9; Kings in one sweep
            rec({**all_main, "TheWorld": 1001}, 6000, suspect=True),                  # all 5 main, flagged
            rec({"TheSun": 1000, "TheWorld": 1001, "KingOfTheWands": 2000}, 6000)]    # one of each
    cp = completionists(recs)
    ma, pl = cp["sets"]["main_all"], cp["sets"]["pl_all"]
    assert (ma["base_n"], ma["count"], ma["flagged"], ma["clean_count"], ma["clean_base_n"]) == (3, 2, 1, 1, 2)
    assert ma["one_sweep_pct"] == 0.0 and ma["median_span_days"] == round(40 * H / 86400, 1)
    assert (pl["base_n"], pl["count"], pl["one_sweep_pct"]) == (2, 1, 100.0)
    assert cp["sets"]["everything"]["base_n"] == 2 and cp["sets"]["everything"]["count"] == 1
    assert cp["endings_unlocked"]["main"]["counts"][5]["count"] == 2
    assert cp["endings_unlocked"]["pl"]["counts"][1]["count"] == 1
