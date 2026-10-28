"""Select pinned historical evidence without evaluator answers. Serves task 29."""
from dataclasses import dataclass
import json
from pathlib import Path

from clarifier.shared import constants as c
from clarifier.shared.errors import StagingError, guarded
from clarifier.inference.recording import sha
from clarifier.inference.staging import read_safe, reject_unsafe_path


@dataclass(frozen=True)
class Package:
    """Trusted input binding; no expected decision or review rationale."""
    issue: int
    source: Path
    hashes: dict[str, str]
    total_bytes: int
    cutoff: dict


def read_pinned(root: Path, name: str, expected: str) -> dict:
    """Return verified UTF-8 manifest data or raise StagingError."""
    raw = read_safe(root, name, c.MAX_INPUT_BYTES)
    if sha(raw) != expected:
        raise StagingError("Prepared manifest hash mismatch")
    return json.loads(raw)


def select_row(manifest: dict, issue: int) -> dict:
    """Return one approved package row or raise StagingError."""
    if type(issue) is not int or issue not in c.HISTORICAL_CASE_IDS:
        raise StagingError("Unsupported historical case")
    rows = manifest["cases"]
    if {row["issue"] for row in rows} != set(c.HISTORICAL_CASE_IDS):
        raise StagingError("Historical package catalog differs from approved cases")
    matches = [row for row in rows if row["issue"] == issue]
    if len(matches) != 1:
        raise StagingError("Ambiguous historical package")
    return matches[0]


def select_hashes(entries: dict[str, str], folder: str) -> dict[str, str]:
    """Return only canonical selected-case hashes or raise StagingError."""
    reject_unsafe_path(folder)
    prefix = folder + "/"
    hashes = {name[len(prefix):]: digest for name, digest in entries.items() if name.startswith(prefix)}
    for name in hashes:
        reject_unsafe_path(name)
    if not set(c.EVIDENCE_ORDER) <= set(hashes):
        raise StagingError("Missing historical title, body or snapshot")
    return hashes


def verify_snapshot(row: dict, snapshot: dict, hashes: dict[str, str]) -> None:
    """Raise StagingError if source inventory, cutoff or body binding differs."""
    expected = {item["path"]: item["sha256"] for item in snapshot["files"]}
    declared = {name: value for name, value in hashes.items() if name != "snapshot.json"}
    point = snapshot["decision_point"]
    if (snapshot["issue"] != row["issue"] or expected != declared
            or snapshot["archived_body_sha256"] != row["body_sha256"]
            or hashes["body.md"] != row["body_sha256"]
            or point["kind"] != row["cutoff_kind"] or point["cutoff_utc"] != row["cutoff_utc"]):
        raise StagingError("Historical snapshot inventory or cutoff mismatch")


@guarded(StagingError, "Cannot select verified historical package")
def load(issue: int, root: Path = c.ROOT) -> Package:
    """Return a pinned case binding or raise StagingError before admission."""
    prepared = root / c.PREPARED_PATH
    catalog = read_pinned(prepared, c.PACKAGE_MANIFEST, c.PACKAGE_MANIFEST_SHA256)
    entries = read_pinned(prepared, c.PACKAGE_HASHES, c.PACKAGE_HASHES_SHA256)
    row = select_row(catalog, issue)
    hashes = select_hashes(entries, row["folder"])
    snapshot = read_pinned(prepared / row["folder"], "snapshot.json", hashes["snapshot.json"])
    verify_snapshot(row, snapshot, hashes)
    return Package(issue, prepared / row["folder"], hashes,
                   row["total_bytes_including_metadata"], snapshot["decision_point"])
