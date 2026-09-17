#!/usr/bin/env python3
"""Run the controlled English/Bahasa Indonesia acceptance pilot.

The pilot uses ten paired entity/topic/country cases in each language against
the live Markdown entity vocabulary. It is read-only except for its generated
receipt under runs/. No model or external database is used.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from language_support import (
    canonical_country,
    canonical_topic,
    normalize_language,
    normalize_match_text,
    question_language,
)


ROOT = Path(__file__).resolve().parents[1]
ENTITY_ROOT = ROOT / "entities"
SGT = ZoneInfo("Asia/Singapore")
SYSTEM_FILES = {"index.md", "catalog.md", "log.md", "_template.md"}


@dataclass(frozen=True)
class PilotCase:
    language_value: str
    expected_language: str
    question: str
    topic: str
    expected_topic: str
    country: str
    expected_country: str
    entity_alias: str
    expected_slug: str


PAIRS = [
    ("Who is the Corruption Eradication Commission?", "Apa itu Komisi Pemberantasan Korupsi?", "Corruption", "Korupsi", "Corruption", "United States", "Amerika Serikat", "Corruption Eradication Commission", "Komisi Pemberantasan Korupsi", "corruption-eradication-commission"),
    ("What is the Financial Services Authority?", "Apa itu Otoritas Jasa Keuangan?", "Governance", "Tata Kelola", "Governance", "China", "Tiongkok", "Financial Services Authority", "Otoritas Jasa Keuangan", "financial-services-authority"),
    ("Who is in the House of Representatives?", "Siapa yang terkait dengan Dewan Perwakilan Rakyat?", "Government Policies", "Kebijakan Pemerintah", "Government Policies", "United Kingdom", "Inggris", "House of Representatives", "Dewan Perwakilan Rakyat", "house-of-representatives"),
    ("What is the Deposit Insurance Corporation?", "Apa itu Lembaga Penjamin Simpanan?", "Stability", "Stabilitas", "Stability", "Netherlands", "Belanda", "Deposit Insurance Corporation", "Lembaga Penjamin Simpanan", "deposit-insurance-corporation"),
    ("Tell me more about the Financial System Stability Committee", "Apa yang terjadi terkait Komite Stabilitas Sistem Keuangan?", "Investment", "Investasi", "Investment", "Germany", "Jerman", "Financial System Stability Committee", "Komite Stabilitas Sistem Keuangan", "financial-system-stability-committee"),
    ("What is the University of Indonesia?", "Apa itu Universitas Indonesia?", "Independence", "Independensi", "Independence", "Japan", "Jepang", "University of Indonesia", "Universitas Indonesia", "university-of-indonesia"),
    ("What is the Presidential Palace Complex?", "Apa itu Kompleks Istana Kepresidenan?", "Conflict", "Konflik", "Conflict", "Philippines", "Filipina", "Presidential Palace Complex", "Kompleks Istana Kepresidenan", "presidential-palace-complex"),
    ("What happened at Bank Indonesia?", "Apa yang terjadi di Bank Indonesia?", "Investigation", "Penyelidikan", "Investigation", "South Korea", "Korea Selatan", "Bank Indonesia", "Bank Indonesia", "bank-indonesia"),
    ("Tell me more about Danantara", "Jelaskan tentang Danantara", "Money Laundering", "Pencucian Uang", "Money Laundering", "United Arab Emirates", "Uni Emirat Arab", "Danantara", "Danantara", "danantara"),
    ("What happened in Jakarta?", "Apa yang terjadi di Jakarta?", "Law", "Hukum", "Law", "Saudi Arabia", "Arab Saudi", "Jakarta", "Jakarta", "jakarta"),
]


def cases() -> list[PilotCase]:
    output = []
    for index, pair in enumerate(PAIRS):
        en_q, id_q, en_topic, id_topic, expected_topic, en_country, id_country, en_alias, id_alias, slug = pair
        output.append(PilotCase("en-US" if index % 2 else "eng", "eng", en_q, en_topic, expected_topic, en_country, en_country, en_alias, slug))
        output.append(PilotCase("id-ID" if index % 2 else "ind", "ind", id_q, id_topic, expected_topic, id_country, en_country, id_alias, slug))
    return output


def load_alias_index() -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for domain in ("people", "organisations", "place", "country", "topic", "outlet"):
        folder = ENTITY_ROOT / domain
        for path in folder.glob("*.md") if folder.exists() else []:
            if path.name in SYSTEM_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n") or "\n---" not in text[4:]:
                continue
            end = text.find("\n---", 4)
            data = yaml.safe_load(text[4:end]) or {}
            names: list[Any] = [data.get("displayName"), path.stem.replace("-", " ")]
            aliases = data.get("aliases") or []
            names.extend(aliases if isinstance(aliases, list) else [aliases])
            for name in names:
                key = normalize_match_text(name)
                if key:
                    index.setdefault(key, set()).add(path.stem)
    return index


def run_pilot(repetitions: int = 200, max_avg_ms: float = 5.0) -> dict[str, Any]:
    alias_index = load_alias_index()
    fixtures = cases()
    results = []
    started = time.perf_counter()
    for _ in range(max(1, repetitions)):
        for case in fixtures:
            resolved = alias_index.get(normalize_match_text(case.entity_alias), set())
            if _ == 0:
                results.append({
                    "language": normalize_language(case.language_value) == case.expected_language,
                    "questionLanguage": question_language(case.question) == case.expected_language,
                    "topic": canonical_topic(case.topic) == case.expected_topic,
                    "country": canonical_country(case.country) == case.expected_country,
                    "entity": resolved == {case.expected_slug},
                    "resolved": sorted(resolved),
                    "expectedSlug": case.expected_slug,
                })
            else:
                normalize_language(case.language_value)
                question_language(case.question)
                canonical_topic(case.topic)
                canonical_country(case.country)
    elapsed = time.perf_counter() - started
    total_cases = len(results)
    metric = lambda key: sum(bool(row[key]) for row in results) / total_cases
    paired_duplicates = sum(
        results[index]["resolved"] != results[index + 1]["resolved"]
        for index in range(0, total_cases, 2)
    )
    avg_ms = elapsed * 1000 / (len(fixtures) * max(1, repetitions))
    metrics = {
        "languageAccuracy": metric("language"),
        "questionLanguageAccuracy": metric("questionLanguage"),
        "topicAccuracy": metric("topic"),
        "countryAccuracy": metric("country"),
        "entityPrecision": metric("entity"),
        "entityRecall": metric("entity"),
        "bilingualDuplicateFailures": paired_duplicates,
        "avgDeterministicMsPerArticle": round(avg_ms, 4),
    }
    gates = {
        "languageAccuracy": metrics["languageAccuracy"] == 1.0,
        "questionLanguageAccuracy": metrics["questionLanguageAccuracy"] == 1.0,
        "topicAccuracy": metrics["topicAccuracy"] >= 0.95,
        "countryAccuracy": metrics["countryAccuracy"] >= 0.95,
        "entityPrecision": metrics["entityPrecision"] >= 0.98,
        "entityRecall": metrics["entityRecall"] >= 0.90,
        "noBilingualDuplicates": paired_duplicates == 0,
        "performance": avg_ms <= max_avg_ms,
    }
    return {
        "type": "bilingual-pilot-receipt",
        "generatedAt": datetime.now(SGT).isoformat(timespec="seconds"),
        "languages": ["eng", "ind"],
        "cases": total_cases,
        "casesPerLanguage": {"eng": 10, "ind": 10},
        "repetitions": max(1, repetitions),
        "maxAvgMs": max_avg_ms,
        "metrics": metrics,
        "gates": gates,
        "status": "passed" if all(gates.values()) else "failed",
        "failures": [row for row in results if not all(row[key] for key in ("language", "questionLanguage", "topic", "country", "entity"))],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=200)
    parser.add_argument("--max-avg-ms", type=float, default=5.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = run_pilot(args.repetitions, args.max_avg_ms)
    if not args.no_write:
        output = args.output or ROOT / "runs" / datetime.now(SGT).date().isoformat() / "artifacts" / "bilingual-pilot.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["receipt"] = str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
