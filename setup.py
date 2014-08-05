"""
rq-gevent-worker
================

Implement a new worker based on gevent

Install
-------

.. code-block:: bash

    $ pip install rq-gevent-worker

Usage
-----

.. code-block:: bash

    $ rqgeventworker -h

    $ export PYTHONPATH=<your project import path>:$PYTHONPATH; rqgeventworker

For more information: https://github.com/zhangliyong/rq-gevent-worker
"""
from setuptools import setup

setup(
    name='rq-gevent-worker',
    version='0.1.4',
    py_modules=['rq_gevent_worker'],
    entry_points={
        'console_scripts': [
            'rqgeventworker=rq_gevent_worker:main',
            ]
        },
    url='https://github.com/zhangliyong/rq-gevent-worker',
    license='BSD',
    author='Lyon Zhang',
    author_email='lyzhang87@gmail.com',
    description='Implement a new worker based on gevent',
    long_description=__doc__,
    install_requires=['rq >= 0.4.6', 'gevent >= 1.0'],
)
