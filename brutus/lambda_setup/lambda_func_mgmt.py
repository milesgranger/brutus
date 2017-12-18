# -*- coding: utf-8 -*-


import boto3


class LambdaManagement:

    def check_aws_config(self):
        """
        Run checks to ensure making AWS resources are in order
        """
        raise NotImplementedError

    def create(self):
        """
        Create lambda function
        """
        raise NotImplementedError

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
