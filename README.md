# Indonesia Politics Media Monitoring

An empty, reusable knowledge-vault system for monitoring Indonesian political media. It ingests raw media items, compiles them into structured Markdown article notes, cascades links to related entities, supports deterministic queries, and provides an issue-radar dashboard.

The Markdown notes are the source of truth. Catalogs, run receipts, dashboard data, and query databases are generated artifacts.

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

1. Place raw input notes under `Inputs/articles/YYYY-MM/`.
2. Enrich and review them if required.
3. Run the compile-and-cascade workflow in `scripts/ingest_cascade.py`.
4. Rebuild catalogs with `scripts/generate_catalog.py`.
5. Validate links with `scripts/check_links.py`.
6. Query the vault with `scripts/query.py`.
7. Generate dashboard data from the Markdown source of truth.

See the corresponding procedure documents under `scripts/` before operating a workflow.

## Empty-Vault Behaviour

- Catalog generation produces valid zero-row tables.
- Link checking succeeds when no entity notes exist.
- Ingestion dry runs succeed when there are no input articles.
- Deterministic query primitives return empty results without failing.
- Dashboard generation produces a valid zero-state view.

## Configuration

Copy `.env.example` to the ignored `.env.local` only when local credentials or connection settings are required. Never commit secrets.

The initial repository contains no monitoring topics, sources, schedules, corpus records, operational history, credentials, deployment identity, or inherited Git history.

## Version Control

Git tracks code, schemas, procedures, tests, domain manuals, and empty system ledgers. It excludes corpus data, generated catalogs, generated databases, run artifacts, local credentials, dependencies, and caches.

This system was migrated from `media-monitoring` commit `d969639` without importing source data or Git history. See [`docs/MIGRATION_PLAN.md`](docs/MIGRATION_PLAN.md) and [`docs/MIGRATION_REPORT.md`](docs/MIGRATION_REPORT.md).
