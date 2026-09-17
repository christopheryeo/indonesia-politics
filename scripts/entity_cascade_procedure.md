---
type: procedure
name: entity-cascade
status: active
last_updated: 2026-08-03
---

# Entity Cascade Procedure

Use this procedure after a raw input has been compiled into an article note.

New articles must carry `language: eng` or `language: ind`. Preserve titles, summaries, key points,
quotations, and source evidence in the source language; keep structural headings and fields in English.

## 1. Extract and resolve

1. Extract every wikilink and classified entity from the compiled article.
2. Resolve each candidate against the applicable domain catalog and aliases.
3. Do not create duplicates. Stop for review when identity is ambiguous.
4. Appointment notes are maintained from cited authoritative sources; the cascade does not create or count them.
5. Normalize English and Bahasa candidates for matching, then resolve both forms through the same canonical note's aliases.
6. Stop for review when a normalized alias maps to more than one note; never choose or merge automatically.

## 2. Create or update entities

1. Read the target domain's `index.md` and use only its registered fields.
2. Create canonical slugs and include the display name in `aliases`.
3. Use `[[real-filename|Display Name]]` for all links.
4. Populate summaries only from the ingested source material.
5. Add an article backlink under `## Coverage`.
6. Use `scripts/patch_coverage.py` for idempotent Coverage insertion and count maintenance.
7. Quote YAML tags beginning with `#`, for example `tags: ['#sensitive']`.
8. Never infer sensitivity from keywords. Apply `#sensitive` only when the input is explicitly marked restricted.
9. Use official Indonesian display names for Indonesian institutions and places, retain stable existing filenames, and register reviewed English and Bahasa forms as aliases.
10. Keep analytical topics and Issue Radar tags canonical in English, with reviewed Bahasa synonyms resolving to them.

## 3. Reconcile

1. Update each affected entity's related links without removing valid existing relationships.
2. Regenerate every affected catalog with `scripts/generate_catalog.py <domain>`.
3. Append one timestamped audit entry per created or updated entity.
4. Never rewrite earlier log entries.

## 4. Validate

1. Run `scripts/article_quality.py --check` for the compiled article.
2. Run `scripts/check_links.py`.
3. Treat schema errors, broken links, invalid YAML, or failed count reconciliation as blocking.
4. Use `scripts/fix_links.py` only for its documented deterministic repair classes.
5. Record elapsed time, article count, and average processing time.
6. Report article counts by `eng` and `ind`, plus language holds.

The cascade is complete only when the article is in `entities/article/YYYY-MM/`, all required entity backlinks and counts are reconciled, catalogs are regenerated, logs are appended, and validation passes.
