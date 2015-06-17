==================
Amazon SQS support
==================

This is a small wrapper around SQS that provides some testing support
and and some abstraction over the boto SQS APIs.

There are 2 basic parts, a producer API and a worker API.

Note that these APIs don't let you pass AWS credentials. This means
that you must either pass credentials through ~/.boto configuration,
through environment variables, or through temporary credentials
provided via EC2 instance roles.

Producing jobs
==============

To send work to workers, instantiate a Queue:

    >>> import zc.sqs
    >>> queue = zc.sqs.Queue("myqueue")
    Connected to region us-east-1.

The SQS queue must already exist.  Creating queues is outside the
scope of these APIs.  Trying to create a Queue instance with a
nonexistent queue name will result in an exception being raised.

    >>> import mock
    >>> with mock.patch("boto.sqs.connect_to_region") as conn:
    ...     conn().get_queue.return_value = None
    ...     zc.sqs.Queue("nonexistent") # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    NonExistentQueue: nonexistent

To place data in the queue, you call it.  You can pass positional,
and/or keyword arguments.

    >>> queue(1, 2, x=3)
    [[1, 2], {'x': 3}]

In this example, we're running in test mode.  In test mode, data are
simply echoed back (unless we wire up a worker, as will be discussed
below).

Arguments must be json encodable.

Workers
=======

Workers are provided as factories that accept configuration data and
return callables that are called with queued messages. A worker
factory could be implemented with a class that has __init__ and
__call__ methods, or with a function that takes configuration data and
returns a nested function to handle messages.

Normally, workers don't return anything.  If the input is bad, the
worker should raise an exception. The exception will be logged, as
will the input data.  If the input is good, but the worker can't
perform the request, it should raise zc.sqs.TransientError to indicate
that the work should be retried later.

Containers
==========

To attach your workers to queues, you use a container, which is just a
program that polls an SQS queue and calls your worker.  There are
currently 2 containers:

sequential
   The sequential container pulls requests from an SQS queue and hands
   them to a worker, one at a time.

   This is a script entry point and accepts an argument list,
   containing the path to an ini file.  It uses "long polling" to loop
   efficiently.

test
   The test container is used for writing tests.  It supports
   integration tests of producer and worker code.  When running in
   test mode, it replaces (part of) the sequential container.

The sequential entry point takes the name of an ini file with 2 sections:

container
  The container section configures the container with options:

  worker MODULE:expr
     The worker constructor

  queue
     The name of an sqs queue to listen to.

  loggers
     A ZConfig-based logger configuration string.

worker (optional)
  Worker options, passed to the worker constructor as a dictionary.

  If not provided, an empty dictionary will be passed.

Here's a simple (pointless) example to illustrate how this is wired
up.  First, we'll define a worker factory::

    def scaled_addr(config):
        scale = float(config.get('scale', 1))

        def add(a, b, x):
            if x == 'later':
                print ("not now")
                raise zc.sqs.TransientError # Not very imaginative, I know
            print (scale * (a + b + x))

        return add

.. -> src

    >>> import zc.sqs.tests
    >>> exec(src, zc.sqs.tests.__dict__)

Now, we'll define a container configuration::

  [container]
  worker = zc.sqs.tests:scaled_addr
  queue = adder
  loggers =
     <logger>
       level INFO
       <logfile>
         path STDOUT
         format %(levelname)s %(name)s %(message)s
       </logfile>
     </logger>
     <logger>
       level INFO
       propagate false
       name zc.sqs.messages
       <logfile>
         path messages.log
         format %(message)s
       </logfile>
     </logger>

  [worker]
  scale = 2

.. -> ini

    >>> with open('ini', 'w') as f:
    ...     _ = f.write(ini)

Now, we'll run the container.

    >>> import zc.thread
    >>> @zc.thread.Thread
    ... def thread():
    ...     zc.sqs.sequential(['ini'])

.. give it some time

    >>> import time
    >>> time.sleep(.1)
    Connected to region us-east-1.

We ran the container in a thread because it runs forever and wouldn't
return.

Normally, the entry point would run forever, but since we're running
in test mode, the container just wires the worker up to the test
environment.

Now, if we create a queue (in test mode):

    >>> adder = zc.sqs.Queue("adder")
    Connected to region us-east-1.

and send it work:

    >>> adder(1, 2, 3)
    12.0
    deleted '[[1, 2, 3], {}]'

We see that the worker ran.

We also see a testing message showing that the test succeeded.

If a worker can't perform an action immediately, it indicates that the
message should be delayed by raising TransientError as shown in the
worker example above:

    >>> adder(1, 2, 'later')
    not now

In this case, since the worker raised TransientError, the message
wasn't deleted from the queue. This means that it'll be handled later
when the job times out.

If the worker rasies an exception, the exception and the message are
logged:

    >>> adder(1, 2, '') # doctest: +ELLIPSIS
    ERROR zc.sqs Handling a message
    Traceback (most recent call last):
    ...
    TypeError: unsupported operand type(s) for +: 'int' and '...'
    deleted '[[1, 2, ""], {}]'

    >>> with open("messages.log") as f:
    ...     print(f.read())
    [[1, 2, ""], {}]
    <BLANKLINE>

Silencing tests
===============

Sometimes, you don't want the testing infrastructure to output
information when sending messages.  There testing ``setUp`` method
adds an ``sqs_queues`` attribute to globals.  You can call
``be_silent`` to make it stop outputting infomation:

    >>> sqs_queues.be_silent()

After calling this, any subsequent queues will be quiet:

    >>> queue = zc.sqs.Queue("quiet")
    >>> queue(1)

You can get the queued data:

    >>> [m.get_body() for m in sqs_queues.get_queue("quiet").get_messages()]
    ['[[1], {}]']

You can switch back to being noisy:

    >>> sqs_queues.be_silent()

    >>> queue = zc.sqs.Queue("loud")
    >>> queue(1)


.. cleanup

   >>> print('Stopping'); adder.queue.queue.put('STOP'); time.sleep(.01) # doctest: +ELLIPSIS
   Stopping...

Changes
=======

1.0.0
-----

- Python 3 support.

0.3.0 (2014-10-17)
------------------

- Use long polling instead of a configurable polling interval.

0.2.1 (2013-05-15)
------------------

- Better error handling when SQS queues don't exist.

0.2.0 (2013-05-15)
------------------

- A new silent mode for test queues.

0.1.0 (2013-04-23)
------------------

Initial release.
