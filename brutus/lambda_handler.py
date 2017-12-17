# -*- coding: utf-8 -*-

import cloudpickle


def handler(event, context):
    """
    Execute pickled function in remote Lambda environment
    """
    job = cloudpickle.loads(context['job'])
    func = job['func']
    args = job['args']
    kwargs = job['kwargs']

    try:
        cloudpickle.dumps({'result': func(*args, **kwargs),
                           'error': None})
    except Exception as exc:
        cloudpickle.dumps({'result': None,
                           'error': '{}'.format(exc)})
