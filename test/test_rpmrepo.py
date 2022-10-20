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

    def test_dump_primary(self):
        primary = {
            ('tarantool-lrexlib-pcre', '0', '1.el7.centos', '2.9.0.5'): {
                'checksum': '69743803d280e7e92165bb7b1926330cf8041cae56ab83f2f07bb35485e81a30',
                'name': 'tarantool-lrexlib-pcre',
                'arch': 'x86_64',
                'version': {'ver': '2.9.0.5', 'rel': '1.el7.centos', 'epoch': '0'},
                'summary': None,
                'description': None,
                'packager': None,
                'url': 'https://github.com/tarantool/lrexlib',
                'file_time': '1655216309',
                'build_time': 1541643049,
                'package_size': 20780,
                'installed_size': 42856,
                'archive_size': 43124,
                'location': 'Packages/tarantool-lrexlib-pcre-2.9.0.5-1.el7.centos.x86_64.rpm',
                'format': {
                    'license': 'MIT',
                    'vendor': None,
                    'group': None,
                    'buildhost': '5d6663a7b0f9',
                    'sourcerpm': 'tarantool-lrexlib-2.9.0.5-1.el7.centos.src.rpm',
                    'header_start': 280,
                    'header_end': 6104,
                    'provides': {
                        ('tarantool-lrexlib-pcre', '0', None, '2.9.0.5'): {
                            'name': 'tarantool-lrexlib-pcre', 'epoch': '0', 'rel': None,
                            'ver': '2.9.0.5', 'flags': 'EQ'},
                        ('tarantool-lrexlib-pcre', '0', '1.el7.centos', '2.9.0.5'): {
                            'name': 'tarantool-lrexlib-pcre', 'epoch': '0', 'rel': '1.el7.centos',
                            'ver': '2.9.0.5', 'flags': 'EQ'},
                        ('tarantool-lrexlib-pcre(x86-64)', '0', '1.el7.centos', '2.9.0.5'): {
                            'name': 'tarantool-lrexlib-pcre(x86-64)', 'epoch': '0',
                            'rel': '1.el7.centos', 'ver': '2.9.0.5', 'flags': 'EQ'}
                    },
                    'requires': {
                        ('libc.so.6()(64bit)', None, None, None): {
                            'name': 'libc.so.6()(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libc.so.6(GLIBC_2.14)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.14)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libc.so.6(GLIBC_2.2.5)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.2.5)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libc.so.6(GLIBC_2.3)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.3)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libc.so.6(GLIBC_2.3.4)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.3.4)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libc.so.6(GLIBC_2.4)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.4)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('libpcre.so.1()(64bit)', None, None, None): {
                            'name': 'libpcre.so.1()(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('pcre', None, None, None): {
                            'name': 'pcre', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('rtld(GNU_HASH)', None, None, None): {
                            'name': 'rtld(GNU_HASH)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None},
                        ('tarantool', '0', None, '1.9.0.0'): {
                            'name': 'tarantool', 'epoch': '0',
                            'rel': None, 'ver': '1.9.0.0', 'flags': 'GT', 'pre': None}
                    },
                    'obsoletes': {},
                    'conflicts': {},
                    'files': [
                        {'name': '/usr/lib64/tarantool/rex_pcre.so', 'type': 'file'},
                        {'name': '/usr/lib64/tarantool/', 'type': 'dir'}
                    ]
                }
            }
        }
        primary_str = """<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" \
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="1">
<package type="rpm">
  <name>tarantool-lrexlib-pcre</name>
  <arch>x86_64</arch>
  <version epoch="0" ver="2.9.0.5" rel="1.el7.centos"/>
  <checksum type="sha256" \
pkgid="YES">69743803d280e7e92165bb7b1926330cf8041cae56ab83f2f07bb35485e81a30</checksum>
  <summary></summary>
  <description></description>
  <packager></packager>
  <url>https://github.com/tarantool/lrexlib</url>
  <time file="1655216309" build="1541643049"/>
  <size package="20780" installed="42856" archive="43124"/>
  <location href="Packages/tarantool-lrexlib-pcre-2.9.0.5-1.el7.centos.x86_64.rpm"/>
  <format>
    <rpm:license>MIT</rpm:license>
    <rpm:group></rpm:group>
    <rpm:buildhost>5d6663a7b0f9</rpm:buildhost>
    <rpm:sourcerpm>tarantool-lrexlib-2.9.0.5-1.el7.centos.src.rpm</rpm:sourcerpm>
    <rpm:header-range start="280" end="6104"/>
    <rpm:provides>
      <rpm:entry name="tarantool-lrexlib-pcre" flags="EQ" epoch="0" ver="2.9.0.5"/>
      <rpm:entry name="tarantool-lrexlib-pcre" flags="EQ" epoch="0" ver="2.9.0.5" \
rel="1.el7.centos"/>
      <rpm:entry name="tarantool-lrexlib-pcre(x86-64)" flags="EQ" epoch="0" ver="2.9.0.5" \
rel="1.el7.centos"/>
    </rpm:provides>
    <rpm:requires>
      <rpm:entry name="libc.so.6(GLIBC_2.14)(64bit)"/>
      <rpm:entry name="libpcre.so.1()(64bit)"/>
      <rpm:entry name="pcre"/>
      <rpm:entry name="rtld(GNU_HASH)"/>
      <rpm:entry name="tarantool" flags="GT" epoch="0" ver="1.9.0.0"/>
    </rpm:requires>
    <rpm:obsoletes>
    </rpm:obsoletes>
  </format>
</package>
</metadata>
"""
        self.assertEqual(rpmrepo.dump_primary(primary), primary_str)

    def test_escape_xml_special_chars_in_primary_dump(self):
        primary = {
            ('python3-gevent', '0', '1.el7', '21.1.2'): {
                'name': 'python3-gevent',
                'arch': 'x86_64',
                'version': {'ver': '21.1.2', 'rel': '1.el7', 'epoch': '0'},
                'checksum': '3dbbd8920df527ebb4176d531e5ec1da43cd44d1359dd69cd102a0e75131f878',
                'summary': 'foo & bar',  # should be escaped
                'description': '<foo> and <bar>',  # should be escaped
                'packager': '<bar>&<foo>',  # should be escaped
                'url': 'http://www.gevent.org/',
                'file_time': '1661151589',
                'build_time': '1661158857',
                'package_size': '1797532',
                'installed_size': '7755119',
                'archive_size': '7920508',
                'location': 'Packages/python3-gevent-21.1.2-1.el7.x86_64.rpm',
                'format': {
                    'license': 'MIT & MIT',  # should be escaped
                    'vendor': 'Foo&Bar',  # should be escaped
                    'group': None,
                    'buildhost': 'd5420ea808fe',
                    'sourcerpm': 'python-gevent-21.1.2-1.el7.src.rpm',
                    'header_start': '4424',
                    'header_end': '147768',
                    'provides': {
                        ('python3-gevent', '0', '1.el7', '21.1.2'): {
                            'name': 'python3-gevent', 'epoch': '0', 'rel': '1.el7', 'ver': '21.1.2',
                            'flags': 'EQ'
                        },
                        ('python3-gevent(x86-64)', '0', '1.el7', '21.1.2'): {
                            'name': 'python3-gevent(x86-64)', 'epoch': '0', 'rel': '1.el7',
                            'ver': '21.1.2', 'flags': 'EQ'
                        },
                        ('python3.8dist(gevent)', '0', None, '21.1.2'): {
                            'name': 'python3.8dist(gevent)', 'epoch': '0', 'rel': None,
                            'ver': '21.1.2', 'flags': 'EQ'
                        },
                        ('python3dist(gevent)', '0', None, '21.1.2'): {
                            'name': 'python3dist(gevent)', 'epoch': '0', 'rel': None,
                            'ver': '21.1.2', 'flags': 'EQ'
                        }
                    },
                    'requires': {
                        # The '>' and '<' should be escaped.
                        ('(python3.8dist(greenlet) >= 0.4.17 with python3.8dist(greenlet) < 2)',
                         None, None, None): {
                            'name': '(python3.8dist(greenlet) >= 0.4.17 '
                                    'with python3.8dist(greenlet) < 2)',
                            'epoch': None, 'rel': None, 'ver': None, 'flags': None, 'pre': None
                        },
                        ('libc.so.6()(64bit)', None, None, None): {
                            'name': 'libc.so.6()(64bit)', 'epoch': None, 'rel': None, 'ver': None,
                            'flags': None, 'pre': None
                        },
                        ('libc.so.6(GLIBC_2.2.5)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.2.5)(64bit)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('libc.so.6(GLIBC_2.4)(64bit)', None, None, None): {
                            'name': 'libc.so.6(GLIBC_2.4)(64bit)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('libcares.so.2()(64bit)', None, None, None): {
                            'name': 'libcares.so.2()(64bit)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('libev.so.4()(64bit)', None, None, None): {
                            'name': 'libev.so.4()(64bit)', 'epoch': None, 'rel': None, 'ver': None,
                            'flags': None, 'pre': None
                        },
                        ('libpthread.so.0()(64bit)', None, None, None): {
                            'name': 'libpthread.so.0()(64bit)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('libpthread.so.0(GLIBC_2.2.5)(64bit)', None, None, None): {
                            'name': 'libpthread.so.0(GLIBC_2.2.5)(64bit)', 'epoch': None,
                            'rel': None, 'ver': None, 'flags': None, 'pre': None
                        },
                        ('python(abi)', '0', None, '3.8'): {
                            'name': 'python(abi)', 'epoch': '0', 'rel': None, 'ver': '3.8',
                            'flags': 'EQ', 'pre': None
                        },
                        ('python3-greenlet', '0', None, '0.4.17'): {
                            'name': 'python3-greenlet', 'epoch': '0', 'rel': None, 'ver': '0.4.17',
                            'flags': 'GT', 'pre': None
                        },
                        ('python3.8dist(setuptools)', None, None, None): {
                            'name': 'python3.8dist(setuptools)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('python3.8dist(zope.event)', None, None, None): {
                            'name': 'python3.8dist(zope.event)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('python3.8dist(zope.interface)', None, None, None): {
                            'name': 'python3.8dist(zope.interface)', 'epoch': None, 'rel': None,
                            'ver': None, 'flags': None, 'pre': None
                        },
                        ('rtld(GNU_HASH)', None, None, None): {
                            'name': 'rtld(GNU_HASH)', 'epoch': None, 'rel': None, 'ver': None,
                            'flags': None, 'pre': None
                        }
                    },
                    'obsoletes': {},
                    'conflicts': {},
                    'files': []
                }
            }
        }
        primary_str = """<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" \
xmlns:rpm="http://linux.duke.edu/metadata/rpm" packages="1">
<package type="rpm">
  <name>python3-gevent</name>
  <arch>x86_64</arch>
  <version epoch="0" ver="21.1.2" rel="1.el7"/>
  <checksum type="sha256" \
pkgid="YES">3dbbd8920df527ebb4176d531e5ec1da43cd44d1359dd69cd102a0e75131f878</checksum>
  <summary>foo &amp; bar</summary>
  <description>&lt;foo&gt; and &lt;bar&gt;</description>
  <packager>&lt;bar&gt;&amp;&lt;foo&gt;</packager>
  <url>http://www.gevent.org/</url>
  <time file="1661151589" build="1661158857"/>
  <size package="1797532" installed="7755119" archive="7920508"/>
  <location href="Packages/python3-gevent-21.1.2-1.el7.x86_64.rpm"/>
  <format>
    <rpm:license>MIT &amp; MIT</rpm:license>
    <rpm:vendor>Foo&amp;Bar</rpm:vendor>
    <rpm:group></rpm:group>
    <rpm:buildhost>d5420ea808fe</rpm:buildhost>
    <rpm:sourcerpm>python-gevent-21.1.2-1.el7.src.rpm</rpm:sourcerpm>
    <rpm:header-range start="4424" end="147768"/>
    <rpm:provides>
      <rpm:entry name="python3-gevent" flags="EQ" epoch="0" ver="21.1.2" rel="1.el7"/>
      <rpm:entry name="python3-gevent(x86-64)" flags="EQ" epoch="0" ver="21.1.2" rel="1.el7"/>
      <rpm:entry name="python3.8dist(gevent)" flags="EQ" epoch="0" ver="21.1.2"/>
      <rpm:entry name="python3dist(gevent)" flags="EQ" epoch="0" ver="21.1.2"/>
    </rpm:provides>
    <rpm:requires>
      <rpm:entry name="(python3.8dist(greenlet) &gt;= 0.4.17 with python3.8dist(greenlet) &lt; 2)"/>
      <rpm:entry name="libc.so.6(GLIBC_2.4)(64bit)"/>
      <rpm:entry name="libcares.so.2()(64bit)"/>
      <rpm:entry name="libev.so.4()(64bit)"/>
      <rpm:entry name="libpthread.so.0()(64bit)"/>
      <rpm:entry name="libpthread.so.0(GLIBC_2.2.5)(64bit)"/>
      <rpm:entry name="python(abi)" flags="EQ" epoch="0" ver="3.8"/>
      <rpm:entry name="python3-greenlet" flags="GT" epoch="0" ver="0.4.17"/>
      <rpm:entry name="python3.8dist(setuptools)"/>
      <rpm:entry name="python3.8dist(zope.event)"/>
      <rpm:entry name="python3.8dist(zope.interface)"/>
      <rpm:entry name="rtld(GNU_HASH)"/>
    </rpm:requires>
    <rpm:obsoletes>
    </rpm:obsoletes>
  </format>
</package>
</metadata>
"""
        self.assertEqual(rpmrepo.dump_primary(primary), primary_str)
