# -*- coding: utf-8 -*-

import cloudpickle
from brutus.base import BrutusBackend

from concurrent.futures import ProcessPoolExecutor


def process(job):

    job = cloudpickle.loads(job)
    print('Executing job, remotely')
    func = job['func']
    args = job['args']
    kwargs = job['kwargs']

    return func(*args, **kwargs)


class Lambda(BrutusBackend):

    def dispatch(self, func: callable, *args, **kwargs):
        job = dict(
            func=func,
            args=args,
            kwargs=kwargs
        )

        job = cloudpickle.dumps(job)
        # TODO: implement sending job off to lambda_backend function and waiting for result

        with ProcessPoolExecutor(max_workers=1) as executor:
            result = executor.submit(process, job=job).result()

        return result
