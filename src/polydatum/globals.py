from functools import partial
from werkzeug.local import LocalStack, LocalProxy

def _lookup_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return getattr(top, name)


# context locals
_request_ctx_stack = LocalStack()
current_dal = LocalProxy(partial(_lookup_object, 'dal'))
request = LocalProxy(partial(_lookup_object, 'request'))