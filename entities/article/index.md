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
| sourceType | enum: feed, crawl | yes |
| sourceUrl | string | no |
| tone | enum: Factual, Opinionated | no |
| toneSentiment | enum: Positive, Neutral, Negative | no |
| eventType | enum: Facilitated, Unfacilitated | no |
| coverageCount | number | yes |
| tags | list | yes |

## Operating rules

1. Use `scripts/ingest_cascade.py`; do not manually bypass compilation and cascade.
2. Store compiled notes under `entities/article/YYYY-MM/`.
3. Preserve source identifiers and provenance.
4. Use `#sensitive` only when the input explicitly marks restricted material.
5. Rebuild the catalog and run link checks after ingestion.

## Cascade status

**Last counted:** not yet run

| Month | Cascaded | Inputs remaining | Total | % cascaded |
|---|---:|---:|---:|---:|
| **Total** | **0** | **0** | **0** | **0.0%** |

Note: This repository begins with an empty corpus.
