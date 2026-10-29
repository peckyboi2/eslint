"""Synthetic issue identity tests with no provider/public capability. Serves B01."""
from copy import deepcopy
import unittest
from unittest.mock import Mock

from clarifier.controls import intake_identity as gate, policy as p


def fixture():
    """Return synthetic trusted context and issue event."""
    repo = dict(id=p.REPOSITORY_ID, full_name=p.REPOSITORY, default_branch='main',
                owner=dict(id=p.OWNER_ID, login=p.OWNER))
    user = dict(id=42, login='new-reporter', type='User')
    data = dict(event_name='issues', repository=p.REPOSITORY, repository_id=str(p.REPOSITORY_ID),
                repository_owner=p.OWNER, repository_owner_id=str(p.OWNER_ID), ref=p.TRUSTED_REF,
                ref_type='branch', run_attempt='1', sha='a'*40, workflow_sha='a'*40,
                workflow_ref=f'{p.REPOSITORY}/.github/workflows/{p.TRIAGE_WORKFLOW}@{p.TRUSTED_REF}',
                run_id='100', actor='new-reporter', actor_id='42', triggering_actor='new-reporter')
    issue = dict(id=800, number=7, title='Bug: synthetic', body='untrusted report',
                 user=user, state='open', locked=False, created_at='2026-10-29T00:00:00Z',
                 updated_at='2026-10-29T00:00:00Z', html_url=f'https://github.com/{p.REPOSITORY}/issues/7')
    return data, dict(action='opened', repository=repo, issue=issue, sender=user)


class IntakeIdentityTests(unittest.TestCase):
    def test_new_reporter(self):
        data, event = fixture()
        ctx = gate.verify(data, event)
        self.assertEqual((ctx.event_name, ctx.issue_id, ctx.issue_number), ('issues',800,7))

    def test_rejections_have_no_effect(self):
        data, event = fixture()
        for field, value in [('repository_id','1'),('ref','refs/heads/evil'),('run_attempt','2'),
                             ('workflow_sha','b'*40),('event_name','issue_comment'),('triggering_actor',p.OWNER)]:
            with self.subTest(field=field):
                provider, public = Mock(), Mock()
                wrong = {**data, field:value}
                with self.assertRaises(p.IdentityError): gate.verify(wrong,event)
                provider.assert_not_called(); public.assert_not_called()
        for field, value in [('action','edited'),('repository',{}),('issue',{}),('sender',{})]:
            wrong = {**event,field:value}
            with self.assertRaises(p.IdentityError): gate.verify(data,wrong)

    def test_live_new_user_and_rerun(self):
        data, event = fixture(); ctx = gate.verify(data,event)
        run = dict(id=100,run_attempt=1,event='issues',head_branch='main',head_sha='a'*40,
                   path=f'.github/workflows/{p.TRIAGE_WORKFLOW}',actor=event['sender'],triggering_actor=event['sender'])
        gate.verify_live(ctx,run,event['repository'],{})
        run['triggering_actor'] = dict(id=p.OWNER_ID,login=p.OWNER)
        with self.assertRaises(p.IdentityError): gate.verify_live(ctx,run,event['repository'],{})
