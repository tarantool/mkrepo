# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- RPM:
  * Escape contents of `<url>...</url>` in primary.xml.

## [1.0.2] - 2022-12-07

### Changed

- Bump `boto3` version from 1.4.1 to 1.17.5.

## [1.0.1] - 2022-12-07

### Fixed

- RPM:
  * Fix Python 3.6 compatibility by replacing the `removesuffix()` method, which 
    is available since Python 3.9.0, with another code.

### Changed

- Use the `python3` shebang instead of `python` in the `mkrepo` executable path.
- Slightly update package description in `setup.py`.

### Added

- Add auto-installation of required package dependencies.

## [1.0.0] - 2022-11-23

### Added

- RPM:
  * Add support for deletion of stale repo metadata.

### Changed

- RPM:
  * Include 'primary' files into primary.xml.
  * Add the `<rpm:conflicts>` section to primary.xml when it's needed.
  * Not include 'primary' files and packages that are provided into the
    `<rpm:requires>` section.
  * Keep only the highest version of `libc.so.6` in the `<rpm:requires>`
    section.

### Fixed

- RPM:
  * Process `I18NSTRING` header type entries.
  * Handle `latin-1` chars in SUMMARY and DESCRIPTION headers.
  * Fix wrong string representation of flags in the `<rpm:requires>`
    tag entries.

### Removed

- Completely drop support of Python 2.
