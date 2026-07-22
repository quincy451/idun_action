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
    cd /workspace
    export CHOST=aarch64-alpine-linux-musl
    export PACKAGER="ActionC64U Idun package builder"
    export PACKAGER_PRIVKEY=/keys/idun-action-apk.rsa
    abuild -d -P /packages -s /workspace
'
