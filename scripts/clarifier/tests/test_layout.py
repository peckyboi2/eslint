"""R3 package integration checks; no inference, GitHub call or public write."""
from pathlib import Path
import subprocess
import sys
import unittest

from clarifier.shared import constants as c, errors
from clarifier.controls import policy
from clarifier.inference import transport


class PackageLayoutTests(unittest.TestCase):
    def test_existing_cli_commands_load_from_outside_checkout(self):
        for name in ('preview', 'c_preview', 'workflow', 'stop'):
            with self.subTest(command=name):
                result = subprocess.run(
                    [sys.executable, '-B', str(c.HERE / f'{name}.py'), '--help'],
                    cwd=c.PRIVATE_TEMP_ROOT, capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout)

    def test_packages_share_the_same_typed_error_boundary(self):
        self.assertIs(transport.ClarifierError, errors.ClarifierError)
        self.assertTrue(issubclass(policy.IdentityError, errors.ClarifierError))
        self.assertTrue(issubclass(policy.PostingBlocked, errors.ClarifierError))
