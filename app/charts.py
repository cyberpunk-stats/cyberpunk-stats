"""Render a chart from charts.js into a self-contained HTML page for st.iframe."""
from __future__ import annotations

import json
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import streamlit as st

D3 = "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"
D3_SANKEY = "https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"

CSS = """
html, body { margin: 0; padding: 0; background: #000000; color: #f0efec;
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; overflow: hidden; }
#root { width: 100%; padding: 4px 2px 2px; box-sizing: border-box; }
svg { display: block; overflow: visible; font-family: inherit; }
.dim { opacity: 0.35; transition: opacity 120ms; }
.lnk.dim { stroke-opacity: 0.08; }
:root { --tip-accent: #00f0ff; --tip-title: #fcee0a; }
body.pl { --tip-accent: #ff2a4d; --tip-title: #ff8095; }
.tip { position: fixed; pointer-events: none; opacity: 0; z-index: 10; max-width: 300px;
  background: #121212; border: 1px solid color-mix(in srgb, var(--tip-accent) 35%, transparent);
  border-left: 3px solid var(--tip-accent); padding: 8px 10px;
  font-size: 12px; line-height: 1.45; box-shadow: 0 4px 18px #0009; transition: opacity 80ms; }
.tt { font-weight: 600; color: var(--tip-title); margin-bottom: 4px; }
.tr { display: flex; justify-content: space-between; gap: 14px; color: #c3c2b7; }
.tr b { color: #f0efec; font-weight: 600; }
.tn { margin-top: 6px; color: #898781; font-size: 11px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 10px 0 8px; font-size: 12px; color: #c3c2b7; }
.li { display: inline-flex; align-items: center; gap: 6px; }
.sw { width: 10px; height: 10px; border-radius: 2px; display: inline-block; box-sizing: border-box; }
.sw.hollow { background: transparent !important; border-radius: 50%; }
"""


_THEME = {"name": ""}


@contextmanager
def theme(name: str):
    """Charts drawn inside this block use the named theme ("pl": Phantom Liberty red)."""
    prev, _THEME["name"] = _THEME["name"], name
    try:
        yield
    finally:
        _THEME["name"] = prev


@lru_cache(maxsize=1)
def _js() -> str:
    return (Path(__file__).parent / "charts.js").read_text()


def render(spec: dict) -> None:
    """Draw spec["type"] (a chart in charts.js) with the rest of spec as its data. Streamlit sizes the iframe to
    the chart's height, which changes with screen width (narrow screens stack labels above the bars)."""
    libs = f'<script src="{D3}"></script>'
    if spec["type"] == "sankey":
        libs += f'<script src="{D3_SANKEY}"></script>'
    # JSON inside <script>: escape "</" so data can never close the tag.
    data = json.dumps(spec).replace("</", "<\\/")
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap' rel='stylesheet'>"
        f"<style>{CSS}</style>{libs}</head><body class='{_THEME['name']}'><div id='root'></div>"
        f"<script>window.SPEC = {data};</script><script>{_js()}</script></body></html>"
    )
    st.iframe(html, height="content")
