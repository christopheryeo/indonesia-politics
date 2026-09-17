---
type: domain-log
domain: Decisions
entry_count: 3
---

# Decision Audit Log

Append new entries below. Never rewrite prior entries.

- 2026-07-31T20:47:32+08:00 | decision: [[validate-publisher-location-during-enrichment|Validate Publisher Location During Enrichment]] | action: approved | reasoning: require explicit publisher-country validation before automatic enrichment application or Issue Radar staging.
- 2026-07-31T20:54:49+08:00 | decision: [[enrich-reusable-topic-and-tone-sentiment|Enrich Reusable Topic and Tone Sentiment]] | action: approved | reasoning: confidence-gate reusable topics and tone sentiment and preserve NewsAPI JSON before Markdown derivation.
- 2026-08-03T12:00:00+08:00 | decision: [[support-english-and-bahasa-indonesia|Support English and Bahasa Indonesia]] | action: approved | reasoning: preserve bilingual source evidence, require forward-only language metadata, resolve both languages through canonical aliases, and answer queries in the question language.
