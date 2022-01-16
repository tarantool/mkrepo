#!/usr/bin/env python

import datetime
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from io import BytesIO
from xml.sax.saxutils import escape

import rpmfile
import storage

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# Changelog limit is used to get only last CHANGELOG_LIMIT changelog lines.
# Usually it takes last 10.
CHANGELOG_LIMIT = 10


def gzip_bytes(data):
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb") as fobj:
        fobj.write(data)
    return out.getvalue()


def gunzip_bytes(data):
    fobj = BytesIO(data)
    decompressed = gzip.GzipFile(fileobj=fobj)

    return decompressed.read()


def file_checksum(file_name, checksum_type):
    h = hashlib.new(checksum_type)
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def bytes_checksum(data, checksum_type):
    fobj = BytesIO(data)
    h = hashlib.new(checksum_type)
    for chunk in iter(lambda: fobj.read(4096), b""):
        h.update(chunk)

    return h.hexdigest()


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


def sign_metadata(repomdfile):
    """Requires a proper ~/.rpmmacros file.

    See <http://fedoranews.org/tchung/gpg/>
    """
    cmd = ["gpg", "--detach-sign", "--armor", "--digest-algo SHA256", repomdfile]
    try:
        subprocess.check_call(cmd)
        print("Successfully signed repository metadata file")
    except subprocess.CalledProcessError:
        print("Unable to sign repository metadata '%s'" % repomdfile)
        exit(1)


def setup_repository(repo, tempdir):
    """Make sure a repo is present at repopath"""
    if repo._grab.storage.exists("repodata/repomd.xml"):
        return

    tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)
    cmd = ['createrepo', '--no-database', tmpdir]
    subprocess.check_output(cmd)
    repo._grab.syncdir(os.path.join(tmpdir, "repodata"), "repodata")
    shutil.rmtree(tmpdir)


def parse_repomd(data):
    root = ET.fromstring(data)
    namespaces = {'repo': 'http://linux.duke.edu/metadata/repo'}

    filelists = {}
    primary = {}
    other = {}

    # The revision is an optional XML element and may be absent.
    revision = '0'
    revision_element = root.find('repo:revision', namespaces)
    if revision_element:
        revision = revision_element.text

    for child in root:
        if 'type' not in child.attrib:
            continue

        result = {}
        for key in ['checksum', 'open-checksum',
                    'timestamp', 'size', 'open-size']:
            result[key] = child.find('repo:' + key, namespaces).text
        result['location'] = child.find(
            'repo:location', namespaces).attrib['href']

        if child.attrib['type'] == 'filelists':
            filelists = result
        elif child.attrib['type'] == 'primary':
            primary = result
        elif child.attrib['type'] == 'other':
            other = result

    return filelists, primary, other, revision


def parse_filelists(data):
    root = ET.fromstring(data)
    namespaces = {'filelists': 'http://linux.duke.edu/metadata/filelists'}

    packages = {}

    for child in root:
        if not child.tag.endswith('}package'):
            continue

        pkgid = child.attrib['pkgid']
        name = child.attrib['name']
        arch = child.attrib['arch']
        version = child.find('filelists:version', namespaces)

        version = {'ver': version.attrib['ver'],
                   'rel': version.attrib['rel'],
                   'epoch': version.attrib.get('epoch', '0')}

        files = []
        for node in child.findall('filelists:file', namespaces):
            file_name = node.text
            file_type = 'file'

            if 'type' in node.attrib and node.attrib['type'] == 'dir':
                file_type = 'dir'
            files.append({'type': file_type, 'name': file_name})

        package = {'pkgid': pkgid, 'name': name, 'arch': arch,
                   'version': version, 'files': files}
        nerv = (name, version['epoch'], version['rel'], version['ver'])
        packages[nerv] = package

    return packages


def dump_filelists(filelists):
    res = ""

    res += '<?xml version="1.0" encoding="UTF-8"?>\n'
    res += '<filelists xmlns="http://linux.duke.edu/metadata/filelists" packages="%d">\n' % len(
        filelists)

    for package in filelists.values():
        res += '<package pkgid="%s" name="%s" arch="%s">\n' % (
            package['pkgid'], package['name'], package['arch'])

        ver = package['version']

        res += '  <version '
        components = ' '.join(['%s="%s"' % (c, ver[c])
                               for c in ['epoch', 'ver', 'rel'] if ver[c]])
        res += '%s/>\n' % components

        for fileentry in package['files']:
            if fileentry['type'] == 'file':
                res += '  <file>%s</file>\n' % fileentry['name']
            else:
                res += '  <file type="dir">%s</file>\n' % fileentry['name']

        res += '</package>\n'

    res += "</filelists>\n"

    return res


def parse_primary(data):
    root = ET.fromstring(data)
    namespaces = {'primary': 'http://linux.duke.edu/metadata/common',
                  'rpm': 'http://linux.duke.edu/metadata/rpm'}

    packages = {}

    for child in root:
        if not child.tag.endswith('}package'):
            continue

        checksum = child.find('primary:checksum', namespaces).text
        name = child.find('primary:name', namespaces).text
        arch = child.find('primary:arch', namespaces).text
        summary = child.find('primary:summary', namespaces).text
        description = child.find('primary:description', namespaces).text
        packager = child.find('primary:packager', namespaces).text
        url = child.find('primary:url', namespaces).text
        time = child.find('primary:time', namespaces)
        file_time = time.attrib['file']
        build_time = time.attrib['build']
        size = child.find('primary:size', namespaces)
        package_size = size.attrib['package']
        installed_size = size.attrib['installed']
        archive_size = size.attrib['archive']
        location = child.find('primary:location', namespaces).attrib['href']

        version = child.find('primary:version', namespaces)
        version = {'ver': version.attrib['ver'],
                   'rel': version.attrib['rel'],
                   'epoch': version.attrib.get('epoch', '0')}

        # format
        fmt = child.find('primary:format', namespaces)

        format_license = fmt.find('rpm:license', namespaces).text
        vendor = fmt.find('rpm:vendor', namespaces)
        format_vendor = vendor.text if vendor else ""
        format_group = fmt.find('rpm:group', namespaces).text
        format_buildhost = fmt.find('rpm:buildhost', namespaces).text
        format_sourcerpm = fmt.find('rpm:sourcerpm', namespaces).text
        header_range = fmt.find('rpm:header-range', namespaces)
        format_header_start = header_range.attrib['start']
        format_header_end = header_range.attrib['end']

        # provides

        provides = fmt.find('rpm:provides', namespaces)
        if provides is None:
            provides = []

        provides_dict = {}

        for entry in provides:
            provides_name = entry.attrib['name']
            provides_epoch = entry.attrib.get('epoch', None)
            provides_rel = entry.attrib.get('rel', None)
            provides_ver = entry.attrib.get('ver', None)
            provides_flags = entry.attrib.get('flags', None)

            nerv = (provides_name, provides_epoch, provides_rel, provides_ver)

            provides_dict[nerv] = {'name': provides_name,
                                   'epoch': provides_epoch,
                                   'rel': provides_rel,
                                   'ver': provides_ver,
                                   'flags': provides_flags}

        # requires

        requires = fmt.find('rpm:requires', namespaces)
        if requires is None:
            requires = []

        requires_dict = {}

        for entry in requires:
            requires_name = entry.attrib['name']
            requires_epoch = entry.attrib.get('epoch', None)
            requires_rel = entry.attrib.get('rel', None)
            requires_ver = entry.attrib.get('ver', None)
            requires_flags = entry.attrib.get('flags', None)
            requires_pre = entry.attrib.get('pre', None)

            nerv = (requires_name, requires_epoch, requires_rel, requires_ver)

            requires_dict[nerv] = {'name': requires_name,
                                   'epoch': requires_epoch,
                                   'rel': requires_rel,
                                   'ver': requires_ver,
                                   'flags': requires_flags,
                                   'pre': requires_pre}

        # obsoletes

        obsoletes = fmt.find('rpm:obsoletes', namespaces)
        if obsoletes is None:
            obsoletes = []

        obsoletes_dict = {}

        for entry in obsoletes:
            obsoletes_name = entry.attrib['name']
            obsoletes_epoch = entry.attrib.get('epoch', None)
            obsoletes_rel = entry.attrib.get('rel', None)
            obsoletes_ver = entry.attrib.get('ver', None)
            obsoletes_flags = entry.attrib.get('flags', None)

            nerv = (obsoletes_name, obsoletes_epoch,
                    obsoletes_rel, obsoletes_ver)

            obsoletes_dict[nerv] = {'name': obsoletes_name,
                                    'epoch': obsoletes_epoch,
                                    'rel': obsoletes_rel,
                                    'ver': obsoletes_ver,
                                    'flags': obsoletes_flags}

        # files
        files = []
        for node in fmt.findall('primary:file', namespaces):
            file_name = node.text
            file_type = 'file'

            if 'type' in node.attrib and node.attrib['type'] == 'dir':
                file_type = 'dir'
            files.append({'type': file_type, 'name': file_name})

        # result package
        format_dict = {'license': format_license,
                       'vendor': format_vendor,
                       'group': format_group,
                       'buildhost': format_buildhost,
                       'sourcerpm': format_sourcerpm,
                       'header_start': format_header_start,
                       'header_end': format_header_end,
                       'provides': provides_dict,
                       'requires': requires_dict,
                       'obsoletes': obsoletes_dict,
                       'files': files}

        package = {
            'checksum': checksum,
            'name': name,
            'arch': arch,
            'version': version,
            'summary': summary,
            'description': description,
            'packager': packager,
            'url': url,
            'file_time': file_time,
            'build_time': build_time,
            'package_size': package_size,
            'installed_size': installed_size,
            'archive_size': archive_size,
            'location': location,
            'format': format_dict}

        nerv = (name, version['epoch'], version['rel'], version['ver'])
        packages[nerv] = package
    return packages


def parse_other(data):
    """Parse other.xml

    Find 'other:changelog' and 'other:version' and
    fill changelog, version and package.

    Keyword Arguments:
    data - The unparsed data of other.xml.gz (byte, default: None)

    Return Parsed data as a packages (dict)
    """
    root = ET.fromstring(data)

    namespaces = {'other': 'http://linux.duke.edu/metadata/other'}

    packages = {}

    for child in root:
        if not child.tag.endswith('}package'):
            continue

        package_id = child.attrib['pkgid']
        name = child.attrib['name']
        arch = child.attrib['arch']
        version = child.find('other:version', namespaces)
        version = {
            'ver': version.attrib['ver'],
            'rel': version.attrib['rel'],
            'epoch': version.attrib.get('epoch', '0'),
        }

        changelog_list = child.findall('other:changelog', namespaces)

        changelog = []

        for log in changelog_list:
            changelog.append({
                'author': log.attrib['author'],
                'date': log.attrib['date'],
                'text': log.text,
            })

        package = {'pkgid': package_id, 'name': name, 'arch': arch,
                   'version': version, 'changelog': changelog}
        nerv = (name, version['epoch'], version['rel'], version['ver'])

        packages[nerv] = package

    return packages


def dump_primary(primary):
    res = ""

    res += '<?xml version="1.0" encoding="UTF-8"?>\n'
    res += (
        '<metadata xmlns="http://linux.duke.edu/metadata/common" '
        'xmlns:rpm="http://linux.duke.edu/metadata/rpm" '
        'packages="%d">\n' % len(primary)
    )

    for package in primary.values():
        res += '<package type="rpm">\n'
        res += '  <name>%s</name>\n' % package['name']
        res += '  <arch>%s</arch>\n' % package['arch']

        ver = package['version']
        res += '  <version '
        components = ' '.join(['%s="%s"' % (c, ver[c])
                               for c in ['epoch', 'ver', 'rel'] if ver[c]])
        res += '%s/>\n' % components

        res += '  <checksum type="sha256" pkgid="YES">%s</checksum>\n' % (
            package['checksum'])

        res += '  <summary>%s</summary>\n' % escape(package['summary'] or '')
        res += '  <description>%s</description>\n' % escape(
            package['description'] or '')
        res += '  <packager>%s</packager>\n' % escape(
            package['packager'] or '')

        res += '  <url>%s</url>\n' % (package['url'] or '')
        res += '  <time file="%s" build="%s"/>\n' % (package['file_time'],
                                                     package['build_time'])
        res += '  <size package="%s" installed="%s" archive="%s"/>\n' % (
            package['package_size'],
            package['installed_size'],
            package['archive_size']
        )
        res += '  <location href="%s"/>\n' % package['location']

        fmt = package['format']

        res += '  <format>\n'

        res += '    <rpm:license>%s</rpm:license>\n' % fmt['license']

        if fmt['vendor']:
            res += '    <rpm:vendor>%s</rpm:vendor>\n' % escape(fmt['vendor'])

        res += '    <rpm:group>%s</rpm:group>\n' % (fmt['group'] or '')
        res += '    <rpm:buildhost>%s</rpm:buildhost>\n' % fmt['buildhost']
        res += '    <rpm:sourcerpm>%s</rpm:sourcerpm>\n' % fmt['sourcerpm']

        res += '    <rpm:header-range start="%s" end="%s"/>\n' % (
            fmt['header_start'], fmt['header_end'])

        res += '    <rpm:provides>\n'

        for key in sorted(fmt['provides']):
            provides = fmt['provides'][key]
            entry = ['name="%s"' % provides['name']]
            for component in ['flags', 'epoch', 'ver', 'rel']:
                if provides[component] is not None:
                    entry.append('%s="%s"' % (component, provides[component]))

            res += '      <rpm:entry ' + ' '.join(entry) + '/>\n'

        res += '    </rpm:provides>\n'

        res += '    <rpm:requires>\n'

        for key in sorted(fmt['requires']):
            requires = fmt['requires'][key]
            entry = ['name="%s"' % requires['name']]
            for component in ['flags', 'epoch', 'ver', 'rel', 'pre']:
                if requires[component] is not None:
                    entry.append('%s="%s"' % (component, requires[component]))

            res += '      <rpm:entry ' + ' '.join(entry) + '/>\n'

        res += '    </rpm:requires>\n'

        res += '    <rpm:obsoletes>\n'

        for key in sorted(fmt['obsoletes']):
            obsoletes = fmt['obsoletes'][key]
            entry = ['name="%s"' % obsoletes['name']]
            for component in ['flags', 'epoch', 'ver', 'rel']:
                if obsoletes[component] is not None:
                    entry.append('%s="%s"' % (component, obsoletes[component]))

            res += '      <rpm:entry ' + ' '.join(entry) + '/>\n'

        res += '    </rpm:obsoletes>\n'

        res += '  </format>\n'
        res += '</package>\n'

    res += "</metadata>\n"

    return res


def parse_ver_str(ver_str):
    if not ver_str:
        return (None, None, None)

    expr = r'^(\d+:)?([^-]*)(-[^-]*)?$'
    match = re.match(expr, ver_str)
    if not match:
        raise RuntimeError("Can't parse version: '%s'" % ver_str)
    epoch = match.group(1)[:-1] if match.group(1) else "0"
    ver = match.group(2)
    rel = match.group(3)[1:] if match.group(3) else None
    return epoch, ver, rel


def header_to_other(header, sha256):
    """Method that decodes data for parsing in sha256

    Keyword arguments:
    header - data that get passed to decode (string, default: None)
    sha256 - code format that is assigned for generating package id (string)

    Return data from the header of xml tree (name, version, author, etc)
    """
    pkgid = sha256
    name = get_with_decode(header, 'NAME', None)
    arch = get_arch_from_header(header)
    epoch = header.get('EPOCH', '0')
    rel = get_with_decode(header, 'RELEASE', None)
    ver = get_with_decode(header, 'VERSION', None)
    version = {'ver': ver, 'rel': rel, 'epoch': epoch}

    package = {
        'pkgid': pkgid,
        'name': name,
        'arch': arch,
        'version': version,
        'changelog': [],
    }

    changelog_name = header.get('CHANGELOGNAME', [])
    if not isinstance(changelog_name, list):
        changelog_name = [changelog_name]
    changelog_text = header.get('CHANGELOGTEXT', [])
    if not isinstance(changelog_text, list):
        changelog_text = [changelog_text]
    changelog_date = header.get('CHANGELOGTIME', [])
    if not isinstance(changelog_date, list):
        changelog_date = [changelog_date]

    # get newest CHANGELOG_LIMIT lines in terms of time
    # (initial commit is oldest), we order these lines as a createrepo does
    # in reversed order (from old to new)
    changelog_name = changelog_name[:CHANGELOG_LIMIT][::-1]
    changelog_text = changelog_text[:CHANGELOG_LIMIT][::-1]
    changelog_date = changelog_date[:CHANGELOG_LIMIT][::-1]

    for date, author, text in zip(changelog_date, changelog_name, changelog_text):
        package['changelog'].append({
            'author': escape(author.decode('utf-8')),
            'date': date,
            'text': escape(text.decode('utf-8')),
        })

    nerv = (name, version['epoch'], version['rel'], version['ver'])
    return nerv, package


def dump_other(other):
    """Generate other.xml.gz info

    The method generates information for all packages in next structure
    consequently:
    <package pkgid="..." name="..." arch="..."
        <version epoch="..." ver="..." rel="..."/>
        <changelog author="..." date"...">...</changelog>
    </package>

    Keyword arguments:
    other - other data for packages (dict)

    Return full xml tree of an other data (string)
    """
    res = ""
    res += '<?xml version="1.0" encoding="UTF-8"?>\n'
    res += '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="%d">\n' % len(other)

    for package in other.values():
        res += '<package pkgid="%s" name="%s" arch="%s">\n' % (
            package['pkgid'], package['name'], package['arch'])

        ver = package['version']
        log = package['changelog']

        res += '  <version '
        components = ' '.join(
            ['%s="%s"' % (c, ver[c]) for c in ['epoch', 'ver', 'rel'] if ver[c]])
        res += '%s/>\n' % components

        for changelog in log:
            res += '  <changelog author="%s" date="%s">%s</changelog>\n' % (
                escape(changelog['author']), changelog['date'], escape(changelog['text']))

        res += '</package>\n'

    res += "</otherdata>"

    return res


def get_with_decode(dictionary, key, default='', encoding='utf-8'):
    res = dictionary.get(key, default)
    if res:
        res = res.decode(encoding)
    return res


def get_arch_from_header(header):
    """Defines the architecture of the package according to
    the data from the header.

    Keyword arguments:
    header - parsed rpm package header (dict)

    Return the architecture the package is for (string)
    """

    # The architecture definition condition is based on
    # https://github.com/rpm-software-management/yum/blob/4ed25525ee4781907bd204018c27f44948ed83fe/yum/packages.py#L2222
    sourcepackage = header.get('SOURCEPACKAGE', None)
    sourcerpm = get_with_decode(header, 'SOURCERPM', '')
    if sourcepackage == 1 or not sourcerpm:
        return 'src'
    else:
        return get_with_decode(header, 'ARCH', None)


def header_to_filelists(header, sha256):
    pkgid = sha256
    name = get_with_decode(header, 'NAME', None)
    arch = get_arch_from_header(header)
    epoch = header.get('EPOCH', '0')
    rel = get_with_decode(header, 'RELEASE', None)
    ver = get_with_decode(header, 'VERSION', None)
    version = {'ver': ver, 'rel': rel, 'epoch': epoch}

    dirnames = header.get('DIRNAMES', [])
    if not isinstance(dirnames, list):
        dirnames = [dirnames]
    classdict = header.get('CLASSDICT', [])
    if not isinstance(classdict, list):
        classdict = [classdict]
    basenames = header.get('BASENAMES', [])
    if not isinstance(basenames, list):
        basenames = [basenames]
    dirindexes = header.get('DIRINDEXES', [])
    if not isinstance(dirindexes, list):
        dirindexes = [dirindexes]
    fileclasses = header.get('FILECLASS', [])
    if not isinstance(fileclasses, list):
        fileclasses = [fileclasses]

    files = []

    for entry in zip(basenames, dirindexes, fileclasses):
        filename = entry[0].decode('utf-8')
        dirname = dirnames[entry[1]].decode('utf-8')

        fileclass = classdict[entry[2]]

        filetype = "file"

        if fileclass == "directory":
            filetype = "dir"

        files.append({'name': dirname + filename, 'type': filetype})

    for dirname in dirnames:
        files.append({'name': dirname.decode('utf-8'), 'type': 'dir'})

    package = {'pkgid': pkgid, 'name': name, 'arch': arch,
               'version': version, 'files': files}
    nerv = (name, version['epoch'], version['rel'], version['ver'])

    return nerv, package


def header_to_primary(
        header,
        sha256,
        mtime,
        location,
        header_start,
        header_end,
        size):
    name = get_with_decode(header, 'NAME', None)
    arch = get_arch_from_header(header)
    summary = get_with_decode(header, 'SUMMARY')
    description = get_with_decode(header, 'DESCRIPTION')
    packager = get_with_decode(header, 'PACKAGER', None)
    build_time = header.get('BUILDTIME', '')
    url = get_with_decode(header, 'URL')
    epoch = header.get('EPOCH', '0')
    rel = get_with_decode(header, 'RELEASE', None)
    ver = get_with_decode(header, 'VERSION')
    version = {'ver': ver, 'rel': rel, 'epoch': epoch}

    package_size = size
    installed_size = header['SIZE']
    archive_size = header['PAYLOADSIZE']

    # format

    format_license = get_with_decode(header, 'LICENSE', None)
    format_vendor = get_with_decode(header, 'VENDOR', None)
    format_group = get_with_decode(header, 'GROUP', None)
    format_buildhost = get_with_decode(header, 'BUILDHOST', None)
    format_sourcerpm = get_with_decode(header, 'SOURCERPM', None)
    format_header_start = header_start
    format_header_end = header_end

    # provides

    provides_dict = {}
    providename = header.get('PROVIDENAME', [])
    provideversion = header.get('PROVIDEVERSION', [])
    provideflags = header.get('PROVIDEFLAGS', [])

    if not isinstance(provideflags, list):
        provideflags = [provideflags]

    for entry in zip(providename, provideversion, provideflags):
        provides_name = entry[0].decode('utf-8')
        provides_epoch, provides_ver, provides_rel = \
            parse_ver_str(entry[1].decode('utf-8'))
        provides_flags = rpmfile.flags_to_str(entry[2])

        nerv = (provides_name, provides_epoch, provides_rel, provides_ver)

        provides_dict[nerv] = {'name': provides_name,
                               'epoch': provides_epoch,
                               'rel': provides_rel,
                               'ver': provides_ver,
                               'flags': provides_flags}

    # requires

    requires_dict = {}
    requirename = header.get('REQUIRENAME', [])
    requireversion = header.get('REQUIREVERSION', [])
    requireflags = header.get('REQUIREFLAGS', [])
    if type(requireflags) is not list:
        requireflags = [requireflags]

    for entry in zip(requirename, requireversion, requireflags):
        requires_name = entry[0].decode('utf-8')
        requires_epoch, requires_ver, requires_rel = \
            parse_ver_str(entry[1].decode('utf-8'))
        requires_flags = rpmfile.flags_to_str(entry[2])

        if entry[2] & rpmfile.RPMSENSE_RPMLIB:
            continue

        pre = None

        if entry[2] & 4352:
            pre = "1"

        nerv = (requires_name, requires_epoch, requires_rel, requires_ver)

        requires_dict[nerv] = {'name': requires_name,
                               'epoch': requires_epoch,
                               'rel': requires_rel,
                               'ver': requires_ver,
                               'flags': requires_flags,
                               "pre": pre}

    # obsoletes

    obsoletes_dict = {}
    obsoletename = header.get('OBSOLETENAME', [])
    obsoleteversion = header.get('OBSOLETEVERSION', [])
    obsoleteflags = header.get('OBSOLETEFLAGS', [])

    if not isinstance(obsoleteflags, list):
        obsoleteflags = [obsoleteflags]

    for entry in zip(obsoletename, obsoleteversion, obsoleteflags):
        obsoletes_name = entry[0].decode('utf-8')
        obsoletes_epoch, obsoletes_ver, obsoletes_rel = \
            parse_ver_str(entry[1].decode('utf-8'))
        obsoletes_flags = rpmfile.flags_to_str(entry[2])

        nerv = (obsoletes_name, obsoletes_epoch, obsoletes_rel, obsoletes_ver)

        obsoletes_dict[nerv] = {'name': obsoletes_name,
                                'epoch': obsoletes_epoch,
                                'rel': obsoletes_rel,
                                'ver': obsoletes_ver,
                                'flags': obsoletes_flags}

    # files
    dirnames = header.get('DIRNAMES', [])
    if not isinstance(dirnames, list):
        dirnames = [dirnames]
    basenames = header.get('BASENAMES', [])
    if not isinstance(basenames, list):
        basenames = [basenames]
    dirindexes = header.get('DIRINDEXES', [])
    if not isinstance(dirindexes, list):
        dirindexes = [dirindexes]

    files = []
    for entry in zip(basenames, dirindexes):
        filename = entry[0].decode('utf-8')
        dirname = dirnames[entry[1]].decode('utf-8')
        files.append({'name': dirname + filename, 'type': 'file'})

    for dirname in dirnames:
        files.append({'name': dirname.decode('utf-8'), 'type': 'dir'})

    # result package
    format_dict = {'license': format_license,
                   'vendor': format_vendor,
                   'group': format_group,
                   'buildhost': format_buildhost,
                   'sourcerpm': format_sourcerpm,
                   'header_start': format_header_start,
                   'header_end': format_header_end,
                   'provides': provides_dict,
                   'requires': requires_dict,
                   'obsoletes': obsoletes_dict,
                   'files': files}

    package = {
        'checksum': sha256,
        'name': name,
        'arch': arch,
        'version': version,
        'summary': summary,
        'description': description,
        'packager': packager,
        'url': url,
        'file_time': str(
            int(mtime)),
        'build_time': build_time,
        'package_size': package_size,
        'installed_size': installed_size,
        'archive_size': archive_size,
        'location': location,
        'format': format_dict}

    nerv = (name, version['epoch'], version['rel'], version['ver'])

    return nerv, package


def generate_repomd(filelists_str, filelists_gz,
                    primary_str, primary_gz,
                    other_str, other_gz, revision):
    filelists_bytes = filelists_str.encode('utf-8')
    primary_bytes = primary_str.encode('utf-8')
    other_bytes = other_str.encode('utf-8')

    filelists_str_sha256 = bytes_checksum(filelists_bytes, 'sha256')
    primary_str_sha256 = bytes_checksum(primary_bytes, 'sha256')
    other_str_sha256 = bytes_checksum(other_bytes, 'sha256')

    filelists_gz_sha256 = bytes_checksum(filelists_gz, 'sha256')
    primary_gz_sha256 = bytes_checksum(primary_gz, 'sha256')
    other_gz_sha256 = bytes_checksum(other_gz, 'sha256')

    filelists_name = 'repodata/%s-filelists.xml.gz' % filelists_gz_sha256
    primary_name = 'repodata/%s-primary.xml.gz' % primary_gz_sha256
    other_name = 'repodata/%s-other.xml.gz' % other_gz_sha256

    nowdt = datetime.datetime.now()
    nowtuple = nowdt.timetuple()
    nowtimestamp = time.mktime(nowtuple)

    res = ""

    res += '<?xml version="1.0" encoding="UTF-8"?>\n'
    res += (
        '<repomd xmlns="http://linux.duke.edu/metadata/repo" '
        'xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n'
    )

    res += '  <revision>%s</revision>\n' % revision

    res += '  <data type="filelists">\n'
    res += '    <checksum type="sha256">%s</checksum>\n' % filelists_gz_sha256
    res += '    <open-checksum type="sha256">%s</open-checksum>\n' % (
        filelists_str_sha256)
    res += '    <location href="%s"/>\n' % filelists_name
    res += '    <timestamp>%s</timestamp>\n' % int(nowtimestamp)
    res += '    <size>%s</size>\n' % len(filelists_gz)
    res += '    <open-size>%s</open-size>\n' % len(filelists_bytes)
    res += '  </data>\n'

    res += '  <data type="primary">\n'
    res += '    <checksum type="sha256">%s</checksum>\n' % primary_gz_sha256
    res += '    <open-checksum type="sha256">%s</open-checksum>\n' % (
        primary_str_sha256)
    res += '    <location href="%s"/>\n' % primary_name
    res += '    <timestamp>%s</timestamp>\n' % int(nowtimestamp)
    res += '    <size>%s</size>\n' % len(primary_gz)
    res += '    <open-size>%s</open-size>\n' % len(primary_bytes)
    res += '  </data>\n'

    res += '  <data type="other">\n'
    res += '    <checksum type="sha256">%s</checksum>\n' % other_gz_sha256
    res += '    <open-checksum type="sha256">%s</open-checksum>\n' % other_str_sha256
    res += '    <location href="%s"/>\n' % other_name
    res += '    <timestamp>%s</timestamp>\n' % int(nowtimestamp)
    res += '    <size>%s</size>\n' % len(other_gz)
    res += '    <open-size>%s</open-size>\n' % len(other_bytes)
    res += '  </data>\n'

    res += '</repomd>\n'

    return res


def save_malformed_list(storage, malformed_list):
    """Save the list of malformed packages to the storage.

    Keyword arguments:
    storage - storage with repositories (Storage object).
    malformed_list - list of malformed packages (list of strings).
    """
    file = 'repodata/malformed_list.txt'
    if malformed_list:
        print('Save malformed list...')
        storage.write_file(file, '\n'.join(malformed_list).encode('utf-8'))
    elif storage.exists(file):
        # The list existed before, but is not up-to-date now.
        print('Delete malformed list...')
        storage.delete_file(file)


def parse_metafiles(storage):
    """Parse metafiles.

    Keyword arguments:
    storage - storage with repositories (Storage object).
    """
    filelists = {}
    primary = {}
    others = {}
    revision = "0"
    initial_filelists = None
    initial_primary = None
    initial_others = None

    if storage.exists('repodata/repomd.xml'):
        data = storage.read_file('repodata/repomd.xml')

        filelists, primary, others, revision = parse_repomd(data)

        initial_filelists = filelists.get('location', None)
        # The file can be specified in repomd.xml but doesn't exist.
        if initial_filelists and storage.exists(initial_filelists):
            data = storage.read_file(initial_filelists)
            filelists = parse_filelists(gunzip_bytes(data))
        else:
            initial_filelists = None
            filelists = {}

        initial_primary = primary.get('location', None)
        # The file can be specified in repomd.xml but doesn't exist.
        if initial_primary and storage.exists(initial_primary):
            data = storage.read_file(initial_primary)
            primary = parse_primary(gunzip_bytes(data))
        else:
            initial_primary = None
            primary = {}

        initial_others = others.get('location', None)
        if initial_others and storage.exists(initial_others):
            data = storage.read_file(initial_others)
            others = parse_other(gunzip_bytes(data))
        else:
            initial_others = None
            others = {}

    return (filelists, primary, others, revision,
            initial_filelists, initial_primary, initial_others)


def update_repo(storage, sign, tempdir, force=False):
    (filelists, primary, others, revision,
     initial_filelists, initial_primary, initial_other) = parse_metafiles(storage)

    recorded_files = set()
    for package in primary.values():
        recorded_files.add((package['location'], float(package['file_time'])))

    existing_files = set()
    expr = r'^.*\.rpm$'
    for file_path in storage.files('.'):
        match = re.match(expr, file_path)

        if not match:
            continue

        mtime = storage.mtime(file_path)

        existing_files.add((file_path, mtime))

    files_to_add = existing_files - recorded_files
    # List of packages that can't be added to the index
    # (some problems encountered during processing).
    malformed_list = []

    for file_to_add in files_to_add:
        file_path = file_to_add[0]
        mtime = file_to_add[1]
        print("Adding: '%s'" % file_path)

        tmpdir = tempfile.mkdtemp('', 'tmp', tempdir)
        storage.download_file(file_path, os.path.join(tmpdir, 'package.rpm'))

        rpminfo = rpmfile.RpmInfo()
        header = None

        try:
            header = rpminfo.parse_file(os.path.join(tmpdir, 'package.rpm'))
        except Exception as err:
            print("Can't parse '%s':\n%s" % (file_path, str(err)))
            if force:
                malformed_list.append(file_path)
                continue
            else:
                raise err

        sha256 = file_checksum(os.path.join(tmpdir, 'package.rpm'), "sha256")

        statinfo = os.stat(os.path.join(tmpdir, 'package.rpm'))
        size = statinfo.st_size

        shutil.rmtree(tmpdir)

        nerv, prim = header_to_primary(header, sha256, mtime, file_path,
                                       rpminfo.header_start, rpminfo.header_end,
                                       size)
        _, flist = header_to_filelists(header, sha256)
        _, other = header_to_other(header, sha256)

        primary[nerv] = prim
        filelists[nerv] = flist
        others[nerv] = other

    save_malformed_list(storage, malformed_list)

    revision = str(int(revision) + 1)

    filelists_str = dump_filelists(filelists)
    primary_str = dump_primary(primary)
    other_str = dump_other(others)

    filelists_gz = gzip_bytes(filelists_str.encode('utf-8'))
    primary_gz = gzip_bytes(primary_str.encode('utf-8'))
    other_gz = gzip_bytes(other_str.encode('utf-8'))

    repomd_str = generate_repomd(filelists_str, filelists_gz,
                                 primary_str, primary_gz,
                                 other_str, other_gz, revision)

    filelists_gz_sha256 = bytes_checksum(filelists_gz, 'sha256')
    primary_gz_sha256 = bytes_checksum(primary_gz, 'sha256')
    other_gz_sha256 = bytes_checksum(other_gz, 'sha256')

    filelists_name = 'repodata/%s-filelists.xml.gz' % filelists_gz_sha256
    primary_name = 'repodata/%s-primary.xml.gz' % primary_gz_sha256
    other_name = 'repodata/%s-other.xml.gz' % other_gz_sha256

    storage.write_file(filelists_name, filelists_gz)
    storage.write_file(primary_name, primary_gz)
    storage.write_file(other_name, other_gz)
    storage.write_file('repodata/repomd.xml', repomd_str.encode('utf-8'))

    # Here we are deleting few old metafiles.
    # The difference in names between the old and new files (in case the new
    # packages were not added to the repository) exists because part of the
    # name is the sha256 hash from  the".gz" files, wich includes information
    # about time when it was created (in seconds (float)). In my opinion, this
    # difference is not obvious on the one hand and may cease to exist on the
    # other hand (if we start to set timestamp according to a different logic
    # or if the hashsum is removed from the filename).
    # Let's check the names for equivalence.
    if initial_filelists and initial_filelists != filelists_name:
        storage.delete_file(initial_filelists)
    if initial_primary and initial_primary != primary_name:
        storage.delete_file(initial_primary)
    if initial_other and initial_other != other_name:
        storage.delete_file(initial_other)

    if sign:
        keyname = os.getenv('GPG_SIGN_KEY')
        repomd_signed = gpg_sign_string(repomd_str, keyname)
        storage.write_file('repodata/repomd.xml.asc', repomd_signed)


def main():
    stor = storage.FilesystemStorage(sys.argv[1])

    update_repo(stor)


if __name__ == '__main__':
    main()
