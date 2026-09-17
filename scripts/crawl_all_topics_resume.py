#!/usr/bin/env python3
"""Compatibility launcher for the 61-topic crawl after a provider metadata variation."""

from pathlib import Path


source_path = Path(__file__).with_name("crawl_all_topics.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    'return str(label.get("eng") or "").strip()',
    'return str(label.get("eng") or "").strip() if isinstance(label, dict) else str(label or "").strip()',
)
needle = '''        run = args.run_root / slug
        run.mkdir(parents=True, exist_ok=True)
        aliases = [str(topic.get("displayName") or "").strip()]
'''
replacement = '''        run = args.run_root / slug
        run.mkdir(parents=True, exist_ok=True)
        prior_manifest = run / "crawl-manifest.json"
        prior_payload = run / "admitted-newsapi-response.json"
        if prior_manifest.exists():
            prior = json.loads(prior_manifest.read_text(encoding="utf-8"))
            if prior_payload.exists():
                for article in json.loads(prior_payload.read_text(encoding="utf-8")).get("articles", {}).get("results", []):
                    seen_uris.add(str(article.get("uri") or ""))
                    seen_urls.add(str(article.get("url") or ""))
                    seen_bodies.add(hashlib.sha256(str(article.get("body") or "").encode()).hexdigest())
            summary.append({"topic": topic.get("displayName"), "accepted": prior.get("accepted", 0), "intakePlanned": (prior.get("intake") or {}).get("planned", 0), "held": len(prior.get("dispositions") or []) - prior.get("accepted", 0)})
            print(json.dumps({**summary[-1], "status": "already_completed"}, ensure_ascii=False), flush=True)
            continue
        aliases = [str(topic.get("displayName") or "").strip()]
'''
if needle not in source:
    raise SystemExit("resume patch target is unavailable")
source = source.replace(needle, replacement)
exec(compile(source, str(source_path), "exec"))
