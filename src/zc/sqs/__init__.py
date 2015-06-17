from __future__ import print_function

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
import boto.sqs
import boto.sqs.message
import json
import logging
import sys
import time
import ZConfig

logger = logging.getLogger(__name__)
message_logger = logging.getLogger(__name__ + ".messages")

class TransientError(Exception):
    "A job failed, but should be retried."

class NonExistentQueue(Exception):
    """An SQS queue with the specified name does not exist"""

class Queue:

    def __init__(self, name, region="us-east-1"):
        self.name = name
        self.connection = boto.sqs.connect_to_region(region)
        self.queue = self.connection.get_queue(name)
        if self.queue is None:
            raise NonExistentQueue(name)

    def __call__(self, *args, **kw):
        message = boto.sqs.message.Message()
        message.set_body(json.dumps((args, kw)))
        if not self.queue.write(message):
            raise AssertionError("Failed to send message")


def sequential(args=None):
    if args is None:
        args = sys.argv[1:]

    [ini] = args

    parser = ConfigParser.RawConfigParser()
    with open(ini) as fp:
        parser.readfp(fp)

    container = dict(parser.items('container'))
    name = container.pop('queue')
    region = container.pop('region', 'us-east-1')
    worker = container.pop('worker')
    ZConfig.configureLoggers(container.pop('loggers'))

    if container:
        print("Unexpected container options", container)

    if parser.has_section('worker'):
        worker_options = dict(parser.items('worker'))
    else:
        worker_options = {}

    module, expr = worker.split(':', 1)
    module = __import__(module, {}, {}, ['*'])
    worker = eval(expr, module.__dict__)(worker_options)

    connection = boto.sqs.connect_to_region(region)
    queue = connection.get_queue(name)

    while 1:
        rs = queue.get_messages(wait_time_seconds=20)
        if len(rs):
            message = rs[0]
            data = message.get_body()
            try:
                args, kw = json.loads(data)
                worker(*args, **kw)
            except TransientError:
                continue
            except Exception:
                logger.exception("Handling a message")
                message_logger.info(data)

            queue.delete_message(message)
