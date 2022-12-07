#!/usr/bin/env python

from os import path

from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
with open(path.join(this_directory, 'requirements.txt')) as f:
    install_requires = f.readlines()

setup(
    name='mkrepo',
    packages=[''],
    version='1.0.2',
    description='Maintain DEB and RPM repositories on S3',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Konstantin Nazarov',
    author_email='mail@kn.am',
    url='https://github.com/tarantool/mkrepo',
    keywords=['rpm', 'deb'],
    python_requires='>=3.6.*',
    install_requires=install_requires,
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
    scripts=['mkrepo']
)
