from io import BytesIO
import time

from storage import Storage


class DummyStorage(Storage):
    """DummyStorage implements the "Storage" interface, that doesn't
    use the file system for use in tests.
    """
    def __init__(self):
        self.fs = {}

    def read_file(self, key):
        file = self.fs.get(key, None)
        if file is None:
            raise FileNotFoundError(2, 'No such file or directory:', key)
        return file['data'].getvalue()

    def write_file(self, key, data):
        buf = BytesIO()
        buf.write(data)
        buf.seek(0)
        self.fs[key] = {'data': buf, 'mtime': time.time()}

    def download_file(self, key, destination):
        if self.fs.get(key) is None:
            raise FileNotFoundError(2, 'No such file or directory:', key)
        source = self.fs[key]['data']
        dest = BytesIO()
        dest.write(source.getbuffer())
        self.fs[destination] = {'data': dest, 'mtime': time.time()}

    def upload_file(self, key, source):
        if self.fs.get(source) is None:
            raise FileNotFoundError(2, 'No such file or directory:', source)
        source = self.fs[source]['data']
        dest = BytesIO()
        dest.write(source.getbuffer())
        self.fs[key] = {'data': dest, 'mtime': time.time()}

    def delete_file(self, key):
        del self.fs[key]

    def mtime(self, key):
        return self.fs[key]['mtime']

    def exists(self, key):
        return bool(self.fs.get(key))

    def files(self, subdir=''):
        for key in self.fs:
            if key.startswith(subdir):
                yield key
