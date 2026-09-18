---
type: domain-index
domain: Articles
subtype: article
---

# Articles

Compiled media notes that have completed the entity cascade. Raw inputs remain under `Inputs/articles/` until compilation succeeds.

## YAML registry

| Field | Type | Required |
|---|---|---|
| sourceId | string | yes |
| publishedDate | datetime | yes |
| language | enum: eng, ind, und | no (legacy); eng or ind required for new intake |
| sourceType | enum: feed, crawl | yes |
| sourceUrl | string | no |
| tone | enum: Factual, Opinionated | yes |
| toneSentiment | enum: Positive, Neutral, Negative | yes |
| eventType | enum: Facilitated, Unfacilitated | yes |
| coverageCount | number | yes |
| tags | list | yes |

## Operating rules

1. Use `scripts/ingest_cascade.py`; do not manually bypass compilation and cascade.
2. Store compiled notes under `entities/article/YYYY-MM/`.
3. Preserve source identifiers and provenance.
4. Use `#sensitive` only when the input explicitly marks restricted material.
5. Rebuild the catalog and run link checks after ingestion.
6. Preserve source-language prose. New intake may use `und` only as a review hold and must be reviewed to `eng` or `ind` before cascade.
7. `tone`, `toneSentiment`, and `eventType` are enrichment fields that `scripts/ingest_cascade.py` does not populate. Crawl inputs arriving with empty values must be enriched before or immediately after cascade — an empty string fails `scripts/article_quality.py` as an invalid enum. Until 2026-08-13 this table marked the three optional while the validator required them; the validator is authoritative and the table now matches it.

## Cascade status

**Last counted:** 2026-09-18 (72-article full-folder batch from `Inputs/articles/2026-09/`; see note below)

| Month | Cascaded | Inputs remaining | Total | % cascaded |
|---|---:|---:|---:|---:|
| 2026-05 | 1 | 0 | 1 | 100.0% |
| 2026-06 | 5 | 0 | 5 | 100.0% |
| 2026-07 | 205 | 0 | 205 | 100.0% |
| 2026-08 | 231 | 0 | 231 | 100.0% |
| 2026-09 | 1,206 | 0 | 1,206 | 100.0% |
| **Total** | **1,648** | **0** | **1,648** | **100.0%** |

Note: Counts are recomputed from `Inputs/articles/` and `entities/article/` on every cascade run, not accreted from batch receipts. Last run 2026-09-18: 72 file(s) from `Inputs/articles/2026-09/`; all input folders are empty. Per-batch history is in `log.md`.
