"""Task 19 orchestration infrastructure tests, no live GitHub effects."""
import unittest
import json
from unittest.mock import Mock,patch
from clarifier.controls import identity
from clarifier.controls import policy as p
from clarifier import workflow
from clarifier.github import workflow_io as io
from clarifier.tests.test_identity import context_data


class WorkflowTests(unittest.TestCase):
    def test_waiting_run_rechecks_persisted_enabled_and_binding_before_engine(self):
        from clarifier.controls import admission
        from clarifier.github import stop_io
        from clarifier.shared import constants as c
        from clarifier.tests.test_admission import enabled
        ctx = identity.verify(context_data())
        key = admission.input_key(c.APPROVED)
        state = admission.reserve(enabled(), ctx, key, 100)
        binding = dict(run_id=ctx.run_id, attempt=ctx.attempt, sha=ctx.sha, input_key=key,
                       event_key=admission.event_key(ctx, key), source_issue=c.SOURCE_ISSUE,
                       mode='preview', configuration=io.fingerprint(), public_actions=[])
        stopped = stop_io.disabled(state, 101, 'Stopped while workflow waited')
        for current, artifact in ((stopped, binding), (state, {**binding, 'run_id': '999'}),
                                  (enabled(), binding)):
            with patch.object(io, 'StateStore') as store, patch('clarifier.preview.run') as model:
                store.return_value.read.return_value.state = current
                with self.assertRaises(p.AdmissionDenied):
                    io.infer(ctx, Mock(), artifact)
                model.assert_not_called()

    def test_real_entry_gates_reject_before_token_platform_or_mutation(self):
        from clarifier import stop
        for name, entry, phase in ((p.TRIAGE_WORKFLOW, workflow.run, 'admit'),
                                   (p.TRIAGE_WORKFLOW, workflow.run, 'infer'),
                                   (p.TRIAGE_WORKFLOW, workflow.run, 'post'),
                                   (p.STOP_WORKFLOW, stop.run, 'execute')):
            for field in context_data(name):
                data = {**context_data(name), field: None}
                with self.subTest(workflow=name, phase=phase, field=field):
                    with patch.dict(io.os.environ, {'TRUSTED_GITHUB_CONTEXT': json.dumps(data)}), \
                         patch.object(io, 'platform') as platform, \
                         patch.object(io, 'prepare_admission') as admission, \
                         patch('clarifier.preview.run') as model:
                        if name == p.STOP_WORKFLOW:
                            with self.assertRaises(p.IdentityError):
                                entry(phase)
                        else:
                            self.assertEqual(entry(phase), 1)
                        platform.assert_not_called()
                        admission.assert_not_called()
                        model.assert_not_called()

    def test_rejected_context_never_reads_token_or_admits(self):
        with patch.object(io,'context',side_effect=p.IdentityError('Rejected')), patch.object(io,'platform') as edge:
            self.assertEqual(workflow.run('admit'),1)
        edge.assert_not_called()

    def test_phase_order(self):
        with patch.object(io,'context',return_value=identity.verify(context_data())), patch.object(io,'platform',return_value=Mock()), patch.object(io,'prepare_admission') as admit:
            self.assertEqual(workflow.run('admit'),0); admit.assert_called_once()

    def test_absent_admission_precedes_engine(self):
        with patch.object(io,'StateStore') as store, patch('clarifier.preview.run') as model:
            store.return_value.read.return_value.state={}
            with self.assertRaises(p.AdmissionDenied): io.infer(identity.verify(context_data()),Mock(),{})
        model.assert_not_called()

    def test_privileged_token_read_follows_live_gate(self):
        with patch.object(io,'GitHub') as edge,patch.object(io.os.environ,'get') as getenv:
            edge.return_value.verify_context.side_effect=p.IdentityError('Rejected')
            with self.assertRaises(p.IdentityError): io.platform(identity.verify(context_data()),True)
            getenv.assert_not_called()
