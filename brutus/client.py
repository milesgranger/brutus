import zmq
import time
import gevent
import sys
import random

from gevent import monkey
monkey.patch_all()

from zmq.eventloop import ioloop, zmqstream
ioloop.install()


def process_msg(msg):
    print('Got reply: {}'.format(msg))


def client(port_push='5556', port_pull='5557'):

    context = zmq.Context()
    socket_push = context.socket(zmq.PUSH)
    socket_push.bind("tcp://*:{}".format(port_push))
    print('Client push connected to port: {}'.format(port_push))

    for job in range(20):

        gevent.spawn(socket_push.send_string(str(job)))

        time.sleep(0.05)


    socket_pull = context.socket(zmq.PULL)
    socket_pull.connect('tcp://localhost:{}'.format(port_pull))
    stream_pull = zmqstream.ZMQStream(socket=socket_pull)
    stream_pull.on_recv(process_msg)

    print('client submitted all requests...')
    ioloop.IOLoop.instance().start()

    return

if __name__ == '__main__':
    client()

