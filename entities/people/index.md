---
type: domain-index
domain: People
subtype: person
---

# People

Named individuals referenced by monitored coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| displayName | string | yes |
| aliases | list | no |
| role | string | no |
| affiliation | relation: organisations | no |
| country | relation: country | no |
| mentionCount | number | yes |
| status | string | yes |
| tags | list | no |

## Operating rules

Disambiguate people before creation, preserve aliases and dated roles, maintain Coverage backlinks, and regenerate the catalog after changes.
