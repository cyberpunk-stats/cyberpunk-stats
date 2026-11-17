"""Cyberpunk Stats: what was your first Cyberpunk 2077 ending? Reads only endings_summary.json."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from charts import render, theme

DATA = Path(__file__).resolve().parents[1] / "data" / "08_reporting" / "endings_summary.json"
UNMARKED = "TheWorld only (no ending achievement)"
MIN_CELL_N = 30  # rows with fewer players than this are grayed out

# Display order = overall share, fixed everywhere so colors keep their validated neighbours.
# (key, label, short label, color, label ink on the color)
MAIN = [
    ("TheSun", "The Sun", "The Sun", "#c98500", "#0b0b0b"),
    (UNMARKED, "The World only", "The World only", "#d55181", "#ffffff"),
    ("TheStar", "The Star", "The Star", "#3987e5", "#ffffff"),
    ("Temperance", "Temperance", "Temperance", "#199e70", "#ffffff"),
    ("TheTower", "The Tower", "The Tower", "#9085e9", "#ffffff"),
    ("TheDevil", "The Devil", "The Devil", "#e66767", "#ffffff"),
]
KINGS = [
    ("KingOfTheWands", "King of Wands", "Wands", "#d95926", "#ffffff"),
    ("KingOfTheSwords", "King of Swords", "Swords", "#9085e9", "#ffffff"),
    ("KingOfThePentacles", "King of Pentacles", "Pentacles", "#0ca30c", "#ffffff"),
    ("KingOfTheCups", "King of Cups", "Cups", "#3987e5", "#ffffff"),
]
# In-game achievement names, from Steam's GetSchemaForGame.
ACHIEVEMENT_NAMES = {
    "TheWorld": "The World", "TheStar": "The Star", "TheSun": "The Sun", "Temperance": "Temperance",
    "TheDevil": "The Devil", "TheTower": "The Tower", "KingOfTheWands": "King of Wands",
    "KingOfTheCups": "King of Cups", "KingOfTheSwords": "King of Swords", "KingOfThePentacles": "King of Pentacles",
    "QueenOfTheHighway": "Life of the Road", "BushidoAndChill": "Bushido and Chill", "TheFool": "The Fool",
    "TheLovers": "The Lovers", "TheWheelOfFortune": "The Wheel of Fortune", "TheHightPriestess": "The High Priestess",
    "AllThePresidentsMen": "All the President's Men", "IHateSpider": "Arachnophobia",
}
LABEL = {**ACHIEVEMENT_NAMES, **{k: lab for k, lab, *_ in MAIN + KINGS}}
COLOR = {k: c for k, _, _, c, _ in MAIN + KINGS}
GRAY = "#6d6c68"
SWEEP, SEPARATE, NONE = "#00b8c4", "#d95926", "#3a3a37"

SECTIONS = [
    ("about", "What this is"),
    ("main-first", "Main game: first ending"),
    ("world-only", "The World only and The Devil"),
    ("first-vs-ever", "First ending vs ever unlocked"),
    ("routes", "Which routes were open"),
    ("pl-first", "Phantom Liberty: first ending"),
    ("pl-main", "Phantom Liberty and the main ending"),
    ("next", "What players did next"),
    ("rushers", "Rushers"),
    ("completionists", "Completionists"),
    ("stops", "Where players stopped"),
    ("method", "Sampling bias and caveats"),
]

# Like the game's quests, each section is named after a song Johnny Silverhand might have liked.
SONGS = {
    "about": ("Every Breath You Take", "The Police"),
    "main-first": ("The End", "The Doors"),
    "world-only": ("Sympathy for the Devil", "The Rolling Stones"),
    "first-vs-ever": ("Once in a Lifetime", "Talking Heads"),
    "routes": ("Highway to Hell", "AC/DC"),
    "pl-first": ("Free Bird", "Lynyrd Skynyrd"),
    "pl-main": ("Should I Stay or Should I Go", "The Clash"),
    "next": ("Here I Go Again", "Whitesnake"),
    "rushers": ("Born to Run", "Bruce Springsteen"),
    "completionists": ("(I Can't Get No) Satisfaction", "The Rolling Stones"),
    "stops": ("Stuck in the Middle with You", "Stealers Wheel"),
    "method": ("Little Lies", "Fleetwood Mac"),
}


def song_kicker(anchor: str, n: int, extra_class: str = "") -> str:
    """'01 // THE END': the section's song title (artists are kept in SONGS for reference)."""
    return f"<div class='kicker {extra_class}'>{n:02d} // {html.escape(SONGS[anchor][0])}</div>"


st.set_page_config(page_title="What was your first Cyberpunk 2077 ending?", page_icon="◢", layout="wide",
                   initial_sidebar_state="collapsed")

# Interface colors (not data colors) live here: yellow / black / cyan, and red for Phantom Liberty.
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root { --accent: #fcee0a; --accent-2: #00f0ff; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
        --panel: #0b0b0b; --line: #fcee0a33; }
html, body, p, li, td, th, label, div.stMarkdown, button, input { font-family: 'Inter', sans-serif !important; }
.stApp { background: #000; color: var(--ink); }
h1, h2, h3 { font-family: 'Rajdhani', sans-serif !important; color: var(--accent) !important;
             text-transform: uppercase; letter-spacing: 0.04em; }
h1 { font-size: 3rem !important; line-height: 1.05 !important; }
h2 { font-size: 2rem !important; padding-top: 0.2rem !important; }
h3 { font-size: 1.2rem !important; color: var(--accent-2) !important; }
a { color: var(--accent-2) !important; }
section[data-testid="stSidebar"] { background: #070707; border-right: 1px solid #00f0ff33; }
section[data-testid="stSidebar"] a { color: var(--ink-2) !important; text-decoration: none; }
section[data-testid="stSidebar"] a:hover { color: var(--accent) !important; }
.kicker { font-family: 'Rajdhani', sans-serif; color: var(--accent-2); letter-spacing: 0.18em; font-size: 0.85rem;
          text-transform: uppercase; margin-bottom: -0.6rem; }
.kicker.sec { border-top: 1px solid var(--line); padding-top: 2.2rem; margin-top: 2.2rem; }
.kicker.intro { margin-top: 0.8rem; }
a.nav { display: block; padding: 3px 0; font-size: 0.9rem; }
a.nav span { color: var(--muted); font-family: 'Rajdhani', sans-serif; margin-right: 10px; }
.callout, .step, .kpi .l, .kpi .s, .lede, .howto { font-family: 'Inter', sans-serif !important; letter-spacing: normal; }
.lede { color: var(--ink-2); font-size: 1.05rem; max-width: 60rem; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 0.6rem 0 1.2rem; }
.kpi { background: var(--panel); border-left: 3px solid var(--accent); padding: 12px 14px;
       clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%); }
.kpi .v { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: var(--ink); line-height: 1.1; }
.kpi .l { color: var(--ink-2); font-size: 0.85rem; }
.kpi .s { color: var(--muted); font-size: 0.78rem; margin-top: 2px; }
.callout { border-left: 3px solid var(--accent-2); background: color-mix(in srgb, var(--accent-2) 6%, transparent);
           padding: 10px 14px; margin: 0.6rem 0 1rem; color: var(--ink-2); max-width: 60rem; }
.howto { color: var(--ink-2); font-size: 0.93rem; max-width: 60rem; margin: 0.2rem 0 1.1rem; padding-left: 14px;
         border-left: 1px dashed var(--muted); }
.howto .hl { display: block; font-family: 'Rajdhani', sans-serif; color: var(--muted); letter-spacing: 0.14em;
             font-size: 0.78rem; text-transform: uppercase; margin-bottom: 2px; }
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin: 0.8rem 0 1.2rem; }
.step { background: var(--panel); border-top: 2px solid var(--accent-2); padding: 12px 14px; color: var(--ink-2); }
.step b { color: var(--accent); font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; letter-spacing: 0.05em; }
.badge { display: inline-block; font-size: 0.75rem; color: #000; background: var(--accent); padding: 1px 8px;
         margin-left: 8px; vertical-align: middle; font-weight: 600; letter-spacing: 0.04em; }
/* Phantom Liberty sections: red-heavy variant of the same tokens */
[class*="st-key-pl_"] { --accent: #ff2a4d; --accent-2: #ff8095; --line: #ff2a4d40; }
[class*="st-key-pl_"] .badge { color: #fff; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load() -> dict:
    return json.loads(DATA.read_text())


S = load()
RM = S["run_metrics"]


def fmt(n) -> str:
    return f"{n:,}"


def pct(v, d=1) -> str:
    return "—" if v is None else f"{v:.{d}f}%"


def header(anchor: str, n: int, title: str, lede: str | None = None, clean_aware: bool = False) -> None:
    st.markdown(song_kicker(anchor, n, "sec"), unsafe_allow_html=True)
    st.header(title, anchor=anchor)
    if clean_aware and CLEAN:
        st.markdown("<span class='badge'>CLEAN DATA</span>", unsafe_allow_html=True)
    if lede:
        st.markdown(f"<p class='lede'>{lede}</p>", unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str | None]]) -> None:
    cards = "".join(f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div>"
                    f"{f'<div class=s>{s}</div>' if s else ''}</div>" for v, l, s in items)
    st.markdown(f"<div class='kpis'>{cards}</div>", unsafe_allow_html=True)


def callout(text: str) -> None:
    st.markdown(f"<div class='callout'>{text}</div>", unsafe_allow_html=True)


def how(text: str) -> None:
    """Plain-language note on reading the chart above it."""
    st.markdown(f"<div class='howto'><span class='hl'>How to read this</span>{text}</div>", unsafe_allow_html=True)


def toggle(label: str, options: list[str], key: str) -> str:
    return st.segmented_control(label, options, default=options[0], key=key, label_visibility="collapsed") or options[0]


# ------------------------------------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### Cyberpunk Stats")
    st.markdown("".join(f"<a class='nav' href='#{a}'><span>{i:02d}</span>{t}</a>" for i, (a, t) in enumerate(SECTIONS)),
                unsafe_allow_html=True)
    st.divider()
    CLEAN = st.toggle("Exclude flagged records", value=False,
                      help="A record is flagged when 8 or more achievements unlocked within one minute around an "
                           "ending, which is what unlock tools tend to do, or when an account finished an ending "
                           "with under 15 hours played. Sections marked CLEAN DATA change when this is on.")
    st.caption(f"Data: {fmt(RM['public_profiles'])} public Steam profiles. A fan project, not affiliated with "
               "CD PROJEKT RED.")

T = S["tracks_clean" if CLEAN else "tracks"]
T_ALL, T_CLEAN = S["tracks"], S["tracks_clean"]
MAIN_T, PL_T = T["main"], T["pl"]


def dist_parts(track: str, order: list[tuple]) -> list[dict]:
    fd, fd_all, fd_clean = T[track]["first_ending_distribution"], T_ALL[track]["first_ending_distribution"], \
        T_CLEAN[track]["first_ending_distribution"]
    parts = []
    for key, label, short, color, ink in order:
        if key not in fd:
            continue
        all_n, clean_n = fd_all.get(key, {}).get("count", 0), fd_clean.get(key, {}).get("count", 0)
        parts.append({"label": label, "short": short, "color": color, "ink": ink, "pct": fd[key]["pct"],
                      "tip": [["Players", fmt(fd[key]["count"])],
                              ["Share, everyone", pct(fd_all.get(key, {}).get("pct"), 2)],
                              ["Share without flagged players", pct(fd_clean.get(key, {}).get("pct"), 2)],
                              ["Flagged players", fmt(all_n - clean_n)]]})
    return parts


def dumbbell_rows(gap: dict, order: list[tuple]) -> list[dict]:
    return [{"label": lab, "a": gap[k]["first_ending_pct"], "b": gap[k]["unlock_pct"], "color": c,
             "valueLabel": f"{pct(gap[k]['unlock_pct'])}  ×{gap[k]['inflation_ratio']}",
             "tip": [["Saw it first", pct(gap[k]["first_ending_pct"], 2)],
                     ["Unlocked it at some point", pct(gap[k]["unlock_pct"], 2)],
                     ["Times bigger", f"×{gap[k]['inflation_ratio']}"]]}
            for k, lab, _, c, _ in order if k in gap]


FIRST_VS_EVER_LEGEND = [{"label": "Saw it first", "color": "#c3c2b7", "hollow": True},
                        {"label": "Unlocked it at some point", "color": "#c3c2b7"}]

# ------------------------------------------------------------------------------------------------ 00 about
st.markdown("<div class='kicker'>Cyberpunk Stats // a data project for curiosity and fun</div>", unsafe_allow_html=True)
st.markdown(song_kicker("about", 0, "intro"), unsafe_allow_html=True)
st.title("What was your first Cyberpunk 2077 ending?", anchor="about")
st.markdown(
    "<p class='lede'>Steam keeps a record of the exact second each achievement unlocks. Every ending in Cyberpunk "
    "2077 and Phantom Liberty has its own achievement, so the oldest ending achievement on a profile shows which "
    "ending that player saw first. For most people, that was their first playthrough. This page adds it up across "
    f"{fmt(RM['public_profiles'])} public Steam profiles.</p>", unsafe_allow_html=True)

st.markdown(f"""
<div class='steps'>
<div class='step'><b>1 · FIND PROFILES</b><br>Every Steam review of the game shows who wrote it. I collected the
profile behind each review: {fmt(RM['candidates_discovered'])} profiles in total.</div>
<div class='step'><b>2 · READ ACHIEVEMENTS</b><br>A profile is public when its owner lets anyone see their game
details. For public profiles, Steam's Web API lists each achievement and when it unlocked. The other
{pct(RM['private_pct_of_queried'])} were private, so their achievements are hidden and they're left out.</div>
<div class='step'><b>3 · FIND THE FIRST ENDING</b><br>The earliest ending achievement counts as the first ending,
once for the main game and once for Phantom Liberty. Achievements less than 5 minutes apart count as the same
credits roll.</div>
</div>""", unsafe_allow_html=True)

_fd_all, _fd_clean = T_ALL["main"]["first_ending_distribution"], T_CLEAN["main"]["first_ending_distribution"]
_clean_shift = max(abs(_fd_all[k]["pct"] - _fd_clean.get(k, {"pct": 0})["pct"]) for k in _fd_all)
why_col, flag_col = st.columns(2)
with why_col:
    st.markdown("### Why people who reviewed the game?")
    st.markdown(
        "<p class='lede'>Steam doesn't publish a list of who owns or plays a game. Reading someone's achievements "
        "takes their account, and the reviews on the store page are the only big public list of accounts that have "
        "played Cyberpunk 2077. Every review counts, positive or negative, in any language, however long the "
        "person played. Steam allows one review per account, so each review is one profile.</p>"
        "<p class='lede'>People who write reviews may care about the game more than the average player, and this "
        "data has no way to check that. The last section checks the part it can: whether private profiles look "
        "different from public ones.</p>", unsafe_allow_html=True)
with flag_col:
    st.markdown("### What's a flagged record?")
    st.markdown(
        "<p class='lede'>Some players unlock achievements with tools like Steam Achievement Manager or Cyber Engine "
        "Tweaks scripts, or load someone else's save right before the ending. Either way, there's no real "
        "playthrough behind those achievements. A record is flagged when 8 or more achievements unlocked within one minute of an ending, "
        "which is what a bulk unlock looks like, or when the account got an ending with less than 15 hours "
        "played.</p>"
        f"<p class='lede'>{fmt(RM['flagged_any'])} of {fmt(RM['completed_any'])} finishers are flagged "
        f"({pct(100 * RM['flagged_any'] / RM['completed_any'])}). They're counted by default. The Exclude flagged "
        "records switch in the sidebar (open it with the » button at the top left) takes them out, and sections marked CLEAN DATA change when it's on. The main "
        f"game shares move by {_clean_shift:.2f} points at most; the completionist numbers move the most.</p>",
        unsafe_allow_html=True)

kpis([
    (fmt(RM["candidates_discovered"]), "profiles found", None),
    (fmt(RM["public_profiles"]), "public profiles", f"{fmt(RM['private_profiles'])} private"),
    (fmt(T_ALL["main"]["strict_sample_n"]), "main game finishers counted", None),
    (fmt(T_ALL["pl"]["strict_sample_n"]), "Phantom Liberty finishers counted", None),
])

st.markdown("### From profiles to results")
funnel = [
    ("Profiles found", RM["candidates_discovered"], "One profile per Steam review of the game."),
    ("Profiles checked", RM["ids_queried"], "Achievement lookups made so far."),
    ("Public profiles", RM["public_profiles"], "Game details are visible, so the achievements can be read."),
    ("Finished an ending", RM["completed_any"], "At least one main game or Phantom Liberty ending."),
    ("Main game, counted", T_ALL["main"]["strict_sample_n"],
     f"Leaves out {fmt(T_ALL['main']['offline_sync_ties'])} players whose first two endings unlocked in the same "
     "second, so their order can't be told apart."),
    ("Phantom Liberty, counted", T_ALL["pl"]["strict_sample_n"],
     f"Leaves out {fmt(T_ALL['pl']['offline_sync_ties'])} players with two endings in the same second."),
]
render({"type": "hbars", "labelWidth": 200, "color": "#00b8c4",
        "rows": [{"label": l, "value": v, "display": fmt(v), "note": note,
                  "tip": [["Profiles", fmt(v)], ["Of profiles found", pct(100 * v / RM["candidates_discovered"])]]}
                 for l, v, note in funnel]})
how("Each bar is one step of collecting the data, and its length is the number of profiles still in at that step. "
    "Profiles drop out when they're private, when the player never finished an ending, or when two endings unlocked "
    "in the same second. That last one happens when a game played offline syncs its achievements all at once, so "
    "there's no telling which ending came first.")
callout("Every profile here belongs to someone who reviewed the game, and reviewers aren't a perfect match for all "
        "players. Private profiles are missing too. The last section checks how much that changes the results.")

# ------------------------------------------------------------------------------------------------ 01 main first
header("main-first", 1, "Main game: first ending",
       f"The first ending of {fmt(MAIN_T['strict_sample_n'])} players. Hover over a block to see how many players "
       "it stands for.", True)
render({"type": "segmented", "parts": dist_parts("main", MAIN)})
how("The bar is every player put together, and each colored block is one ending. The wider the block, the more "
    "players saw that ending first. The top three are close, so check the percentages printed on the blocks. "
    "On a small screen some blocks get too narrow for a label, and the list underneath has every share.")
callout("The World is the achievement for finishing the main story. The World only means a player got it with no "
        "ending achievement in the same credits roll. The next section looks at who those players are.")

# ------------------------------------------------------------------------------------------------ 02 world only
header("world-only", 2, "The World only and The Devil",
       "The World unlocks when the credits roll, and most endings unlock their own achievement in the same second. "
       "In about a quarter of first credits rolls, The World shows up alone. There are two known reasons.", True)
st.markdown(
    "- The Devil with Takemura dead. If Takemura is left behind in *Search and Destroy*, The Devil ending rolls "
    "credits without its achievement. It's the only base game route known to do this, and it probably explains "
    "most of the group.\n"
    "- Achievements that failed to unlock. Some of these players got a different ending and its achievement never "
    "popped. The data can estimate how many (see below).\n\n"
    "*Path of Least Resistance* and dying in *Don't Fear the Reaper* don't unlock anything, The World included, so "
    "those players aren't in these numbers at all.")
dt = MAIN_T["devil_total"]
g = dt["glitch_estimate"]
devil_red = COLOR["TheDevil"]
rows = [{"label": "Devil achievement only", "a": dt["achievement_pct"], "color": devil_red,
         "valueLabel": pct(dt["achievement_pct"]),
         "tip": [["Players", fmt(dt["achievement_count"])], ["Share", pct(dt["achievement_pct"], 2)]],
         "note": "Players who got The Devil with Takemura alive. The Devil can't be smaller than this."}]
floors = T_ALL["main"]["devil_total"].get("floors")
if floors and not CLEAN:
    rows += [
        {"label": "Plus rushers", "a": floors["rushers_pct"], "color": devil_red,
         "valueLabel": pct(floors["rushers_pct"]),
         "tip": [["Players", fmt(floors["rushers_count"])], ["Share", pct(floors["rushers_pct"], 2)]],
         "note": "Adds The World only players who hadn't finished Panam's or Rogue's questline and never unlocked "
                 "an ending afterwards. The Devil is about the only ending open to them."},
        {"label": "Plus no questline done", "a": floors["neither_questline_pct"], "color": devil_red,
         "valueLabel": pct(floors["neither_questline_pct"]),
         "tip": [["Players", fmt(floors["neither_questline_count"])],
                 ["Share", pct(floors["neither_questline_pct"], 2)]],
         "note": "Adds every The World only player who hadn't finished either questline before their first ending."},
    ]
rows += [
    {"label": "After glitch correction", "a": dt["adjusted_low_pct"], "b": dt["adjusted_high_pct"], "band": True,
     "color": devil_red, "valueLabel": f"{pct(dt['adjusted_low_pct'])} to {pct(dt['adjusted_high_pct'])}",
     "tip": [["Low end", pct(dt["adjusted_low_pct"], 2)], ["High end", pct(dt["adjusted_high_pct"], 2)],
             ["Failure rate used", f"{g['failure_rate_low_pct']}% to {g['failure_rate_high_pct']}%"]],
     "note": f"Takes out the {fmt(g['expected_glitched_low'])} to {fmt(g['expected_glitched_high'])} The World only "
             "players whose Star, Sun or Temperance achievement probably failed."},
    {"label": "Devil plus all The World only", "a": dt["total_pct"], "color": devil_red,
     "valueLabel": pct(dt["total_pct"]),
     "tip": [["Players", fmt(dt["total_count"])], ["Share", pct(dt["total_pct"], 2)]],
     "note": "Counts every The World only first ending as The Devil. The Devil can't be bigger than this."},
]
st.markdown("### How big could The Devil be?")
render({"type": "dumbbell", "rows": rows, "max": 35, "labelWidth": 200})
how("Each row is one way of counting The Devil, from the strictest at the top to the most generous at the bottom. "
    "A dot is a single number and the thick bar is a range. The top row counts only The Devil achievement. Each row "
    "below adds a group of The World only players who most likely got The Devil too. Hover over a row to see which "
    "players it adds.")
if CLEAN:
    callout("The two questline rows are only worked out for all records, so they're hidden while flagged records are "
            "left out.")

callout(f"How often do achievements fail? The World should unlock in the same second as The Star or The Sun, and "
        f"it was missing in {pct(g['world_missing_star_sun']['pct'], 2)} of those credits rolls. The Star can't be "
        f"reached without Panam's questline, yet {pct(g['star_without_panam']['pct'], 2)} of players whose first "
        "ending was The Star didn't have its achievement, Life of the Road, at the time. Those two rates set the low "
        "and high ends of the correction.")

st.markdown("### What The World only players did afterwards")
st.markdown("<p class='lede'>A Devil save with Takemura dead can be reloaded to reach The Sun, The Star or "
            "Temperance, but it can't unlock The Devil achievement. A Devil achievement later on means another "
            "playthrough, an unlock tool, or a first ending whose achievement failed.</p>", unsafe_allow_html=True)
ub = S["unmarked_breakdown"]
ub_labels = {"no_named_ending": "Never got an ending achievement",
             "named_not_devil": "Later got The Sun, The Star, Temperance or The Tower",
             "devil_lt_4h": "Later got The Devil, within 4 hours", "devil_4h_to_24h": "Later got The Devil, 4 to 24 hours after",
             "devil_ge_24h": "Later got The Devil, a day or more after"}
render({"type": "hbars", "labelWidth": 400, "color": COLOR[UNMARKED], "max": 100,
        "rows": [{"label": ub_labels[k], "value": b["pct"], "display": pct(b["pct"]),
                  "tip": [["Players", fmt(b["count"])], ["Share", pct(b["pct"], 2)], ["Flagged", fmt(b["flagged"])]]}
                 for k, b in ub["buckets"].items()]})
late_devil = sum(ub["buckets"][k]["pct"] for k in ("devil_lt_4h", "devil_4h_to_24h", "devil_ge_24h"))
how(f"Each bar is the share of The World only players who did that next. Most either stopped there or went on to "
    f"a different ending. About {pct(late_devil, 0)} came back for The Devil, and nearly all of them did it at "
    "least a day later, which looks like a new playthrough.")
st.caption(f"All records, {fmt(ub['n'])} players.")

# ------------------------------------------------------------------------------------------------ 03 first vs ever
header("first-vs-ever", 3, "First ending vs ever unlocked",
       "How many players unlocked each ending at some point, next to how many saw it first.", True)
render({"type": "dumbbell", "rows": dumbbell_rows(MAIN_T["first_vs_unlock_gap"], MAIN), "max": 100,
        "labelWidth": 130, "legend": FIRST_VS_EVER_LEGEND})
how("Each line is one ending. The hollow circle on the left is the share of players who saw that ending first, and "
    "the filled dot on the right is the share who unlocked it at any point, through replays or by reloading a save. "
    "A longer line means more players came back for that ending later. The number after the × says how many times "
    "bigger the second figure is.")
gap = MAIN_T["first_vs_unlock_gap"]
callout(f"Steam's global achievement percentages count every unlock, replays included. By that count The Devil "
        f"looks {gap['TheDevil']['inflation_ratio']} times as common as it is among first endings, and The Tower "
        f"{gap['TheTower']['inflation_ratio']} times.")

# ------------------------------------------------------------------------------------------------ 04 routes
header("routes", 4, "Which routes were open",
       "Had the player finished Panam's questline (Life of the Road, needed for The Star) or Rogue's (Bushido and "
       "Chill) before their first ending?")
ra = S["route_availability"]
cols = [("panam", "Panam's done"), ("rogue", "Rogue's done"), ("neither", "Neither")]
rows_k = [(k, lab) for k, lab, *_ in MAIN if k in ra and ra[k]["n"]]
render({"type": "heatmap", "rows": [lab for _, lab in rows_k], "cols": [c for _, c in cols], "max": 100,
        "cells": [[{"v": ra[k][c]["pct"], "colLabel": cl, "small": ra[k]["n"] < MIN_CELL_N,
                    "tip": [["Players", fmt(ra[k][c]["count"])], ["Of this first ending", pct(ra[k][c]["pct"], 2)],
                            ["Players with this first ending", fmt(ra[k]["n"])]]}
                   for c, cl in cols] for k, _ in rows_k]})
how("Each row is a first ending and each column is a questline. The number in a square is the share of those "
    "players who had finished it, and brighter squares mean bigger shares. Read along a row to see what was open "
    "to that group. A row can add up to more than 100%, because plenty of players had done both questlines.")
callout(f"{pct(ra[UNMARKED]['neither']['pct'])} of The World only players had done neither questline, against "
        f"{pct(ra['TheDevil']['neither']['pct'])} for The Devil achievement and under "
        f"{pct(max(ra[k]['neither']['pct'] for k in ('TheSun', 'TheStar', 'Temperance')) + 0.5, 0)} for The Sun, "
        "The Star and Temperance. Without either questline, The Devil is close to the only base game ending left.")

# ------------------------------------------------------------------------------------------------ 05 + 06 PL
with st.container(key="pl_sections"), theme("pl"):
    header("pl-first", 5, "Phantom Liberty: first ending",
           f"The first Phantom Liberty ending of {fmt(PL_T['strict_sample_n'])} players.", True)
    render({"type": "segmented", "parts": dist_parts("pl", KINGS)})
    how("The same kind of bar as the main game: every player together, one block per ending. King of Wands takes "
        "up more than half of it.")
    st.markdown("### First vs ever unlocked")
    render({"type": "dumbbell", "rows": dumbbell_rows(PL_T["first_vs_unlock_gap"], KINGS), "max": 100,
            "labelWidth": 150, "legend": FIRST_VS_EVER_LEGEND})
    how("Read it like the main game version: the hollow circle is the share who saw that ending first, the filled dot "
        "the share who unlocked it at any point. King of Wands has the shortest line, so fewer players went back "
        "for it after seeing another ending first.")

    header("pl-main", 6, "Phantom Liberty and the main ending",
           "Did finishing Phantom Liberty change which main ending people got first? Players are split by whether "
           "they finished the expansion before their first main ending (usually in the same playthrough), after it, "
           "or not at all.")
    pv = S["pl_vs_main"]
    view = toggle("View", ["All", "Without The Tower", "Same game version", "Same routes open"], "pl_view")
    GROUPS = [("pl_before", "Finished PL first"), ("pl_after", "Finished PL later"), ("no_pl_ending", "No PL ending")]
    ROUTES = {"Both questlines": "both", "Panam only": "panam_only", "Rogue only": "rogue_only", "Neither": "neither"}
    if view == "Same routes open":
        route = st.selectbox("Questlines done before the first ending", list(ROUTES), key="pl_route")
        src = pv["pl_era_by_routes"][ROUTES[route]]
    else:
        src = pv[{"All": "by_pl_status", "Without The Tower": "by_pl_status_no_tower",
                  "Same game version": "pl_era_no_tower"}[view]]
    keys = [m for m in MAIN if view == "All" or m[0] != "TheTower"]
    rows = [{"label": gl, "sub": f"{fmt(src[g_]['n'])} players", "n": src[g_]["n"], "parts": src[g_]["pct"],
             "empty": f"Fewer than {MIN_CELL_N} players" if src[g_]["n"] < MIN_CELL_N else None}
            for g_, gl in GROUPS]
    render({"type": "stacked", "labelWidth": 230, "rows": rows,
            "keys": [{"key": k, "label": lab, "color": c, "ink": ink} for k, lab, _, c, ink in keys]})
    how("Each bar is one group of players, split by their first main ending. Compare the same color across the "
        "three bars. The buttons change who is counted. Without The Tower leaves it out, because The Tower can only "
        "be reached through Phantom Liberty. Same game version keeps only endings reached after the expansion came "
        "out. Same routes open compares players who had the same side questlines done.")
    bp = pv["pl_era_both_routes_pct"]
    callout(f"Players who finished Phantom Liberty first had more endings open to them: {pct(bp['pl_before'])} had "
            f"both questlines done by their first ending, compared with {pct(bp['pl_after'])} of those who played "
            f"it later and {pct(bp['no_pl_ending'])} of those who never finished it.")

    st.markdown("### Does the Phantom Liberty ending predict the main ending?")
    order_v = toggle("Order", ["Phantom Liberty first", "Main game first"], "king_order")
    if order_v == "Phantom Liberty first":
        with_tower = toggle("Tower", ["Without The Tower", "With The Tower"], "king_tower") == "With The Tower"
        src = pv["king_to_main_pl_before" if with_tower else "king_to_main_pl_before_no_tower"]
        cols = [m for m in MAIN if with_tower or m[0] != "TheTower"]
        rows_k = [(k, lab) for k, lab, *_ in KINGS]
        st.caption("Players who finished Phantom Liberty before their first main ending. Their Phantom Liberty ending decides "
                   "whether The Tower is even possible, so it's left out unless you switch it on.")
    else:
        src = pv["main_to_king_pl_after"]
        cols = KINGS
        rows_k = [(k, lab) for k, lab, *_ in MAIN if k in src]
        st.caption("Players who finished Phantom Liberty after their first main ending.")
    render({"type": "heatmap", "rows": [lab for _, lab in rows_k], "cols": [m[2] for m in cols], "labelWidth": 150,
            "cells": [[{"v": src[k]["pct"].get(c[0]), "colLabel": c[1], "small": src[k]["n"] < MIN_CELL_N,
                        "tip": [["Share of row", pct(src[k]["pct"].get(c[0]), 2)],
                                ["Players in row", fmt(src[k]["n"])]]}
                       for c in cols] for k, _ in rows_k]})
    small_rows = any(src[k]["n"] < MIN_CELL_N for k, _ in rows_k)
    how("Each row is one group of players and each column is where they ended up. Every row adds up to 100%. If "
        "all the rows look about the same, the first ending in one part of the game says little about the other."
        + (f" Squares marked — have fewer than {MIN_CELL_N} players." if small_rows else ""))

# ------------------------------------------------------------------------------------------------ 07 next
header("next", 7, "What players did next",
       "Where players went after their first ending. A reload sweep is a second ending less than 4 hours after the "
       "first, usually from a save made before the final choice.", True)
track = toggle("Track", ["Main game", "Phantom Liberty"], "next_track")
tkey, order = ("main", MAIN) if track == "Main game" else ("pl", KINGS)
tr = T[tkey]["transitions"]
nodes, links, totals = [], [], {}
for k, lab, _, c, _ in order:
    if k not in tr:
        continue
    tt = tr[k]["transition_types"]
    nodes.append({"id": f"f:{k}", "label": lab, "color": c,
                  "tip": [["Players", fmt(tr[k]["n"])],
                          ["Reload sweep", pct(tt.get("save_reload_sweep", {}).get("pct"))],
                          ["New playthrough", pct(tt.get("separate_playthrough", {}).get("pct"))],
                          ["No second ending", pct(tt.get("no_second_ending", {}).get("pct"))]]})
for k, lab, _, c, _ in order:
    if k != UNMARKED:
        nodes.append({"id": f"s:{k}", "label": lab, "color": c, "tip": []})
nodes.append({"id": "s:none", "label": "No second ending", "color": NONE, "tip": []})
for k, lab, _, c, _ in order:
    if k not in tr:
        continue
    t = tr[k]
    for k2, cnt in t["second_ending"].items():
        links.append({"source": f"f:{k}", "target": f"s:{k2}", "value": cnt,
                      "tip": [["Players", fmt(cnt)], ["Of this first ending", pct(100 * cnt / t["n"])]]})
        totals[k2] = totals.get(k2, 0) + cnt
    none = t["transition_types"].get("no_second_ending", {}).get("count", 0)
    links.append({"source": f"f:{k}", "target": "s:none", "value": none,
                  "tip": [["Players", fmt(none)], ["Of this first ending", pct(100 * none / t["n"])]]})
    totals["none"] = totals.get("none", 0) + none
for n in nodes:
    if n["id"].startswith("s:"):
        n["tip"] = [["Players arriving here", fmt(totals.get(n["id"][2:], 0))]]
nodes = [n for n in nodes if not n["id"].startswith("s:") or totals.get(n["id"][2:], 0) > 0]
render({"type": "sankey", "nodes": nodes, "links": links, "height": 440,
        "headers": ["FIRST ENDING", "NEXT ENDING"]})
how("First endings are on the left, and the next ending each player unlocked is on the right. The width of each "
    "stream is the number of players who took that path; hover over one to see how many. The gray block at the "
    "bottom right is everyone who never unlocked a second ending.")

st.markdown("### Reload sweep or new playthrough")
rows = []
for k, lab, *_ in order:
    if k in tr:
        tt = tr[k]["transition_types"]
        rows.append({"label": lab, "n": tr[k]["n"],
                     "parts": {x: tt.get(x, {}).get("pct", 0)
                               for x in ("save_reload_sweep", "separate_playthrough", "no_second_ending")}})
render({"type": "stacked", "labelWidth": 150, "rows": rows,
        "keys": [{"key": "save_reload_sweep", "label": "Reload sweep (under 4 hours)", "color": SWEEP, "ink": "#0b0b0b"},
                 {"key": "separate_playthrough", "label": "New playthrough", "color": SEPARATE},
                 {"key": "no_second_ending", "label": "No second ending", "color": NONE}]})
how("Each bar splits the players with one first ending three ways: those who reloaded a save for a second ending "
    "within 4 hours, those who came back later in a new playthrough, and those who stopped at one ending.")

# ------------------------------------------------------------------------------------------------ 08 rushers
header("rushers", 8, "Rushers",
       "A rusher is someone whose first ending was The World only, who hadn't finished Panam's or Rogue's questline "
       "before it, and who never unlocked an ending achievement afterwards. They followed the main story to the "
       "end and stopped.")
rp = S["rusher_playtime"]
rg = rp["groups"]
RG = [("rushers", "Rushers", COLOR[UNMARKED]), ("single_ending_not_rushers", "One ending, not rushers", GRAY),
      ("single_ending_thedevil", "One ending: The Devil", GRAY),
      ("single_ending_star_sun_temperance", "One ending: The Star, The Sun or Temperance", GRAY),
      ("everyone_else", "Every other finisher", GRAY)]
kpis([(fmt(rg["rushers"]["n"]), "rushers",
       f"{pct(100 * rg['rushers']['n'] / T_ALL['main']['strict_sample_n'])} of main game finishers"),
      (f"{rg['rushers']['median_h']}h", "typical (median) playtime",
       f"against {rg['single_ending_not_rushers']['median_h']}h for other players with one ending"),
      (pct(100 * rp["vs_single_ending"]["p_less"], 0), "chance a random rusher played less",
       "than a random non-rusher with one ending")])
render({"type": "ranges", "unit": "h", "labelWidth": 300,
        "rows": [{"label": lab, "color": c, "p25": rg[k]["p25_h"], "median": rg[k]["median_h"],
                  "p75": rg[k]["p75_h"],
                  "tip": [["Players", fmt(rg[k]["n"])], ["Median", f"{rg[k]['median_h']}h"],
                          ["Middle half", f"{rg[k]['p25_h']} to {rg[k]['p75_h']}h"], ["Average", f"{rg[k]['mean_h']}h"]]}
                 for k, lab, c in RG if rg[k]["n"]],
        "legend": [{"label": "Middle half of the group; white line = median", "color": GRAY}]})
how("Each bar covers the hours played by the middle half of a group: a quarter of the group played less than its "
    "left edge, and a quarter played more than its right edge. The white line is the median, where half played "
    "less and half played more. The rushers' bar sits well to the left of everyone else's.")
st.caption("Playtime is the account's total. Replays add hours, so players with one ending make the fairest "
           "comparison.")

with st.container(key="pl_rushers"), theme("pl"):
    st.markdown("### Rushers in Phantom Liberty")
    rk = S["pl_vs_main"]["rusher_kings"]
    RKG = [("rushers", "Rushers", COLOR[UNMARKED]), ("world_only_not_rushers", "The World only, not rushers", GRAY),
           ("everyone_else", "Every other finisher", GRAY)]
    render({"type": "hbars", "labelWidth": 230, "max": 100,
            "rows": [{"label": lab, "value": rk["finish_rate"][k]["finished_pl_pct"], "color": c,
                      "display": f"{pct(rk['finish_rate'][k]['finished_pl_pct'])} finished Phantom Liberty",
                      "tip": [["Main game finishers", fmt(rk["finish_rate"][k]["n"])],
                              ["Finished Phantom Liberty", fmt(rk["finish_rate"][k]["finished_pl"])]]}
                     for k, lab, c in RKG]})
    how("The share of each group that also finished Phantom Liberty.")
    rk_view = toggle("Rusher order", ["Any order", "Phantom Liberty first", "Phantom Liberty later"], "rk_view")
    src = rk["all"] if rk_view == "Any order" else \
        rk["by_order"]["pl_before" if rk_view == "Phantom Liberty first" else "pl_after"]
    rows = [{"label": lab, "sub": f"{fmt(src[k]['n'])} players", "n": src[k]["n"], "parts": src[k]["pct"],
             "empty": f"Fewer than {MIN_CELL_N} players" if src[k]["n"] < MIN_CELL_N else None} for k, lab, _ in RKG]
    render({"type": "stacked", "labelWidth": 280, "rows": rows,
            "keys": [{"key": k, "label": lab, "color": c, "ink": ink} for k, lab, _, c, ink in KINGS]})
    how("For the players in each group who did finish Phantom Liberty, the bar shows which Phantom Liberty ending they got "
        "first.")

# ------------------------------------------------------------------------------------------------ 09 completionists
header("completionists", 9, "Completionists",
       "How many ending achievements each player has. The most common results are one ending and all of them.", True)
cp = S["completionists"]
c1, c2 = st.columns(2)
for col, (tk, title, color) in zip((c1, c2), (("main", "Main game endings unlocked", "#3987e5"),
                                              ("pl", "Phantom Liberty endings unlocked", "#d95926"))):
    eu = cp["endings_unlocked"][tk]
    with col:
        st.markdown(f"### {title}")
        render({"type": "columns", "color": color, "xLabel": f"endings unlocked · {fmt(eu['n'])} finishers",
                "bars": [{"x": x, "value": v["pct"], "display": pct(v["pct"], 0),
                          "title": f"{x} ending{'s' if x != '1' else ''}",
                          "tip": [["Players", fmt(v["count"])], ["Of finishers", pct(v["pct"], 2)]]}
                         for x, v in eu["counts"].items() if x != "0"]})
how("Each column is a number of endings unlocked, and its height is the share of finishers with exactly that many. "
    "The tall columns at both ends show that players tend to stop after one ending or collect the whole set.")
sets = cp["sets"]
SET_LABELS = {"main_all": "All 5 main endings", "main_base_four": "All 4 base game endings",
              "pl_all": "All 4 Phantom Liberty endings", "everything": "All 9 endings"}
kpis([(pct(sets[k]["clean_pct" if CLEAN else "pct"]), SET_LABELS[k],
       f"{sets[k]['median_span_days']} days from first to last (median) · {pct(sets[k]['flagged_pct'], 0)} flagged")
      for k in SET_LABELS])
callout("Unlock tools add whole sets of achievements at once, and about a fifth of completionists are flagged for "
        "it. This is where switching on Exclude flagged records changes the numbers most. Each percentage is out of "
        "the players who finished that part of the game, or both parts for all 9 endings.")

# ------------------------------------------------------------------------------------------------ 10 stops
header("stops", 10, "Where players stopped",
       "Story achievements, in the order the game hands them out.")
sf_track = toggle("Funnel", ["Main game", "Phantom Liberty"], "sf_track")
sf = S["story_funnel"]["main" if sf_track == "Main game" else "pl"]
stage_names = {s_["stage"]: f"{s_['stage']} · {LABEL.get(s_['achievement'], s_['achievement'])}"
               for s_ in sf["stages"] if s_["achievement"]}
st.caption(f"Out of {fmt(sf['base_n'])} players" + (" who started Phantom Liberty (saved President Myers) or "
                                                    "finished it." if sf_track != "Main game"
                                                    else " with public profiles."))
render({"type": "hbars", "labelWidth": 400, "max": 100, "color": "#00b8c4",
        "rows": [{"label": stage_names.get(s_["stage"], s_["stage"]), "value": s_["pct_of_base"],
                  "display": pct(s_["pct_of_base"]),
                  "tip": [["Reached", fmt(s_["reached"])], ["Of everyone", pct(s_["pct_of_base"], 2)],
                          ["Of the step before", pct(s_["pct_of_previous"], 2)]]} for s_ in sf["stages"]]})
how("Each bar is the share of players who reached that point in the story. The bars get shorter as people drop "
    "off. The last bar is everyone who finished.")
st.markdown(f"### Where the {fmt(sf['not_finished'])} who didn't finish stopped")
render({"type": "hbars", "labelWidth": 400, "max": 100, "color": GRAY,
        "rows": [{"label": stage_names.get(lab, lab), "value": v["pct_of_non_finishers"] or 0,
                  "display": pct(v["pct_of_non_finishers"]),
                  "color": "#00b8c4" if lab == sf["most_common_stop"] else GRAY,
                  "tip": [["Players", fmt(v["count"])], ["Of those who didn't finish", pct(v["pct_of_non_finishers"], 2)],
                          ["Median playtime", f"{v['median_playtime_h']}h" if v["median_playtime_h"] else "—"]]}
                 for lab, v in sf["stopped_after"].items()]})
how("This one only counts players who never finished. Each bar is the last story point they reached, and the "
    "highlighted bar is the most common place to stop. Hover to see how many hours those players had put in.")

# ------------------------------------------------------------------------------------------------ 11 method
header("method", 11, "Sampling bias and caveats",
       "Private profiles hide achievements, but Steam still shows how long the reviewer has played. That lets the "
       "two groups be compared on hours.")
sb = S["sampling_bias"]
render({"type": "dumbbell", "labelWidth": 110,
        "rows": [{"label": band, "a": v["public_pct"], "b": v["private_pct"], "color": "#00b8c4",
                  "valueLabel": "", "tip": [["Public", pct(v["public_pct"], 2)], ["Private", pct(v["private_pct"], 2)]]}
                 for band, v in sb["playtime_bands"].items()],
        "legend": [{"label": "Public profiles", "color": "#00b8c4", "hollow": True},
                   {"label": "Private profiles", "color": "#00b8c4"}]})
how("Each row is a range of hours played. The hollow circle is the share of public profiles in that range and the "
    "filled dot is the share of private ones. Short lines mean the two groups look alike.")
shift = max(abs(sb["first_ending_reweighted_to_private"][k] - sb["first_ending_public"][k])
            for k in sb["first_ending_public"])
kpis([(f"{sb['median_playtime_h']['public']}h / {sb['median_playtime_h']['private']}h",
       "median playtime, public / private", None),
      (f"{shift:.2f} points", "biggest change to any first ending share",
       "when public players are weighted to match private playtime"),
      (f"{pct(sb['devil_if_hidden_finishers_none_devil_pct'])} to {pct(sb['devil_if_hidden_finishers_all_devil_pct'])}",
       "The Devil plus The World only, worst case for mods",
       f"if the {fmt(sb['hanako_no_finish_100h'])} players with 100+ hours stuck after The High Priestess had "
       "finished without an achievement")])
st.markdown("### Caveats")
st.markdown(f"""
- Every profile here belongs to someone who reviewed the game on Steam, which isn't a random sample of all players.
- Playtime is the account's total when the profile was read, not when the review was written.
- Achievements less than 5 minutes apart count as the same credits roll. Players with two endings in the same second
  are left out, since their order can't be told.
- The Phantom Liberty figures only include players who reached a Phantom Liberty ending.
- The Tower doesn't unlock The World. It has its own achievement, so it's still counted normally.
- Some modded games unlock no achievements at the end, so those players count as never finished.
  {fmt(RM['base_ending_no_world'])} players have a base game ending achievement but no The World (for example, they
  quit during the credits); they're counted by their ending achievement.
- Unlock tools and downloaded saves exist. The flags catch bulk unlocks and accounts with very little playtime, but
  not a single achievement unlocked by hand.
""")
with st.expander("Extra check: does each ending unlock The World?"):
    wc = S["world_cosync"]
    st.dataframe([{"First ending": LABEL.get(k, k), "Players": v["n"],
                   "Same credits roll %": v["within_grace"]["pct"],
                   "The World under 2h later %": v["world_later_lt_2h"]["pct"],
                   "The World 2h+ later %": v["world_later_ge_2h"]["pct"],
                   "The World earlier %": v["world_earlier"]["pct"],
                   "No The World %": v["no_world"]["pct"]} for k, v in wc.items()], hide_index=True)
    st.caption("Main game endings: the first of the five main endings. Phantom Liberty endings: the first of all nine endings.")
with st.expander("Achievement names"):
    st.dataframe([{"Achievement": LABEL.get(k, k), "Steam API name": v} for k, v in S["achievement_mapping"].items()],
                 hide_index=True)
st.caption(f"Cyberpunk Stats · a fan project, not affiliated with CD PROJEKT RED · data from "
           f"{datetime.fromtimestamp(S['generated_at']).strftime('%Y-%m-%d')}")
