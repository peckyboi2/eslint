"""Typed, safe failure boundaries for trusted helpers. Serves tasks 09–15 and R1."""
from functools import wraps
from typing import Callable, ParamSpec, TypeVar


class ClarifierError(ValueError):
    """A bounded preview failure with a credential-free diagnostic."""


class ValidationError(ClarifierError):
    """The model result is invalid and must remain silent."""


class StagingError(ClarifierError):
    """Approved evidence cannot be staged safely."""


class SkillError(ClarifierError):
    """Canonical skill bytes or native loading cannot be verified."""


class RequestError(ClarifierError):
    """The model request differs from the approved envelope."""


class TransportError(ClarifierError):
    """The engine or guarded provider exchange failed."""


class RecordingError(ClarifierError):
    """An immutable evidence record cannot be written."""


class ConfigurationError(ClarifierError):
    """The configuration is missing, malformed or outside this preview."""


class InterruptedRun(ClarifierError):
    """The preview was interrupted before completion."""


P = ParamSpec("P")
T = TypeVar("T")


def guarded(error_type: type[ClarifierError], message: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Return a decorator translating unexpected failures to safe typed errors."""
    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def call(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return function(*args, **kwargs)
            except ClarifierError:
                raise
            except KeyboardInterrupt:
                raise InterruptedRun("Preview interrupted") from None
            except Exception:
                # Exception text can contain credentials or untrusted response fragments.
                raise error_type(message) from None
        return call
    return decorate
