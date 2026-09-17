---
type: procedure
name: enriched-radar-load
status: active
last_updated: 2026-08-03
---

# Enriched Radar Input Load Procedure

This procedure moves approved article enrichment into the shared article database safely. UAT is
always used first. The bridge never writes production. Articles may arrive through either source
route, but all downstream processing begins from `Inputs/articles/`.

## 0. Land both source routes in Inputs

- Feed export: preserve the delivery under `raw/`, then run `scripts/raw_feed_to_inputs.py` to derive
  `Inputs/articles/YYYY-MM/` notes.
- NewsAPI crawler JSON: preview with `scripts/newsapi_to_inputs.py <response.json>`, then rerun with
  `--write`. The bridge preserves the source response under `raw/newsapi/` before deriving one
  Markdown note per article in its publication-month folder.
- Other crawler notes: write the crawler note into `Inputs/articles/`. If it is loose at the root,
  preview and then run `scripts/route_input_articles.py --write` to place it in its publication-month
  folder.

Never enrich, stage, compile, or cascade a file directly from `raw/`.

Normalize source language to `eng` or `ind`. A missing, conflicting, unsupported, or `und` value is
a review hold and cannot proceed to automatic enrichment or Wiki cascade.

## 1. Enrich

Run `scripts/enrich_radar_inputs.py` to create assessment JSON for the eight required enrichment
fields: issue tags, outlet name, publisher country, institutional category, reusable topic, tone,
tone sentiment, and event type. Apply only the automatically
accepted fields to the loose Markdown articles. Publisher country must have
`outletLocationValidation.status: validated`; disagreement, missing evidence, low confidence, or a
conflict with the supplied crawler country places the article in the review queue. Publisher
location means the outlet's home country, never the article dateline or event location.
Evidence excerpts remain verbatim in the source language. Reusable analytical topics and tags remain
canonical English values so English and Bahasa coverage cluster together.

## 2. Prepare the UAT bundle

```bash
python3 scripts/stage_enriched_radar_inputs.py prepare \
  --input-dir Inputs/articles \
  --assessment runs/YYYY-MM-DD/artifacts/radar-input-enrichment.json \
  --output-dir runs/YYYY-MM-DD/artifacts/enriched-radar-uat-bundle
```

Repeat `--assessment` when a retry artifact exists. Enrichment and staging include loose files and
month subfolders by default. Use `--loose-only` only for an explicitly bounded loose-file batch.

## 3. Review holds

Open `review_queue.csv`. The bridge holds any article with a missing field, disagreement,
low confidence, or model review request.
Language holds must be explicitly reviewed to `eng` or `ind`; approval cannot leave `und`.

For an approved hold, copy `review_approval_template.json`, set `approved: true`, record
`approvedBy` and `approvedAt`, and confirm all nine approval fields, including `language`. Re-run `prepare` with
`--approvals <reviewed-file.json>` into a new empty output directory. Never edit a generated bundle
in place.

## 4. Verify the bundle

```bash
python3 scripts/stage_enriched_radar_inputs.py verify-bundle \
  --bundle-dir runs/YYYY-MM-DD/artifacts/enriched-radar-uat-bundle
```

Require `status: passed`.

## 5. Load isolated staging

Using the approved UAT MySQL account, run the bundle's `phase3_load.sql`, followed by
`phase3_validate.sql`. Require the batch status `validated`.

## 6. Build canonical-shaped candidates

Run `phase4_transform.sql`, followed by `phase4_validate.sql`. Require transform status
`validated`. External article IDs remain in `vendor_article_id`; new positive UAT article IDs are
allocated above the current UAT maximum.

## 7. Load canonical UAT

Run `phase5_load_uat.sql`. It inserts articles, online coverage, and issue tags in one transaction.
Any count, relationship, duplicate-key, or integrity failure rolls the transaction back.

## 8. Run the radar

Run `scripts/issue_radar.py --source uat` with the approved read-only credentials. Follow
`scripts/issue_radar_procedure.md` for AI/analyst clustering, ramification, filing, and delivery.

Production promotion is a separate explicitly approved operation after UAT acceptance. This bridge
contains no production-writing SQL.
Language is retained in Markdown and staging provenance only; this procedure does not add a canonical
MySQL language column.
