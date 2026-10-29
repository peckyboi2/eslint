"""Shared staged contract checks, synthetic only. Serves B03."""
import json
from pathlib import Path
import tempfile
import unittest

from clarifier.controls import intake_identity
from clarifier.github import issue_io
from clarifier.inference import live_snapshot, packages, request, staging
from clarifier.outputs import routing
from clarifier.shared import constants as c
from clarifier.tests.test_intake_identity import fixture


class LivePipelineTests(unittest.TestCase):
    def test_live_and_historical_closed_contract(self):
        data,event=fixture(); ctx=intake_identity.verify(data,event)
        snap=live_snapshot.capture(ctx,event['issue'],event['issue'])
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            root=Path(folder); source=root/'source'; issue_io.write_source(snap,source)
            live=packages.Package(snap.number,source,snap.hashes,sum(map(len,snap.files.values())),{'kind':'opened'})
            for index,package in enumerate((live, packages.load(19118))):
                staged=root/str(index)
                manifest=staging.stage(package.source,staged,expected=package.hashes)
                prompt=request.build_prompt(staged,tuple(package.hashes))
                files=json.loads(prompt.split('\n',1)[1])['files']
                self.assertEqual(set(files),set(package.hashes))
                self.assertEqual(manifest['source_hashes'],package.hashes)
                self.assertNotIn('expected_decision',prompt)

    def test_dynamic_routes_are_silent(self):
        for decision in c.ALLOWED_DECISIONS:
            output=dict(decision=decision,rationale='Synthetic fixture',
                        clarification='Could you share the required configuration?' if decision=='clarify' else None)
            route=routing.route_result(output,'run-1','gpt-6.1-sol',source_issue=7,trusted_live=True)
            self.assertEqual(route['source_issue'],7)
            self.assertEqual(route['public_actions'],[])
            self.assertIsNone(route['posting_target'])
