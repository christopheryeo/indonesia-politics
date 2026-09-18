#!/usr/bin/env python3
"""Render a human-readable crawl log for one batch run folder.

Reads the per-topic ``crawl-manifest.json`` files and ``summary.json`` that
``crawl_all_topics.py`` writes under a batch run root, and emits ``crawl-log.md``
summarising queries, candidate/accepted/held counts, held reasons, intake, and
any per-query endpoint errors. Also prints a compact JSON diagnostics block on
stdout so an operator can study the run programmatically.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from collections import Counter


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=pathlib.Path, help="batch run folder, e.g. runs/2026-09-17/topic-crawls/batch-B1")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--date-start", required=True)
    parser.add_argument("--date-end", required=True)
    args = parser.parse_args()

    manifests = sorted(args.run_root.glob("*/crawl-manifest.json"))
    rows = []
    held_reasons: Counter = Counter()
    query_errors: list[dict] = []
    zero_accept: list[str] = []
    empty_candidates: list[str] = []
    total_candidates = total_accepted = total_held = total_intake = 0

    for mpath in manifests:
        m = load(mpath)
        slug = mpath.parent.name
        searches = m.get("searches") or []
        dispositions = m.get("dispositions") or []
        accepted = int(m.get("accepted") or 0)
        intake = (m.get("intake") or {})
        planned = int(intake.get("planned") or 0)
        candidates = sum(int(s.get("candidates") or 0) for s in searches)
        held = len(dispositions) - accepted
        for d in dispositions:
            if d.get("disposition") != "accepted":
                held_reasons[str(d.get("reason") or "unknown")] += 1
        for s in searches:
            if s.get("error"):
                query_errors.append({"topic": slug, "query": s.get("query"), "language": s.get("language"), "error": s.get("error")})
        if accepted == 0:
            zero_accept.append(slug)
        if candidates == 0 and not any(s.get("error") for s in searches):
            empty_candidates.append(slug)
        total_candidates += candidates
        total_accepted += accepted
        total_held += held
        total_intake += planned
        rows.append({
            "topic": m.get("topic") or slug, "slug": slug, "queries": len(searches),
            "candidates": candidates, "accepted": accepted, "held": held,
            "intakePlanned": planned, "errors": sum(1 for s in searches if s.get("error")),
            "intakeError": intake.get("error"),
        })

    lines: list[str] = []
    lines.append(f"# Crawl Log — Batch {args.batch}")
    lines.append("")
    lines.append(f"- **Date range:** {args.date_start} → {args.date_end} (inclusive, Asia/Singapore)")
    lines.append(f"- **Generated:** {dt.datetime.now().astimezone().isoformat(timespec='seconds')}")
    lines.append(f"- **Run root:** `{args.run_root}`")
    lines.append(f"- **Topics crawled:** {len(rows)}")
    lines.append(f"- **Totals:** candidates={total_candidates}, accepted={total_accepted}, "
                 f"held={total_held}, intake planned={total_intake}")
    lines.append(f"- **Zero-accept topics:** {len(zero_accept)}  |  **Zero-candidate topics:** {len(empty_candidates)}  |  **Query errors:** {len(query_errors)}")
    lines.append("")
    lines.append("## Per-topic")
    lines.append("")
    lines.append("| Topic | Queries | Candidates | Accepted | Held | Intake | Errors |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in sorted(rows, key=lambda x: (-x["accepted"], x["slug"])):
        lines.append(f"| {r['topic']} | {r['queries']} | {r['candidates']} | {r['accepted']} | "
                     f"{r['held']} | {r['intakePlanned']} | {r['errors']} |")
    lines.append("")
    lines.append("## Held / rejected reasons")
    lines.append("")
    if held_reasons:
        for reason, n in held_reasons.most_common():
            lines.append(f"- **{n}** — {reason}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Zero-accept topics")
    lines.append("")
    lines.append(("- " + "\n- ".join(zero_accept)) if zero_accept else "- (none)")
    lines.append("")
    lines.append("## Query endpoint errors")
    lines.append("")
    if query_errors:
        for e in query_errors:
            lines.append(f"- `{e['topic']}` [{e['language']}] {e['query']!r}: {e['error']}")
    else:
        lines.append("- (none)")
    lines.append("")

    out = args.run_root / "crawl-log.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    diagnostics = {
        "batch": args.batch, "topics": len(rows),
        "totals": {"candidates": total_candidates, "accepted": total_accepted,
                    "held": total_held, "intakePlanned": total_intake},
        "zeroAccept": zero_accept, "zeroCandidate": empty_candidates,
        "queryErrors": query_errors, "heldReasons": dict(held_reasons),
        "intakeErrors": [{"topic": r["slug"], "error": r["intakeError"]} for r in rows if r["intakeError"]],
        "logPath": str(out),
    }
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
