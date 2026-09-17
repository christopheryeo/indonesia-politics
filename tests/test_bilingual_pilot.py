import pathlib
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import bilingual_pilot as PILOT  # noqa: E402


class BilingualPilotTests(unittest.TestCase):
    def test_twenty_case_pilot_passes_against_synthetic_bilingual_entities(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            organisations = root / "organisations"
            place = root / "place"
            organisations.mkdir()
            place.mkdir()
            seen = set()
            for pair in PILOT.PAIRS:
                english_alias, bahasa_alias, slug = pair[7], pair[8], pair[9]
                if slug in seen:
                    continue
                seen.add(slug)
                domain = place if slug in {"presidential-palace-complex", "jakarta"} else organisations
                (domain / f"{slug}.md").write_text(
                    "---\n"
                    f"displayName: '{bahasa_alias}'\n"
                    f"aliases: ['{bahasa_alias}', '{english_alias}']\n"
                    "---\n",
                    encoding="utf-8",
                )
            with mock.patch.object(PILOT, "ENTITY_ROOT", root):
                result = PILOT.run_pilot(repetitions=2, max_avg_ms=50.0)
        self.assertEqual(result["cases"], 20)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["gates"].values()))


if __name__ == "__main__":
    unittest.main()
