
import boto.sqs
import boto.sqs.message
import json

class Queue:

    def __init__(self, name, region="us-east-1"):
        self.name = name
        self.connection = boto.sqs.connect_to_region(region)
        self.queue = connection.get_queue(name)

    def __call__(self, *args, **kw):
        message = boto.sqs.message.Message()
        message.set_body(json.dumps((args, kw)))
        if not self.queue.write(message):
            raise AssertionError("Failed to send message")

