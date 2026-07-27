"use client";

import { useMemo, useState } from "react";
import data from "./dashboard-data.json";

const number = new Intl.NumberFormat("en-SG");
const compact = new Intl.NumberFormat("en-SG", { notation: "compact", maximumFractionDigits: 1 });

type RankingKey = "countries" | "outlets" | "people" | "organizations" | "topics";
type MixKey = "sentiments" | "eventTypes" | "sourceTypes";

const mixLabels: Record<MixKey, string> = {
  sentiments: "Sentiment",
  eventTypes: "Event type",
  sourceTypes: "Source",
};

const statusOrder: Record<string, number> = { hot: 3, warm: 2, watch: 1, closed: 0, dismissed: 0 };

function formatGenerated(value: string) {
  return new Intl.DateTimeFormat("en-SG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
}

export default function Dashboard() {
  const [windowSize, setWindowSize] = useState<3 | 6 | 99>(99);
  const [ranking, setRanking] = useState<RankingKey>("countries");
  const [mix, setMix] = useState<MixKey>("sentiments");
  const sortedIssues = useMemo(
    () => [...data.issues].sort((a, b) => (statusOrder[b.status] ?? 0) - (statusOrder[a.status] ?? 0) || b.score - a.score),
    [],
  );
  const [selectedIssue, setSelectedIssue] = useState(sortedIssues[0]?.name ?? "");

  const months = windowSize === 99 ? data.months : data.months.slice(-windowSize);
  const visibleArticles = months.reduce((sum, month) => sum + month.count, 0);
  const maxMonth = Math.max(...months.map((month) => month.count), 1);
  const currentIssue = sortedIssues.find((issue) => issue.name === selectedIssue) ?? sortedIssues[0];
  const rankingRows = data.top[ranking];
  const rankingMax = Math.max(...rankingRows.map((row) => row.count), 1);
  const mixRows = data[mix];
  const mixTotal = mixRows.reduce((sum, row) => sum + row.count, 0);
  const mixColors = ["#A00202", "#C6D781", "#AE9842", "#CBAC81", "#777477"];
  const donutStops = mixRows.map((row, index) => {
    const start = mixTotal
      ? (mixRows.slice(0, index).reduce((sum, item) => sum + item.count, 0) / mixTotal) * 100
      : 0;
    const end = start + (mixTotal ? (row.count / mixTotal) * 100 : 0);
    return `${mixColors[index % mixColors.length]} ${start}% ${end}%`;
  });
  const maxEntity = Math.max(...data.entityComposition.map((entity) => entity.count), 1);

  return (
    <main>
      <header className="command-header">
        <div className="header-inner">
          <div className="brand-lockup" aria-label="Sentient.io AI and Data Cloud Platform">
            <span className="brand-orbit" aria-hidden="true"><span /></span>
            <span className="brand-words"><strong>Sentient.io</strong><small>AI &amp; DATA CLOUD PLATFORM</small></span>
          </div>
          <div className="header-meta">
            <span className="live-dot" aria-hidden="true" />
            <span>Dashboard rebuilt {formatGenerated(data.refreshedAt)} SGT</span>
            <span aria-hidden="true">·</span>
            <span>{data.summary.articles ? `Latest coverage ${formatGenerated(data.latestCoverageAt)} SGT` : "Awaiting first ingest"}</span>
          </div>
        </div>

        <div className="hero header-inner">
          <div>
            <p className="eyebrow">Media intelligence / Indonesia politics</p>
            <h1>See the signal<br />before it becomes the story.</h1>
            <p className="hero-copy">A connected view of coverage volume, voices, entities, geography and issue momentum—calculated directly from the vault.</p>
          </div>
          <div className="hero-pulse" aria-label={`${number.format(data.summary.liveIssues)} live issues under watch`}>
            <div className="pulse-ring pulse-three" />
            <div className="pulse-ring pulse-two" />
            <div className="pulse-ring pulse-one" />
            <div className="pulse-core"><strong>{data.summary.liveIssues}</strong><span>LIVE<br />ISSUES</span></div>
          </div>
        </div>
      </header>

      <div className="dashboard-shell">
        {data.summary.articles === 0 && (
          <section className="empty-state" role="status">
            <strong>Empty vault ready.</strong> Add reviewed source material to begin monitoring Indonesia politics.
          </section>
        )}
        <section className="metric-strip" aria-label="Corpus summary">
          <article className="metric metric-primary">
            <span>Articles monitored</span>
            <strong>{number.format(data.summary.articles)}</strong>
            <small>{data.coverage.from} – {data.coverage.to}</small>
          </article>
          <article className="metric">
            <span>Connected entities</span>
            <strong>{number.format(data.summary.entities)}</strong>
            <small>Across {data.entityComposition.length + 3} knowledge domains</small>
          </article>
          <article className="metric">
            <span>Media outlets</span>
            <strong>{number.format(data.summary.outlets)}</strong>
            <small>Tracked source records</small>
          </article>
          <article className="metric">
            <span>Knowledge links</span>
            <strong>{compact.format(data.summary.links)}</strong>
            <small>{data.summary.linksPerArticle} links per article</small>
          </article>
          <article className="metric">
            <span>Coverage mentions</span>
            <strong>{compact.format(data.summary.coverageMentions)}</strong>
            <small>Reported reach across sources</small>
          </article>
        </section>

        <section className="dashboard-grid trend-section">
          <article className="panel panel-wide">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Coverage velocity</p>
                <h2>Articles by month</h2>
              </div>
              <div className="period-control" aria-label="Chart period">
                {([3, 6, 99] as const).map((value) => (
                  <button key={value} className={windowSize === value ? "active" : ""} onClick={() => setWindowSize(value)} aria-pressed={windowSize === value}>
                    {value === 99 ? "All" : `${value}M`}
                  </button>
                ))}
              </div>
            </div>
            <div className="chart-summary">
              <strong>{number.format(visibleArticles)}</strong>
              <span>articles in selected period</span>
              <span className="peak-note">Peak: {data.peakMonth?.label} · {number.format(data.peakMonth?.count ?? 0)}</span>
            </div>
            <div className="bar-chart" role="img" aria-label={`Monthly article counts from ${months[0]?.label} to ${months.at(-1)?.label}`}>
              {months.map((month) => (
                <div className="bar-column" key={month.key}>
                  <span className="bar-value">{compact.format(month.count)}</span>
                  <div className="bar-track"><div className="bar-fill" style={{ height: `${Math.max(3, (month.count / maxMonth) * 100)}%` }} /></div>
                  <span className="bar-label">{month.label.replace(" 20", " ’")}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel momentum-panel">
            <p className="section-kicker">Current read</p>
            <h2>Coverage pulse</h2>
            <div className="pulse-number">
              <strong>{number.format(data.latestMonth?.count ?? 0)}</strong>
              <span>articles in {data.latestMonth?.label}</span>
            </div>
            <div className={`change-chip ${(data.monthChange ?? 0) < 0 ? "down" : "up"}`}>
              {(data.monthChange ?? 0) > 0 ? "+" : ""}{data.monthChange ?? 0}% vs prior month
            </div>
            <p className="context-note">The latest month may be incomplete. Use the full history to distinguish collection timing from a true change in attention.</p>
            <div className="mini-rule" />
            <div className="micro-stats">
              <div><span>Peak month</span><strong>{data.peakMonth?.label}</strong></div>
              <div><span>Peak volume</span><strong>{number.format(data.peakMonth?.count ?? 0)}</strong></div>
            </div>
          </article>
        </section>

        <section className="issue-radar">
          <div className="section-heading-row">
            <div>
              <p className="section-kicker red">Early warning</p>
              <h2>Issue radar</h2>
            </div>
            <p>Deterministic signals, filed assessments</p>
          </div>
          <div className="radar-layout">
            <div className="issue-list" role="list" aria-label="Monitored issues">
              {sortedIssues.map((issue) => (
                <button key={issue.name} className={`issue-row ${selectedIssue === issue.name ? "selected" : ""}`} onClick={() => setSelectedIssue(issue.name)} aria-pressed={selectedIssue === issue.name}>
                  <span className={`status status-${issue.status}`}>{issue.status}</span>
                  <span className="issue-name">{issue.name}</span>
                  <span className="issue-score">{Math.round(issue.score * 100)}</span>
                </button>
              ))}
            </div>
            {currentIssue && (
              <article className="issue-detail">
                <div className="score-gauge" style={{ "--score": `${currentIssue.score * 100}%` } as React.CSSProperties}>
                  <strong>{Math.round(currentIssue.score * 100)}</strong><span>RADAR<br />SCORE</span>
                </div>
                <div className="issue-copy">
                  <div className="issue-meta">
                    <span>{currentIssue.ramification} ramification</span>
                    <span>{currentIssue.articles} source notes</span>
                    <span>flagged {currentIssue.firstFlagged}</span>
                  </div>
                  <h3>{currentIssue.name}</h3>
                  <p>{currentIssue.assessment || "Assessment recorded in the issue watchlist."}</p>
                  {currentIssue.posture && <p className="posture"><strong>Posture:</strong> {currentIssue.posture}</p>}
                </div>
              </article>
            )}
          </div>
        </section>

        <section className="dashboard-grid intelligence-grid">
          <article className="panel entity-panel">
            <div className="panel-heading">
              <div><p className="section-kicker">Knowledge graph</p><h2>Entity composition</h2></div>
              <span className="big-inline">{compact.format(data.summary.entities)}</span>
            </div>
            <div className="entity-bars">
              {data.entityComposition.map((entity) => (
                <div className="entity-row" key={entity.key}>
                  <span>{entity.label}</span>
                  <div className="entity-track"><i style={{ width: `${Math.max(2, (entity.count / maxEntity) * 100)}%` }} /></div>
                  <strong>{number.format(entity.count)}</strong>
                </div>
              ))}
            </div>
          </article>

          <article className="panel mix-panel">
            <div className="panel-heading">
              <div><p className="section-kicker">Corpus mix</p><h2>{mixLabels[mix]}</h2></div>
              <select aria-label="Select corpus breakdown" value={mix} onChange={(event) => setMix(event.target.value as MixKey)}>
                {(Object.keys(mixLabels) as MixKey[]).map((key) => <option key={key} value={key}>{mixLabels[key]}</option>)}
              </select>
            </div>
            <div className="donut-layout">
              <div className="donut" style={{ background: `conic-gradient(${donutStops.join(",")})` }}>
                <div><strong>{compact.format(mixTotal)}</strong><span>classified</span></div>
              </div>
              <div className="legend">
                {mixRows.map((row, index) => (
                  <div key={row.name}><i style={{ background: mixColors[index % mixColors.length] }} /><span>{row.name}</span><strong>{number.format(row.count)}</strong></div>
                ))}
              </div>
            </div>
          </article>

          <article className="panel ranking-panel">
            <div className="panel-heading">
              <div><p className="section-kicker">Influence map</p><h2>Top {ranking}</h2></div>
              <select aria-label="Select entity ranking" value={ranking} onChange={(event) => setRanking(event.target.value as RankingKey)}>
                <option value="countries">Countries</option>
                <option value="outlets">Outlets</option>
                <option value="people">People</option>
                <option value="organizations">Organizations</option>
                <option value="topics">Topics</option>
              </select>
            </div>
            <div className="ranking-list">
              {rankingRows.map((row, index) => (
                <div className="ranking-row" key={row.name}>
                  <span className="rank">{String(index + 1).padStart(2, "0")}</span>
                  <span className="ranking-name">{row.name}<i style={{ width: `${(row.count / rankingMax) * 100}%` }} /></span>
                  <strong>{number.format(row.count)}</strong>
                </div>
              ))}
            </div>
          </article>

          <article className="panel health-panel">
            <p className="section-kicker">Data confidence</p>
            <h2>Corpus health</h2>
            <p className="health-intro">Field completeness across compiled article notes.</p>
            <div className="health-list">
              {data.health.map((item) => (
                <div key={item.label}>
                  <div><span>{item.label}</span><strong>{item.value}%</strong></div>
                  <div className="health-track"><i style={{ width: `${item.value}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="source-seal">
              <span>MD</span>
              <div><strong>Source of truth</strong><small>Computed from Markdown—not generated text</small></div>
            </div>
          </article>
        </section>

        <section className="latest-section">
          <div className="section-heading-row">
            <div><p className="section-kicker">Freshest coverage</p><h2>Latest article notes</h2></div>
            <span>{data.latestArticles.length} most recent</span>
          </div>
          <div className="latest-table" role="table" aria-label="Latest monitored articles">
            {data.latestArticles.length === 0 && (
              <p className="empty-list">No article notes have been ingested.</p>
            )}
            {data.latestArticles.map((article, index) => (
              <div className="latest-row" role="row" key={`${article.path}-${index}`}>
                <span className="latest-index">{String(index + 1).padStart(2, "0")}</span>
                <div className="latest-copy">
                  <strong>{article.title}</strong>
                  <p>{article.summary}</p>
                </div>
                <span>{article.published}</span>
              </div>
            ))}
          </div>
        </section>

        <footer>
          <div className="brand-lockup footer-brand"><span className="brand-orbit" aria-hidden="true"><span /></span><span className="brand-words"><strong>Sentient.io</strong></span></div>
          <p>Media Intelligence · Rebuilt {formatGenerated(data.refreshedAt)} SGT · Latest coverage {formatGenerated(data.latestCoverageAt)} SGT</p>
        </footer>
      </div>
    </main>
  );
}
