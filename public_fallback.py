#!/usr/bin/env python3
"""Public fallback collector for x-virality-score.

No X login, cookies, tokens or API keys. Uses multiple public web indexes and
never invents view counts. A post becomes a hit only when a numeric view metric
is attributable to that post; otherwise the metric remains unknown.
"""
from __future__ import annotations
import argparse, html as htmllib, json, re, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
POST_RE = re.compile(r"https?://(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)/status/(\d+)", re.I)
VIEW_RE = re.compile(r"(?:views?|visualizaciones?)\D{0,18}([0-9][0-9,.]*\s*[KMB]?)", re.I)
SOURCES = (
    ("google", "https://www.google.com/search?q={q}"),
    ("bing", "https://www.bing.com/search?q={q}"),
    ("duckduckgo", "https://html.duckduckgo.com/html/?q={q}"),
)

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")

def parse_number(raw: str):
    s = raw.upper().replace(",", "").replace(" ", "")
    mult = 1
    if s.endswith("K"): mult, s = 1_000, s[:-1]
    elif s.endswith("M"): mult, s = 1_000_000, s[:-1]
    elif s.endswith("B"): mult, s = 1_000_000_000, s[:-1]
    try: return int(float(s) * mult)
    except ValueError: return None

def clean(text: str) -> str:
    text = urllib.parse.unquote(htmllib.unescape(text))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))

def extract(source: str, raw: str, handle: str, found: dict):
    # Search engines often escape URLs; normalise common forms first.
    raw = raw.replace("\\u0026", "&").replace("%2F", "/").replace("%3A", ":")
    for m in POST_RE.finditer(raw):
        author, post_id = m.groups()
        if author.lower() != handle.lower():
            continue
        context = clean(raw[max(0, m.start()-700):min(len(raw), m.end()+700)])
        vm = VIEW_RE.search(context)
        views = parse_number(vm.group(1)) if vm else None
        item = found.setdefault(post_id, {
            "id": post_id, "handle": "@" + author,
            "url": f"https://x.com/{author}/status/{post_id}",
            "views": None, "views_verified": False, "sources": []
        })
        if source not in item["sources"]: item["sources"].append(source)
        if views is not None:
            item["views"], item["views_verified"] = views, True

def discover(handle: str):
    found, status = {}, {}
    queries = [
        f'site:x.com/{handle}/status {handle}',
        f'"@{handle}" "status" x.com',
        f'"{handle}" "x.com/{handle}/status"',
    ]
    for source, template in SOURCES:
        ok, errors = 0, []
        for query in queries:
            try:
                raw = fetch(template.format(q=urllib.parse.quote_plus(query)))
                extract(source, raw, handle, found)
                ok += 1
            except Exception as exc:
                errors.append(type(exc).__name__)
        status[source] = {"queries_ok": ok, "errors": errors}
    return list(found.values()), status

def build(handle, timezone, min_views, star_views):
    now = datetime.now(ZoneInfo(timezone))
    posts, source_status = discover(handle)
    verified = [p for p in posts if p["views_verified"]]
    hits = [p for p in verified if p["views"] >= min_views]
    for p in hits: p["star"] = p["views"] >= star_views
    unknown = [p for p in posts if not p["views_verified"]]
    return {
        "title": f"Daily X narrative digest — {now.date().isoformat()}",
        "date": now.date().isoformat(), "timezone": timezone,
        "updated": now.isoformat(timespec="seconds"),
        "brand_title": "Connectrom X Virality Score", "brand_handle": "@" + handle,
        "collector_mode": "public_fallback_multi_source",
        "metric_policy": "No inferred or invented view counts; unknown remains unknown.",
        "thresholds": {"min_views": min_views, "star_views": star_views},
        "source_status": source_status,
        "hits": hits, "hits_count": len(hits),
        "public_posts_found": len(posts), "verified_view_metrics": len(verified),
        "unknown_metrics": unknown,
        "virals": [], "outsiders": [], "patterns": [], "no_hits": [],
        "operator": {"handle": "@" + handle, "name": handle, "profile_url": f"https://x.com/{handle}"},
        "ui": {"default_theme": "night"},
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", default="connectrom")
    ap.add_argument("--timezone", default="Europe/London")
    ap.add_argument("--min-views", type=int, default=5000)
    ap.add_argument("--star-views", type=int, default=10000)
    ap.add_argument("--output", default="board/data.public.json")
    a = ap.parse_args()
    try: data = build(a.handle.lstrip("@"), a.timezone, a.min_views, a.star_views)
    except Exception as e:
        print(f"PUBLIC FALLBACK ERROR: {e}"); return 2
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {out} | posts={data['public_posts_found']} verified_views={data['verified_view_metrics']} hits={data['hits_count']}")
    print("SOURCES: " + " | ".join(f"{k}={v['queries_ok']}/3" for k,v in data['source_status'].items()))
    return 0

if __name__ == "__main__": raise SystemExit(main())
