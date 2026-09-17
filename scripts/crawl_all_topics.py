#!/usr/bin/env python3
"""Run governed NewsAPI.ai discovery and intake for every active topic entity.

The crawler keeps independent evidence for each topic, accepts only in-range Indonesian
or English article bodies from Indonesia-located sources, and delegates final schema
validation and raw-payload preservation to newsapi_to_inputs.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

import yaml

from topic_crawl_direct_recovery import runtime_key


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOPICS = ROOT / "entities" / "topic"


def frontmatter(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def active_topics() -> list[tuple[str, dict]]:
    ignored = {"catalog.md", "index.md", "log.md", "_template.md"}
    items = []
    for path in sorted(TOPICS.glob("*.md")):
        if path.name in ignored:
            continue
        data = frontmatter(path)
        if data.get("status") == "active":
            items.append((path.stem, data))
    return items


def batch_slugs(batches_file: pathlib.Path, batch_id: str) -> list[str]:
    """Return the ordered topicIds for a batch defined in the crawl-batches manifest."""
    manifest = yaml.safe_load(batches_file.read_text(encoding="utf-8")) or {}
    for batch in manifest.get("batches") or []:
        if str(batch.get("id")) == batch_id:
            return [str(slug) for slug in (batch.get("topics") or [])]
    available = ", ".join(str(b.get("id")) for b in (manifest.get("batches") or []))
    raise SystemExit(f"unknown batch {batch_id!r}; available batches: {available}")


def request_articles(key: str, query: str, language: str, start: str, end: str) -> list[dict]:
    payload = {
        "action": "getArticles",
        "keyword": query,
        "lang": language,
        "dateStart": start,
        "dateEnd": end,
        "articlesPage": 1,
        "articlesCount": 50,
        "includeSourceLocation": True,
        "apiKey": key,
    }
    request = urllib.request.Request(
        "https://eventregistry.org/api/v1/article/getArticles",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read())
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return list((data.get("articles") or {}).get("results") or [])


def country(article: dict) -> str:
    location = (article.get("source") or {}).get("location") or {}
    label = location.get("label") or {}
    return str(label.get("eng") or "").strip()


def valid(article: dict, start: dt.date, end: dt.date) -> tuple[bool, str]:
    body = str(article.get("body") or "").strip()
    published = str(article.get("dateTimePub") or "")
    if not article.get("uri") or not article.get("title") or not article.get("url"):
        return False, "missing identity field"
    if str(article.get("lang") or "") not in {"eng", "ind"}:
        return False, "unsupported language"
    if len(body) < 100:
        return False, "incomplete body"
    if not published:
        return False, "missing publication date"
    try:
        date = dt.datetime.fromisoformat(published.replace("Z", "+00:00")).date()
    except ValueError:
        return False, "invalid publication date"
    if not start <= date <= end:
        return False, "outside date range"
    if country(article) != "Indonesia":
        return False, "source country is not Indonesia"
    if not (article.get("source") or {}).get("uri"):
        return False, "missing publisher identity"
    return True, "accepted"


def normalized(article: dict) -> dict:
    article = dict(article)
    source = dict(article.get("source") or {})
    source["location"] = {"country": {"label": {"eng": country(article)}}}
    article["source"] = source
    return article


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-start", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--date-end", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--target", type=int, default=20)
    parser.add_argument("--query-limit", type=int, default=3)
    parser.add_argument("--config", type=pathlib.Path, default=ROOT / ".env.local")
    parser.add_argument("--run-root", type=pathlib.Path, default=ROOT / "runs" / "2026-09-07" / "artifacts" / "topic-crawls" / "all-61-topics")
    parser.add_argument("--batch", help="Batch id from --batches-file to crawl (e.g. B1); default crawls every active topic")
    parser.add_argument("--batches-file", type=pathlib.Path, default=ROOT / "topics" / "crawl-batches.yaml")
    args = parser.parse_args()
    key = runtime_key(args.config)
    start, end = args.date_start, args.date_end
    if end < start or args.target < 1:
        raise SystemExit("invalid date range or target")
    topics = active_topics()
    if args.batch:
        wanted = batch_slugs(args.batches_file, args.batch)
        by_slug = dict(topics)
        missing = [slug for slug in wanted if slug not in by_slug]
        if missing:
            raise SystemExit(f"batch {args.batch} references topics not active: {', '.join(missing)}")
        topics = [(slug, by_slug[slug]) for slug in wanted]
        if args.run_root == parser.get_default("run_root"):
            args.run_root = args.run_root.parent / f"batch-{args.batch}"
    seen_uris, seen_urls, seen_bodies = set(), set(), set()
    summary = []
    for slug, topic in topics:
        run = args.run_root / slug
        run.mkdir(parents=True, exist_ok=True)
        aliases = [str(topic.get("displayName") or "").strip()]
        aliases.extend(str(x).strip() for x in topic.get("aliases") or [])
        queries = list(dict.fromkeys(x for x in aliases if x))[:args.query_limit]
        accepted, disposition, searches = [], [], []
        for query in queries:
            if len(accepted) >= args.target:
                break
            for language in ("ind", "eng"):
                if len(accepted) >= args.target:
                    break
                try:
                    results = request_articles(key, query, language, start.isoformat(), end.isoformat())
                    searches.append({"query": query, "language": language, "candidates": len(results)})
                except Exception as exc:  # record an endpoint failure per query; continue other lanes
                    searches.append({"query": query, "language": language, "error": str(exc)})
                    continue
                for article in results:
                    ok, reason = valid(article, start, end)
                    uri, url = str(article.get("uri") or ""), str(article.get("url") or "")
                    body_hash = hashlib.sha256(str(article.get("body") or "").encode()).hexdigest()
                    if ok and (uri in seen_uris or url in seen_urls or body_hash in seen_bodies):
                        ok, reason = False, "duplicate across crawl batch"
                    if ok:
                        accepted.append(normalized(article))
                        seen_uris.add(uri)
                        seen_urls.add(url)
                        seen_bodies.add(body_hash)
                    disposition.append({"uri": uri, "url": url, "disposition": "accepted" if ok else "held", "reason": reason})
                    if len(accepted) >= args.target:
                        break
        payload_path = run / "admitted-newsapi-response.json"
        payload_path.write_text(json.dumps({"articles": {"results": accepted}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        bridge = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "newsapi_to_inputs.py"), str(payload_path), "--write"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        try:
            intake = json.loads(bridge.stdout) if bridge.returncode == 0 else {"error": bridge.stderr.strip()}
        except json.JSONDecodeError:
            intake = {"error": bridge.stdout.strip() or bridge.stderr.strip()}
        manifest = {
            "topic": topic.get("displayName"), "dateStart": start.isoformat(), "dateEnd": end.isoformat(),
            "target": args.target, "searches": searches, "dispositions": disposition,
            "accepted": len(accepted), "intake": intake,
        }
        (run / "crawl-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.append({"topic": topic.get("displayName"), "accepted": len(accepted), "intakePlanned": intake.get("planned", 0), "held": len(disposition) - len(accepted)})
        print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
    summary_path = args.run_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"topics": len(summary), "accepted": sum(x["accepted"] for x in summary), "intakePlanned": sum(x["intakePlanned"] for x in summary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
