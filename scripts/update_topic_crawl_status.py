#!/usr/bin/env python3
"""Apply one validated crawl-status transition to an Indonesia Topic Entity."""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "entities" / "topic"
STATUSES = {"Not started", "Queued", "In progress", "Completed", "Failed", "Cancelled"}
TRANSITIONS = {"Not started": {"Queued"}, "Queued": {"In progress", "Failed", "Cancelled"}, "In progress": {"Completed", "Failed", "Cancelled"}, "Completed": {"Queued"}, "Failed": {"Queued"}, "Cancelled": {"Queued"}}


def split(text: str) -> tuple[str, str]:
    return text[4:text.find("\n---\n", 4)], text[text.find("\n---\n", 4) + 5:]


def replace(raw: str, key: str, value: str) -> str:
    return re.sub(rf"(?m)^{re.escape(key)}:\s*.*$", f"{key}: {value}", raw, count=1)


def resolve(value: str) -> Path:
    matches = []
    for path in TOPICS.glob("*.md"):
        if path.name in {"index.md", "catalog.md", "log.md", "_template.md"} or path.name.startswith("log-"):
            continue
        raw, _ = split(path.read_text(encoding="utf-8")); data = yaml.safe_load(raw) or {}
        identities = [path.stem, str(data.get("topicId") or ""), str(data.get("displayName") or ""), *[str(x) for x in data.get("aliases") or []]]
        if value.casefold() in {item.casefold() for item in identities}:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError("topic must resolve to exactly one canonical Topic Entity")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True); parser.add_argument("--status", required=True)
    parser.add_argument("--reason", default="explicit operator status update")
    parser.add_argument("--completed-at", help="required timezone-qualified completion instant")
    args = parser.parse_args()
    try:
        if args.status not in STATUSES: raise ValueError(f"status must be one of {sorted(STATUSES)}")
        path = resolve(args.topic); raw, body = split(path.read_text(encoding="utf-8")); data = yaml.safe_load(raw) or {}
        current = data.get("crawlStatus")
        if current == args.status:
            print(f"NO-OP: {path.stem} is already {args.status}"); return 0
        if args.status not in TRANSITIONS.get(current, set()): raise ValueError(f"{current!r} cannot transition to {args.status!r}")
        stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        if args.status == "Completed":
            if not args.completed_at: raise ValueError("Completed requires --completed-at")
            parsed = dt.datetime.fromisoformat(args.completed_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None: raise ValueError("completed-at requires a timezone")
            completed = parsed.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            raw = replace(raw, "lastCrawledAt", completed)
        raw = replace(raw, "crawlStatus", args.status); raw = replace(raw, "crawlStatusAt", stamp)
        path.write_text("---\n" + raw + "\n---\n" + body, encoding="utf-8")
        display = data.get("displayName") or path.stem
        with (TOPICS / "log.md").open("a", encoding="utf-8") as ledger:
            ledger.write(f"- {stamp} | entity: [[{path.stem}|{display}]] | action: crawl status transition | from: {current} | to: {args.status} | reason: {args.reason}\n")
        print(f"UPDATED: {path.stem}: {current} -> {args.status}"); return 0
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
