"""Synthetic quota/dedup bindings; no model/public effects. Serves B04."""
from dataclasses import replace
import unittest
from unittest.mock import Mock

from clarifier.controls import admission as a, intake_binding as b, intake_identity, ledger, policy as p
from clarifier.inference import live_snapshot
from clarifier.tests.test_intake_identity import fixture


def enabled():
    """Return a detached synthetic preview-enabled ledger."""
    state=ledger.initial(1,'synthetic bootstrap')
    state.update(enabled=True)
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=2,reason='synthetic enable',action='enable-preview'))
    return ledger.validate(state)


class IntakeAdmissionTests(unittest.TestCase):
    def setUp(self):
        data,event=fixture(); self.ctx=intake_identity.verify(data,event)
        self.snap=live_snapshot.capture(self.ctx,event['issue'],event['issue'])
        self.key=a.input_key(self.snap.hashes)
        self.provider,self.public=Mock(),Mock()

    def tearDown(self):
        self.provider.assert_not_called(); self.public.assert_not_called()

    def test_dedup_ignores_new_run_and_changed_source(self):
        state=a.reserve(enabled(),self.ctx,self.key,10)
        for ctx,key in [(replace(self.ctx,run_id='101'),self.key),
                        (replace(self.ctx,run_id='102'),'b'*64),(replace(self.ctx,attempt=2),self.key)]:
            with self.assertRaises(p.AdmissionDenied): a.reserve(state,ctx,key,11)
        self.assertEqual(len(state['admissions']),1)

    def test_binding_swaps_and_missing_reservation(self):
        config={'aggregate_sha256':'c'*64}
        bound=b.build(self.ctx,self.snap,config)
        state=a.reserve(enabled(),self.ctx,self.key,10)
        b.validate(self.ctx,self.snap,config,bound,state)
        for changes in ({'source_issue':20373},{'issue_id':801},{'input_key':'b'*64},
                        {'run_id':'101'},{'configuration':{}},{'source_sha256':'a'*64}):
            with self.assertRaises(p.AdmissionDenied): b.validate(self.ctx,self.snap,config,{**bound,**changes},state)
        with self.assertRaises(p.AdmissionDenied): b.validate(self.ctx,self.snap,config,bound,enabled())

    def test_rolling_campaign_and_no_refund(self):
        state=enabled()
        for index in range(p.CAMPAIGN_LIMIT):
            ctx=replace(self.ctx,run_id=str(100+index),issue_id=800+index)
            state=a.reserve(state,ctx,self.key,10+(index//10)*p.ROLLING_SECONDS)
            if index==9:
                with self.assertRaises(p.AdmissionDenied): a.reserve(state,replace(ctx,run_id='999',issue_id=999),self.key,10)
        with self.assertRaises(p.AdmissionDenied): a.reserve(state,replace(self.ctx,run_id='999',issue_id=999),self.key,999999)
        self.assertEqual(len(state['admissions']),20)
