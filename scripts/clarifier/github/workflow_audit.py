"""Actual workflow capability inspection for task 23; complements actionlint."""
import json
from pathlib import Path
import re

from clarifier.shared import constants as c
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


def inspect(triage: str, stop: str) -> dict:
    """Return a permission/capability matrix or raise PlatformError on unsafe drift."""
    for text in (triage,stop):
        require('permissions: {}' in text and 'workflow_dispatch:' in text,'Missing manual/default permission policy')
        require(not re.search(r'^  (push|pull_request|issues|schedule|workflow_run):',text,re.M),'Automatic trigger forbidden')
        require('secrets.' not in text and 'write-all' not in text,'Unexpected secret/broad permissions')
        for action,pin in re.findall(r'uses: ([^@\s]+)@([^\s]+)',text):
            require(PINS.get(action)==pin,'Unpinned/unapproved dependency')
        require('persist-credentials: false' in text,'Checkout credential persistence')
    tj,sj=jobs(triage),jobs(stop)
    require(set(tj)=={'gate','admission','inference','output'} and set(sj)=={'stop'},'Unknown jobs')
    require('cancel-in-progress: false' in triage and 'queue:' not in triage,'Concurrency policy changed')
    require('concurrency:' not in stop and 'needs:' not in stop,'Stop depends on triage')
    require('actions: write' not in triage and 'actions: write' in sj['stop'],'Actions write outside stop')
    require('issues: write' in tj['output'] and all('issues: write' not in tj[k] for k in ('gate','admission','inference')),'Issues write outside handler')
    require('write' not in tj['inference'] and 'GH_TOKEN' not in tj['inference'] and 'github.token' not in tj['inference'],'Inference write credential/capability')
    require('inputs.mode == \'post\'' in tj['output'] and 'github.run_attempt == 1' in tj['output'],'Posting mode/rerun gate absent')
    require('timeout-minutes: 15' in tj['inference'] and 'retention-days: 30' in tj['inference'],'Missing runtime/retention limit')
    return dict(verification_type='static actual YAML capability inspection; external actionlint required',
                platform='GitHub Actions equivalent; no gh-aw compiler/lockfile',
                jobs={'gate':['contents:read'],'admission':['contents:write'],
                      'inference':['contents:read','no GitHub token in model environment','tools:[]'],
                      'output':['contents:write','issues:write','comment-only trusted handler'],
                      'stop':['contents:write','actions:write','independent']},
                silent_branches='no status/error/default comment integration',
                platform_limits=['Hosted inference engine/login absent','No OS jail or host egress firewall tested',
                                 'Runner image label is mutable','Provider/backend revision unpinned',
                                 'Token permissions do not restrict trusted code to one API operation',
                                 'GitHub scheduling/queue/cancel and log retention not live-tested',
                                 'Final recheck cannot atomically lock GitHub source/stop flag and HTTP POST'])


def run(root: Path=c.ROOT) -> dict:
    """Return inspection of the actual workflow files."""
    folder=root/'.github/workflows'
    return inspect((folder/p.TRIAGE_WORKFLOW).read_text(),(folder/p.STOP_WORKFLOW).read_text())


if __name__=='__main__': print(json.dumps(run(),indent=2))
