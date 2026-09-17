#!/usr/bin/env python3
"""Persist, validate, reconcile, and close restartable Indonesia topic crawl goals."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"cascaded", "duplicate", "off-topic", "rejected", "held"}
PHASES = {"identity", "date", "completeness", "relevance", "normalized", "enriched", "dryRun", "cascaded", "topicLinked", "validated"}
CRITICAL = {"credential-unavailable", "credential-rejected", "required-discovery-unavailable", "provider-systemic-failure", "provenance-conflict", "manifest-integrity-failure", "unauthorized-write-required", "production-action-required", "unrecoverable-validation-failure"}


class GoalError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoalError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GoalError(f"{path} must be a JSON object")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoalError(f"{path}:{line_no}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise GoalError(f"{path}:{line_no}: candidate must be an object")
        row["_line"] = line_no
        result.append(row)
    return result


def receipt_valid(path_value: Any, month: str, dry_run: bool) -> bool:
    if not isinstance(path_value, str) or not path_value:
        return False
    try:
        value = load(ROOT / path_value)
    except GoalError:
        return False
    metrics, metadata = value.get("articleMetrics"), value.get("metadata")
    return value.get("operation") == "ingest_cascade" and value.get("status") == "ok" and isinstance(metrics, dict) and isinstance(metadata, dict) and metadata.get("month") == month and metadata.get("dryRun") is dry_run and isinstance(metrics.get("processedCount"), int) and metrics["processedCount"] > 0 and metrics.get("failedCount") == 0


def coverage_has_article(topic_id: str, article_path: str) -> bool:
    path = ROOT / "entities" / "topic" / f"{topic_id}.md"
    if not path.exists():
        return False
    coverage = path.read_text(encoding="utf-8").partition("## Coverage\n")[2].partition("\n## ")[0]
    return Path(article_path).stem in coverage


def validate(state: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []; seen_ids: set[str] = set(); seen_identity: set[str] = set(); months: set[str] = set()
    counts = {name: 0 for name in sorted(TERMINAL)}
    topics = set(state.get("topics") or [])
    if not topics:
        errors.append("goal has no selected topics")
    for row in candidates:
        line = row["_line"]; candidate_id = str(row.get("candidateId") or "").strip(); topic = str(row.get("topicId") or "").strip()
        disposition = str(row.get("disposition") or "").strip(); identity = str(row.get("providerUri") or row.get("canonicalUrl") or candidate_id).strip()
        if not candidate_id or candidate_id in seen_ids: errors.append(f"line {line}: missing or duplicate candidateId")
        seen_ids.add(candidate_id)
        if topic not in topics: errors.append(f"line {line}: unknown topicId {topic!r}")
        if row.get("set") not in {"A", "B"}: errors.append(f"line {line}: set must be A or B")
        if disposition not in TERMINAL:
            errors.append(f"line {line}: invalid disposition"); continue
        counts[disposition] += 1
        if not str(row.get("reason") or "").strip(): errors.append(f"line {line}: missing evidence-backed reason")
        if identity in seen_identity and disposition != "duplicate": errors.append(f"line {line}: duplicate identity requires duplicate disposition")
        seen_identity.add(identity)
        if disposition == "duplicate" and not row.get("duplicateOf"): errors.append(f"line {line}: duplicate requires duplicateOf")
        if disposition == "held" and not row.get("holdStage"): errors.append(f"line {line}: held requires holdStage")
        if disposition == "cascaded":
            article, intake = str(row.get("articlePath") or ""), str(row.get("intakePath") or "")
            if not article or not intake or not (ROOT / article).exists(): errors.append(f"line {line}: cascaded requires existing intakePath and articlePath")
            elif not coverage_has_article(topic, article): errors.append(f"line {line}: target Coverage does not link articlePath")
            else:
                parts = Path(article).parts
                try: months.add(parts[parts.index("article") + 1])
                except (ValueError, IndexError): errors.append(f"line {line}: articlePath must be under entities/article/YYYY-MM")
            phases = row.get("phaseEvidence")
            if not isinstance(phases, dict) or any(not str(phases.get(name) or "").strip() for name in PHASES): errors.append(f"line {line}: cascaded lacks complete phaseEvidence")
    for event in state.get("criticalEvents") or []:
        if not isinstance(event, dict) or event.get("kind") not in CRITICAL or event.get("resolved") is not True: errors.append("unresolved or unknown critical event")
    for topic in topics:
        checkpoint = (state.get("topicCompletion") or {}).get(topic)
        if not isinstance(checkpoint, dict) or checkpoint.get("status") != "completed" or not checkpoint.get("verifiedAt"): errors.append(f"topic {topic}: completion checkpoint is not verified")
    for month in months:
        item = (state.get("monthReceipts") or {}).get(month)
        if not isinstance(item, dict) or not receipt_valid(item.get("dryRunReceipt"), month, True) or not receipt_valid(item.get("cascadeReceipt"), month, False): errors.append(f"month {month}: missing valid dry-run/real receipts")
    return {"valid": not errors, "candidateCount": len(candidates), "terminalCounts": counts, "errors": errors, "state": state.get("status")}


def init(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    if args.date_start > args.date_end: raise GoalError("date-start must not be later than date-end")
    if not all((ROOT / "entities" / "topic" / f"{topic}.md").exists() for topic in args.topic): raise GoalError("one or more selected topics do not exist")
    run_dir.mkdir(parents=True, exist_ok=False)
    state = {"schemaVersion": "topic-crawl-goal.v1", "status": "running", "startedAt": now(), "updatedAt": now(), "topics": list(dict.fromkeys(args.topic)), "dateStart": args.date_start, "dateEnd": args.date_end, "timezone": args.timezone, "maxCandidatesPerSet": args.max_candidates, "batchSize": args.batch_size, "retryPolicy": {"maxAttempts": args.max_attempts, "backoffSeconds": args.backoff_seconds}, "policy": "schemas/topic_crawl_resolution_policy.yaml", "criticalEvents": [], "topicCompletion": {}, "monthReceipts": {}}
    write(run_dir / "goal-state.json", state); (run_dir / "candidates.ndjson").write_text("", encoding="utf-8")
    print(json.dumps({"runDir": str(run_dir), "topics": state["topics"], "status": "running"}, indent=2)); return 0


def reconcile(args: argparse.Namespace, close: bool) -> int:
    run_dir = args.run_dir.resolve(); state = load(run_dir / "goal-state.json"); result = validate(state, rows(run_dir / "candidates.ndjson")); result["runDir"] = str(run_dir)
    if close and result["valid"]:
        state.update({"status": "completed", "completedAt": now(), "updatedAt": now()}); write(run_dir / "goal-state.json", state)
        write(run_dir / "goal-receipt.json", {"schemaVersion": "topic-crawl-goal-receipt.v1", "status": "ok", "startedAt": state["startedAt"], "endedAt": state["completedAt"], "topics": state["topics"], "candidateMetrics": result["terminalCounts"], "candidateCount": result["candidateCount"], "reconciliation": "one terminal disposition per candidate", "monthReceipts": state["monthReceipts"]}); result["closed"] = True
    elif close: result["closed"] = False
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["valid"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest="command", required=True)
    init_p = commands.add_parser("init"); init_p.add_argument("--run-dir", type=Path, required=True); init_p.add_argument("--topic", action="append", required=True); init_p.add_argument("--date-start", required=True); init_p.add_argument("--date-end", required=True); init_p.add_argument("--timezone", default="Asia/Singapore"); init_p.add_argument("--max-candidates", type=int, default=500); init_p.add_argument("--batch-size", type=int, default=10); init_p.add_argument("--max-attempts", type=int, default=3); init_p.add_argument("--backoff-seconds", type=int, default=20)
    for name in ("reconcile", "close"): commands.add_parser(name).add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    try: return init(args) if args.command == "init" else reconcile(args, args.command == "close")
    except GoalError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
