from __future__ import absolute_import
import importlib
import json
import six


class Config(object):
    """
    Simple configuration object. Keys are accessible as attributes.
    Keys can not be changed once initialized.
    """
    def __init__(self, opts=None):
        if opts:
            for k, v in six.iteritems(opts):
                object.__setattr__(self, k, v)

    def __setattr__(self, key, value):
        raise KeyError('Config keys can not be changed.')

    def get(self, key, default=None):
        return getattr(self, key, default)

    def require(self, key):
        """
        Raises an exception if value for ``key`` is empty.
        """
        value = self.get(key)
        if not value:
            raise ValueError('"{}" has not been configured.'.format(key))
        return value

    def items(self):
        for k in dir(self):
            if k.isupper():
                yield (k, self.get(k))

    def __str__(self):
        return json.dumps(dict(list(self.items())), indent=2)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)


def from_module(module_name):
    """
    Load a configuration module and return a Config
    """
    d = importlib.import_module(module_name)
    config = {}
    for key in dir(d):
        if key.isupper():
            config[key] = getattr(d, key)
    return Config(config)