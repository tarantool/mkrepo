import unittest

from rpmrepo import header_to_other
from rpmrepo import dump_other


class TestOtherGeneration(unittest.TestCase):
    def test_other_header(self):
        """Method to check header function of other.xml.gz file.

        We need to examine this, because if it will fail, then everything
        will throw an error or generate file incorrectly.
        """
        sha_256_key = '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2'
        header = {
            'NAME': b'Test Package Header Other 1',
            'ARCH': b'aarch64',
            'EPOCH': 1,
            'RELEASE': b'10.el8_4',
            'VERSION': b'1.30.0',
            'CHANGELOGNAME': [b'Beniamino Galvani <bgalvani@redhat.com> - 1:1.30', ],
            'CHANGELOGTIME': [1626091200, ],
            'CHANGELOGTEXT': [b'- text line header other 1', ]
        }

        header_data = header_to_other(header, sha_256_key)
        expected_header_to_other = (
            ('Test Package Header Other 1', 1, '10.el8_4', '1.30.0'),
            {
                'pkgid': '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2',
                'name': 'Test Package Header Other 1',
                'arch': 'aarch64',
                'version': {
                    'ver': '1.30.0',
                    'rel': '10.el8_4',
                    'epoch': 1
                },
                'changelog': [{
                    'author': 'Beniamino Galvani &lt;bgalvani@redhat.com&gt; - 1:1.30',
                    'date': 1626091200,
                    'text': '- text line header other 1'
                }],
            }
        )

        self.assertEqual(header_data, expected_header_to_other)

    def test_dump_other(self):
        """Method that dumps data to generate other.xml file.

        We need to examine this to check if all data are stored
        as it should be.
        """
        expected_other_dump = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                          '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="1">\n' \
                          '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2" ' \
                          'name="Test Package Dump Other 1" arch="aarch64">\n' \
                          '  <version epoch="1" ver="1.30.0" rel="10.el8_4"/>\n' \
                          '  <changelog author="User1 <user1@mail.ru> - 1:1.30.0-10" ' \
                          'date="1626091200">- text line dump other 1</changelog>\n' \
                          '</package>\n' \
                          '</otherdata>'
        other_data = {
            ('Test Package Dump Other 1', 1, '10.el8_4', '1.30.0'): {
                'pkgid': '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2',
                'name': 'Test Package Dump Other 1',
                'arch': 'aarch64',
                'version': {
                    'ver': '1.30.0',
                    'rel': '10.el8_4',
                    'epoch': 1
                },
                'changelog': [
                    {
                        'author': 'User1 <user1@mail.ru> - 1:1.30.0-10',
                        'date': 1626091200,
                        'text': '- text line dump other 1'
                    },
                ]
            },
        }

        self.assertEqual(dump_other(other_data), expected_other_dump)

    def test_many_packages(self):
        """Method that dumps multiple packages.

        To check if everything is correctly generated.
        """
        expected_many_packages = '<?xml version="1.0" encoding="UTF-8"?>\n' \
                          '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="3">\n' \
                          '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2" ' \
                          'name="Test Many Packages 1" arch="aarch64">\n' \
                          '  <version epoch="1" ver="1.30.0" rel="10.el8_4"/>\n' \
                          '  <changelog author="User1 <user1@mail.ru> - 1:1.30.0-10" ' \
                          'date="1626091200">- text line many packages 1</changelog>\n' \
                          '</package>\n' \
                          '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d1" ' \
                          'name="Test Many Packages 2" arch="aarch64">\n' \
                          '  <version epoch="1" ver="1.29.0" rel="10.el8_4"/>\n' \
                          '  <changelog author="User2 <user2@mail.ru> - 1:1.29.0-10" ' \
                          'date="1626091180">- text line many packages 2</changelog>\n' \
                          '</package>\n' \
                          '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d0" ' \
                          'name="Test Many Packages 3" arch="aarch64">\n' \
                          '  <version epoch="1" ver="1.28.0" rel="10.el8_4"/>\n' \
                          '  <changelog author="User3 <user3@mail.ru> - 1:1.28.0-10" ' \
                          'date="1626091120">- text line many packages 3</changelog>\n' \
                          '</package>\n' \
                          '</otherdata>'

        dump_many_packages = {
            ('Test Many Packages 1', 1, '10.el8_4', '1.30.0'): {
                'pkgid': '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2',
                'name': 'Test Many Packages 1',
                'arch': 'aarch64',
                'version': {
                    'ver': '1.30.0',
                    'rel': '10.el8_4',
                    'epoch': 1
                },
                'changelog': [
                    {
                        'author': 'User1 <user1@mail.ru> - 1:1.30.0-10',
                        'date': 1626091200,
                        'text': '- text line many packages 1'
                    },
                ]
            },
            ('Test Many Packages 2', 1, '10.el8_4', '1.29.0'): {
                'pkgid': '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d1',
                'name': 'Test Many Packages 2',
                'arch': 'aarch64',
                'version': {
                    'ver': '1.29.0',
                    'rel': '10.el8_4',
                    'epoch': 1
                },
                'changelog': [
                    {
                        'author': 'User2 <user2@mail.ru> - 1:1.29.0-10',
                        'date': 1626091180,
                        'text': '- text line many packages 2'
                    },
                ]
            },
            ('Test Many Packages 3', 1, '10.el8_4', '1.28.0'): {
                'pkgid': '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d0',
                'name': 'Test Many Packages 3',
                'arch': 'aarch64',
                'version': {
                    'ver': '1.28.0',
                    'rel': '10.el8_4',
                    'epoch': 1
                },
                'changelog': [
                    {
                        'author': 'User3 <user3@mail.ru> - 1:1.28.0-10',
                        'date': 1626091120,
                        'text': '- text line many packages 3'
                    },
                ]
            },
        }

        self.assertEqual(dump_other(dump_many_packages), expected_many_packages)

if __name__ == '__main__':
    unittest.main()
