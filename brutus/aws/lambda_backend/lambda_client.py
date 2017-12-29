# -*- coding: utf-8 -*-

import os
import sys
import cloudpickle
import requests
import time
import datetime
from concurrent.futures import ThreadPoolExecutor
from boto3.session import Session
from brutus.base import BrutusBackend
from typing import Iterable, Optional

from brutus.aws.lambda_backend.lambda_setup.build_lambda_env import LambdaEnvBuilder


class LambdaSetup:

    def __init__(self,
                 boto3_session: Session,
                 function_name: str):
        """
        Initialize the setup / confirmation of a given lambda function
        """
        self.valid_function = False
        self.stack_name = None
        self.function_name = function_name
        self.boto3_session = boto3_session
        self.api_gateway_endpoint = ''
        self.cloudformation_template = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    'lambda_setup',
                                                    'brutus-CloudFormation.yaml')
        if not os.path.exists(self.cloudformation_template):
            raise FileNotFoundError('Can seem to locate the brutus-CloudFormation.yml file.')

    def _wait_for_stack_creation(self) -> Optional[str]:
        """
        Wait for the result of the stack creation
        """

        cf = self.boto3_session.client('cloudformation')

        timeout_dt = datetime.datetime.now() + datetime.timedelta(minutes=10)
        creation_status = None
        print('Creating CloudFormation Stack, this can take up to 10mins')
        while datetime.datetime.now() < timeout_dt:
            time.sleep(2)
            stacks = cf.describe_stacks(StackName=self.stack_name).get('Stacks')
            if stacks:
                stack = stacks.pop()
                creation_status = stack.get('StackStatus')
                sys.stdout.write('\rStack Status: {}'.format(creation_status))
                if creation_status in ['CREATE_COMPLETE', 'ROLLBACK_COMPLETE']:
                    break
        return creation_status

    def _launch_cloudformation(self, python_runtime: str) -> Optional[str]:
        """
        Launch the brutus cloud formation

        Returns
        -------
        str or None - Final creation status; one of [None, 'CREATE_COMPLETE', 'ROLLBACK_COMPLETE']
        """

        # Read the cloud formation template
        with open(self.cloudformation_template, 'r') as f:
            template = f.read()

        # Stack name derived from function_name
        self.stack_name = 'Brutus-Stack-Deployment-Function-{}'.format(self.function_name)

        # Launch template
        cf = self.boto3_session.client('cloudformation')
        cf.create_stack(
            StackName=self.stack_name,
            TemplateBody=template,
            Parameters=[
                {
                    'ParameterKey': 'FunctionNameParameter',
                    'ParameterValue': self.function_name,
                    'UsePreviousValue': True
                },
                {
                    'ParameterKey': 'PythonRuntimeParameter',
                    'ParameterValue': python_runtime,
                    'UsePreviousValue': True
                },
            ],
            TimeoutInMinutes=10,
            Capabilities=[
                'CAPABILITY_NAMED_IAM',
            ],
            OnFailure='ROLLBACK',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'Brutus-Lambda-Deployment'
                },
            ],
            EnableTerminationProtection=False
        )

        # Wait for stack to complete, timeout, or fail to complete
        stack_deployment_result = self._wait_for_stack_creation()
        return stack_deployment_result

    def _handle_cloudformation_launch_result(self, result) -> None:
        """
        Logic to handle output of self._launch_cloudformation()
        """
        if result == 'CREATE_COMPLETE':
            self.valid_function = True
            return
        else:
            raise RuntimeError('Launching of CloudFormation failed with status: {}\n'
                               'We suggest you go to the AWS console and view the events of the stack creation '
                               'and let us know what happened by filing an issue!'.format(result)
                               )

    @property
    def _api_endpoint(self):
        """Return the formatted API endpoint"""
        cf = self.boto3_session.client('cloudformation')
        api_gateway_id = cf.describe_stack_resource(StackName=self.stack_name,
                                                    LogicalResourceId='ApiGatewayRestApi'
                                                    ).get('StackResourceDetail', {}
                                                          ).get('PhysicalResourceId')
        if api_gateway_id is None:
            raise RuntimeError('Unable to determine stack resource "ApiGatewayRestApi id'
                               'We suggest you go to the AWS console and view the events of the stack creation '
                               'and let us know what happened by filing an issue!'
                               )
        endpoint_template = 'https://{api_gateway_id}.execute-api.{region_name}.amazonaws.com/BrutusDeploymentStage/brutus'.format(api_gateway_id=api_gateway_id, region_name=self.boto3_session.region_name)
        return endpoint_template

    def _validate_new_function(self):
        """
        Validate the default deployment of a function
        """
        response = requests.post(self._api_endpoint, data={'job': b'bytes'})
        if response.ok:
            if response.json().get('success'):
                print('\nSuccessfully validated function!')
                return True

        raise RuntimeError('Unable to validate function, please check the stack creation on AWS')


class Lambda(LambdaSetup, BrutusBackend):
    """
    Main interface to Lambda processing on AWS
    """

    def __init__(self, function_name: str, boto3_session: Session):
        """
        Initialize the executor
        """
        super().__init__(function_name=function_name, boto3_session=boto3_session)

    def submit(self, func: callable, *args, **kwargs):
        """
        Execute the function remotely
        """
        job = dict(
            func=func,
            args=args,
            kwargs=kwargs
        )
        job = cloudpickle.dumps(job)
        with ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(requests.post, url=self.api_gateway_endpoint, data={'job': job}, timeout=320)
        return future

    def map(self, func: callable, iter: Iterable):
        """
        Map iterable over function
        """
        raise NotImplementedError

    @classmethod
    def create(cls,
               function_name: str,
               boto3_session: Session,
               python_packages: Iterable[str],
               python_runtime: str = 'python3.6'):
        """
        Create the lambda function or confirm it exists
        """
        creator = cls(function_name=function_name,
                      boto3_session=boto3_session)

        # Launch cloud formation first to build all needed resources
        launch_result = creator._launch_cloudformation(python_runtime=python_runtime)
        creator._handle_cloudformation_launch_result(launch_result)

        # Test newly created Enpoint
        creator._validate_new_function()

        # Build lambda environment
        LambdaEnvBuilder.build(requirements=python_packages)

        # Update function with current environment

        return creator


