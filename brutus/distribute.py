import dill
import requests
import random
import time

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


def wait(job_connections):

    job_connections = [r for r in job_connections]

    while True:
        if all([job.status == 'complete' for job in job_connections]):
            return [job.result for job in job_connections]
        else:
            time.sleep(0.1)


if __name__ == '__main__':

    @distribute
    def adder(x):
        time.sleep(random.random())
        return x

    results = map(adder, range(50))

    print('Results: ', results)

    #print([job.status() for job in results])

    print('Waiting for results...')
    results = wait(results)
    print('finished: ', results)
