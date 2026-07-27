---
type: procedure
name: issue-radar
status: active
last_updated: 2026-07-23
---

# Issue Radar Procedure

Turns deterministic radar flags into filed, cited issue assessments in `entities/issues/`. The
split follows the vault's core division of labour: `scripts/issue_radar.py` does the counting from
read-only canonical product tables (velocity, breadth, institutional attachment, recurrence — mechanical, hindsight-free); this
procedure does the judgment (clustering, ramification, catalysts, posture). Neither replaces the
other: the radar over-generates by design (~20x at tag level), and the judgment pass must never
invent signals the radar did not report.

**Cadence:** run after every ingest/cascade batch, before the nightly catalog rebuild. A pass with
no new flags still updates `lastScored` on active (`hot`/`warm`) issues.

**Hard rules (inherited from the cascade procedure):** piped `[[real-filename|Display]]` links
only; no enrichment from live web or model background knowledge — every claim, and especially
every catalyst date, must be quoted from a citing article already in the vault; quote flow-list
values beginning with `#`; append-only logs.

## Step 1 — Run the signal layer (mechanical)

1. Run against UAT while developing or validating:
   `python3 scripts/issue_radar.py --source uat --defaults-file <read-only-client.cnf>`.
   Run against production only with an approved read-only account (preferably a replica):
   `python3 scripts/issue_radar.py --source production --defaults-file <read-only-client.cnf>`.
   Add `--asof <date>` for reconstruction. Capture every flag at WARM or above; WATCH flags are
   optional at analyst discretion. The script never writes to either database.
2. Do not edit, reweight, or suppress the script's output by hand. If the thresholds seem wrong,
   that is a Decision-note conversation, not an in-pass adjustment.

## Step 2 — Cluster flags into issue objects (judgment)

3. Read `entities/issues/catalog.md` first. For each flag, decide: does this tag belong to an
   issue already on the watchlist? Updating an existing note is the default; minting a new issue
   is the exception. (Backtest reference: `amos yee`, `enlistment act`, `cmpb`, `deportation`,
   `fines`, `chicago` were six flags but one issue.)
4. To test whether two flags are one issue, open a sample of each flag's recent citing articles
   (via the shared article database or the article catalog) and check overlap of articles and entities — shared
   articles means same issue. Never cluster on tag-name similarity alone.
5. Name the issue by its risk, not its keyword (`ns-enforcement-enlistment-act`, not `amos-yee` —
   people are carriers of issues, not issues).

## Step 3 — Ramification questionnaire (judgment, answered only from vault content)

6. For each issue object, answer in writing, citing articles:
   a. **Forced response** — if coverage doubles, who must respond: a minister, an agency,
      or no one? (Institutional-category migration is the strongest single predictor.)
   b. **Fault lines** — does it touch a standing sensitivity: NS fairness, sovereignty, foreign-
      policy neutrality, race/religion, procurement probity?
   c. **Catalysts** — do the citing articles mention future dated events (court dates, parliament
      sittings, scheduled visits, exercises, anniversaries)? Extract each with its date and source
      link. An accelerating issue with a known catalyst is schedulable risk.
   d. **Irreversible positions** — has anyone senior taken an on-record stance that constrains
      future response?
   e. **Migration** — is a foreign story acquiring domestic institutional categories (the US-Iran
      → repatriation pattern)?
7. Assign `ramification`: `severe` (multiple fault lines or forced minister-level response),
   `high` (one fault line, institutional response likely), `moderate` (contained but recurring),
   `low` (benign shape). Acceleration without ramification is a dismissal, not an alert.

## Step 4 — File (mechanical bookkeeping + judgment prose)

8. Create or update the issue note per the `entities/issues/index.md` registry and template:
   frontmatter fields from the radar output (`score`, `status` from tier, `clusterTags`,
   `firstFlagged` preserved from first filing, `lastScored` = today); `## Signals` appended, never
   rewritten; `## Assessment`, `## Catalysts`, `## Posture` written per Step 3.
9. Benign flags: file with `status: dismissed` and a one-line reason. Dismissals are calibration
   data — never deleted, and a dismissed issue that re-flags later is reopened, not duplicated.
10. Append one `log.md` entry per issue touched (full timestamp, wikilink, action, reasoning).
11. Regenerate the domain catalog: `python3 scripts/generate_catalog.py issues`.

## Step 5 — Surface (delivery)

12. Report to the user only issues at `warm`+ whose ramification is `moderate`+, ordered per the
    domain's Producing a List convention, each with its plain-language "why" lines and catalysts.
    Everything else stays on the quiet watchlist. A radar that cries wolf gets muted — precision
    over recall at the alert layer, liberal filing at the watchlist layer.

## Known limits

- Detects percolating issues only; exogenous shocks (bomb threats, sudden attacks) have no media
  precursors and must never be claimed as detectable.
- Tag-level candidates are a proxy; clustering quality is the judgment layer's responsibility.
- Corpus tone fields carry no negative-sentiment label; unfacilitated/opinionated share stands in.
