---
type: procedure
name: generic-article-ingestion
status: active
last_updated: 2026-08-03
---

# Generic Article Ingestion Procedure

Use this procedure whenever one or more new Markdown articles appear under
`inputs/articles/`. It is independent of article count and publication date. Markdown entity notes
remain the source of truth; database tables, catalogs, dashboards, query indexes, bundles, and run
receipts are derived artifacts.

This procedure coordinates the more specific enrichment, cascade, database-load, and Issue Radar
procedures. Follow those procedures whenever this document delegates to them.

## Goal invocation — use only when a Goal is invoked

<!-- GOAL-ONLY SECTION: Use this section only after the operator explicitly invokes a Goal. -->
<!-- Do not treat this section as authorization to create a Goal, write to a database, change a
     frozen schema, or broaden an ordinary manual or conversational request. -->

When a Goal has been explicitly invoked, use this reusable Goal prompt:

> Execute `scripts/generic_article_ingestion_procedure.md` against a frozen snapshot of the current
> Markdown files under `inputs/articles/`, excluding `.gitkeep`. Follow every pre-ingestion and
> post-ingestion quality gate, success condition, end condition, and breakout condition in the
> procedure. Process batches in publication-date order with no more than 10 articles per batch.
> Preserve raw provenance and source-language prose, do not change frozen schemas, and do not write
> to any database unless the operator explicitly authorizes the exact target for this Goal. Continue
> until every snapshot file is cascaded, excluded as a proven duplicate, or placed on a documented
> hold. Defer and report files arriving after the snapshot. Finish by reporting English and Bahasa
> counts, held and excluded files, Issue Radar results, total elapsed time, average time per
> successfully processed article, and numerical Wiki/database shared-field parity.

The Goal inherits every rule in this procedure. The prompt does not override approval gates,
restricted-data handling, schema freezes, transactional rollback requirements, or breakout
conditions.

<!-- END GOAL-ONLY SECTION -->

## Objectives

1. Convert every eligible input into a provenance-preserving Wiki article.
2. Enrich each article sufficiently for entity cascade and Issue Radar.
3. Cascade articles and reciprocal entity relationships without duplicates.
4. Synchronize the validated Wiki corpus with the explicitly approved database target.
5. Finish with measurable Wiki/database reconciliation and a clear account of held files.

## 1. Establish the batch snapshot

1. Read `README.md`, this procedure, and the applicable enrichment, cascade, database-load, and
   Issue Radar procedures.
2. Enumerate every Markdown article under `inputs/articles/`, excluding `.gitkeep`.
3. Record each file's path, hash, source ID, publication date, and language.
4. Freeze this list as the run snapshot. Files appearing after the snapshot belong to the next run.
5. Sort by publication date, then source ID.
6. Process no more than 10 articles per batch.

## 2. Run pre-ingestion quality checks

Before changing anything:

1. Validate the existing Wiki for YAML, registered fields, links, aliases, and malformed labels.
2. Reconcile catalogs, entity counts, reciprocal backlinks, and audit-ledger entry counts.
3. Count existing Wiki and database articles.
4. Check every incoming source ID against existing Wiki articles, database vendor article IDs,
   other snapshot files, and declared duplicate lists.
5. Confirm that raw source evidence is preserved under `raw/`.
6. Confirm the database name and available schema with read-only queries.
7. Record baseline counts for post-run comparison.

## 3. Check input readiness

Each article must have:

- a unique source ID;
- an article title;
- a full, non-placeholder body;
- a publication date;
- a source URL;
- `eng` or `ind` language;
- a publisher name and domain;
- duplicate status; and
- preserved raw provenance.

Place incomplete or ambiguous articles on review hold. Do not cascade them.

## 4. Enrich the articles

Follow `scripts/enriched_radar_load_procedure.md` and populate:

1. canonical issue tags;
2. a reusable analytical topic;
3. an institutional category;
4. tone;
5. tone sentiment;
6. event type;
7. canonical publisher name;
8. publisher country;
9. publisher-location validation; and
10. outlet relation, country relation, and coverage count.

Publisher country means the publisher's home country, not the article dateline. Keep reusable
analytical topics and tags in canonical English for both English and Bahasa coverage. Preserve
source prose in its original language. Place low-confidence, conflicting, or unsupported values on
review hold; never guess.

## 5. Review and approve enrichment

1. Review every hold and disagreement.
2. Record the approved values, reviewer, and approval timestamp.
3. Require explicit approval for language, publisher location, and every analytical field.
4. Rebuild the approved working set.
5. Verify that every approved article is cascade-ready.
6. Exclude declared duplicates while preserving their raw evidence.

## 6. Prepare downstream bundles

Before cascade moves the inputs:

1. Create immutable database bundles from the approved working set.
2. Include article, coverage, and tag records.
3. Preserve external source IDs as database vendor IDs.
4. Verify bundle hashes, counts, and relationships.
5. Require zero unresolved review or quarantine records.

## 7. Compile and cascade into the Wiki

Follow `scripts/entity_cascade_procedure.md` and:

1. route loose articles into their publication-month folders;
2. compile articles into `entities/article/YYYY-MM/`;
3. preserve source text exactly;
4. resolve entities against canonical filenames and aliases;
5. create only unambiguous new entities;
6. add reciprocal article backlinks to entity `Coverage` sections;
7. reconcile mention and article counts;
8. use canonical piped Obsidian links;
9. append audit-log entries without rewriting history; and
10. regenerate every affected catalog.

## 8. Run post-cascade Wiki checks

Require all of the following:

- article-quality errors: 0;
- article-quality warnings: 0;
- broken or malformed links: 0;
- invalid YAML records: 0;
- duplicate source IDs: 0;
- missing reciprocal backlinks: 0;
- entity count mismatches: 0;
- catalog mismatches: 0;
- audit-ledger count mismatches: 0;
- source-text provenance mismatches: 0; and
- approved-language mismatches: 0.

Do not proceed to database loading when a blocking Wiki check fails.

## 9. Load the database

Database writes require explicit authorization for each run.

1. Confirm the exact database and table prefix.
2. Load isolated staging tables and require staging status `validated`.
3. Build canonical-shaped candidates and require transformation status `validated`.
4. Load canonical tables transactionally.
5. Roll back the entire batch when any count, duplicate, relationship, or integrity gate fails.
6. Never modify a frozen database schema without an approved system-rule decision.

## 10. Reconcile Wiki and database

Prove synchronization numerically:

- Wiki IDs equal database vendor IDs;
- Wiki-only IDs: 0;
- database-only IDs: 0;
- titles and source-text hashes match;
- publication dates, topics, tone, sentiment, and event types match;
- issue-tag sets match;
- coverage URLs, countries, and publisher names match;
- outlet metadata matches;
- duplicate vendor groups: 0;
- orphaned coverage and tag records: 0;
- pending quarantine records: 0; and
- shared-field parity: 100%.

Document fields intentionally stored in only one system as asymmetric and exclude them explicitly
from the parity denominator.

## 11. Run Issue Radar

1. Run Issue Radar read-only against the synchronized database.
2. Report the number of articles evaluated and flags produced.
3. Process flags according to `scripts/issue_radar_procedure.md`.
4. Do not invent issues when the deterministic radar reports none.

## 12. Final reporting

Report:

- snapshot size;
- articles processed, cascaded, and loaded;
- duplicates excluded;
- held articles and the reason for each hold;
- English and Bahasa counts;
- Wiki/database parity;
- Issue Radar result;
- files arriving after the snapshot;
- total elapsed time; and
- average time per successfully processed article.

Use Singapore Time (SGT, UTC+8) for operator timestamps.

## Success and end conditions

The run succeeds only when:

1. every snapshot file is cascaded, excluded as a proven duplicate, or placed on a documented hold;
2. every approved article passes the Wiki quality gates;
3. all affected catalogs, ledgers, backlinks, and counts reconcile;
4. every authorized database load gate is validated;
5. Wiki/database parity is 100% for shared fields;
6. Issue Radar completes successfully; and
7. no snapshot file remains unexplained.

The run ends after final reporting. Post-snapshot arrivals are reported and deferred to the next run.

## Breakout conditions

### Hold one article and continue

- missing or unsupported language;
- missing or placeholder body;
- missing source URL or publisher;
- publisher-location uncertainty;
- conflicting enrichment;
- possible duplicate requiring judgment;
- ambiguous entity or alias resolution; or
- explicitly sensitive material requiring review.

### Stop the entire batch

- existing Wiki structural failure;
- missing raw provenance;
- required frozen-schema modification;
- unconfirmed database target or missing database-write authorization;
- failed staging, transformation, or load validation;
- unreconciled counts or hashes;
- partial transactional application;
- Wiki/database shared-field parity below 100%; or
- a required destructive or ambiguous repair.

Files arriving after the frozen snapshot are not failures. They form the next run's batch.
