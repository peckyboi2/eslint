"""Actual workflow capability inspection for task 23; complements actionlint."""
import json
from pathlib import Path
import re

from clarifier.shared import constants as c, intake_constants as k
from clarifier.controls import policy as p

PINS = {'actions/checkout':'11bd71901bbe5b1630ceea73d27597364c9af683',
        'actions/upload-artifact':'ea165f8d65b6e75b540449e92b4886f43607fa02',
        'actions/download-artifact':'d3f86a106a0bac45b974a628896c90dbdf5c8093'}


def jobs(text: str) -> dict[str,str]:
    """Return explicitly delimited jobs from the constrained authored YAML."""
    body=text.split('\njobs:\n',1)[1]
    boundaries=list(re.finditer(r'^  ([a-z]+):\n',body,re.M))
    return {match.group(1):body[match.end():boundaries[i+1].start() if i+1<len(boundaries) else len(body)] for i,match in enumerate(boundaries)}


def require(condition: bool, message: str) -> None:
    """Raise PlatformError for an unsafe authored-workflow capability."""
    if not condition: raise p.PlatformError(message)


def inspect_provider_secret(triage_jobs: dict[str, str], stop: str) -> None:
    """Raise PlatformError unless the sole provider secret is step-scoped to inference."""
    inference = triage_jobs['inference']
    expected = ('      - env:\n'
                '          CLARIFIER_READ_TOKEN: ${{ github.token }}\n'
                '          CLARIFIER_PROVIDER_KEY: ${{ secrets.CLARIFIER_PROVIDER_KEY }}\n'
                '        run: python3 -B scripts/clarifier/workflow.py infer')
    require(expected in inference, 'Provider credential is not scoped to the inference command')
    require(inference.count('secrets.') == 1, 'Unexpected inference secret reference')
    require('secrets.' not in stop and all('secrets.' not in triage_jobs[name]
            for name in ('gate', 'admission')), 'Provider credential outside inference')


def inspect(triage: str, stop: str, approval: str | None = None) -> dict:
    """Return inspected authored capability matrix or raise PlatformError on drift."""
    for text in (triage,stop,*([approval] if approval is not None else [])):
        require('permissions: {}' in text,'Missing default permission policy')
        require('write-all' not in text,'Unexpected broad permissions')
        for action,pin in re.findall(r'uses: ([^@\s]+)@([^\s]+)',text):
            require(PINS.get(action)==pin,'Unpinned/unapproved dependency')
        require('persist-credentials: false' in text,'Checkout credential persistence')
    require('  issues:\n    types: [opened]' in triage,'Only issue openings accepted')
    require(not re.search(r'^  (push|pull_request|schedule|workflow_run|workflow_dispatch|issue_comment):',triage,re.M),'Unexpected trigger')
    require('workflow_dispatch:' in stop and not re.search(r'^  issues:',stop,re.M),'Stop must be owner manual dispatch')
    tj,sj=jobs(triage),jobs(stop)
    require(set(tj)=={'gate','admission','inference'} and set(sj)=={'stop'},'Unknown jobs/public output from issue event')
    require(triage.count('secrets.') == 1, 'Unexpected workflow-wide secret reference')
    inspect_provider_secret(tj, stop)
    for name in ('gate', 'admission', 'inference'):
        require('actions: read' in tj[name] and 'issues: read' in tj[name], 'Missing live metadata read permission')
    require(triage.count('queue: max')==1 and 'cancel-in-progress: false' in triage and 'cancel-in-progress: true' not in triage,'Bounded queue policy changed')
    require('concurrency:' not in stop and 'needs:' not in stop,'Stop depends on triage')
    require('actions: write' not in triage and 'actions: write' in sj['stop'],'Actions write outside stop')
    require('issues: write' not in triage and 'issues: write' not in stop,'Public write capability in issue/stop workflow')
    require('contents: read' in tj['gate'] and 'contents: write' not in tj['gate'],'Gate is not read only')
    require('contents: write' in tj['admission'] and 'GH_TOKEN' in tj['admission'],'Missing dedicated admission edge')
    require('write' not in tj['inference'] and 'GH_TOKEN' not in tj['inference'],'Inference write credential/capability')
    require('CLARIFIER_READ_TOKEN: ${{ github.token }}' in tj['inference'],'Missing harness-only read token')
    require('hosted_install.py --destination "$RUNNER_TEMP/clarifier-bin" --github-path' in tj['inference'], 'Missing pinned runtime installation')
    require('timeout-minutes: 15' in tj['inference'] and 'retention-days: 30' in tj['inference'],'Missing runtime/retention limit')
    if approval is not None:
        require('workflow_dispatch:' in approval and 'issues: write' not in approval,'Approval must remain manual/inactive')
        require('secrets.' not in approval and 'approve.py' in approval,'Unreviewed approval activation')
    return dict(verification_type='static actual YAML capability inspection; not hosted enforcement',
                platform='GitHub Actions equivalent; no gh-aw compiler/lockfile',
                jobs={'gate':['contents:read','actions:read','issues:read'],
                      'admission':['contents:write','actions:read','issues:read'],
                      'inference':['contents:read','actions:read','issues:read','provider key only in trusted gateway step','no state/post token in model environment','tools:[]'],
                      'approval':['contents:read','manual; release blocked before credentials'],
                      'stop':['contents:write','actions:write','independent']},
                queue=dict(running=1,pending=100,overflow='GitHub cancellation; manual recovery'),
                silent_branches='no public comment job in issue workflow',
                platform_limits=['Linux binary pinned; installation and provider access not yet observed in GitHub','No OS jail or host firewall tested',
                                 'Runner image mutable; provider revision unpinned',
                                 'GitHub scheduling/cancel/retention untested',
                                 'Final check cannot atomically lock GitHub edits or stop flag'])


def run(root: Path=c.ROOT) -> dict:
    """Return inspection of the actual workflow files."""
    folder=root/'.github/workflows'
    return inspect((folder/p.TRIAGE_WORKFLOW).read_text(),(folder/p.STOP_WORKFLOW).read_text(),
                   (folder/k.APPROVAL_WORKFLOW).read_text())


if __name__=='__main__': print(json.dumps(run(),indent=2))
