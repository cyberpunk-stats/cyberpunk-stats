"""Collect Steam reviewers' Cyberpunk 2077 achievement timestamps into a resumable SQLite checkpoint.

Steps:
  A. GetSchemaForGame       -> verify/resolve ending achievement apinames
  B. GetAppReviews          -> discover candidate steamids
  C. GetPlayerAchievements  -> fetch unlock timestamps, checkpoint to SQLite

The checkpoint is the raw input of the Kedro pipelines; build the stats with `kedro run`.

Usage:
  export STEAM_API_KEY=...           # or put it in .env
  cyberpunk-stats-collect --target-samples 3000
  cyberpunk-stats-collect --resume   # continue after interruption
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from ..domain.classify import classify, to_canonical
from ..domain.constants import TRACKED
from .checkpoint import Checkpoint
from .client import SteamClient
from .steam import REVIEW_FILTERS, fetch_achievements, fetch_review_page, resolve_schema

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None

log = logging.getLogger(__name__)

DEFAULT_CHECKPOINT = Path("data/01_raw/checkpoint.sqlite")
ERROR_STREAK_LIMIT = 10  # consecutive failed lookups -> requeue them and pause (e.g. daily API cap hit)
MAX_PAUSE_S = 4 * 3600


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target-samples", type=int, default=3000,
                   help="stop after this many public profiles with >=1 completed ending, "
                        "main game or Phantom Liberty (default 3000)")
    p.add_argument("--min-playtime-mins", type=int, default=0,
                   help="optional: skip reviewers below this lifetime playtime to save API calls (default 0 = off; "
                        "completion is decided by achievements)")
    p.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT,
                   help=f"SQLite checkpoint path (default {DEFAULT_CHECKPOINT})")
    p.add_argument("--resume", action="store_true", help="continue from existing checkpoint")
    p.add_argument("--review-filter", choices=list(REVIEW_FILTERS), default="recent",
                   help="review feed to sample; run again with --resume and another filter to widen the sample")
    p.add_argument("--rate", type=float, default=1.3, help="max requests/sec (default 1.3)")
    p.add_argument("--map", action="append", default=[], metavar="CANON=APINAME",
                   help="override achievement apiname, e.g. --map TheStar=ACH_STAR (repeatable)")
    p.add_argument("--retry-errors", action="store_true",
                   help="with --resume: put previously failed lookups back in the queue")
    p.add_argument("--error-pause-mins", type=float, default=30,
                   help=f"pause after {ERROR_STREAK_LIMIT} failed lookups in a row; doubles each time, "
                        "up to 4h (default 30)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # urllib3 debug logs would leak the key

    db_path = args.checkpoint
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not args.resume:
        sys.exit(f"{db_path} exists. Pass --resume to continue it, or move it away to start fresh.")

    if load_dotenv:
        load_dotenv()
    key = os.environ.get("STEAM_API_KEY")
    if not key:
        sys.exit("STEAM_API_KEY not set (environment or .env)")

    overrides = dict(m.split("=", 1) for m in args.map)
    bad = set(overrides) - set(TRACKED)
    if bad:
        sys.exit(f"--map keys must be one of {TRACKED}, got {sorted(bad)}")

    client = SteamClient(key, args.rate)
    db = Checkpoint(db_path)

    mapping = resolve_schema(client, overrides)
    old = db.get("achievement_mapping")
    if old and old != mapping:
        log.warning("achievement mapping changed since last run: %s -> %s", old, mapping)
    db.put("achievement_mapping", mapping)

    completed = sum(1 for _, _, raw in db.players() if classify(to_canonical(raw, mapping))["completed"])
    log.info("starting with %d completed runs in checkpoint; target %d", completed, args.target_samples)

    if args.retry_errors:
        log.info("requeued %d previously failed lookups", db.requeue_errors())

    base_pause = args.error_pause_mins * 60
    pause_s = base_pause

    def pause(reason: str) -> None:
        # Long, growing pauses: a streak of failures usually means the daily API cap or a Steam outage.
        nonlocal pause_s
        log.warning("%s; pausing %.0f min before retrying (progress is saved)", reason, pause_s / 60)
        time.sleep(pause_s)
        pause_s = min(pause_s * 2, MAX_PAUSE_S)

    feed_open = not db.get(f"exhausted:{args.review_filter}", False)
    fetched = 0
    streak: list[str] = []
    t0 = time.monotonic()
    try:
        while completed < args.target_samples:
            batch = db.pending(50)
            if not batch:
                if not feed_open:
                    log.warning("review feed '%s' exhausted before reaching target", args.review_filter)
                    break
                res = fetch_review_page(client, db, args.review_filter, args.min_playtime_mins)
                if res == "failed":
                    pause("review feed request failed")
                elif res == "exhausted":
                    feed_open = False
                    db.put(f"exhausted:{args.review_filter}", True)
                else:
                    pause_s = base_pause
                continue
            for sid, pt in batch:
                status, detail, raw = fetch_achievements(client, sid)
                db.record(sid, pt, status, detail, raw)
                fetched += 1
                if status == "error":
                    streak.append(sid)
                    if len(streak) >= ERROR_STREAK_LIMIT:
                        db.requeue(streak)
                        streak = []
                        pause(f"{ERROR_STREAK_LIMIT} lookups failed in a row (last: {detail})")
                        break  # re-read the queue, which now includes the requeued IDs
                    continue
                streak = []
                pause_s = base_pause
                if raw is not None and classify(to_canonical(raw, mapping))["completed"]:
                    completed += 1
                if fetched % 50 == 0:
                    sc = db.status_counts()
                    log.info("fetched %d this run (%.2f req/s) | completed %d/%d | private %d public %d | 429s %d",
                             fetched, fetched / (time.monotonic() - t0), completed, args.target_samples,
                             sc.get("private", 0), sc.get("public", 0), client.http_429s)
                if completed >= args.target_samples:
                    break
    except KeyboardInterrupt:
        log.warning("interrupted; progress is checkpointed. Re-run with --resume.")

    log.info("checkpoint saved to %s (%d completed). Build the stats with `kedro run`.", db_path, completed)


if __name__ == "__main__":
    main()
