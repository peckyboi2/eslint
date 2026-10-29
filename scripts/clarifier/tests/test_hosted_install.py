"""Synthetic installer safeguards; no network, provider calls or public writes. Serves B06."""
import hashlib
import io
import os
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.request

from clarifier.inference import hosted_install as installer
from clarifier.shared.errors import ConfigurationError, TransportError


def profile_data() -> dict:
    return dict(linux_archive_url=installer.ARCHIVE_URL,
                linux_archive_sha256=installer.ARCHIVE_SHA256,
                linux_binary_sha256="a" * 64, cli_version=installer.CLI_VERSION)


def elf_bytes() -> bytes:
    result = bytearray(64)
    result[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", result, 16, 3, 62, 1)
    struct.pack_into("<H", result, 52, 64)
    return bytes(result)


def member(name: str = installer.ARCHIVE_MEMBER) -> tarfile.TarInfo:
    result = tarfile.TarInfo(name)
    result.size = 64
    return result


class HostedInstallTests(unittest.TestCase):
    def test_exact_release_profile_is_required(self):
        self.assertEqual(installer.validate_profile(profile_data()).binary_sha256, "a" * 64)
        for key, value in (("linux_archive_url", "https://example.org/codex"),
                           ("linux_archive_sha256", "b" * 64), ("cli_version", "latest"),
                           ("linux_binary_sha256", None), ("linux_binary_sha256", "A" * 64)):
            with self.subTest(key=key, value=value), self.assertRaises(ConfigurationError):
                installer.validate_profile({**profile_data(), key: value})

    def test_only_official_https_redirect_hosts_are_allowed(self):
        installer.validate_download_url(installer.ARCHIVE_URL)
        installer.validate_download_url("https://release-assets.githubusercontent.com/file?signature=opaque")
        for url in ("http://github.com/file", "https://example.org/file",
                    "https://github.com.evil.example/file", "https://user@github.com/file",
                    "https://github.com:443/file", "https://github.com:invalid/file",
                    "https://github.com/file#fragment", "https://github.com/\\evil",
                    "https://github.com/file\nother"):
            with self.subTest(url=url), self.assertRaises(TransportError):
                installer.validate_download_url(url)

    def test_redirect_limit_is_enforced_without_network(self):
        handler = installer.ReleaseRedirectHandler()
        request = urllib.request.Request(installer.ARCHIVE_URL)
        redirect = "https://release-assets.githubusercontent.com/file"
        for _ in range(installer.MAX_REDIRECTS):
            self.assertIsNotNone(handler.redirect_request(request, None, 302, "redirect", {}, redirect))
        with self.assertRaises(TransportError):
            handler.redirect_request(request, None, 302, "redirect", {}, redirect)

    def test_archive_size_hash_and_deadline_are_bounded(self):
        with patch.object(installer, "ARCHIVE_BYTES", 3):
            target = io.BytesIO()
            with patch.object(installer.time, "monotonic", return_value=0):
                self.assertEqual(installer.copy_download(io.BytesIO(b"abc"), target, 0),
                                 (3, hashlib.sha256(b"abc").hexdigest()))
                with self.assertRaises(TransportError):
                    installer.copy_download(io.BytesIO(b"abcd"), io.BytesIO(), 0)
            with patch.object(installer.time, "monotonic", return_value=installer.MAX_DOWNLOAD_SECONDS + 1):
                with self.assertRaises(TransportError):
                    installer.copy_download(io.BytesIO(b"abc"), io.BytesIO(), 0)
        profile = installer.validate_profile(profile_data())
        installer.verify_archive_identity(installer.ARCHIVE_BYTES, installer.ARCHIVE_SHA256, profile)
        for size, digest in ((0, installer.ARCHIVE_SHA256), (installer.ARCHIVE_BYTES, "b" * 64)):
            with self.assertRaises(TransportError):
                installer.verify_archive_identity(size, digest, profile)

    def test_download_rejects_response_before_any_execution(self):
        response = Mock(status=200)
        response.geturl.return_value = installer.ARCHIVE_URL
        response.headers = {"Content-Length": "wrong"}
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as folder, patch.object(installer.urllib.request, "build_opener", return_value=opener), patch.object(installer.subprocess, "run") as execute:
            with self.assertRaises(TransportError):
                installer.download_archive(Path(folder), installer.validate_profile(profile_data()))
            self.assertEqual(list(Path(folder).iterdir()), [])
            execute.assert_not_called()

    def test_download_uses_no_proxy_and_exact_fixed_url(self):
        response = Mock(status=200)
        response.geturl.return_value = installer.ARCHIVE_URL
        response.headers = {"Content-Length": "3"}
        response.read = io.BytesIO(b"abc").read
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        profile = installer.InstallProfile(installer.ARCHIVE_URL, hashlib.sha256(b"abc").hexdigest(), "a" * 64, installer.CLI_VERSION)
        with tempfile.TemporaryDirectory() as folder, patch.object(installer.urllib.request, "build_opener", return_value=opener) as build, patch.object(installer, "ARCHIVE_BYTES", 3):
            path = installer.download_archive(Path(folder), profile)
            self.assertEqual(path.read_bytes(), b"abc")
            self.assertEqual(build.call_args.args[0].proxies, {})
            opener.open.assert_called_once_with(installer.ARCHIVE_URL, timeout=installer.SOCKET_TIMEOUT_SECONDS)

    def test_destination_is_new_private_and_inside_runner_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = installer.create_install_directory(root / "bin", root)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o700)
            for path in (root, destination, root.parent / "outside", root / ".." / "escape"):
                with self.subTest(path=path), self.assertRaises(ConfigurationError):
                    installer.create_install_directory(path, root)
            (root / "link").symlink_to(destination, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                installer.create_install_directory(root / "link", root)

    def test_symlinked_parent_cannot_escape_runner_temp(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            (root / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ConfigurationError):
                installer.create_install_directory(root / "escape" / "bin", root)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_exactly_one_regular_bounded_member_is_required(self):
        self.assertEqual(installer.validate_archive_member([member()]).name, installer.ARCHIVE_MEMBER)
        for name in ("../codex", "/tmp/codex", "codex", "sub/" + installer.ARCHIVE_MEMBER):
            with self.subTest(name=name), self.assertRaises(TransportError):
                installer.validate_archive_member([member(name)])
        for members in ([], [member(), member()]):
            with self.assertRaises(TransportError):
                installer.validate_archive_member(members)
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE):
            candidate = member()
            candidate.type = kind
            with self.subTest(kind=kind), self.assertRaises(TransportError):
                installer.validate_archive_member([candidate])
        for size in (0, installer.MAX_BINARY_BYTES + 1):
            candidate = member()
            candidate.size = size
            with self.assertRaises(TransportError):
                installer.validate_archive_member([candidate])
        for key, value in (("sparse", []), ("pax_headers", {"path": installer.ARCHIVE_MEMBER}), ("linkname", "target")):
            candidate = member()
            setattr(candidate, key, value)
            with self.assertRaises(TransportError):
                installer.validate_archive_member([candidate])

    def test_extraction_never_uses_archive_paths_or_execute_bits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as target:
                entry = member()
                entry.mode = 0o7777
                target.addfile(entry, io.BytesIO(elf_bytes()))
            binary = installer.extract_binary(archive, root)
            self.assertEqual(binary.read_bytes(), elf_bytes())
            self.assertEqual(binary.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(TransportError):
                installer.extract_binary(archive, root)

    def test_duplicate_tar_members_are_rejected_before_binary_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as target:
                target.addfile(member(), io.BytesIO(elf_bytes()))
                target.addfile(member(), io.BytesIO(elf_bytes()))
            with self.assertRaises(TransportError):
                installer.extract_binary(archive, root)
            self.assertFalse((root / installer.BINARY_NAME).exists())

    def test_binary_copy_rejects_declared_size_mismatches(self):
        for payload, declared in ((b"abc", 2), (b"ab", 3)):
            with self.assertRaises(TransportError):
                installer.copy_binary(io.BytesIO(payload), io.BytesIO(), declared)

    def test_elf_rejects_wrong_class_endian_architecture_or_type(self):
        installer.validate_elf(elf_bytes())
        for offset, value in ((0, 0), (4, 1), (5, 2), (7, 9), (16, 1), (18, 183), (20, 0), (52, 0)):
            invalid = bytearray(elf_bytes())
            invalid[offset] = value
            with self.subTest(offset=offset), self.assertRaises(TransportError):
                installer.validate_elf(bytes(invalid))
        with self.assertRaises(TransportError):
            installer.validate_elf(b"short")

    def test_hash_and_elf_are_checked_without_execution(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(installer.subprocess, "run") as execute:
            binary = Path(folder) / "codex"
            binary.write_bytes(elf_bytes())
            installer.verify_binary(binary, hashlib.sha256(elf_bytes()).hexdigest())
            with self.assertRaises(TransportError):
                installer.verify_binary(binary, "a" * 64)
            binary.write_bytes(b"x" * 64)
            with self.assertRaises(TransportError):
                installer.verify_binary(binary, hashlib.sha256(binary.read_bytes()).hexdigest())
            execute.assert_not_called()

    def test_version_check_does_not_inherit_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / "codex"
            binary.write_bytes(elf_bytes())
            with patch.dict(os.environ, {"CLARIFIER_PROVIDER_KEY": "never-inherit"}), patch.object(installer.subprocess, "run", return_value=Mock(stdout=installer.CLI_VERSION + "\n")) as execute:
                installer.verify_version(binary, installer.CLI_VERSION)
            self.assertEqual(execute.call_args.kwargs["env"], {"PATH": "/usr/bin:/bin", "HOME": str(binary.parent)})
            self.assertEqual(execute.call_args.args[0], [str(binary), "--version"])
            self.assertEqual(binary.stat().st_mode & 0o777, 0o700)
            with patch.object(installer.subprocess, "run", return_value=Mock(stdout="wrong")):
                with self.assertRaises(TransportError):
                    installer.verify_version(binary, installer.CLI_VERSION)
            self.assertEqual(binary.stat().st_mode & 0o777, 0o600)

    def test_install_order_stops_before_execution_for_bad_identity(self):
        profile = profile_data()
        with patch.object(installer, "load_profile", return_value=profile), patch.object(installer, "verify_host"), patch.object(installer, "create_install_directory", return_value=Path("/private/install")), patch.object(installer, "download_archive", side_effect=TransportError("bad archive")), patch.object(installer, "extract_binary") as extract, patch.object(installer, "verify_version") as execute:
            with self.assertRaises(TransportError):
                installer.install(Path("/repo"), Path("/tmp/bin"), Path("/tmp"))
            extract.assert_not_called()
            execute.assert_not_called()
        with patch.object(installer, "load_profile", return_value=profile), patch.object(installer, "verify_host"), patch.object(installer, "create_install_directory", return_value=Path("/private/install")), patch.object(installer, "download_archive", return_value=Path("/archive")), patch.object(installer, "extract_binary", return_value=Path("/binary")), patch.object(installer, "verify_binary", side_effect=TransportError("bad binary")), patch.object(installer, "verify_version") as execute:
            with self.assertRaises(TransportError):
                installer.install(Path("/repo"), Path("/tmp/bin"), Path("/tmp"))
            execute.assert_not_called()

    def test_installer_refuses_wrong_host_before_download(self):
        with patch.object(installer.platform, "system", return_value="Darwin"), patch.object(installer.platform, "machine", return_value="x86_64"):
            with self.assertRaises(ConfigurationError):
                installer.verify_host()

    def test_github_path_export_is_explicit_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "github_path"
            output.touch()
            installer.publish_github_path(root / "bin", output)
            self.assertEqual(output.read_text(), str(root / "bin") + "\n")
            link = root / "link"
            link.symlink_to(output)
            for path in (link, root / "absent"):
                with self.assertRaises(ConfigurationError):
                    installer.publish_github_path(root / "bin", path)


if __name__ == "__main__":
    unittest.main()
