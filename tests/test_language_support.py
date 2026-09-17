import pathlib
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import language_support as LANGUAGE  # noqa: E402
import people_country_inference as COUNTRY_INFERENCE  # noqa: E402
import ingest_cascade as CASCADE  # noqa: E402


class LanguageSupportTests(unittest.TestCase):
    def test_language_code_normalization(self):
        for raw, expected in {
            "en": "eng", "en-US": "eng", "English": "eng",
            "id": "ind", "id-ID": "ind", "Bahasa Indonesia": "ind",
            "": "und", "jpn": "und",
        }.items():
            with self.subTest(raw=raw):
                self.assertEqual(LANGUAGE.normalize_language(raw), expected)

    def test_unicode_and_punctuation_normalization(self):
        self.assertEqual(
            LANGUAGE.normalize_match_text("  KOMISI—Pemberantasan Korupsi "),
            "komisi pemberantasan korupsi",
        )

    def test_canonical_bilingual_terms(self):
        self.assertEqual(LANGUAGE.canonical_topic("Korupsi"), "Corruption")
        self.assertEqual(LANGUAGE.canonical_topic("Tata Kelola"), "Governance")
        self.assertEqual(LANGUAGE.canonical_country("Amerika Serikat"), "United States")
        self.assertEqual(LANGUAGE.canonical_country("Tiongkok"), "China")

    def test_query_language_detection(self):
        self.assertEqual(LANGUAGE.question_language("Siapa Prabowo Subianto?"), "ind")
        self.assertEqual(LANGUAGE.question_language("Who is Prabowo Subianto?"), "eng")
        self.assertEqual(LANGUAGE.question_language("Prabowo Subianto"), "eng")
        self.assertEqual(
            LANGUAGE.question_language("Who is Prabowo? Jawab dalam Bahasa Indonesia"),
            "ind",
        )

    def test_bahasa_person_country_evidence(self):
        evidence = COUNTRY_INFERENCE.country_in_direct_text(
            "Budi Santoso adalah pejabat dari Indonesia yang menangani kebijakan tersebut.",
            "Budi Santoso",
        )
        self.assertEqual(evidence.country, "Indonesia")
        self.assertEqual(evidence.confidence, "high")

    def test_ambiguous_bilingual_alias_blocks_cascade_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            directories = {domain: root / domain for domain in CASCADE.DOMAIN_DIRS}
            for directory in directories.values():
                directory.mkdir()
            for slug in ("one", "two"):
                (directories["organisations"] / f"{slug}.md").write_text(
                    "---\ndisplayName: 'Example Body'\naliases: ['Badan Contoh']\n---\n",
                    encoding="utf-8",
                )
            with mock.patch.object(CASCADE, "DOMAIN_DIRS", directories):
                with self.assertRaisesRegex(RuntimeError, "ambiguous normalized alias"):
                    CASCADE.load_entities()


if __name__ == "__main__":
    unittest.main()
