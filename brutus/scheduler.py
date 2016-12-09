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
    shutdown = False

    def adder(self, x, y):
        return x, y

taskqueue = TaskQueue()


@app.route('/')
def index():
    return 'Hello there!'


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
    """
    msg = request.files['job'].read()
    print('Adding job: ', msg)
    taskqueue.jobs.append(msg)
    print('Have {} jobs'.format(len(taskqueue.jobs)))
    return json.dumps({'success': True})


@app.route('/get_job')
def get_job():
    """
    Accessed by worker processes
    :return: bytes file
    """

    # Tell worker to shutdown if signal indicates
    if taskqueue.shutdown:
        return send_file(io.BytesIO(b'shutdown'))

    # If nothing in queue, return flag for no jobs.
    if not taskqueue.jobs:
        return send_file(io.BytesIO(b'no_job'))

    # Get the first job in queue, and convert to BytesIO and send as file.
    # dill.dumps(func) does not json serialize well, if ever?
    job = taskqueue.jobs.pop()
    job = io.BytesIO(job)
    return send_file(job)


@app.route('/shutdown_workers')
def shutdown_workers():
    taskqueue.shutdown = True
    return 'Shutting down workers'




if __name__ == '__main__':
    print('Starting scheduler on port 5555')
    #app.run(debug=False, port='5555')
    http_server = WSGIServer(('', 5555), application=app)
    http_server.serve_forever()
