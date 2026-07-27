# Query Latency Optimisation

The query path uses a reversible deterministic fast path before the legacy multi-turn model loop.

## Design

1. Resolve entities from catalogs.
2. Classify supported query shapes.
3. Build a bounded evidence packet from entity summaries, relationships, appointments, and ranked Coverage evidence.
4. Use a single low-reasoning model request for supported, unambiguous questions.
5. Fall back to the legacy procedure-driven loop for ambiguity, unsupported shapes, cache reads, or disabled fast-path configuration.
6. Preserve cache-write behaviour and filter returned sources and entities to the supplied evidence.

## Controls

- `QUERY_FAST_PATH=true|false`
- `QUERY_CACHE_READ=true|false`
- `QUERY_CACHE_WRITE=true|false`
- Per-request flags take precedence over environment defaults.

## Acceptance

Synthetic tests must prove exact resolution, bounded context, one-request execution, safe source filtering, fallback routing, cache compatibility, empty-vault behaviour, and the generic `sensitive` result field.
