import json
import pathlib
import subprocess
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAINS = {
    "article", "appointments", "country", "decisions", "issues",
    "organisations", "outlet", "people", "place", "search", "topic",
}
SYSTEM_NAMES = {"index.md", "catalog.md", "log.md", ".gitkeep"}


def live_runtime_state_exists():
    """Return true when the reusable empty baseline is being used as a live vault."""

    runtime_roots = [
        ROOT / "Inputs" / "articles", ROOT / "raw", ROOT / "runs",
        ROOT / "index", ROOT / "tmp", ROOT / "topics",
    ]
    if any(
        item.name != ".gitkeep"
        for path in runtime_roots
        for item in path.iterdir()
    ):
        return True
    return any(
        path.is_file() and path.name not in SYSTEM_NAMES
        for domain in DOMAINS - {"decisions"}
        for path in (ROOT / "entities" / domain).rglob("*")
    )


class MigrationBaselineTests(unittest.TestCase):
    def test_required_empty_runtime_directories_exist(self):
        if live_runtime_state_exists():
            self.skipTest("empty migration-baseline assertion is not applicable to a live vault")
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
        if live_runtime_state_exists():
            self.skipTest("empty migration-baseline assertion is not applicable to a live vault")
        entities = ROOT / "entities"
        self.assertEqual({path.name for path in entities.iterdir() if path.is_dir()}, DOMAINS)
        for domain in DOMAINS:
            folder = entities / domain
            with self.subTest(domain=domain):
                names = {path.name for path in folder.iterdir() if path.is_file()}
                self.assertTrue({"index.md", "catalog.md", "log.md"} <= names)
                allowed_records = (
                    {
                        "validate-publisher-location-during-enrichment.md",
                        "enrich-reusable-topic-and-tone-sentiment.md",
                        "support-english-and-bahasa-indonesia.md",
                    }
                    if domain == "decisions" else set()
                )
                self.assertEqual(names - SYSTEM_NAMES, allowed_records)
                catalog = (folder / "catalog.md").read_text(encoding="utf-8")
                log = (folder / "log.md").read_text(encoding="utf-8")
                if domain == "decisions":
                    self.assertRegex(catalog, r"(?:note_count: 3|Note count:\*\* 3)")
                    self.assertIn("entry_count: 3", log)
                    self.assertRegex(log, r"(?m)^- 2026-07-31T")
                else:
                    self.assertRegex(catalog, r"(?:note_count: 0|Note count:\*\* 0)")
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
        """Credentials and generated artifacts must never be committed.

        The rule is about what Git tracks, not what sits in an operator's
        working directory: `README.md` explicitly instructs operators to create
        an ignored local `.env.local`, so scanning the working tree would fail
        on a correctly configured live vault. Tracked files are the assertion;
        the working-tree scan is only a fallback for archives without Git.
        """

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

        candidates = None
        try:
            tracked = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=ROOT, capture_output=True, check=True, text=True,
            )
            candidates = [
                pathlib.Path(name)
                for name in tracked.stdout.split("\0")
                if name
            ]
        except (OSError, subprocess.CalledProcessError):
            candidates = None

        if candidates is None:
            candidates = [
                path.relative_to(ROOT)
                for path in ROOT.rglob("*")
                if path.is_file()
            ]

        findings = sorted(
            str(rel) for rel in candidates
            if not excluded_parts.intersection(rel.parts)
            and (rel.name in forbidden_names or rel.suffix.lower() in forbidden_suffixes)
        )
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
