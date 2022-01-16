#!/usr/bin/env python

import bz2
import collections
import datetime
import email
import gzip
import hashlib
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
from io import BytesIO


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


class IndexUnit(object):
    """Describes the common part of an index unit."""

    def __init__(self):
        self.fields = collections.OrderedDict()

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
        return not (self == other)


class Package(IndexUnit):
    """"Package" describes the unit of the "Package" index."""

    def __init__(self, component='main', arch='amd64'):
        super(Package, self).__init__()
        self.component = component
        self.arch = arch

    def parse_deb(self, debfile):
        if subprocess.call('ar t ' + debfile + ' | grep control.tar.gz', shell=True) == 0:
            cmd = 'ar -p ' + debfile + ' control.tar.gz |' + \
                  'tar -xzf - --to-stdout ./control'
        else:
            cmd = 'ar -p ' + debfile + ' control.tar.xz |' + \
                  'tar -xJf - --to-stdout ./control'

        control = subprocess.check_output(cmd, shell=True)
        self.parse_string(control.decode('utf-8').strip())

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


class Source(IndexUnit):
    """"Source" describes the unit of the "Source" index."""

    def __init__(self):
        super(Source, self).__init__()

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


class Index(object):
    """Describes the common part of an index."""

    def __init__(self, component='main'):
        self.component = component
        self.units = set()

    def parse_gzip_file(self, filename):
        """Parse compressed "Index" file.

        Keyword arguments:
        filename - path (string).
        """
        with gzip.open(filename) as f:
            self.parse_string(f.read())

    def parse_plain_file(self, filename):
        """Parse "Index" file.

        Keyword arguments:
        filename - path (string).
        """
        with open(filename) as f:
            self.parse_string(f.read())

    def parse_file(self, filename):
        """Parse compressed or plain "Index" file.

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

        for unit in self.units:
            result.append(unit.dump_string())

        return '\n\n'.join(result) + '\n'


class PackageIndex(Index):
    """"PackageIndex" describes the "Package" index."""

    def __init__(self, component='main', arch='x86_64'):
        super(PackageIndex, self).__init__(component)
        self.arch = arch

    def parse_string(self, data):
        packages = set()
        for entry in data.strip().split('\n\n'):
            if entry.strip() == "":
                continue
            pkg = Package(component=self.component,
                          arch=self.arch)
            pkg.parse_string(entry)
            packages.add(pkg)

        self.units = packages


class SourceIndex(Index):
    """"SourceIndex" describes the "Source" index."""

    def __init__(self, component='main'):
        super(SourceIndex, self).__init__(component)

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

        self.units = sources


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
        # package_index_list - list of the package index (dictionary
        #                      (dist, component, arch) to PackageIndex object).
        self.package_index_list = collections.defaultdict(PackageIndex)
        # source_index_list - list of the source index (dictionary
        #                     (dist, component, arch) to SourceIndex object).
        self.source_index_list = collections.defaultdict(SourceIndex)
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


def get_dist_from_path(path):
    """Return the distribution information from the package path.

    Keyword arguments:
    path - path to control file (string).
    """
    dist = ''
    match_path = re.match('^pool/(?P<dist>[^/]+)/main', path)
    if match_path:
        dist = match_path.group('dist')

    return dist


def split_control_file_path(path, ctrl_type):
    """Return the distribution, architecture and component relevant control file.

    Keyword arguments:
    path - path to control file (string).
    ctrl_type - type of the control file(string: "src" / "binary")
    """

    arch = ''

    if ctrl_type == 'binary':
        # According to
        # https://www.debian.org/doc/manuals/debian-reference/ch02.en.html#_debian_package_file_names
        # the package name format is the following
        # <package-name>_<upstream-version>-<debian.revision>_<architecture>.deb
        #
        # Also to usable characters for <upstream-version> '~' has been
        # added, because some packages from the ubuntu repository use it
        # and according to https://www.debian.org/doc/debian-policy/ch-controlfields.html#version
        # it's fine.
        expr = r'^(?P<package_name>[a-z0-9][-a-z0-9.+]+)_(?P<upstream_version>[-a-zA-Z0-9.+:~]+)'\
               r'(-(?P<debian_revision>[a-zA-Z0-9.+~]+))_(?P<arch>[^\.]+)\.deb$'

        match_package = re.match(expr, os.path.basename(path))
        if not match_package:
            # According to https://www.debian.org/doc/debian-policy/ch-controlfields.html#version:
            # " If there is no debian_revision then hyphens are not allowed [in upstream_version].
            #
            # <...>
            #
            # It [debian_revision] is optional; if it isn't present then the upstream_version
            # must not contain a hyphen.
            #
            # The package management system will break the version number apart at the last hyphen
            # in the string (if there is one) to determine the upstream_version and debian_revision.
            # The absence of a debian_revision is equivalent to a debian_revision of 0.
            expr2 = (
                r'^(?P<package_name>[a-z0-9][-a-z0-9.+]+)_'
                r'(?P<upstream_version>[a-zA-Z0-9.+:~]+)_'
                r'(?P<arch>[^\.]+)\.deb$'
            )
            match_package = re.match(expr2, os.path.basename(path))

        if not match_package:
            return None

        arch = match_package.group('arch') or 'all'

    dist = get_dist_from_path(path) or 'all'
    component = 'main'

    if ctrl_type == 'src':
        arch = 'source'

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


def process_index_file(repo_info, path, dist, component, arch, index_type):
    """Process an index file ("Packages" / "Sources").

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    path - path to the index file (string).
    dist - distribution (string).
    component - repository area (string).
    arch - architecture (string).
    index_type - type of index (string: "sources" / "packages").
    """

    index = None

    if index_type == 'packages':
        index = PackageIndex(arch=arch)
    elif index_type == 'sources':
        index = SourceIndex()
    else:
        raise RuntimeError('Unknown index type: ' + index_type)

    index.parse_string(repo_info.storage.read_file(path).decode('utf-8'))
    if index_type == 'packages':
        repo_info.package_index_list[(dist, component, arch)] = index
    elif index_type == 'sources':
        repo_info.source_index_list[(dist, component, arch)] = index


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

        components = release['Components'].split()
        architectures = release['Architectures'].split()

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
                process_index_file(repo_info, path, dist, component,
                                   arch, 'packages')

            # Process the "Source" index.
            path = 'dists/%s/%s/source/Sources' % (dist, component)
            if repo_info.storage.exists(path):
                process_index_file(repo_info, path, dist, component,
                                   'source', 'sources')


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


def get_mtimes(index_list):
    """Read the mtimes of files from the index.

    Keyword arguments:
    index_list - list of the indices (dictionary
                 (dist, component, arch) to Index object).

    Return the dictionary "filename to mtime".
    """
    mtimes = {}
    for index in index_list.values():
        for unit in index.units:
            if 'FileTime' in unit.fields and 'Filename' in unit.fields:
                mtimes[unit['Filename'].lstrip(
                    '/')] = float(unit['FileTime'])

    return mtimes


def process_index_units(repo_info, tempdir, index_type, force=False):
    """Add information about changed files.

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    tempdir - path to the directory for storing temporary files (string).
    index_type - type of index (string: "sources" / "packages").
    force - skip a malformed package without raising an error (bool).
    """

    index_list = None
    ctrl_type = ''
    expr = ''
    tmp_filename = ''

    if index_type == 'packages':
        index_list = repo_info.package_index_list
        ctrl_type = 'binary'
        expr = r'^.*\.deb$'
        tmp_filename = 'package.deb'
    elif index_type == 'sources':
        index_list = repo_info.source_index_list
        ctrl_type = 'src'
        expr = r'^.*\.dsc$'
        tmp_filename = 'source.dsc'
    else:
        raise RuntimeError('Unknown index type: ' + index_type)

    mtimes = get_mtimes(index_list)
    tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)

    # Dictionary (dist to malformed packages list).
    # Malformed list - list of packages that can't be added to the index
    # (some problems encountered during processing).
    malformed_lists = collections.defaultdict(list)

    for file_path in repo_info.storage.files('pool'):
        file_path = file_path.lstrip('/')

        match = re.match(expr, file_path)
        if not match:
            continue

        components = split_control_file_path(file_path, ctrl_type)

        if not components:
            print("Failed to parse file name: '%s'" % file_path)
            if force:
                dist = get_dist_from_path(file_path) or 'all'
                malformed_lists[dist].append(file_path)
                continue
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

        repo_info.storage.download_file(file_path, os.path.join(tmpdir, tmp_filename))

        local_file = os.path.join(tmpdir, tmp_filename)
        unit = None
        if index_type == 'packages':
            unit = Package()
            try:
                unit.parse_deb(local_file)
            except Exception as err:
                print("Can't parse '%s':\n%s" % (file_path, str(err)))
                if force:
                    malformed_lists[dist].append(file_path)
                    continue
                else:
                    raise err

            unit['Size'] = os.path.getsize(local_file)
            calculate_package_checksums(unit, local_file)
        elif index_type == 'sources':
            unit = Source()
            unit.parse_dsc(local_file, file_path, mtime)

        unit['Filename'] = file_path
        unit['FileTime'] = mtime

        units = index_list[components].units

        # In case of updating the "unit", we need to remove information
        # from "index" about the old and add information about the new one.
        if unit in units:
            units.remove(unit)
        units.add(unit)

    if index_type == 'packages':
        for dist in repo_info.dists:
            malformed_list = malformed_lists.get(dist, [])
            save_malformed_list(repo_info.storage, dist, malformed_list)


def update_index_files(repo_info, index_type):
    """Update the index files ("Sources" / "Packages").

    Keyword arguments:
    repo_info - information about the processed repository (RepoInfo object).
    index_type - type of index (string: "sources" / "packages").
    """

    index_filename = ''
    index_list = None
    if index_type == 'packages':
        index_filename = 'Packages'
        index_list = repo_info.package_index_list
    elif index_type == 'sources':
        index_filename = 'Sources'
        index_list = repo_info.source_index_list
    else:
        raise RuntimeError('Unknown index type: ' + index_type)

    for key in index_list:
        dist, component, arch = key
        subdir = 'source' if arch == 'source' else 'binary-%s' % arch

        repo_info.components[dist].add(component)
        if index_type == 'packages':
            repo_info.architectures[dist].add(arch)

        index = index_list[key]

        prefix = 'dists/%s/' % dist

        file_path = '%s/%s/%s' % (component, subdir, index_filename)
        file = index.dump_string()

        file_gzip_path = '%s/%s/%s.gz' % (component, subdir, index_filename)
        file_gzip = gzip_bytes(file.encode('utf-8'))

        file_bz2_path = '%s/%s/%s.bz2' % (component, subdir, index_filename)
        file_bz2 = bz2_bytes(file.encode('utf-8'))

        repo_info.storage.write_file(prefix + file_path, file.encode('utf-8'))
        repo_info.storage.write_file(prefix + file_gzip_path, file_gzip)
        repo_info.storage.write_file(prefix + file_bz2_path, file_bz2)

        for path in [file_path, file_gzip_path, file_bz2_path]:
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
        release['Description'] = os.getenv('MKREPO_DEB_DESCRIPTION') or 'Repo generator'

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
    process_index_units(repo_info, tempdir, 'packages', force)
    process_index_units(repo_info, tempdir, 'sources')
    update_index_files(repo_info, 'packages')
    update_index_files(repo_info, 'sources')
    update_release_files(repo_info, sign)
