#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KEY_DIR="${ACTION_APK_KEY_DIR:-$ROOT_DIR/.apk-keys}"
PRIVATE_KEY="$KEY_DIR/idun-action-apk.rsa"
PUBLIC_KEY="$PRIVATE_KEY.pub"

usage() {
    printf '%s\n' \
        "Usage: bash tools/init_alpine_signing_key.sh" \
        "" \
        "Create the project APK repository RSA key if it does not exist." \
        "The private key is never overwritten and remains under .apk-keys/."
}

if [[ $# -gt 0 ]]; then
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
fi

command -v openssl >/dev/null 2>&1 || {
    echo "openssl is required to create the APK signing key" >&2
    exit 1
}

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [[ -f "$PUBLIC_KEY" && ! -f "$PRIVATE_KEY" ]]; then
    echo "Public key exists without its private key: $PUBLIC_KEY" >&2
    exit 1
fi

if [[ ! -f "$PRIVATE_KEY" ]]; then
    umask 077
    private_tmp="$(mktemp "$KEY_DIR/.idun-action-apk.rsa.XXXXXX")"
    public_tmp="$(mktemp "$KEY_DIR/.idun-action-apk.rsa.pub.XXXXXX")"
    trap 'rm -f "$private_tmp" "$public_tmp"' EXIT
    openssl genpkey \
        -algorithm RSA \
        -pkeyopt rsa_keygen_bits:4096 \
        -out "$private_tmp"
    openssl pkey -in "$private_tmp" -pubout -out "$public_tmp"
    chmod 600 "$private_tmp"
    chmod 644 "$public_tmp"
    mv "$private_tmp" "$PRIVATE_KEY"
    mv "$public_tmp" "$PUBLIC_KEY"
    trap - EXIT
elif [[ ! -f "$PUBLIC_KEY" ]]; then
    public_tmp="$(mktemp "$KEY_DIR/.idun-action-apk.rsa.pub.XXXXXX")"
    trap 'rm -f "$public_tmp"' EXIT
    openssl pkey -in "$PRIVATE_KEY" -pubout -out "$public_tmp"
    chmod 644 "$public_tmp"
    mv "$public_tmp" "$PUBLIC_KEY"
    trap - EXIT
fi

chmod 600 "$PRIVATE_KEY"
chmod 644 "$PUBLIC_KEY"
fingerprint="$(
    openssl pkey -pubin -in "$PUBLIC_KEY" -outform DER 2>/dev/null |
        sha256sum |
        awk '{print $1}'
)"
printf 'private_key=%s\n' "$PRIVATE_KEY"
printf 'public_key=%s\n' "$PUBLIC_KEY"
printf 'sha256_fingerprint=%s\n' "$fingerprint"
