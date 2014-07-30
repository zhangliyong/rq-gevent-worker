rq-gevent-worker
================

Implement a new worker based on gevent

##Install

    $ pip install rq-gevent-worker

##Usage

    $ export PYTHONPATH=<your project import path>:$PYTHONPATH; rqgeventworker

##Under The Hood
TODO

##Note

###Crash
Official `Worker` use `os.fork()` to spawn a child process to execute a job,
so if the job cause the process crash, the worker process is still alive.
When using gevent, we use the same process to execute job, the job may
cause the whole worker process crash.

###Why not `rqworker -w <geventworker>`
Because we need gevent monkey patch at the start of the process, rqworker import
many modules before importing geventworker, so it will cause geventworker not work normally.

##Declaration

Most of the code is from [lechup](https://gist.github.com/lechup/d886e89490b2f6c737d7) and [jhorman](https://gist.github.com/jhorman/e16ed695845fca683057), 
