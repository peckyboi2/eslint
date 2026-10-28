"""Typed error and interruption boundaries for tasks 09–15 and R1."""
import unittest
from clarifier.shared.errors import ClarifierError, InterruptedRun, StagingError, guarded


class TypedBoundaries(unittest.TestCase):
    def test_unexpected_exception_text_cannot_leak_credentials(self):
        @guarded(StagingError, 'Safe staging failure')
        def failing():
            raise OSError('Bearer private-value')
        with self.assertRaisesRegex(StagingError, '^Safe staging failure$'):
            failing()

    def test_typed_errors_keep_their_identity(self):
        error = StagingError('Approved diagnostic')
        @guarded(StagingError, 'fallback')
        def failing():
            raise error
        with self.assertRaises(ClarifierError) as caught:
            failing()
        self.assertIs(caught.exception, error)

    def test_interruption_becomes_one_typed_failure(self):
        @guarded(StagingError, 'fallback')
        def interrupted():
            raise KeyboardInterrupt()
        with self.assertRaises(InterruptedRun):
            interrupted()
