import time
import requests
import random
import dill
from concurrent.futures import ProcessPoolExecutor



class Worker(object):
    """
    Worker class
    """

    # Holds the future objects/jobs whose .result() --> {'job_id': <job_id>, 'result': <function result>}
    futures = []

    # Job status counts; updated in update_job_status_counts
    n_running = 0
    n_complete = 0
    n_pending = 0

    # Job tracker, list of dicts containing job_id and status
    job_status = []

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
        self.port = port
        self.check_rate = check_rate
        self.max_queue_size = max_queue_size
        self.n_procs = n_procs
        self.worker_name = worker_name
        #self.process_pool = ProcessPoolExecutor(n_procs)


    @property
    def scheduler_url(self):
        return 'http://{}:{}'.format(self.address, self.port)


    def work(self):
        """
        Performs the main working loop wrapped with ProcessPoolExecutor with basic logic.
        """
        print('Worker "{}" starting with {} processes!'.format(self.worker_name, self.n_procs))

        with ProcessPoolExecutor(3) as exc:
            while True:

                # update pending, running and completed job counts
                if self.futures:
                    self.update_job_status_counts()

                # If the pending futures exceed max_queue_size, wait to allow them to finish
                if self.n_pending >= self.max_queue_size:
                    time.sleep(self.check_rate)
                    self.update_job_status_counts()
                    continue

                # Get a job package from scheduler...
                start = time.perf_counter()
                package = requests.get('{}/get_job'.format(self.scheduler_url),
                                       params={'worker_name': self.worker_name})
                print('WORKER: request time: {} - package: {}'.format(round(time.perf_counter() - start, 6), package))

                # Check for job in package
                if b'no_job' in package.content:
                    time.sleep(self.check_rate)  # Sleep since there is no work to in this package.

                # See if we're suppose to shutdown
                elif b'shutdown' in package.content:
                    print('WORKER {} shutting down...'.format(self.worker_name))
                    break

                # We have a job! Submit it to ProcessPoolExecutor and store future in pending_jobs list.
                else:
                    
                    exc.submit(self.process_job, package=package)

        return

    def process_job(self, package):
        # Load bytes into pyobj...
        package = dill.loads(package.content)
        job_id = package.get('job_id')
        func = package.get('func')
        args = package.get('args')
        kwargs = package.get('kwargs')

        result = func(*args, **kwargs)
        return result


    def update_job_status_counts(self):
        """
        Updates job status numbers and job_status list of dicts
        """
        self.job_status = []
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
            self.job_status.append(status)

        print('WORKER: Job Status --> Pending: {} - Running: {} - Completed - {}'.format(self.n_pending,
                                                                                         self.n_running,
                                                                                         self.n_complete))


    def still_working(self):
        """
        Checks scheduler to see if work status from scheduler is still running
        returning False kills the worker process, otherwise sleeps for .check_rate time.
        :return: True or False
        """
        running = requests.get('http://localhost:5555/status').json()
        return True if running.get('status', 'running') == 'running' else False


if __name__ == '__main__':
    worker = Worker(address='localhost', port='4541')
    worker.work()
