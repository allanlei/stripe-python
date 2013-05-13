import os
import sys
import multiprocessing      # Weird nosetests fix

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

from stripe import __version__

setup(
    name='stripe-requests',
    version=__version__,
    description='Stripe python bindings using requests',
    author='Allan Lei',
    author_email='allanlei@helveticode.com',
    url='https://github.com/allanlei/stripe-requests',
    license=open('LICENSE').read(),
    packages=find_packages(),
    install_requires=[
        'requests >= 1.2.0, < 1.3.0',
    ],
    tests_require=[
        'nose',
    ],
    test_suite = 'nose.collector',
    classifiers=(
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy',
    ),
)