#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APK_ROOT="$ROOT_DIR/build/alpine-apk"
WORK_DIR="$APK_ROOT/work"
PACKAGES_DIR="$APK_ROOT/packages"
REPOSITORY="$APK_ROOT/repository"
KEY_DIR="${ACTION_APK_KEY_DIR:-$ROOT_DIR/.apk-keys}"
VERSION="$(tr -d '[:space:]' < "$ROOT_DIR/packaging/alpine/VERSION")"
PKGREL=0
SOURCE_DATE_EPOCH="$(git -C "$ROOT_DIR" log -1 --format=%ct 2>/dev/null || date -u +%s)"
USE_EXISTING_EXPORT=0
ALPINE_IMAGE="${ACTION_ALPINE_IMAGE:-alpine:3.24}"

usage() {
    printf '%s\n' \
        "Usage: bash tools/build_alpine_packages.sh [options]" \
        "" \
        "Build and sign idun_action and idun_action_full for Alpine/AArch64." \
        "" \
        "Options:" \
        "  --use-existing-export  Package the existing verified AArch64 export" \
        "  --version VERSION      Override packaging/alpine/VERSION" \
        "  --pkgrel NUMBER        Override the Alpine package release (default: 0)" \
        "  -h, --help             Show this help"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --use-existing-export)
            USE_EXISTING_EXPORT=1
            shift
            ;;
        --version)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            VERSION=$2
            shift 2
            ;;
        --pkgrel)
            [[ $# -ge 2 ]] || { usage >&2; exit 2; }
            PKGREL=$2
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

[[ "$PKGREL" =~ ^[0-9]+$ ]] || {
    echo "--pkgrel must be a non-negative integer" >&2
    exit 2
}
command -v docker >/dev/null 2>&1 || {
    echo "docker is required to build Alpine packages on Mint" >&2
    exit 1
}
(( $(id -u) > 0 && $(id -g) > 0 )) || {
    echo "Run the package builder as a normal user, not root" >&2
    exit 1
}

bash "$ROOT_DIR/tools/init_alpine_signing_key.sh"

if (( USE_EXISTING_EXPORT == 0 )); then
    make -C "$ROOT_DIR" verify-aarch64
else
    python3 "$ROOT_DIR/tools/verify_idun_artifacts.py" \
        --build-tools "$ROOT_DIR/build/linux_tools-aarch64" \
        --export "$ROOT_DIR/build/idun-action-aarch64"
fi

python3 "$ROOT_DIR/tools/prepare_alpine_package.py" \
    --export "$ROOT_DIR/build/idun-action-aarch64" \
    --tools-source "$ROOT_DIR/build/linux_tools-aarch64" \
    --work "$WORK_DIR" \
    --version "$VERSION" \
    --pkgrel "$PKGREL" \
    --source-date-epoch "$SOURCE_DATE_EPOCH"

rm -rf "$PACKAGES_DIR"
mkdir -p "$PACKAGES_DIR"
docker run --rm \
    --platform linux/amd64 \
    -e "HOST_UID=$(id -u)" \
    -e "HOST_GID=$(id -g)" \
    -v "$WORK_DIR:/workspace" \
    -v "$PACKAGES_DIR:/packages" \
    -v "$KEY_DIR:/keys:ro" \
    -v "$ROOT_DIR/packaging/alpine/container-build.sh:/container-build.sh:ro" \
    "$ALPINE_IMAGE" \
    /bin/sh /container-build.sh

mapfile -t built_packages < <(
    find "$PACKAGES_DIR" -type f \
        \( -name "idun_action-$VERSION-r$PKGREL.apk" \
        -o -name "idun_action_full-$VERSION-r$PKGREL.apk" \) \
        -print | sort
)
if [[ ${#built_packages[@]} -ne 2 ]]; then
    printf 'Expected exactly two APK files, found %d\n' "${#built_packages[@]}" >&2
    find "$PACKAGES_DIR" -type f -name '*.apk' -print >&2
    exit 1
fi

repository_tmp="$APK_ROOT/repository.tmp"
rm -rf "$repository_tmp"
mkdir -p "$repository_tmp/aarch64"
for package in "${built_packages[@]}"; do
    install -m644 "$package" "$repository_tmp/aarch64/"
done
install -m644 "$KEY_DIR/idun-action-apk.rsa.pub" "$repository_tmp/"

docker run --rm \
    --platform linux/amd64 \
    -e "HOST_UID=$(id -u)" \
    -e "HOST_GID=$(id -g)" \
    -v "$repository_tmp:/repository" \
    -v "$KEY_DIR:/keys:ro" \
    -v "$ROOT_DIR/packaging/alpine/container-index.sh:/container-index.sh:ro" \
    "$ALPINE_IMAGE" \
    /bin/sh /container-index.sh

EXPECTED_COMMANDS="$(
    PYTHONPATH="$ROOT_DIR/tools" python3 -c \
        'from export_idun_workspace import LINUX_TOOL_NAMES; print(" ".join(LINUX_TOOL_NAMES))'
)"
docker run --rm \
    --platform linux/amd64 \
    -e "EXPECTED_COMMANDS=$EXPECTED_COMMANDS" \
    -v "$repository_tmp:/repository:ro" \
    -v "$ROOT_DIR/build/linux_tools-aarch64:/tools:ro" \
    -v "$ROOT_DIR/packaging/alpine/container-verify.sh:/container-verify.sh:ro" \
    "$ALPINE_IMAGE" \
    /bin/sh /container-verify.sh

rm -rf "$REPOSITORY"
mv "$repository_tmp" "$REPOSITORY"
printf 'repository=%s\n' "$REPOSITORY"
printf 'public_key=%s\n' "$REPOSITORY/idun-action-apk.rsa.pub"
printf 'install_package=idun_action\n'
printf 'install_full_package=idun_action_full\n'
