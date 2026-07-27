---
type: domain-index
domain: Search
subtype: query
---

# Search

Reusable answers produced by the query workflow.

## YAML registry

| Field | Type | Required |
|---|---|---|
| queryId | string | yes |
| query | string | yes |
| askedDate | datetime | yes |
| status | enum: answered, unresolved | yes |
| reuseCount | number | yes |
| timeSensitive | boolean | yes |
| procedureVersion | string | yes |
| tags | list | no |

## Operating rules

File answers through `scripts/query.py`, preserve cited sources and resolved entities, and do not reuse stale time-sensitive answers.
