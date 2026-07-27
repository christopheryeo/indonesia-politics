# Migration Report

## Result

The reusable monitoring system was migrated into `indonesia-politics` from the committed `media-monitoring` baseline without source corpus data, operational history, credentials, deployment identity, generated databases, or inherited Git history.

## Source Integrity

- Source branch: `main`
- Source commit and `origin/main`: `d9696392ad1b7a7ce6ea0c7f35f6e7340b23460d`
- Source tree: `c43f90f3f9db1eb7e0f59575ac8abbf0c6f1250f`
- Source filesystem checksum before migration: `af58d80714ff0feba9d433bc9471ad1b59b4629e1995b3b0cc09d89c0aef9af0`
- Source filesystem checksum after migration: `af58d80714ff0feba9d433bc9471ad1b59b4629e1995b3b0cc09d89c0aef9af0`
- Source working tree after migration: clean

## Retained System

1. Python ingestion, cascade, query, quality, link, enrichment, radar, staging, and maintenance tooling.
2. SQL staging and rollback definitions.
3. Article and outlet schemas.
4. Synthetic automated tests, including the committed query-latency fast-path coverage.
5. Dashboard application source, package lock, linting, rendering tests, and zero-state data generator.
6. Stable Obsidian settings.
7. All eleven entity-domain directories with adapted indexes, empty generated catalogs, and empty audit logs.
8. Empty runtime structures for input, raw source, runs, indexes, temporary files, and monitoring topics.

## Excluded State

1. Raw and input articles.
2. Compiled articles and entity records.
3. Issue assessments and source-corpus decisions.
4. Historical audit-log entries and run receipts.
5. Existing monitoring topics and schedules.
6. Query databases, generated dashboard data, and build artifacts.
7. Credentials, local environment files, caches, and dependencies.
8. Source deployment identity and social preview image.
9. Source Git objects, commits, refs, worktrees, and remotes.

## Indonesia Adaptation

1. Renamed the vault and dashboard for Indonesia-politics monitoring.
2. Replaced SAF/MINDEF/DSTA-specific configuration, examples, defaults, and tests.
3. Generalised restricted-content handling from `saf`/`#saf` to `sensitive`/`#sensitive`.
4. Removed keyword-based sensitivity inference; restriction is now explicit input metadata.
5. Rebuilt domain manuals and empty ledgers without source-corpus references.
6. Added an intentional dashboard empty state and empty-corpus query response.
7. Added a secrets-free `.env.example` and migration-specific isolation tests.

## Verification

- Python unit and migration-baseline tests: **35 passed**
- Python syntax compilation: **passed**
- JSON/YAML validation: **14 files passed**
- Catalog generation: **11 empty catalogs generated**
- Wikilink integrity: **clean**
- Empty ingestion dry run: **0 articles; clean exit**
- Empty query: **unresolved with “No matching data” response; no API key required**
- Dashboard dependency installation from lockfile: **passed**
- Dashboard lint: **passed**
- Dashboard production build: **passed**
- Dashboard server-render tests: **2 passed**
- Runtime data scan: **clean**
- Entity-record scan: **clean**
- Credential/database/archive/deployment scan: **clean**
- Source-corpus term and known-ID scan: **clean**

## Destination Version Control

The destination is initialised as a fresh standalone repository with no remote and no inherited source objects. The baseline commit is created only after all checks above pass.

## Residual Risks

1. No live feed, MySQL, OpenAI API, or production deployment was exercised because the baseline intentionally contains no credentials, source data, or deployment identity.
2. The first real Indonesia-politics data load should be treated as a controlled pilot and should repeat schema, cascade, link, query, and dashboard validation.
