"""Pure decision validation for tasks 08, 13 and R1; infrastructure only."""
import json
import unittest
import constants as c
from errors import ValidationError
import validation as v


class StrictValidation(unittest.TestCase):
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
