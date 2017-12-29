# -*- coding: utf-8 -*-

import json
import cloudpickle


def handler(event, context):
    """
    Execute pickled function in remote Lambda environment using all globals from source environment
    """

    print('Passed event: {}'.format(event))
    print('Passed context: {}'.format(context))

    job = None

    return {
        'statusCode': 200,
        'body': str(b'bytes response'),
        'isBase64Encoded': False,
        'headers': {'Content-Type': 'application/octet-stream'}
    }
