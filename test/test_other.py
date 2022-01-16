import unittest

from rpmrepo import dump_other
from rpmrepo import header_to_other


def expected_dump_simple():
    """Provide expected dump for one package."""

    expected_dump = ''
    expected_dump += '<?xml version="1.0" encoding="UTF-8"?>\n'
    expected_dump += '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="1">\n'
    expected_dump += '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2" '  # NOQA
    expected_dump += 'name="Test Package Dump Other 1" arch="aarch64">\n'
    expected_dump += '  <version epoch="1" ver="1.30.0" rel="10.el8_4"/>\n'
    expected_dump += '  <changelog author="User1 &lt;user1@mail.ru&gt; - 1:1.30.0-10" '
    expected_dump += 'date="1626091200">- text line dump other 1</changelog>\n'
    expected_dump += '</package>\n'
    expected_dump += '</otherdata>'

    return expected_dump


def other_data_simple():
    """Provide other data for one package."""

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

    return other_data


def expected_dump_complex():
    """Provide expected dump for several packages."""

    expected_dump = ''
    expected_dump += '<?xml version="1.0" encoding="UTF-8"?>\n'
    expected_dump += '<otherdata xmlns="http://linux.duke.edu/metadata/other" packages="3">\n'
    expected_dump += '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2" '  # NOQA
    expected_dump += 'name="Test Many Packages 1" arch="aarch64">\n'
    expected_dump += '  <version epoch="1" ver="1.30.0" rel="10.el8_4"/>\n'
    expected_dump += '  <changelog author="User1 &lt;user1@mail.ru&gt; - 1:1.30.0-10" '
    expected_dump += 'date="1626091200">- text line many packages 1</changelog>\n'
    expected_dump += '</package>\n'
    expected_dump += '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d1" '  # NOQA
    expected_dump += 'name="Test Many Packages 2" arch="aarch64">\n'
    expected_dump += '  <version epoch="1" ver="1.29.0" rel="10.el8_4"/>\n'
    expected_dump += '  <changelog author="User2 &lt;user2@mail.ru&gt; - 1:1.29.0-10" '
    expected_dump += 'date="1626091180">- text line many packages 2</changelog>\n'
    expected_dump += '</package>\n'
    expected_dump += '<package pkgid="9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d0" '  # NOQA
    expected_dump += 'name="Test Many Packages 3" arch="aarch64">\n'
    expected_dump += '  <version epoch="1" ver="1.28.0" rel="10.el8_4"/>\n'
    expected_dump += '  <changelog author="User3 &lt;user3@mail.ru&gt; - 1:1.28.0-10" '
    expected_dump += 'date="1626091120">- text line many packages 3</changelog>\n'
    expected_dump += '</package>\n'
    expected_dump += '</otherdata>'

    return expected_dump


def other_data_complex():
    """Provide other data for several packages."""

    other_data = {
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

    return other_data


class TestOtherGeneration(unittest.TestCase):

    dump_packages = {
        'One package case': (other_data_simple(), expected_dump_simple()),
        'Several packages case': (other_data_complex(), expected_dump_complex())
    }

    def test_header_to_other(self):
        """Check correctness of header_to_other function."""

        sha_256_key = '9a791d16574dc3408f495eb383b6c2669b34fc4545b3c43c8c791fbbe10619d2'
        header = {
            'NAME': b'Test Package Header Other 1',
            'SOURCERPM':b'tpho-0.0.1-1.fc34.src.rpm',
            'ARCH': b'aarch64',
            'EPOCH': 1,
            'RELEASE': b'10.el8_4',
            'VERSION': b'1.30.0',
            'CHANGELOGNAME': [
                b'Beniamino Galvani <bgalvani@redhat.com> - 1:1.30',
                b'Galvani Beniamino <galvanib@redhat.com> - 1:1.50'
            ],
            'CHANGELOGTIME': [1626091200, 1626091400],
            'CHANGELOGTEXT': [b'- text line header other 1', b'- text line header other 2']
        }

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
                'changelog': [
                    {
                        'author': 'Galvani Beniamino &lt;galvanib@redhat.com&gt; - 1:1.50',
                        'date': 1626091400,
                        'text': '- text line header other 2'
                    },
                    {
                        'author': 'Beniamino Galvani &lt;bgalvani@redhat.com&gt; - 1:1.30',
                        'date': 1626091200,
                        'text': '- text line header other 1'
                    }
                ],
            }
        )

        self.assertEqual(header_to_other(header, sha_256_key), expected_header_to_other)

    def test_dump_other(self):
        """Check dump_other in case of one package and several."""

        for name, (other_data, expected_dump) in self.dump_packages.items():
            with self.subTest(name=name):
                self.assertEqual(dump_other(other_data), expected_dump, name)


if __name__ == '__main__':
    unittest.main()
