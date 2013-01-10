#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

PACKAGES = ['jira']


def get_init_val(val, packages=PACKAGES):
    pkg_init = "%s/__init__.py" % PACKAGES[0]
    value = '__%s__' % val
    fn = open(pkg_init)
    for line in fn.readlines():
        if line.startswith(value):
            return line.split('=')[1].strip().strip("'")


setup(
    name=get_init_val('title'),
    version=get_init_val('version'),
    provides=['jira'],
    description=get_init_val('description'),
    long_description=open('README.rst').read(),
    author=get_init_val('author'),
    author_email='james.rutherford@maplecroft.com',
    url=get_init_val('url'),
    keywords=['jira', 'rpc'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        ],
    license=get_init_val('license'),
    packages=PACKAGES,
    test_suite='tests',
)
