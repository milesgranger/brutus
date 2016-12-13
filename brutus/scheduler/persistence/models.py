import peewee as pw
from playhouse.sqlite_ext import SqliteExtDatabase
import datetime
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
db = SqliteExtDatabase(os.path.join(current_dir, 'data', 'persistence.db'))


class Job(pw.Model):
    """Job instance table"""

    class Meta:
        database = db
        db_talbe = 'job_table'

    time_recv = pw.DateTimeField(default=datetime.datetime.now)
    job_id = pw.CharField(max_length=255, primary_key=True)
    job_package = pw.BlobField()  # Stores the whole package, which contains dill.dumps(dict) of args, kwargs, func, and job_id
    status = pw.CharField(max_length=255)


class Worker(pw.Model):
    """Worker instance table"""

    class Meta:
        database = db
        db_table = 'worker_table'

    name = pw.CharField(max_length=255, default='no_name')
    current_queue_size = pw.IntegerField(default=0)
    max_queue_size = pw.IntegerField(default=50)

