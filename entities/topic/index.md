---
type: domain-index
domain: Topics
subtype: topic
---

# Topics

Recurring political themes, policies, elections, events, and debates used to group coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| displayName | string | yes |
| aliases | list | no |
| category | string | no |
| articleCount | number | yes |
| status | string | yes |
| topicId | string | yes — filename-stable canonical ID |
| tags | list | no |
| lastCrawledAt | ISO 8601 or null | yes |
| crawlStatus | enum | yes — Not started, Queued, In progress, Completed, Failed, Cancelled |
| crawlStatusAt | ISO 8601 or null | yes |

## Operating rules

Prefer stable English analytical themes over one-off headlines and register reviewed Bahasa synonyms
as aliases so bilingual coverage shares one topic. Maintain idempotent Coverage backlinks and regenerate the catalog.

`topics/canonical-topics.yaml` is the machine-readable mirror used by governed crawling. Regenerate
it from the Topic Entity notes with `scripts/sync_canonical_topics.py`; never treat a historical
Coverage entry as evidence that a new governed crawl completed.

Every active Topic Entity must contain exactly one `## Definition`, `## Crawl Prompt`, `## Coverage`,
`## Crawl Log`, and `## Notes` section. The crawl prompt is executable NewsAPI.ai Boolean text;
dates, runtime credentials, and provider controls do not belong in the note. Materialise and refresh
these crawl sections with `scripts/prepare_topic_notes_for_crawl.py` after validating the canonical
registry.
