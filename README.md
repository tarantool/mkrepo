# Create RPM and DEB repositories in S3

`mkrepo` is a repository generator with pluggable backends,
which allows you to maintain an RPM or DEB repository on various
storages, like local filesystem or S3, and periodically regenerate metadata.

Use it in tandem with your favourite CI system to produce a better pipeline.
`mkrepo` helps you to get rid of ad-hoc cron jobs.

As a bonus, `mkrepo` supports on-premises S3 servers like [Minio](http://minio.io).

Works on Linux and OS X. Should also work on BSD and Windows, but I haven't checked.

## Quickstart

Create an s3 bucket named e.g. `builds` and put a sample package `package.rpm` to `s3://builds/rpmrepo/Packages`. Then do the following:

``` bash
./mkrepo.py s3://builds/rpmrepo
```

After this, you will find all metadata generated in `s3://builds/rpmrepo/repodata`

## Run tests

To run the tests, use the following command::

``` bash
make test
```

## Dependencies

Python libraries:

* boto3

## Command-line reference

`mkrepo` parses your `~/.aws/config` and reads secret key and region settings.
So you may skip them in command line invocation in case you have aws config.

``` bash
  mkrepo.py [-h] 
            [--temp-dir TEMP_DIR]
            [--s3-access-key-id S3_ACCESS_KEY_ID]
            [--s3-secret-access-key S3_SECRET_ACCESS_KEY]
            [--s3-endpoint S3_ENDPOINT]
            [--s3-region S3_REGION]
            [--s3-public-read]
            [--sign]
            [--force]
            path [path ...]
```

* `--temp-dir` - /(optional)/directory used to store temporary artifacts (default is .mkrepo)
* `--s3-access-key-id` - /(optional)/ specify S3 access key ID
* `--s3-secret-access-key` - /(optional)/ specify S3 secret key
* `--s3-endpoint` - /(optional)/ specify S3 server URI
* `--s3-region` - /(optional)/ specify S3 region (default is us-east-1)
* `--s3-public-read` - /(optional)/ set read-only permission on files uploaded
  to S3 for anonymous users
* `--sign` - /(optional) sign package metadata
* `--force` - /(optional) when adding packages to the index, the malformed one
  will be skipped. By default, a malformed package will cause the utility to
  stop working. The malformed_list.txt file will also be added to the repository
* `path` - specify list of path to scan for repositories

## Environment variables reference

* `GPG_SIGN_KEY` - the name of the key that will be used to sign package metadata.

<details><summary>Tips for working with GPG keys</summary>

   * Create a new key:
   ``` bash
   gpg --full-generate-key
   ```
   * To view all your keys, you can use:
   ``` bash
   gpg --list-secret-keys --keyid-format LONG
   ```
   * Scripts can use something like this to get the Key ID:
   ``` bash
   export GPG_SIGN_KEY="$(gpg --list-secret-keys --with-colons | grep ^sec: | cut -d: -f5)"
   ```
   * Export the key in ASCII armored format:
   ``` bash
   gpg --armor --export-secret-keys MYKEYID > mykeys.asc
   ```
   * Import the key:
   ``` bash
   cat mykeys.asc | gpg --batch --import
   ```

</details>

* `MKREPO_DEB_ORIGIN` - the value of the ["Origin"](https://wiki.debian.org/DebianRepository/Format#Origin)
  field of the "Release" file.
* `MKREPO_DEB_LABEL` - the value of the ["Label"](https://wiki.debian.org/DebianRepository/Format#Label)
  field of the "Release" file.
* `MKREPO_DEB_DESCRIPTION` - the value of the "Description" field of the "Release" file.

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
