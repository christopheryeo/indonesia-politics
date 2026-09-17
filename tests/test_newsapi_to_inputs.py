import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "newsapi_to_inputs.py"
SPEC = importlib.util.spec_from_file_location("newsapi_to_inputs", SCRIPT)
NEWSAPI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NEWSAPI)


class NewsApiToInputsTests(unittest.TestCase):
    @staticmethod
    def record():
        return {
            "uri": "9410710146",
            "title": "KPK corruption investigation",
            "url": "https://example.com/article",
            "dateTimePub": "2026-07-28T23:23:23Z",
            "body": "A" * 120 + "\n\nTags:",
            "lang": "eng",
            "source": {
                "uri": "example.com",
                "title": "Example News",
                "location": {"country": {"label": {"eng": "Indonesia"}}},
            },
        }

    def test_extracts_newsapi_envelope(self):
        records = NEWSAPI.article_records([{"articles": {"results": [self.record()]}}])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["uri"], "9410710146")

    def test_render_uses_publication_time_and_schema_types(self):
        note = NEWSAPI.render_note(self.record())
        self.assertIn("publishedDate: '2026-07-28T23:23:23Z'", note)
        self.assertIn("language: 'eng'", note)
        self.assertIn("sourceType: 'crawl'", note)
        self.assertIn("coverageCount: 1", note)
        self.assertIn("mediaCount: 0", note)
        self.assertIn("countries: ['Indonesia']", note)
        self.assertNotIn("\nTags:\n", note)

    def test_short_body_is_blocked(self):
        record = self.record()
        record["body"] = "too short"
        self.assertIn(
            "article body has fewer than 100 meaningful characters",
            NEWSAPI.validate_record(record),
        )

    def test_bahasa_language_is_normalized(self):
        record = self.record()
        record["lang"] = "id-ID"
        self.assertIn("language: 'ind'", NEWSAPI.render_note(record))

    def test_missing_language_is_held(self):
        record = self.record()
        record.pop("lang")
        self.assertIn(
            "language is missing or unsupported; review to eng or ind",
            NEWSAPI.validate_record(record),
        )

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / "response.json"
            source.write_text(
                __import__("json").dumps([{"articles": {"results": [self.record()]}}]),
                encoding="utf-8",
            )
            old_inputs, old_articles, old_raw = NEWSAPI.INPUT_ROOT, NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT
            NEWSAPI.INPUT_ROOT = pathlib.Path(folder) / "inputs"
            NEWSAPI.ARTICLE_ROOT = pathlib.Path(folder) / "articles"
            NEWSAPI.RAW_ROOT = pathlib.Path(folder) / "raw"
            try:
                result = NEWSAPI.convert(source, write=False)
            finally:
                NEWSAPI.INPUT_ROOT, NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT = old_inputs, old_articles, old_raw
            self.assertEqual(result["planned"], 1)
            self.assertFalse((pathlib.Path(folder) / "inputs").exists())
            self.assertFalse((pathlib.Path(folder) / "raw").exists())

    def test_embedded_markdown_normalizes_body_and_classifies_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            source_dir = base / "loose"
            source_dir.mkdir()
            record = self.record()
            record["body"] = "First paragraph." + "A" * 100 + "\n\nSecond paragraph."
            outer_body = record["body"].replace("\n", "\\n")
            note = (
                "---\n"
                "articleId: '9410710146'\n"
                "articleTitle: 'KPK corruption investigation'\n"
                "url: 'https://example.com/article'\n"
                "publishedDate: '2026-07-28T23:23:23Z'\n"
                f"rawNewsApiResponse: {json.dumps(record)}\n"
                "---\n\n"
                f"{outer_body}\n"
            )
            (source_dir / "source.md").write_text(note, encoding="utf-8")
            article_root = base / "articles"
            compiled = article_root / "2026-07" / "existing.md"
            compiled.parent.mkdir(parents=True)
            compiled.write_text(
                "---\nsourceId: '9410710146'\nsourceUrl: 'https://example.com/article'\n---\n",
                encoding="utf-8",
            )
            old_articles, old_raw = NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT
            NEWSAPI.ARTICLE_ROOT = article_root
            NEWSAPI.RAW_ROOT = base / "raw"
            try:
                result = NEWSAPI.convert_embedded_directory(
                    source_dir, base / "working", write=True, include_compiled=True,
                )
            finally:
                NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT = old_articles, old_raw
            self.assertEqual(result["plannedUatOnly"], 1)
            destination = base / "working" / "2026-07" / "9410710146-kpk-corruption-investigation.md"
            self.assertIn("First paragraph.", destination.read_text(encoding="utf-8"))
            self.assertNotIn("\\n", destination.read_text(encoding="utf-8"))
            self.assertTrue(any((base / "raw").rglob("*.md")))
            self.assertTrue(any((base / "raw").rglob("*.json")))

    def test_embedded_markdown_excludes_declared_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            source_dir = base / "loose"
            source_dir.mkdir()
            record = self.record()
            record["isDuplicate"] = True
            note = (
                "---\n"
                "articleId: '9410710146'\n"
                "articleTitle: 'KPK corruption investigation'\n"
                "url: 'https://example.com/article'\n"
                "publishedDate: '2026-07-28T23:23:23Z'\n"
                f"rawNewsApiResponse: {json.dumps(record)}\n"
                "---\n\n"
                f"{record['body']}\n"
            )
            (source_dir / "duplicate.md").write_text(note, encoding="utf-8")
            old_articles, old_raw = NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT
            NEWSAPI.ARTICLE_ROOT = base / "articles"
            NEWSAPI.RAW_ROOT = base / "raw"
            try:
                result = NEWSAPI.convert_embedded_directory(
                    source_dir, base / "working", write=False, include_compiled=True,
                )
            finally:
                NEWSAPI.ARTICLE_ROOT, NEWSAPI.RAW_ROOT = old_articles, old_raw
            self.assertEqual(result["excludedDuplicate"], 1)
            self.assertFalse((base / "working").exists())


if __name__ == "__main__":
    unittest.main()
