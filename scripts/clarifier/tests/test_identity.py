"""Task 16 infrastructure checks; rejects reach no model or public effect."""
import unittest
from unittest.mock import Mock

from clarifier.controls import identity
from clarifier.controls import policy as p


def context_data(workflow=p.TRIAGE_WORKFLOW):
    return dict(event_name='workflow_dispatch', repository=p.REPOSITORY,
                repository_id=str(p.REPOSITORY_ID), repository_owner=p.OWNER,
                repository_owner_id=str(p.OWNER_ID), actor=p.OWNER, actor_id=str(p.OWNER_ID),
                triggering_actor=p.OWNER, ref=p.TRUSTED_REF, ref_type='branch',
                workflow_ref=f'{p.REPOSITORY}/.github/workflows/{workflow}@{p.TRUSTED_REF}',
                sha='a'*40, workflow_sha='a'*40, run_id='123', run_attempt='1')


class IdentityTests(unittest.TestCase):
    def test_missing_or_changed_fields_never_reach_effect(self):
        for key in context_data():
            for value in (None, 'wrong'):
                with self.subTest(key=key, value=value):
                    data = context_data(); data[key] = value
                    model, public_write = Mock(), Mock()
                    with self.assertRaises(p.IdentityError):
                        identity.verify(data); model(); public_write()
                    model.assert_not_called(); public_write.assert_not_called()

    def test_stop_and_rerun_share_gate(self):
        data = context_data(p.STOP_WORKFLOW); data['run_attempt'] = '2'
        self.assertEqual(identity.verify(data, p.STOP_WORKFLOW).attempt, 2)

    def test_live_rerun_identity_is_pinned(self):
        ctx = identity.verify(context_data())
        actor = dict(id=p.OWNER_ID, login=p.OWNER)
        repo = dict(id=p.REPOSITORY_ID, full_name=p.REPOSITORY, owner=actor, default_branch='main')
        run = dict(id=123, run_attempt=1, event='workflow_dispatch', head_branch='main',
                   head_sha='a'*40, actor=actor, triggering_actor=actor, path='.github/workflows/'+p.TRIAGE_WORKFLOW)
        identity.verify_live(ctx, run, repo, actor)
        for field in ('actor', 'triggering_actor'):
            changed = {**run, field: {**actor, 'id': 1}}
            with self.assertRaises(p.IdentityError): identity.verify_live(ctx, changed, repo, actor)
        with self.assertRaises(p.IdentityError): identity.verify_live(ctx, run, repo, {**actor, 'id': 1})
