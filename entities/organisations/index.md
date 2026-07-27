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

Use canonical names, preserve aliases, maintain idempotent Coverage backlinks, and regenerate the catalog after changes.
