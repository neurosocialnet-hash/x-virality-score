# Grok Bot X Virality Score

Welcome. This repo is a **Grok Bot virality desk** plus a starter for **your own** public dashboard.

You pick the accounts. The desk reads original posts that already cleared your view floor, mines the keywords and patterns, and hands you an English draft and a video tip. You stay the publisher. Nothing posts, likes, or replies on its own.

## What the bot does

Each day it can:

1. Scan **your** watchlist (Profiles → original posts).
2. Keep posts at or above `min_views`, and mark ★ posts at or above `star_views`.
3. Run a **keyword / pattern** pass on those hits and on ~20 outsider AI posts from the last ~48 hours.
4. Write a full English draft **from that pattern brief**, plus a `video_tip`.
5. Deliver a digest you can open before noon in your timezone.
6. Refresh **your** GitHub Pages board: X Score, Day Target (DONE / NOT DONE), per-hit chips, Night/Day themes, and charts.

## What you provide

| You provide | Where it goes |
| --- | --- |
| Your X handle (with or without `@`) | `board/data.json` → `brand_handle` and `operator` |
| Watchlist handles, **without** `@` | `config/watchlist.json` → `accounts` |
| Timezone, `min_views`, `star_views` | same watchlist file |
| A GitHub account for Pages | your own public repo, for example `x-virality-board` |
| A logged-in X session on the machine that scrapes | read-only. Never commit cookies, tokens, or API keys |

Copy the starters. Your real files stay local:

```bash
cp config/watchlist.example.json config/watchlist.json
cp board/data.example.json board/data.json
```

`config/watchlist.json`, `board/data.json`, and `board/leaderboard_ledger.json` are gitignored so a later pull does not overwrite them.

## What you should end up with

Your live board is a URL **you** publish:

`https://<your-github-user>.github.io/<your-repo>/`

Example: `https://ada.github.io/x-virality-board/`

That URL is the only board the daily loop refreshes. Step-by-step: [docs/first-run.md](docs/first-run.md). Publishing details: [board/SETUP.md](board/SETUP.md).

https://monkeyteamvip.github.io/kiosa-board/ is a **demo / example** (case study and screenshots). It is someone else's board. A fork, a clone, and a marketplace import each get their own Pages URL.

## First run

| Stage | What happens | What you do | Result you should see |
| --- | --- | --- | --- |
| 1. Welcome | You learn this is a read-only desk, and you remain the publisher. | Read this page, or start a Grok Bot chat that has `AGENTS.md`. | You know the output is a digest plus your own board. |
| 2. Watchlist | The desk needs accounts, a timezone, and view floors. | `cp config/watchlist.example.json config/watchlist.json` and replace `example_account` / `another_handle`. | `config/watchlist.json` lists **your** handles and is not committed. |
| 3. Board identity | The starter UI reads `brand_*`, `operator`, and `ui.default_theme` from `data.json`. | `cp board/data.example.json board/data.json` and set your handle and name. | Local `data.json` shows `@you`, not a demo operator. |
| 4. Publish | GitHub Pages serves `index.html` + `data.json` from a repo you own. | Follow [board/SETUP.md](board/SETUP.md) or `board/publish-pages.example.sh`. | `https://<you>.github.io/<repo>/` loads your board. |
| 5. Daily loop | The desk scrapes, drafts, and refreshes **that** URL. | Run [docs/daily-loop.md](docs/daily-loop.md). Pick 1–2 drafts and post them yourself. | Noon digest in chat. Board shows today's X Score and Day Target. |

Marketplace bots should follow [docs/marketplace-first-run.md](docs/marketplace-first-run.md) on the first chat and ask for your handle and watchlist before writing any files.

## Daily loop (short)

1. Optional morning culture check.
2. Read-only watchlist scrape of original posts.
3. Keyword / pattern pass, including ~20 outsiders from the last ~48 hours.
4. English drafts + `video_tip` written from those patterns.
5. Digest by 12:00 in your configured timezone.
6. You edit and publish 1–2 posts yourself.
7. Refresh `board/data.json` and push it to **your** Pages repo.

Full timing: [docs/daily-loop.md](docs/daily-loop.md).

## Config

`config/watchlist.json` (create it from the example; do not commit it):

- `timezone` — when "yesterday" is calculated (example file uses `Europe/Moscow`)
- `min_views` — floor for a hit (example: `5000`)
- `star_views` — highlight threshold (example: `10000`)
- `accounts` — handles **without** `@`. A string, or `{"handle","notes"}`, both work.

Anyone can fork this and track a different niche (AI tools, design, local news). The scout logic stays the same.

## Repo map

```
AGENTS.md                      # role card for the desk agent
README.md                      # you are here
ARTICLE.md                     # operator case study (English)
config/watchlist.example.json  # starter watchlist (placeholders)
docs/first-run.md              # human setup, stage by stage
docs/marketplace-first-run.md  # first chat for a marketplace import
docs/daily-loop.md             # how a day runs
docs/public-board.md           # personal Pages vs the demo
board/index.html               # single-file dashboard
board/data.example.json        # schema the UI expects
board/enrich_leaderboards.py   # week/month ledger (uses your operator)
board/publish-pages.example.sh # publish helper (no secrets inside)
board/SETUP.md                 # Pages + targets + themes
templates/                     # digest shape + draft rules
examples/                      # redacted sample digest
assets/                        # screenshots for the article
```

## Privacy / experimental

- Experimental personal tooling. No warranty.
- The board does not collect visitor data. Theme choice stays in `localStorage` on the visitor's browser.
- X is read through the **operator** session on the machine that runs the desk. Visitor accounts are never used.
- This project is not affiliated with X Corp / Twitter, Inc.
- Third-party posts remain owned by their authors.

## Safety

- View and collect only. Likes, replies, follows, DMs, and posts wait for an explicit yes for that exact action.
- Never store secrets in git.

## License

MIT. See [LICENSE](LICENSE). Example digests are redacted placeholders. Replace them with your own scrapes.
