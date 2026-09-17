---
type: domain-index
domain: Crawl Log
subtype: crawl-log
status: active
last_updated: 2026-09-17
---

# Crawl Log

Canonical daily records of crawl operations. A daily record contains its individual crawl entries,
their positive cascade outcomes, and an evidence-based review; it does not replace canonical article
or entity records.

## YAML registry

| Field | Type | Required |
|---|---|---|
| logDate | date, unique | yes |
| crawlId | string, unique | yes |
| status | enum: active, complete, partial, failed, no-activity | yes |
| entryCount | number | yes |
| cascadedArticleCount | number | yes |
| failureCount | number | yes |
| runReceipts | list of wikilinks or paths | no |

## Daily record structure

```md
## Crawl entries

### YYYY-MM-DDTHH:MM:SS+08:00 — <crawl identifier>

#### Cascaded articles by topic
| Topic | Cascaded articles |
|---|---:|

#### Crawl review

#### Lessons learned

#### Recommendations to improve the topic crawl plan
```

## Operating rules

1. Maintain exactly one fresh canonical note for each Singapore calendar day, whether or not a crawl completed that day.
2. Name the daily note exactly `YYYY-MM-DD Crawl Log.md`, using the Singapore date in reverse-date order; set its `crawlId` to `YYYY-MM-DD-crawl-log`.
3. Update that day's existing note as crawl activity progresses. Do not create multiple daily notes for the same day.
4. Within `## Crawl entries`, order entries by their actual start timestamp in ascending Singapore-time order.
5. For every entry, show `#### Cascaded articles by topic` first. Include only topics with one or more articles successfully cascaded, and show the exact cascaded count for each topic.
6. Follow the results table with `#### Crawl review`, `#### Lessons learned`, and `#### Recommendations to improve the topic crawl plan`. All three must be grounded in the entry's receipt, dispositions, and validation evidence; distinguish cascaded articles from discovered, retrieved, held, duplicate, rejected, or failed items.
7. In the suggestions section, state the observed evidence, the recommended plan change, its expected accuracy benefit, and how it is expected to reduce OpenAI API calls. Prefer deterministic filtering, deduplication, source recovery, and relevance gates before any model call.
8. Treat each documented recommendation as authorised for immediate, autonomous implementation. Apply the scoped crawl-plan change, run its relevant validation, and record the implementation and result in the same daily Crawl Log; do not wait for human approval.
9. Preserve actual start and completion timestamps in Singapore Time, link the relevant immutable run receipt where one exists, and do not infer completion or counts from a planned crawl.
10. Update the append-only `log.md` for every daily-record creation or material state change, then regenerate `catalog.md`.
