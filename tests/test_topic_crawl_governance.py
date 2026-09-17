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


STATE = module("initialize_topic_crawl_state")
GOAL = module("topic_crawl_goal_runner")
REGISTRY = module("sync_canonical_topics")


class TopicCrawlGovernanceTests(unittest.TestCase):
    def test_initialize_adds_crawl_checkpoint_without_claiming_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "topic-a.md").write_text(
                "---\ntype: entity\nsubtype: topic\ndisplayName: Topic A\narticleCount: 7\n---\n\n# Topic A\n",
                encoding="utf-8",
            )
            (root / "log.md").write_text("", encoding="utf-8")
            original = STATE.TOPIC_ROOT
            try:
                STATE.TOPIC_ROOT = root
                self.assertEqual(STATE.initialize(True)["changed"], 1)
                STATE.initialize(False)
                note = (root / "topic-a.md").read_text(encoding="utf-8")
                self.assertIn("crawlStatus: Not started", note)
                self.assertIn("lastCrawledAt: null", note)
                self.assertEqual(STATE.validate()["failures"], 0)
            finally:
                STATE.TOPIC_ROOT = original

    def test_held_candidate_reconciles(self):
        state = {"status": "running", "topics": ["topic-a"], "topicCompletion": {"topic-a": {"status": "completed", "verifiedAt": "2026-09-17T00:00:00Z"}}, "criticalEvents": []}
        candidate = {"_line": 1, "candidateId": "one", "topicId": "topic-a", "set": "A", "canonicalUrl": "https://example.test/a", "disposition": "held", "holdStage": "retrieval", "reason": "Source body was unavailable after bounded retries."}
        self.assertTrue(GOAL.validate(state, [candidate])["valid"])

    def test_unresolved_critical_event_prevents_closure(self):
        state = {"status": "running", "topics": ["topic-a"], "topicCompletion": {"topic-a": {"status": "completed", "verifiedAt": "2026-09-17T00:00:00Z"}}, "criticalEvents": [{"kind": "credential-rejected", "resolved": False}]}
        self.assertFalse(GOAL.validate(state, [])["valid"])

    def test_registry_keeps_filename_ids_and_bilingual_scope(self):
        value = REGISTRY.registry()
        self.assertEqual(len(value["topics"]), len({row["topicId"] for row in value["topics"]}))
        self.assertEqual(value["scope"]["languages"], ["eng", "ind"])


if __name__ == "__main__":
    unittest.main()
