"""Game facts shared by the collector and the Kedro pipelines: achievement names, story markers, timing rules."""
from __future__ import annotations

APPID = 1091500

# Two independent tracks: which main-game ending and which Phantom Liberty ending came first.
MAIN_ENDINGS = ["TheStar", "TheSun", "Temperance", "TheDevil", "TheTower"]
PL_ENDINGS = ["KingOfTheWands", "KingOfTheCups", "KingOfTheSwords", "KingOfThePentacles"]
COMPLETION = "TheWorld"  # main-game credits; used to detect endings with no achievement of their own
TRACKED = MAIN_ENDINGS + PL_ENDINGS + [COMPLETION]
TRACKS = {
    "main": {"title": "Main game", "endings": MAIN_ENDINGS, "extra": [COMPLETION]},
    "pl": {"title": "Phantom Liberty", "endings": PL_ENDINGS, "extra": []},
}

# TheWorld with no ending achievement before it. Most likely The Devil with Takemura dead (left to die in
# Search and Destroy, which skips the TheDevil achievement), plus some ending achievements that failed to pop.
UNMARKED = "TheWorld only (no ending achievement)"

SYNC_GRACE_S = 300       # unlocks within 5 min are treated as the same credits roll
SWEEP_WINDOW_S = 14400   # < 4h between endings = save-reload sweep

# Side-questline achievements that gate the TheStar / TheSun routes (checked against the data:
# ~98% of TheStar-first players have QueenOfTheHighway before their ending, ~93% of TheSun-first
# players have BushidoAndChill).
PANAM_MARKER = "QueenOfTheHighway"  # "Life of the Road": Panam's questline, required for TheStar
ROGUE_MARKER = "BushidoAndChill"    # watch Bushido X with Rogue: Rogue's questline. Not strictly required
                                    # for TheSun or Temperance (e.g. Don't Fear the Reaper gives TheSun).

CO_SYNC_ENDINGS = ["TheStar", "TheSun", "Temperance"]  # unlock in the same second as TheWorld

# Story milestones in play order (Steam apinames). TheHermit (finding Alt) is left out: about a fifth of
# finishers unlock it after TheHightPriestess, so it doesn't mark a fixed point in the story.
MAIN_MILESTONES = [("Became a mercenary (end of prologue)", "TheFool"),
                   ("Stole the Relic (end of Act 1)", "TheLovers"),
                   ("Interrogated Hellman (Act 2)", "TheWheelOfFortune"),
                   ("Talked with Hanako (end of Act 2)", "TheHightPriestess")]
# Both PL milestones come early; later PL achievements (e.g. Kingmaker / Spin Doctor) depend on the
# route taken, so nothing marks progress between the Chimera and the endings.
PL_MILESTONES = [("Saved President Myers (start)", "AllThePresidentsMen"),
                 ("Defeated the Chimera (early)", "IHateSpider")]

PL_RELEASE_TS = 1695686400  # 2023-09-26, Phantom Liberty and update 2.0
MAIN_ORDER = ["TheSun", "TheStar", "Temperance", "TheDevil", UNMARKED, "TheTower"]
