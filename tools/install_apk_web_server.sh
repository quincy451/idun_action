#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPOSITORY="$ROOT_DIR/build/alpine-apk/repository"
PORT=8088
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"

usage() {
    printf '%s\n' \
        "Usage: bash tools/install_apk_web_server.sh [--port PORT]" \
        "" \
        "Install and configure lighttpd for the generated APK repository." \
        "Both lighttpd services are left stopped and disabled."
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            PORT=$2
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || {
    echo "--port must be an unprivileged TCP port from 1024 through 65535" >&2
    exit 2
}
command -v apt-get >/dev/null 2>&1 || {
    echo "This installer requires a Debian/Ubuntu/Mint host with apt-get" >&2
    exit 1
}
command -v sudo >/dev/null 2>&1 || {
    echo "sudo is required to install the web server" >&2
    exit 1
}

mkdir -p "$REPOSITORY"
config_tmp="$(mktemp)"
service_tmp="$(mktemp)"
trap 'rm -f "$config_tmp" "$service_tmp"' EXIT
sed \
    -e "s|@REPOSITORY@|$REPOSITORY|g" \
    -e "s|@PORT@|$PORT|g" \
    "$ROOT_DIR/packaging/web/lighttpd-idun-action.conf.in" > "$config_tmp"
sed \
    -e "s|@USER@|$RUN_USER|g" \
    -e "s|@GROUP@|$RUN_GROUP|g" \
    -e "s|@REPOSITORY@|$REPOSITORY|g" \
    -e "s|@KEY_DIR@|$ROOT_DIR/.apk-keys|g" \
    "$ROOT_DIR/packaging/web/idun-action-apk.service.in" > "$service_tmp"

# Mask the distribution service before package installation so apt cannot
# start it as a side effect. The dedicated service is created only afterward.
sudo systemctl stop lighttpd.service >/dev/null 2>&1 || true
sudo systemctl stop lighttpd-maint.timer >/dev/null 2>&1 || true
sudo systemctl mask lighttpd.service lighttpd-maint.timer >/dev/null
sudo apt-get install -y lighttpd
sudo systemctl stop lighttpd.service
sudo systemctl unmask lighttpd.service lighttpd-maint.timer >/dev/null
sudo systemctl disable lighttpd.service >/dev/null 2>&1 || true
sudo systemctl disable --now lighttpd-maint.timer >/dev/null 2>&1 || true
sudo systemctl stop lighttpd-maint.service >/dev/null 2>&1 || true

sudo install -m644 "$config_tmp" /etc/lighttpd/idun-action-apk.conf
sudo install -m644 "$service_tmp" /etc/systemd/system/idun-action-apk.service
sudo systemctl daemon-reload
sudo systemctl disable idun-action-apk.service >/dev/null 2>&1 || true
sudo systemctl stop idun-action-apk.service

/usr/sbin/lighttpd -tt -f /etc/lighttpd/idun-action-apk.conf
[[ "$(systemctl is-active lighttpd.service 2>/dev/null || true)" != active ]]
[[ "$(systemctl is-active idun-action-apk.service 2>/dev/null || true)" != active ]]
[[ "$(systemctl is-enabled lighttpd.service 2>/dev/null || true)" != enabled ]]
[[ "$(systemctl is-enabled idun-action-apk.service 2>/dev/null || true)" != enabled ]]
[[ "$(systemctl is-active lighttpd-maint.timer 2>/dev/null || true)" != active ]]
[[ "$(systemctl is-enabled lighttpd-maint.timer 2>/dev/null || true)" != enabled ]]

printf 'web_server=lighttpd\n'
printf 'repository=%s\n' "$REPOSITORY"
printf 'url=http://%s:%s/\n' "$(hostname -I | awk '{print $1}')" "$PORT"
printf 'service=idun-action-apk.service\n'
printf 'state=stopped-and-disabled\n'
