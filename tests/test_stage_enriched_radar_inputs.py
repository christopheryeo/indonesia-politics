import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


STAGER = load_script("stage_enriched_radar_inputs")
CASCADE = load_script("ingest_cascade")


class EnrichedRadarStagerTests(unittest.TestCase):
    def test_phase4_duplicate_check_is_collation_explicit(self):
        sql = STAGER.phase4_transform_sql("batch", "transform")
        self.assertIn("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;", sql)
        self.assertIn("u.`vendor_article_id` COLLATE utf8mb4_unicode_ci", sql)
        self.assertIn("a.`vendor_article_id` COLLATE utf8mb4_unicode_ci", sql)

    def article(self, article_id, title):
        return (
            "---\n"
            f"articleId: '{article_id}'\n"
            f"articleTitle: '{title}'\n"
            "publishedDate: '2026-07-23T07:29:40.852Z'\n"
            "language: 'eng'\n"
            "category: 'Multilateral Relations'\n"
            f"topic: '{title}'\n"
            "tone: 'Factual'\n"
            "toneSentiment: 'Neutral'\n"
            "eventType: 'Facilitated'\n"
            "tags: ['AI Safety']\n"
            "outlets: ['example-news']\n"
            "countries: ['Singapore']\n"
            "coverageCount: 1\n"
            "mediaCount: 0\n"
            "sourceType: 'news'\n"
            "url: 'https://example.com/story'\n"
            "---\n\nSource body.\n"
        )

    def assessment(self, article_id, ready=True):
        auto = {
            "topic": True,
            "tone": True,
            "toneSentiment": True,
            "eventType": ready,
            "metadata": True,
            "tags": True,
        }
        return {
            "articleId": article_id,
            "consensus": {
                "topic": "AI safety governance",
                "tone": "Factual",
                "toneSentiment": "Neutral",
                "eventType": "Facilitated",
                "issueTags": ["AI Safety"],
                "outletName": "Example News",
                "outletCountry": "Singapore",
                "institutionalCategory": "Non-institutional",
                "outletLocationValidation": {
                    "status": "validated",
                    "country": "Singapore",
                    "method": "two-pass-enrichment-consensus",
                    "confidence": 0.9,
                    "reviewRequired": False,
                    "reviewReasons": [],
                },
                "autoApplicable": auto,
                "reviewRequired": not ready,
                "reviewReasons": [] if ready else ["event-type disagreement or low confidence"],
            },
        }

    def prepare_fixture(self, folder, approvals=None):
        base = pathlib.Path(folder)
        inputs = base / "inputs"
        inputs.mkdir()
        (inputs / "one.md").write_text(
            self.article("art_alpha", "First article"), encoding="utf-8",
        )
        (inputs / "two.md").write_text(
            self.article("9403203639", "Second article"), encoding="utf-8",
        )
        (inputs / "month").mkdir()
        (inputs / "month" / "not-loose.md").write_text(
            self.article("nested_article", "Nested article"), encoding="utf-8",
        )
        assessment = base / "assessment.json"
        assessment.write_text(json.dumps({
            "assessments": [
                self.assessment("art_alpha", True),
                self.assessment("9403203639", False),
            ],
        }), encoding="utf-8")
        output = base / "bundle"
        arguments = [
            "prepare", "--input-dir", str(inputs),
            "--loose-only",
            "--assessment", str(assessment),
            "--output-dir", str(output),
        ]
        if approvals:
            approval_path = base / "approvals.json"
            approval_path.write_text(json.dumps(approvals), encoding="utf-8")
            arguments.extend(["--approvals", str(approval_path)])
        self.assertEqual(STAGER.main(arguments), 0)
        return output

    def test_bundle_preserves_external_ids_and_holds_uncertain_article(self):
        with tempfile.TemporaryDirectory() as folder:
            output = self.prepare_fixture(folder)
            manifest = json.loads(
                (output / "bundle_manifest.json").read_text(encoding="utf-8"),
            )
            article_rows = [
                line.split("\t")
                for line in (output / "articles.tsv").read_text(encoding="utf-8").splitlines()
            ]
            phase4 = (output / "phase4_transform.sql").read_text(encoding="utf-8")
            phase5 = (output / "phase5_load_uat.sql").read_text(encoding="utf-8")

            self.assertEqual(manifest["counts"]["articles"], 2)
            self.assertEqual(manifest["counts"]["readyArticles"], 1)
            self.assertEqual(manifest["counts"]["reviewArticles"], 1)
            self.assertEqual([row[4] for row in article_rows], ["-1", "-2"])
            self.assertEqual([row[6] for row in article_rows], ["art_alpha", "9403203639"])
            self.assertIn("@allocation_ceiling+ROW_NUMBER()", phase4)
            self.assertIn("ROLLBACK", phase5)
            self.assertIn("SIGNAL SQLSTATE '45000'", phase5)
            self.assertEqual(STAGER.main([
                "verify-bundle", "--bundle-dir", str(output),
            ]), 0)

    def test_reviewed_approval_can_admit_held_article(self):
        approval = {
            "approvals": {
                "9403203639": {
                    "approved": True,
                    "approvedBy": "reviewer",
                    "approvedAt": "2026-07-23T17:00:00+08:00",
                    "fields": {
                        "language": "eng",
                        "topic": "AI safety governance",
                        "tone": "Factual",
                        "toneSentiment": "Neutral",
                        "eventType": "Facilitated",
                        "tags": ["AI Safety"],
                        "outletName": "Example News",
                        "outletCountry": "Singapore",
                        "category": "Multilateral Relations",
                    },
                },
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            output = self.prepare_fixture(folder, approval)
            manifest = json.loads(
                (output / "bundle_manifest.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(manifest["counts"]["readyArticles"], 2)
            self.assertEqual(manifest["counts"].get("reviewArticles", 0), 0)

    def test_missing_publisher_location_validation_is_held(self):
        assessment = self.assessment("art_alpha", True)
        assessment["consensus"].pop("outletLocationValidation")
        _, problems = STAGER.assessment_state(
            "art_alpha",
            {
                "tone": "Factual",
                "eventType": "Facilitated",
                "tags": ["AI Safety"],
                "outlets": ["example-news"],
                "countries": ["Singapore"],
                "category": "Government",
            },
            assessment,
            None,
        )
        self.assertIn("PUBLISHER_LOCATION_NOT_VALIDATED", {item["rule"] for item in problems})

    def test_und_language_is_held_even_when_enrichment_is_ready(self):
        assessment = self.assessment("art_alpha", True)
        _, problems = STAGER.assessment_state(
            "art_alpha",
            {
                "language": "und", "topic": "AI safety governance", "tone": "Factual",
                "toneSentiment": "Neutral", "eventType": "Facilitated",
                "tags": ["AI Safety"], "outlets": ["example-news"],
                "countries": ["Singapore"], "category": "Government",
            },
            assessment,
            None,
        )
        self.assertIn("language", {item["field"] for item in problems})

    def test_compiled_article_body_preserves_exact_issue_tags(self):
        self.assertEqual(
            CASCADE.issue_tag_lines(["AI Safety", "Defence Spending", "ai safety"]),
            "- AI Safety\n- Defence Spending",
        )


if __name__ == "__main__":
    unittest.main()
