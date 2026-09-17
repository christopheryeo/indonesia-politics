# Indonesia Politics Project Agent Instructions

## Project

This repository is a file-based media-monitoring knowledge vault for Indonesian politics. It begins with an empty corpus and retains only the reusable system.

## Mandatory Startup

Before working in this repository, read `README.md`. For a specific operation, also read the matching procedure under `scripts/`.

## Operating Rules

1. Treat Markdown entity notes as the source of truth.
2. Preserve provenance from raw input through compiled article and entity links.
3. Never edit preserved source evidence under `raw/`.
4. Keep generated catalogs, query databases, run receipts, and dashboard data generated.
5. Keep schemas frozen. Record an approved system-rule change before changing a schema.
6. Use canonical piped Obsidian links whose target is the real filename and whose label is the display name.
7. Use `scripts/` for deterministic bookkeeping and procedures for judgment-based work.
8. Treat `#sensitive` records as restricted; do not export them without the applicable review.
9. Never commit credentials, local environment files, corpus data, dependencies, caches, or generated artifacts.

## Domain System Files

Every entity domain uses:

1. `index.md` — operating manual and field registry.
2. `catalog.md` — generated complete listing.
3. `log.md` — append-only audit ledger.

Do not hand-edit catalogs or rewrite historical log entries.

## Empty Baseline

The repository intentionally starts without articles, raw feeds, entity records, issues, decisions, query cache entries, monitoring topics, run receipts, or databases. Empty-state operation is a tested requirement, not an error.

This describes the shipped system, not necessarily the checkout in front of you. Corpus data is Git-ignored, so a fresh clone is empty while a working vault may hold thousands of notes. Check `README.md` § Current State and the cascade-status table in `entities/article/index.md` before assuming either state. Baseline tests detect a live vault and skip rather than fail.

## Schema Changes

`schemas/` is frozen. Record an approved change in `docs/SYSTEM_RULE_CHANGES.md` before editing a schema, and state which of the note corpus or the schema is being treated as authoritative.

## Timing

Time compile-and-cascade runs end to end. Report total elapsed time, articles processed, and average time per article. Use Singapore Time (SGT, UTC+8) for operator timestamps unless a source timestamp must be preserved exactly.
