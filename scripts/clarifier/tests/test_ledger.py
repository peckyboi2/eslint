"""Task 17 strict-state infrastructure checks."""
import unittest
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


class TransitionTests(unittest.TestCase):
    def test_reservations_and_decisions_cannot_be_removed(self):
        from clarifier.tests.test_admission import enabled,ctx
        from clarifier.controls.admission import reserve
        previous=reserve(enabled(),ctx(1),'a'*64,100)
        for field in ('admissions','decisions'):
            changed=ledger.validate(previous);changed[field]=changed[field][:-1]
            with self.assertRaises(p.StateError):ledger.validate_transition(previous,changed)
