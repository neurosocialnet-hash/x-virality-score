#!/usr/bin/env python3
"""Public fallback collector for x-virality-score.

Clean-epoch mode for @connectrom. No X login, cookies, tokens or API keys.
Search-index results are discovery candidates only. Old/deleted indexed posts
are excluded from scoring. Search snippets are not authoritative metrics, so
view counts found there remain unverified hints and never enter scoring.
"""
from __future__ import annotations
import argparse, html as htmllib, json, re, urllib.parse, urllib.request
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
POST_RE = re.compile(r"https?://(?:x\.com|twitter\.com)/([A-Za-z0-9_]+)/status/(\d+)", re.I)
VIEW_RE = re.compile(r"(?:views?|visualizaciones?)\D{0,18}([0-9][0-9,.]*\s*[KMB]?)", re.I)
SOURCES = (("google","https://www.google.com/search?q={q}"),("bing","https://www.bing.com/search?q={q}"),("duckduckgo","https://html.duckduckgo.com/html/?q={q}"))
X_EPOCH_MS = 1288834974657

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Language":"en-GB,en;q=0.9"})
    with urllib.request.urlopen(req,timeout=20) as r: return r.read().decode("utf-8","replace")

def parse_number(raw):
    s=raw.upper().replace(",","").replace(" ",""); mult=1
    if s.endswith("K"): mult,s=1000,s[:-1]
    elif s.endswith("M"): mult,s=1000000,s[:-1]
    elif s.endswith("B"): mult,s=1000000000,s[:-1]
    try:return int(float(s)*mult)
    except ValueError:return None

def snowflake_time(post_id):
    try:
        ms=(int(post_id)>>22)+X_EPOCH_MS
        return datetime.fromtimestamp(ms/1000,dt_timezone.utc)
    except Exception:return None

def clean(text):
    text=urllib.parse.unquote(htmllib.unescape(text))
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",text))

def extract(source,raw,handle,found):
    raw=raw.replace("\\u0026","&").replace("%2F","/").replace("%3A",":")
    for m in POST_RE.finditer(raw):
        author,pid=m.groups()
        if author.lower()!=handle.lower():continue
        context=clean(raw[max(0,m.start()-700):min(len(raw),m.end()+700)])
        vm=VIEW_RE.search(context); hint=parse_number(vm.group(1)) if vm else None
        item=found.setdefault(pid,{"id":pid,"handle":"@"+author,"url":f"https://x.com/{author}/status/{pid}","views":None,"views_verified":False,"sources":[]})
        if source not in item["sources"]:item["sources"].append(source)
        # Search-engine snippets can be stale or associate nearby text with the
        # wrong status. Keep any parsed count only as an explicitly untrusted
        # diagnostic hint; it must never satisfy a scoring threshold.
        if hint is not None:
            item["search_view_hint"] = max(hint, item.get("search_view_hint") or 0)
            item["search_view_hint_verified"] = False

def discover(handle):
    found,status={},{}
    queries=[f'site:x.com/{handle}/status {handle}',f'"@{handle}" "status" x.com',f'"{handle}" "x.com/{handle}/status"']
    for source,template in SOURCES:
        ok=0; errors=[]
        for query in queries:
            try:extract(source,fetch(template.format(q=urllib.parse.quote_plus(query))),handle,found);ok+=1
            except Exception as exc:errors.append(type(exc).__name__)
        status[source]={"queries_ok":ok,"errors":errors}
    return list(found.values()),status

def build(handle,tz,min_views,star_views,tracking_start):
    zone=ZoneInfo(tz); now=datetime.now(zone)
    start=datetime.fromisoformat(tracking_start).replace(tzinfo=zone).astimezone(dt_timezone.utc)
    candidates,source_status=discover(handle)
    old=[]; current=[]
    for p in candidates:
        created=snowflake_time(p["id"]); p["created_at"] = created.isoformat() if created else None
        if not created or created < start: old.append(p)
        else: current.append(p)
    verified=[p for p in current if p["views_verified"]]
    hits=[p for p in verified if p["views"]>=min_views]
    for p in hits:p["star"]=p["views"]>=star_views
    unknown=[p for p in current if not p["views_verified"]]
    return {"title":f"Daily X narrative digest — {now.date().isoformat()}","date":now.date().isoformat(),"timezone":tz,"updated":now.isoformat(timespec="seconds"),"brand_title":"Connectrom X Virality Score","brand_handle":"@"+handle,"collector_mode":"public_fallback_clean_epoch","tracking_start":tracking_start,"tracking_policy":"Only posts created on/after tracking_start can score. Older search-index remnants are excluded.","metric_policy":"Search snippets are discovery evidence only. No inferred or invented view counts; unverified counts remain hints and unknown for scoring.","thresholds":{"min_views":min_views,"star_views":star_views},"source_status":source_status,"discovered_candidates":len(candidates),"excluded_pre_epoch":len(old),"excluded_candidates":old,"public_posts_found":len(current),"verified_view_metrics":len(verified),"unknown_metrics":unknown,"hits":hits,"hits_count":len(hits),"virals":[],"outsiders":[],"patterns":[],"no_hits":[],"operator":{"handle":"@"+handle,"name":handle,"profile_url":f"https://x.com/{handle}"},"ui":{"default_theme":"night"}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--handle",default="connectrom");ap.add_argument("--timezone",default="Europe/London");ap.add_argument("--min-views",type=int,default=5000);ap.add_argument("--star-views",type=int,default=10000);ap.add_argument("--tracking-start",default="2026-10-03T00:00:00");ap.add_argument("--output",default="board/data.public.json");a=ap.parse_args()
    try:data=build(a.handle.lstrip("@"),a.timezone,a.min_views,a.star_views,a.tracking_start)
    except Exception as e:print(f"PUBLIC FALLBACK ERROR: {e}");return 2
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"OK: {out} | current={data['public_posts_found']} old_excluded={data['excluded_pre_epoch']} verified_views={data['verified_view_metrics']} hits={data['hits_count']}")
    print("SOURCES: "+" | ".join(f"{k}={v['queries_ok']}/3" for k,v in data['source_status'].items()));return 0
if __name__=="__main__":raise SystemExit(main())
