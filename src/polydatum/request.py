from polydatum.globals import request

try:
    import cPickle as pickle
except ImportError:
    import pickle

class Request(object):
    def __init__(self):
        self._memory = {}

class _memoize_wrapper(object):
    """
    Callable that is returned when you decorate something with `memoize`.
    """
    def __init__(self, func, key=None):
        self.func = func
        self.key = key
        self.bound_to = None

    def cache_key(self, *args, **kwargs):
        if self.key:
            args = self.key(*args, **kwargs)
            kwargs = {}

        return pickle.dumps((id(self.bound_to), id(self.func), args, sorted(kwargs.iteritems())))

    def __call__(self, *args, **kwargs):
        """
        Call the wrapped function, adapting if needed.
        """
        key = self.cache_key(*args, **kwargs)
        mem = request._memory
        try:
            r = mem[key]
        except KeyError:
            if self.bound_to:
                r = self.func(self.bound_to, *args, **kwargs)
            else:
                r = self.func(*args, **kwargs)

            mem[key] = r

        return r

    def __get__(self, instance, owner):
        """
        If `memoize` is decorating a method, `_memoize_wrapper` will be a descriptor.

        `__get__` will be called in this case which gives us an opportunity to bind to
        the instance.
        """
        if instance is None:
            return self
        elif not self.bound_to:
            # Bind this method to an object instance
            self.bound_to = instance

        return self

    def unmemoize(self, *args, **kwargs):
        """
        Remove object matching key from memory.
        """
        key = self.cache_key(*args, **kwargs)
        mem = request._memory
        if key in mem:
            del mem[key]

    def forget(self, obj):
        """
        Remove all instances of obj from memory.
        """
        mem = request._memory
        for k, v in mem.items():
            if v == obj:
                del mem[k]

def memoize(func=None, **kwargs):
    """
    Decorator that caches a function's return value each time it is called for the life of the Request.
    If called later with the same arguments, the cached value is returned, and not re-evaluated.
    """
    if func:
        return _memoize_wrapper(func, **kwargs)
    else:
        return _memoize_wrapper
