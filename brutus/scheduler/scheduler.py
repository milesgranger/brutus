import socket

from brutus.scheduler.server import app
from brutus.scheduler.persistence.models import Job, Worker, db

from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer


class Scheduler(object):

    http_server = None
    address = '127.0.0.1'
    port = 4541
    workers = []
    job_queue = []
    shutdown = False

    def get_free_port(self):
        """Get a free port"""
        s = socket.socket()
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port


    def scheduler_server(self):
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




