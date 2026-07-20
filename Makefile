.PHONY: all build build-aarch64 test test-core test-prg test-sanitize export export-aarch64 verify verify-aarch64 install-user apk apk-existing apk-verify web-install check sync-native sync-native-check clean

NATIVE_ACTION_ROOT ?= ../action/actionc64u

ACTIVE_TESTS = \
	tests.test_linux_workspace_tools \
	tests.test_action_help \
	tests.test_code_map \
	tests.test_profiler_target \
	tests.test_idun_fork_layout \
	tests.test_idun_workspace_export \
	tests.test_alpine_packaging \
	tests.test_shared_6502_sync \
	tests.test_action_source_scan \
	tests.test_vice_smoke

PRG_TESTS = \
	tests.test_idun_prg_runtime \
	tests.test_native_suite_compatibility

all: build test export verify

build:
	bash tools/build_linux_tools.sh

build-aarch64:
	bash tools/build_linux_tools_aarch64.sh

test: build
	ACTION_FORCE_REBUILD=0 python3 -m unittest -v $(ACTIVE_TESTS)

test-core: build
	ACTION_FORCE_REBUILD=0 python3 -m unittest -v $(ACTIVE_TESTS)

test-prg: build
	ACTION_FORCE_REBUILD=0 python3 -m unittest -v $(PRG_TESTS)

test-sanitize:
	bash tools/test_linux_tools_sanitized.sh

export: build
	ACTION_FORCE_REBUILD=0 python3 tools/export_idun_workspace.py

export-aarch64: build-aarch64
	python3 tools/export_idun_workspace.py --output build/idun-action-aarch64 --tools-source build/linux_tools-aarch64

verify: export
	python3 tools/verify_idun_artifacts.py

verify-aarch64: export-aarch64
	python3 tools/verify_idun_artifacts.py --build-tools build/linux_tools-aarch64 --export build/idun-action-aarch64

install-user: export
	bash tools/install_linux_tools.sh --tools build/idun-action/TOOLS

apk:
	bash tools/build_alpine_packages.sh

apk-existing:
	bash tools/build_alpine_packages.sh --use-existing-export

apk-verify:
	bash tools/verify_alpine_repository.sh

web-install:
	bash tools/install_apk_web_server.sh

check:
	bash tools/env_check.sh --strict
	python3 tools/path_probe.py

sync-native:
	python3 tools/shared_6502_sync.py --sync-from $(NATIVE_ACTION_ROOT)

sync-native-check:
	python3 tools/shared_6502_sync.py --check-peer $(NATIVE_ACTION_ROOT)

clean:
	python3 tools/clean_build.py
