from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer
from flask import Flask, request, send_file
import json
import dill
import io
import time




class Scheduler(object):

    http_server = None
    address = '127.0.0.1'
    port = 4541

    class MiddleMan(object):
        """
        Used to communicate between Scheduler loop and scheduler server running in another
        thread. Only attributes which need to be shared between Scheduler and the server need to be in here.
        ie. app.route() functions found in scheduler_server()
        """
        workers = []
        job_queue = []
        shutdown = False


    middleman = MiddleMan()

    def scheduler_server(self):
        """
        Ran by thread, communication with Scheduler via middleman instance
        Because route methods can't use 'self'/class attributes - fix for this?
        """

        # connect server's middleman to Scheduler().middleman instance
        # So server functions can modify attributes of middleman and Scheduler().run()
        # Will react to changes/jobs added.
        self.middleman = middleman = self.middleman

        app = Flask(__name__)

        @app.route('/ping')
        def ping():
            return json.dumps({'success': True})


        @app.route('/job_status/<job_id>')
        def job_status(job_id):
            """
            Return the status of the given job_id.
            """
            return json.dumps({'success': False})


        @app.route('/workers')
        def workers():
            return json.dumps({'workers': middleman.workers})


        @app.route('/register', methods=['POST'])
        def register():
            """Workers register here"""
            data = request.get_json()
            worker_name = data.get('worker_name')
            worker_port = data.get('worker_port')
            middleman.workers.append({'worker_name': worker_name,
                                      'worker_port': worker_port,
                                      'worker_ip': '127.0.0.1',
                                      'jobs': []})
            print('Registered new worker: {} on port: {}'.format(worker_name, worker_port))
            return json.dumps({'success': True})


        @app.route('/submit_job', methods=['POST'])
        def submit_job():
            """
            Accept jobs, and stores in scheduler queue.
            Each job is expected to be constructed and sent to scheduler similar to the following:

            >> job = dict(job_id='test-123',
                          func=my_func,
                          args=(2, 3),
                          kwargs={ kwarg1: 'val1' })
            >> job = dill.dumps(job)
            >> requests.post('http://<scheduler_address_>:<scheduler_port>/submit_job', files={ 'job' : job })
            {'success': True, 'job_id': <job_id>'}
            """
            job = request.files['job'].read()
            _job = dill.loads(job)  # Loaded job

            print('Adding job to queue - job_id: ', _job.get('job_id'))
            middleman.job_queue.append({'job_id': _job.get('job_id'),
                                        'status': 'pending_on_scheduler',
                                        'worker': None,
                                        'job': job})
            print('Have {} jobs'.format(len(middleman.job_queue)))
            return json.dumps({'success': True, 'job_id': _job.get('job_id')})


        @app.route('/shutdown')
        def shutdown_workers():
            print('Shutting down...')
            middleman.shutdown = True
            return 'shutting down cluster.'

        # Safe to use self attributes now
        print('Starting scheduler on port {}'.format(self.port))
        self.http_server = WSGIServer(('', self.port), application=app)
        self.http_server.serve_forever()


    def start_scheduler_server(self):
        exc = ProcessPoolExecutor(2)
        self.server_process = exc.submit(self.scheduler_server)
        return True


    def run(self):

        print('Starting scheduler server...')
        self.start_scheduler_server()
        print('Server started!')

        while True:

            # If no workers, or anything in job queue, just wait.
            if not (self.middleman.workers or self.middleman.job_queue):
                time.sleep(1)

            if self.middleman.shutdown:
                print('Exiting Scheduler loop')
                break

            time.sleep(0.1)

        # Stop the scheduler server.
        self.http_server.stop()
        print('Done.')


if __name__ == '__main__':

    scheduler = Scheduler()
    scheduler.run()




