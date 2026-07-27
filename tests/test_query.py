import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "query.py"
SPEC = importlib.util.spec_from_file_location("query_under_test", SCRIPT)
QUERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUERY)


def answered(answer="ok"):
    return {
        "answer": answer,
        "entities_resolved": ["synthetic-person"],
        "sources_cited": [],
        "status": "answered",
        "time_sensitive": False,
        "sensitive": False,
        "reused_query_id": None,
    }


class QueryFastPathTests(unittest.TestCase):
    def setUp(self):
        QUERY._CATALOG_CACHE.clear()

    def test_empty_vault_returns_no_matches_or_fast_context(self):
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(QUERY, "ENTITIES", pathlib.Path(folder)):
                self.assertEqual(QUERY._catalog_entity_matches("Who is anyone?"), [])
                self.assertIsNone(QUERY.build_fast_context("Who is anyone?"))

    def test_empty_vault_query_returns_no_matching_data_without_api(self):
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(QUERY, "ENTITIES", pathlib.Path(folder)), \
             mock.patch.object(QUERY, "load_local_env"), \
             mock.patch.dict(os.environ, {}, clear=True):
            QUERY._CATALOG_CACHE.clear()
            result = QUERY.run_query("What happened?", cache_write=False)
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("No matching data", result["answer"])
        self.assertFalse(result["cache_written"])

    def test_exact_name_alias_and_acronym_resolution_uses_synthetic_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            entities = pathlib.Path(folder)
            people = entities / "people"
            people.mkdir()
            (people / "catalog.md").write_text(
                "| id | displayName | aliases | acronyms | File |\n"
                "|---|---|---|---|---|\n"
                "| synthetic-person | Synthetic Person | Example Leader | SP | "
                "[synthetic-person.md](synthetic-person.md) |\n",
                encoding="utf-8",
            )
            with mock.patch.object(QUERY, "ENTITIES", entities):
                QUERY._CATALOG_CACHE.clear()
                matches = QUERY._catalog_entity_matches("Who is Example Leader?")
            self.assertEqual(
                [(item["domain"], item["id"]) for item in matches],
                [("people", "synthetic-person")],
            )

    def test_query_shape_classification_is_corpus_independent(self):
        appointment = [{
            "domain": "appointments", "id": "example-office",
            "displayName": "Example Office", "file": "example-office.md",
        }]
        cases = {
            "Who is the president?": ("identity", []),
            "Tell me more about parliament": ("coverage", []),
            "How is the cabinet related to parliament?": ("relationship", []),
            "Give me a list of people related to reform": ("roster", []),
            "Who is the current office holder?": ("appointment", appointment),
            "There is no corruption issue, correct?": ("existence", []),
        }
        for question, (expected, matches) in cases.items():
            with self.subTest(question=question):
                self.assertEqual(QUERY._query_shape(question, matches), expected)

    def test_fast_model_uses_one_low_reasoning_request_and_filters_sources(self):
        payload = answered()
        payload["entities_resolved"].append("invented")
        payload["sources_cited"] = ["article/2026-01/synthetic-source", "invented"]
        response = {
            "output": [{
                "type": "function_call",
                "name": "submit_answer",
                "arguments": json.dumps(payload),
            }]
        }
        context = {
            "resolved_entities": [{"id": "synthetic-person"}],
            "shared_coverage": [],
            "entities": [{
                "coverage_evidence": [{
                    "target": "article/2026-01/synthetic-source",
                    "label": "Synthetic source",
                }],
            }],
        }
        with mock.patch.object(QUERY, "_call_responses", return_value=response) as call:
            result = QUERY._run_fast_model(
                "key", "gpt-5.6", "question", context
            )
        self.assertEqual(result["answer"], "ok")
        self.assertEqual(result["entities_resolved"], ["synthetic-person"])
        self.assertEqual(result["sources_cited"], ["synthetic-source"])
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs["reasoning_effort"], "low")
        self.assertEqual(
            call.call_args.kwargs["tool_choice"],
            {"type": "function", "name": "submit_answer"},
        )

    def test_supported_query_routes_to_fast_model_without_fallback(self):
        match = [{
            "domain": "people", "id": "synthetic-person",
            "displayName": "Synthetic Person", "file": "synthetic-person.md",
            "matched": "Synthetic Person", "score": "100",
        }]
        context = {"resolved_entities": match, "shared_coverage": [], "entities": []}
        with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "QUERY_FAST_PATH": "true",
        }, clear=False), \
             mock.patch.object(QUERY, "load_local_env"), \
             mock.patch.object(QUERY, "_catalog_entity_matches", return_value=match), \
             mock.patch.object(QUERY, "build_fast_context", return_value=context), \
             mock.patch.object(QUERY, "_vault_has_queryable_data", return_value=True), \
             mock.patch.object(QUERY, "_run_fast_model", return_value=answered()) as fast, \
             mock.patch.object(QUERY, "_run_legacy_model") as legacy:
            result = QUERY.run_query(
                "Who is Synthetic Person?", cache_read=False, cache_write=False
            )
        self.assertEqual(fast.call_count, 1)
        legacy.assert_not_called()
        self.assertFalse(result["cache_written"])
        self.assertFalse(result["sensitive"])

    def test_ambiguous_resolution_routes_to_legacy_fallback(self):
        ambiguous = [
            {"domain": "people", "id": "one", "displayName": "One",
             "file": "one.md", "matched": "One", "score": "100"},
            {"domain": "people", "id": "two", "displayName": "Two",
             "file": "two.md", "matched": "Two", "score": "100"},
        ]
        with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "QUERY_FAST_PATH": "true",
        }, clear=False), \
             mock.patch.object(QUERY, "load_local_env"), \
             mock.patch.object(QUERY, "_catalog_entity_matches", return_value=ambiguous), \
             mock.patch.object(QUERY, "_vault_has_queryable_data", return_value=True), \
             mock.patch.object(QUERY, "_run_fast_model") as fast, \
             mock.patch.object(QUERY, "_run_legacy_model",
                               return_value=answered("legacy")) as legacy:
            result = QUERY.run_query(
                "Who is One?", cache_read=False, cache_write=False
            )
        fast.assert_not_called()
        self.assertEqual(legacy.call_count, 1)
        self.assertEqual(result["answer"], "legacy")

    def test_cache_read_and_rollback_switch_preserve_legacy_path(self):
        for environment, cache_read in (
            ({"QUERY_FAST_PATH": "true"}, True),
            ({"QUERY_FAST_PATH": "false"}, False),
        ):
            with self.subTest(environment=environment, cache_read=cache_read), \
                 mock.patch.dict(os.environ, {
                     "OPENAI_API_KEY": "test-key", **environment,
                 }, clear=False), \
                 mock.patch.object(QUERY, "load_local_env"), \
                 mock.patch.object(QUERY, "_vault_has_queryable_data", return_value=True), \
                 mock.patch.object(QUERY, "_run_fast_model") as fast, \
                 mock.patch.object(QUERY, "_run_legacy_model",
                                   return_value=answered("legacy")) as legacy:
                result = QUERY.run_query(
                    "Who is Synthetic Person?",
                    cache_read=cache_read,
                    cache_write=False,
                )
            fast.assert_not_called()
            self.assertEqual(legacy.call_count, 1)
            self.assertEqual(result["answer"], "legacy")

    def test_fast_answer_keeps_cache_write_behavior(self):
        match = [{
            "domain": "people", "id": "synthetic-person",
            "displayName": "Synthetic Person", "file": "synthetic-person.md",
            "matched": "Synthetic Person", "score": "100",
        }]
        with mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "QUERY_FAST_PATH": "true",
        }, clear=False), \
             mock.patch.object(QUERY, "load_local_env"), \
             mock.patch.object(QUERY, "_catalog_entity_matches", return_value=match), \
             mock.patch.object(QUERY, "build_fast_context", return_value={
                 "resolved_entities": match, "shared_coverage": [], "entities": [],
             }), \
             mock.patch.object(QUERY, "_vault_has_queryable_data", return_value=True), \
             mock.patch.object(QUERY, "_run_fast_model", return_value=answered()), \
             mock.patch.object(QUERY, "persist_answer",
                               return_value={"query_id": "saved"}) as persist:
            result = QUERY.run_query(
                "Who is Synthetic Person?", cache_read=False, cache_write=True
            )
        persist.assert_called_once()
        self.assertTrue(result["cache_written"])
        self.assertEqual(result["query_id"], "saved")

    def test_submit_tool_uses_general_sensitive_flag(self):
        schema = next(
            tool for tool in QUERY.build_tools(cache_read=False)
            if tool["name"] == "submit_answer"
        )
        properties = schema["parameters"]["properties"]
        self.assertIn("sensitive", properties)
        self.assertNotIn("saf", properties)


if __name__ == "__main__":
    unittest.main()
