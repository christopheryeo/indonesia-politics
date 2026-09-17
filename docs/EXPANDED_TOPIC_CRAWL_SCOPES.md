---
type: crawl-scope-proposal
status: ready-for-execution
created: 2026-09-07
owner: Alex
procedure: scripts/topic_crawl_plan.md
---

# Expanded Topic Crawl Scopes

Each scope uses the governed Topic Date-Range Crawl procedure. The date range is inclusive, uses
Asia/Singapore, accepts English and Bahasa Indonesia, and caps discovery at 50 canonical article
candidates per topic. The cap keeps the first pass bounded; held, duplicate, and rejected results
remain evidenced rather than being replaced with unrelated candidates.

## Common controls

- Date range: 2026-08-01 to 2026-09-07
- Timezone: Asia/Singapore
- Languages: eng, ind
- Candidate cap: 50 per topic
- Sources: public article URLs only; NewsAPI.ai mapping, retrieval, and recovery follow the
  governing procedure.
- Exclusions: duplicate article IDs, canonical URLs, NewsAPI.ai URIs, source identities, and body
  hashes; non-article pages; incomplete or unsupported-language bodies.

## 1. Kejagung-Polri-KPK jurisdiction and case-transfer disputes

Queries:

- `Kejagung Polri KPK pengambilalihan perkara`
- `sengketa kewenangan Kejaksaan Polri KPK`
- `KPK mengambil alih penyidikan Kejaksaan Polri`
- `Indonesia law-enforcement case transfer KPK AGO police`

## 2. Asset recovery and beneficial ownership in corruption and TPPU cases

Queries:

- `perampasan aset TPPU korupsi`
- `pemulihan aset hasil korupsi`
- `pemilik manfaat perkara korupsi`
- `Indonesia asset recovery beneficial ownership corruption money laundering`

## 3. Danantara governance and state-asset consolidation

Queries:

- `Danantara tata kelola`
- `Danantara konsolidasi aset negara`
- `Danantara transparansi investasi`
- `Danantara governance state asset consolidation Indonesia`

## 4. Central-bank independence and macroeconomic governance

Queries:

- `independensi Bank Indonesia`
- `gubernur Bank Indonesia KSSK stabilitas rupiah`
- `tata kelola kebijakan moneter Indonesia`
- `Bank Indonesia independence macroeconomic governance`

## 5. Civil-military boundaries in domestic governance

Queries:

- `TNI di ranah sipil`
- `perbantuan TNI lembaga sipil`
- `pengawasan sipil militer Indonesia`
- `Indonesia civil military relations domestic governance`

