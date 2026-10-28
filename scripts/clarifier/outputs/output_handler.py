"""Pure comment-only output planning for task 20; no generic mutation interface."""
from dataclasses import dataclass
import hashlib
import re

from clarifier.shared import constants as c
from clarifier.controls import ledger
from clarifier.controls import policy as p
from clarifier.outputs import release_gate
from clarifier.controls.identity import Context
from clarifier.outputs.validation import parse_and_validate


@dataclass(frozen=True)
class CommentPlan:
    """One trusted target, bounded comment and configuration identity."""
    report: int
    text: str
    input_key: str
    event_key: str
    configuration: str
    marker: str


def check_enabled(state: dict) -> None:
    """Raise PostingBlocked unless validated admission and posting are enabled."""
    state = ledger.validate(state)
    if not state['enabled'] or not state['posting_enabled']:
        raise p.PostingBlocked('Posting or admission disabled')


def check_mode(mode: str, ctx: Context) -> None:
    """Raise PostingBlocked unless explicit initial-run posting was selected."""
    if mode != 'post' or ctx.attempt != 1:
        raise p.PostingBlocked('Preview, replay or rerun cannot post')


def check_target(issue: dict, target: p.Target) -> None:
    """Reject unbound targets, PRs, non-bugs or changed historical source bytes."""
    if type(target.issue) is not int or target.issue < 1 or target.source_issue != c.SOURCE_ISSUE:
        raise p.PostingBlocked('No approved sandbox copy of source #20373')
    expected = f'https://api.github.com/repos/{p.REPOSITORY}'
    if (issue.get('number') != target.issue or issue.get('repository_url') != expected
            or issue.get('url') != f'{expected}/issues/{target.issue}' or 'pull_request' in issue
            or issue.get('state') != 'open' or issue.get('locked') is not False):
        raise p.PostingBlocked('Wrong/unsupported sandbox issue')
    labels = issue.get('labels', [])
    if not isinstance(labels,list) or not any(isinstance(x,dict) and x.get('name')=='bug' for x in labels):
        raise p.PostingBlocked('Unsupported non-bug report')
    if _hash(issue.get('body')) != target.body_sha256 or _hash(issue.get('title')) != target.title_sha256:
        raise p.PostingBlocked('Source title/body changed; review required')


def _hash(text) -> str:
    if not isinstance(text,str): raise p.PostingBlocked('Missing source text')
    return hashlib.sha256(text.encode()).hexdigest()


def attempt_marker(ctx: Context, event: str, configuration: str) -> str:
    """Return trusted deterministic marker, outside model-controlled text."""
    return 'clarifier-attempt-'+_hash(f'{p.REPOSITORY_ID}:{ctx.run_id}:{event}:{configuration}')


def format_comment(comment: str, ctx: Context, marker: str) -> str:
    """Return bounded bot/model/run attribution or raise PostingBlocked."""
    visible=re.sub(rf'`(?:@[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|{re.escape(p.SAFE_PLUGIN_SCOPE)})`','',comment)
    if '@' in visible or '\\' in comment: raise p.PostingBlocked('Public mentions or escaped markup are not permitted')
    result = (comment+f'\n\n**Created by AI (OpenAI Codex, {c.FIXED_CONFIG["model"]}).**'
              +f'\nPosted by GitHub Actions application; [run {ctx.run_id}](https://github.com/{p.REPOSITORY}/actions/runs/{ctx.run_id}).'
              +f'\n<!-- {marker} -->')
    if len(result)>c.MAX_COMMENT_CHARS: raise p.PostingBlocked('Attributed comment exceeds bound')
    return result


def plan(raw: str, ctx: Context, mode: str, target: p.Target, issue: dict,
         source_key: str, event: str, configuration: str, state: dict,
         release: release_gate.Release) -> CommentPlan | None:
    """Return one safe comment or silent None; raise typed errors on any mismatch."""
    result = parse_and_validate(raw)
    if result['decision'] != c.CLARIFY: return None
    check_mode(mode, ctx)
    check_enabled(state)
    check_target(issue, target)
    release_gate.verify(release, configuration, _hash(raw))
    marker = attempt_marker(ctx, event, configuration)
    text = format_comment(result['clarification'],ctx,marker)
    return CommentPlan(target.issue,text,source_key,event,configuration,marker)
