"""Approved text staging and private workspace lifecycle. Serves tasks 09, 29 and R1."""
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import TYPE_CHECKING, TypedDict

from clarifier.shared import constants as c
from clarifier.shared.errors import StagingError, guarded
from clarifier.inference.recording import Session, save_json, sha

if TYPE_CHECKING:
    from clarifier.inference.packages import Package


class FileDigest(TypedDict):
    """Size and digest of one approved staged file."""
    bytes: int
    sha256: str


class StagedManifest(TypedDict):
    """A closed file inventory with no evaluator inputs."""
    source_hashes: dict[str, str]
    staged_files: dict[str, FileDigest]
    staged_bytes: int
    excluded: list[str]


@dataclass(frozen=True)
class StagedCase:
    """Private workspace and its verified historical evidence."""
    workspace: Path
    evidence: Path
    manifest: StagedManifest


def reject_unsafe_path(name: str) -> None:
    """Raise StagingError for a noncanonical or escaping evidence path."""
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or ".." in path.parts
            or "\\" in name or path.as_posix() != name):
        raise StagingError("Unsafe source path")


def reject_symlinks(path: Path) -> None:
    """Raise StagingError if the file or any parent is a symbolic link."""
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise StagingError("Symbolic links are not allowed")


@guarded(StagingError, "Cannot read safe UTF-8 source file")
def read_safe(root: Path, name: str, limit: int) -> bytes:
    """Return bounded regular-file bytes or raise StagingError."""
    reject_unsafe_path(name)
    path = root / name
    reject_symlinks(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise StagingError("Unsafe file type, hardlink or input size")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise StagingError("Input size limit exceeded")
        data.decode("utf-8")
        return data
    finally:
        os.close(fd)


def verify_source_hashes(files: dict[str, bytes], expected: dict[str, str]) -> None:
    """Raise StagingError if any approved source is missing or has changed."""
    if set(files) != set(expected):
        raise StagingError("Unexpected or missing case files")
    for name, digest in expected.items():
        if sha(files[name]) != digest:
            raise StagingError(f"Historical hash mismatch: {name}")


def build_manifest(files: dict[str, bytes], expected: dict[str, str]) -> StagedManifest:
    """Return the deterministic approved-file manifest."""
    entries = {name: FileDigest(bytes=len(data), sha256=sha(data)) for name, data in files.items()}
    return StagedManifest(source_hashes=dict(expected), staged_files=entries,
                          staged_bytes=sum(item["bytes"] for item in entries.values()), excluded=list(c.EXCLUDED))


@guarded(StagingError, "Cannot stage approved case")
def verify_inventory(source: Path, expected: dict[str, str]) -> None:
    """Reject unexpected paths, symlinks or directories with StagingError."""
    reject_symlinks(source)
    directories = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents
                   if parent != PurePosixPath(".")}
    found = {path.relative_to(source).as_posix() for path in source.rglob("*")}
    if found != set(expected) | directories:
        raise StagingError("Unexpected or missing case files")
    for name in found:
        reject_unsafe_path(name)
        reject_symlinks(source / name)
        if name in directories and not (source / name).is_dir():
            raise StagingError("Expected support directory")


@guarded(StagingError, "Cannot stage approved case")
def stage(source: Path, destination: Path, limit: int = c.MAX_INPUT_BYTES,
          *, expected: dict[str, str] = c.APPROVED) -> StagedManifest:
    """Copy only the exact approved case or raise StagingError without truncation."""
    verify_inventory(source, expected)
    files = {name: read_safe(source, name, limit) for name in expected}
    if sum(map(len, files.values())) > limit:
        raise StagingError("Case package exceeds input limit")
    verify_source_hashes(files, expected)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    return build_manifest(files, expected)


@guarded(StagingError, "Cannot prepare private workspace")
def prepare(session: Session, package: "Package | None" = None) -> StagedCase:
    """Create the private workspace and audited input copy or raise StagingError."""
    session.temporary = tempfile.TemporaryDirectory(prefix="cs467-preview-", dir=c.PRIVATE_TEMP_ROOT)
    workspace = Path(session.temporary.name) / c.WORKSPACE_DIR
    workspace.mkdir()
    session.record.update(model_workspace=str(workspace), host_isolation=dict(c.HOST_ISOLATION))
    evidence = workspace / c.EVIDENCE_DIR
    source = package.source if package else session.root / c.CASE_PATH
    expected = package.hashes if package else c.APPROVED
    manifest = stage(source, evidence, session.config["input_limit_bytes"], expected=expected)
    if package:
        if manifest["staged_bytes"] != package.total_bytes:
            raise StagingError("Historical package size mismatch")
        session.record['source_issue']=package.issue
        boundary='snapshot_boundary' if package.cutoff.get('kind')=='issues:opened' else 'historical_cutoff'
        session.record[boundary]=package.cutoff
    session.record["input_hashes"] = manifest["source_hashes"]
    save_json(session.folder / c.MANIFEST_FILE, manifest)
    shutil.copytree(evidence, session.folder / c.INPUT_DIR)
    return StagedCase(workspace, evidence, manifest)


def cleanup(session: Session) -> None:
    """Remove private workspace resources and record a safe cleanup failure."""
    try:
        if session.temporary:
            session.temporary.cleanup()
    except OSError:
        session.record["status"] = "failed"
        session.record["errors"].append("Private workspace cleanup failed")
