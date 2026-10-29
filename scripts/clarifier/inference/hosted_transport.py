"""One fixed API exchange behind native Codex skill loading. Serves B06."""
import http.client
import json
import os

from clarifier.inference import recording as rec, request, transport
from clarifier.shared import constants as c, intake_constants as k
from clarifier.shared.errors import TransportError, guarded


class ApiHandler(transport.Handler):
    """Trusted API edge: token lives in gateway memory, never the model/CLI environment."""
    @guarded(TransportError, 'Hosted API exchange failed; no automatic retry')
    def fetch_provider(self, outgoing: dict) -> bytes:
        """Return one bounded API SSE response or raise redacted TransportError."""
        connection = http.client.HTTPSConnection(k.API_HOST,timeout=c.RUNTIME_SECONDS)
        headers = {'Authorization':'Bearer '+self.server.credential,
                   'Content-Type':'application/json','Accept':'text/event-stream'}
        try:
            connection.request('POST',k.API_PATH,json.dumps(outgoing).encode(),headers)
            response = connection.getresponse()
            raw = response.read(c.MAX_RESPONSE_BYTES+1)
            rec.save_json(self.server.folder/c.PROVIDER_STATUS_FILE,
                          dict(status=response.status,host=k.API_HOST,path=k.API_PATH))
            if response.status != 200:
                raise TransportError(f'Hosted provider HTTP {response.status}')
            return raw
        finally:
            connection.close()

    def record_response(self, raw: bytes) -> None:
        """Preserve response then reject model-ID drift before any CLI dispatch."""
        super().record_response(raw)
        if self.server.completion.get('model') != self.server.config['model']:
            raise TransportError('Hosted returned model differs from requested frozen model')


class ApiGate(transport.Gate):
    """The existing native-envelope/tool rejection gate with a fixed API edge."""
    def __init__(self, session, loaded, prompt: str, credential: str):
        """Construct one gateway or raise TransportError; credential is never recorded."""
        super().__init__(session.folder,loaded.text,prompt,session.config)
        self.RequestHandlerClass = ApiHandler
        self.credential = credential
        self.secrets = session.secrets


@guarded(TransportError, 'Hosted provider credential unavailable')
def provider_credential(session) -> str:
    """Return explicitly provisioned gateway key or raise; never inspect local login."""
    credential = os.environ.get(k.PROVIDER_KEY_ENV)
    if not credential or not credential.isascii() or any(char.isspace() for char in credential):
        raise TransportError('Hosted API credential absent; owner activation required')
    session.secrets.append(credential)
    return credential


def execute(session, staged, loaded, prompt: str, engine) -> None:
    """Execute native skill-bound CLI once or raise TransportError; no GitHub token."""
    credential = provider_credential(session)
    session.gate = ApiGate(session,loaded,prompt,credential)
    url = session.gate.start()
    settings = request.make_config(url,loaded.path,session.config,True)
    argv,env = transport.record_invocation(session,engine,staged,prompt,settings)
    session.record['engine_exit_code'] = transport.execute_engine(
        staged.workspace,session.folder,prompt,argv,env,c.RUNTIME_SECONDS,session.secrets)
