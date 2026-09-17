---
type: goal-contract
name: autonomous-topic-crawl
status: active
created: 2026-09-17
owner: Christopher Yeo
---

# Autonomous Indonesia Politics Topic Crawl

Use this contract with `scripts/topic_crawl_plan.md` for a restartable, governed crawl.
It permits local discovery, intake, reviewed enrichment, cascade, validation and topic checkpointing.
It does not permit production writes, schema changes, credential disclosure, invented source text, or
operations outside this vault.

Create one run folder per batch with `scripts/topic_crawl_goal_runner.py init`; process at most ten
topics per batch. Keep `candidates.ndjson` append-only and record exactly one terminal disposition
for every candidate: `cascaded`, `duplicate`, `off-topic`, `rejected`, or `held`. Cascade only
source-backed, policy-complete inputs after a month-specific dry run, then retain both successful
receipts. Close only when every selected topic has a verified completion checkpoint, every terminal
ledger row reconciles exactly, each cascaded record has all phase evidence and a Topic Coverage
backlink, no critical event is unresolved, and `goal-receipt.json` exists.

Individual duplicates, off-topic candidates, unavailable bodies, exhausted item retries, or normal
enrichment holds are recorded and do not require a handoff. Escalate only unavailable/rejected
credentials, systemic provider failure, provenance or manifest conflict, a required schema change,
an unauthorized action, or unrecoverable cascade/validation failure.
