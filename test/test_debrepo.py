#!/usr/bin/env python3

import os
import unittest

import debrepo


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
        cur_dir = os.path.dirname(os.path.abspath(__file__))

        test_file_names = [
            'ubuntu_groovy_packages_main.txt',
            'ubuntu_groovy_packages_multiverse.txt',
            'ubuntu_groovy_packages_restricted.txt',
            'ubuntu_groovy_packages_universe.txt'
        ]

        for test_file_name in test_file_names:
            test_path = os.path.join(cur_dir, test_file_name)
            with open(test_path, 'r') as test_file:
                for package_name in test_file:
                    self.assertIsNotNone(debrepo.split_control_file_path(package_name, 'binary'),
                                         "Can't parse packagename: %s" % package_name)


if __name__ == '__main__':
    unittest.main()
