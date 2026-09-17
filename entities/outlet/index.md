---
type: domain-index
domain: Outlets
subtype: outlet
---

# Outlets

Publishers and media channels responsible for monitored coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| outletId | string | yes |
| displayName | string | yes |
| aliases | list | no |
| country | string | no |
| mediaCategory | string | no |
| channels | list | no |
| articleCount | number | yes |

## Operating rules

Create outlets through cascade using the publisher's official name, register reviewed English/Bahasa
variants as aliases, keep article counts and Coverage backlinks idempotent, and follow `schemas/outlet.yaml`.
