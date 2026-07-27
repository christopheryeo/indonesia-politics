import json
import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAINS = {
    "article", "appointments", "country", "decisions", "issues",
    "organisations", "outlet", "people", "place", "search", "topic",
}
SYSTEM_NAMES = {"index.md", "catalog.md", "log.md", ".gitkeep"}


class MigrationBaselineTests(unittest.TestCase):
    def test_required_empty_runtime_directories_exist(self):
        required = [
            ROOT / "Inputs" / "articles",
            ROOT / "raw",
            ROOT / "runs",
            ROOT / "index",
            ROOT / "tmp",
            ROOT / "topics",
        ]
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(path.is_dir())
                self.assertEqual(
                    [item.name for item in path.iterdir() if item.name != ".gitkeep"],
                    [],
                )

    def test_every_domain_has_only_empty_system_files(self):
        entities = ROOT / "entities"
        self.assertEqual({path.name for path in entities.iterdir() if path.is_dir()}, DOMAINS)
        for domain in DOMAINS:
            folder = entities / domain
            with self.subTest(domain=domain):
                names = {path.name for path in folder.iterdir() if path.is_file()}
                self.assertTrue({"index.md", "catalog.md", "log.md"} <= names)
                self.assertEqual(names - SYSTEM_NAMES, set())
                catalog = (folder / "catalog.md").read_text(encoding="utf-8")
                self.assertRegex(catalog, r"(?:note_count: 0|Note count:\*\* 0)")
                log = (folder / "log.md").read_text(encoding="utf-8")
                self.assertIn("entry_count: 0", log)
                self.assertNotRegex(log, r"(?m)^- \d{4}-\d{2}-\d{2}")

    def test_configuration_is_valid_and_clean(self):
        manifest = yaml.safe_load((ROOT / "wiki.yaml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "indonesia-politics")
        self.assertIn("Indonesian", manifest["description"])
        dashboard = json.loads(
            (ROOT / "dashboards" / "default.json").read_text(encoding="utf-8")
        )
        self.assertEqual(dashboard["name"], "Indonesia Politics Overview")
        self.assertIsNone(dashboard["updated_at"])
        self.assertNotIn("chat", json.dumps(dashboard))

    def test_no_credentials_databases_archives_or_deployment_identity(self):
        forbidden_names = {
            ".env", ".env.local", "wiki.db", "hosting.json",
        }
        forbidden_suffixes = {
            ".sqlite", ".sqlite3", ".zip", ".tar", ".gz",
        }
        excluded_parts = {
            ".git", "node_modules", "dist", ".vinext", ".wrangler",
            "__pycache__", ".pytest_cache",
        }
        findings = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or excluded_parts.intersection(path.parts):
                continue
            if path.name in forbidden_names or path.suffix.lower() in forbidden_suffixes:
                findings.append(str(path.relative_to(ROOT)))
        self.assertEqual(findings, [])

    def test_dashboard_has_no_source_deployment_identity(self):
        site = ROOT / "dashboards" / "site"
        self.assertFalse((site / ".openai" / "hosting.json").exists())
        self.assertFalse((site / "public" / "og.png").exists())
        vite = (site / "vite.config.ts").read_text(encoding="utf-8")
        self.assertNotIn('import hostingConfig from "./.openai/hosting.json"', vite)

    def test_query_optimisation_and_generic_sensitivity_are_present(self):
        query = (ROOT / "scripts" / "query.py").read_text(encoding="utf-8")
        self.assertIn("FAST_CONTEXT_CHAR_CAP", query)
        self.assertIn("_run_fast_model", query)
        self.assertIn('"sensitive"', query)
        self.assertNotIn('"saf":', query)


if __name__ == "__main__":
    unittest.main()
