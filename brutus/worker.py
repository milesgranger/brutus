import time
from flask import Flask, request, send_file
import requests
import random
import json
import dill
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import socket

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

    def __init__(self, address, port, check_rate=0.25, max_queue_size=50, n_procs=2, worker_name='brutus_jr'):
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
        self.address = address
        self.scheduler_port = port
        self.check_rate = check_rate
        self.max_queue_size = max_queue_size
        self.n_procs = n_procs
        self.worker_name = worker_name


    def get_free_port(self):
        """Get a free port"""
        s = socket.socket()
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port


    def server(self):
        """
        Starts worker server
        Used to receive jobs from server
        """
        app = Flask(__name__)

        @app.route('/receive_job', methods=['POST'])
        def receive_job():
            """Receive job from server"""
            job = request.files['job'].read()
            job = dill.loads(job)  # Loaded job
            self.job_queue.append(job)
            print('Received and added job to queue: ', job.get('job_id'))

        @app.route('/status_check', methods=['GET'])
        def status_check():
            """Respond to scheduler with current job(s) state"""
            self.update_job_status_counts()  # Calculate the latest counts before sending.
            data = {'success': True, 'worker_jobs': self.job_queue}
            return json.dumps(data)

        @app.route('/shutdown')
        def shutdown():
            self.shutdown = True

        @app.route('/ping', methods=['GET'])
        def ping():
            """Check is server is alive"""
            return json.dumps({'ping': 'pong'})

        # Start the worker server.
        self.server_port = self.get_free_port()
        print('Worker thread starting server on port: {}'.format(self.server_port))
        self.http_server = WSGIServer(('', self.server_port), application=app)
        self.http_server.serve_forever()


    def check_server(self, start=False):
        """Makes /ping request on worker server and checks for response
        Will optionally start the server"""

        if start:
            future_thread_pool = ThreadPoolExecutor(max_workers=2)
            future_thread_pool.submit(self.server)
            time.sleep(0.5)

        print('Checking "{}" server is up...'.format(self.worker_name))
        r = requests.get('http://{}:{}/ping'.format(self.address, self.server_port)).json()

        if r.get('ping') == 'pong':
            print('Worker server up! Registering with scheduler...')
            response = requests.post(self.scheduler_url + '/register', json={'worker_name': self.worker_name,
                                                                             'worker_port': self.server_port})
            if response.ok:
                print('Registered with scheduler!')
                return True
            else:
                print('Unable to register with scheduler...shutting down')

        else:
            print('Scheduler non-responsive...shutting down.')

        self.shutdown = True
        return False


    @property
    def scheduler_url(self):
        return 'http://{}:{}'.format(self.address, self.scheduler_port)


    def work(self):
        """
        Performs the main working loop wrapped with ProcessPoolExecutor with basic logic.
        """
        print('Worker "{}" starting with {} processes!'.format(self.worker_name, self.n_procs))
        if not self.check_server(start=True):
            self.http_server.stop()
            return
        print('Waiting for jobs...')

        with ProcessPoolExecutor(self.n_procs) as exc:
            while True:

                if not self.job_queue:
                    time.sleep(self.check_rate)
                    continue

                if self.shutdown:
                    break

                job = self.job_queue.pop()
                print('Processing job: ', job.get('job_id'))
                job_id = job.get('job_id')
                future = exc.submit(self.process_job, package=job)
                self.futures.append((job_id, future))

                # Update job status counts
                self.update_job_status_counts()

        print('Killing worker server...')
        self.http_server.stop()
        print('Killed.')

        return

    def process_job(self, package):
        """Loads and executes the function given the package"""

        # Load bytes into pyobj...
        package = dill.loads(package.content)
        func = package.get('func')
        args = package.get('args')
        kwargs = package.get('kwargs')

        # Run the function
        result = func(*args, **kwargs)
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
    worker = Worker(address='localhost', port='4541')
    worker.work()

