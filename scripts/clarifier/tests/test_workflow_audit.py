"""Task 23 actual YAML capability regression checks, not a YAML parser."""
import unittest
from unittest.mock import Mock
from clarifier.shared import constants as c
from clarifier.controls import policy as p
from clarifier.github import workflow_audit as audit


class AuditTests(unittest.TestCase):
    def test_300_issue_events_never_reach_admission_model_or_public_write(self):
        from clarifier.controls import identity
        from clarifier.tests.test_identity import context_data
        audit.run()
        admission, model, public_write = Mock(), Mock(), Mock()
        for number in range(1, 301):
            data = {**context_data(), 'event_name': 'issues', 'run_id': str(number)}
            with self.assertRaises(p.IdentityError):
                identity.verify(data)
                admission()
                model()
                public_write()
        admission.assert_not_called()
        model.assert_not_called()
        public_write.assert_not_called()

    def test_300_released_manual_attempts_obey_hosted_caps_without_retry(self):
        from clarifier.controls import admission
        from clarifier.tests.test_admission import enabled, ctx
        state = enabled()
        admitted, rejected = [], []
        for number in range(1, 301):
            try:
                state = admission.reserve(state, ctx(number), 'a'*64, 100)
                admitted.append(number)
            except p.AdmissionDenied:
                rejected.append(number)
        self.assertEqual(len(admitted), 10)
        self.assertEqual(len(rejected), 290)
        self.assertEqual(len(state['admissions']), 10)
        self.assertEqual(state['posts'], [])
        for number in range(301, 311):
            state = admission.reserve(state, ctx(number), 'a'*64, 100+p.ROLLING_SECONDS)
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(state, ctx(311), 'a'*64, 100+2*p.ROLLING_SECONDS)
        self.assertEqual(len(state['admissions']), p.CAMPAIGN_LIMIT)
        self.assertEqual(state['posts'], [])

    def test_actual_workflows(self): self.assertEqual(audit.run()['jobs']['stop'][1],'actions:write')

    def test_provider_key_is_allowed_only_on_the_inference_command(self):
        folder=c.ROOT/'.github/workflows'
        triage=(folder/p.TRIAGE_WORKFLOW).read_text(); stop=(folder/p.STOP_WORKFLOW).read_text()
        audit.inspect(triage,stop)
        secret='          CLARIFIER_PROVIDER_KEY: ${{ secrets.CLARIFIER_PROVIDER_KEY }}\n'
        mutations=(triage.replace(secret,''),
                   triage.replace('permissions: {}','permissions: {}\nenv:\n  KEY: ${{ secrets.CLARIFIER_PROVIDER_KEY }}'),
                   triage.replace('CLARIFIER_PROVIDER_KEY','ANOTHER_KEY'),
                   triage.replace('  gate:\n','  gate:\n    env:\n'+secret),
                   triage.replace('  inference:\n','  inference:\n    env:\n'+secret),
                   triage.replace('        run: python3 -B scripts/clarifier/workflow.py infer','        run: echo provider-key'))
        for mutated in mutations:
            with self.subTest(workflow=mutated), self.assertRaises(p.PlatformError):
                audit.inspect(mutated,stop)

    def test_runtime_install_and_metadata_permissions_are_required(self):
        folder=c.ROOT/'.github/workflows'
        triage=(folder/p.TRIAGE_WORKFLOW).read_text(); stop=(folder/p.STOP_WORKFLOW).read_text()
        for before,after in (('      actions: read\n',''),('      issues: read\n',''),(' --github-path','')):
            with self.subTest(removed=before), self.assertRaises(p.PlatformError):
                audit.inspect(triage.replace(before,after),stop)

    def test_preview_archive_requires_hidden_skill_and_bounded_directory(self):
        folder=c.ROOT/'.github/workflows'
        triage=(folder/p.TRIAGE_WORKFLOW).read_text(); stop=(folder/p.STOP_WORKFLOW).read_text()
        for before,after in (('          include-hidden-files: true\n',''),
                             ('include-hidden-files: true','include-hidden-files: false'),
                             ('path: evals/automatic-workflow','path: .')):
            with self.subTest(change=after), self.assertRaises(p.PlatformError):
                audit.inspect(triage.replace(before,after),stop)

    def test_unsafe_permission_secret_or_stop_dependency_rejected(self):
        folder=c.ROOT/'.github/workflows'
        triage=(folder/p.TRIAGE_WORKFLOW).read_text();stop=(folder/p.STOP_WORKFLOW).read_text()
        for t,s in ((triage.replace('contents: read','contents: write'),stop),
                    (triage.replace('  cancel-in-progress: false','  cancel-in-progress: false\n  queue: max'),stop),
                    (triage,stop+'\nconcurrency: triage\n'),
                    (triage+'\n# secrets.ANY\n',stop),
                    (triage.replace(audit.PINS['actions/checkout'],'a'*40),stop)):
            with self.assertRaises(p.PlatformError):audit.inspect(t,s)
