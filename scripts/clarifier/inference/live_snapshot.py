"""Pure closed snapshots for issue intake; report text stays data. Serves B02–B03."""
from dataclasses import dataclass
from datetime import datetime
import json
import re

from clarifier.controls import identity, policy as p
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import StagingError, guarded
from clarifier.inference.recording import sha


@dataclass(frozen=True)
class LiveSnapshot:
    """Bounded exact UTF-8 staged files and their source identity."""
    issue_id: int
    number: int
    files: dict[str, bytes]
    hashes: dict[str, str]
    source_sha256: str


def canonical(value: dict) -> bytes:
    """Return canonical UTF-8 JSON bytes; raises TypeError for non-JSON input."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n').encode()


@guarded(StagingError, 'Malformed or ineligible issue snapshot')
def project(issue: dict) -> dict:
    """Return eligible report projection or raise StagingError without truncation."""
    if 'pull_request' in issue or issue['state'] != 'open' or issue['locked'] is not False:
        raise StagingError('Closed, locked or PR report rejected')
    if type(issue['id']) is not int or type(issue['number']) is not int or min(issue['id'],issue['number']) <= 0:
        raise StagingError('Invalid report identity')
    if not isinstance(issue['title'],str) or not issue['title'].startswith(k.BUG_PREFIX):
        raise StagingError('Report title is not eligible')
    if issue['body'] is not None and not isinstance(issue['body'],str):
        raise StagingError('Invalid report body')
    author = issue['user']
    if author['type'] != 'User' or type(author['id']) is not int or author['id'] <= 0:
        raise StagingError('Only User-authored reports are eligible')
    for field in ('created_at','updated_at'):
        if not isinstance(issue[field],str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',issue[field]):
            raise StagingError('Invalid issue version timestamp')
        datetime.strptime(issue[field],'%Y-%m-%dT%H:%M:%SZ')
    if issue['updated_at'] < issue['created_at']:
        raise StagingError('Issue version precedes creation')
    return {**{name:issue[name] for name in k.SNAPSHOT_KEYS},
            'author':{'id':author['id'],'type':author['type']},'repository_id':p.REPOSITORY_ID}


@guarded(StagingError, 'Issue event/API snapshot disagreement')
def capture(ctx: identity.Context, opening: dict, current: dict) -> LiveSnapshot:
    """Return an unchanged bounded opening snapshot or raise StagingError."""
    event, live = project(opening), project(current)
    if event != live or live['id'] != ctx.issue_id or live['number'] != ctx.issue_number:
        raise StagingError('Issue changed or target disagrees with opening event')
    expected_url = f'https://github.com/{p.REPOSITORY}/issues/{ctx.issue_number}'
    if opening.get('html_url') != expected_url or current.get('html_url') != expected_url:
        raise StagingError('Issue transferred or URL identity mismatch')
    source_hash = sha(canonical(live))
    metadata = {key:value for key,value in live.items() if key not in ('title','body')}
    metadata.update(source_sha256=source_hash, support='Linked material not fetched; title/body only')
    files = {'title.txt':live['title'].encode(), 'body.md':(live['body'] or '').encode(),
             'snapshot.json':canonical(metadata)}
    if sum(map(len,files.values())) > c.MAX_INPUT_BYTES:
        raise StagingError('Issue package exceeds input limit')
    return LiveSnapshot(live['id'],live['number'],files,
                        {name:sha(data) for name,data in files.items()},source_hash)
