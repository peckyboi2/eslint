"""Constants/schema consistency for tasks 08–15 and R1; infrastructure only."""
import json
import unittest
import constants as c
import recording


class ConstantPolicy(unittest.TestCase):
    def test_schema_and_configuration_share_trusted_limits(self):
        config = json.loads((c.ROOT / c.CONFIG_PATH).read_text())
        self.assertEqual(recording.validate_configuration(config), config)
        schema = json.loads((c.ROOT / c.SCHEMA_PATH).read_text())
        self.assertEqual(set(schema['required']), c.RESULT_KEYS)
        self.assertEqual(schema['properties'][c.DECISION]['enum'], list(c.ALLOWED_DECISIONS))
        self.assertEqual(schema['properties'][c.RATIONALE]['maxLength'], c.MAX_RATIONALE_CHARS)
        self.assertEqual(schema['properties'][c.CLARIFICATION]['maxLength'], c.MAX_CLARIFICATION_CHARS)

    def test_snapshot_covers_every_runtime_module(self):
        modules = {path.name for path in c.HERE.glob('*.py') if not path.name.startswith('test_')}
        self.assertEqual(modules, {f'{name}.py' for name in c.MODULE_NAMES})
        self.assertEqual(len(c.CONFIG_PATHS), len(set(c.CONFIG_PATHS)))
