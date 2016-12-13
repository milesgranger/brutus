import json

import dill
from flask import Flask, request
from gevent import monkey

from brutus.scheduler.persistence.models import Job, Worker, db

monkey.patch_all()
from gevent.wsgi import WSGIServer


class Scheduler(object):

    http_server = None
    address = '127.0.0.1'
    port = 4541
    workers = []
    job_queue = []
    shutdown = False

    def scheduler_server(self):
        """
        Ran by thread, communication with Scheduler via middleman instance
        Because route methods can't use 'self'/class attributes - fix for this?
        """

        # connect server's middleman to Scheduler().middleman instance
        # So server functions can modify attributes of middleman and Scheduler().run()
        # Will react to changes/jobs added.

        app = Flask(__name__)

        @app.route('/ping')
        def ping():
            return json.dumps({'success': True})


        @app.route('/job_status')
        @app.route('/job_status/<job_id>')
        def job_status(job_id=None):
            """
            Return the status of the given job_id.
            """
            if job_id:
                job = Job.get(Job.job_id == job_id)
                return json.dumps({'success': False, 'status': job.status})

            else:
                jobs = [{'job_id': job.job_id,
                         'time_requested': str(job.time_recv),
                         'job_status': job.status
                         }
                        for job in Job.select()]
                return json.dumps(jobs)


        @app.route('/worker_status')
        def workers():
            """Return list of workers currently registered with scheduler"""
            worker_list = [{'worker_name': worker.name,
                            'worker_address': '{}:{}'.format(worker.ip_address, worker.port),
                            'current_queue_size': worker.current_queue_size,
                            'max_queue_size': worker.max_queue_size
                            }
                           for worker in Worker.select()]
            return json.dumps(worker_list)


        @app.route('/register', methods=['POST'])
        def register():
            """Workers register here"""
            data = request.get_json()
            worker_name = data.get('worker_name')
            worker_port = data.get('worker_port')
            worker = Worker.create(name=worker_name,
                                   port=worker_port,
                                   ip_address='127.0.0.1')
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

            saved_job = Job.create(job_id=_job.get('job_id'),
                                   job_package=job,
                                   status='stored on scheduler')
            print('Stored job w/ id: ', saved_job.job_id)
            return json.dumps({'success': True, 'job_id': _job.get('job_id')})


        @app.route('/shutdown')
        def shutdown_workers():
            print('Shutting down...')
            return 'shutting down cluster.'

        db.connect()
        db.drop_tables(models=[Job, Worker], safe=True)
        db.create_tables(models=[Job, Worker], safe=True)

        # Safe to use self attributes now
        print('Starting scheduler on port {}'.format(self.port))
        self.http_server = WSGIServer(('', self.port), application=app)
        self.http_server.serve_forever()


    def run(self):

        self.scheduler_server()

        # Stop the scheduler server.
        self.http_server.stop()
        db.close()
        print('Done.')


if __name__ == '__main__':

    scheduler = Scheduler()
    scheduler.run()




