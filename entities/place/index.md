---
type: domain-index
domain: Places
subtype: place
---

# Places

Specific locations referenced by monitored coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| displayName | string | yes |
| aliases | list | no |
| placeType | string | no |
| country | relation: country | no |
| mentionCount | number | yes |
| status | string | yes |
| tags | list | no |

## Operating rules

Use the most specific official Indonesian name for Indonesian places, keep stable existing filenames,
and register established English forms as aliases. Maintain Coverage backlinks and regenerate the catalog.
