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
            test_path = os.path.join(TEST_DIR, test_file_name)
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


if __name__ == '__main__':
    unittest.main()
