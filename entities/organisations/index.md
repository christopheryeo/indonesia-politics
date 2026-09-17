---
type: domain-index
domain: Organisations
subtype: organisation
---

# Organisations

Political parties, public bodies, companies, civil-society groups, and other organisations mentioned in coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| displayName | string | yes |
| aliases | list | no |
| orgType | string | no |
| country | relation: country | no |
| mentionCount | number | yes |
| status | string | yes |
| tags | list | no |

## Operating rules

Use official Indonesian display names for Indonesian bodies and established English names for
international bodies. Preserve stable filenames and register reviewed English and Bahasa forms as
aliases. Maintain idempotent Coverage backlinks and regenerate the catalog after changes.
