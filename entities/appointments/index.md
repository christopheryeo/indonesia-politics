---
type: domain-index
domain: Appointments
subtype: appointment
---

# Appointments

Stable political offices with dated holders.

## YAML registry

| Field | Type | Required |
|---|---|---|
| appointmentId | string | yes |
| displayName | string | yes |
| aliases | list | no |
| currentHolder | relation: people | no |
| status | string | yes |
| tags | list | no |

## Operating rules

Create or update appointments only from cited authoritative sources. Record holder changes as dated entries and append every change to `log.md`.
