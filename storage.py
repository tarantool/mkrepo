#!/usr/bin/env python

import errno
import os
import shutil
import time
import urllib
from io import BytesIO

import boto3


class Storage:

    def __init__(self):
        pass

    def read_file(self, key):
        raise NotImplementedError()

    def write_file(self, key, data):
        raise NotImplementedError()

    def download_file(self, key, destination):
        raise NotImplementedError()

    def upload_file(self, key, source):
        raise NotImplementedError()

    def delete_file(self, key):
        raise NotImplementedError()

    def mtime(self, key):
        raise NotImplementedError()

    def exists(self, key):
        raise NotImplementedError()

    def files(self, subdir=None):
        raise NotImplementedError()


def _mkdir_recursive(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class FilesystemStorage(Storage):

    def __init__(self, basedir='.'):
        self.basedir = basedir

    def read_file(self, key):
        fullpath = os.path.join(self.basedir, key)
        with open(fullpath, 'rb') as f:
            return f.read()

    def write_file(self, key, data):
        fullpath = os.path.join(self.basedir, key)

        if not os.path.exists(self.basedir):
            raise RuntimeError("Base directory doesn't exist: '%s'" %
                               self.basedir)

        dirname = os.path.dirname(fullpath)

        if not os.path.exists(dirname):
            _mkdir_recursive(dirname)

        with open(fullpath, 'wb+') as f:
            f.write(data)

    def download_file(self, key, destination):
        fullpath = os.path.join(self.basedir, key)

        shutil.copy(fullpath, destination)

    def upload_file(self, key, source):
        fullpath = os.path.join(self.basedir, key)

        if not os.path.exists(self.basedir):
            raise RuntimeError("Base directory doesn't exist: '%s'" %
                               self.basedir)

        dirname = os.path.dirname(fullpath)

        if not os.path.exists(dirname):
            _mkdir_recursive(dirname)

        shutil.copy(source, fullpath)

    def delete_file(self, key):
        fullpath = os.path.join(self.basedir, key)

        os.remove(fullpath)

    def mtime(self, key):
        fullpath = os.path.join(self.basedir, key)

        return os.path.getmtime(fullpath)

    def exists(self, key):
        fullpath = os.path.join(self.basedir, key)

        return os.path.exists(fullpath)

    def files(self, subdir=None):
        basedir = self.basedir

        if subdir is not None:
            basedir = os.path.join(basedir, subdir)

        for dirname, _, files in os.walk(basedir):
            for filename in files:
                yield os.path.relpath(os.path.join(dirname, filename), self.basedir)


class S3Storage(Storage):

    def __init__(self,
                 endpoint,
                 bucket,
                 prefix="",
                 aws_access_key_id=None,
                 aws_secret_access_key=None,
                 aws_region=None,
                 aws_public_read=False):
        self.bucket = bucket
        self.prefix = prefix
        self.public_read = aws_public_read

        self.client = boto3.client('s3', endpoint_url=endpoint,
                                   aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key,
                                   region_name=aws_region)
        self.resource = boto3.resource(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region)

    def read_file(self, key):
        fullkey = os.path.normpath(os.path.join(self.prefix, key.lstrip('/')))

        s3obj = self.resource.Object(self.bucket, fullkey)

        buf = BytesIO()
        s3obj.download_fileobj(buf)
        return buf.getvalue()

    def write_file(self, key, data):
        fullkey = os.path.normpath(os.path.join(self.prefix, key.lstrip('/')))

        s3obj = self.resource.Object(self.bucket, fullkey)

        buf = BytesIO()
        buf.write(data)
        buf.seek(0)

        # Set the arguments of the uploaded file according
        # to the "S3Storage" settings.
        extra_args = {}
        if self.public_read:
            extra_args['ACL'] = 'public-read'

        s3obj.upload_fileobj(buf, ExtraArgs=extra_args)

    def download_file(self, key, destination):
        fullkey = os.path.normpath(os.path.join(self.prefix, key.lstrip('/')))

        self.client.download_file(self.bucket, fullkey, destination)

    def upload_file(self, key, source):
        fullkey = os.path.normpath(os.path.join(self.prefix, key))

        # Set the arguments of the uploaded file according
        # to the "S3Storage" settings.
        extra_args = {}
        if self.public_read:
            extra_args['ACL'] = 'public-read'

        self.client.upload_file(source, self.bucket, fullkey,
                                ExtraArgs=extra_args)

    def delete_file(self, key):
        fullkey = os.path.normpath(os.path.join(self.prefix, key.lstrip('/')))

        self.client.delete_object(Bucket=self.bucket, Key=fullkey)

    def mtime(self, key):
        fullkey = os.path.normpath(os.path.join(self.prefix, key.lstrip('/')))

        obj = self.resource.Object(self.bucket, fullkey)
        mtime = obj.last_modified
        mtime_sec = time.mktime(mtime.timetuple())
        return mtime_sec

    def exists(self, key):
        fullkey = os.path.normpath(
            os.path.join(self.prefix, key.lstrip('/')))

        bucket = self.resource.Bucket(self.bucket)

        objs = list(bucket.objects.filter(Prefix=fullkey))

        return len(objs) > 0 and objs[0].key == fullkey

    def files(self, subdir=None):
        dirname = self.prefix

        if subdir is not None:
            dirname = os.path.join(dirname, subdir.lstrip('/'))

        dirname = os.path.normpath(dirname)

        paginator = self.client.get_paginator('list_objects')
        list_parameters = {'Bucket': self.bucket,
                           'Prefix': dirname}

        for result in paginator.paginate(**list_parameters):
            if result.get('Contents') is not None:
                for fileobj in result.get('Contents'):
                    filepath = os.path.relpath(fileobj.get('Key'), dirname)
                    yield os.path.normpath(os.path.join(subdir or '/', filepath))


class HttpStorage(Storage):

    def __init__(self, baseuri, basedir='.', timeout=10):
        """RO Http storage implementation"""
        self.basedir = basedir
        if not baseuri.startswith('http://') and \
                not baseuri.startswith('https://'):
            baseuri = "http://%s" % baseuri
        self.baseuri = baseuri
        self.timeout = timeout

    def read_file(self, key):
        fullpath = os.path.join(self.basedir, key)
        with open(fullpath, 'rb') as f:
            return f.read()

    def write_file(self, key, data):
        fullpath = os.path.join(self.basedir, key)

        if not os.path.exists(self.basedir):
            raise RuntimeError("Base directory doesn't exist: '%s'" %
                               self.basedir)

        dirname = os.path.dirname(fullpath)

        if not os.path.exists(dirname):
            _mkdir_recursive(dirname)

        with open(fullpath, 'w+b') as f:
            f.write(data)

    def download_file(self, key, destination, params=None):
        status, data = self.get(key, params)
        if status != 200:
            return False
        self.write_file(destination, data)
        return True

    def mtime(self, key):
        """All files are fresh"""
        return time.time()

    def get(self, path, params=None, deep=0):
        args = [self.baseuri, path]
        if params is not None:
            args.extend(['?', urllib.urlencode(params)])

        opener = urllib.FancyURLopener({"timeout": self.timeout})
        ret, data = opener.open(''.join(args)), None
        if ret.getcode() == 200:
            data = ret.read()

        return ret.getcode(), data

    def exists(self, key, params=None):
        status, _ = self.get(key, params)
        return status == 200
