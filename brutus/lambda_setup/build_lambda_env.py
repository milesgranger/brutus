# -*- coding: utf-8 -*-

import os
import shutil
import docker

from brutus.settings import LAMBDA_ENV


class LambdaEnvBuilder:
    """
    Build python packages on the Amazon Linux AMI using docker
    output built files to ../lambda_env and final packaged env to ../lambda_env/lambda_env.zip

    Example
    >>> LambdaEnvBuilder.build(packages_or_file=['pandas', 'numpy'])
    """

    @staticmethod
    def get_docker_client():
        return docker.from_env()

    @staticmethod
    def clear_lambda_target_dir(client):
        """
        Either make a directory at LAMBDA_ENV or clear it.
        """
        if not os.path.exists(LAMBDA_ENV):
            os.mkdir(LAMBDA_ENV)
        else:
            print('Clearning lambda_env target dir.')
            container = client.containers.run('milesg/brutus', 'rm -rf /lambda_env',
                                              detach=True,
                                              auto_remove=True,
                                              remove=True,
                                              read_only=False,
                                              volumes={LAMBDA_ENV: {'bind': '/lambda_env', 'mode': 'rw'}}
                                              )
            for line in container.logs(stream=True):
                pass
                #print(line.strip())
            print('done.')

    @staticmethod
    def make_or_move_requirements(packages_or_file):
        """
        Ensure there is a file of python package requirements in the LAMBDA_ENV directory
        to ensure we can use it to install packages from
        """
        # TODO: Add ability to install files from current environment
        if isinstance(packages_or_file, list):
            with open(os.path.join(LAMBDA_ENV, 'requirements.txt'), 'w') as f:
                for package in packages_or_file:
                    f.write('{}\n'.format(package))
        elif isinstance(packages_or_file, str) and os.path.exists(packages_or_file):
            shutil.copyfile(packages_or_file, os.path.join(LAMBDA_ENV, 'requirements.txt'))

        else:
            raise ValueError('Do not know how to make requirements.txt out of type: {} with values: {}\n' \
                             'Should be either a list of packages or a file path to file created from "pip freeze"'
                             .format(type(packages_or_file), packages_or_file)
                             )

    @classmethod
    def build(cls, packages_or_file):

        client = cls.get_docker_client()

        cls.clear_lambda_target_dir(client)

        # Copy or create a requirements.txt into the lambda env dir
        cls.make_or_move_requirements(packages_or_file)

        # Copy the lambda handler file into the lambda env dir
        shutil.copyfile(os.path.join(os.path.dirname(__file__), '..', 'lambda_handler.py'),
                        os.path.join(LAMBDA_ENV, 'lambda_handler.py')
                        )

        container = client.containers.run('milesg/brutus', 'pip install -r /lambda_env/requirements.txt -t /lambda_env',
                                          detach=True,
                                          auto_remove=True,
                                          read_only=False,
                                          remove=True,
                                          volumes={LAMBDA_ENV: {'bind': '/lambda_env', 'mode': 'rw'}}
                                          )

        print('Building environment on Amazon Linux container...')
        for line in container.logs(stream=True):
            print(line.strip().decode('utf-8'))

        print('Creating zip...')
        shutil.make_archive(base_name='lambda_env', format='zip', root_dir=LAMBDA_ENV, verbose=1)
        shutil.move('lambda_env.zip', os.path.join(LAMBDA_ENV, 'lambda_env.zip'))
        print('done')


if __name__ == '__main__':
    LambdaEnvBuilder.build(packages_or_file=['cloudpickle', 'numpy'])
