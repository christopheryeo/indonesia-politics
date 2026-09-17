# System Rule Changes

`AGENTS.md` rule 5 freezes the schemas under `schemas/`. A schema may change only after the change
is approved and recorded here. This file is the ledger of those approvals. Append new entries at the
end; never rewrite a prior entry.

---

## SRC-001 — Align `schemas/article.yaml` with the article registry

- **Date:** 2026-08-13 (SGT)
- **Approved by:** Christopher
- **Schema:** `schemas/article.yaml`
- **Trigger:** Wiki quality check, 2026-08-13

### Problem

`schemas/article.yaml` declared a field set that no part of the running system used:

| Schema declared | Reality |
|---|---|
| `articleId` | notes write `sourceId` |
| `url` | notes write `sourceUrl` |
| `articleTitle` | not a frontmatter key; the title is the note H1 |
| `outlets`, `countries` | body wikilinks, not frontmatter |
| `category`, `topic`, `mediaCount` | never written by the compiler |

All 222 compiled notes carry an identical key set that matches the registry table in
`entities/article/index.md`, which is what `scripts/article_quality.py` enforces. Nothing in
`scripts/`, `tests/`, or `dashboards/` reads `schemas/article.yaml`, so the drift produced no runtime
failure — it made the schema a misleading document for anyone treating it as the contract.

### Decision

Update the schema to describe the system as built. Per `AGENTS.md` rule 1, the Markdown entity notes
are the source of truth; where a frozen schema and the notes disagree and the notes are internally
consistent across the whole corpus, the schema is the stale artefact.

The rejected alternative was migrating all 222 notes to the schema's field names. That would have
touched every article, `article_quality.py`, `ingest_cascade.py`, and the dashboard generator to
resolve a documentation defect, with no gain in correctness.

### Change

`id_field` `articleId` → `sourceId`. `url` → `sourceUrl`. Added `sourceType`, `status`, `aliases`,
which the registry requires and the notes carry. Removed `articleId`, `url`, `articleTitle` as
stored keys, and `outlets`, `countries`, `category`, `topic`, `mediaCount`. Added a `notes` block
recording where titles and entity relations actually live, and this supersession.

`title_field: articleTitle` is retained to name the display concept. It is not a stored key.

### Scope

Schema file only. No note, script, test, or generated artefact was modified. Verified after the
change: `check_links.py` clean, `article_quality.py` 0 errors / 0 warnings across 222 notes,
`pytest tests/` 58 passed.

---

## SRC-002 — Governed Topic Crawl State and Resolution Policy

- **Date:** 2026-09-17 (SGT)
- **Approved by:** Christopher
- **Schema:** `schemas/topic_crawl_resolution_policy.yaml`
- **Trigger:** Align Indonesia Politics Wiki crawling and topic operations with the established
  AI Animation Wiki governance model.

### Decision

Add a conservative, source-backed resolution policy for topic-crawl holds and policy-complete
enrichment. Topic crawl workflow state is stored in Topic Entity frontmatter and mirrored in a
generated canonical topic registry. Historical Coverage backlinks remain authoritative coverage
evidence but are not retroactively converted into crawl-completion checkpoints.

### Scope

New topic-crawl policy only; no article schema or existing source evidence is changed.
