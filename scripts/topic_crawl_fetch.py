#!/usr/bin/env python3
"""Map discovered URLs and recover source-backed NewsAPI.ai records without persisting the API key."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request


def api_key(config: pathlib.Path) -> str:
    match = re.search(r"^\s*NEWSAPI_AI_API_KEY\s*=\s*(\S+)\s*$", config.read_text(), re.M)
    if not match:
        raise RuntimeError("NEWSAPI_AI_API_KEY is missing or blank")
    return match.group(1)


def post(endpoint: str, payload: dict, key: str) -> dict:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({**payload, "apiKey": key}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def source_from(candidate: dict, extracted: dict) -> dict:
    url = extracted.get("urlCanonical") or candidate["url"]
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return {
        "title": extracted.get("sourceTitle") or candidate["publisher"],
        "uri": host,
        "location": {"country": {"label": candidate["publisherCountry"]}},
    }


def record(candidate: dict, key: str) -> tuple[dict | None, dict]:
    url = candidate["url"]
    mapped = post("https://eventregistry.org/api/v1/articleMapper", {"articleUrl": url}, key)
    uri = mapped.get(url)
    attempt = {"url": url, "uri": uri, "mapped": bool(uri), "terminalDisposition": None}
    if not isinstance(uri, str) or not uri:
        attempt["terminalDisposition"] = "held"
        attempt["reason"] = "mapper returned no article URI"
        return None, attempt
    primary = post(
        "https://eventregistry.org/api/v1/article/getArticle",
        {"action": "getArticle", "articleUri": uri, "infoArticleBodyLen": -1, "resultType": "info"},
        key,
    )
    primary_error = primary.get("error") if isinstance(primary, dict) else "invalid primary response"
    extracted = post("https://analytics.eventregistry.org/api/v1/extractArticleInfo", {"url": url}, key)
    body = str(extracted.get("body") or "").strip()
    published = extracted.get("datetime") or extracted.get("date")
    language = candidate["language"]
    if len(body) < 100 or not extracted.get("title") or not published:
        attempt.update(terminalDisposition="held", reason="recovery did not return a complete title, date, and body")
        return None, attempt
    result = {
        "uri": uri,
        "title": extracted["title"],
        "url": extracted.get("urlCanonical") or url,
        "dateTimePub": published,
        "lang": language,
        "body": body,
        "source": source_from(candidate, extracted),
    }
    attempt.update(
        terminalDisposition="admitted",
        endpoint="extractArticleInfo",
        primaryDisposition="held" if primary_error else "available",
        primaryReason=primary_error,
        bodyChars=len(body),
        bodySha256=hashlib.sha256(body.encode()).hexdigest(),
    )
    return result, attempt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", type=pathlib.Path)
    parser.add_argument("output_dir", type=pathlib.Path)
    parser.add_argument("--config", type=pathlib.Path, default=pathlib.Path(".env.local"))
    args = parser.parse_args()
    key = api_key(args.config)
    candidates = json.loads(args.candidates.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    attempts, admitted, seen_uris = [], [], set()
    for candidate in candidates:
        item, attempt = record(candidate, key)
        if item and item["uri"] in seen_uris:
            attempt.update(terminalDisposition="duplicate", reason="duplicate NewsAPI.ai URI")
        elif item:
            seen_uris.add(item["uri"])
            admitted.append(item)
        attempts.append(attempt)
    (args.output_dir / "mapping-retrieval-manifest.json").write_text(json.dumps(attempts, indent=2, ensure_ascii=False))
    (args.output_dir / "admitted-newsapi-response.json").write_text(json.dumps({"articles": {"results": admitted}}, indent=2, ensure_ascii=False))
    print(json.dumps({"candidates": len(candidates), "admitted": len(admitted), "held": sum(x["terminalDisposition"] == "held" for x in attempts), "duplicates": sum(x["terminalDisposition"] == "duplicate" for x in attempts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
