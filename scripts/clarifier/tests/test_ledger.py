"""Task 17 and D-retest strict-state infrastructure checks; no inference."""
import unittest
from unittest.mock import Mock
from clarifier.controls import ledger
from clarifier.controls import policy as p


class LedgerTests(unittest.TestCase):
    def test_initial_is_disabled_and_roundtrips(self):
        state = ledger.initial(100, 'Owner-authorised sandbox setup')
        self.assertFalse(state['enabled']); self.assertFalse(state['posting_enabled'])
        self.assertEqual(ledger.decode(ledger.encode(state)), state)

    def test_corrupt_missing_or_ambiguous_state_rejected(self):
        state = ledger.initial(100, 'Setup')
        for field in state:
            missing = dict(state); del missing[field]
            with self.assertRaises(p.StateError): ledger.validate(missing)
        for data in (b'{}', b'null', b'{"schema":1,"schema":1}', b'bad'):
            with self.assertRaises(p.StateError): ledger.decode(data)
        for key, value in [('enabled', 1), ('campaign','reset'), ('posts',[{}]), ('admissions',[{}]), ('decisions',[])]:
            with self.assertRaises(p.StateError): ledger.validate({**state, key:value})

    def test_previous_local_cap_remains_readable_without_granting_the_new_cap(self):
        from clarifier.controls import admission
        from clarifier.controls.identity import Context
        from clarifier.tests.test_admission import enabled,ctx
        for old_cap,old_reason in p.LOCAL_CAMPAIGN_APPROVALS[:-1]:
            state=enabled()
            state['decisions'].append(dict(actor_id=p.OWNER_ID,at=3,reason=old_reason+'a'*64,action='extend-local-preview'))
            state['admissions']=[dict(run_id=str(n),event_key=admission.event_key(ctx(n),'a'*64),
                                      input_key='a'*64,at=100,campaign=ledger.CAMPAIGN) for n in range(1,old_cap+1)]
            decoded=ledger.decode(ledger.encode(state))
            self.assertEqual(ledger.local_campaign_limit(decoded),old_cap)
            local=Context(str(old_cap+1),1,'0'*40,p.LOCAL_WORKFLOW)
            model,write=Mock(),Mock()
            with self.assertRaises(p.AdmissionDenied):
                admission.reserve(decoded,local,'a'*64,101,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT);model();write()
            decoded['decisions'].append(dict(actor_id=p.OWNER_ID,at=101,reason=p.LOCAL_EXTENSION_REASON+'b'*64,action='extend-local-preview'))
            updated=admission.reserve(decoded,local,'a'*64,101,rolling_limit=p.LOCAL_DEVELOPMENT_LIMIT,campaign_limit=p.LOCAL_CAMPAIGN_LIMIT)
            self.assertEqual(updated['admissions'][:-1],state['admissions'])
            self.assertFalse(updated['posting_enabled'])
            with self.assertRaises(p.AdmissionDenied):
                admission.reserve(updated,ctx(old_cap+2),'a'*64,102);model();write()
            model.assert_not_called();write.assert_not_called()


class TransitionTests(unittest.TestCase):
    def test_reservations_and_decisions_cannot_be_removed(self):
        from clarifier.tests.test_admission import enabled,ctx
        from clarifier.controls.admission import reserve
        previous=reserve(enabled(),ctx(1),'a'*64,100)
        for field in ('admissions','decisions'):
            changed=ledger.validate(previous);changed[field]=changed[field][:-1]
            with self.assertRaises(p.StateError):ledger.validate_transition(previous,changed)
