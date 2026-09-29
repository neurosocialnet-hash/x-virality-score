#!/usr/bin/env python3
"""Persistent daily ledger + week/month leaderboards for the X Virality board.

Importer-safe defaults (override with env). This file does not embed a
personal operator handle or a private digest path.

- Reads operator identity from board/data.json (`operator.handle` / `name`,
  else `brand_handle`) or XVS_OPERATOR_HANDLE / XVS_OPERATOR_NAME
- Recomputes leaderboards.week (rolling 7 ending as_of) and leaderboards.month
  (calendar month from tracking_start through as_of) from the ledger ONLY
- Does NOT double-count: re-running overwrites that day's ledger slice
- Only patches leaderboards (+ updated); leaves day_roster / hits / etc. intact
- Does not invent historical "you" views when a day's scrape is missing

Paths:
  XVS_DATA           default: <this dir>/data.json
  XVS_LEDGER         default: <this dir>/leaderboard_ledger.json
  XVS_WATCHLIST      default: <repo>/config/watchlist.json
  XVS_DIGEST_ROOT    default: <repo>/digests
                     each day is YYYY-MM-DD/composed.json or watchlist_merged.json
                     optional YYYY-MM-DD/_parts/you_day.json for the operator
  XVS_TRACKING_START ISO date; else leaderboards.tracking_start or data.date
  XVS_TIMEZONE       else watchlist timezone or data.timezone (default UTC)
  XVS_MIN_VIEWS      else watchlist min_views (default 5000)

Usage:
  cp board/data.example.json board/data.json
  python3 board/enrich_leaderboards.py
  python3 board/enrich_leaderboards.py --as-of 2026-09-23
  python3 board/enrich_leaderboards.py --bootstrap
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser() if raw else default


ROOT = _env_path("XVS_DIGEST_ROOT", REPO_DIR / "digests")
DASH = _env_path("XVS_DATA", SCRIPT_DIR / "data.json")
LEDGER = _env_path("XVS_LEDGER", SCRIPT_DIR / "leaderboard_ledger.json")
WATCHLIST_PATH = _env_path("XVS_WATCHLIST", REPO_DIR / "config" / "watchlist.json")

YOU = "your_handle"
YOU_HANDLE = "@your_handle"
YOU_NAME = "Operator"
THRESHOLD = 5000
TRACKING_START = ""
TZ_NAME = "UTC"
MSK = timezone.utc


def configure() -> None:
    """Load operator, floors, and timezone from the importer's own files."""
    global YOU, YOU_HANDLE, YOU_NAME, THRESHOLD, TRACKING_START, TZ_NAME, MSK

    watchlist: dict = {}
    if WATCHLIST_PATH.exists():
        watchlist = json.loads(WATCHLIST_PATH.read_text())

    data: dict = {}
    if DASH.exists():
        data = json.loads(DASH.read_text())

    op = data.get("operator") or {}
    handle = (
        os.environ.get("XVS_OPERATOR_HANDLE")
        or op.get("handle")
        or data.get("brand_handle")
        or "@your_handle"
    )
    YOU_HANDLE = norm_handle(str(handle))
    YOU = canon_key(YOU_HANDLE)
    YOU_NAME = str(
        os.environ.get("XVS_OPERATOR_NAME") or op.get("name") or "Operator"
    )
    THRESHOLD = int(
        os.environ.get("XVS_MIN_VIEWS") or watchlist.get("min_views") or 5000
    )
    TZ_NAME = str(
        os.environ.get("XVS_TIMEZONE")
        or watchlist.get("timezone")
        or data.get("timezone")
        or "UTC"
    )
    try:
        from zoneinfo import ZoneInfo

        MSK = ZoneInfo(TZ_NAME)
    except Exception:
        MSK = timezone.utc

    boards = data.get("leaderboards") or {}
    TRACKING_START = str(
        os.environ.get("XVS_TRACKING_START")
        or boards.get("tracking_start")
        or data.get("date")
        or datetime.now(MSK).date().isoformat()
    )


def norm_handle(h: str) -> str:
    h = (h or "").strip()
    if not h.startswith("@"):
        h = "@" + h
    return h


def canon_key(h: str) -> str:
    return norm_handle(h).lstrip("@").lower()


def parse_day(s: str) -> date:
    return date.fromisoformat(s)


def fmt_short(d: date) -> str:
    return d.strftime("%b %-d") if hasattr(d, "strftime") else f"{d.month}/{d.day}"


def fmt_short_safe(d: date) -> str:
    # %-d is GNU; fall back for portability
    try:
        return d.strftime("%b %-d")
    except ValueError:
        return d.strftime("%b %d").replace(" 0", " ")


def load_day_hits(day: str) -> list[dict]:
    """Prefer composed.json hits; fall back to watchlist_merged."""
    for name in ("composed.json", "watchlist_merged.json"):
        p = ROOT / day / name
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        hits = data.get("hits") or data.get("watchlist_hits") or []
        if hits:
            return hits
    return []


def day_has_digest(day: str) -> bool:
    p = ROOT / day
    return (p / "composed.json").exists() or (p / "watchlist_merged.json").exists()


def list_digest_days(start: str, end: str | None = None) -> list[str]:
    days = []
    for p in sorted(ROOT.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        if len(name) != 10 or name[4] != "-" or name[7] != "-":
            continue
        try:
            parse_day(name)
        except ValueError:
            continue
        if name < start:
            continue
        if end and name > end:
            continue
        if day_has_digest(name):
            days.append(name)
    return days


def you_posts_ge5k(day: str) -> list[dict]:
    """Return list of {views, url} for operator posts ≥ threshold that day."""
    you_file = ROOT / day / "_parts" / "you_day.json"
    if you_file.exists():
        posts = json.loads(you_file.read_text()).get("posts") or []
        ge5 = [
            {"views": int(p.get("views") or 0), "url": p.get("url") or ""}
            for p in posts
            if int(p.get("views") or 0) >= THRESHOLD
        ]
        if ge5:
            return ge5
    from_hits = []
    for h in load_day_hits(day):
        if canon_key(h.get("handle") or "") != YOU:
            continue
        views = int(h.get("views") or 0)
        if views >= THRESHOLD:
            from_hits.append(
                {"views": views, "url": h.get("url") or h.get("status_url") or ""}
            )
    if from_hits:
        return from_hits
    return []


def build_day_slice(day: str) -> dict[str, dict]:
    """Per-account daily ledger slice for one calendar day (idempotent overwrite)."""
    accounts: dict[str, dict] = {}

    for h in load_day_hits(day):
        key = canon_key(h.get("handle") or "")
        if not key or key == YOU:
            continue
        views = int(h.get("views") or 0)
        if views < THRESHOLD:
            continue
        url = h.get("url") or h.get("status_url") or ""
        handle = norm_handle(h.get("handle") or key)
        name = h.get("display_name") or h.get("name") or key
        cur = accounts.get(key)
        if not cur:
            accounts[key] = {
                "handle": handle,
                "name": name,
                "hits": 1,
                "best": views,
                "total": views,
                "best_url": url,
            }
        else:
            cur["hits"] += 1
            cur["total"] += views
            cur["name"] = name or cur["name"]
            cur["handle"] = handle
            if views > int(cur["best"]):
                cur["best"] = views
                cur["best_url"] = url

    you_ge5 = you_posts_ge5k(day)
    if you_ge5:
        best_post = max(you_ge5, key=lambda p: p["views"])
        accounts[YOU] = {
            "handle": YOU_HANDLE,
            "name": YOU_NAME,
            "hits": len(you_ge5),
            "best": int(best_post["views"]),
            "total": sum(int(p["views"]) for p in you_ge5),
            "best_url": best_post.get("url") or "",
        }

    return accounts


def empty_ledger() -> dict:
    return {
        "tracking_start": TRACKING_START,
        "timezone": TZ_NAME,
        "threshold": THRESHOLD,
        "days": {},
    }


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return empty_ledger()


def save_ledger(ledger: dict) -> None:
    ledger["tracking_start"] = TRACKING_START
    ledger["timezone"] = TZ_NAME
    ledger["threshold"] = THRESHOLD
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def upsert_day(ledger: dict, day: str) -> None:
    if not day_has_digest(day) and day not in ledger.get("days", {}):
        # No digest and no prior slice — skip (e.g. today with no scrape yet)
        return
    if not day_has_digest(day):
        return
    accounts = build_day_slice(day)
    ledger.setdefault("days", {})[day] = {"accounts": accounts}


def bootstrap_ledger(end: str | None = None) -> dict:
    ledger = empty_ledger()
    for day in list_digest_days(TRACKING_START, end):
        upsert_day(ledger, day)
    save_ledger(ledger)
    return ledger


def resolve_as_of(requested: str | None, ledger: dict) -> str:
    """as_of = requested digest day if present in ledger/disk; else latest ledger day;
    else data.json date; never invent a day without digest."""
    days = sorted(ledger.get("days", {}).keys())
    latest_ledger = days[-1] if days else None
    data_date = None
    if DASH.exists():
        try:
            data_date = json.loads(DASH.read_text()).get("date")
        except Exception:
            pass

    if requested:
        if day_has_digest(requested) or requested in (ledger.get("days") or {}):
            return requested
        # requested today with no digest — fall back
        return latest_ledger or data_date or TRACKING_START

    # default: latest digest on disk ≤ today, else latest ledger
    today = datetime.now(MSK).date().isoformat()
    digest_days = list_digest_days(TRACKING_START, today)
    if digest_days:
        return digest_days[-1]
    return latest_ledger or data_date or TRACKING_START


def week_day_list(as_of: str, tracking_start: str) -> list[str]:
    end = parse_day(as_of)
    start = end - timedelta(days=6)
    track = parse_day(tracking_start)
    if start < track:
        start = track
    out = []
    cur = start
    while cur <= end:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def month_day_list(as_of: str, tracking_start: str, ledger_days: list[str]) -> list[str]:
    end = parse_day(as_of)
    track = parse_day(tracking_start)
    # calendar month of as_of, clipped to tracking_start..as_of
    month_start = date(end.year, end.month, 1)
    if month_start < track:
        month_start = track
    # Prefer actual ledger days in that window (missing scrape days simply absent)
    wanted = []
    cur = month_start
    while cur <= end:
        wanted.append(cur.isoformat())
        cur += timedelta(days=1)
    ledger_set = set(ledger_days)
    return [d for d in wanted if d in ledger_set]


def aggregate(ledger: dict, days: list[str]) -> list[dict]:
    """Sum totals / hits, max best, count days-with-hits from ledger slices."""
    acc: dict[str, dict] = {}
    days_hit: dict[str, set] = defaultdict(set)
    day_map = ledger.get("days") or {}

    for day in days:
        slice_ = day_map.get(day) or {}
        accounts = slice_.get("accounts") or {}
        for key, row in accounts.items():
            hits = int(row.get("hits") or 0)
            total = int(row.get("total") or 0)
            best = int(row.get("best") or 0)
            if hits <= 0 and total < THRESHOLD and best < THRESHOLD:
                continue
            if key not in acc:
                acc[key] = {
                    "handle": row.get("handle") or norm_handle(key),
                    "name": row.get("name") or key,
                    "hits": 0,
                    "days": 0,
                    "views": 0,
                    "best": 0,
                    "best_url": row.get("best_url") or "",
                }
            cur = acc[key]
            cur["hits"] += hits
            cur["views"] += total
            cur["name"] = row.get("name") or cur["name"]
            cur["handle"] = row.get("handle") or cur["handle"]
            if best > int(cur["best"]):
                cur["best"] = best
                cur["best_url"] = row.get("best_url") or cur.get("best_url") or ""
            days_hit[key].add(day)

    for key, s in days_hit.items():
        if key in acc:
            acc[key]["days"] = len(s)

    ents = list(acc.values())
    # Drop empty / no-threshold rows just in case
    ents = [e for e in ents if int(e.get("views") or 0) >= THRESHOLD or int(e.get("best") or 0) >= THRESHOLD]
    ents.sort(key=lambda e: (-int(e["views"]), -int(e["best"]), e["handle"].lower()))
    return ents


def week_label(days: list[str]) -> str:
    if not days:
        return "Rolling week"
    a, b = parse_day(days[0]), parse_day(days[-1])
    return f"Rolling week · {fmt_short_safe(a)}–{fmt_short_safe(b)}"


def month_label(as_of: str, days: list[str], tracking_start: str) -> str:
    end = parse_day(as_of)
    month_name = end.strftime("%B %Y")
    if days:
        first = parse_day(days[0])
        return f"{month_name} · from {fmt_short_safe(first)}"
    track = parse_day(tracking_start)
    return f"{month_name} · from {fmt_short_safe(track)}"


def patch_data_json(as_of: str, ledger: dict) -> dict:
    if not DASH.exists():
        raise SystemExit(
            f"missing {DASH}. Copy board/data.example.json to board/data.json first."
        )
    data = json.loads(DASH.read_text())
    tracking_start = ledger.get("tracking_start") or TRACKING_START
    ledger_days = sorted(ledger.get("days", {}).keys())

    week_days = week_day_list(as_of, tracking_start)
    # Aggregate only days that exist in the ledger (missing digests = no slice)
    week_agg_days = [d for d in week_days if d in ledger.get("days", {})]
    month_agg_days = month_day_list(as_of, tracking_start, ledger_days)

    week_entries = aggregate(ledger, week_agg_days)
    month_entries = aggregate(ledger, month_agg_days)

    w_range = [week_days[0], week_days[-1]] if week_days else [as_of, as_of]
    m_range = (
        [month_agg_days[0], month_agg_days[-1]]
        if month_agg_days
        else [tracking_start, as_of]
    )

    data["leaderboards"] = {
        "as_of": as_of,
        "tracking_start": tracking_start,
        "days_included": week_days,
        "month_days_included": month_agg_days,
        "week": {
            "label": week_label(week_days),
            "range": w_range,
            "entries": week_entries,
        },
        "month": {
            "label": month_label(as_of, month_agg_days, tracking_start),
            "range": m_range,
            "entries": month_entries,
        },
    }
    data["updated"] = datetime.now(MSK).replace(microsecond=0).isoformat()
    # Keep data.date as the digest day we are scoring (do not invent Sep 24)
    if day_has_digest(as_of):
        data["date"] = as_of
    elif not data.get("date"):
        data["date"] = as_of

    DASH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD ending day for week/month")
    ap.add_argument(
        "--bootstrap",
        action="store_true",
        help="Rebuild ledger from all digest days (still idempotent per-day overwrite)",
    )
    ap.add_argument(
        "--no-upsert",
        action="store_true",
        help="Only recompute from existing ledger (do not upsert as_of day)",
    )
    args = ap.parse_args()
    configure()

    if args.bootstrap or not LEDGER.exists():
        ledger = bootstrap_ledger(end=args.as_of)
        print(f"bootstrapped ledger days={sorted(ledger['days'].keys())}")
    else:
        ledger = load_ledger()

    as_of = resolve_as_of(args.as_of, ledger)

    if not args.no_upsert:
        if day_has_digest(as_of):
            upsert_day(ledger, as_of)
            save_ledger(ledger)
            print(f"upserted day={as_of} accounts={len(ledger['days'][as_of]['accounts'])}")
        else:
            print(f"no digest for as_of={as_of}; ledger unchanged for that day")
            save_ledger(ledger)

    data = patch_data_json(as_of, ledger)
    lbs = data["leaderboards"]
    you_w = next(
        (e for e in lbs["week"]["entries"] if canon_key(e["handle"]) == YOU), None
    )
    you_m = next(
        (e for e in lbs["month"]["entries"] if canon_key(e["handle"]) == YOU), None
    )
    print("ledger", LEDGER)
    print("as_of", lbs["as_of"], "tracking_start", lbs["tracking_start"])
    print("week", lbs["week"]["label"], lbs["week"]["range"], "n", len(lbs["week"]["entries"]))
    print("month", lbs["month"]["label"], lbs["month"]["range"], "n", len(lbs["month"]["entries"]))
    print("days_included", lbs["days_included"])
    print("month_days_included", lbs["month_days_included"])
    print("you_week", you_w)
    print("you_month", you_m)
    print("week top3", [(e["handle"], e["best"], e["views"]) for e in lbs["week"]["entries"][:3]])
    print("month top3", [(e["handle"], e["best"], e["views"]) for e in lbs["month"]["entries"][:3]])
    print("updated", data["updated"], "date", data.get("date"))


if __name__ == "__main__":
    main()
