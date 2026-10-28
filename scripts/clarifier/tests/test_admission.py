"""Task 18 quota infrastructure checks, never accuracy/dollar-cap evidence."""
import unittest
from unittest.mock import Mock
from clarifier.controls import admission
from clarifier.controls import identity
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.tests.test_identity import context_data


def enabled():
    state=ledger.initial(1,'Owner setup for mock'); state['enabled']=True
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=2,reason='Mock preview authorisation',action='enable-preview'))
    return state


def ctx(number): return identity.verify({**context_data(), 'run_id':str(number)})


class AdmissionTests(unittest.TestCase):
    def denied_without_effect(self, state, context, at):
        model,write=Mock(),Mock()
        with self.assertRaises((p.AdmissionDenied,p.StateError)):
            admission.reserve(state,context,'a'*64,at);model();write()
        model.assert_not_called();write.assert_not_called()

    def test_rolling_boundary_and_failed_run_consumption(self):
        state=enabled()
        for n in range(1,11): state=admission.reserve(state,ctx(n),'a'*64,100)
        self.denied_without_effect(state,ctx(11),100)
        self.denied_without_effect(state,ctx(11),100+p.ROLLING_SECONDS-1)
        state=admission.reserve(state,ctx(11),'a'*64,100+p.ROLLING_SECONDS)
        self.assertEqual(len(state['admissions']),11)

    def test_campaign_is_lifetime_and_cannot_reset(self):
        state=enabled()
        for n in range(1,21): state=admission.reserve(state,ctx(n),'a'*64,n*p.ROLLING_SECONDS)
        self.denied_without_effect(state,ctx(21),21*p.ROLLING_SECONDS)
        self.denied_without_effect({**state,'campaign':'reset'},ctx(21),21*p.ROLLING_SECONDS)

    def test_disabled_corrupt_clock_and_rerun(self):
        self.denied_without_effect(ledger.initial(1,'Setup'),ctx(1),100)
        self.denied_without_effect({},ctx(1),100)
        state=admission.reserve(enabled(),ctx(1),'a'*64,100)
        self.denied_without_effect(state,ctx(2),99)
        self.denied_without_effect(state,identity.verify({**context_data(),'run_id':'1','run_attempt':'2'}),101)
        self.assertEqual(len(state['admissions']),1)

    def test_input_and_event_keys_are_distinct(self):
        key=admission.input_key({'body':'a'*64})
        self.assertEqual(admission.event_key(ctx(1),key),admission.event_key(ctx(1),key))
        self.assertNotEqual(admission.event_key(ctx(1),key),admission.event_key(ctx(2),key))


class LocalExceptionTests(unittest.TestCase):
    def test_limit_increase_is_rejected_for_hosted_context(self):
        state=enabled();state['decisions'].append(dict(actor_id=p.OWNER_ID,at=3,reason='Mock local-only approval',action='extend-local-preview'))
        with self.assertRaises(p.AdmissionDenied):admission.reserve(state,ctx(1),'a'*64,100,rolling_limit=11)
        from clarifier.controls.identity import Context
        local=Context('1',1,'0'*40,p.LOCAL_WORKFLOW)
        with self.assertRaises(p.AdmissionDenied):admission.reserve(enabled(),local,'a'*64,100,rolling_limit=11)
        self.assertEqual(len(admission.reserve(state,local,'a'*64,100,rolling_limit=11)['admissions']),1)

    def test_development_extension_needs_matching_decision_and_stays_local(self):
        from clarifier.controls.identity import Context
        local=Context('1',1,'0'*40,p.LOCAL_WORKFLOW)
        state=enabled()
        state['decisions'].append(dict(actor_id=p.OWNER_ID,at=3,reason='Original one-call extension',action='extend-local-preview'))
        model,write=Mock(),Mock()
        for reason in ('Original one-call extension',p.LOCAL_EXTENSION_REASON+'bad-digest'):
            state['decisions'][-1]['reason']=reason
            with self.assertRaises(p.AdmissionDenied):
                admission.reserve(state,local,'a'*64,100,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT);model();write()
        state['decisions'][-1]['reason']=p.LOCAL_EXTENSION_REASON+'a'*64
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(state,ctx(1),'a'*64,100,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT);model();write()
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(state,ctx(1),'a'*64,100,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT);model();write()
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(enabled(),local,'a'*64,100,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT);model();write()
        updated=admission.reserve(state,local,'a'*64,100,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT)
        self.assertEqual(len(updated['admissions']),1)
        self.assertFalse(updated['posting_enabled'])
        model.assert_not_called();write.assert_not_called()

    def test_local_extension_keeps_rolling_campaign_and_no_refund_limits(self):
        from clarifier.controls.identity import Context
        state=enabled()
        state['decisions'].append(dict(actor_id=p.OWNER_ID,at=3,reason=p.LOCAL_EXTENSION_REASON+'a'*64,action='extend-local-preview'))
        for n in range(1,p.LOCAL_DEVELOPMENT_LIMIT+1):
            state=admission.reserve(state,Context(str(n),1,'0'*40,p.LOCAL_WORKFLOW),'a'*64,100,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT)
        model,write=Mock(),Mock()
        for at in (100,100+p.ROLLING_SECONDS):
            with self.assertRaises(p.AdmissionDenied):
                admission.reserve(state,Context('22',1,'0'*40,p.LOCAL_WORKFLOW),'a'*64,at,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT);model();write()
        self.assertEqual(len(state['admissions']),p.LOCAL_CAMPAIGN_LIMIT)
        model.assert_not_called();write.assert_not_called()
