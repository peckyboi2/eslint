"""Trusted promotion record for tasks 20, 25–27; disabled until reviewed evidence exists."""
from dataclasses import dataclass

from clarifier.controls import ledger
from clarifier.controls import policy as p


@dataclass(frozen=True)
class Release:
    """Deterministic review binds one output and configuration, never model fields."""
    configuration: str
    output_sha256: str
    preview_run: str
    attack_runs: tuple[str, str, str]


def live_release() -> Release:
    """Raise PostingBlocked: no hosted runtime/target or approved live release exists."""
    raise p.PostingBlocked('Live release absent: CI engine/login, sandbox target and reviewed promotion evidence are unprovisioned')


def verify(release: Release, configuration: str, output_sha256: str) -> None:
    """Reject missing/mismatched promotion evidence before any posting intent."""
    if (not isinstance(release, Release) or not ledger.digest(configuration)
            or release.configuration != configuration or release.output_sha256 != output_sha256
            or not release.preview_run or len(set(release.attack_runs)) != 3
            or not all(release.attack_runs)):
        raise p.PostingBlocked('Reviewed output/configuration/attack gate mismatch')
