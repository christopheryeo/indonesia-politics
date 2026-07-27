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
| tags | list | no |

## Operating rules

Prefer stable analytical themes over one-off headlines, maintain idempotent Coverage backlinks, and regenerate the catalog after changes.
