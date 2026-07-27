#!/usr/bin/env python3
"""Build the dashboard dataset from the Markdown vault using Python only."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ENTITIES = ROOT / "entities"
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "dashboard-data.json"
SYSTEM_FILES = {"index.md", "catalog.md", "log.md"}
DOMAINS = [
    "people",
    "organisations",
    "place",
    "country",
    "outlet",
    "topic",
    "appointments",
    "issues",
    "search",
    "decisions",
]


def parse_scalar(value: str):
    value = value.strip()
    if not value:
        return None
    if value in {"null", "None", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            inner = value[1:-1].strip()
            return [part.strip().strip("'\"") for part in inner.split(",")] if inner else []
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def read_note(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    lines = text[4:end].splitlines()
    data: dict = {}
    active_key: str | None = None
    for line in lines:
        if re.match(r"^\s+-\s+", line) and active_key:
            if not isinstance(data.get(active_key), list):
                data[active_key] = []
            data[active_key].append(parse_scalar(re.sub(r"^\s+-\s+", "", line)))
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9_]*):\s*(.*)$", line)
        if not match:
            continue
        active_key, raw = match.groups()
        data[active_key] = [] if not raw.strip() else parse_scalar(raw)
    return data, text[end + 4 :]


def note_files(domain: str) -> list[Path]:
    folder = ENTITIES / domain
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.rglob("*.md")
        if path.name not in SYSTEM_FILES and not any(part.startswith(".") for part in path.parts)
    )


def display_name(meta: dict, path: Path) -> str:
    for key in ("displayName", "articleTitle", "title", "name"):
        if meta.get(key):
            return str(meta[key])
    slug = re.sub(r"^\d+-", "", path.stem)
    return slug.replace("-", " ").title()


def numeric(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def month_label(key: str) -> str:
    try:
        return datetime.strptime(key, "%Y-%m").strftime("%b %Y")
    except ValueError:
        return key


def top_entities(domain: str, limit: int = 8) -> list[dict]:
    rows = []
    for path in note_files(domain):
        meta, _ = read_note(path)
        count = int(numeric(meta.get("articleCount") or meta.get("mentionCount")))
        if count <= 0:
            continue
        rows.append({"name": display_name(meta, path), "count": count})
    return sorted(rows, key=lambda row: (-row["count"], row["name"].lower()))[:limit]


def section_text(body: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", body, flags=re.MULTILINE | re.DOTALL
    )
    if not match:
        return ""
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", match.group(1))
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"[`*_#]", "", text)
    return " ".join(text.split())


def thirty_word_summary(text: str) -> str:
    """Return a deterministic excerpt of at most 30 whitespace-delimited words."""
    words = text.split()
    if not words:
        return "Summary unavailable in the source note."
    excerpt = " ".join(words[:30])
    return f"{excerpt}…" if len(words) > 30 else excerpt


def main() -> None:
    counts = {domain: len(note_files(domain)) for domain in DOMAINS}
    article_paths = note_files("article")
    months: Counter[str] = Counter()
    sentiments: Counter[str] = Counter()
    event_types: Counter[str] = Counter()
    source_types: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    weekdays: Counter[str] = Counter()
    links_by_domain: Counter[str] = Counter()
    coverage_total = 0
    with_url = 0
    with_sentiment = 0
    with_event = 0
    dated_articles = []

    filename_domain = {}
    for domain in DOMAINS:
        for path in note_files(domain):
            filename_domain[path.stem] = domain

    for path in article_paths:
        meta, body = read_note(path)
        raw_date = str(meta.get("publishedDate") or "")
        month = raw_date[:7] if re.match(r"^\d{4}-\d{2}", raw_date) else path.parent.name
        if re.match(r"^\d{4}-\d{2}$", month):
            months[month] += 1
        if meta.get("toneSentiment"):
            sentiments[str(meta["toneSentiment"]).title()] += 1
            with_sentiment += 1
        if meta.get("eventType"):
            event_types[str(meta["eventType"]).title()] += 1
            with_event += 1
        source_types[str(meta.get("sourceType") or "Unknown").title()] += 1
        if meta.get("sourceUrl"):
            with_url += 1
        coverage_total += int(numeric(meta.get("coverageCount"), 1))
        raw_tags = meta.get("tags") or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        for tag in raw_tags:
            tag = str(tag).lstrip("#").strip()
            if tag and tag != "source":
                tags[tag] += 1
        for target in re.findall(r"\[\[([^\]|/#]+)(?:\|[^\]]+)?\]\]", body):
            domain = filename_domain.get(target)
            if domain:
                links_by_domain[domain] += 1
        if raw_date:
            try:
                parsed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                weekdays[parsed.strftime("%a")] += 1
                summary = section_text(body, "Summary")
                if len(summary.split()) < 30:
                    summary = f"{summary} {section_text(body, 'Key Points')}".strip()
                dated_articles.append(
                    (parsed, display_name(meta, path), path, thirty_word_summary(summary))
                )
            except ValueError:
                pass

    month_rows = [
        {"key": key, "label": month_label(key), "count": months[key]}
        for key in sorted(months)
    ]
    peak_month = max(month_rows, key=lambda row: row["count"], default=None)
    latest_month = month_rows[-1] if month_rows else None
    previous_month = month_rows[-2] if len(month_rows) > 1 else None
    month_change = None
    if latest_month and previous_month and previous_month["count"]:
        month_change = round(
            (latest_month["count"] - previous_month["count"]) / previous_month["count"] * 100, 1
        )

    latest_articles = []
    for published, title, path, summary in sorted(dated_articles, reverse=True)[:8]:
        latest_articles.append(
            {
                "title": title,
                "summary": summary,
                "published": published.strftime("%d %b %Y"),
                "month": published.strftime("%b"),
                "path": str(path.relative_to(ROOT)),
            }
        )

    issue_rows = []
    for path in note_files("issues"):
        meta, body = read_note(path)
        issue_rows.append(
            {
                "name": display_name(meta, path),
                "status": str(meta.get("status") or "watch").lower(),
                "ramification": str(meta.get("ramification") or "unrated").lower(),
                "score": round(numeric(meta.get("score")), 2),
                "articles": int(numeric(meta.get("articleCount"))),
                "firstFlagged": str(meta.get("firstFlagged") or "—"),
                "lastScored": str(meta.get("lastScored") or "—"),
                "assessment": section_text(body, "Assessment")[:420],
                "posture": section_text(body, "Posture")[:360],
            }
        )
    issue_rows.sort(key=lambda row: (-row["score"], row["name"]))

    entity_composition = [
        {"key": domain, "label": domain.replace("organisations", "organizations").title(), "count": counts[domain]}
        for domain in ("topic", "outlet", "people", "organisations", "place", "country", "appointments")
    ]
    entity_total = sum(counts.values())
    link_total = sum(links_by_domain.values())
    latest_coverage_at = (
        max(item[0] for item in dated_articles)
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
        if dated_articles
        else "1970-01-01T00:00:00Z"
    )
    refreshed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    data = {
        "refreshedAt": refreshed_at,
        "latestCoverageAt": latest_coverage_at,
        "coverage": {
            "from": month_rows[0]["label"] if month_rows else "—",
            "to": month_rows[-1]["label"] if month_rows else "—",
        },
        "summary": {
            "articles": len(article_paths),
            "entities": entity_total,
            "outlets": counts["outlet"],
            "liveIssues": sum(1 for row in issue_rows if row["status"] not in {"closed", "dismissed"}),
            "links": link_total,
            "linksPerArticle": round(link_total / len(article_paths), 1) if article_paths else 0,
            "coverageMentions": coverage_total,
        },
        "months": month_rows,
        "peakMonth": peak_month,
        "latestMonth": latest_month,
        "monthChange": month_change,
        "sentiments": [{"name": name, "count": count} for name, count in sentiments.most_common()],
        "eventTypes": [{"name": name, "count": count} for name, count in event_types.most_common()],
        "sourceTypes": [{"name": name, "count": count} for name, count in source_types.most_common()],
        "entityComposition": entity_composition,
        "top": {
            "countries": top_entities("country", 10),
            "outlets": top_entities("outlet", 10),
            "people": top_entities("people", 8),
            "organizations": top_entities("organisations", 8),
            "topics": top_entities("topic", 8),
            "places": top_entities("place", 8),
            "tags": [{"name": name, "count": count} for name, count in tags.most_common(8)],
        },
        "issues": issue_rows,
        "health": [
            {"label": "Source URL", "value": round(with_url / len(article_paths) * 100, 1) if article_paths else 0},
            {"label": "Sentiment", "value": round(with_sentiment / len(article_paths) * 100, 1) if article_paths else 0},
            {"label": "Event type", "value": round(with_event / len(article_paths) * 100, 1) if article_paths else 0},
        ],
        "weekdays": [{"name": day, "count": weekdays[day]} for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")],
        "latestArticles": latest_articles,
    }
    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} from {len(article_paths):,} articles and {entity_total:,} entities")


if __name__ == "__main__":
    main()
