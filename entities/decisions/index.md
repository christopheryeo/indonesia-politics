---
type: domain-index
domain: Decisions
subtype: decision
---

# Decisions

Approved changes to vault rules, schemas, and operating behaviour.

## YAML registry

| Field | Type | Required |
|---|---|---|
| decisionId | string | yes |
| displayName | string | yes |
| decidedDate | date | yes |
| status | string | yes |
| owner | string | yes |
| tags | list | no |

## Operating rules

Record and approve a decision before changing a frozen schema or operating rule. Document rationale, impact, and rollback.
