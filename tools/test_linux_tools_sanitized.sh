#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ORIGINAL_CXXFLAGS_SET=0
ORIGINAL_LDFLAGS_SET=0
ORIGINAL_CXXFLAGS="${CXXFLAGS-}"
ORIGINAL_LDFLAGS="${LDFLAGS-}"
[[ -v CXXFLAGS ]] && ORIGINAL_CXXFLAGS_SET=1
[[ -v LDFLAGS ]] && ORIGINAL_LDFLAGS_SET=1

restore_normal_build() {
    local status=$?
    trap - EXIT
    if (( ORIGINAL_CXXFLAGS_SET == 1 && ORIGINAL_LDFLAGS_SET == 1 )); then
        ACTION_FORCE_REBUILD=1 \
            CXXFLAGS="$ORIGINAL_CXXFLAGS" LDFLAGS="$ORIGINAL_LDFLAGS" \
            bash "$ROOT_DIR/tools/build_linux_tools.sh" >/dev/null
    elif (( ORIGINAL_CXXFLAGS_SET == 1 )); then
        env -u LDFLAGS ACTION_FORCE_REBUILD=1 CXXFLAGS="$ORIGINAL_CXXFLAGS" \
            bash "$ROOT_DIR/tools/build_linux_tools.sh" >/dev/null
    elif (( ORIGINAL_LDFLAGS_SET == 1 )); then
        env -u CXXFLAGS ACTION_FORCE_REBUILD=1 LDFLAGS="$ORIGINAL_LDFLAGS" \
            bash "$ROOT_DIR/tools/build_linux_tools.sh" >/dev/null
    else
        env -u CXXFLAGS -u LDFLAGS ACTION_FORCE_REBUILD=1 \
            bash "$ROOT_DIR/tools/build_linux_tools.sh" >/dev/null
    fi
    exit "$status"
}
trap restore_normal_build EXIT

# GCC 13 emits a known maybe-uninitialized false positive from libstdc++'s
# std::regex automaton at -O1; retain the warning without promoting that one
# system-header diagnostic to an error.
SANITIZER_FLAGS="-std=c++17 -Wall -Wextra -Werror -Wno-error=maybe-uninitialized -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined"
ACTION_FORCE_REBUILD=1 \
    CXXFLAGS="$SANITIZER_FLAGS" \
    LDFLAGS="-fsanitize=address,undefined" \
    bash "$ROOT_DIR/tools/build_linux_tools.sh" >/dev/null

ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:strict_string_checks=1" \
UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1" \
ACTION_FORCE_REBUILD=0 \
python3 -m unittest -v \
    tests.test_linux_workspace_tools \
    tests.test_action_help \
    tests.test_code_map \
    tests.test_profiler_target \
    tests.test_idun_fork_layout \
    tests.test_idun_workspace_export \
    tests.test_action_source_scan
