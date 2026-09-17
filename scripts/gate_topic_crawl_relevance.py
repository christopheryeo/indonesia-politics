#!/usr/bin/env python3
"""Batch-gate admitted NewsAPI articles for relevance to one canonical topic.

This intentionally uses one low-reasoning request for a small batch of source
bodies.  It is a cheaper gate than the two-pass enrichment assessment and its
output is evidence only: candidates still need normalisation, enrichment and
the cascade validation gates.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from local_env import load_local_env  # noqa: E402

API_URL = "https://api.openai.com/v1/responses"
MAX_BODY_CHARS = 5_000
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["assessments"],
    "properties": {"assessments": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["uri", "disposition", "confidence", "reason"],
        "properties": {
            "uri": {"type": "string"},
            "disposition": {"type": "string", "enum": ["relevant", "off-topic", "held"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
    }}},
}


class RelevanceError(RuntimeError):
    """A user-facing relevance-gate error."""


def section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in text:
        raise RelevanceError(f"topic note is missing {marker}")
    return text.split(marker, 1)[1].split("\n## ", 1)[0].replace("```text", "").replace("```", "").strip()


def topic_context(topic_id: str) -> dict[str, str]:
    path = ROOT / "entities" / "topic" / f"{topic_id}.md"
    if not path.is_file():
        raise RelevanceError(f"unknown topic ID: {topic_id}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise RelevanceError(f"{path}: missing frontmatter")
    frontmatter = yaml.safe_load(text.split("\n---", 1)[0][4:]) or {}
    if (frontmatter.get("type"), frontmatter.get("subtype")) != ("entity", "topic") or frontmatter.get("status") != "active":
        raise RelevanceError(f"{topic_id}: topic must be active")
    return {
        "topicId": topic_id,
        "displayName": str(frontmatter.get("displayName") or "").strip(),
        "definition": section(text, "Definition"),
        "crawlPrompt": section(text, "Crawl Prompt"),
    }


def response_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content["text"])
    raise RelevanceError("model returned no output text")


def records_from_input(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = (payload.get("articles") or {}).get("results")
    if not isinstance(records, list):
        raise RelevanceError(f"{path}: expected articles.results list")
    return records


def candidates(inputs: list[Path]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for source in inputs:
        for article in records_from_input(source):
            uri = str(article.get("uri") or "").strip()
            if not uri or uri in seen:
                continue
            seen.add(uri)
            result.append({
                "uri": uri,
                "title": str(article.get("title") or ""),
                "date": str(article.get("dateTimePub") or article.get("date") or ""),
                "url": str(article.get("url") or ""),
                "body": str(article.get("body") or "")[:MAX_BODY_CHARS],
            })
    return result


def evaluate(key: str, model: str, topic: dict[str, str], records: list[dict[str, str]]) -> list[dict[str, Any]]:
    prompt = json.dumps({
        "task": "Classify supplied provider articles for relevance to exactly one topic.",
        "rules": [
            "Use only supplied title, metadata, and source body.",
            "relevant means the article substantively fits the topic definition and crawl prompt.",
            "off-topic means it clearly does not fit; held means evidence is insufficient or borderline.",
            "Return exactly one assessment for every supplied URI; do not use outside knowledge.",
        ], "topic": topic, "articles": records,
    }, ensure_ascii=False)
    request = urllib.request.Request(API_URL, data=json.dumps({
        "model": model, "input": prompt, "store": False, "reasoning": {"effort": "low"},
        "text": {"format": {"type": "json_schema", "name": "topic_relevance", "strict": True, "schema": SCHEMA}},
    }, ensure_ascii=False).encode(), method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.loads(response_text(json.loads(response.read().decode("utf-8"))))["assessments"]
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise RelevanceError(f"relevance request failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, help="canonical topic ID")
    parser.add_argument("--input", type=Path, action="append", required=True, help="admitted NewsAPI response; repeatable")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--model", default="gpt-5.6")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.batch_size < 1 or args.offset < 0 or args.limit is not None and args.limit < 1:
        raise SystemExit("batch-size and limit must be positive; offset cannot be negative")
    topic = topic_context(args.topic)
    selected = candidates([path.resolve() for path in args.input])
    selected = selected[args.offset:args.offset + args.limit if args.limit is not None else None]
    if not selected:
        raise SystemExit("no candidates matched")
    load_local_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENAI_API_KEY is unavailable")
    assessments: list[dict[str, Any]] = []
    for start in range(0, len(selected), args.batch_size):
        batch = selected[start:start + args.batch_size]
        print(f"{args.topic}: reviewing {start + 1}-{start + len(batch)} of {len(selected)}", flush=True)
        assessments.extend(evaluate(key, args.model, topic, batch))
    if {item.get("uri") for item in assessments} != {item["uri"] for item in selected} or len(assessments) != len(selected):
        raise SystemExit("model did not return exactly one assessment per candidate")
    output = {"operation": "topic_relevance_gate", "topic": topic, "model": args.model,
              "candidateCount": len(selected), "assessments": assessments}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "candidates": len(selected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RelevanceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
