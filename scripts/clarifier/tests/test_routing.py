"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import json
import unittest

from clarifier.shared import constants as c
from clarifier.outputs import routing as route


class Decisions(unittest.TestCase):
    def result(self, decision="clarify", comment="Could you supply the referenced file so the setup can be reconstructed?"):
        return {"decision": decision, "rationale": "A referenced input is absent.", "clarification": comment}

    def test_all_routes_and_trusted_identity(self):
        for decision in ("clarify", "no_action", "human_review"):
            obj = self.result(decision, "Could you supply `@scope/package` configuration?" if decision == "clarify" else None)
            routed = route.route(json.dumps(obj), "fixture", "fixture-model")
            self.assertTrue(routed["valid"])
            self.assertEqual(routed["public_actions"], [])
            self.assertIsNone(routed["posting_target"])
            self.assertEqual(routed["repository_id"], 1435519573)
            self.assertEqual(routed["preview_comment"] is not None, decision == "clarify")
            if decision == "clarify":
                self.assertIn("Created by AI", routed["preview_comment"])

    def test_invalid_results_stay_silent(self):
        good = self.result()
        cases = ["not json", json.dumps([good]), json.dumps(good) + json.dumps(good),
                 '{"decision":"clarify","decision":"no_action","rationale":"x","clarification":null}',
                 json.dumps({**good, "target": 123}), json.dumps({**good, "action": "close"}),
                 json.dumps({**good, "decision": "close"}), json.dumps({**good, "clarification": None}),
                 json.dumps({**good, "rationale": " "}), json.dumps({**good, "rationale": "a" * 3001}),
                 json.dumps({**good, "rationale": []}), json.dumps({**good, "clarification": "a" * 1501}),
                 json.dumps({**good, "clarification": " "}), json.dumps({**good, "decision": "no_action"}),
                 json.dumps({**good, "decision": "human_review"}), 'NaN', 'null', 'true',
                 json.dumps({**good, "clarification": "@maintainer please act"}),
                 json.dumps({**good, "clarification": "visit https://example.com"}),
                 json.dumps({**good, "clarification": "<script>x</script>"}),
                 json.dumps({**good, "clarification": "a\u202eb"}), 'x' * 16385]
        for raw in cases:
            with self.subTest(raw=raw[:100]):
                out = route.route(raw, "fixture", "fixture-model")
                self.assertFalse(out["valid"])
                self.assertEqual(out["public_actions"], [])
                self.assertIsNone(out["preview_comment"])

    def test_bounds_and_attribution(self):
        out = route.route(json.dumps(self.result(comment="a" * 1500)), "fixture", "model")
        self.assertTrue(out["valid"])
        self.assertLessEqual(len(out["preview_comment"]), 2000)
        self.assertFalse(route.route(json.dumps(self.result()), "@bad", "model")["valid"])


class RejectedAttribution(unittest.TestCase):
    def test_attribution_rejections_have_no_public_action_or_target(self):
        raw = json.dumps({'decision': 'clarify', 'rationale': 'fixture', 'clarification': 'Missing file?'})
        for run_id, model in (('@bad', 'model'), ('fixture', '<bad>'), ('a' * c.MAX_COMMENT_CHARS, 'model')):
            with self.subTest(run_id=run_id[:20], model=model):
                rejected = route.route(raw, run_id, model)
                self.assertFalse(rejected['valid'])
                self.assertEqual(rejected['public_actions'], [])
                self.assertIsNone(rejected['preview_comment'])
                self.assertIsNone(rejected['posting_target'])
