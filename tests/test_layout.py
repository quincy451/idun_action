from pathlib import Path
import unittest


class TestRepoLayout(unittest.TestCase):
    def test_repo_layout_smoke(self) -> None:
        root = Path(__file__).resolve().parents[1]

        required = [
            "README.md",
            "LICENSE",
            ".gitignore",
            "AGENTS.md",
            "docs/inspiration/action.pdf",
            "docs/setup_wsl.md",
            "docs/architecture.md",
            "docs/active_direction.md",
            "src/runtime",
            "src/runtime/modules",
            "src/runtime/udos_modules",
            "src/tools_udos/actc",
            "src/tools_udos/alink/alink.asm",
            "src/tools_udos/alink/direct_prg.inc",
            "src/tools_udos/common",
            "src/tools_cpm/libmods",
            "src/tools_cpm/libmods/libpstr.mod",
            "src/tools_cpm/libmods/libplin.mod",
            "tools/object_format.py",
            "tools/vice_harness.py",
            "tools/export_udos_workspace.py",
            "tools/build_actc.sh",
            "tools/build_actc_udos.sh",
            "tools/build_alink_udos.sh",
            "tools/build_vmrun.sh",
            "tools/build_tool_abi_harness.sh",
            "tools/generate_udos_service_inc.py",
            "pytest/__main__.py",
            "examples/hello.act",
            "examples/if.act",
            "examples/math.act",
            "examples/real_demo.act",
            "examples/reu_demo.act",
            "examples/ovl_demo.act",
            "tests/test_actc_capacity.py",
            "tests/test_actc_overlay.py",
            "tests/test_layout.py",
            "tests/test_udos_workspace_export.py",
        ]

        legacy_ext = "a" + "vm"
        legacy_tool = legacy_ext
        removed_legacy_paths = [
            "src/vm",
            f"src/tools_udos/{legacy_tool}run",
            f"src/tools_udos/{legacy_tool}info",
            "src/tools_udos/actdbg",
            "src/tools_cpm/actc",
            "src/tools_cpm/alink",
            "src/tools_cpm/actmon",
            "tools/actionc64u_compile.py",
            "tools/actionc64u_link.py",
            f"tools/{legacy_tool}_pack.py",
            "tools/build_vmhello.sh",
            "tools/build_alink.sh",
            "tools/build_actmon.sh",
            "tools/install_to_image.py",
            "tools/verify_release.py",
            f"examples/hello.{legacy_ext}",
            f"examples/hello.{legacy_ext}.txt",
            f"examples/reu_runtime.{legacy_ext}.txt",
        ]

        missing = [path for path in required if not (root / path).exists()]
        present_removed = [path for path in removed_legacy_paths if (root / path).exists()]
        self.assertFalse(missing, f"Missing required project paths: {missing}")
        self.assertFalse(present_removed, f"Removed VM-era paths are still present: {present_removed}")


if __name__ == "__main__":
    unittest.main()
