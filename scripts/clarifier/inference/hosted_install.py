#!/usr/bin/env python3
"""Install the pinned hosted CLI without provider credentials. Serves hosted activation B06."""
import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import tarfile
import time
from typing import BinaryIO
import urllib.parse
import urllib.request

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from clarifier.shared.errors import ClarifierError, ConfigurationError, TransportError, guarded

ARCHIVE_URL = "https://github.com/openai/codex/releases/download/rust-v0.154.0/codex-x86_64-unknown-linux-musl.tar.gz"
ARCHIVE_SHA256 = "d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02"
ARCHIVE_BYTES = 98981886
ARCHIVE_MEMBER = "codex-x86_64-unknown-linux-musl"
CLI_VERSION = "codex-cli 0.154.0"
DOWNLOAD_HOSTS = frozenset(("github.com", "release-assets.githubusercontent.com"))
MAX_REDIRECTS = 3
MAX_DOWNLOAD_SECONDS = 120
SOCKET_TIMEOUT_SECONDS = 20
VERSION_TIMEOUT_SECONDS = 30
CHUNK_BYTES = 1024 * 1024
MAX_BINARY_BYTES = 384 * 1024 * 1024
ARCHIVE_NAME = "codex.tar.gz"
BINARY_NAME = "codex"


@dataclass(frozen=True)
class InstallProfile:
    """Validated immutable archive and executable identities."""
    archive_url: str
    archive_sha256: str
    binary_sha256: str
    cli_version: str


def load_profile(root: Path) -> dict:
    """Return the strict shared hosted profile or raise ConfigurationError."""
    from clarifier.inference.hosted_runtime import load_profile as read_profile
    return read_profile(root)


def validate_profile(data: dict) -> InstallProfile:
    """Return installation pins or raise ConfigurationError for unapproved identities."""
    if (data.get("linux_archive_url") != ARCHIVE_URL
            or data.get("linux_archive_sha256") != ARCHIVE_SHA256
            or data.get("cli_version") != CLI_VERSION):
        raise ConfigurationError("Hosted archive differs from the approved release")
    digest = data.get("linux_binary_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ConfigurationError("Hosted executable pin is unavailable or malformed")
    return InstallProfile(ARCHIVE_URL, ARCHIVE_SHA256, digest, CLI_VERSION)


@guarded(TransportError, "Malformed hosted archive redirect")
def validate_download_url(url: str) -> None:
    """Raise TransportError unless a download URL uses an approved HTTPS host."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port is not None or parsed.fragment
            or any(character in url for character in ("\r", "\n", "\\"))):
        raise TransportError("Hosted archive redirect rejected")


class ReleaseRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow only a bounded number of official release redirects."""

    def __init__(self) -> None:
        self.redirects = 0

    def redirect_request(self, request, response, code, message, headers, newurl):
        """Return a validated redirect request or raise TransportError."""
        validate_download_url(newurl)
        self.redirects += 1
        if self.redirects > MAX_REDIRECTS:
            raise TransportError("Hosted archive redirect limit exceeded")
        return super().redirect_request(request, response, code, message, headers, newurl)


def verify_host() -> None:
    """Raise ConfigurationError unless this is the approved Linux x86_64 host."""
    if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise ConfigurationError("Hosted installer requires Linux x86_64")


@guarded(ConfigurationError, "Hosted installation directory unavailable")
def create_install_directory(destination: Path, runner_temp: Path) -> Path:
    """Return a new private runner directory or raise ConfigurationError."""
    if any(character in str(destination) for character in ("\r", "\n")) or ".." in destination.parts:
        raise ConfigurationError("Unsafe hosted installation destination")
    root = runner_temp.resolve(strict=True)
    canonical = destination.parent.resolve(strict=True) / destination.name
    if not canonical.is_relative_to(root) or canonical == root:
        raise ConfigurationError("Hosted destination must be inside RUNNER_TEMP")
    if canonical.exists() or canonical.is_symlink():
        raise ConfigurationError("Hosted destination already exists")
    canonical.mkdir(mode=0o700)
    canonical.chmod(0o700)
    return canonical


def copy_download(response: BinaryIO, target: BinaryIO, started: float) -> tuple[int, str]:
    """Return bounded download size/hash or raise TransportError on overflow or timeout."""
    digest, total = hashlib.sha256(), 0
    while True:
        if time.monotonic() - started > MAX_DOWNLOAD_SECONDS:
            raise TransportError("Hosted archive download timed out")
        chunk = response.read(min(CHUNK_BYTES, ARCHIVE_BYTES - total + 1))
        if time.monotonic() - started > MAX_DOWNLOAD_SECONDS:
            raise TransportError("Hosted archive download timed out")
        if not chunk:
            return total, digest.hexdigest()
        total += len(chunk)
        if total > ARCHIVE_BYTES:
            raise TransportError("Hosted archive exceeds the pinned size")
        digest.update(chunk)
        target.write(chunk)


def verify_archive_identity(size: int, digest: str, profile: InstallProfile) -> None:
    """Raise TransportError unless the complete archive matches its pinned identity."""
    if size != ARCHIVE_BYTES or digest != profile.archive_sha256:
        raise TransportError("Hosted archive size or SHA-256 mismatch")


@guarded(TransportError, "Hosted archive download failed")
def download_archive(directory: Path, profile: InstallProfile) -> Path:
    """Return a verified archive path or raise TransportError without executing it."""
    if profile.archive_url != ARCHIVE_URL:
        raise TransportError("Unapproved hosted archive URL")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), ReleaseRedirectHandler())
    started = time.monotonic()
    path = directory / ARCHIVE_NAME
    with opener.open(profile.archive_url, timeout=SOCKET_TIMEOUT_SECONDS) as response:
        validate_download_url(response.geturl())
        if response.status != 200:
            raise TransportError("Hosted archive did not return HTTP 200")
        content_length = response.headers.get("Content-Length")
        if content_length is not None and content_length != str(ARCHIVE_BYTES):
            raise TransportError("Hosted archive Content-Length mismatch")
        with path.open("xb") as target:
            size, digest = copy_download(response, target, started)
    verify_archive_identity(size, digest, profile)
    return path


def validate_archive_member(members: list[tarfile.TarInfo]) -> tarfile.TarInfo:
    """Return the sole approved regular member or raise TransportError."""
    if len(members) != 1:
        raise TransportError("Hosted archive must contain exactly one member")
    member = members[0]
    if (member.name != ARCHIVE_MEMBER or not member.isreg()
            or member.linkname or member.size < 64 or member.size > MAX_BINARY_BYTES
            or member.sparse is not None or member.pax_headers):
        raise TransportError("Unsafe hosted archive member")
    return member


def copy_binary(source: BinaryIO, target: BinaryIO, expected_size: int) -> None:
    """Copy the declared binary bytes or raise TransportError on a size mismatch."""
    total = 0
    while chunk := source.read(min(CHUNK_BYTES, expected_size - total + 1)):
        total += len(chunk)
        if total > expected_size:
            raise TransportError("Hosted executable exceeds its declared size")
        target.write(chunk)
    if total != expected_size:
        raise TransportError("Hosted executable is truncated")


@guarded(TransportError, "Hosted archive extraction failed")
def extract_binary(archive_path: Path, directory: Path) -> Path:
    """Return a non-executable binary path after exact-member extraction or raise TransportError."""
    with tarfile.open(archive_path, "r:gz") as archive:
        members = []
        for member in archive:
            members.append(member)
            if len(members) > 1:
                raise TransportError("Hosted archive contains extra or duplicate members")
        member = validate_archive_member(members)
        source = archive.extractfile(member)
        if source is None:
            raise TransportError("Hosted archive member has no regular payload")
        binary = directory / BINARY_NAME
        descriptor = os.open(binary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with source, os.fdopen(descriptor, "wb") as target:
            copy_binary(source, target, member.size)
    return binary


def validate_elf(header: bytes) -> None:
    """Raise TransportError unless the header identifies a Linux x86_64 ELF executable."""
    if (len(header) < 64 or header[:7] != b"\x7fELF\x02\x01\x01"
            or header[7] not in (0, 3) or struct.unpack_from("<H", header, 16)[0] not in (2, 3)
            or struct.unpack_from("<H", header, 18)[0] != 62
            or struct.unpack_from("<I", header, 20)[0] != 1
            or struct.unpack_from("<H", header, 52)[0] != 64):
        raise TransportError("Hosted executable is not the approved ELF architecture")


@guarded(TransportError, "Hosted executable identity check failed")
def verify_binary(binary: Path, expected_digest: str) -> None:
    """Raise TransportError unless executable bytes match the configured hash and ELF identity."""
    digest = hashlib.sha256()
    with binary.open("rb") as source:
        validate_elf(source.read(64))
        source.seek(0)
        while chunk := source.read(CHUNK_BYTES):
            digest.update(chunk)
    if digest.hexdigest() != expected_digest:
        raise TransportError("Hosted executable SHA-256 mismatch")


@guarded(TransportError, "Hosted executable version check failed")
def verify_version(binary: Path, expected_version: str) -> None:
    """Raise TransportError unless the verified executable reports the pinned version."""
    binary.chmod(0o700)
    result = subprocess.run([str(binary), "--version"], capture_output=True, text=True,
                            check=True, timeout=VERSION_TIMEOUT_SECONDS,
                            env={"PATH": "/usr/bin:/bin", "HOME": str(binary.parent)})
    if result.stdout.strip() != expected_version:
        binary.chmod(0o600)
        raise TransportError("Hosted executable CLI version mismatch")


@guarded(ConfigurationError, "GitHub executable path export failed")
def publish_github_path(directory: Path, github_path: Path) -> None:
    """Append the verified directory to an existing GitHub path file or raise ConfigurationError."""
    if not github_path.is_file() or github_path.is_symlink():
        raise ConfigurationError("GITHUB_PATH must name an existing regular environment file")
    with github_path.open("a", encoding="utf-8") as target:
        target.write(str(directory) + "\n")


@guarded(ConfigurationError, "Hosted installation failed")
def install(root: Path, destination: Path, runner_temp: Path) -> Path:
    """Return a verified installed CLI or raise a typed error before provider use."""
    profile = validate_profile(load_profile(root))
    verify_host()
    directory = create_install_directory(destination, runner_temp)
    archive = download_archive(directory, profile)
    binary = extract_binary(archive, directory)
    verify_binary(binary, profile.binary_sha256)
    verify_version(binary, profile.cli_version)
    archive.unlink()
    return binary


def main() -> int:
    """Run installation and return a credential-free CLI status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--github-path", action="store_true")
    arguments = parser.parse_args()
    try:
        runner_temp = Path(os.environ["RUNNER_TEMP"])
        binary = install(Path(__file__).resolve().parents[3], arguments.destination, runner_temp)
        if arguments.github_path:
            publish_github_path(binary.parent, Path(os.environ["GITHUB_PATH"]))
        print("Installed verified " + CLI_VERSION)
        return 0
    except (ClarifierError, KeyError):
        print("Hosted installation rejected; no provider request made", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
