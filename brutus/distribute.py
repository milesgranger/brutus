# -*- coding: utf-8 -*-

from functools import wraps
from brutus.base import BrutusBackend


def distribute(func=None, backend: BrutusBackend=None):
    """
    decorator above function to compute using a brutus backend object
    """

    class Distribute:

        def __init__(self, func: callable=None):
            self.func = func

        def __call__(self, *args, **kwargs):
            """
            Execute decorated function in remote Lambda function
            """
            return backend.dispatch(self.func, *args, **kwargs)

    if callable(func):
        return Distribute(func)
    else:
        return Distribute
