
import requests
import random
import time

class JobConnection(object):
    """
    Instance with a connection specific to a job_id
    Methods to query scheduler to see status, get results, or cancel job.
    """

    def __init__(self, job_id, scheduler_address):
        self.job_id = job_id
        self.scheduler_address = scheduler_address


    def status(self):
        """
        Contacts scheduler to check status
        """
        status = requests.get('http://{}/job_status/{}'.format(self.scheduler_address, self.job_id)).json()
        print(status)




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


if __name__ == '__main__':

    @distribute
    def adder(x):
        time.sleep(random.random())
        return x + 3

    result = map(adder, [1, 2, 3, 4, 5, 6])
    results = [r for r in result]

    for i in range(5):
        print('\n\nChecking status....\n')
        for r in results:
            print(r, r.status())
        time.sleep(2)
