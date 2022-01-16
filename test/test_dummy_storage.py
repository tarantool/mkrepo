import unittest

from dummy_storage import DummyStorage


class TestDummyStorage(unittest.TestCase):
    def test_base_functionality(self):
        """Tests the basic functionality of DummyStorage."""
        storage = DummyStorage()
        test_data = 'Test data'
        test_file = 'test/test_file.txt'

        storage.write_file(test_file, test_data.encode('utf-8'))
        self.assertTrue(storage.exists(test_file), 'Check of "write_file" failed.')
        self.assertTrue(isinstance(storage.mtime(test_file), float),
                        'Check of "mtime" failed.')

        read_res = storage.read_file(test_file).decode('utf-8')
        self.assertEqual(test_data, read_res, 'Check of "read_file" failed.')

        download_file = 'download/download_file.txt'
        storage.download_file(test_file, download_file)
        self.assertEqual(storage.read_file(test_file),
                         storage.read_file(download_file),
                         'Check of "download_file" failed.')

        upload_file = 'upload/upload_file.txt'
        storage.upload_file(upload_file, test_file)
        self.assertEqual(storage.read_file(test_file),
                         storage.read_file(upload_file),
                         'Check of "upload_file" failed.')

        storage.delete_file(test_file)
        self.assertFalse(storage.exists(test_file), 'Check of "delete_file" failed.')

        download_file_2 = 'download/download_file_2.txt'
        storage.download_file(download_file, download_file_2)
        download_files = []
        for file in storage.files('download'):
            download_files.append(file)
        self.assertTrue(download_file in download_files, 'Check of "files" failed.')
        self.assertTrue(download_file_2 in download_files, 'Check of "files" failed.')
