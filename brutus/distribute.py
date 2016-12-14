import dill
import requests
import random
import time


def wait(job_connections):
    """wait for job connections, and return actual result"""
    single_val = False

    if type(job_connections) == map:
        job_connections = [r for r in job_connections]

    elif type(job_connections) != list:
        single_val = True
        job_connections = [job_connections]

    while True:
        if all([job.status == 'complete' for job in job_connections]):
            if single_val:
                return job_connections[0].result
            return [job.result for job in job_connections]
        else:
            time.sleep(0.1)


class JobConnection(object):
    """
    Instance with a connection specific to a job_id
    Methods to query scheduler to see status, get results, or cancel job.
    """
    _result = None
    _status = None
    _exception = None

    def __init__(self, job_id, scheduler_address):
        self.job_id = job_id
        self.scheduler_address = scheduler_address


    @property
    def status(self):
        """
        Contacts scheduler to check status
        """
        # Only update if the status is not complete
        if self._status != 'complete':
            status = requests.get('http://{}/job_status/{}'.format(self.scheduler_address, self.job_id)).json()
            self._status = status.get('status')
        return self._status

    @property
    def result(self):
        if self._result is None and self.status == 'complete':
            response = requests.get('http://{}/get_result/{}'.format(self.scheduler_address, self.job_id)).json()
            self._result = response.get('result')
            self._exception = response.get('exception')
        return self._result


    @property
    def exception(self):
        self.result
        return self._exception


def distribute(func=None, address='localhost:4541'):
    """
    Wrapper which sends function and args/kwargs to given scheduler
    Makes function return JobConnection object which is the connection to the job on the scheduler.
    """
    import dill
    import requests
    import random

    class Distribute(object):
        """
        Responsible for submitting jobs to scheduler
        """
        scheduler_address = 'http://{}'.format(address)

        def __init__(self, func):
            self.func = func

        def __call__(self, *args, **kwargs):

            # Check all args are not JobConnections, wait if so
            args = [arg if 'JobConnection' not in str(type(arg)) else wait(arg) for arg in args]
            kwargs = {kw: arg if 'JobConnection' not in str(type(arg)) else wait(arg) for kw, arg in kwargs.items()}

            job = dict(job_id='id-{}'.format(random.random()).replace('.', ''),
                       func=self.func,
                       args=args,
                       kwargs=kwargs)
            job = dill.dumps(job)
            job_key = requests.post(self.scheduler_address + '/submit_job', files={'job': job}).json()

            return JobConnection(job_key.get('job_id'), scheduler_address=address)

    if callable(func):
        return Distribute(func)
    else:
        return Distribute


if __name__ == '__main__':

    @distribute
    def adder(x):
        time.sleep(random.random())
        return x

    @distribute
    def times_2(x):
        time.sleep(random.random())
        return x * 2

    results = map(adder, range(5))
    results = map(times_2, results)

    print('Results: ', results)
