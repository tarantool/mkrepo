# Create RPM and DEB repositories in S3

`mkrepo` allows you to maintain an RPM or DEB repository is S3,
and periodically regenerate metadata.

The typical use case is when you have a CI pipeline that pushes new
packages to an S3 storage and you don't want your CI to bother with
regenerating repository metadata.

As a bonus, `mkrepo` supports on-premises S3 servers like [Minio](http://minio.io).

*NB: currently only works on CentOS*

## Quickstart

Create an s3 bucket named e.g. `builds` and put a sample package `package.rpm` to `s3://builds/rpmrepo/Packages`. Then do the following:

``` bash
./mkrepo.py s3://builds/rpmrepo
```

After this, you will find all metadata generated in `s3://builds/rpmrepo/repodata`

## Dependencies

Python libraries:

* yum
* boto3
* createrepo
* rpmUtils

## Command-line reference

`mkrepo` parses your `~/.aws/config` and reads secret key and region settings.
So you may skip them in command line invocation in case you have aws config.

``` bash
mkrepo.py [-h] [--s3-access-key-id S3_ACCESS_KEY_ID]
          [--s3-secret-access-key S3_SECRET_ACCESS_KEY]
          [--s3-endpoint S3_ENDPOINT] [--s3-region S3_REGION]
          [--sign]
          path [path ...]
```

* `--s3-access-key-id` - /(optional)/ specify S3 access key ID
* `--s3-secret-access-key` - /(optional)/ specify S3 secret key
* `--s3-endpoint` - /(optional)/ specify S3 server URI
* `--s3-region` - /(optional)/ specify S3 region (default is us-east-1)
* `--sign` - /(optional) sign package metadata
* `path` - specify list of path to scan for repositories

## How it works

`mkrepo` searches the supplied path for either `Packages` or `pool` subdir. If
it finds `Packages`, it assumes an rpm repo. If it finds `pool`, it assumes a
deb repo.

Then it parses existing metadata files (if any) and compares timestamps recorded
there with timestamps of all package files in the repo. Any packages that have
different timestamps or that don't exist in metadata, are parsed and added to
metadata.

Then new metadata is uploaded to S3, replacing previous one.

## Credits

Thanks to [Cyril Rohr](https://github.com/crohr) and [Ken Robertson](https://github.com/krobertson), authors of the following awesome tools:

* [rpm-s3](https://github.com/crohr/rpm-s3)
* [deb-s3](https://github.com/krobertson/deb-s3)

Unfortunately, we needed a solution that is completely decoupled from CI pipeline,
and the mentioned tools only support package push mode, when you have to use a
tool to actually push packages to s3, insted of native s3 clients.
