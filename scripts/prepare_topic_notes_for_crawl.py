#!/usr/bin/env python3
"""Materialize the canonical crawl contract into every Indonesia Topic Entity note."""
from __future__ import annotations

import argparse
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOPIC_DIR = ROOT / "entities" / "topic"
REGISTRY_PATH = ROOT / "topics" / "canonical-topics.yaml"
SYSTEM = {"index.md", "catalog.md", "log.md", "_template.md"}
LOG_MARKER = "<!-- Generated from canonical topic state by scripts/prepare_topic_notes_for_crawl.py — do not hand-edit. -->"


def topic_paths() -> list[Path]:
    return [path for path in sorted(TOPIC_DIR.glob("*.md")) if path.name not in SYSTEM and not path.name.startswith("log-") and "conflicted copy" not in path.name.lower()]


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("topic note lacks frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("topic note lacks closing frontmatter delimiter")
    return text[:end + 5], text[end + 5:]


def section_bounds(body: str, title: str) -> tuple[int, int] | None:
    match = re.search(rf"(?m)^## {re.escape(title)}\s*$", body)
    if not match:
        return None
    next_heading = re.search(r"(?m)^## ", body[match.end():])
    end = match.end() + next_heading.start() if next_heading else len(body)
    return match.start(), end


def replace_section(body: str, title: str, content: str, before: str | None = None) -> str:
    rendered = f"## {title}\n{content.strip()}\n\n"
    found = section_bounds(body, title)
    if found:
        start, end = found
        return body[:start] + rendered + body[end:].lstrip("\n")
    if before:
        anchor = section_bounds(body, before)
        if anchor:
            return body[:anchor[0]].rstrip() + "\n\n" + rendered + body[anchor[0]:]
    return body.rstrip() + "\n\n" + rendered


def crawl_log(record: dict) -> str:
    status = record.get("crawlStatus") or "Not started"
    status_at = record.get("crawlStatusAt") or "—"
    completed = record.get("lastCrawledAt") or "never"
    count = record.get("articleCount", 0)
    return (
        f"{LOG_MARKER}\n\n"
        f"**Latest status:** `{status}` (at {status_at}); last successful crawl: {completed}.\n\n"
        "_No granular crawl episodes have been logged for this topic yet._\n\n"
        f"**Articles added to coverage:** {count} historical coverage link(s)."
    )


def registry() -> dict[str, dict]:
    value = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    records = value.get("topics")
    if not isinstance(records, list):
        raise ValueError("canonical topic registry has no topics list")
    mapped = {str(record.get("topicId")): record for record in records if isinstance(record, dict)}
    if len(mapped) != len(records):
        raise ValueError("canonical topic registry has missing or duplicate topic IDs")
    return mapped


def materialize(path: Path, record: dict) -> str:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    body = replace_section(body, "Crawl Prompt", f"```text\n{record['crawlPrompt']}\n```", before="Coverage")
    body = replace_section(body, "Definition", str(record["definition"]), before="Crawl Prompt")
    body = replace_section(body, "Crawl Log", crawl_log(record), before="Notes")
    body = replace_section(body, "Notes", "<!-- Optional monitoring context and related canonical topics. -->")
    return frontmatter + body.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    records = registry(); paths = topic_paths(); changed = 0
    for path in paths:
        if path.stem not in records:
            raise ValueError(f"{path.name}: missing from canonical topic registry")
        updated = materialize(path, records[path.stem])
        if updated != path.read_text(encoding="utf-8"):
            changed += 1
            if args.apply:
                path.write_text(updated, encoding="utf-8")
    if set(records) != {path.stem for path in paths}:
        raise ValueError("canonical registry and Topic Entity IDs differ")
    print(f"{'WROTE' if args.apply else 'DRY-RUN'}: {changed} of {len(paths)} topic notes {'updated' if args.apply else 'would change'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
