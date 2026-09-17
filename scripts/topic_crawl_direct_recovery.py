#!/usr/bin/env python3
"""Recover and save date-eligible NewsAPI.ai source bodies for crawl-only runs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.request


def runtime_key(config: pathlib.Path) -> str:
    match = re.search(r"^\s*NEWSAPI_AI_API_KEY\s*=\s*(\S+)\s*$", config.read_text(), re.M)
    if not match:
        raise RuntimeError("NEWSAPI_AI_API_KEY is missing or blank")
    return match.group(1)


def extract(url: str, key: str) -> dict:
    data = json.dumps({"url": url, "apiKey": key}).encode()
    request = urllib.request.Request(
        "https://analytics.eventregistry.org/api/v1/extractArticleInfo",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def is_in_range(value: str, start: dt.date, end: dt.date) -> bool:
    return start <= dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date() <= end


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", type=pathlib.Path)
    parser.add_argument("output_dir", type=pathlib.Path)
    parser.add_argument("--date-start", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--date-end", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--config", type=pathlib.Path, default=pathlib.Path(".env.local"))
    args = parser.parse_args()
    key = runtime_key(args.config)
    candidates = json.loads(args.candidates.read_text())
    saved, manifest = [], []
    for candidate in candidates:
        item = extract(candidate["url"], key)
        body = str(item.get("body") or "").strip()
        published = str(item.get("datetime") or item.get("date") or "")
        if not item.get("title") or len(body) < 100 or not published:
            manifest.append({"url": candidate["url"], "disposition": "held", "reason": "incomplete recovery response"})
            continue
        if not is_in_range(published, args.date_start, args.date_end):
            manifest.append({"url": candidate["url"], "disposition": "held", "reason": "outside approved date range", "publishedDate": published})
            continue
        saved.append({
            "sourceId": "crawl-" + hashlib.sha256(candidate["url"].encode()).hexdigest()[:10],
            "sourceUrl": item.get("urlCanonical") or candidate["url"],
            "title": item["title"],
            "publishedDate": published,
            "language": candidate["language"],
            "publisher": item.get("sourceTitle") or candidate["publisher"],
            "publisherCountry": candidate["publisherCountry"],
            "body": body,
            "bodySha256": hashlib.sha256(body.encode()).hexdigest(),
        })
        manifest.append({"url": candidate["url"], "disposition": "saved", "publishedDate": published, "bodyChars": len(body)})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "direct-recovery-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (args.output_dir / "recovered-source-records.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2))
    print(json.dumps({"candidates": len(candidates), "saved": len(saved), "held": len(candidates) - len(saved)}))


if __name__ == "__main__":
    main()
