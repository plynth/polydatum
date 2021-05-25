from __future__ import absolute_import
from inspect import isgeneratorfunction


def is_generator(obj):
    return callable(obj) and (
        isgeneratorfunction(obj) or
        isgeneratorfunction(getattr(obj, '__call__'))
    )