# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from gevent import monkey, get_hub
from gevent.hub import LoopExit
monkey.patch_all()

import signal
import gevent
import gevent.pool
from rq import Worker
try: # for rq >= 0.5.0
    from rq.job import JobStatus
except ImportError: # for rq <= 0.4.6 
    from rq.job import Status as JobStatus
from rq.timeouts import BaseDeathPenalty, JobTimeoutException
from rq.worker import StopRequested, green, blue
from rq.exceptions import DequeueTimeout
from rq.logutils import setup_loghandlers
from rq.version import VERSION


class GeventDeathPenalty(BaseDeathPenalty):
    def setup_death_penalty(self):
        exception = JobTimeoutException('Gevent Job exceeded maximum timeout value (%d seconds).' % self._timeout)
        self.gevent_timeout = gevent.Timeout(self._timeout, exception)
        self.gevent_timeout.start()

    def cancel_death_penalty(self):
        self.gevent_timeout.cancel()


class GeventWorker(Worker):
    death_penalty_class = GeventDeathPenalty

    def __init__(self, *args, **kwargs):
        pool_size = 20
        if 'pool_size' in kwargs:
            pool_size = kwargs.pop('pool_size')
        self.gevent_pool = gevent.pool.Pool(pool_size)
        super(GeventWorker, self).__init__(*args, **kwargs)

    def register_birth(self):
        super(GeventWorker, self).register_birth()
        self.connection.hset(self.key, 'pool_size', self.gevent_pool.size)

    def heartbeat(self, timeout=0, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        super(GeventWorker, self).heartbeat(timeout)
        connection.hset(self.key, 'curr_pool_len', len(self.gevent_pool))

    def _install_signal_handlers(self):
        def request_force_stop():
            self.log.warning('Cold shut down.')
            self.gevent_pool.kill()
            raise SystemExit()

        def request_stop():
            if not self._stopped:
                gevent.signal(signal.SIGINT, request_force_stop)
                gevent.signal(signal.SIGTERM, request_force_stop)

                self.log.warning('Warm shut down requested.')
                self.log.warning('Stopping after all greenlets are finished. '
                                 'Press Ctrl+C again for a cold shutdown.')

                self._stopped = True
                self.gevent_pool.join()

            raise StopRequested()

        gevent.signal(signal.SIGINT, request_stop)
        gevent.signal(signal.SIGTERM, request_stop)

    def set_current_job_id(self, job_id, pipeline=None):
        pass

    def work(self, burst=False):
        """Starts the work loop.

        Pops and performs all jobs on the current list of queues.  When all
        queues are empty, block and wait for new jobs to arrive on any of the
        queues, unless `burst` mode is enabled.

        The return value indicates whether any jobs were processed.
        """
        setup_loghandlers()
        self._install_signal_handlers()

        self.did_perform_work = False
        self.register_birth()
        self.log.info('RQ worker started, version %s' % VERSION)
        self.set_state('starting')
        try:
            while True:
                if self.stopped:
                    self.log.info('Stopping on request.')
                    break

                timeout = None if burst else max(1, self.default_worker_ttl - 60)
                try:
                    result = self.dequeue_job_and_maintain_ttl(timeout)

                    if result is None and burst:
                        try:
                            # Make sure dependented jobs are enqueued.
                            get_hub().switch()
                        except LoopExit:
                            pass
                        result = self.dequeue_job_and_maintain_ttl(timeout)

                    if result is None:
                        break
                except StopRequested:
                    break

                job, queue = result
                self.execute_job(job, queue)

        finally:
            if not self.is_horse:
                self.register_death()
        return self.did_perform_work

    def execute_job(self, job, queue):
        def job_done(child):
            self.did_perform_work = True
            self.heartbeat()
            if job.get_status() == JobStatus.FINISHED:
                queue.enqueue_dependents(job)

        child_greenlet = self.gevent_pool.spawn(self.perform_job, job)
        child_greenlet.link(job_done)

    def dequeue_job_and_maintain_ttl(self, timeout):
        if self._stopped:
            raise StopRequested()

        result = None
        while True:
            if self._stopped:
                raise StopRequested()

            self.heartbeat()

            while self.gevent_pool.full():
                gevent.sleep(0.1)
                if self._stopped:
                    raise StopRequested()

            try:
                result = self.queue_class.dequeue_any(self.queues, timeout, connection=self.connection)
                if result is not None:
                    job, queue = result
                    self.log.info('%s: %s (%s)' % (green(queue.name),
                                  blue(job.description), job.id))
                break
            except DequeueTimeout:
                pass

        self.heartbeat()
        return result


def main():
    import sys
    from rq.scripts.rqworker import main as rq_main

    if '-w' in sys.argv or '--worker-class' in sys.argv:
        print("You cannot specify worker class when using this script,"
                "use the official rqworker instead")
        sys.exit(1)

    sys.argv.extend(['-w', 'rq_gevent_worker.GeventWorker'])
    rq_main()
