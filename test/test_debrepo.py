#!/usr/bin/env python3

import os
import unittest
from collections import OrderedDict

import debrepo

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestVersionParsing(unittest.TestCase):
    def test_versions(self):
        versions = [
            (
                'pool/deb9/main/t/tarantool/libtarantool-dev_1.5.2.20.g5f5d924-2_amd64.deb',
                ('deb9', 'main', 'amd64')
            ),
            (
                'pool/deb9/main/v/vim/vim_8.2.2434-3_amd64.deb',
                ('deb9', 'main', 'amd64')
            ),
            (
                'pool/main/t/tarantool/tarantool-python_0.6.6-21_amd64.deb',
                ('all', 'main', 'amd64')
            ),
            (
                'debian/pool/main/o/openssl/libssl1.1_1.1.0l-1~deb9u1_amd64.deb',
                ('all', 'main', 'amd64')
            ),
            (
                'pool/multiverse/a/anbox/anbox_0.0~git20200526-1build1_amd64.deb',
                ('all', 'main', 'amd64')
            ),
            (
                'pool/multiverse/a/astrometry-data-2mass/astrometry-data-2mass_1.1_all.deb',
                ('all', 'main', 'all')
            ),
        ]

        for version in versions:
            self.assertEqual(
                debrepo.split_control_file_path(version[0], 'binary'), version[1])

    def test_versions_parsing_on_ubuntu_groovy(self):
        """Check packagename parser on packages from
        https://mirror.yandex.ru/ubuntu/dists/groovy
        """
        test_file_names = [
            'ubuntu_groovy_packages_main.txt',
            'ubuntu_groovy_packages_multiverse.txt',
            'ubuntu_groovy_packages_restricted.txt',
            'ubuntu_groovy_packages_universe.txt'
        ]

        for test_file_name in test_file_names:
            test_path = os.path.join(TEST_DIR, f"resources/{test_file_name}")
            with open(test_path, 'r') as test_file:
                for package_name in test_file:
                    self.assertIsNotNone(debrepo.split_control_file_path(package_name, 'binary'),
                                         "Can't parse packagename: %s" % package_name)


class TestIndexUnit(unittest.TestCase):
    def test_control_tar_archive(self):
        packages = {
            # control.tar.xz
            'openssl_1.1.1f-1ubuntu2_amd64.deb': OrderedDict(
                [
                    ('Package', 'openssl'),
                    ('Version', '1.1.1f-1ubuntu2'),
                    ('Architecture', 'amd64'),
                    ('Maintainer', 'Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>'),
                    ('Installed-Size', '1257'),
                    ('Depends', 'libc6 (>= 2.15), libssl1.1 (>= 1.1.1)'),
                    ('Suggests', 'ca-certificates'),
                    ('Section', 'utils'),
                    ('Priority', 'optional'),
                    ('Multi-Arch', 'foreign'),
                    ('Homepage', 'https://www.openssl.org/'),
                    ('Description', "Secure Sockets Layer toolkit - cryptographic utility\n "
                                    "This package is part of the OpenSSL project's implementation "
                                    "of the SSL\n and TLS cryptographic protocols for secure "
                                    "communication over the\n Internet.\n .\n It contains the "
                                    "general-purpose command line binary /usr/bin/openssl,\n useful"
                                    " for cryptographic operations such as:\n  * creating RSA, DH, "
                                    "and DSA key parameters;\n  * creating X.509 certificates, "
                                    "CSRs, and CRLs;\n  * calculating message digests;\n  * "
                                    "encrypting and decrypting with ciphers;\n  * testing SSL/TLS "
                                    "clients and servers;\n  * handling S/MIME signed or encrypted "
                                    "mail."),
                    ('Original-Maintainer', 'Debian OpenSSL Team '
                                            '<pkg-openssl-devel@lists.alioth.debian.org>')
                ]
            ),
            # control.tar.zst
            'openssl_1.1.1l-1ubuntu1_amd64.deb': OrderedDict(
                [
                    ('Package', 'openssl'),
                    ('Version', '1.1.1l-1ubuntu1'),
                    ('Architecture', 'amd64'),
                    ('Maintainer', 'Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>'),
                    ('Installed-Size', '1268'),
                    ('Depends', 'libc6 (>= 2.34), libssl1.1 (>= 1.1.1)'),
                    ('Suggests', 'ca-certificates'),
                    ('Section', 'utils'),
                    ('Priority', 'optional'),
                    ('Multi-Arch', 'foreign'),
                    ('Homepage', 'https://www.openssl.org/'),
                    ('Description', "Secure Sockets Layer toolkit - cryptographic utility\n "
                                    "This package is part of the OpenSSL project's implementation "
                                    "of the SSL\n and TLS cryptographic protocols for secure "
                                    "communication over the\n Internet.\n .\n It contains the "
                                    "general-purpose command line binary /usr/bin/openssl,\n useful"
                                    " for cryptographic operations such as:\n  * creating RSA, DH, "
                                    "and DSA key parameters;\n  * creating X.509 certificates, "
                                    "CSRs, and CRLs;\n  * calculating message digests;\n  * "
                                    "encrypting and decrypting with ciphers;\n  * testing SSL/TLS "
                                    "clients and servers;\n  * handling S/MIME signed or encrypted "
                                    "mail."),
                    ('Original-Maintainer', 'Debian OpenSSL Team '
                                            '<pkg-openssl-devel@lists.alioth.debian.org>')
                ]
            )
        }
        package = debrepo.Package()
        for package_name in packages:
            try:
                package.parse_deb(os.path.join(TEST_DIR, f"resources/{package_name}"))
            except FileNotFoundError:
                self.fail('parse_deb() raised FileNotFoundError unexpectedly!')
            self.assertEqual(package.fields, packages[package_name])

    def test_raise_exc_when_unknown_control_tar_archive(self):
        package = debrepo.Package()
        self.assertRaises(FileNotFoundError,
                          package.parse_deb, os.path.join(TEST_DIR, 'resources/unknown.deb'))

    def test_signed_source_dsc(self):
        local_file = os.path.join(TEST_DIR, 'resources/source.dsc')
        file_path = 'pool/impish/main/o/openssl/openssl_1.1.1l-1ubuntu1.3.dsc'
        mtime = 1653149784

        source = debrepo.Source()
        source.parse_dsc(local_file, file_path, mtime)

        self.assertEqual(source.fields, OrderedDict(
            [
                ('Format', '3.0 (quilt)'),
                ('Package', 'openssl'),
                ('Binary', 'openssl, libssl1.1, libcrypto1.1-udeb, libssl1.1-udeb, libssl-dev, '
                           'libssl-doc'),
                ('Architecture', 'any all'),
                ('Version', '1.1.1l-1ubuntu1.3'),
                ('Maintainer', 'Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>'),
                ('Uploaders', 'Christoph Martin <christoph.martin@uni-mainz.de>, '
                              'Kurt Roeckx <kurt@roeckx.be>, '
                              'Sebastian Andrzej Siewior <sebastian@breakpoint.cc>'),
                ('Homepage', 'https://www.openssl.org/'),
                ('Standards-Version', '4.5.0'),
                ('Vcs-Browser', 'https://salsa.debian.org/debian/openssl'),
                ('Vcs-Git', 'https://salsa.debian.org/debian/openssl.git'),
                ('Testsuite', 'autopkgtest'),
                ('Build-Depends', 'debhelper-compat (= 12), m4, bc, dpkg-dev (>= 1.15.7)'),
                ('Package-List', '\n libcrypto1.1-udeb udeb debian-installer optional arch=any '
                                 'profile=!noudeb\n libssl-dev deb libdevel optional arch=any\n '
                                 'libssl-doc deb doc optional arch=all\n libssl1.1 deb libs '
                                 'optional arch=any\n libssl1.1-udeb udeb debian-installer '
                                 'optional arch=any profile=!noudeb\n openssl deb utils optional '
                                 'arch=any'),
                ('Checksums-Sha1', '\n f8819dd31642eebea6cc1fa5c256fc9a4f40809b 9834044 '
                                   'openssl_1.1.1l.orig.tar.gz\n '
                                   '1f13a8055c8c143a78e1f18aeae38b22cf3b18e4 488 '
                                   'openssl_1.1.1l.orig.tar.gz.asc\n '
                                   'a784c4a2da659876fc2ea3726ba0da8da5e2681e 149576 '
                                   'openssl_1.1.1l-1ubuntu1.3.debian.tar.xz\n '
                                   '7cd6e994e3bfadf8cc32ba4eb3eca4adf73b3175 2745 '
                                   'openssl_1.1.1l-1ubuntu1.3.dsc'),
                ('Checksums-Sha256', '\n 0b7a3e5e59c34827fe0c3a74b7ec8baef302b98fa80088d7f9153aa16f'
                                     'a76bd1 9834044 openssl_1.1.1l.orig.tar.gz\n '
                                     'e2ae0ea526223843245dd80224b19a55283f4910dd56b7ee7b23187164f69'
                                     'fda 488 openssl_1.1.1l.orig.tar.gz.asc\n '
                                     '5990f4604858033999b2f28dce460aaf93cef9c48129eb53934c437433ecb'
                                     '2bd 149576 openssl_1.1.1l-1ubuntu1.3.debian.tar.xz\n '
                                     'f6fd0a8a2da7e183f77dea2db6fc41275ab9d9bbf0451d8060902893a5c40'
                                     '5a6 2745 openssl_1.1.1l-1ubuntu1.3.dsc'),
                ('Files', '\n ac0d4387f3ba0ad741b0580dd45f6ff3 9834044 openssl_1.1.1l.orig.tar.gz\n'
                          ' dc5c52d7d1e7c2888351434789cdb89c 488 openssl_1.1.1l.orig.tar.gz.asc\n '
                          '2caf1dee8c91060876169e20d63ac22b 149576 '
                          'openssl_1.1.1l-1ubuntu1.3.debian.tar.xz\n '
                          '9c05b0c20bf0bb702683dd616d6ffb7d 2745 openssl_1.1.1l-1ubuntu1.3.dsc'),
                ('Original-Maintainer', 'Debian OpenSSL Team '
                                        '<pkg-openssl-devel@lists.alioth.debian.org>'),
                ('Directory', 'pool/impish/main/o/openssl')
            ]
        ))


if __name__ == '__main__':
    unittest.main()
