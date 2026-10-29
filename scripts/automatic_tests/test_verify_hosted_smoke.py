"""Synthetic saved-smoke corruption checks; no provider or GitHub access. Serves H02."""
import copy
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import verify_hosted_smoke as smoke
import verify_submission as submission


class HostedSmokeVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy=submission.disposable_copy(submission.ROOT)
        cls.root=cls.copy.__enter__()
        cls.addClassCleanup(cls.copy.__exit__,None,None,None)
        cls.original=Path('evals/hosted-v11/live-smoke-20261029')
        cls.folder=Path('evals/hosted-v11/synthetic-smoke-fixture')
        cls.enterClassContext(patch.object(smoke,'FOLDER',cls.folder))
        cls.enterClassContext(patch.object(smoke,'ASSESSMENT',cls.folder/'assessment.json'))
        shutil.copytree(cls.root/cls.original,cls.root/cls.folder)
        cls.preview=cls.folder/'artifacts/preview-40816597353/preview'
        # Repair delivery only in a disposable synthetic fixture, never in original evidence.
        canonical=cls.root/cls.preview/'configuration'/smoke.SKILL
        canonical.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(cls.root/cls.folder/'recovery/configuration'/smoke.SKILL,canonical)
        cls.summary=smoke.load(cls.root,cls.folder/'assessment.json')
        cls.summary['artifact_completeness_status']='passed'
        cls.summary['artifact_validation'].update(verified_original_files=26,missing_original_files=[],recovered_separately=[])
        cls.save(cls.folder/'assessment.json',cls.summary)
        copied=smoke.load(cls.root,cls.folder/'original-copy-sha256.json')
        copied[canonical.relative_to(cls.root/cls.folder).as_posix()]=smoke.digest(canonical.read_bytes())
        cls.save(cls.folder/'original-copy-sha256.json',copied)
        files={p.relative_to(cls.root/cls.folder).as_posix():smoke.digest(p.read_bytes())
               for p in (cls.root/cls.folder).rglob('*') if p.is_file() and p.name!='SHA256-MANIFEST.json'}
        cls.save(cls.folder/'SHA256-MANIFEST.json',files)
        cls.record=smoke.load(cls.root,cls.preview/'record.json')
        hashes=smoke.load(cls.root,cls.preview/'configuration-hashes.json')
        cls.configuration=dict(version='hosted-preview-v11',aggregate_sha256=hashes['aggregate_sha256'],
                               source_hashes=hashes['files']|hashes['source_hashes'])
        cls.reference=dict(assessment=(cls.folder/'assessment.json').as_posix(),
                           sha256=smoke.digest((cls.root/cls.folder/'assessment.json').read_bytes()))

    @classmethod
    def save(cls,name: Path,value: dict) -> None:
        """Write a synthetic test artifact only inside the disposable checkout."""
        (cls.root/name).write_text(json.dumps(value,indent=2)+'\n')

    def test_complete_synthetic_delivery_replays_without_model_calls(self):
        result=smoke.verify(self.root,self.reference,self.configuration)
        self.assertEqual(result['provider_calls'],1)
        self.assertEqual(result['artifact_completeness'],'passed')
        self.assertFalse(result['evaluated'])

    def test_original_missing_hidden_skill_is_still_a_failure(self):
        summary=smoke.load(self.root,self.original/'assessment.json')
        preview=self.original/'artifacts/preview-40816597353/preview'
        with self.assertRaisesRegex(ValueError,'original artifact export is incomplete'):
            smoke.verify_original_preview(self.root,preview,summary)

    def test_missing_hidden_skill_in_copy_is_rejected(self):
        path=self.root/self.preview/'configuration'/smoke.SKILL
        original=path.read_bytes(); path.unlink()
        try:
            with self.assertRaises(ValueError):
                smoke.verify(self.root,self.reference,self.configuration)
        finally:
            path.write_bytes(original)

    def test_current_configuration_cannot_be_substituted(self):
        expected=copy.deepcopy(self.configuration); expected['aggregate_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'current runtime aggregate differs'):
            smoke.verify_configuration(self.root,self.preview,self.summary,self.record,expected)

    def test_model_identity_mismatch_is_rejected(self):
        record=copy.deepcopy(self.record); record['model_returned']='different-model'
        with self.assertRaisesRegex(ValueError,'requested/returned model differs'):
            smoke.verify_model(self.root,self.preview,self.summary,record)

    def test_tool_actions_are_rejected(self):
        record=copy.deepcopy(self.record); record['tool_calls']=['forbidden']
        with self.assertRaisesRegex(ValueError,'unexpected model capability/action'):
            smoke.verify_model(self.root,self.preview,self.summary,record)

    def test_source_commit_must_contain_recorded_runtime_bytes(self):
        with self.assertRaisesRegex(ValueError,'source commit bytes differ'):
            smoke.verify_source_commit(self.root,self.summary['code_commit'],{smoke.SKILL:'0'*64})


if __name__=='__main__':
    unittest.main()
