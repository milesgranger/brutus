# -*- coding: utf-8 -*-


import os
import boto3

from brutus.settings import LAMBDA_ENV


class LambdaManagement:

    def __init__(self, session: boto3.Session):
        """Handle managment of lambda function"""
        self.session = session

    def check_aws_config(self):
        """
        Run checks to ensure making AWS resources are in order
        """
        raise NotImplementedError

    def create(self, python_runtime: str, role: str):
        """
        Create lambda function
        """

        # Read the local compiled zip environment
        with open(os.path.join(LAMBDA_ENV, 'lambda_env.zip'), 'rb') as f:
            code = f.read()

        if python_runtime != '3.6':
            raise ValueError('Only Python version 3.6 is supported; you asked for: {}'.format(python_runtime))

        # Define client and create function
        # TODO: Handle if function already exists
        client = self.session.client('lambda')
        print('Creating Lambda function...')
        result = client.create_function(
            FunctionName='brutus-function',
            Runtime='python{}'.format(python_runtime),
            Role=role,
            Handler='lambda_handler.handler',
            Code={'ZipFile': code},
            Description='Lambda Function created by Brutus python package',
            Timeout=10,
            MemorySize=1000,
            Publish=True
        )
        print('done with this response: \n'.format(result))
        return True

    def delete(self):
        """
        Remove lambda function
        """
        raise NotImplementedError

    def update(self):
        """
        Update lambda function environment
        """
        raise NotImplementedError
