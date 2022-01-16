import unittest

from dummy_storage import DummyStorage

import rpmrepo


class TestRPMRepo(unittest.TestCase):
    def test_work_with_missing_metafiles(self):
        """The test checks the case when one (or more) files specified in "repomd"
        are absent.
        """
        repomd_data = ''
        repomd_data += '<?xml version="1.0" encoding="UTF-8"?>\n'
        repomd_data += ('<repomd xmlns="http://linux.duke.edu/metadata/repo" '
                        'xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n')
        repomd_data += '  <revision>1</revision>\n'
        repomd_data += '  <data type="filelists">\n'
        repomd_data += (
            '    <checksum type="sha256">'
            '7aaefa796605c6c6e0ca699ef5a3b1120207d291e47341dcae3fde824b368719'
            '</checksum>\n'
        )
        repomd_data += (
            '    <open-checksum type="sha256">'
            '74fed1d15e4bfe14aa354d8f91ea339bebc5e4a6bf748087807ef22a68e08d2c'
            '</open-checksum>\n'
        )
        repomd_data += '    <location href="repodata/filelists.xml.gz"/>\n'
        repomd_data += '    <timestamp>1633360840</timestamp>\n'
        repomd_data += '    <size>341</size>\n'
        repomd_data += '    <open-size>832</open-size>\n'
        repomd_data += '  </data>\n'
        repomd_data += '  <data type="primary">\n'
        repomd_data += (
            '    <checksum type="sha256">'
            'ab110cb17fefe3d6db446c5707c725c18ae086dd55ca82ea160912f821f58715'
            '</checksum>\n'
        )
        repomd_data += (
            '    <open-checksum type="sha256">'
            'b2387880960bca7f74937484dab6eff71d24090cff61739a88a01b5037fac4a8'
            '</open-checksum>\n'
        )
        repomd_data += '    <location href="repodata/primary.xml.gz"/>\n'
        repomd_data += '    <timestamp>1633360840</timestamp>\n'
        repomd_data += '    <size>641</size>\n'
        repomd_data += '    <open-size>1387</open-size>\n'
        repomd_data += '  </data>\n'
        repomd_data += '</repomd>\n'

        storage = DummyStorage()
        storage.write_file('repodata/repomd.xml', repomd_data.encode('utf-8'))

        (filelists, primary, others, revision,
         initial_filelists, initial_primary, initial_others) = rpmrepo.parse_metafiles(storage)
        self.assertEqual(filelists, {})
        self.assertEqual(primary, {})
        self.assertEqual(others, {})
        self.assertIsNone(initial_filelists)
        self.assertIsNone(initial_primary)
        self.assertIsNone(initial_others)

    def test_work_with_missing_information_about_metafiles(self):
        """The test checks the case when in "repomd" information about some metafiles
        are absent.
        """
        repomd_data = ''
        repomd_data += '<?xml version="1.0" encoding="UTF-8"?>\n'
        repomd_data += ('<repomd xmlns="http://linux.duke.edu/metadata/repo" '
                        'xmlns:rpm="http://linux.duke.edu/metadata/rpm">\n')
        repomd_data += '  <revision>1</revision>\n'
        repomd_data += '</repomd>\n'

        storage = DummyStorage()
        storage.write_file('repodata/repomd.xml', repomd_data.encode('utf-8'))

        (filelists, primary, others, revision,
         initial_filelists, initial_primary, initial_others) = rpmrepo.parse_metafiles(storage)
        self.assertEqual(filelists, {})
        self.assertEqual(primary, {})
        self.assertEqual(others, {})
        self.assertIsNone(initial_filelists)
        self.assertIsNone(initial_primary)
        self.assertIsNone(initial_others)
