from cyberpunk_stats.collect import cli
from cyberpunk_stats.collect.checkpoint import Checkpoint
from cyberpunk_stats.domain.constants import TRACKED


def test_error_streak_requeues_and_pauses(tmp_path, monkeypatch):
    """A run of failures (e.g. daily API cap) must pause and retry, not burn candidates as errors."""
    monkeypatch.setenv("STEAM_API_KEY", "dummy")
    monkeypatch.setattr(cli, "load_dotenv", None)
    monkeypatch.setattr(cli, "resolve_schema", lambda client, overrides: {c: c for c in TRACKED})
    sleeps = []
    monkeypatch.setattr(cli.time, "sleep", lambda s: sleeps.append(s))

    ids = [str(i) for i in range(30)]
    def fake_reviews(client, db, review_filter, min_playtime):
        if db.get("served"):
            return "exhausted"
        db.put("served", True)
        db.add_candidates([(i, 2000) for i in ids], review_filter)
        return "open"
    monkeypatch.setattr(cli, "fetch_review_page", fake_reviews)

    calls = {"n": 0}
    def fake_ach(client, sid):
        calls["n"] += 1
        if calls["n"] <= cli.ERROR_STREAK_LIMIT:  # first 10 lookups fail (quota), then recover
            return "error", "HTTP 403", None
        return "public", None, {"TheStar": 1000, "TheWorld": 1001}
    monkeypatch.setattr(cli, "fetch_achievements", fake_ach)

    path = tmp_path / "checkpoint.sqlite"
    cli.main(["--checkpoint", str(path), "--target-samples", "30", "--error-pause-mins", "1"])
    db = Checkpoint(path)
    assert db.status_counts() == {"public": 30}  # nothing lost to the failure streak
    assert sleeps == [60]


def test_retry_errors_requeues(tmp_path):
    db = Checkpoint(tmp_path / "c.sqlite")
    db.add_candidates([("1", 0), ("2", 0)], "recent")
    db.record("1", 0, "error", "HTTP 500", None)
    db.record("2", 0, "private", "Profile is not public", None)
    assert db.requeue_errors() == 1
    assert db.status_counts() == {"pending": 1, "private": 1}
