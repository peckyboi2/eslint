"""Independently pinned Linux engine prerequisite checks. Serves B06."""
import platform
from pathlib import Path
import re
import shutil
import subprocess

from clarifier.inference import hosted_install, recording, transport
from clarifier.outputs.validation import parse_json
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import ConfigurationError, TransportError, guarded


@guarded(ConfigurationError, 'Malformed hosted profile')
def load_profile(root: Path) -> dict:
    """Return exact approved hosted settings or raise ConfigurationError."""
    data = parse_json((root/k.HOSTED_PROFILE).read_text())
    expected = dict(version=k.VERSION, engine='codex-cli', cli_version='codex-cli 0.154.0',
                    model='gpt-6.1-sol', reasoning_effort='xhigh',
                    authentication='API key in trusted gateway only', platform='Linux', architecture='x86_64',
                    linux_archive_url=hosted_install.ARCHIVE_URL,
                    linux_archive_sha256=hosted_install.ARCHIVE_SHA256,
                    linux_binary_sha256=None)
    if set(data) != set(expected) or any(data[key] != value for key,value in expected.items() if key != 'linux_binary_sha256'):
        raise ConfigurationError('Hosted profile differs from approved envelope')
    digest = data['linux_binary_sha256']
    if digest is not None and (not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest)):
        raise ConfigurationError('Invalid Linux executable pin')
    return data


@guarded(TransportError, 'Hosted Linux runtime unavailable')
def prepare_engine(session: recording.Session) -> transport.Engine:
    """Return hash/version-verified Linux engine or raise before provider credential use."""
    profile = load_profile(session.root)
    if profile['linux_binary_sha256'] is None:
        raise TransportError('Hosted Linux executable SHA-256 unverified; activation blocked')
    if (platform.system(),platform.machine()) != (profile['platform'],profile['architecture']):
        raise TransportError('Hosted platform differs from independent Linux profile')
    found = shutil.which('codex')
    if not found or session.temporary is None:
        raise TransportError('Hosted executable/private workspace unavailable')
    binary = Path(found).resolve()
    if recording.sha(binary.read_bytes()) != profile['linux_binary_sha256']:
        raise TransportError('Hosted executable hash mismatch')
    version = subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True,timeout=30,
                             env={'PATH':'/usr/bin:/bin','HOME':str(binary.parent)}).stdout.strip()
    if version != profile['cli_version']:
        raise TransportError('Hosted CLI version mismatch')
    session.record.update(engine_version=version,engine_binary_sha256=profile['linux_binary_sha256'])
    home = Path(session.temporary.name)/c.ENGINE_HOME_DIR
    home.mkdir(mode=0o700)
    return transport.Engine(binary,home)


def record_isolation(session: recording.Session) -> None:
    """Record accurate hosted boundary facts; no host containment guarantee is implied."""
    session.record['host_isolation']={**c.HOST_ISOLATION,
        'gateway':'fixed HTTPS api.openai.com/v1/responses; no redirects; one request; tool rejection',
        'credentials':'API key only in trusted gateway; harness-only read GitHub token; no state/post token in CLI',
        'host_harness_os_jail':False,'host_network_firewall_tested':False}
