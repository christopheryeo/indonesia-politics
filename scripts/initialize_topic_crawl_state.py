#!/usr/bin/env python3
"""Initialize and validate durable crawl checkpoints on Topic Entity notes."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOPIC_ROOT = ROOT / "entities" / "topic"
SYSTEM = {"index.md", "catalog.md", "log.md", "_template.md"}
STATUSES = {"Not started", "Queued", "In progress", "Completed", "Failed", "Cancelled"}


class StateError(RuntimeError):
    pass


def topic_paths() -> list[Path]:
    return [path for path in sorted(TOPIC_ROOT.glob("*.md")) if path.name not in SYSTEM and not path.name.startswith("log-") and "conflicted copy" not in path.name.lower()]


def split(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise StateError("note lacks YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise StateError("note lacks closing YAML delimiter")
    return text[4:end], text[end + 5:]


def put(raw: str, name: str, value: str, after: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(name)}:\s*.*$")
    if len(pattern.findall(raw)) > 1:
        raise StateError(f"duplicate {name} field")
    if pattern.search(raw):
        return pattern.sub(f"{name}: {value}", raw, count=1)
    anchor = re.search(rf"(?m)^{re.escape(after)}:\s*.*$", raw)
    if not anchor:
        raise StateError(f"missing {after} anchor")
    return raw[:anchor.end()] + f"\n{name}: {value}" + raw[anchor.end():]


def initialize(apply: bool) -> dict[str, int | bool]:
    changed: list[tuple[Path, str]] = []
    for path in topic_paths():
        raw, body = split(path.read_text(encoding="utf-8"))
        data = yaml.safe_load(raw) or {}
        topic_id = str(data.get("topicId") or path.stem)
        if topic_id != path.stem:
            raise StateError(f"{path.name}: topicId must equal filename")
        updated = put(raw, "topicId", topic_id, "subtype")
        updated = put(updated, "lastCrawledAt", "null", "articleCount")
        status = data.get("crawlStatus") or "Not started"
        if status not in STATUSES:
            raise StateError(f"{path.name}: invalid crawlStatus {status!r}")
        updated = put(updated, "crawlStatus", str(status), "lastCrawledAt")
        status_at = data.get("crawlStatusAt")
        if status == "Not started":
            status_at = None
        if status == "Completed" and not data.get("lastCrawledAt"):
            raise StateError(f"{path.name}: Completed requires lastCrawledAt")
        rendered = "null" if status_at is None else str(status_at)
        updated = put(updated, "crawlStatusAt", rendered, "crawlStatus")
        if updated != raw:
            changed.append((path, str(data.get("displayName") or topic_id)))
            if apply:
                path.write_text("---\n" + updated + "\n---\n" + body, encoding="utf-8")
    if apply and changed:
        stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        with (TOPIC_ROOT / "log.md").open("a", encoding="utf-8") as ledger:
            for path, display in changed:
                ledger.write(f"- {stamp} | entity: [[{path.stem}|{display}]] | action: crawl checkpoint initialized | reasoning: legacy coverage retained; no historical crawl completion was inferred.\n")
    return {"topics": len(topic_paths()), "changed": len(changed), "applied": apply}


def validate() -> dict[str, int]:
    failures: list[str] = []
    for path in topic_paths():
        raw, _ = split(path.read_text(encoding="utf-8"))
        data = yaml.safe_load(raw) or {}
        if data.get("topicId") != path.stem:
            failures.append(f"{path.name}: missing or mismatched topicId")
        status = data.get("crawlStatus")
        if status not in STATUSES:
            failures.append(f"{path.name}: invalid crawlStatus")
        if "lastCrawledAt" not in data or "crawlStatusAt" not in data:
            failures.append(f"{path.name}: missing crawl fields")
        if status == "Not started" and (data.get("lastCrawledAt") is not None or data.get("crawlStatusAt") is not None):
            failures.append(f"{path.name}: Not started has a checkpoint")
        if status == "Completed" and not data.get("lastCrawledAt"):
            failures.append(f"{path.name}: Completed lacks checkpoint")
    if failures:
        raise StateError("; ".join(failures[:20]))
    return {"topics": len(topic_paths()), "failures": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(validate() if args.check else initialize(args.apply), indent=2))
        return 0
    except (StateError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
