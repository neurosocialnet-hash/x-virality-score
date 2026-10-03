#!/usr/bin/env python3
"""Public fallback collector for x-virality-score.

Reads public search/index sources without logging into X. It never invents view
counts: a post is promoted to hits only when a numeric view metric is present
and attributable to that post. Output is a local JSON file that can be copied
to the separate x-virality-board repository.

No cookies, passwords, tokens or API keys are read or stored.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

UA = "Mozilla/5.0 (compatible; x-virality-score-public-fallback/1.0)"
SEARCH = "https://www.google.com/search?q="
POST_RE = re.compile(r"https?://(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)/status/(\d+)")
VIEW_RE = re.compile(r"(?:views?|visualizaciones?)\D{0,12}([0-9][0-9,.]*\s*[KMB]?)", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def parse_number(raw: str) -> int | None:
    s = raw.upper().replace(",", "").replace(" ", "")
    mult = 1
    if s.endswith("K"):
        mult, s = 1_000, s[:-1]
    elif s.endswith("M"):
        mult, s = 1_000_000, s[:-1]
    elif s.endswith("B"):
        mult, s = 1_000_000_000, s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return None


def discover(handle: str) -> list[dict]:
    # Public web index only; no X session and no authentication bypass.
    q = urllib.parse.quote(f'site:x.com/{handle}/status "{handle}"')
    html = fetch(SEARCH + q)
    found: dict[str, dict] = {}
    for m in POST_RE.finditer(html):
        author, post_id = m.groups()
        if author.lower() != handle.lower():
            continue
        url = f"https://x.com/{author}/status/{post_id}"
        start, end = max(0, m.start()-500), min(len(html), m.end()+500)
        context = re.sub(r"<[^>]+>", " ", html[start:end])
        vm = VIEW_RE.search(context)
        views = parse_number(vm.group(1)) if vm else None
        found[post_id] = {
            "id": post_id,
            "handle": "@" + author,
            "url": url,
            "views": views,
            "views_verified": views is not None,
            "source": "public_web_index",
        }
    return list(found.values())


def build(handle: str, timezone: str, min_views: int, star_views: int) -> dict:
    now = datetime.now(ZoneInfo(timezone))
    posts = discover(handle)
    verified = [p for p in posts if p["views_verified"]]
    hits = [p for p in verified if p["views"] >= min_views]
    for p in hits:
        p["star"] = p["views"] >= star_views
    unknown = [p for p in posts if not p["views_verified"]]
    return {
        "title": f"Daily X narrative digest — {now.date().isoformat()}",
        "date": now.date().isoformat(),
        "timezone": timezone,
        "updated": now.isoformat(timespec="seconds"),
        "brand_title": "Connectrom X Virality Score",
        "brand_handle": "@" + handle,
        "collector_mode": "public_fallback",
        "metric_policy": "No inferred or invented view counts; unknown remains unknown.",
        "thresholds": {"min_views": min_views, "star_views": star_views},
        "hits": hits,
        "hits_count": len(hits),
        "public_posts_found": len(posts),
        "verified_view_metrics": len(verified),
        "unknown_metrics": unknown,
        "virals": [], "outsiders": [], "patterns": [], "no_hits": [],
        "operator": {"handle": "@" + handle, "name": handle, "profile_url": f"https://x.com/{handle}"},
        "ui": {"default_theme": "night"},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="connectrom")
    ap.add_argument("--timezone", default="Europe/London")
    ap.add_argument("--min-views", type=int, default=5000)
    ap.add_argument("--star-views", type=int, default=10000)
    ap.add_argument("--output", default="board/data.public.json")
    args = ap.parse_args()
    try:
        data = build(args.handle.lstrip("@"), args.timezone, args.min_views, args.star_views)
    except Exception as e:
        print(f"PUBLIC FALLBACK ERROR: {e}")
        return 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out} | posts={data['public_posts_found']} verified_views={data['verified_view_metrics']} hits={data['hits_count']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
