#!/usr/bin/env python3
"""Shared English/Bahasa Indonesia normalization and matching primitives.

The vault stores ISO 639-3 codes (``eng`` and ``ind``). ``und`` is an intake
hold value only: a new article must be reviewed to ``eng`` or ``ind`` before
it can be compiled. Text normalization is for identity matching only; source
and display text must always be preserved verbatim.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


LANGUAGE_ALIASES = {
    "eng": "eng", "en": "eng", "english": "eng",
    "ind": "ind", "id": "ind", "indonesian": "ind",
    "bahasa": "ind", "bahasa indonesia": "ind",
}

INDONESIAN_QUERY_TERMS = {
    "apa", "apakah", "bagaimana", "berikan", "daftar", "dengan", "hubungan",
    "ini", "kapan", "mengatakan", "mengenai", "oleh", "semua", "siapa",
    "tentang", "terjadi", "terkait", "yang",
}
ENGLISH_QUERY_TERMS = {
    "all", "about", "current", "every", "give", "happened", "how", "list",
    "related", "relationship", "said", "tell", "what", "when", "who",
}

# Stable analytical topics/tags remain English. These high-confidence synonyms
# prevent the same broad subject being minted twice from common Bahasa labels.
CANONICAL_TOPIC_ALIASES = {
    "antikorupsi": "Anti-corruption",
    "ekonomi": "Economy",
    "hukum": "Law",
    "independensi": "Independence",
    "investasi": "Investment",
    "kebijakan pemerintah": "Government Policies",
    "konflik": "Conflict",
    "korupsi": "Corruption",
    "pencucian uang": "Money Laundering",
    "penyelidikan": "Investigation",
    "stabilitas": "Stability",
    "tata kelola": "Governance",
}

# Canonical country display values plus reviewed Bahasa/English exonyms. The
# ordinary English seed in ingest_cascade.py remains available for other names.
COUNTRY_ALIASES = {
    "amerika serikat": "United States",
    "as": "United States",
    "tiongkok": "China",
    "republik rakyat tiongkok": "China",
    "inggris": "United Kingdom",
    "britania raya": "United Kingdom",
    "uni emirat arab": "United Arab Emirates",
    "uea": "United Arab Emirates",
    "korea selatan": "South Korea",
    "korea utara": "North Korea",
    "belanda": "Netherlands",
    "jerman": "Germany",
    "jepang": "Japan",
    "filipina": "Philippines",
    "selandia baru": "New Zealand",
    "arab saudi": "Saudi Arabia",
}


def normalize_language(value: Any) -> str:
    """Return ``eng``, ``ind`` or the safe intake hold value ``und``."""

    raw = str(value or "").strip().casefold().replace("_", "-")
    if raw in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[raw]
    base = raw.split("-", 1)[0]
    return LANGUAGE_ALIASES.get(base, "und")


def normalize_match_text(value: Any) -> str:
    """Unicode-aware identity normalization without translating the value."""

    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def phrase_in_text(phrase: str, text: str) -> bool:
    """Match a normalized phrase on token boundaries."""

    needle = normalize_match_text(phrase)
    haystack = normalize_match_text(text)
    return bool(needle and re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", haystack))


def canonical_topic(value: Any) -> str:
    raw = str(value or "").strip()
    return CANONICAL_TOPIC_ALIASES.get(normalize_match_text(raw), raw)


def canonical_country(value: Any) -> str:
    raw = str(value or "").strip()
    return COUNTRY_ALIASES.get(normalize_match_text(raw), raw)


def question_language(question: str) -> str:
    """Detect a query's answer language; mixed/indeterminate defaults to English."""

    normalized = normalize_match_text(question)
    if re.search(r"\b(?:jawab|jawablah)\s+(?:dalam\s+)?bahasa(?:\s+indonesia)?\b", normalized):
        return "ind"
    if re.search(r"\b(?:answer|respond)\s+in\s+english\b", normalized):
        return "eng"
    tokens = set(normalized.split())
    ind_score = len(tokens & INDONESIAN_QUERY_TERMS)
    eng_score = len(tokens & ENGLISH_QUERY_TERMS)
    return "ind" if ind_score > eng_score else "eng"
