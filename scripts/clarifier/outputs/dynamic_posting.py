"""Final source/approval rechecks at a fixed comment endpoint. Serves C01."""
from clarifier.controls import policy as p
from clarifier.outputs import exact_approval


class CommentEdge:
    """Fixed dynamic target from trusted preview binding, never model-selected."""
    def __init__(self, api, owner_context, store, binding: dict, approval: dict, raw: str):
        """Bind reviewed source and bytes; raises on later verification failures."""
        self.api,self.context,self.store=api,owner_context,store
        self.binding,self.approval,self.raw=binding,approval,raw

    def read_issue(self) -> dict:
        """Return only the bound sandbox issue or raise PlatformError."""
        number=self.binding['source_issue']
        if type(number) is not int or number <= 0:
            raise p.PostingBlocked('Invalid trusted dynamic target')
        return self.api._request('GET',f'/repos/{p.REPOSITORY}/issues/{number}')

    def create_comment(self, plan) -> int:
        """Return verified bot comment ID after final rechecks; never retry uncertain POST."""
        self.api.verify_context(self.context)
        current=exact_approval.plan(self.approval,self.binding,self.raw,self.read_issue(),self.store.read().state)
        if current != plan:
            raise p.PostingBlocked('Final exact-output plan changed')
        self.require_intent(plan)
        response=self.api._request('POST',f'/repos/{p.REPOSITORY}/issues/{plan.report}/comments',{'body':plan.text})
        user=response.get('user',{}) if isinstance(response,dict) else {}
        if (not isinstance(response,dict) or type(response.get('id')) is not int or response['id'] <= 0
                or user.get('login') != 'github-actions[bot]' or user.get('type') != 'Bot'
                or response.get('body') != plan.text):
            raise p.PlatformError('Dynamic comment response uncertain; human reconciliation required')
        return response['id']

    def require_intent(self, plan) -> None:
        """Raise PostingBlocked unless exactly this report has a reserved lifetime intent."""
        rows=self.store.read().state['posts']
        found=[row for row in rows if row['report']==plan.report and row['marker']==plan.marker
               and row['status']=='reserved' and row['input_key']==plan.input_key
               and row['configuration']==plan.configuration]
        if len(found) != 1:
            raise p.PostingBlocked('Missing dynamic lifetime intent')
