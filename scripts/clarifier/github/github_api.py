"""Trusted fixed-host HTTP edge for tasks 17–28; never exposed to inference."""
import json
import os
import urllib.error
import urllib.request

from clarifier.controls import policy as p


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent token forwarding by rejecting all redirects."""
    def redirect_request(self, *args, **kwargs):
        """Return no redirect request."""
        return None


class GitHub:
    """Private transport for deterministic helpers; credentials stay in memory."""
    def __init__(self, token: str | None = None):
        """Construct a trusted edge; no credential read until a gated job calls it."""
        self._token = token

    def _request(self, method: str, path: str, body=None):
        """Return bounded GitHub JSON or raise redacted PlatformError/Conflict."""
        if not (path == f'/repos/{p.REPOSITORY}' or path == f'/users/{p.OWNER}' or path.startswith(f'/repos/{p.REPOSITORY}/')):
            raise p.PlatformError('Endpoint outside trusted sandbox')
        if method != 'GET' and not self._token:
            raise p.PlatformError('Privileged job token unavailable')
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': p.POLICY_VERSION,
                   'X-GitHub-Api-Version': '2022-11-28'}
        if self._token: headers['Authorization'] = 'Bearer '+self._token
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request('https://api.github.com'+path, data=data, headers=headers, method=method)
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=p.API_TIMEOUT) as response:
                raw = response.read(p.API_LIMIT_BYTES+1)
            if len(raw) > p.API_LIMIT_BYTES: raise p.PlatformError('Platform response exceeds bound')
            return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            if method == 'PATCH' and error.code in (409, 422): raise p.Conflict('State ref conflict') from None
            raise p.PlatformError(f'Platform HTTP {error.code}; no automatic write retry') from None
        except (OSError, ValueError):
            raise p.PlatformError('Platform response unavailable; inspect state before retry') from None

    def verify_context(self, context) -> None:
        """Verify live identity/ref before a privileged boundary or raise IdentityError."""
        from clarifier.controls.identity import verify_live
        if context.event_name == 'issues':
            from clarifier.controls.intake_identity import verify_live
        root = f'/repos/{p.REPOSITORY}/'
        repo = self._request('GET', root.rstrip('/'))
        run = self._request('GET', root+'actions/runs/'+context.run_id)
        actor = self._request('GET', '/users/'+p.OWNER)
        verify_live(context, run, repo, actor)
