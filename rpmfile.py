#!/usr/bin/env python

import struct
import sys

RPM_MAGIC = 0xedabeedb
RPM_VER_MIN = (3, 0)

RPM_HEADER_HEADER_MAGIC = 0x8eade8

OLD_STYLE_HEADER_SIZE = 96

RPMSENSE_ANY = 0
RPMSENSE_LESS = 1 << 1
RPMSENSE_GREATER = 1 << 2
RPMSENSE_EQUAL = 1 << 3
RPMSENSE_SENSEMASK = 0x0e
RPMSENSE_NOTEQUAL = RPMSENSE_EQUAL ^ RPMSENSE_SENSEMASK

RPMSENSE_PROVIDES = (1 << 4)
RPMSENSE_CONFLICTS = (1 << 5)
RPMSENSE_OBSOLETES = (1 << 7)
RPMSENSE_INTERP = (1 << 8),
RPMSENSE_SCRIPT_PRE = ((1 << 9) | RPMSENSE_ANY)
RPMSENSE_SCRIPT_POST = ((1 << 10) | RPMSENSE_ANY)
RPMSENSE_SCRIPT_PREUN = ((1 << 11) | RPMSENSE_ANY)
RPMSENSE_SCRIPT_POSTUN = ((1 << 12) | RPMSENSE_ANY)
RPMSENSE_SCRIPT_VERIFY = (1 << 13)
RPMSENSE_FIND_REQUIRES = (1 << 14)
RPMSENSE_FIND_PROVIDES = (1 << 15)
RPMSENSE_TRIGGERIN = (1 << 16)
RPMSENSE_TRIGGERUN = (1 << 17)
RPMSENSE_TRIGGERPOSTUN = (1 << 18)
RPMSENSE_MISSINGOK = (1 << 19)
RPMSENSE_SCRIPT_PREP = (1 << 20)
RPMSENSE_SCRIPT_BUILD = (1 << 21)
RPMSENSE_SCRIPT_INSTALL = (1 << 22)
RPMSENSE_SCRIPT_CLEAN = (1 << 23)
RPMSENSE_RPMLIB = ((1 << 24) | RPMSENSE_ANY)
RPMSENSE_TRIGGERPREIN = (1 << 25)
RPMSENSE_KEYRING = (1 << 26)
RPMSENSE_PATCHES = (1 << 27)
RPMSENSE_CONFIG = (1 << 28)


def flags_to_str(flags):
    flags = flags & 0x0e

    if flags == RPMSENSE_NOTEQUAL:
        return "NE"
    elif flags == RPMSENSE_EQUAL:
        return "EQ"
    elif flags & RPMSENSE_LESS:
        return "LT"
    elif flags & RPMSENSE_GREATER:
        return "GT"
    elif flags & (RPMSENSE_LESS | RPMSENSE_EQUAL):
        return "LE"
    elif flags & (RPMSENSE_GREATER | RPMSENSE_EQUAL):
        return "GE"
    elif flags == 0:
        return None
    else:
        raise RuntimeError("Unknown flags: %d" % flags)


SIGNATURE_TAG_TABLE = {
    1000: "SIG_SIZE",
    1001: "LEMD5_1",
    1002: "PGP",
    1003: "LEMD5_2",
    1004: "MD5",
    1005: "GPG",
    1006: "PGP5",
    1007: "PAYLOADSIZE",
    264: "BADSHA1_1",
    265: "BADSHA1_2",
    269: "SHA1",
    267: "DSA",
    268: "RSA",
    270: "SIG_LONGSIZE",
    271: "SIG_LONGARCHIVESIZE"
}

HEADER_TAG_TABLE = {
    61: "HEADERIMAGE",
    62: "HEADERSIGNATURES",
    63: "HEADERIMMUTABLE",
    64: "HEADERREGIONS",
    100: "HEADERI18NTABLE",
    256: "SIG_BASE",
    257: "SIGSIZE",
    258: "SIGLEMD5_1",
    259: "SIGPGP",
    260: "SIGLEMD5_2",
    261: "SIGMD5",
    262: "SIGGPG",
    263: "SIGPGP5",
    264: "BADSHA1_1",
    265: "BADSHA1_2",
    266: "PUBKEYS",
    267: "DSAHEADER",
    268: "RSAHEADER",
    269: "SHA1HEADER",
    270: "LONGSIGSIZE",
    271: "LONGARCHIVESIZE",
    1000: "NAME",
    1001: "VERSION",
    1002: "RELEASE",
    1003: "EPOCH",
    1004: "SUMMARY",
    1005: "DESCRIPTION",
    1006: "BUILDTIME",
    1007: "BUILDHOST",
    1008: "INSTALLTIME",
    1009: "SIZE",
    1010: "DISTRIBUTION",
    1011: "VENDOR",
    1012: "GIF",
    1013: "XPM",
    1014: "LICENSE",
    1015: "PACKAGER",
    1016: "GROUP",
    1017: "CHANGELOG",
    1018: "SOURCE",
    1019: "PATCH",
    1020: "URL",
    1021: "OS",
    1022: "ARCH",
    1023: "PREIN",
    1024: "POSTIN",
    1025: "PREUN",
    1026: "POSTUN",
    1027: "OLDFILENAMES",
    1028: "FILESIZES",
    1029: "FILESTATES",
    1030: "FILEMODES",
    1031: "FILEUIDS",
    1032: "FILEGIDS",
    1033: "FILERDEVS",
    1034: "FILEMTIMES",
    1035: "FILEDIGESTS",
    1036: "FILELINKTOS",
    1037: "FILEFLAGS",
    1038: "ROOT",
    1039: "FILEUSERNAME",
    1040: "FILEGROUPNAME",
    1041: "EXCLUDE",
    1042: "EXCLUSIVE",
    1043: "ICON",
    1044: "SOURCERPM",
    1045: "FILEVERIFYFLAGS",
    1046: "ARCHIVESIZE",
    1047: "PROVIDENAME",
    1048: "REQUIREFLAGS",
    1049: "REQUIRENAME",
    1050: "REQUIREVERSION",
    1051: "NOSOURCE",
    1052: "NOPATCH",
    1053: "CONFLICTFLAGS",
    1054: "CONFLICTNAME",
    1055: "CONFLICTVERSION",
    1056: "DEFAULTPREFIX",
    1057: "BUILDROOT",
    1058: "INSTALLPREFIX",
    1059: "EXCLUDEARCH",
    1060: "EXCLUDEOS",
    1061: "EXCLUSIVEARCH",
    1062: "EXCLUSIVEOS",
    1063: "AUTOREQPROV",
    1064: "RPMVERSION",
    1065: "TRIGGERSCRIPTS",
    1066: "TRIGGERNAME",
    1067: "TRIGGERVERSION",
    1068: "TRIGGERFLAGS",
    1069: "TRIGGERINDEX",
    1079: "VERIFYSCRIPT",
    1080: "CHANGELOGTIME",
    1081: "CHANGELOGNAME",
    1082: "CHANGELOGTEXT",
    1083: "BROKENMD5",
    1084: "PREREQ",
    1085: "PREINPROG",
    1086: "POSTINPROG",
    1087: "PREUNPROG",
    1088: "POSTUNPROG",
    1089: "BUILDARCHS",
    1090: "OBSOLETENAME",
    1091: "VERIFYSCRIPTPROG",
    1092: "TRIGGERSCRIPTPROG",
    1093: "DOCDIR",
    1094: "COOKIE",
    1095: "FILEDEVICES",
    1096: "FILEINODES",
    1097: "FILELANGS",
    1098: "PREFIXES",
    1099: "INSTPREFIXES",
    1100: "TRIGGERIN",
    1101: "TRIGGERUN",
    1102: "TRIGGERPOSTUN",
    1103: "AUTOREQ",
    1104: "AUTOPROV",
    1105: "CAPABILITY",
    1106: "SOURCEPACKAGE",
    1107: "OLDORIGFILENAMES",
    1108: "BUILDPREREQ",
    1109: "BUILDREQUIRES",
    1110: "BUILDCONFLICTS",
    1111: "BUILDMACROS",
    1112: "PROVIDEFLAGS",
    1113: "PROVIDEVERSION",
    1114: "OBSOLETEFLAGS",
    1115: "OBSOLETEVERSION",
    1116: "DIRINDEXES",
    1117: "BASENAMES",
    1118: "DIRNAMES",
    1119: "ORIGDIRINDEXES",
    1120: "ORIGBASENAMES",
    1121: "ORIGDIRNAMES",
    1122: "OPTFLAGS",
    1123: "DISTURL",
    1124: "PAYLOADFORMAT",
    1125: "PAYLOADCOMPRESSOR",
    1126: "PAYLOADFLAGS",
    1127: "INSTALLCOLOR",
    1128: "INSTALLTID",
    1129: "REMOVETID",
    1130: "SHA1RHN",
    1131: "RHNPLATFORM",
    1132: "PLATFORM",
    1133: "PATCHESNAME",
    1134: "PATCHESFLAGS",
    1135: "PATCHESVERSION",
    1136: "CACHECTIME",
    1137: "CACHEPKGPATH",
    1138: "CACHEPKGSIZE",
    1139: "CACHEPKGMTIME",
    1140: "FILECOLORS",
    1141: "FILECLASS",
    1142: "CLASSDICT",
    1143: "FILEDEPENDSX",
    1144: "FILEDEPENDSN",
    1145: "DEPENDSDICT",
    1146: "SOURCEPKGID",
    1147: "FILECONTEXTS",
    1148: "rpm/rpmtag.h",
    1149: "RECONTEXTS",
    1150: "POLICIES",
    1151: "PRETRANS",
    1152: "POSTTRANS",
    1153: "PRETRANSPROG",
    1154: "rpm/rpmtag.h",
    1155: "DISTTAG",
    1156: "SUGGESTSNAME",
    1157: "SUGGESTSVERSION",
    1158: "SUGGESTSFLAGS",
    1159: "ENHANCESNAME",
    1160: "ENHANCESVERSION",
    1161: "ENHANCESFLAGS",
    1162: "PRIORITY",
    1163: "CVSID",
    1164: "BLINKPKGID",
    1165: "BLINKHDRID",
    1166: "BLINKNEVRA",
    1167: "FLINKPKGID",
    1168: "FLINKHDRID",
    1169: "FLINKNEVRA",
    1170: "PACKAGEORIGIN",
    1171: "TRIGGERPREIN",
    1172: "BUILDSUGGESTS",
    1173: "BUILDENHANCES",
    1174: "SCRIPTSTATES",
    1175: "SCRIPTMETRICS",
    1176: "BUILDCPUCLOCK",
    1177: "FILEDIGESTALGOS",
    1178: "VARIANTS",
    1179: "XMAJOR",
    1180: "XMINOR",
    1181: "REPOTAG",
    1182: "KEYWORDS",
    1183: "BUILDPLATFORMS",
    1184: "PACKAGECOLOR",
    1185: "PACKAGEPREFCOLOR",
    1186: "XATTRSDICT",
    1187: "FILEXATTRSX",
    1188: "DEPATTRSDICT",
    1189: "CONFLICTATTRSX",
    1190: "OBSOLETEATTRSX",
    1191: "PROVIDEATTRSX",
    1192: "REQUIREATTRSX",
    1193: "BUILDPROVIDES",
    1194: "BUILDOBSOLETES",
    1195: "DBINSTANCE",
    1196: "NVRA",
    5000: "FILENAMES",
    5001: "FILEPROVIDE",
    5002: "FILEREQUIRE",
    5003: "FSNAMES",
    5004: "FSSIZES",
    5005: "TRIGGERCONDS",
    5006: "TRIGGERTYPE",
    5007: "ORIGFILENAMES",
    5008: "LONGFILESIZES",
    5009: "LONGSIZE",
    5010: "FILECAPS",
    5011: "FILEDIGESTALGO",
    5012: "BUGURL",
    5013: "EVR",
    5014: "NVR",
    5015: "NEVR",
    5016: "NEVRA",
    5017: "HEADERCOLOR",
    5018: "VERBOSE",
    5019: "EPOCHNUM",
    5020: "PREINFLAGS",
    5021: "POSTINFLAGS",
    5022: "PREUNFLAGS",
    5023: "POSTUNFLAGS",
    5024: "PRETRANSFLAGS",
    5025: "POSTTRANSFLAGS",
    5026: "VERIFYSCRIPTFLAGS",
    5027: "TRIGGERSCRIPTFLAGS",
    5029: "COLLECTIONS",
    5030: "POLICYNAMES",
    5031: "POLICYTYPES",
    5032: "POLICYTYPESINDEXES",
    5033: "POLICYFLAGS",
    5034: "VCS",
    5035: "ORDERNAME",
    5036: "ORDERVERSION",
    5037: "ORDERFLAGS",
    5038: "MSSFMANIFEST",
    5039: "MSSFDOMAIN",
    5040: "INSTFILENAMES",
    5041: "REQUIRENEVRS",
    5042: "PROVIDENEVRS",
    5043: "OBSOLETENEVRS",
    5044: "CONFLICTNEVRS",
    5045: "FILENLINKS"
}


class RpmInfo(object):

    def _read_header_header(self, f):
        magic = struct.unpack('>I', b'\x00' + f.read(3))[0]
        if magic != RPM_HEADER_HEADER_MAGIC:
            raise RuntimeError("Wrong header header magic: '%s'" % hex(magic))

        ver, reserved, num_index_entries, num_data_bytes = \
            struct.unpack('>BIII', f.read(13))

        return num_index_entries, num_data_bytes

    def _read_index_entry(self, f):
        tag, type, offset, count = \
            struct.unpack('>IIII', f.read(16))

        return tag, type, offset, count

    def _read_store(self, f, tag_table, index_entries, num_index_bytes):
        current_offset = f.tell()

        result = {}

        for entry in index_entries:
            tag, type, offset, count = entry
            f.seek(current_offset + offset)

            value = None
            if type == 0:
                pass
            elif type == 1:
                value = []
                for _ in range(count):
                    value.append(struct.unpack('>c', f.read(1))[0])
                if len(value) == 1:
                    value = value[0]
            elif type == 2:
                value = []
                for _ in range(count):
                    value.append(struct.unpack('>b', f.read(1))[0])
                if len(value) == 1:
                    value = value[0]
            elif type == 3:
                value = []
                for _ in range(count):
                    value.append(struct.unpack('>h', f.read(2))[0])
                if len(value) == 1:
                    value = value[0]
            elif type == 4:
                value = []
                for _ in range(count):
                    value.append(struct.unpack('>I', f.read(4))[0])
                if len(value) == 1:
                    value = value[0]
            elif type == 5:
                value = []
                for _ in range(count):
                    value.append(struct.unpack('>q', f.read(8))[0])
                if len(value) == 1:
                    value = value[0]
            elif type == 6:
                char = None
                string = b''
                while True:
                    char = f.read(1)
                    if char == b'\x00':
                        break
                    string += char
                value = string
            elif type == 7:
                value = struct.unpack('>%ds' % count, f.read(count))[0]
            elif type == 8:
                stringlist = []
                for i in range(count):
                    char = None
                    string = b''
                    while True:
                        char = f.read(1)
                        if char == b'\x00':
                            break
                        string += char
                    stringlist.append(string)
                value = stringlist

            if tag in tag_table:
                result[tag_table[tag]] = value

        addr = current_offset + num_index_bytes
        # align to 8-byte boundary
        addr = (addr + (8 - 1)) & -8
        f.seek(addr)
        return result

    def parse_header(self, f, tag_table):
        num_index_entries, num_index_bytes = self._read_header_header(f)

        index_entries = []
        for i in range(num_index_entries):
            index_entries.append(
                self._read_index_entry(f))

        data = self._read_store(f, tag_table, index_entries, num_index_bytes)

        return data

    def parse_file(self, filename):
        with open(filename, 'rb') as f:
            magic = struct.unpack('>I', f.read(4))[0]
            if magic != RPM_MAGIC:
                raise RuntimeError("Not an RPM file: '%s'" % filename)

            ver_major, ver_minor = struct.unpack('>BB', f.read(2))

            if (ver_major, ver_minor) < RPM_VER_MIN:
                raise RuntimeError(("RPM file version '%d.%d' is less than " +
                                    "minimum supported version '%d.%d'") %
                                   ((ver_major, ver_minor) + RPM_VER_MIN))

            f.seek(OLD_STYLE_HEADER_SIZE)  # size of old-style header

            signature = self.parse_header(f, SIGNATURE_TAG_TABLE)

            self.header_start = f.tell()
            header = self.parse_header(f, HEADER_TAG_TABLE)
            self.header_end = f.tell()

            header.update(signature)
            return header


def main():
    i = RpmInfo()
    data = i.parse_file(sys.argv[1])
    for key, value in data.items():
        print("%s: %s" % (key, str(value)))


if __name__ == '__main__':
    main()
