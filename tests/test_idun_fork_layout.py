from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestIdunForkLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def test_active_entry_points_have_no_adjacent_udos_or_cpm_dependency(self) -> None:
        active_paths = (
            self.root / "Makefile",
            self.root / "tools" / "build_linux_tools.sh",
            self.root / "tools" / "build_linux_tools_aarch64.sh",
            self.root / "tools" / "build_all.sh",
            self.root / "tools" / "smoke.sh",
            self.root / "tools" / "env_check.sh",
            self.root / "tools" / "path_probe.py",
            self.root / "tools" / "setup_linux.sh",
            self.root / "tools" / "export_idun_workspace.py",
            self.root / "tools" / "vice_harness.py",
        )
        forbidden = (
            "../udos",
            "cpm65-u64",
            "build_actc_udos",
            "build_alink_udos",
            "build_release_image",
            "vice-release",
            "/mnt/c/test/action",
        )
        for path in active_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, text)

    def test_cross_product_plan_tracks_native_real_progress_and_remaining_work(self) -> None:
        parity = (self.root / "docs" / "udos_feature_parity.md").read_text(
            encoding="ascii"
        )
        flat_parity = " ".join(parity.split())

        self.assertIn("## Executive Status", parity)
        self.assertIn("five portable groups", parity)
        self.assertIn("Passes 6 and 7 collect\nand preallocate bounded REAL operands", parity)
        self.assertIn("Native pass L now consumes that stream", flat_parity)
        self.assertIn("intentional Idun mechanisms", parity)
        self.assertIn("The constant foundation is complete", parity)
        self.assertIn("round-to-nearest, ties-to-even", parity)
        self.assertIn("Dedicated pass K", parity)
        self.assertIn("inventories are 1,349 broad direct-PRG shapes", flat_parity)
        self.assertIn("181 non-runtime source-backed object-emission shapes", flat_parity)
        self.assertIn("298 compiled-runtime relocation-oracle cases", parity)
        self.assertIn("fifteen link-selected callable builtins", parity)
        self.assertIn("remaining 28 MATH1 routines", parity)
        self.assertIn("RT_F_FLOOR.OBJ", parity)
        self.assertIn("RT_F_CEIL.OBJ", parity)
        self.assertIn("RT_F_ROUND.OBJ", parity)
        self.assertIn("RT_F_FRAC.OBJ", parity)
        self.assertIn("RT_F_MOD.OBJ", parity)
        self.assertIn("RT_F_HYPOT.OBJ", parity)
        self.assertIn("817 native ActionC64U unittests", parity)
        self.assertIn("153 Idun/Alpine unittests", parity)
        self.assertIn("138 Idun ASan/UBSan tests", parity)
        self.assertIn("21 Idun direct-PRG tests", parity)
        self.assertIn("215-test overlay suite and 198-test source-cache suite", parity)
        self.assertIn("Generalize native REAL", parity)
        self.assertIn("MATH1 reachable-only packaging", parity)
        self.assertIn("call-graph pruning", parity)
        self.assertIn("Pass L handles bounded nested straight-line trees", flat_parity)
        self.assertIn("real_two_function_nested_postfix.act", parity)
        self.assertIn("real_function_call_chain_postfix.act", parity)
        self.assertIn("real_function_nested_local_call_postfix.act", parity)
        self.assertIn("pass L is 5,667 bytes with 2,525 bytes free", flat_parity)
        self.assertIn("complete ACTC compiler, passes 0 through L", parity)
        self.assertIn("The portable products are therefore not yet at full feature parity", parity)
        self.assertNotIn("binary32 folding remains", parity)

        handoff = (self.root / "docs" / "idun_fork_handoff.md").read_text(
            encoding="ascii"
        )
        flat_handoff = " ".join(handoff.split())
        self.assertIn("Current native inventories are 1,349 broad", flat_handoff)
        self.assertIn("181 non-runtime source-backed", flat_handoff)
        self.assertIn("298 compiled-runtime relocation-oracle cases", flat_handoff)
        self.assertIn("real_function_nested_postfix.act", handoff)
        self.assertIn("real_function_local_nested_postfix.act", handoff)
        self.assertIn("real_two_function_nested_postfix.act", handoff)
        self.assertIn("real_function_call_chain_postfix.act", handoff)
        self.assertIn("real_function_nested_local_call_postfix.act", handoff)
        self.assertIn(
            "pass 6 is 8,094 bytes with 98 bytes free",
            " ".join(handoff.split()),
        )
        self.assertIn(
            "pass 7 is 6,587 bytes with 1,605 bytes free",
            " ".join(handoff.split()),
        )
        self.assertIn(
            "native MATH1 gap remains 28 public routines",
            " ".join(handoff.split()),
        )
        self.assertIn("RT_F_HYPOT.OBJ", handoff)

    def test_retirement_manifest_covers_every_preserved_udos_directory(self) -> None:
        manifest_path = self.root / "resources" / "retired_udos_tools.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["policy"], "preserved-source-only")
        recorded = {entry["path"] for entry in manifest["legacy_roots"]}
        preserved = {
            path.relative_to(self.root).as_posix()
            for path in (self.root / "src" / "tools_udos").iterdir()
            if path.is_dir()
        }
        self.assertEqual(recorded, preserved)
        self.assertTrue((self.root / "docs" / "retired_udos_tools.md").is_file())

        active_entry_points = (
            self.root / "Makefile",
            self.root / "tools" / "build_linux_tools.sh",
            self.root / "tools" / "build_linux_tools_aarch64.sh",
            self.root / "tools" / "export_idun_workspace.py",
        )
        for path in active_entry_points:
            with self.subTest(active_path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertNotIn("src/tools_udos", text)
                self.assertNotIn("_udos.sh", text)

    def test_every_historical_user_tool_has_a_linux_command_or_retirement(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "export_idun_workspace",
            self.root / "tools" / "export_idun_workspace.py",
        )
        if spec is None or spec.loader is None:
            self.fail("could not load Idun export module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        linux_names = set(module.LINUX_TOOL_NAMES)

        expected = {
            "act2save",
            "actadd",
            "actc",
            "actchk",
            "actcopy",
            "actdbg",
            "actdel",
            "actdir",
            "actedit",
            "actfile",
            "actinfo",
            "actmkdir",
            "actmon",
            "actnew",
            "actren",
            "actrmdir",
            "actsrc",
            "acttree",
            "actwork",
            "actwrite",
            "alink",
            "deltree",
            "xcopy",
        }
        historical = {
            path.name
            for path in (self.root / "src" / "tools_udos").iterdir()
            if path.is_dir() and path.name not in {"common", "stageinfo"}
        }
        self.assertEqual(historical, expected)
        self.assertTrue(expected <= linux_names)
        self.assertTrue({"actmove", "actsave", "tree"} <= linux_names)
        self.assertIn("acthelp", linux_names)
        self.assertIn("actprof", linux_names)
        self.assertTrue(
            (self.root / "docs" / "linux_tool_port_status.md").is_file()
        )

    def test_build_produces_every_exported_linux_command(self) -> None:
        result = subprocess.run(
            ["bash", str(self.root / "tools" / "build_linux_tools.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        tool_dir = Path(result.stdout.strip().splitlines()[-1])

        spec = importlib.util.spec_from_file_location(
            "export_idun_workspace",
            self.root / "tools" / "export_idun_workspace.py",
        )
        if spec is None or spec.loader is None:
            self.fail("could not load Idun export module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in module.LINUX_TOOL_NAMES:
            with self.subTest(tool=name):
                self.assertTrue((tool_dir / name).is_file())

    def test_every_exported_command_name_dispatches(self) -> None:
        result = subprocess.run(
            ["bash", str(self.root / "tools" / "build_linux_tools.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        tool_dir = Path(result.stdout.strip().splitlines()[-1])

        spec = importlib.util.spec_from_file_location(
            "export_idun_workspace",
            self.root / "tools" / "export_idun_workspace.py",
        )
        if spec is None or spec.loader is None:
            self.fail("could not load Idun export module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as directory:
            for name in module.LINUX_TOOL_NAMES:
                with self.subTest(tool=name):
                    completed = subprocess.run(
                        [str(tool_dir / name)],
                        cwd=directory,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertNotEqual(
                        completed.returncode,
                        2,
                        msg=(
                            f"{name} did not dispatch through the multicall binary\n"
                            f"stdout: {completed.stdout}\n"
                            f"stderr: {completed.stderr}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
