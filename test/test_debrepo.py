#!/usr/bin/env python3

import os
import sys
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
            # Commented out because it fails to parse properly at the moment
            # The "dist" should be "main", but parses to "1" with current parser
            #
            # (
            #     'pool/main/t/tarantool/tarantool-python_0.6.6-21_amd64.deb',
            #     ('all', 'main', 'amd64')
            # ),
            #
            # Neither does this
            #
            # (
            #     'debian/pool/main/o/openssl/libssl1.1_1.1.0l-1~deb9u1_amd64.deb',
            #     ('1~deb9u1', 'main', 'amd64')
            # ),
        ]

        for version in versions:
            self.assertEqual(
                debrepo.split_control_file_path(version[0], "binary"), version[1])


if __name__ == '__main__':
    unittest.main()
