"""Internal audit/stop evidence tests with no real effects. Serves C02."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from clarifier.controls import policy as p
from clarifier.github import intake_audit as audit, stop_io
from clarifier.inference import recording
from clarifier.shared import constants as c, intake_constants as k


class IntakeAuditTests(unittest.TestCase):
    def test_blocked_receipt_and_secret_redaction(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder, patch.object(k,'OUTPUT',Path(folder)):
            audit.write_phase('gate',error=p.IdentityError('Wrong repository'))
            row=json.loads((Path(folder)/'gate-audit.json').read_text())
            self.assertEqual(row['public_actions'],[])
            self.assertEqual(row['status'],'blocked')
            recording.save_json(Path(folder)/'redacted.json',{'GH_TOKEN':'secret','nested':{'CLARIFIER_PROVIDER_KEY':'key'}},['credential'])
            text=(Path(folder)/'redacted.json').read_text()
            self.assertNotIn('secret',text); self.assertNotIn('"key"',text)

    def test_stop_disables_both_without_public_write(self):
        api=Mock(); report={'errors':[]}
        stop_io.disable_triage(api,Mock(),report)
        self.assertEqual(report['disabled_workflows'],[p.TRIAGE_WORKFLOW,k.APPROVAL_WORKFLOW])
        self.assertTrue(report['workflow_disabled'])
        self.assertEqual({call.args[0] for call in api._request.call_args_list},{'PUT'})
        self.assertFalse(any('/issues/' in call.args[1] for call in api._request.call_args_list))

    def test_queue_and_approval_runs_included_in_stop_scan(self):
        api=Mock()
        def read(method,path):
            return {'workflow_runs':[dict(id=1 if p.TRIAGE_WORKFLOW in path else 2,status='pending')]}
        api._request.side_effect=read
        self.assertEqual({row['id'] for row in stop_io.active_runs(api)},{1,2})
