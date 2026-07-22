#!/bin/sh
set -eu

: "${HOST_UID:?HOST_UID is required}"
: "${HOST_GID:?HOST_GID is required}"

apk add --no-cache abuild
cp /keys/idun-action-apk.rsa.pub /etc/apk/keys/
addgroup -g "$HOST_GID" packager
adduser -D -h /home/packager -u "$HOST_UID" -G packager packager
addgroup packager abuild

su packager -c '
    set -eu
    cd /repository/aarch64
    apk index \
        --description "Idun Action Alpine 3.24 AArch64 repository" \
        --output APKINDEX.tar.gz \
        ./*.apk
    abuild-sign \
        -k /keys/idun-action-apk.rsa \
        -p idun-action-apk.rsa.pub \
        APKINDEX.tar.gz
    apk mkndx \
        --description "Idun Action Alpine 3.24 AArch64 repository" \
        --sign-key /keys/idun-action-apk.rsa \
        --output Packages.adb \
        ./*.apk
    sha256sum ./*.apk APKINDEX.tar.gz Packages.adb > SHA256SUMS
'
