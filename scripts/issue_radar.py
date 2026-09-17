#!/usr/bin/env python3
"""Early-warning issue radar over canonical MySQL tables or a verified staging bundle.

The radar reads articles, article_tags, and article_coverage using a read-only,
consistent-snapshot transaction. UAT is the safe default; production requires
an explicit ``--source production`` selection. It never writes to MySQL or the
Markdown vault.

For explicitly database-free validation, ``--bundle-dir`` reads the canonical-shaped
TSV files produced by ``stage_enriched_radar_inputs.py``. The bundle must be verified
separately before use; radar scoring and thresholds are identical in both modes.

Authentication is delegated to the MySQL client. Prefer ``--defaults-file`` or
``--login-path`` with a SELECT-only account. Environment variables are also
supported; see ``--help``. Any ``ISSUE_RADAR_MYSQL_*`` variable, or
``ISSUE_RADAR_MYSQL_DEFAULTS_FILE``/``ISSUE_RADAR_MYSQL_LOGIN_PATH`` pointing at
an external option file, may also be placed in the Git-ignored ``.env.local``
(see ``scripts/local_env.py``) instead of exported in the shell. A real shell
export always takes precedence over ``.env.local``.
"""

import argparse
import collections
import csv
import datetime
import getpass
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from local_env import load_local_env  # noqa: E402


INSTITUTIONAL = {
    "Government", "Parliament", "Election", "Political Party", "Public Policy",
    "National Security", "Civil Society",
}
STOP = {
    "security", "indonesia", "indonesian", "minister", "government",
    "parliament", "politics", "political", "party", "election", "policy",
    "asean", "china", "us", "usa", "united states", "conflict",
}
GENERIC_FRACTION = 0.03
MIN_ARTICLES, MIN_WEEKS = 8, 3
WINDOW = 28

WEIGHTS = dict(accel=0.25, breadth=0.20, inst=0.25, recur=0.15, unfac=0.10, opin=0.05)
TIERS = [("HOT", 0.60, 8), ("WARM", 0.40, 4), ("WATCH", 0.25, 2)]
IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")

SOURCE_DEFAULTS = {
    "uat": ("MSM_dataset_UAT", "UAT_"),
    "production": ("MSM_dataset", ""),
}


class RadarError(RuntimeError):
    """A user-facing radar configuration or data-source error."""


def monday(day):
    return day - datetime.timedelta(days=day.weekday())


def safe_identifier(value, label, allow_empty=False):
    if allow_empty and value == "":
        return value
    if not value or not IDENTIFIER.fullmatch(value):
        raise RadarError(f"invalid {label}: {value!r}")
    return value


def product_query(database, prefix):
    """Return the single read-only query used for both UAT and production."""
    database = safe_identifier(database, "database")
    prefix = safe_identifier(prefix, "table prefix", allow_empty=True)
    articles = f"`{database}`.`{prefix}articles`"
    tags = f"`{database}`.`{prefix}article_tags`"
    coverage = f"`{database}`.`{prefix}article_coverage`"
    return f"""
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;
SELECT JSON_OBJECT(
  'article_id', a.article_id,
  'title', COALESCE(a.article_title, ''),
  'published_date', DATE_FORMAT(a.published_date, '%Y-%m-%dT%H:%i:%s'),
  'category', COALESCE(a.category, ''),
  'tone', COALESCE(a.tone, ''),
  'event_type', COALESCE(a.event_type, ''),
  'tags', COALESCE(t.tags, JSON_ARRAY()),
  'outlets', COALESCE(c.outlets, JSON_ARRAY()),
  'countries', COALESCE(c.countries, JSON_ARRAY())
)
FROM {articles} a
LEFT JOIN (
  SELECT article_id, JSON_ARRAYAGG(tag) AS tags
  FROM {tags}
  GROUP BY article_id
) t ON t.article_id = a.article_id
LEFT JOIN (
  SELECT article_id,
         JSON_ARRAYAGG(display_name) AS outlets,
         JSON_ARRAYAGG(country) AS countries
  FROM {coverage}
  GROUP BY article_id
) c ON c.article_id = a.article_id
WHERE a.published_date IS NOT NULL
  AND (a.article_status = 'A' OR a.article_status IS NULL)
ORDER BY a.article_id;
COMMIT;
"""


def product_tags_query(database, prefix):
    """Return a read-only inventory query for every distinct product tag."""
    database = safe_identifier(database, "database")
    prefix = safe_identifier(prefix, "table prefix", allow_empty=True)
    tags = f"`{database}`.`{prefix}article_tags`"
    return f"""
SET SESSION TRANSACTION READ ONLY;
START TRANSACTION WITH CONSISTENT SNAPSHOT;
SELECT JSON_OBJECT('source_tag', MIN(tag), 'article_count', COUNT(DISTINCT article_id))
FROM {tags}
GROUP BY BINARY tag
ORDER BY BINARY MIN(tag);
COMMIT;
"""


def mysql_command(args):
    command = [args.mysql_program]
    if args.defaults_file:
        command.append(f"--defaults-extra-file={args.defaults_file}")
    if args.login_path:
        command.append(f"--login-path={args.login_path}")
    command.extend(["--batch", "--raw", "--skip-column-names", "--default-character-set=utf8mb4"])
    if args.mysql_host:
        command.extend(["--host", args.mysql_host])
    if args.mysql_port:
        command.extend(["--port", str(args.mysql_port)])
    if args.mysql_user:
        command.extend(["--user", args.mysql_user])
    if args.ssl_mode:
        command.append(f"--ssl-mode={args.ssl_mode}")
    return command


def parse_product_rows(output):
    articles = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            published = datetime.datetime.fromisoformat(row["published_date"]).date()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RadarError(f"invalid MySQL row {line_number}: {exc}") from exc

        def clean_set(values):
            return {str(value).strip() for value in (values or []) if value is not None and str(value).strip()}

        articles.append({
            "id": int(row["article_id"]),
            "title": row.get("title") or "",
            "date": published,
            "cat": row.get("category") or "",
            "tags": {value.lower() for value in clean_set(row.get("tags"))},
            "outlets": clean_set(row.get("outlets")),
            "countries": clean_set(row.get("countries")),
            "unfac": row.get("event_type") == "Unfacilitated",
            "opin": row.get("tone") == "Opinionated",
        })
    if not articles:
        raise RadarError("the product-table query returned no articles")
    return articles


def mysql_tsv_value(value):
    """Decode one field written by stage_enriched_radar_inputs.mysql_tsv."""

    if value == r"\N":
        return None
    mapping = {"0": "\0", "t": "\t", "n": "\n", "r": "\r", "Z": "\x1a", "\\": "\\"}
    output = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            output.append(mapping.get(value[index + 1], value[index + 1]))
            index += 2
        else:
            output.append(value[index])
            index += 1
    return "".join(output)


def bundle_rows(path, expected_columns):
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = []
            for line_number, row in enumerate(csv.reader(handle, delimiter="\t"), start=1):
                if len(row) != expected_columns:
                    raise RadarError(
                        f"invalid bundle row {path.name}:{line_number}; "
                        f"expected {expected_columns} columns, found {len(row)}"
                    )
                rows.append([mysql_tsv_value(value) for value in row])
            return rows
    except FileNotFoundError as exc:
        raise RadarError(f"bundle file not found: {path}") from exc


def load_bundle_articles(bundle_dir):
    """Load radar inputs from an immutable UAT-shaped file bundle without MySQL."""

    bundle = Path(bundle_dir).expanduser().resolve()
    article_rows = bundle_rows(bundle / "articles.tsv", 32)
    tag_rows = bundle_rows(bundle / "article_tags.tsv", 6)
    coverage_rows = bundle_rows(bundle / "article_coverage.tsv", 11)

    tags = collections.defaultdict(set)
    outlets = collections.defaultdict(set)
    countries = collections.defaultdict(set)
    for row in tag_rows:
        tags[row[1]].add(str(row[4]).strip().lower())
    for row in coverage_rows:
        if row[6]:
            outlets[row[1]].add(str(row[6]).strip())
        if row[7]:
            countries[row[1]].add(str(row[7]).strip())

    articles = []
    for row in article_rows:
        if row[31] != "ready":
            continue
        try:
            published = datetime.datetime.fromisoformat(str(row[21])).date()
            article_id = int(row[6])
        except (TypeError, ValueError) as exc:
            raise RadarError(f"invalid article row for staging ID {row[1]}: {exc}") from exc
        articles.append({
            "id": article_id,
            "title": row[7] or "",
            "date": published,
            "cat": row[11] or "",
            "tags": tags[row[1]],
            "outlets": outlets[row[1]],
            "countries": countries[row[1]],
            "unfac": row[14] == "Unfacilitated",
            "opin": row[12] == "Opinionated",
        })
    if not articles:
        raise RadarError("the file bundle contains no ready articles")
    return articles, f"file bundle {bundle}"


def resolve_source(args):
    database, prefix = SOURCE_DEFAULTS[args.source]
    return args.database or database, args.table_prefix if args.table_prefix is not None else prefix


def run_mysql(args, query):
    environment = os.environ.copy()
    password = (
        getpass.getpass("MySQL password: ")
        if args.prompt_password else os.environ.get("ISSUE_RADAR_MYSQL_PASSWORD")
    )
    if password:
        environment["MYSQL_PWD"] = password
    try:
        result = subprocess.run(
            mysql_command(args), input=query, text=True, capture_output=True,
            env=environment, check=False,
        )
    except FileNotFoundError as exc:
        raise RadarError(f"MySQL client not found: {args.mysql_program}") from exc
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown MySQL error"
        raise RadarError(f"product-table query failed: {detail}")
    return result.stdout


def load_articles(args):
    database, prefix = resolve_source(args)
    output = run_mysql(args, product_query(database, prefix))
    return parse_product_rows(output), database, prefix


def export_tags(args, destination):
    database, prefix = resolve_source(args)
    output = run_mysql(args, product_tags_query(database, prefix))
    rows = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            source_tag = row["source_tag"]
            rows.append((source_tag, source_tag.strip().lower(), int(row["article_count"])))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RadarError(f"invalid tag-inventory row {line_number}: {exc}") from exc
    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_tag", "radar_tag", "article_count"])
        writer.writerows(rows)
    print(f"Exported {len(rows)} distinct tags from {database}.{prefix}article_tags to {path}")


def candidates(articles, asof):
    """Return tag candidates using only records visible at the evaluation date."""
    eligible = [article for article in articles if article["date"] <= asof]
    frequency = collections.Counter(tag for article in eligible for tag in article["tags"])
    cap = len(eligible) * GENERIC_FRACTION
    output = {}
    for tag, count in frequency.items():
        if count < MIN_ARTICLES or count > cap or tag in STOP or len(tag) < 3:
            continue
        selected = [article for article in eligible if tag in article["tags"]]
        if len({monday(article["date"]) for article in selected}) >= MIN_WEEKS:
            output[tag] = selected
    return output


def waves(dates, asof):
    """Count active-week runs separated by at least two silent weeks."""
    weeks = sorted({monday(day) for day in dates if day <= asof})
    if not weeks:
        return 0
    count, previous = 1, weeks[0]
    for week in weeks[1:]:
        if (week - previous).days > 14:
            count += 1
        previous = week
    return count


def score_issue(selected, asof):
    history = [article for article in selected if article["date"] <= asof]
    if not history:
        return None
    recent_start = asof - datetime.timedelta(days=WINDOW)
    prior_start = asof - datetime.timedelta(days=2 * WINDOW)
    recent = [article for article in history if article["date"] > recent_start]
    prior = [article for article in history if prior_start < article["date"] <= recent_start]
    before = [article for article in history if article["date"] <= recent_start]
    if not recent:
        return None

    recent_volume, prior_volume = len(recent), len(prior)
    acceleration = min(1.0, (recent_volume / max(prior_volume, 1)) / 4.0) if recent_volume >= 3 else 0.0

    seen_outlets = set().union(*(article["outlets"] for article in before)) if before else set()
    seen_countries = set().union(*(article["countries"] for article in before)) if before else set()
    new_outlets = set().union(*(article["outlets"] for article in recent)) - seen_outlets
    new_countries = set().union(*(article["countries"] for article in recent)) - seen_countries
    breadth = min(1.0, len(new_outlets) / 10.0 + len(new_countries) / 4.0) if before else 0.3

    institutional_recent = sum(article["cat"] in INSTITUTIONAL for article in recent) / recent_volume
    institutional_before = (
        sum(article["cat"] in INSTITUTIONAL for article in before) / len(before)
        if before else 0.0
    )
    institutional = min(
        1.0,
        institutional_recent * 0.6
        + max(0.0, institutional_recent - institutional_before) * 0.8,
    )

    wave_count = waves([article["date"] for article in history], asof)
    recurrence = min(1.0, (wave_count - 1) / 3.0)
    unfacilitated = sum(article["unfac"] for article in recent) / recent_volume
    opinionated = sum(article["opin"] for article in recent) / recent_volume

    parts = {
        "accel": acceleration, "breadth": breadth, "inst": institutional,
        "recur": recurrence, "unfac": unfacilitated, "opin": opinionated,
    }
    score = sum(WEIGHTS[name] * value for name, value in parts.items())
    tier = next(
        (name for name, minimum, volume in TIERS if score >= minimum and recent_volume >= volume),
        None,
    )
    reasons = []
    if acceleration > 0.3:
        reasons.append(f"volume {prior_volume}->{recent_volume} over two {WINDOW}d windows")
    if new_outlets:
        reasons.append(f"{len(new_outlets)} never-seen outlets")
    if new_countries:
        reasons.append(f"new countries: {', '.join(sorted(new_countries)[:4])}")
    if institutional_recent > 0.3:
        reasons.append(f"{institutional_recent:.0%} of recent coverage in institutional categories")
    if institutional_recent - institutional_before > 0.2 and before:
        reasons.append(f"institutional share rose {institutional_before:.0%}->{institutional_recent:.0%}")
    if wave_count >= 2:
        reasons.append(f"{wave_count} distinct coverage waves (recurring, not dying)")
    if unfacilitated > 0.7:
        reasons.append(f"{unfacilitated:.0%} unfacilitated (story running on its own)")
    if opinionated > 0.15:
        reasons.append(f"{opinionated:.0%} opinionated pieces")
    return {"score": score, "tier": tier, "vol": recent_volume, "parts": parts, "why": reasons}


def series(selected, asof):
    weekly = collections.defaultdict(lambda: [0, set(), set()])
    for article in selected:
        if article["date"] > asof:
            continue
        bucket = weekly[monday(article["date"]).isoformat()]
        bucket[0] += 1
        bucket[1] |= article["outlets"]
        bucket[2] |= article["countries"]
    return {week: (count, len(outlets), len(countries)) for week, (count, outlets, countries) in sorted(weekly.items())}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Read-only issue radar over canonical MySQL tables or a verified file bundle",
        epilog=(
            "Connection values may also come from ISSUE_RADAR_MYSQL_HOST, _PORT, _USER, "
            "_PASSWORD, _DEFAULTS_FILE, _LOGIN_PATH, _PROGRAM, and _SSL_MODE. "
            "Prefer a MySQL option file or login path over a password environment variable."
        ),
    )
    parser.add_argument("--source", choices=sorted(SOURCE_DEFAULTS), default="uat",
                        help="uat (default) or production; controls database/table defaults")
    parser.add_argument("--bundle-dir", type=Path,
                        help="read a verified UAT-shaped TSV bundle without connecting to MySQL")
    parser.add_argument("--database", help="override the selected MySQL database")
    parser.add_argument("--table-prefix", help="override the table prefix, e.g. UAT_ or empty")
    parser.add_argument("--mysql-program", default=os.environ.get("ISSUE_RADAR_MYSQL_PROGRAM", "mysql"))
    parser.add_argument("--defaults-file", default=os.environ.get("ISSUE_RADAR_MYSQL_DEFAULTS_FILE"),
                        help="MySQL option file; preferred for automation")
    parser.add_argument("--login-path", default=os.environ.get("ISSUE_RADAR_MYSQL_LOGIN_PATH"),
                        help="mysql_config_editor login path")
    parser.add_argument("--mysql-host", default=os.environ.get("ISSUE_RADAR_MYSQL_HOST"))
    parser.add_argument("--mysql-port", type=int, default=int(os.environ.get("ISSUE_RADAR_MYSQL_PORT", "0")) or None)
    parser.add_argument("--mysql-user", default=os.environ.get("ISSUE_RADAR_MYSQL_USER"))
    parser.add_argument("--prompt-password", action="store_true",
                        help="securely prompt for the MySQL password without putting it in arguments")
    parser.add_argument("--ssl-mode", choices=["DISABLED", "PREFERRED", "REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"],
                        default=os.environ.get("ISSUE_RADAR_MYSQL_SSL_MODE"))
    parser.add_argument("--asof", help="historical evaluation date, YYYY-MM-DD")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--issue", help="show one exact tag or title-matched weekly series")
    parser.add_argument("--min-tier", default="WATCH", choices=[tier[0] for tier in TIERS])
    parser.add_argument("--export-tags", metavar="CSV_PATH",
                        help="export every distinct source tag and article count, then exit")
    return parser


def run(args):
    if args.export_tags:
        if args.bundle_dir:
            raise RadarError("--export-tags cannot be combined with --bundle-dir")
        export_tags(args, args.export_tags)
        return
    if args.bundle_dir:
        articles, source_label = load_bundle_articles(args.bundle_dir)
    else:
        articles, database, prefix = load_articles(args)
        source_label = f"{database}.{prefix}articles"
    asof = datetime.date.fromisoformat(args.asof) if args.asof else max(article["date"] for article in articles)

    if args.issue:
        needle = args.issue.strip().lower()
        selected = [
            article for article in articles
            if article["date"] <= asof and (needle in article["tags"] or needle in article["title"].lower())
        ]
        print(
            f"# series for '{args.issue}' as of {asof} "
            f"({len(selected)} matched of {len(articles)} articles; source {source_label})"
        )
        for week, (count, outlet_count, country_count) in series(selected, asof).items():
            print(f"{week}  vol={count:<4} outlets={outlet_count:<4} countries={country_count}")
        result = score_issue(selected, asof)
        if result:
            print(f"\nscore={result['score']:.2f} tier={result['tier']}  " + "; ".join(result["why"]))
        return

    ranked = []
    for tag, selected in candidates(articles, asof).items():
        result = score_issue(selected, asof)
        if result and result["tier"]:
            ranked.append((tag, result))
    order = {tier[0]: index for index, tier in enumerate(TIERS)}
    keep = order[args.min_tier]
    ranked = [item for item in ranked if order[item[1]["tier"]] <= keep]
    ranked.sort(key=lambda item: (-item[1]["score"], item[0]))

    print(
        f"# Issue radar as of {asof} "
        f"({len(ranked)} flagged from {len(articles)} articles, showing top {args.top}; "
        f"source {source_label})\n"
    )
    for tag, result in ranked[:args.top]:
        print(f"[{result['tier']:<5}] {result['score']:.2f}  {tag}  (vol {result['vol']}/28d)")
        for reason in result["why"]:
            print(f"         - {reason}")
    if not ranked:
        print("nothing flagged")


def main():
    load_local_env()
    try:
        run(build_parser().parse_args())
    except (RadarError, ValueError) as exc:
        print(f"issue_radar: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
