"""Synthetic hosted-evaluation identity, freeze and shared-quota safeguards; no provider."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import evaluate_hosted as evaluate
from clarifier.controls import admission, identity, ledger, policy as p
from clarifier.shared import constants as c
from clarifier.shared.errors import ConfigurationError


class HostedEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((evaluate.ROOT/'evals/automatic-v10/evaluation-plan.json').read_text())
        cls.plan.update(campaign_id='synthetic-hosted-evaluation',attempt_limit=13,retries=0,posting=False,temporary_rolling_window_seconds=60)
        for row in cls.plan['cases'][10:]:
            row['issue']=c.SOURCE_ISSUE

    def ctx(self, number=100):
        return identity.Context(str(number),1,'a'*40,evaluate.WORKFLOW)

    def state(self):
        state=ledger.initial(100,'Synthetic owner bootstrap')
        state['enabled']=True
        state['decisions'].append(dict(actor_id=p.OWNER_ID,at=100,action='enable-preview',reason='Synthetic evaluation'))
        return state

    def test_context_accepts_only_owner_original_dispatch_on_main(self):
        data=dict(event_name='workflow_dispatch',repository=p.REPOSITORY,repository_id=str(p.REPOSITORY_ID),
                  repository_owner=p.OWNER,repository_owner_id=str(p.OWNER_ID),actor=p.OWNER,actor_id=str(p.OWNER_ID),
                  triggering_actor=p.OWNER,ref=p.TRUSTED_REF,ref_type='branch',run_attempt=1,run_id='1234',sha='a'*40,
                  workflow_sha='a'*40,workflow_ref=f'{p.REPOSITORY}/.github/workflows/{evaluate.WORKFLOW}@{p.TRUSTED_REF}')
        self.assertEqual(evaluate.context(data).workflow,evaluate.WORKFLOW)
        for key,value in [('actor','attacker'),('run_attempt',2),('workflow_sha','b'*40),('ref','refs/heads/untrusted'),('event_name','issues')]:
            with self.subTest(field=key), self.assertRaises(ConfigurationError):
                evaluate.context({**data,key:value})

    def test_two_smokes_leave_only_eight_slots_in_the_current_daily_window(self):
        state=self.state()
        for number in (1,2):
            state=admission.reserve(state,self.ctx(number),'f'*64,100)
        for slot in range(1,9):
            state=evaluate.reserve(state,self.ctx(100+slot),self.plan,self.plan['cases'][slot-1],100)
        with self.assertRaises(p.AdmissionDenied):
            evaluate.reserve(state,self.ctx(109),self.plan,self.plan['cases'][8],100)
        self.assertEqual(len(state['admissions']),10)
        self.assertEqual(state['posts'],[])
        for slot in range(9,14):
            state=evaluate.reserve(state,self.ctx(100+slot),self.plan,self.plan['cases'][slot-1],100+p.ROLLING_SECONDS+1)
        self.assertEqual(len(state['admissions']),15)
        self.assertEqual(state['posts'],[])

    def test_consumed_slot_cannot_be_retried_with_a_new_github_run(self):
        state=evaluate.reserve(self.state(),self.ctx(),self.plan,self.plan['cases'][0],100)
        with self.assertRaises(ConfigurationError):
            evaluate.reserve(state,self.ctx(999),self.plan,self.plan['cases'][0],100)

    def test_temporary_window_preserves_all_reservations_and_restores_policy(self):
        plan={**self.plan,'active_rolling_window_seconds':60}
        state=self.state()
        for number in (1,2):
            state=admission.reserve(state,self.ctx(number),'f'*64,100)
        for slot in range(1,14):
            state=evaluate.reserve(state,self.ctx(100+slot),plan,plan['cases'][slot-1],200+61*slot)
            self.assertEqual(p.ROLLING_SECONDS,86400)
        self.assertEqual(len(state['admissions']),15)
        with self.assertRaises(p.AdmissionDenied):
            admission.reserve(state,self.ctx(999),'e'*64,1000)
        state=ledger.initial(100,'Synthetic disabled bootstrap')
        fresh={**plan,'campaign_id':'another-campaign'}
        with self.assertRaises(p.AdmissionDenied):
            evaluate.reserve(state,self.ctx(999),fresh,fresh['cases'][0],1000)
        self.assertEqual(p.ROLLING_SECONDS,86400)

    def test_slots_cannot_be_skipped(self):
        with self.assertRaises(ConfigurationError):
            evaluate.reserve(self.state(),self.ctx(),self.plan,self.plan['cases'][1],100)

    def test_disabled_state_denies_admission(self):
        state=ledger.initial(100,'Synthetic disabled bootstrap')
        with self.assertRaises(p.AdmissionDenied):
            evaluate.reserve(state,self.ctx(),self.plan,self.plan['cases'][0],100)

    def test_binding_requires_same_run_source_and_persisted_reservation(self):
        row=self.plan['cases'][0];ctx=self.ctx();saved=evaluate.binding(ctx,self.plan,row,'b'*64)
        state=evaluate.reserve(self.state(),ctx,self.plan,row,100)
        evaluate.verify_reservation(state,ctx,self.plan,row,'b'*64,saved)
        for altered in ({**saved,'slot':2},{**saved,'run_id':'999'},{**saved,'input_hashes':{}}):
            with self.assertRaises(ConfigurationError):
                evaluate.verify_reservation(state,ctx,self.plan,row,'b'*64,altered)
        with self.assertRaises(ConfigurationError):
            evaluate.verify_reservation(self.state(),ctx,self.plan,row,'b'*64,saved)

    def test_freeze_approval_and_sources_are_checked_before_any_provider(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            root=Path(folder); base=root/evaluate.FOLDER;base.mkdir(parents=True)
            plan=copy.deepcopy(self.plan)
            (base/'plan.json').write_text(json.dumps(plan))
            names={name.as_posix() for name in c.CONFIG_PATHS}|{'scripts/evaluate_hosted.py',f'.github/workflows/{evaluate.WORKFLOW}'}
            names|={f'evals/golden/prepared-inputs/inputs/{row["issue"]}/{name}' for row in plan['cases'][:10] for name in row['input_hashes']}
            for name in names:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(evaluate.ROOT/name,target)
            names.add((evaluate.FOLDER/'plan.json').as_posix())
            files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
            runtime={name.as_posix():files[name.as_posix()] for name in c.CONFIG_PATHS}
            plan_sha=hashlib.sha256((base/'plan.json').read_bytes()).hexdigest()
            frozen=dict(plan_sha256=plan_sha,files=files,configuration_sha256=hashlib.sha256(json.dumps(runtime,sort_keys=True,separators=(',',':')).encode()).hexdigest())
            (base/'freeze.json').write_text(json.dumps(frozen));freeze_sha=hashlib.sha256((base/'freeze.json').read_bytes()).hexdigest()
            approval=dict(owner_id=p.OWNER_ID,campaign_id=plan['campaign_id'],plan_sha256=plan_sha,freeze_sha256=freeze_sha,
                          attempt_limit=13,allow_provider_calls=True,posting=False,temporary_rolling_window_seconds=60,
                          authorization_text='Synthetic fixture, never actual provider approval')
            (base/'approval.json').write_text(json.dumps(approval))
            evaluate.reviewed(root,freeze_sha)
            approval['attempt_limit']=14;(base/'approval.json').write_text(json.dumps(approval))
            with self.assertRaises(ConfigurationError):evaluate.reviewed(root,freeze_sha)
            approval['attempt_limit']=13;(base/'approval.json').write_text(json.dumps(approval))
            (root/c.SKILL_PATH).write_text('Poisoned trusted instructions')
            with self.assertRaises(ConfigurationError):evaluate.reviewed(root,freeze_sha)

    def test_workflow_separates_provider_secret_and_state_write(self):
        text=(evaluate.ROOT/'.github/workflows'/evaluate.WORKFLOW).read_text()
        admission_job=text.split('  admission:',1)[1].split('  inference:',1)[0]
        inference_job=text.split('  inference:',1)[1]
        self.assertNotIn('secrets.',admission_job)
        self.assertIn('contents: write',admission_job)
        self.assertNotIn('contents: write',inference_job)
        self.assertNotIn('issues: write',text)
        self.assertEqual(text.count('secrets.CLARIFIER_PROVIDER_KEY'),1)
        self.assertIn('include-hidden-files: true',inference_job)
        self.assertIn('persist-credentials: false',text)


if __name__=='__main__':unittest.main()
