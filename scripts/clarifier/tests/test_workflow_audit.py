"""Task 23 actual YAML capability regression checks, not a YAML parser."""
import unittest
from clarifier.shared import constants as c
from clarifier.controls import policy as p
from clarifier.github import workflow_audit as audit


class AuditTests(unittest.TestCase):
    def test_actual_workflows(self): self.assertEqual(audit.run()['jobs']['stop'][1],'actions:write')

    def test_unsafe_permission_secret_or_stop_dependency_rejected(self):
        folder=c.ROOT/'.github/workflows'
        triage=(folder/p.TRIAGE_WORKFLOW).read_text();stop=(folder/p.STOP_WORKFLOW).read_text()
        for t,s in ((triage.replace('contents: read','contents: write'),stop),
                    (triage.replace('  cancel-in-progress: false','  cancel-in-progress: false\n  queue: max'),stop),
                    (triage,stop+'\nconcurrency: triage\n'),
                    (triage+'\n# secrets.ANY\n',stop),
                    (triage.replace(audit.PINS['actions/checkout'],'a'*40),stop)):
            with self.assertRaises(p.PlatformError):audit.inspect(t,s)
