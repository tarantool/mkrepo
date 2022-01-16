#!/usr/bin/env python

import argparse
import os

import debrepo
import rpmrepo
import storage


def is_deb_repo(stor):
    result = False
    for _ in stor.files("pool/"):
        result = True
        break

    return result


def is_rpm_repo(stor):
    result = False
    for _ in stor.files("Packages/"):
        result = True
        break

    return result


def update_repo(path, args):
    stor = None

    if not os.path.exists(args.temp_dir):
        os.mkdir(args.temp_dir)

    if path.startswith('s3://'):
        path = path[len('s3://'):]

        if '/' in path:
            bucket, prefix = path.split('/', 1)
        else:
            bucket, prefix = path, '.'

        stor = storage.S3Storage(args.s3_endpoint,
                                 bucket,
                                 prefix,
                                 args.s3_access_key_id,
                                 args.s3_secret_access_key,
                                 args.s3_region,
                                 args.s3_public_read)

    else:
        stor = storage.FilesystemStorage(path)

    if is_deb_repo(stor):
        print("Updating deb repository: %s" % path)
        debrepo.update_repo(stor, args.sign, args.temp_dir, args.force)
    elif is_rpm_repo(stor):
        print("Updating rpm repository: %s" % path)
        rpmrepo.update_repo(stor, args.sign, args.temp_dir, args.force)
    else:
        print("Unknown repository: %s" % path)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--temp-dir',
        default=".mkrepo",
        help='directory used to store temporary artifacts')

    parser.add_argument(
        '--s3-access-key-id', help='access key for connecting to S3')
    parser.add_argument(
        '--s3-secret-access-key', help='secret key for connecting to S3')

    parser.add_argument(
        '--s3-endpoint',
        help='region endpoint for connecting to S3 (default: s3.amazonaws.com)')

    parser.add_argument(
        '--s3-region',
        help='S3 region name')

    parser.add_argument(
        '--s3-public-read',
        action='store_true',
        default=False,
        help='set read-only permission on files uploaded to S3 to an anonymous users')

    parser.add_argument(
        '--sign',
        action='store_true',
        default=False,
        help='sign package metadata')

    parser.add_argument(
        '--force',
        action='store_true',
        default=False,
        help="""when adding packages to the index, the malformed one will be
              skipped. By default, a malformed package will cause the utility
              to stop working. The malformed_list.txt file will also be added
              to the repository
              """
        )

    parser.add_argument(
        'path', nargs='+',
        help='List of paths to scan. Either s3://bucket/prefix or /path/on/local/fs')

    args = parser.parse_args()

    paths = args.path

    for path in paths:
        update_repo(path, args)


if __name__ == '__main__':
    main()
