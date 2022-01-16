#!/usr/bin/env python
from distutils.core import setup

setup(
    name='mkrepo',
    packages=[''],
    version='0.1.5',
    description='Maintain deb and rpm repos on s3',
    author='Konstantin Nazarov',
    author_email='mail@kn.am',
    url='https://github.com/tarantool/mkrepo',
    keywords=['rpm', 'deb'],
    classifiers=[],
    scripts=['mkrepo']
)
