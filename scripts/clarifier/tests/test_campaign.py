"""Deterministic evaluator provenance/metric checks for tasks 51–62; no model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clarifier.controls import dry_state, ledger, policy
from clarifier.inference import packages, recording, request
from clarifier.outputs import campaign as cp, campaign_metrics as cm
from clarifier.shared import constants as c


def review(issue, decision):
    """Return a synthetic complete semantic-review fixture, never historical scoring."""
    return dict(issue=issue, run_id=f'fixture-{issue}', comment_quality='pass' if decision == c.CLARIFY else 'not_assessable',
                criteria=[dict(criterion=i, result='pass', evidence='Synthetic evaluator fixture.') for i in range(1, 8)],
                irrelevant_content=False, redundant_content=False, silent_branch_violation=False)


class Metrics(unittest.TestCase):
    def rows(self):
        expected = (c.CLARIFY, c.CLARIFY, c.HUMAN_REVIEW, *(c.NO_ACTION for _ in range(7)))
        return [cm.compare_case(dict(issue=i, run_id=f'fixture-{i}', status='completed', actual_decision=d,
                                     campaign_id='fixture', configuration_sha256='a'*64, public_actions=[]), d, review(i,d))
                for i,d in zip(c.HISTORICAL_CASE_IDS, expected)]

    def test_counts_distinguish_failed_match_quality_deferral_and_execution(self):
        rows=self.rows()
        rows[0]['quality_review']['comment_quality']='fail'
        rows[0]['clarification_success']=False
        rows[1].update(status='failed',actual_decision=None,decision_pass=False,clarification_success=False)
        rows[1]['quality_review']['comment_quality']='not_assessable'
        rows[2].update(actual_decision=c.NO_ACTION,decision_pass=False)
        report=cm.aggregate(rows,'fixture','a'*64)
        self.assertEqual(report['metrics']['decision_matches'],dict(count=8,denominator=10))
        self.assertEqual(report['metrics']['missed_necessary_clarifications'],dict(count=2,denominator=2))
        self.assertEqual(report['metrics']['all_deferrals'],dict(count=0,denominator=10))
        self.assertEqual(report['execution_failures'],[20606])
        self.assertEqual(report['confusion'][c.HUMAN_REVIEW][c.NO_ACTION],1)
        self.assertEqual(report['metrics']['public_writes']['count'],0)
        self.assertFalse(report['promotion_allowed'])

    def test_mixed_identity_missing_cases_and_borrowed_failure_are_rejected(self):
        for key,value in (('campaign_id','other'),('configuration_sha256','b'*64)):
            rows=self.rows();rows[0][key]=value
            with self.assertRaises(cp.CampaignError):cm.aggregate(rows,'fixture','a'*64)
        with self.assertRaises(cp.CampaignError):cm.aggregate(self.rows()[:-1],'fixture','a'*64)
        row=self.rows()[0];row['status']='failed'
        with self.assertRaises(cp.CampaignError):cm.compare_case(row,c.CLARIFY,review(row['issue'],c.CLARIFY))

    def test_quality_requires_all_criteria_and_correct_run(self):
        row=self.rows()[0]
        for change in ({'run_id':'other'}, {'criteria':[]}, {'comment_quality':'pending'}, {'redundant_content':None}):
            with self.assertRaises(cp.CampaignError):
                cm.compare_case(row,c.CLARIFY,{**review(row['issue'],c.CLARIFY),**change})


class Provenance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'item').write_text('Frozen')
        self.files={'item':recording.sha(b'Frozen')}

    def test_content_path_and_symlink_drift_fail_closed(self):
        cp.verify_files(self.root,self.files)
        (self.root/'item').write_text('Changed')
        with self.assertRaises(cp.CampaignError):cp.verify_files(self.root,self.files)
        with self.assertRaises(cp.CampaignError):cp.verify_files(self.root,{'../item':'a'*64})
        (self.root/'link').symlink_to(self.root/'item')
        with self.assertRaises(cp.CampaignError):cp.verify_files(self.root,{'link':recording.sha(b'Changed')})

    def test_manifest_hash_is_checked_before_loading_any_identity(self):
        folder=self.root/cp.CAMPAIGN_FOLDER;folder.mkdir(parents=True)
        (folder/cp.MANIFEST_NAME).write_text('{}')
        with self.assertRaises(cp.CampaignError):cp.verify_freeze(self.root,'a'*64)

    def test_isolation_rejects_inherited_context_tools_and_settings(self):
        case=dict(issue=20373,input_hashes=packages.load(20373).hashes)
        skill=(c.ROOT/c.SKILL_PATH).read_text().strip()
        prompt=request.build_prompt(packages.load(20373).source)
        sent=dict(model='gpt-6.1-sol',input=[dict(role='developer',content=[dict(type='input_text',text=skill)]),
            dict(role='user',content=[dict(type='input_text',text=prompt)])],tools=[],tool_choice='none',
            parallel_tool_calls=False,reasoning=dict(effort='xhigh'),store=False,stream=True)
        loaded=dict(loaded_content_sha256=recording.sha(skill.encode()),
            canonical_content_sha256=recording.sha((c.ROOT/c.SKILL_PATH).read_bytes()),
            native_prompt_matched=True,implicit_host_context_forwarded=False)
        manifest=dict(model='gpt-6.1-sol',reasoning_effort='xhigh',skill_sha256=loaded['canonical_content_sha256'],
                      cli_version='codex-cli 0.154.0',engine_binary_sha256='a'*64)
        record=dict(engine_version=manifest['cli_version'],engine_binary_sha256='a'*64,model_returned='gpt-6.1-sol',
                    inference_admitted=True,transport_request_attempts=1,tool_calls=[],model_workspace=str(self.root/'absent'),public_actions=[])
        (self.root/c.LOADER_FILE).write_text(json.dumps(loaded))
        for changes in ({},{'tools':[dict(type='shell')]},{'reasoning':dict(effort='low')},
                        {'input':sent['input']+[dict(role='user',content=[])]}):
            (self.root/c.REQUEST_FILE).write_text(json.dumps({**sent,**changes}))
            if changes:
                with self.assertRaises(cp.CampaignError):cp.verify_isolation(c.ROOT,self.root,manifest,case,record)
            else:
                cp.verify_isolation(c.ROOT,self.root,manifest,case,record)
        self.assertEqual(record['public_actions'],[])

    def test_attempt_inventory_and_declared_configuration_are_required(self):
        case=dict(issue=20373,run_id='fixture',input_hashes={})
        folder=self.root/'evals/runs/fixture';folder.mkdir(parents=True)
        record=dict(run_id='fixture',source_issue=20373,input_hashes={},status='failed',public_actions=[],
                    posting_available=False,configuration_sha256='a'*64,model_requested='model')
        recording.save_json(folder/c.RECORD_FILE,record)
        recording.save_json(folder/c.ARTIFACT_HASHES_FILE,{c.RECORD_FILE:recording.sha((folder/c.RECORD_FILE).read_bytes())})
        manifest=dict(configuration_sha256='a'*64,model='model')
        self.assertEqual(cp.read_attempt(self.root,manifest,case)[1]['public_actions'],[])
        with self.assertRaises(cp.CampaignError):cp.read_attempt(self.root,{**manifest,'configuration_sha256':'b'*64},case)
        (folder/c.RECORD_FILE).write_text('{}')
        with self.assertRaises(cp.CampaignError):cp.read_attempt(self.root,manifest,case)

    def test_declared_order_denies_duplicate_attempts(self):
        cases=[dict(issue=i,run_id=f'fixture-{i}') for i in c.HISTORICAL_CASE_IDS]
        self.assertEqual(cp.select_next(self.root,dict(cases=cases),20373),cases[0])
        with self.assertRaises(cp.CampaignError):cp.select_next(self.root,dict(cases=cases),20606)
        (self.root/'evals/runs'/cases[0]['run_id']).mkdir(parents=True)
        with self.assertRaises(cp.CampaignError):cp.select_next(self.root,dict(cases=cases),20373)

    def test_silent_route_denies_preview_comment_without_public_write(self):
        route=dict(source_issue=20373,posting_target=None,mode='preview',public_actions=[],
                   preview_comment='leak',validated_output=dict(decision=c.NO_ACTION,clarification=None))
        (self.root/c.VALIDATION_FILE).write_text(json.dumps(route))
        with self.assertRaises(cp.CampaignError):cp.verify_route(self.root,dict(issue=20373))
        self.assertEqual(route['public_actions'],[])

    def test_f_allowance_preserves_41_reservations_and_hosted_caps(self):
        dry_state.initialise(self.root)
        decision=self.root/dry_state.DEVELOPMENT_DECISION;decision.parent.mkdir(parents=True)
        decision.write_text(json.dumps(dict(actor_id=policy.OWNER_ID,scope=policy.LOCAL_WORKFLOW,
            rolling_limit=51,campaign_limit=51,campaign=ledger.CAMPAIGN,authorization_text='Synthetic explicit F authority')))
        with patch.object(dry_state.time,'time_ns',side_effect=range(1,53)):
            for n in range(41):dry_state.reserve(self.root,f'fixture-{n}',c.APPROVED)
            before=dry_state.DryStore(self.root/dry_state.STATE).read().state
            for n in range(10):dry_state.reserve(self.root,f'final-{n}',c.APPROVED)
            after=dry_state.DryStore(self.root/dry_state.STATE).read().state
            with self.assertRaises(policy.AdmissionDenied):dry_state.reserve(self.root,'excess',c.APPROVED)
        self.assertEqual(after['admissions'][:41],before['admissions'])
        self.assertEqual(len(after['admissions']),51)
        self.assertFalse(after['posting_enabled'])
        self.assertEqual((policy.ROLLING_LIMIT,policy.CAMPAIGN_LIMIT),(10,20))
