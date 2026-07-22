#!/bin/sh
set -eu

: "${EXPECTED_COMMANDS:?EXPECTED_COMMANDS is required}"

apk verify --keys-dir /repository /repository/aarch64/*.apk
apk verify --keys-dir /repository /repository/aarch64/APKINDEX.tar.gz
apk verify --keys-dir /repository /repository/aarch64/Packages.adb

test_root=/tmp/idun-action-apk-root
mkdir -p "$test_root/etc/apk/keys"
cp /repository/idun-action-apk.rsa.pub "$test_root/etc/apk/keys/"
apk \
    --root "$test_root" \
    --arch aarch64 \
    --initdb \
    --keys-dir "$test_root/etc/apk/keys" \
    --repository /repository \
    --no-network \
    add idun_action_full

test -x "$test_root/usr/share/actionc64u/TOOLS/action-workspace-tools"
test -f "$test_root/usr/share/actionc64u/TOOLS/actsvc"
test -f "$test_root/usr/share/actionc64u/DOC/action-help.sqlite3"
test -f "$test_root/usr/share/actionc64u/LIB/GFX1.ACT"
test -f "$test_root/usr/share/actionc64u/workspace-template/ACTION.PROJ"
test -f "$test_root/usr/share/actionc64u/workspace-template/PLAYGROUND/HELLO.ACT"
test -x "$test_root/usr/bin/idun-action-new-workspace"

generated_workspace=/tmp/idun-action-generated-workspace
IDUN_ACTION_TEMPLATE="$test_root/usr/share/actionc64u/workspace-template" \
    "$test_root/usr/bin/idun-action-new-workspace" "$generated_workspace"
test -f "$generated_workspace/PLAYGROUND/HELLO.ACT"
if IDUN_ACTION_TEMPLATE="$test_root/usr/share/actionc64u/workspace-template" \
    "$test_root/usr/bin/idun-action-new-workspace" "$generated_workspace"; then
    echo "workspace helper replaced an existing destination" >&2
    exit 1
fi

command_count=0
for command in $EXPECTED_COMMANDS; do
    test -L "$test_root/usr/bin/$command"
    test "$(readlink "$test_root/usr/bin/$command")" = \
        "../share/actionc64u/TOOLS/$command"
    test -L "$test_root/usr/share/actionc64u/TOOLS/$command"
    test "$(readlink "$test_root/usr/share/actionc64u/TOOLS/$command")" = \
        action-workspace-tools
    command_count=$((command_count + 1))
done

test "$(sha256sum "$test_root/usr/share/actionc64u/TOOLS/action-workspace-tools" | awk '{print $1}')" = \
    "$(sha256sum /tools/action-workspace-tools | awk '{print $1}')"
test ! -e /repository/idun-action-apk.rsa
apk --root "$test_root" info -e idun_action
apk --root "$test_root" info -e idun_action_full

printf 'packages=2\n'
printf 'commands=%s\n' "$command_count"
printf 'workspace_helper=PASS\n'
printf 'alpine_repository=PASS\n'
