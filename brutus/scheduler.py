from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer
from flask import Flask, request, send_file
import json
import dill
import io

app = Flask(__name__)


class TaskQueue(object):

    jobs = []
    job_status = []
    shutdown = False


taskqueue = TaskQueue()


@app.route('/')
def index():
    return 'Hello there!'


@app.route('/job_status/<job_id>')
def job_status(job_id):
    """
    Return the status of the given job_id.
    """
    job_status = next((job for job in taskqueue.job_status if job['job_id'] == job_id), None)
    if job_status:
        job_status['success'] = True
        return json.dumps(job_status)
    return json.dumps({'success': False})


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
    taskqueue.job_status.append({'job_id': _job.get('job_id'),
                                 'status': 'pending',
                                 'worker': None})
    taskqueue.jobs.append(job)
    print('Have {} jobs'.format(len(taskqueue.jobs)))
    return json.dumps({'success': True, 'job_id': _job.get('job_id')})


@app.route('/get_job')
def get_job():
    """
    Accessed by worker processes
    :return: bytes file
    """

    worker_name = request.args.get('worker_name')

    # Tell worker to shutdown if signal indicates
    if taskqueue.shutdown:
        return send_file(io.BytesIO(b'shutdown'))

    # If nothing in queue, return flag for no jobs.
    if not taskqueue.jobs:
        return send_file(io.BytesIO(b'no_job'))

    # Get the first job in queue, and convert to BytesIO and send as file.
    # dill.dumps(func) does not json serialize well, if ever?
    job = taskqueue.jobs.pop()
    _job = dill.loads(job)
    job = io.BytesIO(job)

    # Update job in job_status list that this has been sent to worker.
    _job = next((j for j in taskqueue.job_status if j['job_id'] == _job['job_id']))
    i = taskqueue.job_status.index(_job)
    _job['worker'] = worker_name
    _job['status'] = 'sent to worker'
    taskqueue.job_status[i] = _job

    # Send the bytes BytesIO formatted job to worker.
    return send_file(job)


@app.route('/shutdown_workers')
def shutdown_workers():
    taskqueue.shutdown = True
    return 'Shutting down workers'




if __name__ == '__main__':
    print('Starting scheduler on port 5555')
    #app.run(debug=False, port='5555')
    http_server = WSGIServer(('', 4541), application=app)
    http_server.serve_forever()
