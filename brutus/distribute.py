# -*- coding: utf-8 -*-

import cloudpickle


def distribute(func=None):
    """
    Implement as decorator above any cloudpickle-able function
    """

    class Distribute:

        def __init__(self, func):
            self.func = func

        def __call__(self, *args, **kwargs):
            """
            Execute decorated function in remote Lambda function
            """
            job = dict(
                func=func,
                args=args,
                kwargs=kwargs
            )

            job = cloudpickle.dumps(job)
            # TODO: implement sending job off to lambda function and waiting for result

            return self.func(*args, **kwargs)

    if callable(func):
        return Distribute(func)
    else:
        return Distribute