"""Actual YAML queue contract checks; no hosted scheduling claim. Serves B05."""
import unittest
from clarifier.shared import constants as c, intake_constants as k


class QueueTests(unittest.TestCase):
    def test_bounded_platform_queue_without_pending_replacement(self):
        text=(c.ROOT/'.github/workflows/clarifier-triage.yml').read_text()
        self.assertEqual(text.count('concurrency:'),1)
        self.assertIn('queue: max',text)
        self.assertIn('cancel-in-progress: false',text)
        self.assertNotIn('cancel-in-progress: true',text)
        self.assertEqual(k.MAX_PENDING,100)

    def test_stop_has_no_queue_dependency(self):
        text=(c.ROOT/'.github/workflows/clarifier-stop.yml').read_text()
        self.assertNotIn('concurrency:',text)
        self.assertNotIn('needs:',text)
        self.assertNotIn('issues: write',text)
