#!/usr/bin/python

import sys
from setuptools import setup, find_packages
from pip.req import parse_requirements

data_files = [
    ('/etc/sd-agent', ['config.cfg'])
]

if sys.platform != 'darwin':
    data_files.append(('/etc/init.d', ['extra/init/sd-agent']))

setup(
    name='sd-agent',
    version='1.13.4',
    description='Monitoring agent for Server Density (Linux, FreeBSD and OS X)',
    author='Server Density',
    author_email='hello@serverdensity.com',
    url='http://www.serverdensity.com',
    packages=find_packages(),
    scripts=['bin/sd-agent'],
    data_files=data_files,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Simplified BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: BSD :: FreeBSD",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Logging",
        "Topic :: System :: Monitoring",
    ]
)
