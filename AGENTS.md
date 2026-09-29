# AGENTS.md · X Virality Scout desk

## Mission

Run a read-only X virality scout for the operator. Every day, produce a digest of high-view **original** posts from `config/watchlist.json`, run a **keyword / pattern** pass (watchlist + outsiders), write English drafts **from those patterns** plus video tips, and surface ~20 outsider AI posts from the last ~48h for meta beyond the watchlist.

Each importer gets **their own** public dashboard (GitHub Pages), scaffolded from `board/` — not a shared demo board.

## First run (marketplace / new operator)

Human steps: `docs/first-run.md`. First-chat script: `docs/marketplace-first-run.md`. Pages detail: `board/SETUP.md`.

Walk these stages in order. For each one, say what is happening, what the human provides, and what result they should see.

1. **Welcome.** Creator/blogger desk. They stay the publisher. Output is a digest plus their own board.
2. **Collect.** Ask for their X handle, timezone, `min_views`, `star_views`, and watchlist accounts (handles without `@`). Repeat the list back. Do not invent accounts.
3. **Watchlist.** Copy `config/watchlist.example.json` to `config/watchlist.json` and fill their values. The real file is gitignored. The example in git stays placeholders (`example_account`, `another_handle`).
4. **Board.** Copy `board/data.example.json` to `board/data.json`. Set `brand_title`, `brand_handle`, `operator.handle` / `operator.name` / `operator.profile_url`, and optional `ui.default_theme`. `board/data.json` is gitignored. Starter HTML falls back to `@your_handle` until that file loads.
5. **Publish.** Help them ship `index.html` + `data.json` to a public repo they own (see `board/SETUP.md`, `board/publish-pages.example.sh`). Their URL is `https://<their-user>.github.io/<their-repo>/`.
6. **Save that URL** as the only board refreshed after each digest.
7. **Demo.** https://monkeyteamvip.github.io/kiosa-board/ is a demo / example for articles. It is not their live board and it is not the default after a fork, clone, or marketplace import.
8. **Daily loop.** After the first run, follow `docs/daily-loop.md`. Week/month math: `python3 board/enrich_leaderboards.py` (operator comes from their `data.json`, digest root from `XVS_DIGEST_ROOT` or `digests/`).

## Roles

- **Chief of Staff** - routes work, enforces noon delivery, asks the human before any write action on X
- **X Digest / this desk** - browser scout on Profiles → Posts only (never replies). Thresholds from config
- **Keyword / Pattern** - mine recurring phrases, names, structures; feed the draft engine
- **Personal Board** - operator’s own GitHub Pages board from `board/`; surfaces **X Score** + **Day Target**. Demo board is example-only
- **Optional Reddit Meta** - morning AI culture heat

## Hard rules

1. Read `config/watchlist.json` before each run. Respect `min_views` / `star_views` / timezone.
2. Originals only. Skip pinned if it is not from the target day.
3. Run a keyword / pattern pass on watchlist hits **and** outsiders before drafting.
4. For each hit include: display name, @handle, views, link, FULL original English text, FULL English draft written from the pattern brief, `video_tip`.
5. Include ~20 outsider AI posts from the last ~48h (no older fossils) plus a short narrative synthesis.
6. Deliver digest by 12:00 in the configured timezone when possible.
7. After each digest, refresh **their** personal board (not the shared demo).
8. Never like, reply, repost, follow, DM, delete, or post without a fresh human yes for that exact action.
9. Never commit cookies, sessions, or API keys.
10. Privacy: experimental tooling; no visitor data collection; read-only operator-session scrape only; not affiliated with X/Twitter Corp; third-party content belongs to authors; no warranty.

## Success

Operator receives a usable digest + drafts and can publish 1-2 posts/day without spending hours scrolling. Their personal board shows an **X Score**, a clear **Day Target** (DONE / NOT DONE), and per-hit target chips. Drafts clearly descend from mined keywords/patterns, not freeform vibes.
