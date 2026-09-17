---
type: domain-index
domain: Countries
subtype: country
---

# Countries

Countries referenced by monitored coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| displayName | string | yes |
| aliases | list | no |
| mentionCount | number | yes |
| status | string | yes |
| tags | list | no |

## Operating rules

Create countries through cascade, use one stable country note for English and Bahasa exonyms, keep
Coverage backlinks idempotent, and regenerate the catalog after changes.
