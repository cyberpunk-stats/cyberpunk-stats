"""Small helpers shared by the endings pipeline modules."""
from __future__ import annotations

def pct(n: int, d: int) -> float | None:
    return round(100.0 * n / d, 2) if d else None
