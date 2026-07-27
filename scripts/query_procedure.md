---
type: procedure
name: entity-query
status: active
last_updated: 2026-07-27
---

# Query Procedure

Answer natural-language questions by navigating catalogs and compiled entity summaries before reading source articles.

## 0. Check reusable answers

1. Search the query cache when cache reads are enabled.
2. Reuse only a relevant, fresh answer.
3. Treat time-sensitive answers or answers whose underlying entity counts changed as stale.

## 1. Resolve

1. Extract every named or implied person, organisation, appointment, place, country, outlet, topic, or issue.
2. Resolve candidates against domain catalogs and aliases.
3. Do not scan the raw corpus as a substitute for entity resolution.
4. Return an unresolved result when identity remains ambiguous.

## 2. Read bounded context

1. Read the resolved entity's Summary, Definition, Office, Holders, and Related Entities sections as applicable.
2. Rank Coverage evidence and read only the most relevant source notes.
3. Follow related entities only when the question requires broader context.
4. Keep deterministic context within the configured size caps.

## 3. Answer

1. Use only evidence actually read from the vault.
2. Do not add live-web or model-background facts.
3. Answer directly without exposing internal catalog, cache, or query mechanics.
4. Put source identifiers and resolved entities in their structured fields.
5. Set `sensitive: true` only when the answer relies on material explicitly marked restricted.

## 4. File

1. When cache writes are enabled, file a new answer under `entities/search/` or register reuse.
2. Append an audit entry and regenerate the search catalog.
3. Never overwrite an earlier answer or log entry.

An empty vault must return empty resolution results or a clear unresolved/no-matching-data response without failing.
