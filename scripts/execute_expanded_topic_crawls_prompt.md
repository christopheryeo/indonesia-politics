# Execution Prompt — Expanded Indonesia Politics Topic Crawls

Use this prompt with a coding agent that has access to this repository, public web discovery, and a
runtime-only `NEWSAPI_AI_API_KEY`. It is an execution instruction, not a request to weaken the
governance gates.

```text
Execute the governed Topic Date-Range Crawl procedure in
scripts/topic_crawl_plan.md for the five active topics and scopes defined in
docs/EXPANDED_TOPIC_CRAWL_SCOPES.md.

Scope
- Date range, inclusive: 2026-08-01 to 2026-09-07
- Timezone: Asia/Singapore
- Languages: eng, ind
- Candidate cap: 50 canonical article URLs per topic
- Topics, in this order:
  1. Kejagung-Polri-KPK jurisdiction and case-transfer disputes
  2. Asset recovery and beneficial ownership in corruption and TPPU cases
  3. Danantara governance and state-asset consolidation
  4. Central-bank independence and macroeconomic governance
  5. Civil-military boundaries in domestic governance

Before each crawl
1. Read README.md, scripts/topic_crawl_plan.md,
   scripts/enriched_radar_load_procedure.md, scripts/entity_cascade_procedure.md, and
   scripts/generic_article_ingestion_procedure.md completely.
2. Resolve the supplied topic to exactly one active entity under entities/topic/. Stop that topic
   and report the ambiguity if resolution is not exact.
3. Confirm NEWSAPI_AI_API_KEY is available at runtime without printing, storing, or exposing its
   value. If it is missing, stop before any NewsAPI.ai request and report the blocked status.
4. Create one separate, secret-free run directory and scope manifest per topic below
   runs/2026-09-07/artifacts/topic-crawls/.

For each topic
1. Use every query listed under that topic in docs/EXPANDED_TOPIC_CRAWL_SCOPES.md, plus only
   narrowly justified query variants derived from its registered aliases.
2. Discover public article URLs, canonicalize them, record discovery evidence, and deduplicate.
   Do not treat search pages, snippets, social posts, indexes, or homepages as articles.
3. For each canonical URL, use NewsAPI.ai articleMapper to obtain an article URI. Collapse duplicate
   URIs and record one mapping/recovery/hold disposition for every discovered URL.
4. Retrieve each URI through NewsAPI.ai getArticle with the maximum available article body. Use the
   extraction endpoint only as the documented recovery path for unmapped or partial results.
5. Admit only records that pass identity, selected-date-range, eng/ind language, source-backed
   complete-body, and duplicate gates. Hold all failures with an evidence-backed reason. Do not
   synthesize or repair missing source text.
6. Convert only admitted records through scripts/newsapi_to_inputs.py in preview mode. Review every
   validation result. Write only a clean, frozen batch.
7. Enrich only the new manifest-bound records. Require the configured agreement and completeness
   gates. Route disagreement, uncertainty, invalid vocabulary, or insufficient evidence to holds.
8. Run the month-specific ingest cascade as a dry run first. Resolve only that batch's failures,
   then run the approved manifest live. Regenerate affected catalogs and validate with
   scripts/check_links.py.

Hard boundaries
- Never reveal, log, commit, place in a manifest, or include NEWSAPI_AI_API_KEY in commands,
  requests, outputs, source evidence, or the final report.
- Never overwrite existing input, raw, compiled article, entity, or historical-log content.
- Never write to a database, run Issue Radar, create Issue entities, or broaden the selected topic
  scope without separate explicit authorisation.
- Do not treat a discovery-path zero as proof of zero coverage. A zero-result topic is complete
  only when every configured discovery route succeeded.
- If any systemic credential, endpoint, provenance, or validation failure occurs, stop that topic,
  preserve only secret-free evidence, mark its manifest failed, and continue with the next topic
  only when doing so is safe and independent.

Final report
Return a concise per-topic table with: resolved topic; date range; run-directory link; discovery
queries; discovered URL count; mapped URI count; retrieved, held, duplicate, rejected, normalized,
enriched, and cascaded counts; validation status; elapsed cascade time; and average seconds per
processed article. State clearly whether every topic completed or which are blocked.
```

The procedure is authoritative if this prompt conflicts with any repository convention.
