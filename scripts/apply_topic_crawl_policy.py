#!/usr/bin/env python3
"""Apply the approved conservative resolution policy without another model call."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from enrich_radar_inputs import parse_frontmatter, replace_fields, split_note  # noqa: E402


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def policy_updates(consensus: dict[str, Any]) -> dict[str, Any]:
    """Return only documented defaults for fields still requiring review."""

    auto = consensus.get("autoApplicable") or {}
    updates: dict[str, Any] = {}
    if not auto.get("tone"):
        updates["tone"] = "Factual"
    if not auto.get("toneSentiment"):
        updates["toneSentiment"] = "Neutral"
    if not auto.get("eventType"):
        updates["eventType"] = "Unfacilitated"
    if not auto.get("metadata"):
        updates["category"] = "Non-institutional"
    if not auto.get("tags"):
        updates["tags"] = ["#source"]
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows: dict[str, dict[str, Any]] = {}
    for artifact in args.assessment:
        for assessment in json.loads(artifact.read_text(encoding="utf-8")).get("assessments", []):
            if (assessment.get("consensus") or {}).get("reviewRequired"):
                rows[str(assessment.get("path") or "")] = assessment
    resolved: list[dict[str, Any]] = []
    missing: list[str] = []
    for raw_path, assessment in sorted(rows.items()):
        path = resolve_path(raw_path)
        if not path.is_file():
            missing.append(raw_path)
            continue
        lines, body = split_note(path.read_text(encoding="utf-8"))
        updates = policy_updates(assessment["consensus"])
        if updates:
            path.write_text(
                "---\n" + "\n".join(replace_fields(lines, updates)) + "\n---\n\n" + body.rstrip() + "\n",
                encoding="utf-8",
            )
        resolved.append({"path": raw_path, "articleId": assessment.get("articleId"),
                         "disposition": "policy-resolved", "updates": updates})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"policyVersion": 1, "resolved": resolved, "missing": missing}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"resolved": len(resolved), "missing": missing}))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
