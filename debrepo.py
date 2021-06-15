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
from io import BytesIO
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


def gzip_bytes(data):
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb") as fobj:
        fobj.write(data)
    return out.getvalue()


def bz2_bytes(data):
    return bz2.compress(data)


def gpg_sign_string(data, keyname=None, inline=False):
    """Signing data according to the specified options.

    Keyword arguments:
    data - data for sign (Unicode string).
    keyname - name of the gpg key that will be used to sign the
              data (string, default: None).
    inline - option specifies whether to use a cleartext
             signature (bool, default: False).

    Return signed data in binary format.
    """

    cmd = "gpg --armor --digest-algo SHA256"

    if inline:
        cmd += " --clearsign"
    else:
        cmd += " --detach-sign"

    if keyname is not None:
        cmd += " --local-user '%s'" % keyname

    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    stdout = proc.communicate(input=data.encode('utf-8'))[0]

    if proc.returncode != 0:
        raise RuntimeError("Failed to sign file: %s" % stdout)

    return stdout


class Package(object):

    def __init__(self, component='main', arch='amd64'):
        self.component = component
        self.arch = arch
        self.fields = collections.OrderedDict()

    def parse_deb(self, debfile):
        if subprocess.call('ar t ' + debfile + ' | grep control.tar.gz', shell=True) == 0:
            cmd = 'ar -p ' + debfile + ' control.tar.gz |' + \
                  'tar -xzf - --to-stdout ./control'
        else:
            cmd = 'ar -p ' + debfile + ' control.tar.xz |' + \
                  'tar -xJf - --to-stdout ./control'

        control = subprocess.check_output(cmd, shell=True)
        self.parse_string(control.decode('utf-8').strip())

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


class Source(object):
    """"Source" describes the unit of the "Source" index."""

    def __init__(self):
        self.fields = collections.OrderedDict()

    def parse_dsc(self, dscfile, location, mtime):
        """Parse the dsc control file.

        Keyword arguments:
        dscfile - path to dsc file (string).
        location - location of the dsc file on the target host (string).
        mtime - modification time (float).
        """
        with open(dscfile) as file:
            self.parse_string(file.read())

        # Add "Directory" field (https://wiki.debian.org/DebianRepository/Format#Directory).
        self.fields['Directory'] = os.path.dirname(location)

        # Add information about the dsc file to checksums.
        size = os.path.getsize(dscfile)
        file_information = '%i %s' % (size, os.path.basename(location))

        file_fields = {
            'Files': 'md5',
            'Checksums-Sha1': 'sha1',
            'Checksums-Sha256': 'sha256'
        }

        for field, checksum_type in file_fields.items():
            if self.fields[field]:
                self.fields[field] = '%s\n %s %s' % (
                    self.fields[field],
                    file_checksum(dscfile, checksum_type),
                    file_information)

    def parse_string(self, data):
        """Parse control file.

        Keyword arguments:
        data - control file (string).
        """
        key = None
        value = None

        result = collections.OrderedDict()
        for line in data.strip().split('\n'):
            if line.startswith(' '):
                # Multiline field case
                # (https://www.debian.org/doc/debian-policy/ch-controlfields.html#syntax-of-control-files).
                value = '%s\n%s' % (value, line)
            else:
                if key:
                    # Save the key: value pair, read in the previous iteration.
                    result[key] = value.strip(' ')
                key, value = line.split(':', 1)
                # We need to replace "Source" key to the "Package" according to
                # https://wiki.debian.org/DebianRepository/Format#A.22Sources.22_Indices
                if key == 'Source':
                    key = 'Package'

        if key:
            # Save the result of the last iteration.
            result[key] = value.strip(' ')

        self.fields = result

    def dump_string(self):
        """Return the content of the index unit in text format."""
        result = []
        for key, value in self.fields.items():
            pattern = '%s: %s'
            if str(value).startswith('\n'):
                pattern = '%s:%s'
            result.append(pattern % (key, self.fields[key]))

        return "\n".join(result)

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def __hash__(self):
        return hash((self.fields['Package'],
                     self.fields['Version']))

    def __eq__(self, other):
        return ((self.fields['Package'],
                 self.fields['Version']) ==
                (other.fields['Package'],
                 other.fields['Version']))

    def __ne__(self, other):
        return not(self == other)


class SourceList(object):
    """"SourceList" describes the "Source" index."""

    def __init__(self, component='main'):
        self.component = component
        self.sources = set()

    def parse_string(self, data):
        """Parse "Sources" file (source index).

        Keyword arguments:
        data - "Source" index (string).
        """
        sources = set()
        for entry in data.strip().split('\n\n'):
            if entry.strip() == "":
                continue
            src = Source()
            src.parse_string(entry)
            sources.add(src)

        self.sources = sources

    def parse_gzip_file(self, filename):
        """Parse compressed "Sources" file ("Source" index).

        Keyword arguments:
        filename - path (string).
        """
        with gzip.open(filename) as f:
            self.parse_string(f.read())

    def parse_plain_file(self, filename):
        """Parse "Sources" file ("Source" index).

        Keyword arguments:
        filename - path (string).
        """
        with open(filename) as f:
            self.parse_string(f.read())

    def parse_file(self, filename):
        """Parse compressed or plain "Sources" file ("Source" index).

        Keyword arguments:
        filename - path (string).
        """
        filetype = mimetypes.guess_type(filename)
        if filetype[1] is None:
            self.parse_plain_file(filename)
        elif filetype[1] == 'gzip':
            self.parse_gzip_file(filename)
        else:
            raise RuntimeError("Unsupported Sources type: '%s'" % filetype[1])

    def dump_string(self):
        """Return the content of the index in text format."""
        result = []

        for src in self.sources:
            result.append(src.dump_string())

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


class RepoInfo(object):
    """RepoInfo accumulate information about the processed
    repository to simplify work.
    """

    def __init__(self, storage):
        # storage - storage with repositories (Storage object).
        self.storage = storage
        # package_lists - list of the package lists (dictionary
        #                 (dist, component, arch) to PackageList object).
        self.package_lists = collections.defaultdict(PackageList)
        # source_lists - list of the source lists (dictionary
        #                (dist, component) to SourceList object).
        self.source_lists = collections.defaultdict(SourceList)
        # dists - list of distributions (set of strings).
        self.dists = set()
        # checksums - files checksums (dictionary).
        self.checksums = collections.defaultdict(dict)
        # sizes - files sizes (dictionary)
        self.sizes = collections.defaultdict(dict)
        # components - distributions components (dictionary).
        self.components = collections.defaultdict(set)
        # architectures - architectures supported in distributions (dictionary).
        self.architectures = collections.defaultdict(set)


def split_pkg_path(pkg_path):

    # We assume that DEB file format is the following, with optional <revision>, <dist> and <arch>
    # <package>_<version>.<revision>-<dist>_<arch>.deb

    expr = r'^(?P<package>[^_]+)_(?P<version>[0-9]+(\.[0-9]+){2,3}(\.g[a-f0-9]+)?\-[0-9])(\.(?P<revision>[^\-]+))?([\-]?(?P<dist>[^_]+))?_(?P<arch>[^\.]+)\.deb$'
    match_package = re.match(expr, pkg_path)

    # The distribution information may be missing in the file name,
    # but present in the path.
    match_path = re.match('^pool/(?P<dist>[^/]+)/main', pkg_path)

    if not match_package:
        return None

    component = 'main'

    dist = match_package.group('dist') or match_path.group('dist')
    if dist is None:
        dist = 'all'
    arch = match_package.group('arch')
    if arch is None:
        arch = 'all'

    return (dist, component, arch)


def save_malformed_list(storage, dist, malformed_list):
    """Save the list of malformed packages to the storage.

    Keyword arguments:
    storage - storage with repositories (Storage object).
    dist - distribution version (string)
    malformed_list - list of malformed packages (list of strings).
    """
    file = 'dists/%s/malformed_list.txt' % dist
    if malformed_list:
        print('Save malformed list...')
        storage.write_file(file, '\n'.join(malformed_list).encode('utf-8'))
    elif storage.exists(file):
        # The list existed before, but is not up-to-date now.
        print('Delete malformed list...')
        storage.delete_file(file)


def split_src_path(src_path):
    """Return the distribution and component relevant src_path.

    Keyword arguments:
    src_path - path to control file (string).
    """
    component = 'main'

    match_path = re.match('^pool/(?P<dist>[^/]+)/main', src_path)

    if not match_path:
        return None

    dist = match_path.group('dist')
    if dist is None:
        dist = 'all'

    return (dist, component)


def process_packages_file(repo_info, path, dist, component, arch):
    """Process the "Packages" file.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    path - path to the "Packages" file.
    dist - distribution (string).
    component - repository area (string).
    arch - architecture (string).
    """
    package_list = PackageList()
    package_list.parse_string(repo_info.storage.read_file(path).decode('utf-8'))

    repo_info.package_lists[(dist, component, arch)] = package_list


def process_sources_file(repo_info, path, dist, component):
    """Process the "Sources" file.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    path - path to the "Sources" file.
    dist - distribution (string).
    component - repository area (string).
    """
    source_list = SourceList()
    source_list.parse_string(repo_info.storage.read_file(path).decode('utf-8'))

    repo_info.source_lists[(dist, component)] = source_list


def read_release_and_indices(repo_info):
    """Read the "Release" files from "dists/$DIST/Release"
    and "Packages" files.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    """
    expr = r'^dists/([^/]*)/Release$'
    for file_path in repo_info.storage.files('dists'):
        match = re.match(expr, file_path)

        if not match:
            continue

        dist = match.group(1)
        repo_info.dists.add(dist)

        release = Release()
        release.parse_string(repo_info.storage.read_file('dists/%s/Release' %
                                                         dist).decode('utf-8'))

        components = release['Components'].split(' ')
        architectures = release['Architectures'].split(' ')

        for component in components:
            # In fact, we support only "main".
            for arch in architectures:
                # Process the "Packages" indices.
                if arch == 'source':
                    # The "source" case is processed below as special.
                    # We have few reasons for this:
                    # - several differences in processing.
                    # - often "source" architecture is not specified,
                    #   but "Source" index exists.
                    continue

                path = 'dists/%s/%s/binary-%s/Packages' % (dist, component, arch)
                process_packages_file(repo_info, path, dist, component, arch)

            # Process the "Source" index.
            path = 'dists/%s/%s/source/Sources' % (dist, component)
            if repo_info.storage.exists(path):
                process_sources_file(repo_info, path, dist, component)


def calculate_package_checksums(package, file_path):
    """Calculate the checksums of the file and add it to the Package object.

    Keyword arguments:
    package - processed package (Package object).
    file - path to the file (string).
    """
    checksum_names = {'md5': 'MD5Sum', 'sha1': 'SHA1', 'sha256': 'SHA256'}
    for checksum_type in ['md5', 'sha1', 'sha256']:
        checksum = file_checksum(file_path, checksum_type)
        checksum_name = checksum_names[checksum_type]
        package[checksum_name] = checksum


def get_packages_mtimes(package_lists):
    """Read the mtimes of files from the packages lists.

    Keyword arguments:
    package_lists - list of the package lists (dictionary
                    (dist, component, arch) to PackageList object).

    Return the dictionary "filename to mtime".
    """
    mtimes = {}
    for package_list in package_lists.values():
        for package in package_list.packages:
            if 'FileTime' in package.fields:
                mtimes[package['Filename'].lstrip(
                    '/')] = float(package['FileTime'])

    return mtimes


def get_sources_mtimes(source_lists):
    """Read the mtimes of files from the sources lists.

    Keyword arguments:
    source_lists - list of the source lists (dictionary
                   (dist, component, arch) to SourceList object).

    Return the dictionary "filename to mtime".
    """
    mtimes = {}
    for source_lists in source_lists.values():
        for source in source_lists.sources:
            if 'FileTime' in source.fields and 'Filename' in source.fields:
                mtimes[source['Filename'].lstrip(
                    '/')] = float(source['FileTime'])

    return mtimes


def process_packages(repo_info, tempdir, force):
    """Add information about changed files to the package.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    tempdir - path to the directory for storing temporary files (string).
    force - skip a malformed package without raising an error (bool).
    """
    mtimes = get_packages_mtimes(repo_info.package_lists)
    tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)

    # Dictionary (dist to malformed packages list).
    # Malformed list - list of packages that can't be added to the index
    # (some problems encountered during processing).
    malformed_lists = {}

    expr = r'^.*\.deb$'
    for file_path in repo_info.storage.files('pool'):
        file_path = file_path.lstrip('/')

        match = re.match(expr, file_path)

        if not match:
            continue

        components = split_pkg_path(file_path)

        if not components:
            print("Failed to parse file name: '%s'" % file_path)
            sys.exit(1)

        dist, _, _ = components
        repo_info.dists.add(dist)

        mtime = repo_info.storage.mtime(file_path)
        if file_path in mtimes:
            if str(mtime) == str(mtimes[file_path]):
                print("Skipping: '%s'" % file_path)
                continue
            print("Updating: '%s'" % file_path)
        else:
            print("Adding: '%s'" % file_path)

        repo_info.storage.download_file(file_path, os.path.join(tmpdir, 'package.deb'))

        package = Package()
        local_file = os.path.join(tmpdir, 'package.deb')

        try:
            package.parse_deb(local_file)
        except Exception as err:
            print("Can't parse '%s':\n%s" % (file_path, str(err)))
            if force:
                if dist in malformed_lists:
                    malformed_lists[dist].append(file_path)
                else:
                    malformed_lists[dist] = [file_path]
                continue
            else:
                raise err

        package['Filename'] = file_path
        package['Size'] = os.path.getsize(local_file)
        package['FileTime'] = mtime

        calculate_package_checksums(package, local_file)

        packages = repo_info.package_lists[components].packages

        if package in packages:
            packages.remove(package)
        packages.add(package)

    for dist in repo_info.dists:
        malformed_list = malformed_lists.get(dist, [])
        save_malformed_list(repo_info.storage, dist, malformed_list)


def process_sources(repo_info, tempdir):
    """Add information about changed files to the source.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    tempdir - path to the directory for storing temporary files (string).
    """
    mtimes = get_sources_mtimes(repo_info.source_lists)
    tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)

    expr = r'^.*\.dsc$'
    for file_path in repo_info.storage.files('pool'):
        file_path = file_path.lstrip('/')

        match = re.match(expr, file_path)

        if not match:
            continue

        components = split_src_path(file_path)

        if not components:
            print("Failed to parse file name: '%s'" % file_path)
            sys.exit(1)

        dist, _ = components
        repo_info.dists.add(dist)

        mtime = repo_info.storage.mtime(file_path)
        if file_path in mtimes:
            if str(mtime) == str(mtimes[file_path]):
                print("Skipping: '%s'" % file_path)
                continue
            print("Updating: '%s'" % file_path)
        else:
            print("Adding: '%s'" % file_path)

        repo_info.storage.download_file(file_path, os.path.join(tmpdir, 'source.dsc'))

        source = Source()
        local_file = os.path.join(tmpdir, 'source.dsc')
        source.parse_dsc(local_file, file_path, mtime)

        source['Filename'] = file_path
        source['FileTime'] = mtime

        sources = repo_info.source_lists[components].sources

        if source in sources:
            sources.remove(source)
        sources.add(source)


def update_packages_files(repo_info):
    """Update the "Packages" files.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    """
    for key in repo_info.package_lists:
        dist, component, arch = key
        subdir = 'source' if arch == 'source' else 'binary-%s' % arch

        repo_info.components[dist].add(component)
        repo_info.architectures[dist].add(arch)

        package_list = repo_info.package_lists[key]

        prefix = 'dists/%s/' % dist

        pkg_file_path = '%s/%s/Packages' % (component, subdir)
        pkg_file = package_list.dump_string()

        pkg_file_gzip_path = '%s/%s/Packages.gz' % (component, subdir)
        pkg_file_gzip = gzip_bytes(pkg_file.encode('utf-8'))

        pkg_file_bz2_path = '%s/%s/Packages.bz2' % (component, subdir)
        pkg_file_bz2 = bz2_bytes(pkg_file.encode('utf-8'))

        repo_info.storage.write_file(prefix + pkg_file_path, pkg_file.encode('utf-8'))
        repo_info.storage.write_file(prefix + pkg_file_gzip_path, pkg_file_gzip)
        repo_info.storage.write_file(prefix + pkg_file_bz2_path, pkg_file_bz2)

        for path in [pkg_file_path, pkg_file_gzip_path, pkg_file_bz2_path]:
            data = repo_info.storage.read_file(prefix + path)
            repo_info.sizes[dist][path] = len(data)

            for checksum_type in ['md5', 'sha1', 'sha256']:
                h = hashlib.new(checksum_type)
                h.update(data)

                repo_info.checksums[dist][(checksum_type, path)] = h.hexdigest()


def update_sources_files(repo_info):
    """Update the "Sources" files.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    """
    for key in repo_info.source_lists:
        dist, component = key
        subdir = 'source'

        repo_info.components[dist].add(component)

        source_list = repo_info.source_lists[key]

        prefix = 'dists/%s/' % dist

        src_file_path = '%s/%s/Sources' % (component, subdir)
        src_file = source_list.dump_string()

        src_file_gzip_path = '%s/%s/Sources.gz' % (component, subdir)
        src_file_gzip = gzip_bytes(src_file.encode('utf-8'))

        src_file_bz2_path = '%s/%s/Sources.bz2' % (component, subdir)
        src_file_bz2 = bz2_bytes(src_file.encode('utf-8'))

        repo_info.storage.write_file(prefix + src_file_path, src_file.encode('utf-8'))
        repo_info.storage.write_file(prefix + src_file_gzip_path, src_file_gzip)
        repo_info.storage.write_file(prefix + src_file_bz2_path, src_file_bz2)

        for path in [src_file_path, src_file_gzip_path, src_file_bz2_path]:
            data = repo_info.storage.read_file(prefix + path)
            repo_info.sizes[dist][path] = len(data)

            for checksum_type in ['md5', 'sha1', 'sha256']:
                h = hashlib.new(checksum_type)
                h.update(data)

                repo_info.checksums[dist][(checksum_type, path)] = h.hexdigest()


def sign_release_file(storage, release_str, dist):
    """Sign the "Release" file.

    Keyword arguments:
    storage - storage with repositories (Storage object).
    release_str - string containing the "Release" file (string).
    dist - distribution name (string).
    """
    keyname = os.getenv('GPG_SIGN_KEY')
    release_signature = gpg_sign_string(release_str, keyname)
    release_inline = gpg_sign_string(release_str, keyname, True)
    storage.write_file('dists/%s/Release.gpg' % dist, release_signature)
    storage.write_file('dists/%s/InRelease' % dist, release_inline)


def update_release_files(repo_info, sign):
    """Update the "Release" files.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    """
    creation_date = rfc_2822_now_str()

    for dist in repo_info.dists:
        release = Release()

        release['Origin'] = os.getenv('MKREPO_DEB_ORIGIN') or 'Repo generator'
        release['Label'] = os.getenv('MKREPO_DEB_LABEL') or 'Repo generator'
        release['Codename'] = dist
        release['Date'] = creation_date
        release['Architectures'] = ' '.join(repo_info.architectures[dist])
        release['Components'] = ' '.join(repo_info.components[dist])
        release['Description'] = os.getenv('MKREPO_DEB_DESCRIPTION')\
            or 'Repo generator'

        checksum_lines = collections.defaultdict(list)
        checksum_names = {'md5': 'MD5Sum', 'sha1': 'SHA1', 'sha256': 'SHA256'}
        for checksum_key, checksum_value in repo_info.checksums[dist].items():
            checksum_type, path = checksum_key

            file_size = repo_info.sizes[dist][path]
            checksum_name = checksum_names[checksum_type]

            line = ' %s %s %s' % (checksum_value, file_size, path)
            checksum_lines[checksum_name].append(line)

        for checksum_name in checksum_lines.keys():
            release[checksum_name] = \
                '\n' + '\n'.join(checksum_lines[checksum_name])

        release_str = release.dump_string()
        repo_info.storage.write_file('dists/%s/Release' % dist,
                           release_str.encode('utf-8'))

        if sign:
            sign_release_file(repo_info.storage, release_str, dist)


def update_repo(storage, sign, tempdir, force=False):
    """Update metainformation of the repository.

    Keyword arguments:
    storage - storage with repositories (Storage object).
    sign - whether to sign the "Release" files (bool).
    tempdir - path to the directory for storing temporary files (string).
    force - skip a malformed package without raising an error (bool).
    """
    repo_info = RepoInfo(storage)

    read_release_and_indices(repo_info)
    process_packages(repo_info, tempdir, force)
    process_sources(repo_info, tempdir)
    update_packages_files(repo_info)
    update_sources_files(repo_info)
    update_release_files(repo_info, sign)
