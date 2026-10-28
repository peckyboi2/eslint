"""Pure decision validation for tasks 08, 13 and R1; infrastructure only."""
import json
import unittest
from clarifier.shared import constants as c
from clarifier.shared.errors import ValidationError
from clarifier.outputs import validation as v


class StrictValidation(unittest.TestCase):
    def test_exact_result_bytes_and_one_byte_excess_remain_publicly_silent(self):
        from clarifier.outputs import routing
        raw = json.dumps(dict(decision='no_action', rationale='Boundary fixture.', clarification=None))
        exact = raw + ' ' * (c.MAX_OUTPUT_BYTES - len(raw.encode()))
        self.assertEqual(len(exact.encode()), c.MAX_OUTPUT_BYTES)
        self.assertEqual(v.parse_and_validate(exact)['decision'], 'no_action')
        blocked = routing.route(exact + ' ', 'size-test', 'fixture-model')
        self.assertFalse(blocked['valid'])
        self.assertEqual(blocked['public_actions'], [])
        self.assertIsNone(blocked['preview_comment'])

    def test_schema_boundaries_are_exact(self):
        result = {'decision': c.CLARIFY, 'rationale': 'r' * c.MAX_RATIONALE_CHARS,
                  'clarification': 'c' * c.MAX_CLARIFICATION_CHARS}
        self.assertEqual(v.parse_and_validate(json.dumps(result)), result)
        for key in (c.RATIONALE, c.CLARIFICATION):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                v.parse_and_validate(json.dumps({**result, key: result[key] + 'x'}))

    def test_json_and_structural_failures_are_typed(self):
        for raw in ('NaN', 'Infinity', '{"a":1,"a":2}', '{', '[]', 'null', '\ud800'):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValidationError):
                v.parse_and_validate(raw)

    def test_hidden_controls_and_unsafe_wording_rejected(self):
        for text in ('\x00', '\t', '\u202e', '\ud800', '@person', 'www.example.com',
                     '[x](target)', '```shell```', '<html>'):
            with self.subTest(text=repr(text)), self.assertRaises(ValidationError):
                v.validate_clarification(text)
        self.assertTrue(v.safe_text('visible\ntext', 20))
        self.assertFalse(v.safe_text([], 20))
        v.validate_clarification('Could you share `@scope/package`?')
