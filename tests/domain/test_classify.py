import pytest

from cyberpunk_stats.domain.classify import classify
from cyberpunk_stats.domain.constants import UNMARKED
from tests.conftest import H


def track(r, t):
    p = f"{t}_"
    return r[p + "first_ending"], r[p + "second_ending"], r[p + "transition_type"], r[p + "offline_sync_tie"]


@pytest.mark.parametrize("unlocks, expected", [
    ({}, (None, None, None, False)),
    ({"TheStar": 1000, "TheWorld": 1010}, ("TheStar", None, None, False)),
    # Star first, Sun via reload 1h later
    ({"TheStar": 1000, "TheWorld": 1005, "TheSun": 1000 + H}, ("TheStar", "TheSun", "save_reload_sweep", False)),
    # Sun 2 days later = separate playthrough
    ({"TheStar": 1000, "TheSun": 1000 + 48 * H}, ("TheStar", "TheSun", "separate_playthrough", False)),
    # The Tower is a regular main-game ending
    ({"TheTower": 1000, "TheWorld": 1001, "TheDevil": 1000 + H}, ("TheTower", "TheDevil", "save_reload_sweep", False)),
    # TheWorld only -> unmarked ending
    ({"TheWorld": 5000}, (UNMARKED, None, None, False)),
    # TheWorld long before any named ending -> unmarked first, second = earliest named
    ({"TheWorld": 1000, "TheDevil": 1000 + 2 * H}, (UNMARKED, "TheDevil", "save_reload_sweep", False)),
    # TheWorld 200s before a named ending -> same credits roll
    ({"TheWorld": 1000, "TheSun": 1200}, ("TheSun", None, None, False)),
    # Offline sync tie on first position
    ({"TheStar": 1000, "TheSun": 1000, "TheWorld": 1000}, ("Tie:TheStar+TheSun", None, None, True)),
    # Tie on later endings still flags the record
    ({"TheStar": 1000, "TheSun": 9000, "Temperance": 9000}, ("TheStar", "Temperance", "save_reload_sweep", True)),
    # unlocktime 0 is not an unlock
    ({"TheStar": 0, "TheWorld": 0}, (None, None, None, False)),
])
def test_main_track(unlocks, expected):
    assert track(classify(unlocks), "main") == expected


@pytest.mark.parametrize("unlocks, expected", [
    ({"TheStar": 1000}, (None, None, None, False)),
    ({"KingOfTheSwords": 1000}, ("KingOfTheSwords", None, None, False)),
    ({"KingOfTheCups": 1000, "KingOfTheWands": 1000 + H}, ("KingOfTheCups", "KingOfTheWands", "save_reload_sweep", False)),
    ({"KingOfThePentacles": 1000, "KingOfTheSwords": 1000 + 30 * H},
     ("KingOfThePentacles", "KingOfTheSwords", "separate_playthrough", False)),
    ({"KingOfTheCups": 1000, "KingOfTheWands": 1000}, ("Tie:KingOfTheCups+KingOfTheWands", None, None, True)),
])
def test_pl_track(unlocks, expected):
    assert track(classify(unlocks), "pl") == expected


def test_tracks_are_independent():
    r = classify({"KingOfTheWands": 1000, "TheWorld": 1000 + 50 * H, "TheSun": 1000 + 50 * H})
    assert track(r, "pl")[0] == "KingOfTheWands"
    assert track(r, "main")[0] == "TheSun"
    assert r["completed"]


def test_world_coinciding_with_pl_ending_is_not_unmarked():
    r = classify({"KingOfTheSwords": 1000, "TheWorld": 1020})
    assert not r["main_completed"]
    assert r["pl_first_ending"] == "KingOfTheSwords"
    # ...but if a main ending shares that credits roll, TheWorld still counts normally
    r = classify({"KingOfTheSwords": 1000, "TheWorld": 1020, "TheTower": 1010})
    assert r["main_first_ending"] == "TheTower"
