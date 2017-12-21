# -*- coding: utf-8 -*-

import boto3

from typing import Union, List, AnyStr
from brutus.lambda_setup.build_lambda_env import LambdaEnvBuilder
from brutus.lambda_setup.lambda_func_mgmt import LambdaManagement


class Client(LambdaManagement, LambdaEnvBuilder):

    def __init__(self,
                 boto3_session: boto3.Session,
                 max_workers: int=1000,
                 requirements: Union[AnyStr, List[AnyStr]]=None,
                 python_runtime: str='3.6'
                 ):
        """
        Configure the remote AWS Lambda function so all following local Python functions
        using the @distribute decorator are executed according to this environment set here.

        Parameters
        ----------
        boto3_session - boto3.Session: connected boto3 session which has privileges: Lambda creation, invokation,
                                       API gateway creation
        max_workers - int: Limit of simultaneous running Lambda functions.
        requirements - str or list of string: path to pip freeze file or list of python packages to have available
                                              for the Lambda function.
        python_runtime - str: Python runtime env. Right now only 3.6 is supported.

        Returns
        -------
        None - Configures/updates/creates the Lambda function
        """
        super().__init__(session=boto3_session)

        if requirements:
            self.build(requirements=requirements)
            self.create(python_runtime='3.6')