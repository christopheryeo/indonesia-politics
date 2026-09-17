import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_topic_notes", ROOT / "scripts" / "prepare_topic_notes_for_crawl.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareTopicNotesTests(unittest.TestCase):
    def test_materialize_adds_tampines_style_crawl_sections(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            note = Path(directory) / "topic-a.md"
            note.write_text("---\ntopicId: topic-a\narticleCount: 2\ncrawlStatus: Not started\ncrawlStatusAt: null\nlastCrawledAt: null\n---\n\n# Topic A\n\n## Coverage\n- [[article-a]]\n", encoding="utf-8")
            record = {"definition": "Indonesian political reporting materially related to Topic A.", "crawlPrompt": '("Topic A") AND Indonesia', "articleCount": 2, "crawlStatus": "Not started", "crawlStatusAt": None, "lastCrawledAt": None}
            rendered = MODULE.materialize(note, record)
            for title in ("Definition", "Crawl Prompt", "Coverage", "Crawl Log", "Notes"):
                self.assertEqual(rendered.count(f"## {title}\n"), 1)
            self.assertLess(rendered.index("## Definition"), rendered.index("## Crawl Prompt"))
            self.assertLess(rendered.index("## Crawl Prompt"), rendered.index("## Coverage"))
            self.assertLess(rendered.index("## Coverage"), rendered.index("## Crawl Log"))
            self.assertLess(rendered.index("## Crawl Log"), rendered.index("## Notes"))
            self.assertIn("- [[article-a]]", rendered)
            self.assertIn('("Topic A") AND Indonesia', rendered)
            note.write_text(rendered, encoding="utf-8")
            self.assertEqual(MODULE.materialize(note, record), rendered)


if __name__ == "__main__":
    unittest.main()
