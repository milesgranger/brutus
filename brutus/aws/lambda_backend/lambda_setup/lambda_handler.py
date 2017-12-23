# -*- coding: utf-8 -*-


def handler(event, context):
    """
    Execute pickled function in remote Lambda environment
    """

    print('Passed event: {}'.format(event))
    print('Passed context: {}'.format(context))

    return {'success': True}