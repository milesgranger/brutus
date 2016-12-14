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



def wait(job_connections):
    """
    Wait for job connections, and return actual result
    expects job_connections (list, mapping or single instance) to be of instances of JobConnection
    """

    # TODO: Add check/warning if results have an exception result from JobConnection

    # Determine if we should return a single result, not a lot of results.
    single_val = False

    # Convert mapping to list
    if type(job_connections) == map:
        job_connections = [r for r in job_connections]

    # TODO: Add ability to check dict/kwargs with vals as JobConnection instances
    elif type(job_connections) == dict:
        pass

    # If we made it here, and it is not a list, it must be a single value
    elif type(job_connections) != list:
        single_val = True
        job_connections = [job_connections]

    # Test if these are not JobConnection objects
    if all(['JobConnection' not in str(type(job)) for job in job_connections]):
        if single_val:
            return job_connections[0]
        return job_connections

    # Wait for all JobConnection.status == 'complete' and then get their
    # result from the scheduler; returning the actual values, as if the
    # function wasn't @distribute decorated.
    while True:
        if all([job.status == 'complete' for job in job_connections]):
            if single_val:
                return job_connections[0].result
            return [job.result for job in job_connections]
        else:
            time.sleep(0.1)



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

            # Wait for all args to come back (assuming they are JobConnection instances)
            # if they aren't wait() will return the value right away.
            # TODO: Make this a future, so it doesn't get hung up on a single result/arg taking a while..:
            args = [wait(arg) for arg in args]
            kwargs = {kw: wait(arg) for kw, arg in kwargs.items()}

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


############################
###### TESTING #############
############################
if __name__ == '__main__':

    @distribute
    def adder(x):
        time.sleep(random.random())
        return x

    @distribute
    def times_2(x):
        time.sleep(random.random())
        return x * 2

    @distribute
    def add(x):
        return sum(x)

    results = map(adder, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    results = map(times_2, results)
    total = wait(add(results))

    print('Results: ', total)
