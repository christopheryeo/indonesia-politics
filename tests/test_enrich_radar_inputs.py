import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "enrich_radar_inputs.py"
SPEC = importlib.util.spec_from_file_location("enrich_radar_inputs", SCRIPT)
ENRICH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENRICH)


class RadarInputEnrichmentTests(unittest.TestCase):
    def test_frontmatter_parser_reads_current_input_shape(self):
        lines = [
            "articleId: '42'",
            "articleTitle: 'Writer''s argument'",
            "tags: ['AI Safety', 'OpenAI']",
            "outlets: []",
        ]
        parsed = ENRICH.parse_frontmatter(lines)
        self.assertEqual(parsed["articleId"], "42")
        self.assertEqual(parsed["articleTitle"], "Writer's argument")
        self.assertEqual(parsed["tags"], ["AI Safety", "OpenAI"])

    def test_shortlist_uses_existing_tag_surface_values(self):
        inventory = [
            ("Artificial Intelligence", "artificial intelligence", 20),
            ("Submarine", "submarine", 10),
        ]
        result = ENRICH.shortlist_tags("Artificial intelligence investment is rising.", inventory)
        self.assertEqual(result, ["Artificial Intelligence"])

    def test_discovery_includes_loose_and_month_inputs_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / "loose.md").write_text("x", encoding="utf-8")
            (root / "2026-07").mkdir()
            (root / "2026-07" / "monthly.md").write_text("x", encoding="utf-8")
            (root / "not-a-month").mkdir()
            (root / "not-a-month" / "ignored.md").write_text("x", encoding="utf-8")
            self.assertEqual(len(ENRICH.discover_input_paths(root)), 2)
            self.assertEqual(
                [path.name for path in ENRICH.discover_input_paths(root, loose_only=True)],
                ["loose.md"],
            )

    def test_consensus_requires_two_pass_agreement(self):
        primary = self.classification()
        review = self.classification()
        result = ENRICH.consensus(primary, review, 0.82, {"AI Safety"})
        self.assertTrue(result["autoApplicable"]["tone"])
        self.assertTrue(result["autoApplicable"]["eventType"])
        self.assertEqual(result["issueTags"], ["AI Safety"])

        review["tone"] = "Factual"
        result = ENRICH.consensus(primary, review, 0.82, {"AI Safety"})
        self.assertFalse(result["autoApplicable"]["tone"])
        self.assertIsNone(result["tone"])

    def test_apply_only_writes_registered_fields(self):
        lines = [
            "articleId: '42'",
            "category: 'Multilateral Relations'",
            "tone: 'Factual'",
            "eventType: 'Unfacilitated'",
            "tags: []",
            "outlets: []",
            "countries: []",
            "coverageCount: 1",
        ]
        result = {
            "tone": "Opinionated",
            "eventType": "Facilitated",
            "issueTags": ["AI Safety"],
            "outletName": "Example News",
            "outletCountry": "Singapore",
            "institutionalCategory": "National Security",
            "autoApplicable": {"tone": True, "eventType": True, "metadata": True, "tags": True},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "article.md"
            path.write_text("---\n" + "\n".join(lines) + "\n---\n\nBody\n", encoding="utf-8")
            changed = ENRICH.apply_result(path, lines, "Body", result)
            text = path.read_text(encoding="utf-8")
        self.assertEqual(
            changed,
            ["category", "countries", "coverageCount", "eventType", "outlets", "tags", "tone"],
        )
        self.assertIn("tone: 'Opinionated'", text)
        self.assertIn("tags: ['AI Safety']", text)
        self.assertNotIn("confidence", text)

    def test_apply_assessment_deduplicates_articles_across_files(self):
        result = {
            "tone": "Opinionated",
            "eventType": "Facilitated",
            "issueTags": ["AI Safety"],
            "outletName": "Example News",
            "outletCountry": "Singapore",
            "institutionalCategory": "National Security",
            "autoApplicable": {"tone": True, "eventType": True, "metadata": True, "tags": True},
        }
        with tempfile.TemporaryDirectory() as folder:
            relative = pathlib.Path(folder) / "article.md"
            relative.write_text(
                "---\narticleId: '42'\ntone: 'Factual'\neventType: 'Unfacilitated'\n"
                "tags: []\noutlets: []\ncountries: []\ncategory: 'Other'\ncoverageCount: 1\n"
                "---\n\nBody\n",
                encoding="utf-8",
            )
            assessment = {
                "assessments": [{
                    "articleId": "42",
                    "path": str(relative),
                    "consensus": result,
                }]
            }
            one = pathlib.Path(folder) / "one.json"
            two = pathlib.Path(folder) / "two.json"
            one.write_text(__import__("json").dumps(assessment), encoding="utf-8")
            two.write_text(__import__("json").dumps(assessment), encoding="utf-8")
            original_root = ENRICH.ROOT
            ENRICH.ROOT = pathlib.Path("/")
            try:
                code = ENRICH.apply_assessments([one, two])
            finally:
                ENRICH.ROOT = original_root
        self.assertEqual(code, 0)

    @staticmethod
    def classification():
        return {
            "tone": "Opinionated",
            "tone_confidence": 0.93,
            "tone_evidence": ["The author argues"],
            "event_type": "Facilitated",
            "event_confidence": 0.91,
            "event_trigger": "scheduled report",
            "event_evidence": ["The report was released"],
            "issue_tags": ["AI Safety"],
            "outlet_name": "Example News",
            "outlet_country": "Singapore",
            "institutional_category": "National Security",
            "metadata_confidence": 0.90,
            "review_required": False,
            "review_reason": "",
        }


if __name__ == "__main__":
    unittest.main()
