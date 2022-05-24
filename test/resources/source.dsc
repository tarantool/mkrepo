-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: openssl
Binary: openssl, libssl1.1, libcrypto1.1-udeb, libssl1.1-udeb, libssl-dev, libssl-doc
Architecture: any all
Version: 1.1.1l-1ubuntu1.3
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Uploaders: Christoph Martin <christoph.martin@uni-mainz.de>, Kurt Roeckx <kurt@roeckx.be>, Sebastian Andrzej Siewior <sebastian@breakpoint.cc>
Homepage: https://www.openssl.org/
Standards-Version: 4.5.0
Vcs-Browser: https://salsa.debian.org/debian/openssl
Vcs-Git: https://salsa.debian.org/debian/openssl.git
Testsuite: autopkgtest
Build-Depends: debhelper-compat (= 12), m4, bc, dpkg-dev (>= 1.15.7)
Package-List:
 libcrypto1.1-udeb udeb debian-installer optional arch=any profile=!noudeb
 libssl-dev deb libdevel optional arch=any
 libssl-doc deb doc optional arch=all
 libssl1.1 deb libs optional arch=any
 libssl1.1-udeb udeb debian-installer optional arch=any profile=!noudeb
 openssl deb utils optional arch=any
Checksums-Sha1:
 f8819dd31642eebea6cc1fa5c256fc9a4f40809b 9834044 openssl_1.1.1l.orig.tar.gz
 1f13a8055c8c143a78e1f18aeae38b22cf3b18e4 488 openssl_1.1.1l.orig.tar.gz.asc
 a784c4a2da659876fc2ea3726ba0da8da5e2681e 149576 openssl_1.1.1l-1ubuntu1.3.debian.tar.xz
Checksums-Sha256:
 0b7a3e5e59c34827fe0c3a74b7ec8baef302b98fa80088d7f9153aa16fa76bd1 9834044 openssl_1.1.1l.orig.tar.gz
 e2ae0ea526223843245dd80224b19a55283f4910dd56b7ee7b23187164f69fda 488 openssl_1.1.1l.orig.tar.gz.asc
 5990f4604858033999b2f28dce460aaf93cef9c48129eb53934c437433ecb2bd 149576 openssl_1.1.1l-1ubuntu1.3.debian.tar.xz
Files:
 ac0d4387f3ba0ad741b0580dd45f6ff3 9834044 openssl_1.1.1l.orig.tar.gz
 dc5c52d7d1e7c2888351434789cdb89c 488 openssl_1.1.1l.orig.tar.gz.asc
 2caf1dee8c91060876169e20d63ac22b 149576 openssl_1.1.1l-1ubuntu1.3.debian.tar.xz
Original-Maintainer: Debian OpenSSL Team <pkg-openssl-devel@lists.alioth.debian.org>

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEUMSg3c8x5FLOsZtRZWnYVadEvpMFAmJxkfMACgkQZWnYVadE
vpMgGhAAuo14/iNvA+Oq36X7cx8M26uex2oSbIpIRtZtoM0xg+9b01tT9za0smHJ
bDkweGGkOK/cikWRM6Rr4F8ZgLURfRJfBAN2V9OGxOtLGO6JWD2wKrVMfeuUifdE
scE6uiNhG4xa/ZAMTLF1ohO2Loe0UUUc9J52IxULY2c2+rkvUgOHgF+nzCNAfejH
94UJQif6PcI6xT7C3Vl/aLJSPVSnCDU1zI94Jn/7+I71pOZRWBZ2MZgpdomMdU5h
hHo2vm93W779RpKkx0SI25LcC9HSp+iAh2xiRj9G+vKp08Pp6levZrag2lR5OrlE
aUkvU/XKV49unBZcqCZPuABihWeNdgaXnMxqClkLQPvyLd1mnJMq+LKNKEop/+cq
KNpC0Z5w/IQRV/B7Xg9K4mK24EZiiCS3EOT/MZ5A6WWGc0txgqye9wQweFQQVMtH
OaDk/6mUOjvuNRpNEb+jwuBogFjnQLn+aXOyFIOLRV6FAcxXtqo/3UgkC7Cwyw96
Aw1tPHjMrO2+vY2UCG/oVc5at3St2DDjwqnavTACvzmyCEJPkoRll5n/jKFL7N8z
MEJgpPEnVOJ5ek9aovsRafJKIL9BkWAWbNsze8Fk4VPFC48/fcb0NSQhBUSnNBlo
D0Q8QMKABH6ZCCDpOIlh6831sV8miyds08lvTFigQNfO75ihxx0=
=Ue1f
-----END PGP SIGNATURE-----
