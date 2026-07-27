import argparse
import datetime
import importlib.util
import json
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "issue_radar.py"
SPEC = importlib.util.spec_from_file_location("issue_radar", SCRIPT)
RADAR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RADAR)


class IssueRadarTests(unittest.TestCase):
    def test_product_query_uses_read_only_canonical_uat_tables(self):
        query = RADAR.product_query("MSM_dataset_UAT", "UAT_")
        self.assertIn("SET SESSION TRANSACTION READ ONLY", query)
        self.assertIn("`MSM_dataset_UAT`.`UAT_articles`", query)
        self.assertIn("`MSM_dataset_UAT`.`UAT_article_tags`", query)
        self.assertIn("`MSM_dataset_UAT`.`UAT_article_coverage`", query)

    def test_product_query_rejects_unsafe_identifiers(self):
        with self.assertRaises(RADAR.RadarError):
            RADAR.product_query("MSM_dataset; DROP DATABASE x", "")

    def test_parse_product_rows_normalises_tags_and_deduplicates_coverage(self):
        row = {
            "article_id": 42,
            "title": "Example",
            "published_date": "2026-07-22T12:30:00",
            "category": "Parliament",
            "tone": "Opinionated",
            "event_type": "Unfacilitated",
            "tags": [" Enlistment Act ", "ENLISTMENT ACT", None],
            "outlets": ["CNA", "CNA", None],
            "countries": ["Singapore", "Singapore", None],
        }
        articles = RADAR.parse_product_rows(json.dumps(row))
        self.assertEqual(articles[0]["tags"], {"enlistment act"})
        self.assertEqual(articles[0]["outlets"], {"CNA"})
        self.assertEqual(articles[0]["countries"], {"Singapore"})
        self.assertTrue(articles[0]["unfac"])
        self.assertTrue(articles[0]["opin"])

    def test_historical_candidates_do_not_use_future_articles(self):
        asof = datetime.date(2026, 1, 31)
        articles = []
        for index in range(7):
            articles.append(self.article(asof - datetime.timedelta(days=index * 7), "future-assisted"))
        for index in range(3):
            articles.append(self.article(asof + datetime.timedelta(days=index + 1), "future-assisted"))
        self.assertNotIn("future-assisted", RADAR.candidates(articles, asof))

    def test_mysql_defaults_file_is_first_client_option(self):
        args = argparse.Namespace(
            mysql_program="mysql", defaults_file="/secure/client.cnf", login_path=None,
            mysql_host=None, mysql_port=None, mysql_user=None, ssl_mode=None,
        )
        command = RADAR.mysql_command(args)
        self.assertEqual(command[:2], ["mysql", "--defaults-extra-file=/secure/client.cnf"])

    def test_production_query_uses_unprefixed_product_tables(self):
        database, prefix = RADAR.SOURCE_DEFAULTS["production"]
        query = RADAR.product_query(database, prefix)
        self.assertIn("`MSM_dataset`.`articles`", query)
        self.assertIn("`MSM_dataset`.`article_tags`", query)
        self.assertIn("`MSM_dataset`.`article_coverage`", query)
        self.assertNotIn("`UAT_", query)

    def test_secure_password_prompt_option_is_available(self):
        args = RADAR.build_parser().parse_args(["--prompt-password"])
        self.assertTrue(args.prompt_password)

    def test_tag_inventory_query_is_read_only_and_counts_articles(self):
        query = RADAR.product_tags_query("MSM_dataset", "")
        self.assertIn("SET SESSION TRANSACTION READ ONLY", query)
        self.assertIn("COUNT(DISTINCT article_id)", query)
        self.assertIn("GROUP BY BINARY tag", query)
        self.assertIn("`MSM_dataset`.`article_tags`", query)

    @staticmethod
    def article(day, tag):
        return {
            "id": 1, "title": "", "date": day, "cat": "", "tags": {tag},
            "outlets": set(), "countries": set(), "unfac": False, "opin": False,
        }


if __name__ == "__main__":
    unittest.main()
