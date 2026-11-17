"""Rate-limited HTTP client for the Steam Web API."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

log = logging.getLogger(__name__)


class SteamClient:
    """Rate-limited GET with exponential backoff on 429/5xx/network errors."""

    def __init__(self, api_key: str | None, rate: float, max_retries: int = 7):
        self.api_key = api_key
        self.min_interval = 1.0 / rate
        self.max_retries = max_retries
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "cyberpunk-stats-sampler/1.0"
        self.http_429s = 0

    def _throttle(self) -> None:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def get(self, url: str, params: dict[str, Any]) -> requests.Response | None:
        delay = 2.0
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                r = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                # Don't log str(e): it can contain the full URL including the API key.
                log.warning("network error (%s), retry %d in %.0fs", type(e).__name__, attempt + 1, delay)
                time.sleep(delay)
                delay = min(delay * 2, 300)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if r.status_code == 429:
                    self.http_429s += 1
                ra = r.headers.get("Retry-After", "")
                wait = float(ra) if ra.isdigit() else delay
                wait += random.uniform(0, 1)
                log.warning("HTTP %d, backing off %.0fs (attempt %d)", r.status_code, wait, attempt + 1)
                time.sleep(wait)
                delay = min(delay * 2, 300)
                continue
            return r
        log.error("giving up after %d retries", self.max_retries)
        return None
