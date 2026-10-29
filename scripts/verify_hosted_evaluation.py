"""Replay the frozen 13-case hosted campaign without invoking a provider."""
import base64
from collections import Counter
import json
from pathlib import Path
import subprocess

import evaluate_hosted as evaluator
import verify_hosted_smoke as smoke
from clarifier.inference.transport import inspect_response
from clarifier.outputs.validation import parse_and_validate
from clarifier.outputs.routing import route_result

FOLDER=Path('evals/golden/hosted-v11-20261029')
CAMPAIGN=evaluator.FOLDER
SUMMARY=FOLDER/'comparison.json'


def require(value,reason):
    if not value:raise ValueError('Hosted evaluation: '+reason)


def load(root,name):return smoke.load(root,name)


def sha(data):return smoke.digest(data)


def inventory(root,folder):
    """Check exact original artifact bytes, including hidden native skill evidence."""
    manifest=load(root,folder/'artifact-hashes.json')
    actual={p.relative_to(root/folder).as_posix() for p in (root/folder).rglob('*') if p.is_file()}
    require(actual==set(manifest)|{'artifact-hashes.json'},'original artifact inventory differs')
    for name,digest in manifest.items():
        require(sha(smoke.read(root,folder/name))==digest,'original artifact hash differs: '+name)
    require('configuration/'+smoke.SKILL in manifest,'hidden canonical skill missing')


def case(root,row,configuration,freeze_sha,commit):
    """Bind original GitHub dispatch, quota envelope, native request and actual answer."""
    label=str(row.get('attack',row['issue']))
    folder=FOLDER/'slots'/f'{row["slot"]:02}-{label}'
    run=load(root,folder/'run-final.json');record_folder=folder/'artifacts/attempt'
    record=load(root,record_folder/'record.json');saved=load(root,folder/'artifacts/admission.json')
    require(run['repository']['full_name']=='peckyboi2/eslint' and run['repository']['id']==1435519573,'wrong run repository')
    require(run['path']=='.github/workflows/clarifier-evaluate.yml' and run['event']=='workflow_dispatch'
            and run['head_branch']=='main' and run['head_sha']==commit and run['run_attempt']==1
            and run['status']=='completed' and run['conclusion']=='success','dispatch receipt differs')
    require(run['actor']['id']==run['triggering_actor']['id']==234542779,'run owner differs')
    require(record['run_id']==row['run_id'] and record['github_run_id']==str(run['id'])
            and record['code_commit']==commit and record['evaluation_slot']==row['slot'],'record origin differs')
    plan=load(root,CAMPAIGN/'plan.json');plan['active_rolling_window_seconds']=60
    ctx=evaluator.identity.Context(str(run['id']),1,commit,evaluator.WORKFLOW)
    require(saved==record['binding']==evaluator.binding(ctx,plan,row,freeze_sha),'admission binding differs')
    inventory(root,record_folder)
    config=load(root,record_folder/'configuration-hashes.json')
    require(config['files']|config['source_hashes']==configuration['source_hashes']
            and config['aggregate_sha256']==record['configuration_sha256']==configuration['aggregate_sha256'],'runtime differs')
    require(record['input_hashes']==row['input_hashes'],'input hashes differ')
    for name,digest in row['input_hashes'].items():
        require(sha(smoke.read(root,record_folder/'input'/name))==digest,'retained input differs')
    request=load(root,record_folder/'request.json');loader=load(root,record_folder/'loader.json')
    completion,text=inspect_response(smoke.read(root,record_folder/'response.sse'))
    require(record['status']=='completed' and record['errors']==[] and record['engine_exit_code']==0,'execution failed')
    require(record['transport_request_attempts']==1,'request allowance differs')
    require(record['model_requested']==record['model_returned']==request['model']==completion['model']=='gpt-6.1-sol','model differs')
    require(record['engine_binary_sha256']=='3188814c35471432d4123203e0eb38e5bddc60226e3d7ddf0e59e649ea140022'
            and record['engine_version']=='codex-cli 0.154.0','engine differs')
    require(record['tool_calls']==request['tools']==[] and request['tool_choice']=='none','model tool capability/action')
    require(record['public_actions']==saved['public_actions']==[] and record['posting_available'] is False,'public action')
    require(load(root,record_folder/'provider-status.json')['status']==200,'provider failed')
    require(record['usage']==completion['usage'],'usage differs')
    require(smoke.read(root,record_folder/'raw-output.txt').decode()==text,'raw output differs')
    output=parse_and_validate(text);validation=load(root,record_folder/'validation.json')
    require(validation['valid'] is True and validation['validated_output']==output
            and validation['decision']==output['decision'] and validation['public_actions']==[],'validation differs')
    require(validation==route_result(output,row['run_id'],'gpt-6.1-sol',source_issue=row['issue']),
            'trusted routing/attribution differs')
    canonical=smoke.read(root,record_folder/'configuration'/smoke.SKILL)
    require(loader['native_prompt_matched'] is True and loader['implicit_host_context_forwarded'] is False
            and loader['outbound_tools']==[] and loader['loaded_content_sha256']==sha(canonical.decode().strip().encode())
            and loader['canonical_content_sha256']==record['skill_sha256']==sha(canonical),'native skill proof differs')
    return dict(slot=row['slot'],case=label,kind=row['kind'],expected_decision=row['expected_decision'],
                actual_decision=output['decision'],decision_match=row['expected_decision']==output['decision'],
                github_run_id=str(run['id']),run_url=run['html_url'],run_id=row['run_id'],provider_calls=1,
                usage=record['usage'],tool_calls=[],public_actions=[])


def aggregate(rows):
    historical=rows[:10];attacks=rows[10:]
    return dict(historical_matches=sum(row['decision_match'] for row in historical),historical_total=10,
                adversarial_matches=sum(row['decision_match'] for row in attacks),adversarial_total=3,
                always_no_action_baseline=7,provider_calls=sum(row['provider_calls'] for row in rows),
                unnecessary_requests=sum(row['expected_decision']=='no_action' and row['actual_decision']=='clarify' for row in historical),
                unsupported_requests=sum(row['expected_decision']=='human_review' and row['actual_decision']=='clarify' for row in historical),
                missed_clarifications=sum(row['expected_decision']=='clarify' and row['actual_decision']!='clarify' for row in historical),
                human_review_deferrals=sum(row['actual_decision']=='human_review' for row in historical),
                confusion={label:dict(Counter(row['actual_decision'] for row in historical if row['expected_decision']==label)) for label in ('clarify','no_action','human_review')},
                usage={key:sum(row['usage'][key] for row in rows) for key in ('input_tokens','output_tokens','total_tokens')},
                public_actions=0,tool_calls=0)


def verify(root,reference,configuration):
    """Verify all 13 real attempts, fixed expectations, source freeze and restoration."""
    require(reference['path']==SUMMARY.as_posix(),'unexpected summary path')
    require(sha(smoke.read(root,SUMMARY))==reference['sha256'],'comparison review hash differs')
    summary=load(root,SUMMARY);freeze_sha=sha(smoke.read(root,CAMPAIGN/'freeze.json'))
    require(summary['freeze_sha256']==freeze_sha,'freeze reference differs')
    plan,frozen=evaluator.reviewed(root,freeze_sha)
    commit=summary['source_commit']
    smoke.verify_source_commit(root,commit,frozen['files'])
    rows=[case(root,row,configuration,freeze_sha,commit) for row in plan['cases']]
    require(summary['cases']==rows and summary['aggregate']==aggregate(rows),'saved comparison differs from actual outputs')
    before=json.loads(base64.b64decode(load(root,CAMPAIGN/'state-before.json')['content']))
    after=json.loads(base64.b64decode(load(root,CAMPAIGN/'state-after.json')['content']))
    require(after['admissions'][:len(before['admissions'])]==before['admissions']
            and len(before['admissions'])==2 and len(after['admissions'])==15,'reservation history changed')
    require(before['posts']==after['posts']==[] and before['posting_enabled'] is after['posting_enabled'] is False,'posting enabled')
    for row in rows:
        matched=[item for item in after['admissions'] if item['run_id']==row['github_run_id']]
        require(len(matched)==1,'missing or duplicate durable reservation')
        original=plan['cases'][row['slot']-1]
        require(matched[0]['input_key']==evaluator.slot_key(plan,original),'reservation source differs')
    restored=load(root,CAMPAIGN/'restoration.json')
    require(restored['window']=='restored' and restored['variable_receipt']['value']=='86400'
            and restored['workflow']=='disabled' and restored['workflow_receipt']['state']=='disabled_manually','temporary exception not restored')
    review=load(root,FOLDER/'semantic-reviews.json')
    require(review['reviewer']=='assistant; not independent human validation','review attribution differs')
    require(review['comparison_sha256']==reference['sha256'],'semantic review not bound to outputs')
    require(len(review['cases'])==13 and [r['slot'] for r in review['cases']]==list(range(1,14)),'semantic review incomplete')
    for result,assessment in zip(rows,review['cases']):
        require(assessment['decision_match']==result['decision_match'] and assessment['actual_decision']==result['actual_decision'],
                'semantic decision assessment differs')
        require(bool(assessment['assessment']),'missing semantic explanation')
        if result['actual_decision']=='clarify':
            require([criterion['criterion'] for criterion in assessment['criteria']]==list(range(1,8)),
                    'clarification criteria incomplete')
            require(all(criterion['status'] in ('pass','fail','not-assessable') and criterion['reason'] for criterion in assessment['criteria']),
                    'clarification assessment missing reason')
            require(assessment['quality_pass']==all(criterion['status']=='pass' for criterion in assessment['criteria']),
                    'wording score differs from criteria')
            label=result['case'];folder=FOLDER/'slots'/f'{result["slot"]:02}-{label}'/'artifacts/attempt'
            text=smoke.read(root,folder/'raw-output.txt').decode()
            output=parse_and_validate(text)
            for criterion in assessment['criteria']:
                require(criterion['excerpt'] in output['clarification'] or criterion['excerpt'] in output['rationale'],
                        'review excerpt not in actual answer')
    return dict(evaluated=True,source_commit=commit,configuration_sha256=configuration['aggregate_sha256'],
                **summary['aggregate'],temporary_evaluation_window_seconds=60,normal_window_restored_seconds=86400,
                verification='Offline replay of original hosted API artifacts and predeclared outcomes; no model request')
