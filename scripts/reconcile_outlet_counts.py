#!/usr/bin/env python3
"""Recompute outlet articleCount from unique Coverage backlinks.

Outlet counts are corpus-wide totals, so patch_coverage.py intentionally does
not increment them one link at a time. Run this reconciliation after a cascade
batch to derive the count from Markdown source-of-truth Coverage sections.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTLETS = ROOT / "entities" / "outlet"
SYSTEM = {"index.md", "catalog.md", "log.md", "_template.md", ".DS_Store"}


def coverage_ids(text: str) -> set[str]:
    match = re.search(r"(?ms)^## Coverage\s*$\n(.*?)(?=^## |\Z)", text)
    if not match:
        return set()
    return set(re.findall(r"\[\[(article/[^|\]#]+)", match.group(1)))


def scalar(text: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*(.*?)\s*$", text)
    return (match.group(1).strip().strip("'\"") if match else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply reconciled counts; default is check-only")
    parser.add_argument("--no-run-log", action="store_true", help="reserved for consistency with other bookkeeping tools")
    args = parser.parse_args()
    mismatches = []
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    today = now[:10]
    log_lines = []
    for path in sorted(OUTLETS.glob("*.md")):
        if path.name in SYSTEM:
            continue
        text = path.read_text(encoding="utf-8")
        actual = len(coverage_ids(text))
        declared_raw = scalar(text, "articleCount")
        if not declared_raw.isdigit():
            raise RuntimeError(f"{path.relative_to(ROOT)} has missing or invalid articleCount")
        declared = int(declared_raw)
        if declared == actual:
            continue
        display = scalar(text, "displayName") or path.stem
        mismatches.append({"outlet": path.stem, "displayName": display, "before": declared, "after": actual})
        if args.write:
            updated, count_replacements = re.subn(
                r"(?m)^articleCount:\s*\d+\s*$", f"articleCount: {actual}", text, count=1
            )
            if count_replacements != 1:
                raise RuntimeError(f"failed to update articleCount in {path.relative_to(ROOT)}")
            updated = re.sub(r"(?m)^last_updated:.*$", f"last_updated: {now}", updated, count=1)
            path.write_text(updated, encoding="utf-8")
            log_lines.append(
                f"- {now} - Reconciled [[{path.stem}|{display}]] articleCount "
                f"from {declared} to {actual} using unique Coverage backlinks."
            )
    if args.write and log_lines:
        log_path = OUTLETS / "log.md"
        log_text = log_path.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(log_lines) + "\n"
        actual_entries = len(re.findall(r"(?m)^- ", log_text))
        log_text, replacements = re.subn(
            r"(?m)^entry_count:\s*\d+\s*$", f"entry_count: {actual_entries}", log_text, count=1
        )
        if replacements != 1:
            raise RuntimeError("outlet log lacks entry_count")
        log_path.write_text(log_text, encoding="utf-8")
    result = {
        "status": "reconciled" if args.write else ("passed" if not mismatches else "mismatch"),
        "outletsScanned": len([p for p in OUTLETS.glob("*.md") if p.name not in SYSTEM]),
        "mismatches": len(mismatches),
        "changes": mismatches,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.write or not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
