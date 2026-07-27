---
type: domain-index
domain: Issues
subtype: issue
---

# Issues

Reviewed early-warning assessments layered over recurring political-media coverage.

## YAML registry

| Field | Type | Required |
|---|---|---|
| issueId | string | yes |
| displayName | string | yes |
| status | enum: watch, warm, hot, dismissed, closed | yes |
| score | number | yes |
| ramification | string | yes |
| articleCount | number | yes |
| firstFlagged | date | yes |
| lastScored | date | yes |
| tags | list | no |

## Operating rules

The deterministic radar produces candidates; a reviewed assessment creates an issue. Cite evidence, record catalysts and posture, and append status changes to `log.md`.
