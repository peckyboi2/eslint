"""Task 19 orchestration infrastructure tests, no live GitHub effects."""
import unittest
from unittest.mock import Mock,patch
from clarifier.controls import identity
from clarifier.controls import policy as p
from clarifier import workflow
from clarifier.github import workflow_io as io
from clarifier.tests.test_identity import context_data


class WorkflowTests(unittest.TestCase):
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
