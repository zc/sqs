##############################################################################
#
# Copyright (c) 2010 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from zope.testing import setupstack, renormalizing
import logging
import manuel.capture
import manuel.doctest
import manuel.testing
import re
import unittest
import zc.sqs.testing

def cleanup_logging():
    del logging.getLogger().handlers[:]
    logging.getLogger().setLevel(logging.NOTSET)
    del logging.getLogger('zc.sqs.messages').handlers[:]
    logging.getLogger('zc.sqs.messages').setLevel(logging.NOTSET)

def setUp(test):
    setUp=zc.sqs.testing.setUp(test)
    setupstack.register(test, cleanup_logging)

def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                checker = renormalizing.OutputChecker([
                    (re.compile("u'"), "'"),
                    ]),
                ) + manuel.capture.Manuel(),
            'README.rst',
            setUp=zc.sqs.testing.setUp, tearDown=setupstack.tearDown,
            ),
        ))

