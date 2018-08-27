#!/usr/bin/env python

import collections
import mimetypes
import gzip
import bz2
import json
import tarfile
import subprocess
import re
import os
import tempfile
import StringIO
import hashlib
import time
import datetime
import email
import sys

def file_checksum(file_name, checksum_type):
    h = hashlib.new(checksum_type)
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)

    return h.hexdigest()


def rfc_2822_now_str():
    nowdt = datetime.datetime.now()
    nowtuple = nowdt.timetuple()
    nowtimestamp = time.mktime(nowtuple)
    return email.utils.formatdate(nowtimestamp)


def gzip_string(data):
    out = StringIO.StringIO()
    with gzip.GzipFile(fileobj=out, mode="w") as fobj:
        fobj.write(data)
    return out.getvalue()


def bz2_string(data):
    buf = bytearray(data, 'utf-8')
    return bz2.compress(buf)


def gpg_sign_string(data, keyname=None, inline=False):
    cmd = "gpg --armor --digest-algo SHA256"

    if inline:
        cmd += " --clearsign"
    else:
        cmd += " --detach-sign"

    if keyname is not None:
        cmd += " --default-key='%s'" % keyname

    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    stdout = proc.communicate(input=data)[0]

    if proc.returncode != 0:
        raise RuntimeError("Failed to sign file: %s" % stdout)

    return stdout


class Package(object):

    def __init__(self, component='main', arch='amd64'):
        self.component = component
        self.arch = arch
        self.fields = collections.OrderedDict()

    def parse_deb(self, debfile):
        cmd = 'ar -p ' + debfile + ' control.tar.gz |' + \
              'tar -xzf - --to-stdout ./control'

        control = subprocess.check_output(cmd, shell=True)
        self.parse_string(control.strip())

    def parse_string(self, data):
        key = None
        value = None

        result = collections.OrderedDict()
        for line in data.strip().split('\n'):
            if line.startswith(" "):
                if value:
                    value = '%s\n%s' % (value, line)
                else:
                    value = line
            else:
                if key:
                    result[key] = value.strip()
                key, value = line.split(':', 1)
        if key:
            result[key] = value.strip()

        self.fields = result

    def dump_string(self):
        result = []
        for key in self.fields:
            result.append('%s: %s' % (key, self.fields[key]))

        return "\n".join(result)

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def __hash__(self):
        return hash((self.fields['Package'],
                     self.fields['Version'],
                     self.fields['Architecture']))

    def __eq__(self, other):
        return ((self.fields['Package'],
                 self.fields['Version'],
                 self.fields['Architecture']) ==
                (other.fields['Package'],
                 other.fields['Version'],
                 other.fields['Architecture']))

    def __ne__(self, other):
        return not(self == other)


class PackageList(object):

    def __init__(self, component='main', arch='x86_64'):
        self.component = component
        self.arch = arch
        self.packages = set()

    def parse_string(self, data):
        packages = set()
        for entry in data.strip().split('\n\n'):
            if entry.strip() == "":
                continue
            pkg = Package(component=self.component,
                          arch=self.arch)
            pkg.parse_string(entry)
            packages.add(pkg)

        self.packages = packages

    def add_deb_file(self, filename, relative_path):
        pass

    def parse_gzip_file(self, filename):
        with gzip.open(filename) as f:
            self.parse_string(f.read())

    def parse_plain_file(self, filename):
        with open(filename) as f:
            self.parse_string(f.read())

    def parse_file(self, filename):
        filetype = mimetypes.guess_type(filename)
        if filetype[1] is None:
            self.parse_plain_file(filename)
        elif filetype[1] == 'gzip':
            self.parse_gzip_file(filename)
        else:
            raise RuntimeError("Unsupported Packages type: '%s'" % filetype[1])

    def dump_string(self):
        result = []

        for pkg in self.packages:
            result.append(pkg.dump_string())

        return '\n\n'.join(result) + '\n'


class Release(object):

    def __init__(self, codename=None, origin=None, suite=None):
        self.fields = collections.OrderedDict()

        if codename:
            self['Codename'] = codename
        if origin:
            self['Origin'] = origin
        if suite:
            self['Suite'] = suite

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def parse_string(self, data):
        key = None
        value = None

        result = collections.OrderedDict()
        for line in data.strip().split('\n'):
            if line.startswith(" "):
                if value:
                    value = '%s\n%s' % (value, line)
                else:
                    value = line
            else:
                if key:
                    result[key] = value.strip()
                key, value = line.split(':', 1)
        if key:
            result[key] = value.strip()

        self.fields = result

    def parse_plain_file(self, filename):
        with open(filename) as f:
            self.parse_string(f.read().strip())

    def parse_inplace_file(self, filename):
        raise NotImplementedError()

    def parse_file(self, filename):
        if filename.lower() == 'inrelease':
            self.parse_inplace_file(filename)
        else:
            self.parse_plain_file(filename)

    def dump_string(self):
        result = []
        for key in self.fields:
            result.append('%s: %s' % (key, self.fields[key]))

        return "\n".join(result) + '\n'


def split_pkg_path(pkg_path):

    # We assume that DEB file format is the following, with optional <revision>, <dist> and <arch>
    # <package>_<version>.<revision>-<dist>_<arch>.deb

    expr = r'^(?P<package>[^_]+)_(?P<version>[0-9]+\.[0-9]+\.[0-9]+\-[0-9]+)(\.(?P<revision>[^\-]+))?([\-]?(?P<dist>[^_]+))?_(?P<arch>[^\.]+)\.deb$'
    match = re.match(expr, pkg_path)

    if not match:
        return None

    component = 'main'

    dist = match.group('dist')
    if dist is None:
        dist = 'all'
    arch = match.group('arch')
    if arch is None:
        arch = 'all'

    return (dist, component, arch)


def update_repo(storage, sign, tempdir):
    dists = set()
    package_lists = collections.defaultdict(PackageList)

    expr = r'^dists/([^/]*)/Release$'
    for file_path in storage.files('dists'):
        match = re.match(expr, file_path)

        if not match:
            continue

        dist = match.group(1)
        dists.add(dist)

        release = Release()
        release.parse_string(storage.read_file('dists/%s/Release' % dist))

        components = release['Components'].split(' ')
        architectures = release['Architectures'].split(' ')

        for component in components:
            for arch in architectures:
                subdir = 'source' if arch == 'source' else 'binary-%s' % arch

                package_list = PackageList()
                package_list.parse_string(
                    storage.read_file('dists/%s/%s/%s/Packages' %
                                      (dist, component, subdir)))

                package_lists[(dist, component, arch)] = package_list

    mtimes = {}
    for package_list in package_lists.itervalues():
        for package in package_list.packages:
            if 'FileTime' in package.fields:
                mtimes[package['Filename'].lstrip(
                    '/')] = float(package['FileTime'])

    tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)

    expr = r'^.*\.deb$'
    for file_path in storage.files('pool'):
        file_path = file_path.lstrip('/')

        match = re.match(expr, file_path)

        if not match:
            continue

        components = split_pkg_path(file_path)

        if not components:
            print("Failed to parse file name: '%s'" % file_path)
            sys.exit(1)

        dist, _, _ = components
        dists.add(dist)

        mtime = storage.mtime(file_path)
        if file_path in mtimes:
            if str(mtime) == str(mtimes[file_path]):
                print "Skipping: '%s'" % file_path
                continue
            print "Updating: '%s'" % file_path
        else:
            print "Adding: '%s'" % file_path

        storage.download_file(file_path, os.path.join(tmpdir, 'package.deb'))

        package = Package()
        local_file = os.path.join(tmpdir, 'package.deb')
        package.parse_deb(local_file)
        package['Filename'] = file_path
        package['Size'] = os.path.getsize(local_file)
        package['FileTime'] = mtime

        checksum_names = {'md5': 'MD5Sum', 'sha1': 'SHA1', 'sha256': 'SHA256'}
        for checksum_type in ['md5', 'sha1', 'sha256']:
            checksum = file_checksum(local_file, checksum_type)
            checksum_name = checksum_names[checksum_type]
            package[checksum_name] = checksum

        packages = package_lists[components].packages

        if package in packages:
            packages.remove(package)
        packages.add(package)

    checksums = collections.defaultdict(dict)
    sizes = collections.defaultdict(dict)
    components = collections.defaultdict(set)
    architectures = collections.defaultdict(set)

    for key in package_lists.iterkeys():
        dist, component, arch = key
        subdir = 'source' if arch == 'source' else 'binary-%s' % arch

        components[dist].add(component)
        architectures[dist].add(arch)

        package_list = package_lists[key]

        prefix = 'dists/%s/' % dist

        pkg_file_path = '%s/%s/Packages' % (component, subdir)
        pkg_file = package_list.dump_string()

        pkg_file_gzip_path = '%s/%s/Packages.gz' % (component, subdir)
        pkg_file_gzip = gzip_string(pkg_file)

        pkg_file_bz2_path = '%s/%s/Packages.bz2' % (component, subdir)
        pkg_file_bz2 = bz2_string(pkg_file)

        storage.write_file(prefix + pkg_file_path, pkg_file)
        storage.write_file(prefix + pkg_file_gzip_path, pkg_file_gzip)
        storage.write_file(prefix + pkg_file_bz2_path, pkg_file_bz2)

        for path in [pkg_file_path, pkg_file_gzip_path, pkg_file_bz2_path]:
            data = storage.read_file(prefix + path)
            sizes[dist][path] = len(data)

            for checksum_type in ['md5', 'sha1', 'sha256']:
                h = hashlib.new(checksum_type)
                h.update(data)

                checksums[dist][(checksum_type, path)] = h.hexdigest()

    creation_date = rfc_2822_now_str()

    for dist in dists:
        release = Release()

        release['Origin'] = 'Repo generator'
        release['Label'] = 'Repo generator'
        release['Codename'] = dist
        release['Date'] = creation_date
        release['Architectures'] = ' '.join(architectures[dist])
        release['Components'] = ' '.join(components[dist])
        release['Description'] = 'Repo generator'

        checksum_lines = collections.defaultdict(list)
        checksum_names = {'md5': 'MD5Sum', 'sha1': 'SHA1', 'sha256': 'SHA256'}
        for checksum_key, checksum_value in checksums[dist].iteritems():
            checksum_type, path = checksum_key

            file_size = sizes[dist][path]
            checksum_name = checksum_names[checksum_type]

            line = ' %s %s %s' % (checksum_value, file_size, path)
            checksum_lines[checksum_name].append(line)

        for checksum_name in checksum_lines.keys():
            release[checksum_name] = \
                '\n' + '\n'.join(checksum_lines[checksum_name])

        release_str = release.dump_string()
        storage.write_file('dists/%s/Release' % dist, release_str)

        if sign:
            release_str_signature = gpg_sign_string(release_str)
            release_str_inline = gpg_sign_string(release_str, inline=True)
            storage.write_file('dists/%s/Release.gpg' %
                               dist, release_str_signature)
            storage.write_file('dists/%s/InRelease' % dist, release_str_inline)
