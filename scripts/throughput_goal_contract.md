---
type: goal-contract
name: throughput-goal-contract
status: active
owner: Christopher (chris@sentient.io)
created: 2026-07-24
applies_to: [Inputs/articles, entities/article, UAT database loads]
---

# Throughput Goal Contract — Unprocessed Article Loading & Cascade

This contract governs any run (interactive, `/goal`, or scheduled) whose purpose is to
process unprocessed articles from `Inputs/articles/` into both stores — the UAT database
and the wiki — at maximum throughput **without degrading wiki quality**. Quality is the
constraint; throughput is the variable. A throughput gain that costs a single gate
failure is a net miss.

This contract adds no new procedures. Execution follows the existing documents:
`enriched_radar_load_procedure.md` (enrich → stage → UAT load) and
`entity_cascade_procedure.md` (compile → cascade). Where this contract and those
procedures appear to conflict, the procedures win and the conflict is reported.

## 1. Objective

Maximise end-to-end throughput — **articles per second**, measured from the start of a
batch's enrichment to the completion of its cascade and gates — while every quality gate
in §5 passes.

## 2. Baseline (measured 2026-07-24)

- Backlog: 115 loose crawler articles under `Inputs/articles/` (root), plus 1 stray file
  in `Inputs/articles/N/` (see §7.2).
- Cascade-stage throughput: ~0.19–0.22 sec/article (receipts of 2026-07-18,
  batches of 1,294–1,572).
- End-to-end throughput including enrichment: **unmeasured** — the first run under this
  contract establishes it.
- Compiled corpus at baseline: 16,840 articles.

## 3. Unit of work: the 10-article batch

Work proceeds in batches of **10 articles** (final batch may be smaller). No batch
starts until the previous batch's gates (§5.1) have passed. Batch order: oldest
publication date first.

Per batch, in order:

1. **Route** — `route_input_articles.py --write` places loose files into their
   `YYYY-MM` folders.
2. **Enrich** — fill the six radar fields per the current enrichment design
   (lookup-first outlet resolution; single confidence-gated model pass for tone,
   event type, tags). Confidence thresholds are those in force; they are never
   altered by this contract (§6).
3. **Stage & load UAT** — `stage_enriched_radar_inputs.py prepare` → `verify-bundle`
   (must report `status: passed`) → phased SQL load; every phase must reach
   `validated`. Uncertain articles go to the review queue, not the bundle.
4. **Compile & cascade** — `ingest_cascade.py` for the batch's articles per the
   cascade procedure. People/organisations/places are linked only if they already
   exist; creating them stays with the judgment procedure.
5. **Gates & receipt** — run §5.1 gates; write the run receipt via `run_logger.py`
   including elapsed time and processed count.

## 4. Throughput measurement

- **Metric:** articles per second = articles completing step 4 ÷ elapsed seconds for
  steps 2–5, taken from the batch's run receipt.
- **Reported per batch** (printed, not just filed): batch number, articles processed,
  articles held for review, elapsed seconds, articles/second.
- **Anomaly rule:** if a batch runs below 50% of the median of all prior batches in the
  run, note it and continue; if **two consecutive** batches do, pause and report before
  continuing.

## 5. Quality gates (pass/fail — never advisory)

### 5.1 Per batch (before the next batch starts)

- `article_quality.py --check` over the batch's 10 compiled articles: **0 failures**.
- Link check scoped to files touched by the batch: **no hard failures** (broken links,
  nested-target links, YAML errors).
- UAT load phases for the batch's bundle: all **`validated`**; bundle verify
  **`passed`**.
- Print the actual command outputs — a gate not shown in the transcript did not run.

### 5.2 Per run (after the final batch)

- Full-vault `check_links.py` prints **CLEAN** (exit 0), using the documented
  split-invocation pattern if needed for timeouts.
- `Inputs/articles/` root contains **0 unprocessed `.md` files** (review-held articles
  excepted, per §7.1), confirmed by directory listing.
- Related-entities warnings remain **0**.
- Summary printed: batches run, total processed, total held for review, per-batch
  art/sec table, median art/sec.

### 5.3 Human audit (outside the run)

- Weekly spot-audit of 5 randomly chosen newly-cascaded articles against their cited
  sources (provenance check no script performs). Failures reopen the run's batches.

## 6. Constraints (hard, non-negotiable)

- Never edit, normalize, or delete anything under `raw/`.
- Never lower or bypass enrichment confidence thresholds, and never hand-fill a field
  the gate held back.
- Never write to the production MySQL database; UAT only. Production promotion is a
  separate, explicitly approved act.
- Never modify frozen schemas, radar weights/thresholds, or vault rules; any proposed
  change goes to `entities/decisions/` first and is out of scope for a throughput run.
- Append-only logs; one log line per entity touched; receipts for every batch.

## 7. Edge-case rulings (pre-decided so the run never improvises)

1. **Review-held articles count as processed** for backlog and goal purposes once they
   are (a) listed in the run's review queue artifact with reasons, and (b) reported in
   the batch summary. They are *not* loaded, compiled, or cascaded until an attributed
   approval file admits them on a later run. The run never approves its own holds.
2. **The stray `Inputs/articles/N/` file** is not processed. Report its presence and
   contents in the run summary for a human ruling; do not move or delete it.
3. **Gate failure protocol:** stop the line at the failing batch. For mechanical link
   classes only, one `fix_links.py` repair attempt is permitted, followed by a gate
   re-run. If the gate still fails — or the failure is a quality/schema/load failure —
   halt the run and report: batch number, failing gate, full output, articles affected.
   At most 10 articles are ever suspect.
4. **Enrichment API or MySQL unavailability:** halt and report. Do not retry in a loop,
   do not proceed to later steps for unenriched articles.
5. **Duplicate or already-compiled article encountered:** skip it, report it, do not
   overwrite (existing destinations are never overwritten).

## 8. Stop conditions

The run ends when any of the following holds:

- All backlog articles are processed or review-held, and §5.2 gates pass (success).
- A gate failure survives the §7.3 protocol (halt with report).
- The turn/time bound in the invoking `/goal` condition is reached (default: 40 turns).
- The operator clears the goal.

## 9. Invocation reference

Run under Claude Code CLI (v2.1.139+) from the vault root, workspace trusted, with
`.env.local` (OpenAI key) and read-only MySQL credentials configured **before** setting
the goal. Pair with auto mode for unattended turns. Example condition:

```
/goal All unprocessed articles under Inputs/articles are enriched, loaded to UAT,
compiled and cascaded per scripts/throughput_goal_contract.md, in batches of 10.
After each batch print the batch articles/second, the article_quality.py --check
output (0 failures), the scoped link-check result (no hard failures), and the
review-queue count. After the final batch run full-vault check_links.py and print
CLEAN, and show Inputs/articles root has 0 unprocessed .md files. Constraints:
never edit raw/, never change confidence thresholds, never write production MySQL,
follow the contract's gate-failure protocol. Or stop after 40 turns.
```

## 10. Review cadence

Weekly scoreboard to the owner: backlog count, batches run, median art/sec and trend,
review-queue depth, gate results (all zeros expected), spot-audit outcome. Contract
targets are revisited after the first full run establishes the end-to-end baseline
(§2), recorded here as an amendment with its date.
