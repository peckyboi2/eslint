"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import copy
import json
from pathlib import Path
import unittest

from clarifier.shared import constants as c
from clarifier.shared import errors
from clarifier.inference import request as req


class CapabilityBoundary(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        self.incoming = {"model": self.config["model"], "instructions": "trusted skill", "tools": [{"name": "shell"}],
                         "input": [{"role": "developer", "content": [{"text": "private host context"}]},
                                   {"role": "user", "content": [{"text": "approved evidence"}]}]}

    def test_only_exact_skill_and_evidence_cross_boundary(self):
        self.incoming["previous_response_id"] = "prior-session"
        self.incoming["input"].append({"role": "assistant", "content": [{"text": "old answer"}]})
        result = req.prepare_request(self.incoming, "trusted skill", "approved evidence", self.config)
        self.assertEqual(result["tools"], [])
        self.assertEqual(result["tool_choice"], "none")
        self.assertEqual(result["input"][1:], [{"role": "user", "content": [{"type": "input_text", "text": "approved evidence"}]}])
        self.assertNotIn("previous_response_id", result)
        self.assertNotIn("private host context", json.dumps(result))
        self.assertNotIn("old answer", json.dumps(result))
        for key in ("instructions", "model"):
            altered = copy.deepcopy(self.incoming)
            altered[key] = "altered"
            with self.assertRaises(ValueError):
                req.prepare_request(altered, "trusted skill", "approved evidence", self.config)
        with self.assertRaises(ValueError):
            req.prepare_request(self.incoming, "trusted skill", "different prompt", self.config)


class RestrictedSettings(unittest.TestCase):
    def test_generated_settings_disable_all_exposed_features(self):
        import tomllib
        config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        settings = tomllib.loads(req.make_config('http://127.0.0.1:12345', Path('/skill'), config, True))
        self.assertEqual(settings['sandbox_mode'], 'read-only')
        self.assertEqual(settings['approval_policy'], 'never')
        self.assertFalse(settings['model_providers']['preview_guard']['requires_openai_auth'])
        self.assertTrue(settings['features']['skip_host_skill_discovery'])
        for feature in c.DISABLED_FEATURES:
            self.assertIs(settings['features'][feature], False)

    def test_malformed_envelopes_raise_typed_errors(self):
        config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        for incoming in (None, [], {'instructions': 'skill', 'input': [None]}):
            with self.subTest(incoming=incoming), self.assertRaises(errors.ClarifierError):
                req.prepare_request(incoming, 'skill', 'prompt', config)
