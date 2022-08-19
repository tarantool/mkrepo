#!/usr/bin/env python

from os import path

from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mkrepo',
    packages=[''],
    version='0.1.9',
    description='Maintain deb and rpm repos on s3',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Konstantin Nazarov',
    author_email='mail@kn.am',
    url='https://github.com/tarantool/mkrepo',
    keywords=['rpm', 'deb'],
    classifiers=[],
    scripts=['mkrepo']
)
