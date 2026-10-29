"""Synthetic hosted adapter prerequisites; zero real provider calls. Serves B06."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from clarifier.inference import hosted_runtime as runtime, hosted_transport as hosted, recording, transport
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import TransportError


class HostedTransportTests(unittest.TestCase):
    def test_unverified_pin_fails_before_credential_or_launch(self):
        session=Mock(root=c.ROOT)
        profile=runtime.load_profile(c.ROOT)
        profile['linux_binary_sha256']=None
        with patch.object(runtime,'load_profile',return_value=profile), patch.object(hosted,'provider_credential') as credential, patch.object(runtime.subprocess,'run') as launch:
            with self.assertRaises(TransportError): runtime.prepare_engine(session)
        credential.assert_not_called(); launch.assert_not_called()

    def test_verified_linux_engine_checks_version_without_provider_access(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            binary=Path(folder)/'codex'; binary.write_bytes(b'synthetic pinned executable')
            profile=runtime.load_profile(c.ROOT)
            profile['linux_binary_sha256']=recording.sha(binary.read_bytes())
            session=Mock(root=c.ROOT,temporary=Mock(name='temporary'),record={})
            session.temporary.name=folder
            with patch.object(runtime,'load_profile',return_value=profile), patch.object(runtime.platform,'system',return_value='Linux'), patch.object(runtime.platform,'machine',return_value='x86_64'), patch.object(runtime.shutil,'which',return_value=str(binary)), patch.object(runtime.subprocess,'run',return_value=Mock(stdout='codex-cli 0.154.0\n')) as version, patch.object(hosted,'provider_credential') as credential:
                engine=runtime.prepare_engine(session)
            self.assertEqual(engine.binary,binary)
            self.assertEqual(session.record['engine_binary_sha256'],profile['linux_binary_sha256'])
            self.assertTrue(engine.home.is_dir())
            self.assertEqual(version.call_args.kwargs['env'],{'PATH':'/usr/bin:/bin','HOME':str(binary.parent)})
            version.assert_called_once(); credential.assert_not_called()

    def test_linux_binary_hash_mismatch_blocks_version_execution(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            binary=Path(folder)/'codex'; binary.write_bytes(b'wrong executable')
            session=Mock(root=c.ROOT,temporary=Mock())
            with patch.object(runtime.platform,'system',return_value='Linux'), patch.object(runtime.platform,'machine',return_value='x86_64'), patch.object(runtime.shutil,'which',return_value=str(binary)), patch.object(runtime.subprocess,'run') as version:
                with self.assertRaises(TransportError): runtime.prepare_engine(session)
            version.assert_not_called()

    def test_local_host_cannot_substitute_for_linux_engine(self):
        with patch.object(runtime.platform,'system',return_value='Darwin'), patch.object(runtime.platform,'machine',return_value='arm64'), patch.object(runtime.shutil,'which') as executable:
            with self.assertRaises(TransportError): runtime.prepare_engine(Mock(root=c.ROOT))
        executable.assert_not_called()

    def test_missing_credential_does_not_read_chatgpt_login(self):
        session=Mock(secrets=[])
        with patch.dict(hosted.os.environ,{},clear=True), patch.object(transport,'copy_login') as login:
            with self.assertRaises(TransportError): hosted.provider_credential(session)
        login.assert_not_called(); self.assertEqual(session.secrets,[])

    def test_credential_is_not_in_native_environment(self):
        engine=transport.Engine(Path('/trusted/codex'),Path('/tmp/engine'))
        argv,env=transport.invocation(engine,Mock(workspace=Path('/tmp/workspace')))
        self.assertNotIn(k.PROVIDER_KEY_ENV,env)
        self.assertNotIn('GH_TOKEN',env)
        self.assertNotIn(k.READ_TOKEN_ENV,env)

    def test_fixed_api_destination_and_no_redirect_retry(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            handler=object.__new__(hosted.ApiHandler)
            handler.server=Mock(credential='synthetic-key',folder=Path(folder))
            response=Mock(status=302); response.read.return_value=b'no redirect'
            with patch.object(hosted.http.client,'HTTPSConnection') as connect:
                connect.return_value.getresponse.return_value=response
                with self.assertRaises(TransportError): handler.fetch_provider({'tools':[]})
            connect.assert_called_once_with('api.openai.com',timeout=300)
            args=connect.return_value.request.call_args.args
            self.assertEqual(args[:2],('POST','/v1/responses'))
            self.assertEqual(json.loads(args[2]),{'tools':[]})
            for path in Path(folder).iterdir(): self.assertNotIn('synthetic-key',path.read_text())

    def test_returned_model_drift_blocks_cli_dispatch(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE_TEMP_ROOT) as folder:
            handler=object.__new__(hosted.ApiHandler)
            handler.server=Mock(folder=Path(folder),secrets=[],config={'model':'gpt-6.1-sol','response_limit_bytes':c.MAX_RESPONSE_BYTES})
            with self.assertRaises(TransportError): handler.record_response(transport.synthetic_response())
            self.assertTrue((Path(folder)/c.RAW_OUTPUT_FILE).exists())
