"""Steam Web API calls: achievement schema, review feed (candidate discovery), player achievements."""
from __future__ import annotations

import logging
import sys

from ..domain.constants import APPID, TRACKED
from .checkpoint import Checkpoint
from .client import SteamClient

log = logging.getLogger(__name__)

SCHEMA_URL = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
ACH_URL = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
# store.steampowered.com/appreviews was retired in Oct 2026; this is its documented replacement.
REVIEWS_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
REVIEW_FILTERS = {"helpful": 0, "recent": 1, "updated": 2}  # EUserReviewsAppReviewsFilter
STALE_PAGE_LIMIT = 3  # consecutive pages with no unseen reviews -> feed exhausted


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def resolve_schema(client: SteamClient, overrides: dict[str, str]) -> dict[str, str]:
    """Return {canonical_name: actual_apiname}. Aborts if an ending can't be resolved."""
    r = client.get(SCHEMA_URL, {"key": client.api_key, "appid": APPID})
    if r is None or r.status_code != 200:
        sys.exit(f"GetSchemaForGame failed (HTTP {getattr(r, 'status_code', 'n/a')}). Is STEAM_API_KEY valid?")
    achs = r.json().get("game", {}).get("availableGameStats", {}).get("achievements", [])
    by_api = {a["name"]: a for a in achs}
    by_display = {_norm(a.get("displayName", "")): a for a in achs}
    log.info("schema: %d achievements for appid %d", len(achs), APPID)

    mapping: dict[str, str] = {}
    for canon in TRACKED:
        if canon in overrides:
            api = overrides[canon]
            how = "override"
        elif canon in by_api:
            api, how = canon, "exact apiname"
        elif _norm(canon) in by_display:
            api, how = by_display[_norm(canon)]["name"], "displayName match"
        else:
            api, how = None, "NOT FOUND"
        if api and api not in by_api:
            how = f"{how} -> apiname '{api}' NOT IN SCHEMA"
            api = None
        meta = by_api.get(api, {}) if api else {}
        log.info("  %-16s -> %-24s [%s] %s: %s", canon, api, how,
                 meta.get("displayName", ""), meta.get("description", ""))
        if api:
            mapping[canon] = api

    missing = [c for c in TRACKED if c not in mapping]
    if missing:
        log.error("Unresolved achievements: %s", missing)
        log.error("Ending-like achievements in schema, to pick the right ones:")
        for a in achs:
            log.error("  %-28s %-28s %s", a["name"], a.get("displayName", ""), a.get("description", ""))
        sys.exit("Fix with e.g. --map TheStar=<apiname> and re-run.")
    return mapping


def fetch_review_page(client: SteamClient, db: Checkpoint, review_filter: str, min_playtime: int) -> str:
    """Fetch one page of reviews into candidates. Returns "open", "exhausted", or "failed"
    (request failed; the cursor is unchanged, so the caller can retry later)."""
    ckey = f"cursor:{review_filter}"
    cursor = db.get(ckey, "*")
    params = {"appid": APPID, "filter": REVIEW_FILTERS[review_filter], "languages[0]": "all",
              "num_per_page": 100, "cursor": cursor, "review_type": 0, "purchase_type": 1,
              "filter_offtopic_activity": "false"}
    if review_filter == "helpful":
        params["day_range"] = 0  # no limit; the default is only the last 30 days
    # No key: GetAppReviews doesn't need one, and only a publisher key raises the rate limit.
    r = client.get(REVIEWS_URL, params)
    if r is None or r.status_code != 200:
        log.error("GetAppReviews failed (HTTP %s)", getattr(r, "status_code", "n/a"))
        return "failed"
    try:
        data = r.json().get("response", {})
    except ValueError:
        log.error("GetAppReviews returned non-JSON (HTTP %s)", r.status_code)
        return "failed"
    reviews = data.get("reviews") or []
    next_cursor = data.get("cursor")

    rows, low = [], 0
    for rv in reviews:
        a = rv.get("author", {})
        sid, pt = a.get("steamid"), int(a.get("playtime_forever") or 0)
        if not sid:
            continue
        if pt < min_playtime:
            low += 1
            continue
        rows.append((str(sid), pt))
    unseen = db.mark_reviews_seen([str(rv["recommendationid"]) for rv in reviews if "recommendationid" in rv])
    new = db.add_candidates(rows, review_filter)
    db.bump("reviews_seen", unseen)
    db.bump("filtered_low_playtime", low)
    db.bump("duplicate_reviewers", len(rows) - new)
    db.bump("review_pages", 1)
    log.info("reviews[%s]: page of %d (%d unseen), %d new candidates, %d below playtime",
             review_filter, len(reviews), unseen, new, low)

    # Recent/Updated end with an empty page; Helpful keeps returning results, so also stop
    # after a few pages that contain nothing new.
    skey = f"stale_pages:{review_filter}"
    db.put(skey, 0 if unseen else db.get(skey, 0) + 1)
    if not reviews or not next_cursor or next_cursor == cursor or db.get(skey) >= STALE_PAGE_LIMIT:
        return "exhausted"
    db.put(ckey, next_cursor)
    return "open"


def fetch_achievements(client: SteamClient, steamid: str) -> tuple[str, str | None, dict[str, int] | None]:
    """Returns (status, detail, {apiname: unlocktime} | None)."""
    r = client.get(ACH_URL, {"appid": APPID, "key": client.api_key, "steamid": steamid})
    if r is None:
        return "error", "retries exhausted", None
    try:
        ps = r.json().get("playerstats", {})
    except ValueError:
        return "error", f"HTTP {r.status_code} non-JSON", None
    if not ps.get("success"):
        err = ps.get("error", f"HTTP {r.status_code}")
        if "not public" in err.lower():
            return "private", err, None
        if "no stats" in err.lower():
            return "no_stats", err, None
        return "error", err, None
    unlocked = {a["apiname"]: int(a["unlocktime"])
                for a in ps.get("achievements", []) if a.get("achieved") == 1}
    return "public", None, unlocked
