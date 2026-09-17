# Indonesia Politics Media Monitoring

An empty, reusable knowledge-vault system for monitoring Indonesian political media. It ingests raw media items, compiles them into structured Markdown article notes, cascades links to related entities, supports deterministic queries, and provides an issue-radar dashboard.

The vault supports English (`eng`) and Bahasa Indonesia (`ind`) source material. Source prose is
preserved in its original language; machine-facing schemas and headings remain English.

The Markdown notes are the source of truth. Catalogs, run receipts, dashboard data, and query databases are generated artifacts.

## Current State

This checkout is a **live vault**, not the empty baseline. The sections below describe the reusable
system and its empty-state contract, which the baseline tests still assert and which apply when the
system is redeployed for another beat. They do not describe what is in this working copy.

| | |
|---|---|
| Articles | 250 (May–Aug 2026), 100% cascaded, 0 inputs pending |
| Entity notes | 130 across 8 populated domains — 55 outlets, 50 topics, 10 people, 8 organisations, 3 decisions, 2 countries, 2 places |
| Empty domains | `appointments`, `issues`, `search` |
| Entity links | 1,926 (7.7 per article) |
| Last quality audit | 2026-08-13 — see `docs/SYSTEM_RULE_CHANGES.md` for approved schema changes |

Corpus data is not tracked by Git (see `.gitignore`), so a fresh clone reproduces the empty baseline
described below.

## Directory Structure

- `Inputs/articles/` — raw items awaiting compilation and cascade.
- `raw/` — preserved upstream deliveries; never edit source evidence directly.
- `entities/` — article and entity domains.
- `schemas/` — frozen article and outlet schemas.
- `scripts/` — deterministic tooling and operating procedures.
- `topics/` — monitoring-topic definitions; intentionally empty at baseline.
- `dashboards/` — dashboard definitions and web application.
- `runs/` — generated operation receipts.
- `index/` — generated query databases.
- `tests/` — synthetic, corpus-independent automated tests.

## Entity System Files

Every folder under `entities/` contains:

1. `index.md` — the hand-maintained operating manual and field registry.
2. `catalog.md` — a generated listing; never edit manually.
3. `log.md` — an append-only audit ledger.

At baseline, all catalogs and logs are empty.

## Core Workflow

For the complete reusable workflow—including snapshotting, enrichment, review holds, Wiki cascade,
database loading, quality gates, synchronization tests, success conditions, and breakout
conditions—follow [`scripts/generic_article_ingestion_procedure.md`](scripts/generic_article_ingestion_procedure.md).

1. Place raw input notes under `Inputs/articles/YYYY-MM/`.
2. Enrich and review them if required.
3. Run the compile-and-cascade workflow in `scripts/ingest_cascade.py`.
4. Rebuild catalogs with `scripts/generate_catalog.py`.
5. Validate links with `scripts/check_links.py`.
6. Query the vault with `scripts/query.py`.
7. Generate dashboard data from the Markdown source of truth.

See the corresponding procedure documents under `scripts/` before operating a workflow.

For a governed, topic-specific NewsAPI.ai crawl, use
[`scripts/topic_crawl_plan.md`](scripts/topic_crawl_plan.md). It is the entrypoint for URL
discovery, NewsAPI.ai URI retrieval, source-completeness gates, the existing intake bridge,
reviewed enrichment, and Markdown cascade.

The topic registry is generated from canonical Topic Entity notes at
[`topics/canonical-topics.yaml`](topics/canonical-topics.yaml). Before its first use, initialise and
verify explicit crawl checkpoints with `python3 scripts/initialize_topic_crawl_state.py --apply` and
`--check`, then regenerate the registry with `python3 scripts/sync_canonical_topics.py --write`.
For a resumable multi-topic operation, follow
[`scripts/topic_crawl_goal_contract.md`](scripts/topic_crawl_goal_contract.md).
Use `scripts/update_topic_crawl_status.py` for the only permitted workflow-state transitions; it
rejects invalid transitions and requires an actual timezone-qualified completion time.

## Empty-Vault Behaviour

- Catalog generation produces valid zero-row tables.
- Link checking succeeds when no entity notes exist.
- Ingestion dry runs succeed when there are no input articles.
- Deterministic query primitives return empty results without failing.
- Dashboard generation produces a valid zero-state view.

## Configuration

Copy `.env.example` to the ignored `.env.local` only when local credentials or connection settings are required. `NEWSAPI_AI_API_KEY` is required only for `scripts/topic_crawl_plan.md` and is runtime-only: never commit, log, or retain it in crawl evidence. Never commit secrets.

The initial repository contains no monitoring topics, sources, schedules, corpus records, operational history, credentials, deployment identity, or inherited Git history.

## Version Control

Git tracks code, schemas, procedures, tests, domain manuals, and empty system ledgers. It excludes corpus data, generated catalogs, generated databases, run artifacts, local credentials, dependencies, and caches.

This system was migrated from `media-monitoring` commit `d969639` without importing source data or Git history. See [`docs/MIGRATION_PLAN.md`](docs/MIGRATION_PLAN.md) and [`docs/MIGRATION_REPORT.md`](docs/MIGRATION_REPORT.md).
