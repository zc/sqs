
from zope.testing import setupstack

import ConfigParser
import json
import mock
import pprint
import Queue
import time
import zc.sqs

max_message_size = 1 << 16

class Queues:

    def __init__(self):
        self.queues = {}

    def connect_to_region(self, region):
        print ("Connected to region %s." % region)
        return self

    def get_queue(self, name):
        try:
            return self.queues[name]
        except KeyError:
            self.queues[name] = TestQueue(name)

        return self.queues[name]

class TestQueue:

    def __init__(self, name):
        self.name = name


    def write(self, message):
        try:
            self.queue.put(message)
            time.sleep(.01)
        except AttributeError:
            pprint.pprint(json.loads(message.get_body()))

        return True

    def get_messages(self):
        try:
            queue = self.queue
        except AttributeError:
            queue = self.queue = Queue.Queue()

        mess = self.queue.get()
        if mess == 'STOP':
            raise ValueError
        return [mess]

    def delete_message(self, message):
        print "deleted", pprint.pformat(message.get_body())

def setUp(test):
    setupstack.setUpDirectory(test)
    queues = Queues()

    setupstack.context_manager(
        test, mock.patch("boto.sqs.connect_to_region",
                         side_effect=queues.connect_to_region))

