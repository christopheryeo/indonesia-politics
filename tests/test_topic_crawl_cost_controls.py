import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


ENRICH = module("enrich_radar_inputs")
GATE = module("gate_topic_crawl_relevance")
POLICY = module("apply_topic_crawl_policy")


class TopicCrawlCostControlTests(unittest.TestCase):
    def test_gate_reads_canonical_topic_context(self):
        registry = __import__("yaml").safe_load(
            (ROOT / "topics" / "canonical-topics.yaml").read_text(encoding="utf-8")
        )
        context = GATE.topic_context(registry["topics"][0]["topicId"])
        self.assertTrue(context["displayName"])
        self.assertTrue(context["definition"])
        self.assertTrue(context["crawlPrompt"])

    def test_manifest_rejects_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            fake_root = base / "repo"
            source = fake_root / "Inputs" / "articles" / "cost-control-test.md"
            source.parent.mkdir(parents=True)
            source.write_text("---\narticleId: 'test'\n---\n\nBody\n", encoding="utf-8")
            manifest = fake_root / "batch.manifest"
            manifest.write_text(
                "Inputs/articles/cost-control-test.md\nInputs/articles/cost-control-test.md\n",
                encoding="utf-8",
            )
            original_root = ENRICH.ROOT
            try:
                ENRICH.ROOT = fake_root
                with self.assertRaises(ENRICH.EnrichmentError):
                    ENRICH.paths_from_manifest(manifest)
            finally:
                ENRICH.ROOT = original_root

    def test_completeness_requires_enrichment_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            note = pathlib.Path(folder) / "article.md"
            note.write_text(
                "---\narticleId: 'test'\narticleTitle: 'Title'\npublishedDate: '2026-09-17T00:00:00Z'\n"
                "language: 'eng'\ntopic: ''\ntone: ''\ntoneSentiment: ''\neventType: ''\ntags: []\n"
                "outlets: ['example']\ncountries: ['Indonesia']\nurl: 'https://example.test'\n---\n\nBody\n",
                encoding="utf-8",
            )
            missing = ENRICH.completeness_errors(note)
        self.assertEqual(missing, ["topic", "tone", "toneSentiment", "eventType", "tags"])

    def test_policy_uses_defaults_only_for_unresolved_fields(self):
        updates = POLICY.policy_updates({"autoApplicable": {"tone": True, "tags": False}})
        self.assertNotIn("tone", updates)
        self.assertEqual(updates["toneSentiment"], "Neutral")
        self.assertEqual(updates["tags"], ["#source"])


if __name__ == "__main__":
    unittest.main()
