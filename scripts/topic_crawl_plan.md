---
type: procedure
name: topic-date-range-crawl
status: ready
created: 2026-09-07
owner: Indonesia Politics Wiki
---

# Indonesia Politics Topic Date-Range Crawl

## Purpose

Run a governed NewsAPI.ai crawl for one existing Indonesia Politics Topic Entity over one inclusive
publication-date range. The procedure discovers and deduplicates candidate URLs, maps each URL to
a NewsAPI.ai article URI, retrieves complete source-backed article text, stages schema-valid raw
notes, and moves only reviewed, valid notes through the existing enrichment and Wiki cascade.

The Markdown corpus is authoritative. `runs/` contains operational evidence; it is not a source of
truth for article content. This procedure neither writes to a database nor creates an Issue Radar
assessment unless the invoking instruction explicitly authorizes that downstream work. For a
restartable multi-topic run, also use `scripts/topic_crawl_goal_contract.md` and initialise its
append-only ledger with `scripts/topic_crawl_goal_runner.py`.

## Invocation

Provide:

1. `topic` — an exact existing file, filename, display name, alias, or unambiguous wikilink under
   `entities/topic/`;
2. `dateStart` — inclusive `YYYY-MM-DD`; and
3. `dateEnd` — inclusive `YYYY-MM-DD`.

Optional inputs are `timezone` (default `Asia/Singapore`), `maxCandidates`, `languages`
(default `eng, ind`), named outlet constraints, and `runLabel`.

Use:

> Execute `scripts/topic_crawl_plan.md` with topic `<TOPIC>`, dateStart `<YYYY-MM-DD>`, and
> dateEnd `<YYYY-MM-DD>`. Follow the procedure through completion.

Stop before retrieval if the topic is ambiguous or inactive, the dates are invalid or reversed, or
`NEWSAPI_AI_API_KEY` is absent. Never place the key in a command transcript, note, manifest,
receipt, log, request capture, or source control.

## Governing rules

- Read `README.md`, `scripts/enriched_radar_load_procedure.md`,
  `scripts/entity_cascade_procedure.md`, and `scripts/generic_article_ingestion_procedure.md`
  before operating their stages.
- Preserve source prose in its original English or Bahasa Indonesia. Analytical topics, tags, and
  system headings remain canonical English.
- Do not modify `raw/`, frozen schemas, or historical logs. Never overwrite an existing input or
  compiled article note.
- Treat discovery, URL-to-URI mapping, retrieval, admission, enrichment, and cascade as separate
  gates. A zero from one discovery path is not proof of zero coverage.
- Time the compile-and-cascade stage end to end and report total elapsed time, processed count, and
  average seconds per processed article.

## 1. Resolve and freeze scope

1. Resolve `topic` to exactly one active Topic Entity under `entities/topic/` and read its
   `displayName` and aliases. Do not substitute a broader or similarly named topic.
2. Create `runs/YYYY-MM-DD/artifacts/topic-crawls/<topic-slug>-<dateStart>-<dateEnd>-<suffix>/`.
3. Save a secret-free scope manifest containing the resolved topic path, display name, aliases,
   dates, timezone, language and outlet constraints, candidate cap, operator timestamp, and a
   baseline inventory of `Inputs/articles/` and `entities/article/`.
4. Record status `in_progress` in that manifest and set the resolved Topic Entity to `In progress`
   with `scripts/update_topic_crawl_status.py --topic <id> --status Queued`, followed by the same
   command with `--status 'In progress'`.
   Topic files carry the canonical `lastCrawledAt`, `crawlStatus`, and `crawlStatusAt` fields;
   historical coverage alone must never be treated as a successful crawl checkpoint.

## 2. Discover candidate article URLs

1. Search public article results using the topic display name, meaningful aliases, Indonesia
   politics context, date range, requested languages, and any outlet constraints. Use multiple
   queries rather than a single literal topic label.
2. For each hit, record the provider, exact query, result rank, discovered URL, apparent title,
   publisher, apparent publication time, and discovery time in a secret-free discovery manifest.
3. Follow public article URLs only. Search pages, topic indexes, category pages, homepages,
   snippets, social posts without an underlying article, and non-article documents are discovery
   evidence only.
4. Resolve redirects and strip non-identity tracking parameters, retaining both discovered and
   canonical URLs. Deduplicate canonical URLs before NewsAPI.ai calls. Continue until available
   result pages yield no new in-range URLs or `maxCandidates` is reached.

## 3. Map canonical URLs to NewsAPI.ai article URIs

For every unique canonical URL, make one programmatic `POST` to
`https://eventregistry.org/api/v1/articleMapper` with:

```json
{
  "articleUrl": "<canonical article URL>",
  "apiKey": "<runtime NEWSAPI_AI_API_KEY>"
}
```

Validate HTTP status, content type, and response shape before reading an article URI. Record the
canonical URL, attempt time, status, disposition, and returned URI in the mapping manifest, but
never the key or request headers. Deduplicate returned article URIs: multiple URLs mapping to one
URI represent one candidate article.

An unmapped URL may be checked with the direct extraction endpoint in section 5 to diagnose
indexing or canonicalization. It must be held or rejected unless a source-backed, identity-checked
body is actually recovered.

## 4. Retrieve each mapped article

For every unique mapped URI, make a programmatic `POST` to
`https://eventregistry.org/api/v1/article/getArticle` with:

```json
{
  "action": "getArticle",
  "articleUri": "<NewsAPI.ai article URI>",
  "infoArticleBodyLen": -1,
  "resultType": "info",
  "apiKey": "<runtime NEWSAPI_AI_API_KEY>"
}
```

`infoArticleBodyLen: -1` requests the maximum body available from NewsAPI.ai; it does not itself
prove complete publisher text. For each response, record the URI, URL, returned title, outlet,
publication timestamp, language, body character/word/paragraph counts, SHA-256 body hash, endpoint,
response metadata, and gate outcomes in the retrieval manifest. Do not persist raw credentialed
requests or headers.

## 5. Admit, recover, or hold

Admit an article only when all of the following are evidenced:

1. returned URL, title, source, and publication event match the discovered article;
2. the source publication date converted to the selected timezone is within the inclusive range;
3. language resolves to `eng` or `ind`;
4. the body is non-empty, coherent, and plausibly complete rather than abruptly truncated; and
5. it is absent from current inputs and compiled articles by article ID, canonical URL, NewsAPI URI,
   source identity, and body hash where available.

For a missing, partial, or unmapped result, call
`POST https://analytics.eventregistry.org/api/v1/extractArticleInfo` with the canonical `url` and
the runtime key for comparison or recovery. If it still cannot yield a complete source-backed body,
hold the candidate with the evidence-backed reason. Never synthesize missing text or send a partial
body to enrichment or cascade.

## 5A. Low-cost source-body relevance gate

Before creating raw notes or invoking the two-pass enrichment model, classify the admitted
source-backed records against the resolved Topic Entity. This is a triage gate, not article
classification: it costs one low-reasoning OpenAI request per batch of up to ten candidates and
uses at most 5,000 source-body characters per candidate.

```bash
python3 scripts/gate_topic_crawl_relevance.py \
  --topic <canonical-topic-id> \
  --input <run-dir>/admitted-newsapi-response.json \
  --output <run-dir>/relevance-gate.json
```

Only `relevant` candidates may continue to normalisation. Record `off-topic` and `held`
candidates as terminal dispositions in the run ledger, including the gate reason and confidence.
Do not retry, re-fetch, or send either group to full enrichment unless new source evidence changes
its disposition. A provider record with an empty or inadequate body remains held before this gate.

## 6. Normalize accepted results

1. Write a secret-free NewsAPI response envelope containing only admitted, source-backed records to
   the run directory, or construct equivalent records in memory.
2. Use the existing bridge in preview mode first:

   ```bash
   python3 scripts/newsapi_to_inputs.py <admitted-newsapi-response.json>
   ```

3. Review every reported validation error. A record with a missing publisher country, unsupported
   language, inadequate body, missing URI/title/URL/source, or duplicate collision is held rather
   than forced through.
4. On a clean, frozen batch, write with:

   ```bash
   python3 scripts/newsapi_to_inputs.py <admitted-newsapi-response.json> --write
   ```

   The bridge preserves its source response under `raw/newsapi/` and writes raw notes to
   `Inputs/articles/YYYY-MM/`. Raw notes retain deterministic crawl fields only; analytical and
   judgment-heavy fields stay blank until review.
5. Save a newline-delimited, repo-relative normalized-file manifest (for example,
   `Inputs/articles/2026-09/<article>.md`) containing only the relevance-approved notes, and
   update each candidate's terminal or next-stage disposition. Freeze this manifest before any
   enrichment request; never expand it in place.

## 7. Enrich and validate the frozen batch

1. Run `scripts/enrich_radar_inputs.py` against only the frozen normalized-file manifest. Use
   `--no-fetch` because the relevance gate has already admitted complete, source-backed provider
   text; allow a publisher-page fetch only when that evidence is specifically found deficient and
   the candidate is moved back to the recovery gate.

   ```bash
   python3 scripts/enrich_radar_inputs.py \
     --manifest <run-dir>/normalized-inputs.manifest \
     --output <run-dir>/enrichment.json \
     --no-fetch
   ```

2. Require the configured independent classification agreement and confidence threshold for topic,
   tags, institutional category, tone, sentiment, event type, outlet, and publisher country. The
   relevance-approved Topic Entity is the governing scope; a disagreeing topic label is review or
   hold evidence, not a reason to broaden the crawl.
3. First apply only fields that independently agree and clear the threshold:

   ```bash
   python3 scripts/enrich_radar_inputs.py \
     --apply-assessment <run-dir>/enrichment.json
   ```

   Then resolve only the conservative non-topic defaults permitted by
   `schemas/topic_crawl_resolution_policy.yaml`, producing a secret-free policy receipt. A missing
   or disagreeing topic label remains held for attributed review; do not make a second model call
   merely to break a disagreement:

   ```bash
   python3 scripts/apply_topic_crawl_policy.py \
     --assessment <run-dir>/enrichment.json \
     --output <run-dir>/policy-resolution.json
   ```
4. Run the shared completeness gate against that same immutable manifest:

   ```bash
   python3 scripts/enrich_radar_inputs.py \
     --manifest <month-manifest-path> \
     --check-complete
   ```

## 8. Compile and cascade

For each affected publication month:

1. Run `scripts/ingest_cascade.py --month <YYYY-MM> --manifest <month-manifest-path> --dry-run`.
2. Resolve every preview failure or hold that article; do not broaden the batch.
3. Run the same command without `--dry-run` for the approved manifest.
4. Confirm successful notes moved to `entities/article/YYYY-MM/`, backlinks and coverage were
   updated, affected catalogs and logs were generated, and all required validation passed.
5. Do not load a database, run Issue Radar, or create Issue entities unless explicitly authorized.

## 9. Reconcile and close

1. Reconcile discovery, mapping, retrieval, normalization, enrichment, and cascade manifests so
   every discovered candidate has exactly one terminal disposition: cascaded, duplicate, off-topic,
   rejected, or held with a reason.
2. Mark the scope manifest `complete` only when all configured discovery routes and required stages
   succeeded. Mark it `failed` for systemic credential, endpoint, provenance, or validation failure;
   retain recoverable secret-free evidence.
3. A zero-result run can be `complete` only when all configured discovery paths ran successfully.
4. After a successful reconciliation, transition the Topic Entity to `Completed` with the actual
   completion instant; failure and cancellation are also recorded through
   `scripts/update_topic_crawl_status.py`.

## 10. Write the daily Crawl Log (mandatory)

At the end of every crawl, including zero-result, partial, failed, and completed outcomes, create
or update the Singapore-date daily note in `entities/crawl-log/` named `YYYY-MM-DD Crawl Log.md`.
Add the crawl as one entry in ascending actual-start-time order. The entry must contain:

1. `#### Cascaded articles by topic` — only topics with one or more successfully cascaded articles,
   with each exact cascaded count.
2. `#### Crawl review` — outcome, dispositions, validation state, and receipt evidence.
3. `#### Lessons learned` — evidence-based operational learnings.
4. `#### Recommendations to improve the topic crawl plan` — evidence, recommended change, expected
   accuracy benefit, and expected OpenAI API-call reduction.

Record non-cascaded outcomes in the review, not the topic table. Each recorded recommendation is
authorised for immediate implementation: apply the scoped code or crawl-plan change, validate it,
and record the result in the same Crawl Log entry. Then update the daily note's aggregate
frontmatter, append the domain audit `log.md` entry, and regenerate
`entities/crawl-log/catalog.md`.

## Acceptance checklist

- [ ] One active Topic Entity and valid inclusive dates were resolved.
- [ ] `NEWSAPI_AI_API_KEY` was runtime-only and never persisted.
- [ ] Candidate URLs were canonicalized and deduplicated.
- [ ] Every URL has a mapping/recovery/hold disposition, and duplicate URIs were collapsed.
- [ ] Every admitted article passed identity, date, language, complete-body, provenance, and
      duplicate gates.
- [ ] Relevance-approved candidates passed the batched low-cost source-body gate; off-topic and
      held candidates were terminally ledgered without full enrichment.
- [ ] New source evidence was preserved only through the bridge under `raw/newsapi/`.
- [ ] Each raw note passed reviewed enrichment and completeness validation.
- [ ] Each cascaded month passed dry-run and live cascade validation.
- [ ] Every candidate has one final disposition, with a timed per-month cascade result.
- [ ] The daily Crawl Log records the completed crawl, its positive cascaded-topic counts, review,
      lessons, and autonomous improvement recommendations.
- [ ] For Goal Mode runs, the append-only ledger and `goal-receipt.json` pass
      `scripts/topic_crawl_goal_runner.py reconcile` before closure.

## Final report

Report the resolved topic, date range, timezone, run directory, discovery queries and counts,
candidate and URI counts, retrieval/recovery outcomes, held/duplicate/rejected/normalized/enriched/
cascaded totals, validation results, per-month elapsed and average cascade time, and links to the
secret-free manifests and affected notes.
