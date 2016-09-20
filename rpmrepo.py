#!/usr/bin/env python

import boto3
import os
import sys

import subprocess
import tempfile
import shutil
import yum
import storage
import rpmUtils


LIB_ROOT = os.path.dirname(os.path.dirname(__file__))

sys.path.insert(1, os.path.join(LIB_ROOT, "vendor/createrepo"))
import createrepo

ENDPOINT = 'http://farm.tarantool.org:9001'

class LoggerCallback(object):
    def errorlog(self, message):
        print message

    def log(self, message):
        message = message.strip()
#        if message:
#            print message

class S3Grabber(object):
    def __init__(self, storage):
        self.storage = storage

    def key_exists(self, key):
        objs = list(self.bucket.objects.filter(Prefix=key))
        if len(objs) > 0 and objs[0].key == key:
            return key
        else:
            return None

    def urlgrab(self, url, filename, **kwargs):
        if url.startswith('file://'):
            url = url[len('file://'):]

        if not self.storage.exists(url):
            print "urlgrab: key doesn't exist: %s" % url
            raise createrepo.grabber.URLGrabError(14, '%s not found' % url)

        self.storage.download_file(url, filename)

        mtime = self.storage.mtime(url)
        os.utime(filename, (mtime, mtime))

        return filename

    def syncdir(self, dir, remote_dir):
        """Copy all files in dir to url, removing any existing keys."""
        existing_keys = list(self.storage.files(remote_dir))
        new_keys = []

        for filename in sorted(os.listdir(dir)):
            source = os.path.join(dir, filename)
            target = os.path.join(remote_dir, filename)
            self.storage.upload_file(target, source)
            new_keys.append(target.lstrip('/'))

        for key in existing_keys:
            if key not in new_keys:
                self.storage.delete_file(key)


def sign_metadata(repomdfile):
    """Requires a proper ~/.rpmmacros file. See <http://fedoranews.org/tchung/gpg/>"""
    cmd = ["gpg", "--detach-sign", "--armor", repomdfile]
    try:
        subprocess.check_call(cmd)
        print "Successfully signed repository metadata file"
    except subprocess.CalledProcessError as e:
        print "Unable to sign repository metadata '%s'" % (repomdfile)
        exit(1)

def setup_repository(repo):
    """Make sure a repo is present at repopath"""
    if repo._grab.storage.exists("repodata/repomd.xml"):
        return

    tmpdir = tempfile.mkdtemp()
    cmd = ['createrepo', '--no-database', tmpdir]
    subprocess.check_output(cmd)
    repo._grab.syncdir(os.path.join(tmpdir, "repodata"), "repodata")
    shutil.rmtree(tmpdir)

def update_repo(storage, sign):
    tmpdir = tempfile.mkdtemp()
    s3grabber = S3Grabber(storage)

    archlist = set(rpmUtils.arch.arches.keys() +
                   rpmUtils.arch.arches.values() +
                   ['src'])

    # Set up temporary repo that will fetch repodata from s3
    yumbase = yum.YumBase()
    yumbase.preconf.disabled_plugins = '*'
    yumbase.conf.cachedir = os.path.join(tmpdir, 'cache')
    yumbase.repos.disableRepo('*')
    repo = yumbase.add_enable_repo('s3')
    repo._grab = s3grabber

    setup_repository(repo)

    # Ensure that missing base path doesn't cause trouble
    repo._sack = yum.sqlitesack.YumSqlitePackageSack(
        createrepo.readMetadata.CreaterepoPkgOld)

    yumbase._getSacks(archlist=list(archlist))

    # Create metadata generator
    mdconf = createrepo.MetaDataConfig()
    mdconf.directory = tmpdir
    mdconf.pkglist = yum.packageSack.MetaSack()
    mdconf.database = False
    mdconf.deltas = False
    mdgen = createrepo.MetaDataGenerator(mdconf, LoggerCallback())
    mdgen.tempdir = tmpdir

    # Combine existing package sack with new rpm file list
    new_packages = yum.packageSack.PackageSack()

    rpmfiles = [f for f in storage.files() if f.endswith('.rpm')]

    pkgs = yumbase.pkgSack.searchNevra()

    pkgs = []
    pkgs = yumbase.pkgSack.returnPackages()

    mtimes = {}

    for pkg in pkgs:
        mtimes['Packages/'+pkg.relativepath] = pkg.filetime

    for rpmfile in rpmfiles:
        rpmfile = rpmfile.lstrip('/')

        mtime = storage.mtime(rpmfile)
        if rpmfile in mtimes:
            if mtime == mtimes[rpmfile]:
                print "Skipping: '%s'" % rpmfile
                continue
            print "Updating: '%s'" % rpmfile
        else:
            print "Adding: '%s'" % rpmfile

        mdgen._grabber = s3grabber

        # please, don't mess with my path in the <location> tags of primary.xml.gz
        relative_path = "."
        newpkg = mdgen.read_in_package('file://' +rpmfile, relative_path)

        # don't put a base url in <location> tags of primary.xml.gz
        newpkg._baseurl = None

        older_pkgs = yumbase.pkgSack.packagesByTuple(newpkg.pkgtup)

        # Remove packages with the same version
        for i, older in enumerate(reversed(older_pkgs), 1):
            if older.pkgtup == newpkg.pkgtup:
                yumbase.pkgSack.delPackage(older)

        new_packages.addPackage(newpkg)

    mdconf.pkglist.addSack('existing', yumbase.pkgSack)
    mdconf.pkglist.addSack('new', new_packages)

    # Write out new metadata to tmpdir
    mdgen.doPkgMetadata()
    mdgen.doRepoMetadata()
    mdgen.doFinalMove()

    if sign:
        # Generate repodata/repomd.xml.asc
        sign_metadata(os.path.join(tmpdir, 'repodata', 'repomd.xml'))

    # Replace metadata on s3
    s3grabber.syncdir(os.path.join(tmpdir, 'repodata'), 'repodata')

    shutil.rmtree(tmpdir)
