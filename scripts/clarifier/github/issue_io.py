"""Fixed issue collector and bounded event file edge. Serves B02."""
import os
from pathlib import Path

from clarifier.controls import policy as p
from clarifier.inference import live_snapshot, staging
from clarifier.outputs.validation import parse_json
from clarifier.shared import intake_constants as k
from clarifier.shared.errors import StagingError, guarded


@guarded(StagingError, 'Issue event file unavailable or malformed')
def read_event() -> dict:
    """Return bounded runner event JSON or raise StagingError; never evaluate text."""
    path = Path(os.environ['GITHUB_EVENT_PATH'])
    raw = staging.read_safe(path.parent,path.name,k.EVENT_BYTES)
    return parse_json(raw.decode())


def collect(api, ctx, opening: dict) -> live_snapshot.LiveSnapshot:
    """Return fresh fixed-endpoint snapshot or raise typed platform/staging errors."""
    api.verify_context(ctx)
    current = api._request('GET',f'/repos/{p.REPOSITORY}/issues/{ctx.issue_number}')
    return live_snapshot.capture(ctx,opening,current)


def write_source(snapshot: live_snapshot.LiveSnapshot, folder: Path) -> None:
    """Write exact files exclusively or raise OSError before staging/inference."""
    folder.mkdir(parents=True,exist_ok=False)
    for name, data in snapshot.files.items():
        with (folder/name).open('xb') as stream:
            stream.write(data)
