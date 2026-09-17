"""Outlet identity resolution during cascade.

Feed intake supplies human display names; crawl intake often supplies the
machine slug of the same publisher. Before this was handled, a crawl batch
naming "liputan6-com" created a second note beside the existing "Liputan 6",
splitting article counts across duplicate records. These tests pin both
directions: known aliases of one publisher must collapse, and separate regional
editions must not.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from ingest_cascade import outlet_identity_keys, resolve_outlet_by_identity  # noqa: E402


class _Record:
    def __init__(self, display, aliases=None):
        self.display = display
        self.aliases = aliases or []


def collides(left, right):
    return bool(outlet_identity_keys(left) & outlet_identity_keys(right))


class OutletIdentityKeyTests(unittest.TestCase):
    def test_machine_slug_matches_display_name_of_same_publisher(self):
        for slug, display in [
            ("liputan6-com", "Liputan 6"),
            ("antara", "ANTARA News"),
            ("jpnn-com", "Jawa Pos National Network"),
            ("media-indonesia", "Media Indonesia - News & Views -"),
            ("kompas-com", "Kompas"),
            ("tirto-id", "tirto.id"),
        ]:
            with self.subTest(slug=slug):
                self.assertTrue(collides(slug, display))

    def test_distinct_publishers_and_regional_editions_stay_separate(self):
        for left, right in [
            ("antara-news-kepri", "ANTARA News"),
            ("antara-news-mataram", "antara-news-kepri"),
            ("detik-bali", "detik News"),
            ("tribun-jogja", "Tribun Jateng"),
            ("tribun-medan", "Tribun Manado"),
            ("okezone-news", "Okezone Economy"),
        ]:
            with self.subTest(pair=(left, right)):
                self.assertFalse(collides(left, right))

    def test_two_word_names_do_not_collapse_to_a_shared_acronym(self):
        """"Tribun Jogja" and "Tribun Jateng" would both yield "tj"."""

        self.assertNotIn("tj", outlet_identity_keys("Tribun Jogja"))
        self.assertIn("jpnn", outlet_identity_keys("Jawa Pos National Network"))

    def test_empty_and_punctuation_only_labels_are_safe(self):
        for label in ["", None, "   ", "---", "&"]:
            with self.subTest(label=label):
                self.assertEqual(outlet_identity_keys(label), set())


class OutletResolutionTests(unittest.TestCase):
    def setUp(self):
        self.records = {
            "liputan-6": _Record("Liputan 6"),
            "antara-news": _Record("ANTARA News"),
            "antara-news-kepri": _Record("ANTARA News Kepri"),
            "tribun-jogja": _Record("Tribun Jogja"),
            "tribun-jateng": _Record("Tribun Jateng"),
        }

    def test_resolves_slug_to_existing_note(self):
        self.assertEqual(resolve_outlet_by_identity("liputan6-com", self.records), "liputan-6")
        self.assertEqual(resolve_outlet_by_identity("antara", self.records), "antara-news")

    def test_unknown_publisher_creates_its_own_note(self):
        self.assertIsNone(resolve_outlet_by_identity("Some Brand New Outlet", self.records))

    def test_regional_edition_does_not_absorb_into_parent(self):
        self.assertIsNone(resolve_outlet_by_identity("antara-news-mataram", self.records))

    def test_ambiguous_match_refuses_to_guess(self):
        records = {"a-news": _Record("Example"), "b-news": _Record("Example")}
        self.assertIsNone(resolve_outlet_by_identity("example", records))

    def test_empty_label_resolves_to_nothing(self):
        self.assertIsNone(resolve_outlet_by_identity("", self.records))


if __name__ == "__main__":
    unittest.main()
