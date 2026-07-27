#!/usr/bin/env python3
"""Compile raw input articles and cascade their entity backlinks.

This is the reusable runner for a full-folder article cascade. It packages the
mechanical parts of the manual procedure in ``entity_cascade_procedure.md``:
turn a raw intake file into a compiled article note, move it into the article
domain, create or update the linked entity notes, rebuild generated catalogs,
validate the hard failure classes, update the article-domain status table, and
write a timed run receipt.

Use this when a monthly folder already exists under ``Inputs/articles/YYYY-MM/``
and each file is a raw feed/crawl Markdown item. The script intentionally does
not fetch articles, edit preserved ``raw/`` exports, enrich summaries from the
web, create people/organisation/place notes from model judgment, or run the
early-warning issue radar. It only uses the raw file's metadata/body plus entity
notes already present in the vault.

Timing contract:
  A cascade run starts the timer before compile/cascade work begins and stops
  after validation, status bookkeeping, and receipt writing. The receipt's
  ``articleMetrics.avgSecPerArticle`` is the throughput number to report after
  each cascade run. If there are no input files, the script exits cleanly and
  does not write a receipt, because no article was processed.

Dry-run contract:
  ``--dry-run`` previews the compile/cascade pass and prints what would be
  processed, but it does not write notes, move inputs, append logs, rebuild
  catalogs, validate changed files, or update status tables.

Examples:
  python3 scripts/ingest_cascade.py --month 2026-07
  python3 scripts/ingest_cascade.py --input-dir Inputs/articles/2026-07
  python3 scripts/ingest_cascade.py --month 2026-07 --dry-run
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from patch_coverage import apply_update as patch_apply_update
from run_logger import RunLogger

try:
    import yaml
except ImportError:
    print("This script requires PyYAML. Install it with: pip3 install pyyaml", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "Inputs" / "articles"
ARTICLE_ROOT = ROOT / "entities" / "article"
SYSTEM_FILES = {"index.md", "catalog.md", "log.md", "_template.md", ".DS_Store"}
CATALOG_DOMAINS = ["article", "outlet", "country", "topic", "organisations", "people", "place"]

DOMAIN_DIRS = {
    "outlets": ROOT / "entities" / "outlet",
    "countries": ROOT / "entities" / "country",
    "topics": ROOT / "entities" / "topic",
    "organisations": ROOT / "entities" / "organisations",
    "people": ROOT / "entities" / "people",
    "places": ROOT / "entities" / "place",
}
LOGS = {
    "article": ROOT / "entities" / "article" / "log.md",
    "outlets": ROOT / "entities" / "outlet" / "log.md",
    "countries": ROOT / "entities" / "country" / "log.md",
    "topics": ROOT / "entities" / "topic" / "log.md",
    "organisations": ROOT / "entities" / "organisations" / "log.md",
    "people": ROOT / "entities" / "people" / "log.md",
    "places": ROOT / "entities" / "place" / "log.md",
}
DOMAIN_LINK_PREFIX = {
    "outlets": "outlet",
    "countries": "country",
    "topics": "topic",
    "organisations": "organisations",
    "people": "people",
    "places": "place",
}
COUNTED_DOMAINS = {"countries", "organisations", "people", "places"}

# This runner uses plural domain keys; patch_coverage.py (which owns the
# Coverage-block insertion and the count-increment rules) uses the singular
# folder names under entities/. Map between them at the one call site.
PATCH_COVERAGE_DOMAINS = {
    "outlets": "outlet",
    "countries": "country",
    "topics": "topic",
    "organisations": "organisations",
    "people": "people",
    "places": "place",
}

COUNTRY_SEED = {
    "singapore", "china", "united states", "us", "usa", "u.s.", "u.s", "malaysia",
    "indonesia", "philippines", "vietnam", "thailand", "brunei", "cambodia", "laos",
    "myanmar", "india", "japan", "south korea", "north korea", "taiwan", "hong kong",
    "australia", "new zealand", "united kingdom", "uk", "france", "germany", "russia",
    "ukraine", "iran", "iraq", "israel", "palestine", "qatar", "bahrain", "kuwait",
    "oman", "saudi arabia", "united arab emirates", "uae", "turkey", "syria", "lebanon",
    "jordan", "yemen", "pakistan", "bangladesh", "sri lanka", "canada", "sweden",
    "norway", "finland", "denmark", "netherlands", "belgium", "italy", "spain",
    "poland", "greece", "austria", "switzerland", "serbia", "kosovo", "cyprus",
    "estonia", "latvia", "lithuania", "south africa", "sudan", "somalia", "venezuela",
    "cuba", "marshall islands", "papua new guinea", "afghanistan", "iceland", "ireland",
    "egypt", "bulgaria", "mexico", "brazil", "argentina",
}


@dataclass
class EntityRecord:
    """A loaded entity note plus the names that can resolve back to it."""

    slug: str
    path: Path
    display: str
    frontmatter: dict[str, Any]


def slugify(value: str) -> str:
    """Return the vault filename stem for a display label or source ID."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "untitled"


def title_from_slug(slug: str) -> str:
    acronyms = {"tni", "dpr", "kpk", "mk", "ma", "us", "uk", "uae"}
    return " ".join(word.upper() if word in acronyms else word.capitalize() for word in slug.split("-"))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown note into YAML frontmatter and body text."""

    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    data = yaml.safe_load(raw) or {}
    return (data if isinstance(data, dict) else {}), body


def yaml_scalar(value: Any) -> str:
    """Normalize a raw YAML value into a single-line string."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.replace("\n", " ").strip()
    return str(value)


def yaml_list(value: Any) -> list[str]:
    """Normalize a raw YAML scalar/list into a clean list of strings."""

    if not value:
        return []
    if isinstance(value, list):
        return [yaml_scalar(item) for item in value if yaml_scalar(item)]
    return [yaml_scalar(value)]


def yaml_quote(value: Any) -> str:
    """Render a scalar safely for YAML frontmatter.

    Several vault fields contain values that can be misread by YAML, especially
    hashtags beginning with ``#`` and titles with punctuation. Let PyYAML render
    the scalar instead of hand-quoting those edge cases.
    """

    rendered = yaml.safe_dump(
        yaml_scalar(value),
        default_flow_style=True,
        allow_unicode=True,
        width=1_000_000,
    ).strip()
    return rendered.replace("\n...", "")


def wikilink(target: str, display: str | None = None) -> str:
    return f"[[{target}|{display or title_from_slug(target)}]]"


def canonical_field(frontmatter: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in frontmatter and frontmatter[name] not in (None, ""):
            return frontmatter[name]
    return ""


def dump_note(path: Path, frontmatter_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body.rstrip() + "\n", encoding="utf-8")


def load_entities() -> tuple[dict[str, dict[str, EntityRecord]], dict[str, dict[str, str]]]:
    """Load existing entity notes and build lowercase alias lookup tables.

    The cascade can create outlets, countries, and topics from raw metadata.
    People, organisations, and places are only linked when an existing note or
    alias is already present, because creating those entities requires judgment.
    """

    records: dict[str, dict[str, EntityRecord]] = {}
    aliases: dict[str, dict[str, str]] = {}
    for domain, domain_dir in DOMAIN_DIRS.items():
        records[domain] = {}
        aliases[domain] = {}
        for path in domain_dir.glob("*.md"):
            if path.name in SYSTEM_FILES:
                continue
            try:
                frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except Exception:
                frontmatter = {}
            display = yaml_scalar(frontmatter.get("displayName")) or title_from_slug(path.stem)
            record = EntityRecord(path.stem, path, display, frontmatter)
            records[domain][path.stem] = record
            alias_values = {display, path.stem.replace("-", " "), *yaml_list(frontmatter.get("aliases"))}
            for value in alias_values:
                if value.strip():
                    aliases[domain][value.strip().lower()] = path.stem
    return records, aliases


def append_log(domain: str, line: str, dry_run: bool) -> None:
    if dry_run:
        return
    LOGS[domain].parent.mkdir(parents=True, exist_ok=True)
    with LOGS[domain].open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def append_coverage(domain: str, record: EntityRecord, article_link: str, timestamp: str, dry_run: bool) -> bool:
    """Append an article backlink to an entity note if it is not already there.

    Returns ``True`` only when the note would receive a new Coverage entry. That
    makes reruns idempotent: an already-linked article is not counted twice.

    The insertion itself is delegated to ``patch_coverage.apply_update`` so the
    Coverage-block placement and the mentionCount/articleCount rules (including
    the outlet carve-out from the fix-articlecount-double-counting decision)
    exist in exactly one place. A previous inline copy here appended to the end
    of the file instead of into ``## Coverage``, which stranded backlinks under
    whatever section happened to be last.
    """

    if dry_run and not record.path.exists():
        return True

    target, _, label = article_link.removeprefix("[[").removesuffix("]]").partition("|")
    update = {"domain": PATCH_COVERAGE_DOMAINS[domain], "id": record.slug, "article": target}
    if label:
        update["label"] = label

    result = patch_apply_update(update["domain"], record.slug, [update], dry_run)
    if "error" in result:
        raise RuntimeError(f"patch_coverage failed for {domain}/{record.slug}: {result['error']}")
    if result["noop"]:
        return False

    # patch_coverage deliberately does not touch last_updated; the cascade does.
    if not dry_run:
        text = record.path.read_text(encoding="utf-8")
        record.path.write_text(
            re.sub(r"last_updated:.*", f"last_updated: {timestamp}", text, count=1),
            encoding="utf-8",
        )
    return True


def ensure_outlet(
    name: str,
    article_link: str,
    records: dict[str, dict[str, EntityRecord]],
    aliases: dict[str, dict[str, str]],
    timestamp: str,
    today: str,
    batch: str,
    dry_run: bool,
) -> tuple[str, str, bool]:
    """Create or update the outlet note for the article's publishing outlet."""

    display = yaml_scalar(name) or "Unknown Outlet"
    slug = aliases["outlets"].get(display.lower()) or slugify(display)
    path = DOMAIN_DIRS["outlets"] / f"{slug}.md"
    if slug not in records["outlets"]:
        body = f"# {display}\n\n## Coverage\n- {article_link}\n"
        frontmatter = [
            "type: entity", "subtype: outlet", "domain: Outlets", "status: active",
            f"displayName: {yaml_quote(display)}", "aliases:", f"  - {yaml_quote(display)}",
            "owner: Alex", f"created: {timestamp}", f"last_updated: {timestamp}",
            "articleCount: 1", "tags:", '  - "#outlet"',
        ]
        if not dry_run:
            dump_note(path, frontmatter, body)
        records["outlets"][slug] = EntityRecord(slug, path, display, {})
        aliases["outlets"][display.lower()] = slug
        append_log("outlets", f"- {today} - Created [[{slug}|{display}]] from {batch}.", dry_run)
        return slug, display, True
    record = records["outlets"][slug]
    if append_coverage("outlets", record, article_link, timestamp, dry_run):
        append_log("outlets", f"- {today} - Added coverage {article_link} to [[{slug}|{record.display}]].", dry_run)
    return slug, display, False


def ensure_country(
    name: str,
    article_link: str,
    records: dict[str, dict[str, EntityRecord]],
    aliases: dict[str, dict[str, str]],
    timestamp: str,
    today: str,
    batch: str,
    dry_run: bool,
) -> tuple[str, str, bool] | None:
    """Create or update a country note from explicit/inferred country metadata."""

    raw_name = yaml_scalar(name)
    if not raw_name:
        return None
    slug = aliases["countries"].get(raw_name.lower()) or slugify(raw_name)
    display = title_from_slug(slug) if slug in {"us", "usa", "u-s", "u-s-a", "uk", "uae"} else raw_name
    path = DOMAIN_DIRS["countries"] / f"{slug}.md"
    if slug not in records["countries"]:
        body = f"# {display}\n\n## Coverage\n- {article_link}\n"
        frontmatter = [
            "type: entity", "subtype: country", "domain: Countries", "status: active",
            f"displayName: {yaml_quote(display)}", "aliases:", f"  - {yaml_quote(raw_name)}",
            "owner: Alex", f"created: {timestamp}", f"last_updated: {timestamp}",
            "mentionCount: 1", "tags:", '  - "#country"',
        ]
        if not dry_run:
            dump_note(path, frontmatter, body)
        records["countries"][slug] = EntityRecord(slug, path, display, {})
        aliases["countries"][raw_name.lower()] = slug
        append_log("countries", f"- {today} - Created [[{slug}|{display}]] from {batch}.", dry_run)
        return slug, display, True
    record = records["countries"][slug]
    if append_coverage("countries", record, article_link, timestamp, dry_run):
        append_log("countries", f"- {today} - Added coverage {article_link} to [[{slug}|{record.display}]].", dry_run)
    return slug, display, False


def ensure_topic(
    name: str,
    article_link: str,
    records: dict[str, dict[str, EntityRecord]],
    aliases: dict[str, dict[str, str]],
    timestamp: str,
    today: str,
    batch: str,
    dry_run: bool,
) -> tuple[str, str, bool] | None:
    """Create or update a topic note from raw topic/category/tag metadata."""

    display = yaml_scalar(name)
    if not display:
        return None
    slug = aliases["topics"].get(display.lower()) or slugify(display)
    path = DOMAIN_DIRS["topics"] / f"{slug}.md"
    if slug not in records["topics"]:
        body = f"# {display}\n\n## Coverage\n- {article_link}\n"
        frontmatter = [
            "type: entity", "subtype: topic", "domain: Topics", "status: active",
            f"displayName: {yaml_quote(display)}", "aliases:", f"  - {yaml_quote(display)}",
            "owner: Alex", f"created: {timestamp}", f"last_updated: {timestamp}",
            f"category: {yaml_quote('Imported article topic')}", "articleCount: 1",
            "tags:", '  - "#topic"',
        ]
        if not dry_run:
            dump_note(path, frontmatter, body)
        records["topics"][slug] = EntityRecord(slug, path, display, {})
        aliases["topics"][display.lower()] = slug
        append_log("topics", f"- {today} - Created [[{slug}|{display}]] from {batch}.", dry_run)
        return slug, display, True
    record = records["topics"][slug]
    if append_coverage("topics", record, article_link, timestamp, dry_run):
        append_log("topics", f"- {today} - Added coverage {article_link} to [[{slug}|{record.display}]].", dry_run)
    return slug, display, False


def update_existing_entity(
    domain: str,
    slug: str,
    article_link: str,
    records: dict[str, dict[str, EntityRecord]],
    timestamp: str,
    today: str,
    dry_run: bool,
) -> bool:
    """Backlink an already-known people/organisation/place entity to the article."""

    record = records[domain][slug]
    if append_coverage(domain, record, article_link, timestamp, dry_run):
        append_log(domain, f"- {today} - Added coverage {article_link} to [[{slug}|{record.display}]].", dry_run)
        return True
    return False


def first_sentence(body: str) -> str:
    """Derive a short summary from the source body without adding new facts."""

    clean = re.sub(r"\s+", " ", body).strip()
    clean = re.sub(r"^#.*?(?=[A-Z0-9])", "", clean).strip()
    if not clean:
        return "Summary unavailable in source item."
    match = re.search(r"(.{80,450}?[.!?])\s", clean)
    return match.group(1).strip() if match else clean[:450].strip()


def key_points(body: str) -> list[str]:
    """Extract up to three source-backed key points from the raw article body."""

    clean = re.sub(r"\s+", " ", body).strip()
    points = []
    for match in re.finditer(r"\(([ivx]+)\)\s*(.*?)(?=\s*\([ivx]+\)|$)", clean, flags=re.I):
        point = match.group(2).strip(" ;")
        if len(point) > 20:
            points.append(point[:350])
        if len(points) >= 3:
            break
    if not points:
        points = [p.strip()[:350] for p in re.split(r"(?<=[.!?])\s+", clean) if len(p.strip()) > 40][:3]
    return points or ["No further key points were available in the source item."]


def issue_tag_lines(source_tags: list[str]) -> str:
    """Preserve exact enriched issue-tag values in the compiled article body."""

    values = []
    seen = set()
    for raw in source_tags:
        value = re.sub(r"[\r\n]+", " ", str(raw)).strip()
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            values.append(value)
    return "\n".join(f"- {value}" for value in values) or "- None recorded"


def article_filename(frontmatter: dict[str, Any], raw_path: Path) -> str:
    """Build the compiled article filename from source ID and title."""

    source_id = yaml_scalar(canonical_field(frontmatter, "id", "sourceId", "articleId"))
    title = yaml_scalar(canonical_field(frontmatter, "title", "headline", "articleTitle")) or raw_path.stem
    if source_id:
        return f"{slugify(source_id.replace('/', '-'))}-{slugify(title)[:70]}.md"
    return raw_path.name


def infer_countries(search_text: str) -> list[str]:
    """Infer country mentions using a fixed dictionary, not model knowledge."""

    out = []
    seen = set()
    for country in sorted(COUNTRY_SEED, key=len, reverse=True):
        if country in seen:
            continue
        if re.search(r"\b" + re.escape(country) + r"\b", search_text):
            out.append(country)
            seen.add(country)
        if len(out) >= 8:
            break
    return out


def compile_one(
    raw_path: Path,
    month: str,
    records: dict[str, dict[str, EntityRecord]],
    aliases: dict[str, dict[str, str]],
    timestamp: str,
    today: str,
    batch: str,
    dry_run: bool,
) -> dict[str, int]:
    """Compile one raw intake file and cascade its entity backlinks.

    The output article uses the compiled article schema shape expected in
    ``entities/article``. Source prose is preserved under ``## Source Text``;
    summary/key points are extracted from that prose only. The raw input file is
    removed only after the compiled article note and cascade logs are written.
    """

    text = raw_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    title = yaml_scalar(canonical_field(frontmatter, "title", "headline", "articleTitle")) or raw_path.stem
    out_path = ARTICLE_ROOT / month / article_filename(frontmatter, raw_path)
    article_slug = out_path.stem
    article_link = wikilink(f"article/{month}/{article_slug}", title)
    metrics = defaultdict(int)

    outlet_names = yaml_list(canonical_field(frontmatter, "outlets", "outlet", "sourceOutlet")) or ["Unknown Outlet"]
    countries = yaml_list(canonical_field(frontmatter, "countries", "country"))
    topics = yaml_list(canonical_field(frontmatter, "topics", "topic", "subjects", "category"))
    source_tags = yaml_list(frontmatter.get("tags"))
    for tag in source_tags:
        cleaned = tag.strip("#")
        if cleaned and cleaned.lower() not in {"source", "article"} and cleaned not in topics:
            topics.append(cleaned.replace("-", " "))
    if not topics:
        topics = ["Uncategorised"]

    raw_search = " ".join([title, body, " ".join(source_tags)]).lower()
    if not countries:
        countries = infer_countries(raw_search)

    outlet_links = []
    for outlet in outlet_names:
        slug, display, was_created = ensure_outlet(outlet, article_link, records, aliases, timestamp, today, batch, dry_run)
        metrics["outlets_created" if was_created else "outlets_updated"] += 1
        outlet_links.append(wikilink(f"outlet/{slug}", display))

    country_links = []
    for country in countries:
        result = ensure_country(country, article_link, records, aliases, timestamp, today, batch, dry_run)
        if result:
            slug, display, was_created = result
            metrics["countries_created" if was_created else "countries_updated"] += 1
            country_links.append(wikilink(f"country/{slug}", display))

    topic_links = []
    seen_topics = set()
    for topic in topics[:12]:
        if topic.lower() in seen_topics:
            continue
        seen_topics.add(topic.lower())
        result = ensure_topic(topic, article_link, records, aliases, timestamp, today, batch, dry_run)
        if result:
            slug, display, was_created = result
            metrics["topics_created" if was_created else "topics_updated"] += 1
            topic_links.append(wikilink(f"topic/{slug}", display))

    related_links = []
    for domain in ["organisations", "people", "places"]:
        matches = []
        for name, slug in aliases[domain].items():
            if len(name) >= 4 and re.search(r"\b" + re.escape(name) + r"\b", raw_search):
                matches.append(slug)
        for slug in sorted(set(matches))[:15]:
            if update_existing_entity(domain, slug, article_link, records, timestamp, today, dry_run):
                metrics[f"{domain}_updated"] += 1
            related_links.append(wikilink(f"{DOMAIN_LINK_PREFIX[domain]}/{slug}", records[domain][slug].display))

    article_tags = ["#source"]
    sensitive_value = canonical_field(frontmatter, "sensitive", "restricted")
    if sensitive_value is True or str(sensitive_value).strip().lower() in {"1", "true", "yes"}:
        article_tags.append("#sensitive")

    source_url = yaml_scalar(canonical_field(frontmatter, "url", "sourceUrl", "link"))
    source_id = yaml_scalar(canonical_field(frontmatter, "id", "sourceId", "articleId")) or article_slug
    published = yaml_scalar(canonical_field(frontmatter, "published", "publishedDate", "date"))
    source_type = yaml_scalar(frontmatter.get("sourceType")) or "feed"

    article_frontmatter = [
        "type: source", "subtype: article", "domain: Sources", "status: active", "aliases: []",
        "owner: Alex", f"created: {timestamp}", f"last_updated: {timestamp}",
        f"sourceId: {yaml_quote(source_id)}", f"sourceUrl: {yaml_quote(source_url)}",
        f"sourceType: {yaml_quote(source_type)}", f"publishedDate: {yaml_quote(published)}",
        f"tone: {yaml_quote(frontmatter.get('tone'))}",
        f"toneSentiment: {yaml_quote(frontmatter.get('toneSentiment'))}",
        f"eventType: {yaml_quote(frontmatter.get('eventType'))}",
        f"coverageCount: {len(outlet_links)}", "tags:",
        *[f'  - "{tag}"' for tag in article_tags],
    ]
    related = []
    for link in country_links + topic_links + related_links:
        if link not in related:
            related.append(link)
    article_body = f"""# {title}

## Summary
{first_sentence(body)}

## Key Points
{chr(10).join(f"- {point}" for point in key_points(body))}

## Issue Tags
{issue_tag_lines(source_tags)}

## Covered By
{chr(10).join(f"- {link}" for link in outlet_links) or "- None recorded"}

## Related Entities
{chr(10).join(f"- {link}" for link in related) or "- None identified from source metadata"}

## AI Context
Compiled from the raw source item in `Inputs/articles/{month}/` during the {batch}. No live-web enrichment was used.

## Source Text
{body.strip()}
"""
    if not dry_run:
        dump_note(out_path, article_frontmatter, article_body)
        append_log(
            "article",
            f"- {today} - Compiled and cascaded [[article/{month}/{article_slug}|{title}]] "
            f"from Inputs/articles/{month}/{raw_path.name}.",
            dry_run,
        )
        raw_path.unlink()
    metrics["processed"] += 1
    return dict(metrics)


def rebuild_catalogs(dry_run: bool) -> list[str]:
    """Regenerate generated catalogs after a write run."""

    if dry_run:
        return []
    rebuilt = []
    for domain in CATALOG_DOMAINS:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_catalog.py"), domain], cwd=ROOT, check=True)
        rebuilt.append(domain)
    return rebuilt


def focused_validation(month: str) -> dict[str, int | list[str]]:
    """Check touched notes for hard YAML and wikilink failures.

    This is intentionally narrower than the vault-wide ``check_links.py`` scan.
    It covers the article month plus the entity domains this runner can touch,
    which keeps cascade validation bounded while still catching broken links and
    malformed frontmatter introduced by the run.
    """

    scan_dirs = [
        ARTICLE_ROOT / month,
        DOMAIN_DIRS["outlets"],
        DOMAIN_DIRS["countries"],
        DOMAIN_DIRS["topics"],
        DOMAIN_DIRS["organisations"],
        DOMAIN_DIRS["people"],
        DOMAIN_DIRS["places"],
    ]
    notes = [
        path
        for directory in scan_dirs
        if directory.exists()
        for path in directory.rglob("*.md")
        if path.name not in SYSTEM_FILES
    ]
    valid = set()
    for path in (ROOT / "entities").rglob("*.md"):
        if path.name == ".DS_Store":
            continue
        rel = path.relative_to(ROOT / "entities").with_suffix("").as_posix()
        valid.add(rel)
        valid.add(path.stem)

    errors = []
    links_checked = 0
    for path in notes:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            end = text.find("\n---", 4)
            if end == -1:
                errors.append(f"{path.relative_to(ROOT)} :: frontmatter not closed")
            else:
                try:
                    yaml.safe_load(text[4:end])
                except Exception as exc:
                    errors.append(f"{path.relative_to(ROOT)} :: YAML: {exc}")
        for match in re.finditer(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]", text):
            links_checked += 1
            target = match.group(1).strip()
            if target not in valid:
                errors.append(f"{path.relative_to(ROOT)} :: broken wikilink: {target}")
                if len(errors) > 100:
                    break
        if len(errors) > 100:
            break
    return {
        "notes_scanned": len(notes),
        "wikilinks_checked": links_checked,
        "errors": len(errors),
        "error_samples": errors[:30],
    }


def count_months() -> dict[str, tuple[int, int]]:
    """Count cascaded and remaining input articles for every visible month."""

    months = sorted(
        {
            path.name
            for path in list(INPUT_ROOT.glob("????-??")) + list(ARTICLE_ROOT.glob("????-??"))
            if path.is_dir()
        }
    )
    counts = {}
    for month in months:
        cascaded = len(list((ARTICLE_ROOT / month).glob("*.md"))) if (ARTICLE_ROOT / month).exists() else 0
        inputs = len(list((INPUT_ROOT / month).glob("*.md"))) if (INPUT_ROOT / month).exists() else 0
        counts[month] = (cascaded, inputs)
    return counts


def update_article_status(month: str, processed_count: int, dry_run: bool) -> dict[str, int]:
    """Refresh the article-domain cascade status table in ``index.md``."""

    counts = count_months()
    cascaded_total = sum(cascaded for cascaded, _ in counts.values())
    input_total = sum(inputs for _, inputs in counts.values())
    total = cascaded_total + input_total
    if dry_run:
        return {"cascaded": cascaded_total, "inputs": input_total, "total": total}

    index_path = ARTICLE_ROOT / "index.md"
    text = index_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for row_month, (cascaded, inputs) in counts.items():
        row_total = cascaded + inputs
        pct = (cascaded / row_total * 100) if row_total else 0.0
        rows.append(
            f"| {row_month} | {cascaded:,} | {inputs:,} | {row_total:,} | {pct:.1f}% |"
        )
    pct_total = (cascaded_total / total * 100) if total else 0.0
    rows.append(f"| **Total** | **{cascaded_total:,}** | **{input_total:,}** | **{total:,}** | **{pct_total:.1f}%** |")
    table = (
        "| Month | Cascaded | Inputs remaining | Total | % cascaded |\n"
        "|---|---:|---:|---:|---:|\n"
        + "\n".join(rows)
    )
    text = re.sub(r"\*\*Last counted:\*\*.*", f"**Last counted:** {today} ({processed_count:,}-article full-folder batch from `Inputs/articles/{month}/`; see note below)", text, count=1)
    text = re.sub(
        r"\| Month \| Cascaded \| Inputs remaining \| Total \| % cascaded \|\n"
        r"\|---\|---:\|---:\|---:\|---:\|\n"
        r"(?:\|.*\|\n?)+",
        table + "\n\n",
        text,
        count=1,
    )
    note = f"A full-folder batch of {processed_count:,} files from `Inputs/articles/{month}/` was compiled/cascaded on {today}; the folder is now empty and the {month} row is fully cascaded."
    marker = "Note:"
    if note not in text and marker in text:
        text = text.replace(marker, marker + " " + note + " ", 1)
    index_path.write_text(text, encoding="utf-8")
    return {"cascaded": cascaded_total, "inputs": input_total, "total": total}


def run_batch(args: argparse.Namespace) -> int:
    """Resolve the requested input folder and run the timed cascade batch."""

    if args.input_dir:
        input_dir = Path(args.input_dir)
        if not input_dir.is_absolute():
            input_dir = ROOT / input_dir
        month = input_dir.name
    else:
        month = args.month
        input_dir = INPUT_ROOT / month
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise SystemExit(f"Input directory must end in YYYY-MM, got {month!r}")
    if not input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    raw_files = sorted(path for path in input_dir.glob("*.md") if path.name != ".DS_Store")
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")
    batch = args.batch_label or f"{month} full-folder cascade batch"
    print(f"Input folder: {input_dir.relative_to(ROOT)}")
    print(f"Article files found: {len(raw_files)}")
    if not raw_files:
        print("No articles to process.")
        return 0

    records, aliases = load_entities()
    aggregate = defaultdict(int)
    status = "ok"
    errors: list[dict[str, str]] = []
    notes = f"Full-folder cascade from Inputs/articles/{month}."
    with RunLogger("ingest_cascade", trigger="manual", notes=notes, metadata={"month": month, "dryRun": args.dry_run}) as run:
        try:
            with run.stage("compile_cascade", article_count=len(raw_files), file_count=len(raw_files)):
                for raw_path in raw_files:
                    for key, value in compile_one(raw_path, month, records, aliases, timestamp, today, batch, args.dry_run).items():
                        aggregate[key] += value
            rebuilt = rebuild_catalogs(args.dry_run)
            validation = {"notes_scanned": 0, "wikilinks_checked": 0, "errors": 0, "error_samples": []}
            if not args.dry_run:
                with run.stage("focused_validation", file_count=0):
                    validation = focused_validation(month)
                if validation["errors"]:
                    status = "failed"
                    errors.extend({"message": sample} for sample in validation["error_samples"])
            status_counts = update_article_status(month, int(aggregate["processed"]), args.dry_run)
            run.set_article_metrics(
                inputCount=len(raw_files),
                processedCount=int(aggregate["processed"]),
                createdCount=int(aggregate["processed"]),
                failedCount=0 if status == "ok" else int(validation["errors"]),
            )
            run.set_file_metrics(scannedCount=int(validation["notes_scanned"]))
            run.add_output("catalogsRebuilt", rebuilt)
            run.add_output("focusedValidation", validation)
            run.add_output("entityUpdates", dict(aggregate))
            run.add_output("statusCounts", status_counts)
            if status != "ok":
                for error in errors:
                    run.add_error(error["message"])
        except Exception as exc:
            run.add_error(str(exc), type=type(exc).__name__)
            raise

    print(f"Processed: {aggregate['processed']}")
    for key in sorted(k for k in aggregate if k != "processed"):
        print(f"{key}: {aggregate[key]}")
    if not args.dry_run:
        remaining = len(list(input_dir.glob("*.md"))) if input_dir.exists() else 0
        article_count = len(list((ARTICLE_ROOT / month).glob("*.md")))
        print(f"Inputs remaining: {remaining}")
        print(f"Compiled article notes in {month}: {article_count}")
        print(f"Focused validation errors: {validation['errors']}")
    print(f"Receipt: {run.path.relative_to(ROOT) if run.path else '(not written)'}")
    return 1 if status != "ok" else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--month", help="Month folder under Inputs/articles, e.g. 2026-07.")
    group.add_argument("--input-dir", help="Explicit input folder ending in YYYY-MM.")
    parser.add_argument("--batch-label", help="Human-readable batch label for notes/logs.")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without writing notes or moving inputs.")
    args = parser.parse_args()
    return run_batch(args)


if __name__ == "__main__":
    raise SystemExit(main())
