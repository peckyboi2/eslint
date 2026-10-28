"""Deterministic infrastructure tests for tasks 08–15 and R1; no model inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from clarifier.shared import constants as c
from clarifier.shared import errors
from clarifier.inference import recording as rec
from clarifier.inference import request as req
from clarifier.inference import skill


class NativeLoading(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        self.incoming = {"model": self.config["model"], "instructions": "trusted skill", "tools": [{"name": "shell"}],
                         "input": [{"role": "developer", "content": [{"text": "private host context"}]},
                                   {"role": "user", "content": [{"text": "approved evidence"}]}]}

    def test_native_developer_loading_and_duplicate_rejection(self):
        incoming = copy.deepcopy(self.incoming)
        incoming.pop("instructions")
        incoming["input"].insert(0, {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "trusted skill"}]})
        result = req.prepare_request(incoming, "trusted skill\n", "approved evidence", self.config)
        self.assertEqual(result["input"][0]["content"][0]["text"], "trusted skill")
        incoming["input"].append(copy.deepcopy(incoming["input"][0]))
        with self.assertRaises(ValueError):
            req.prepare_request(incoming, "trusted skill\n", "approved evidence", self.config)


class VerifiedSkill(unittest.TestCase):
    def test_exact_canonical_bytes_and_digest_are_recorded(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            source = root / c.SKILL_PATH
            source.parent.mkdir(parents=True)
            source.write_text('trusted skill\n')
            session = rec.start_run(True, root, lambda: 'fixed-time', lambda: 'fixed-id')
            session.config = {'skill_sha256': rec.sha(source.read_bytes())}
            loaded = skill.load_verified(session, root / 'workspace')
            self.assertEqual(loaded.path.read_bytes(), source.read_bytes())
            self.assertEqual(loaded.sha256, session.record['skill_sha256'])
            self.assertEqual(loaded.text, 'trusted skill\n')
            with self.assertRaises(errors.ClarifierError):
                skill.load_verified(session, root / 'workspace')

    def test_probe_discards_private_host_context(self):
        incoming = {'instructions': 'skill', 'input': [{'role': 'developer', 'content': [{'text': 'private-host'}]}]}
        self.assertNotIn('private-host', json.dumps(skill.native_probe(incoming, 'skill')))
        self.assertEqual(skill.loader_evidence(incoming, 'skill')['outbound_tools'], [])
