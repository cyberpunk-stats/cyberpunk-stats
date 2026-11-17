# What was your first Cyberpunk 2077 ending?

This is a data project made entirely out of curiosity and for fun, because I'm a little obsessive about Cyberpunk 2077. I read Steam achievement unlock times from public profiles of people who reviewed Cyberpunk 2077, and treat the earliest ending achievement as the first ending to figure out which endings people tend to pick on their first playthrough.

Live dashboard: https://cyberpunk-stats.streamlit.app/

This project is not affiliated with CD PROJEKT RED.

## How it works

1. The collector command `cyberpunk-stats-collect` reads the game's Steam reviews to find profiles, then fetches each public profile's achievements from the Steam Web API into a resumable SQLite checkpoint at `data/01_raw/checkpoint.sqlite`.
2. A [Kedro](https://kedro.org/) project (`kedro run`) with three pipelines, ingest, classification and endings, turns the checkpoint into `data/08_reporting/endings_summary.json`. The output holds aggregates only, with no SteamIDs inside.
3. A Streamlit app in `app/` draws the dashboard from that JSON with D3 charts.

The collector stays separate from Kedro because it is long-running, rate-limited, and resumable. It needs network access and an API key. Kedro handles the reproducible analysis part.

## Why people who reviewed the game?

Steam does not publish who owns or plays a game. Store page reviews are the only large public list of accounts that have played it. Every review counts: positive or negative, any language, any playtime. Steam allows one review per account.

Reviewers may care about the game more than the average player. That possible bias cannot be measured from this data alone.

## Just looking at the dashboard locally

The repo already includes `data/08_reporting/endings_summary.json`, so you can skip the collection step. Install the app dependencies and run:

```bash
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

Run that from the repo root. No API key is needed.

## Collecting your own data

You will need Python 3.10 or newer.

```bash
git clone <repo-url>
cd cyberpunk-stats
pip install -e ".[dev]"
pip install -r app/requirements.txt
```

The first install brings the collector, Kedro and pytest. The second adds Streamlit for the dashboard.

Get a Steam API key (see the next section). Create a `.env` file in the repo root:

```bash
STEAM_API_KEY=your_key_here
```

The `.env` file is gitignored. Never commit or share it.

Start collecting:

```bash
cyberpunk-stats-collect --target-samples 3000
```

The default target is 3000 completed players. The tool checkpoints constantly and can be stopped with Ctrl+C, then resumed later:

```bash
cyberpunk-stats-collect --resume
```

You can widen the sample by switching the review feed:

```bash
cyberpunk-stats-collect --resume --review-filter helpful
```

Choices are `helpful`, `recent`, and `updated`.

If some lookups failed earlier, requeue them:

```bash
cyberpunk-stats-collect --resume --retry-errors
```

After collection finishes, build the summary:

```bash
kedro run
```

Kedro reads the checkpoint from `data/01_raw/checkpoint.sqlite`. If you saved it somewhere else with `--checkpoint`, move it there or change the path in `conf/base/catalog.yml`.

Then launch the dashboard:

```bash
streamlit run app/streamlit_app.py
```

The default rate is 1.3 requests per second, so large samples take days. The run pauses automatically after 10 failed lookups in a row, which often means the daily API limit was hit, and it retries later.

| Option | Description |
| --- | --- |
| `-h`, `--help` | Show the help message and exit |
| `--target-samples` | Stop after this many public profiles with at least one completed ending, main game or Phantom Liberty (default: 3000) |
| `--min-playtime-mins` | Skip reviewers below this lifetime playtime; 0 means off; completion is decided by achievements (default: 0) |
| `--checkpoint` | SQLite checkpoint path (default: `data/01_raw/checkpoint.sqlite`) |
| `--resume` | Continue from an existing checkpoint |
| `--review-filter` | Review feed to sample: `helpful`, `recent`, or `updated` (default: `recent`); use with `--resume` and another filter to widen the sample |
| `--rate` | Maximum requests per second (default: 1.3) |
| `--map` | Override an achievement's Steam API name, for example `--map TheStar=ACH_STAR` (repeatable). Only needed if Steam renames an achievement |
| `--retry-errors` | With `--resume`, put previously failed lookups back in the queue |
| `--error-pause-mins` | Pause after 10 failed lookups in a row; doubles each time, up to 4 hours (default: 30) |
| `-v`, `--verbose` | Verbose output |

## Getting a Steam API key

1. Log in to Steam in a browser.
2. Go to https://steamcommunity.com/dev/apikey.
3. Enter a domain name. For personal use anything works, for example `localhost`.
4. Agree to the Steam Web API Terms of Use and register.
5. Copy the key.

Steam only gives keys to accounts that are not "limited." A limited account is one that has not spent at least 5 USD in the Steam store. Steam may ask you to confirm with the Steam Guard Mobile Authenticator. The terms limit you to 100,000 API calls per day. The key is tied to your account, so treat it like a password and revoke it on the same page if it leaks. The review feed itself needs no key; only the achievement and schema lookups do.

## What gets flagged

A record is flagged when 8 or more achievements unlock within 60 seconds around an ending or The World, or when an ending appears on an account with under 15 hours played. These look like unlock tools or downloaded saves. The thresholds live in `conf/base/parameters.yml`. The dashboard has a switch to exclude flagged records.

## Project layout

```
app/                                Streamlit dashboard and D3 charts
conf/base/                          Kedro catalog and parameters
data/01_raw/                        SQLite checkpoint from the collector
data/08_reporting/                  Aggregated JSON output for the dashboard
src/cyberpunk_stats/
  collect/                          Steam API client, checkpoint and the collector command
  domain/                           Game constants and ending classification, shared by both halves
  pipelines/ingest/                 Reads the checkpoint tables
  pipelines/classification/         Builds per-player records and flags
  pipelines/endings/                Computes the aggregate statistics
tests/                              Test suite
```

## Tests

Run the test suite with:

```bash
pytest
```

## Privacy

The checkpoint holds SteamIDs and raw achievement lists. It is gitignored, along with everything in `data/` except `endings_summary.json`. The `endings_summary.json` file contains only aggregates. Private profiles can't be read, so the collector only records that they're private, and the only thing used from them is the playtime shown on their review. Nothing is published per player.

## Caveats

- Reviewers are not a random sample of all players. They may be more invested than average, and this data cannot measure that gap.
- Playtime is lifetime at fetch time, not the exact playtime when the ending unlocked.
- Same-second ties are excluded from first-ending counts.
- "The World only" is mostly The Devil with Takemura dead, plus some achievements that never fired.
- Unlock tools cannot be fully filtered out.
