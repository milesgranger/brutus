import time
from flask import Flask, request, send_file
import requests
import random
import json
import dill
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import socket
from multiprocessing import Manager

from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer


class Worker(object):
    """
    Worker class
    """

    shutdown = False

    # Holds the future objects/jobs whose .result() --> {'job_id': <job_id>, 'result': <function result>}
    futures = []

    # Job status counts; updated in update_job_status_counts
    n_running = 0
    n_complete = 0
    n_pending = 0

    # Worker server
    http_server = None
    server_port = None

    # Job tracker, list of dicts containing job_id and status
    job_queue = []

    def __init__(self, scheduler_address, scheduler_port, check_rate=0.25, max_queue_size=50, n_procs=2, worker_name='brutus_jr'):
        """
        :param address:         str: Scheduler http/tcp address
        :param port:            str: Scheduler port
        :param check_rate:      float: time to sleep between contacting scheduler for more work, or waiting for
                                       number of pending jobs to fall below max_queue_size before rechecking work status
        :param max_queue_size:  int: Maximum number of pending jobs. If pending jobs exceeds this, worker stops asking
                                     for more work, and waits for pending work queue to fall below this number.
        :param n_procs:         int: Number of processes used by ProcessPoolExecutor
        :param worker_name:     str: Name of this worker, each worker should be unique, but doesn't have to be.
                                     Allows tracking of who has what jobs; and scheduler to note when a worker is
                                     suspected to be dead.
        :return:
        """
        self.scheduler_address = scheduler_address
        self.scheduler_port = scheduler_port
        self.check_rate = check_rate
        self.max_queue_size = max_queue_size
        self.n_procs = n_procs
        self.worker_name = worker_name


    @property
    def scheduler_url(self):
        return 'http://{}:{}'.format(self.scheduler_address, self.scheduler_port)


    def work(self):
        """
        Performs the main working loop wrapped with ProcessPoolExecutor with basic logic.
        """
        print('Worker "{}" starting with {} processes!\nRegistering w/ scheduler.'
              .format(self.worker_name, self.n_procs))
        requests.post(self.scheduler_url + '/register', json={'worker_name': self.worker_name})
        print('Waiting for jobs...')

        with ProcessPoolExecutor(self.n_procs) as exc:
            while True:

                # Update job status counts
                self.update_job_status_counts()

                if self.n_pending >= self.max_queue_size:
                    time.sleep(self.check_rate)
                    continue

                # Try to get a job from scheduler, but post current status as well
                response = requests.post(self.scheduler_url + '/get_job', json={'worker_name': self.worker_name})

                if response.content == b'no_job':
                    time.sleep(self.check_rate)
                elif response.content == b'shutdown':
                    break
                else:
                    _job = dill.loads(response.content)
                    print('Processing job: {}'.format(_job.get('job_id')))
                    future = exc.submit(self.process_job, package=response.content)
                    self.futures.append((_job.get('job_id'), future))
                    #self.process_job(package=response.content)

        print('Killing worker server...')
        self.http_server.stop()
        print('Killed.')

        return

    def process_job(self, package):
        """Loads and executes the function given the package"""

        # Load bytes into pyobj...
        package = dill.loads(package)
        func = package.get('func')
        args = package.get('args')
        kwargs = package.get('kwargs')

        # Run the function
        print('Executing function')
        result = func(*args, **kwargs)
        print('result of function:  ', result)
        return result


    def update_job_status_counts(self):
        """
        Updates job status numbers and job_status list of dicts
        """
        self.job_queue = []
        self.n_pending, self.n_running, self.n_complete = 0, 0, 0
        for job_id, future in self.futures:
            if future.done():
                status = {'status': 'complete_on_worker'}
                self.n_complete += 1
            elif future.running():
                status = {'status': 'running_on_worker'}
                self.n_running += 1
            else:
                status = {'status': 'pending_on_worker'}
                self.n_pending += 1

            status.update({'job_id': job_id})
            self.job_queue.append(status)

        print('WORKER: Job Status --> Pending: {} - Running: {} - Completed - {}'.format(self.n_pending,
                                                                                         self.n_running,
                                                                                         self.n_complete))



if __name__ == '__main__':
    worker = Worker(scheduler_address='localhost', scheduler_port='4541')
    worker.work()

