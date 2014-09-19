# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os

import chronic
from rq import Queue

from rq_gevent_worker import GeventWorker
from tests import RQTestCase
from tests.fixtures import create_file_after_timeout, say_hello


class TestGeventWorker(RQTestCase):
    def test_register_worker(self):
        """ensure pool size is registered."""
        w = GeventWorker(Queue(), pool_size=10)
        w.register_birth()
        self.assertEqual(self.testconn.hget(w.key, 'pool_size'), '10')

    def test_gevent_num(self):
        """ensure gevent num is registered."""
        q = Queue()
        w = GeventWorker(q)
        w.heartbeat()
        self.assertEqual(self.testconn.hget(w.key, 'curr_pool_len'), '0')

        job = q.enqueue(say_hello)
        w.execute_job(job, q)
        w.heartbeat()
        self.assertEqual(self.testconn.hget(w.key, 'curr_pool_len'), '1')
        w.register_death()

    def create_queue_with_two_jobs(self):
        sentinel_file1 = '/tmp/.rq_sentinel1'
        sentinel_file2 = '/tmp/.rq_sentinel2'

        q = Queue()

        # Put it on the queue with a timeout value
        q.enqueue(
            create_file_after_timeout,
            args=(sentinel_file1, 1))

        q.enqueue(
            create_file_after_timeout,
            args=(sentinel_file2, 1))

        try:
            os.unlink(sentinel_file1)
            os.unlink(sentinel_file2)
        except OSError as e:
            if e.errno == 2:
                pass
        return q

    def test_sequence(self):
        w = GeventWorker(self.create_queue_with_two_jobs(), pool_size=1)
        with chronic.Timer('default'):
            w.work(burst=True)

        self.assertGreater(chronic.timings['default']['total_elapsed'], 2.0)

    def test_concurrent(self):
        w = GeventWorker(self.create_queue_with_two_jobs(), pool_size=2)
        with chronic.Timer('default'):
            w.work(burst=True)

        self.assertLess(chronic.timings['default']['total_elapsed'], 1.5)
