"""Task 20 comment-handler infrastructure tests; no approval/live-write claims."""
import hashlib
import json
import unittest
from unittest.mock import Mock

from clarifier.controls import identity
from clarifier.outputs import output_handler as h
from clarifier.controls import policy as p
from clarifier.shared.errors import ClarifierError
from clarifier.outputs.release_gate import Release
from clarifier.tests.test_admission import enabled
from clarifier.tests.test_identity import context_data

RAW=json.dumps(dict(decision='clarify',rationale='Missing minimal setup.',clarification='Could you share a minimal reproduction with the configuration?'))


def fixture():
    state=enabled();state['posting_enabled']=True
    state['decisions'].append(dict(actor_id=p.OWNER_ID,at=3,reason='Mock posting release only',action='enable-posting'))
    target=p.Target(issue=1,body_sha256=hashlib.sha256(b'body').hexdigest(),title_sha256=hashlib.sha256(b'title').hexdigest())
    root=f'https://api.github.com/repos/{p.REPOSITORY}'
    issue=dict(number=1,repository_url=root,url=root+'/issues/1',state='open',locked=False,labels=[{'name':'bug'}],body='body',title='title')
    release=Release('b'*64,hashlib.sha256(RAW.encode()).hexdigest(),'mock-preview',('mock-1','mock-2','mock-3'))
    return dict(raw=RAW,ctx=identity.verify(context_data()),mode='post',target=target,issue=issue,source_key='a'*64,event='e'*64,configuration='b'*64,state=state,release=release)


class OutputHandlerTests(unittest.TestCase):
    def test_one_attributed_bounded_plan(self):
        args=fixture();result=h.plan(**args)
        self.assertEqual(result.report,1);self.assertIn('GitHub Actions application',result.text)
        self.assertIn('gpt-6.1-sol',result.text);self.assertLessEqual(len(result.text),2000)

    def test_rejected_or_silent_paths_never_write(self):
        args=fixture()
        variants=[{'raw':'bad'},{'mode':'preview'},{'target':p.LIVE_TARGET},
                  {'ctx':identity.verify({**context_data(),'run_attempt':'2'})},
                  {'state':{**args['state'],'enabled':False}}, {'state':{}},
                  {'release':None}, {'configuration':'c'*64}]
        for key,value in [('number',2),('pull_request',{}),('body','edited'),('labels',[]),('repository_url','upstream')]:
            variants.append({'issue':{**args['issue'],key:value}})
        for variant in variants:
            write=Mock()
            with self.subTest(variant=variant):
                with self.assertRaises(ClarifierError): h.plan(**{**args,**variant});write()
                write.assert_not_called()
        for decision in ('no_action','human_review'):
            result=h.plan(**{**args,'raw':json.dumps(dict(decision=decision,rationale='Sufficient or uncertain.',clarification=None))})
            self.assertIsNone(result)

    def test_mentions_rejected_even_in_code(self):
        args=fixture()
        with self.assertRaises(p.PostingBlocked): h.format_comment('`@reporter` please respond',args['ctx'],'trusted-marker')

    def test_scoped_package_in_code_is_safe_but_escaped_or_plain_mentions_are_blocked(self):
        args=fixture()
        self.assertIn('`@fe/eslint-config`',h.format_comment('Please share `@fe/eslint-config`.',args['ctx'],'trusted-marker'))
        self.assertIn('`@typescript-eslint`',h.format_comment('The `@typescript-eslint` plugin.',args['ctx'],'trusted-marker'))
        for text in ('@reporter please respond','`@reporter` please respond',r'\`@fe/eslint-config\` please respond'):
            with self.assertRaises(p.PostingBlocked):h.format_comment(text,args['ctx'],'trusted-marker')

    def test_live_release_is_disabled(self):
        from clarifier.outputs.release_gate import live_release
        with self.assertRaises(p.PostingBlocked): live_release()
