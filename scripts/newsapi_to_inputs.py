#!/usr/bin/env python3
"""Preserve NewsAPI crawler evidence and derive schema-valid Markdown intake notes.

The source JSON is evidence and is copied byte-for-byte under ``raw/newsapi/`` on a write run.
Generated notes contain only deterministic source mappings; topic, tone sentiment, issue tags and
other judgment fields remain blank until ``enrich_radar_inputs.py`` accepts them.

The source may be a crawler JSON response or a directory of loose Markdown exports whose
frontmatter embeds ``rawNewsApiResponse``. Default mode is a dry run. Pass ``--write`` to
preserve the evidence and create canonical notes. ``--output-root`` supports an isolated
working set; ``--include-compiled`` admits already-cascaded records to that working set for
UAT preparation without making them eligible for a second Wiki cascade.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from language_support import normalize_language

try:
    import yaml
except ImportError:
    print("This script requires PyYAML. Install it with: pip3 install pyyaml", file=sys.stderr)
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "raw" / "newsapi"
INPUT_ROOT = ROOT / "Inputs" / "articles"
ARTICLE_ROOT = ROOT / "entities" / "article"


class NewsApiInputError(RuntimeError):
    """A source-shape or preservation failure that blocks conversion."""


def slugify(value: Any, max_len: int = 70) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text[:max_len].rstrip("-") or "untitled"


def yaml_quote(value: Any) -> str:
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def yaml_flow(values: list[Any]) -> str:
    clean: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            clean.append(yaml_quote(item))
    return "[" + ", ".join(clean) + "]"


def english_label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("eng") or next(iter(value.values()), "")).strip()
    return str(value or "").strip()


def article_records(payload: Any) -> list[dict[str, Any]]:
    """Extract article result objects from the NewsAPI response envelope."""

    blocks = payload if isinstance(payload, list) else [payload]
    records: list[dict[str, Any]] = []
    for block_index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            raise NewsApiInputError(f"top-level item {block_index} is not an object")
        if isinstance(block.get("articles"), dict):
            values = block["articles"].get("results")
        elif isinstance(block.get("results"), list):
            values = block["results"]
        else:
            values = [block] if block.get("uri") else None
        if not isinstance(values, list):
            raise NewsApiInputError(f"top-level item {block_index} has no articles.results list")
        for record_index, record in enumerate(values, start=1):
            if not isinstance(record, dict):
                raise NewsApiInputError(
                    f"top-level item {block_index} article {record_index} is not an object"
                )
            records.append(record)
    return records


def published_datetime(record: dict[str, Any]) -> str:
    value = record.get("dateTimePub") or record.get("dateTime")
    if not value:
        raise NewsApiInputError("missing dateTimePub/dateTime")
    try:
        dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise NewsApiInputError(f"invalid publication datetime: {value!r}") from exc
    return str(value)


def clean_working_body(value: Any) -> str:
    """Remove only deterministic extraction debris from the generated working copy."""

    body = str(value or "").strip()
    body = re.sub(r"(?:\n\s*)+Tags:\s*$", "", body, flags=re.IGNORECASE).rstrip()
    return body


def normalize_embedded_body(value: Any) -> str:
    """Normalize crawler-export escape sequences in a derived working copy only."""

    body = str(value or "").replace("\\r\\n", "\n").replace("\\n", "\n")
    return clean_working_body(body)


def source_country(record: dict[str, Any]) -> str:
    source = record.get("source") or {}
    location = source.get("location") or {}
    country = location.get("country") or {}
    return english_label(country.get("label"))


def target_for(record: dict[str, Any]) -> tuple[str, str]:
    article_id = str(record.get("uri") or "").strip()
    title = str(record.get("title") or "").strip()
    if not article_id:
        raise NewsApiInputError("missing article uri")
    if not title:
        raise NewsApiInputError(f"article {article_id} is missing title")
    month = published_datetime(record)[:7]
    return month, f"{slugify(article_id, 120)}-{slugify(title)}.md"


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("uri", "title", "url", "source"):
        if not record.get(field):
            errors.append(f"missing {field}")
    try:
        published_datetime(record)
    except NewsApiInputError as exc:
        errors.append(str(exc))
    body = clean_working_body(record.get("body"))
    if len(body) < 100:
        errors.append("article body has fewer than 100 meaningful characters")
    source = record.get("source") or {}
    if not source.get("title") or not source.get("uri"):
        errors.append("publisher title/domain is missing")
    if not source_country(record):
        errors.append("publisher country candidate is missing")
    if normalize_language(record.get("lang") or record.get("language")) == "und":
        errors.append("language is missing or unsupported; review to eng or ind")
    return errors


def render_note(record: dict[str, Any]) -> str:
    article_id = str(record.get("uri") or "").strip()
    title = str(record.get("title") or "").strip()
    source = record.get("source") or {}
    outlet = str(source.get("title") or source.get("uri") or "").strip()
    body = clean_working_body(record.get("body"))
    lines = [
        "---",
        f"articleId: {yaml_quote(article_id)}",
        f"articleTitle: {yaml_quote(title)}",
        f"publishedDate: {yaml_quote(published_datetime(record))}",
        f"language: {yaml_quote(normalize_language(record.get('lang') or record.get('language')))}",
        "category: ''",
        "topic: ''",
        "tone: ''",
        "toneSentiment: ''",
        "eventType: ''",
        "tags: []",
        f"outlets: {yaml_flow([slugify(outlet)])}",
        f"countries: {yaml_flow([source_country(record)])}",
        "coverageCount: 1",
        "mediaCount: 0",
        "sourceType: 'crawl'",
        f"url: {yaml_quote(record.get('url'))}",
        "---",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def split_markdown_note(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise NewsApiInputError("embedded Markdown has no YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise NewsApiInputError("embedded Markdown has unterminated YAML frontmatter")
    try:
        metadata = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        raise NewsApiInputError(f"embedded Markdown YAML is invalid: {exc}") from exc
    if not isinstance(metadata, dict):
        raise NewsApiInputError("embedded Markdown frontmatter must be an object")
    return metadata, text[end + 4 :].lstrip("\n")


def embedded_record(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Extract and cross-check an embedded NewsAPI record from one Markdown export."""

    metadata, source_body = split_markdown_note(path.read_text(encoding="utf-8"))
    raw_record = metadata.get("rawNewsApiResponse")
    if isinstance(raw_record, str):
        try:
            raw_record = json.loads(raw_record)
        except json.JSONDecodeError as exc:
            raise NewsApiInputError(f"rawNewsApiResponse is invalid JSON: {exc}") from exc
    if not isinstance(raw_record, dict):
        raise NewsApiInputError("rawNewsApiResponse is missing or is not an object")

    errors: list[str] = []
    comparisons = {
        "article ID": (metadata.get("articleId"), raw_record.get("uri")),
        "title": (metadata.get("articleTitle"), raw_record.get("title")),
        "URL": (metadata.get("url"), raw_record.get("url")),
        "publication datetime": (metadata.get("publishedDate"), raw_record.get("dateTimePub") or raw_record.get("dateTime")),
    }
    for label, (outer, inner) in comparisons.items():
        if str(outer or "").strip() != str(inner or "").strip():
            errors.append(f"outer/inner {label} mismatch")

    outer_body = normalize_embedded_body(source_body)
    inner_body = normalize_embedded_body(raw_record.get("body"))
    if outer_body != inner_body:
        errors.append("outer/inner body mismatch")
    raw_record = dict(raw_record)
    raw_record["body"] = inner_body
    return raw_record, errors


def compiled_identity_index(article_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Index compiled articles by source ID and normalized source URL."""

    by_id: dict[str, str] = {}
    by_url: dict[str, str] = {}
    for path in article_root.glob("*/*.md"):
        if path.name in {"index.md", "catalog.md", "log.md", "_template.md"}:
            continue
        try:
            metadata, _ = split_markdown_note(path.read_text(encoding="utf-8"))
        except (OSError, NewsApiInputError):
            continue
        source_id = str(metadata.get("sourceId") or "").strip()
        source_url = str(metadata.get("sourceUrl") or "").strip().rstrip("/")
        if source_id:
            by_id[source_id] = display_path(path)
        if source_url:
            by_url[source_url] = display_path(path)
    return by_id, by_url


def truthy(value: Any) -> bool:
    return value is True or str(value or "").strip().lower() in {"1", "true", "yes"}


def preserve_bytes(source: Path, target: Path, raw: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != raw:
        raise NewsApiInputError(f"raw preservation collision: {target}")
    if not target.exists():
        shutil.copyfile(source, target)


def convert_embedded_directory(
    source_dir: Path,
    output_root: Path,
    write: bool = False,
    include_compiled: bool = False,
) -> dict[str, Any]:
    """Preserve loose Markdown exports and build a canonical isolated working set."""

    paths = sorted(path for path in source_dir.glob("*.md") if path.is_file())
    if not paths:
        raise NewsApiInputError(f"no loose Markdown files found in {source_dir}")
    compiled_ids, compiled_urls = compiled_identity_index(ARTICLE_ROOT)
    results: list[dict[str, Any]] = []
    day = dt.datetime.now().astimezone().date().isoformat()

    for path in paths:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", path.name).strip("-")
        markdown_target = RAW_ROOT / day / "embedded-markdown" / f"{digest[:12]}-{safe_name}"
        response_target = RAW_ROOT / day / "embedded-responses" / f"{digest[:12]}-{path.stem}.json"
        errors: list[str] = []
        record: dict[str, Any] = {}
        try:
            record, crosscheck_errors = embedded_record(path)
            errors.extend(crosscheck_errors)
            errors.extend(validate_record(record))
        except (OSError, NewsApiInputError) as exc:
            errors.append(str(exc))

        article_id = str(record.get("uri") or "").strip()
        url = str(record.get("url") or "").strip().rstrip("/")
        already_compiled = bool(
            (article_id and article_id in compiled_ids) or (url and url in compiled_urls)
        )
        declared_duplicate = truthy(record.get("isDuplicate"))
        destination: Path | None = None
        if record:
            try:
                month, filename = target_for(record)
                destination = output_root / month / filename
                if destination.exists():
                    errors.append("working-set destination already exists")
            except NewsApiInputError as exc:
                errors.append(str(exc))

        if declared_duplicate:
            status = "excluded_duplicate"
        elif already_compiled and not include_compiled:
            status = "excluded_existing"
        elif errors:
            status = "blocked"
        elif already_compiled:
            status = "planned_uat_only"
        else:
            status = "planned"

        if write:
            preserve_bytes(path, markdown_target, raw)
            if record:
                response_bytes = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                response_target.parent.mkdir(parents=True, exist_ok=True)
                if response_target.exists() and response_target.read_bytes() != response_bytes:
                    raise NewsApiInputError(f"raw response preservation collision: {response_target}")
                if not response_target.exists():
                    response_target.write_bytes(response_bytes)
            if status in {"planned", "planned_uat_only"} and destination:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(render_note(record), encoding="utf-8")

        results.append({
            "articleId": article_id,
            "source": display_path(path),
            "destination": display_path(destination) if destination else None,
            "status": status,
            "alreadyCompiled": already_compiled,
            "declaredDuplicate": declared_duplicate,
            "compiledMatch": compiled_ids.get(article_id) or compiled_urls.get(url),
            "sha256": digest,
            "rawMarkdownPath": display_path(markdown_target),
            "rawResponsePath": display_path(response_target) if record else None,
            "errors": sorted(set(errors)),
        })

    return {
        "mode": "write" if write else "dry-run",
        "source": display_path(source_dir),
        "outputRoot": display_path(output_root),
        "articles": len(paths),
        "planned": sum(item["status"] == "planned" for item in results),
        "plannedUatOnly": sum(item["status"] == "planned_uat_only" for item in results),
        "excludedDuplicate": sum(item["status"] == "excluded_duplicate" for item in results),
        "excludedExisting": sum(item["status"] == "excluded_existing" for item in results),
        "blocked": sum(item["status"] == "blocked" for item in results),
        "results": results,
    }


def preservation_target(source: Path, digest: str) -> Path:
    day = dt.datetime.now().astimezone().date().isoformat()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", source.name).strip("-") or "newsapi.json"
    return RAW_ROOT / day / f"{digest[:12]}-{safe_name}"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def convert(source: Path, write: bool = False) -> dict[str, Any]:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NewsApiInputError(f"invalid JSON: {exc}") from exc
    records = article_records(payload)
    uri_counts = Counter(str(record.get("uri") or "") for record in records)
    url_counts = Counter(str(record.get("url") or "") for record in records)
    results: list[dict[str, Any]] = []
    raw_target = preservation_target(source, digest)

    # Preserve evidence before deriving any working intake notes.
    if write:
        raw_target.parent.mkdir(parents=True, exist_ok=True)
        if raw_target.exists() and raw_target.read_bytes() != raw:
            raise NewsApiInputError(f"raw preservation collision: {raw_target}")
        if not raw_target.exists():
            shutil.copyfile(source, raw_target)

    for record in records:
        article_id = str(record.get("uri") or "").strip()
        errors = validate_record(record)
        if article_id and uri_counts[article_id] > 1:
            errors.append("duplicate article uri in source payload")
        url = str(record.get("url") or "").strip()
        if url and url_counts[url] > 1:
            errors.append("duplicate article url in source payload")
        destination = None
        try:
            month, filename = target_for(record)
            destination = INPUT_ROOT / month / filename
            compiled = ARTICLE_ROOT / month / filename
            if destination.exists():
                errors.append("input destination already exists")
            if compiled.exists():
                errors.append("compiled article already exists")
        except NewsApiInputError as exc:
            errors.append(str(exc))

        item = {
            "articleId": article_id,
            "destination": display_path(destination) if destination else None,
            "status": "blocked" if errors else "planned",
            "errors": sorted(set(errors)),
        }
        results.append(item)
        if write and not errors and destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render_note(record), encoding="utf-8")

    return {
        "mode": "write" if write else "dry-run",
        "source": str(source),
        "sha256": digest,
        "rawPreservationPath": display_path(raw_target),
        "articles": len(records),
        "planned": sum(item["status"] == "planned" for item in results),
        "blocked": sum(item["status"] == "blocked" for item in results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="NewsAPI JSON response file or loose-Markdown directory")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-root", type=Path, default=INPUT_ROOT)
    parser.add_argument(
        "--include-compiled", action="store_true",
        help="write already-compiled records into a custom working set for UAT only",
    )
    args = parser.parse_args(argv)
    try:
        source = args.source.resolve()
        if source.is_dir():
            result = convert_embedded_directory(
                source,
                args.output_root.resolve(),
                args.write,
                args.include_compiled,
            )
        else:
            result = convert(source, args.write)
    except (OSError, NewsApiInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
