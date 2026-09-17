#!/usr/bin/env python3
"""Generate the canonical Indonesia Politics topic registry from Topic Entity notes."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "entities" / "topic"
OUTPUT = ROOT / "topics" / "canonical-topics.yaml"
SYSTEM = {"index.md", "catalog.md", "log.md", "_template.md"}


def paths() -> list[Path]:
    return [p for p in sorted(TOPICS.glob("*.md")) if p.name not in SYSTEM and not p.name.startswith("log-") and "conflicted copy" not in p.name.lower()]


def load(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"{path}: missing frontmatter")
    return yaml.safe_load(text.split("\n---\n", 1)[0][4:]) or {}


def phrase(values: list[str]) -> str:
    quoted = [f'"{value.replace(chr(34), chr(39))}"' for value in values if value]
    return " OR ".join(quoted) or '"Indonesia politics"'


def registry() -> dict:
    records = []
    for path in paths():
        data = load(path)
        topic_id = str(data.get("topicId") or path.stem)
        if topic_id != path.stem:
            raise ValueError(f"{path}: topicId must equal filename")
        display = str(data.get("displayName") or "").strip()
        if not display:
            raise ValueError(f"{path}: displayName is required")
        aliases = data.get("aliases") or []
        aliases = [str(value).strip() for value in aliases if str(value).strip()]
        seeds = list(dict.fromkeys([display, *aliases]))
        records.append({"topicId": topic_id, "displayName": display, "category": str(data.get("category") or "Uncategorised"), "aliases": aliases, "keywords": seeds, "definition": f"Monitors Indonesian political reporting materially related to {display}.", "crawlPrompt": f"({phrase(seeds)}) AND Indonesia", "advisorySources": [], "languages": ["eng", "ind"]})
    ids = [record["topicId"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate topic IDs")
    return {"schemaVersion": "indonesia-politics-canonical-topics.v1", "maximumActiveTopics": 90, "assignmentLimit": 3, "updated": dt.date.today().isoformat(), "scope": {"domain": "Indonesian politics", "regions": ["Indonesia"], "languages": ["eng", "ind"]}, "topics": records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    value = registry()
    rendered = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120)
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("ERROR: canonical topic registry is stale; run sync_canonical_topics.py --write")
            return 1
        print(f"CLEAN: {len(value['topics'])} canonical topics")
        return 0
    print(f"{'WROTE' if args.write else 'DRY-RUN'}: {len(value['topics'])} canonical topics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
