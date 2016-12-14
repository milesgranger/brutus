import json
import time
import dill
import io
from flask import Flask, request, send_file
from brutus.scheduler.persistence.models import Job, Worker, db

app = Flask(__name__)

def update_job_statuses(status_list):
    start = time.perf_counter()
    with db.atomic():
        for status in status_list:
            query = Job.update(status=status.get('status')).where(Job.job_id == status.get('job_id'))
            query.execute()
    print('Updated all job statuses in {}s'.format(time.perf_counter() - start))



@app.route('/ping')
def ping():
    return json.dumps({'success': True})


@app.route('/job_status')
@app.route('/job_status/<job_id>')
def job_status(job_id=None):
    """
    Return the status of the given job_id, or lists all jobs and their statuses
    """
    if job_id:
        try:
            job = Job.get(Job.job_id == job_id)
            return json.dumps({'success': True, 'status': job.status})
        except:
            return json.dumps({'success': False, 'status': '{} does not exist.'.format(job_id)})

    else:
        jobs = [{'job_id': job.job_id,
                 'time_requested': str(job.time_recv),
                 'status': job.status
                 }
                for job in Job.select()]
        return json.dumps(jobs)


@app.route('/worker_status')
def workers():
    """Return list of workers currently registered with scheduler"""
    worker_list = [{'worker_name': worker.name,
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
    Worker.create(name=worker_name)
    print('Registered new worker: {}'.format(worker_name))
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
                           status='pending_on_scheduler')

    print('Stored job w/ id: ', saved_job.job_id)
    return json.dumps({'success': True,
                       'job_id': saved_job.job_id})


@app.route('/submit_job_result', methods=['POST'])
def submit_job_results():
    package = dill.loads(request.files['package'].read())
    with db.atomic():
        query = Job.update(status=package.get('status'),
                           exception=package.get('exception'),
                           result=dill.dumps(package.get('result'))).where(Job.job_id == package.get('job_id'))
        query.execute()
    return json.dumps({'success': True})


@app.route('/get_result/<job_id>')
def get_result(job_id):
    """Gets the result of a completed job"""
    with db.atomic():
        job = Job.get(Job.job_id == job_id)
        result = dill.loads(job.result)
        exception = job.exception
        i = job.delete_instance()
    print('Deleted {} job with result: {}'.format(i, result))
    return json.dumps({'result': result, 'exception': exception})


@app.route('/fetch_job', methods=['POST'])
def get_job():
    data = request.get_json()
    worker = data.get('worker_name')
    job_statuses = data.get('job_statuses')
    if job_statuses:
        update_job_statuses(job_statuses)
    print('Received job request from: {}, with {} job statuses'.format(worker, len(job_statuses)))

    # Check if any jobs are pending in scheduler db.
    jobs_exists = Job.select().where(Job.status == 'pending_on_scheduler').count()
    if jobs_exists:
        job = Job.select().where(Job.status == 'pending_on_scheduler').order_by(Job.time_recv.asc()).limit(1).get()
        job.status = 'sent_to_{}'.format(worker)
        job.save()
        return send_file(io.BytesIO(job.job_package))
    return send_file(io.BytesIO(b'no_job'))


@app.route('/shutdown')
def shutdown_workers():
    print('Shutting down...')
    return 'shutting down cluster.'