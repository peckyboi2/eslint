"""Task 16 infrastructure checks; rejects reach no model or public effect."""
import unittest
from copy import deepcopy
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
    def test_context_matrix_for_triage_and_independent_stop(self):
        for workflow in (p.TRIAGE_WORKFLOW, p.STOP_WORKFLOW):
            for attempt in ('1', '2'):
                good = {**context_data(workflow), 'run_attempt': attempt}
                self.assertEqual(identity.verify(good, workflow).workflow, workflow)
                for key in good:
                    for value in (None, '', True, 0, [], {}, 'wrong'):
                        effect = Mock()
                        data = {**good, key: value}
                        with self.subTest(workflow=workflow, attempt=attempt, field=key, value=value):
                            with self.assertRaises(p.IdentityError):
                                identity.verify(data, workflow)
                                effect()
                            effect.assert_not_called()
                    data = dict(good)
                    del data[key]
                    with self.assertRaises(p.IdentityError):
                        identity.verify(data, workflow)

    def test_live_identity_matrix_includes_owner_name_and_rerun_initiator(self):
        for workflow in (p.TRIAGE_WORKFLOW, p.STOP_WORKFLOW):
            for attempt in (1, 2):
                ctx = identity.verify({**context_data(workflow), 'run_attempt': str(attempt)}, workflow)
                actor = dict(id=p.OWNER_ID, login=p.OWNER)
                repo = dict(id=p.REPOSITORY_ID, full_name=p.REPOSITORY, owner=actor, default_branch='main')
                run = dict(id=123, run_attempt=attempt, event='workflow_dispatch', head_branch='main',
                           head_sha='a'*40, actor=actor, triggering_actor=actor, path='.github/workflows/'+workflow)
                identity.verify_live(ctx, run, repo, actor)
                for record, paths in ((repo, ('id', 'full_name', 'default_branch', 'owner.id', 'owner.login')),
                                      (run, ('id', 'run_attempt', 'event', 'head_branch', 'head_sha', 'path',
                                             'actor.id', 'actor.login', 'triggering_actor.id', 'triggering_actor.login')),
                                      (actor, ('id', 'login'))):
                    for path in paths:
                        for value in (None, 'wrong'):
                            changed = deepcopy(record)
                            parts = path.split('.')
                            parent = changed if len(parts) == 1 else changed[parts[0]]
                            parent[parts[-1]] = value
                            inputs = [run, repo, actor]
                            inputs[0 if record is run else 1 if record is repo else 2] = changed
                            mutation = Mock()
                            with self.subTest(workflow=workflow, attempt=attempt, path=path, value=value):
                                with self.assertRaises(p.IdentityError):
                                    identity.verify_live(ctx, *inputs)
                                    mutation()
                                mutation.assert_not_called()

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
