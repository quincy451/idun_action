import importlib.util
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestToolAbiPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.script = self.root / "tools" / "run_tool_abi_additive_pipeline.py"
        self.base_fs = self.root.parent / "udos" / "build" / "udos-release-fs-manual-pipeline-44"
        self.compat_avmrun_prg = "AVMRUNC.PRG"
        self.compat_avmrun_labels = "avmrunc.current.labels"
        self.prod_avmrun_prg = "AVMRUN.PRG"
        self.prod_avmrun_labels = "avmrun.current.labels"
        spec = importlib.util.spec_from_file_location("run_tool_abi_additive_pipeline", self.script)
        assert spec is not None and spec.loader is not None
        self.pipeline_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pipeline_module)

    def run_scenario(self, scenario: str, expected_console: str, expected_avo_size: int, expected_avm_size: int) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-additive"
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--scenario",
                    scenario,
                    "--out-fs",
                    str(out_fs),
                    "--keep-workspace",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=300,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)

            summary = json.loads(result.stdout)
            self.assertEqual(summary["scenario"], scenario)
            self.assertEqual(summary.get("artifact_kind"), "avm")
            self.assertEqual(summary.get("runtime_kind"), "avmrunc")
            workspace = Path(summary["workspace"])
            actc_object_path = Path(summary["actc_object_path"])
            alink_image_path = Path(summary["alink_image_path"])

            self.assertTrue(workspace.is_dir(), msg=output)
            self.assertTrue(actc_object_path.is_file(), msg=output)
            self.assertTrue(alink_image_path.is_file(), msg=output)
            self.assertEqual(summary["avmrunc_console"], expected_console)
            self.assertEqual(actc_object_path.stat().st_size, expected_avo_size)
            normalized_expected_avm = self.pipeline_module.normalize_expected_avm_for_linked_printstd(
                self.pipeline_module.SCENARIOS[scenario]["expected_avm"]
            )
            self.assertEqual(alink_image_path.stat().st_size, len(normalized_expected_avm))

    def run_direct_prg_scenario(self, scenario: str) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-direct-prg"
            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--scenario",
                    scenario,
                    "--out-fs",
                    str(out_fs),
                    "--keep-workspace",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=300,
            )

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)

            summary = json.loads(result.stdout)
            self.assertEqual(summary["scenario"], scenario)
            self.assertEqual(summary.get("artifact_kind"), "prg")
            self.assertEqual(summary.get("runtime_kind"), "direct_prg")
            workspace = Path(summary["workspace"])
            actc_object_path = Path(summary["actc_object_path"])
            artifact_path = Path(summary["alink_artifact_path"])

            self.assertTrue(workspace.is_dir(), msg=output)
            self.assertTrue(artifact_path.is_file(), msg=output)
            self.assertEqual(artifact_path.name.upper(), "MAIN.PRG")
            self.assertEqual(summary.get("runtime_console", ""), self.pipeline_module.SCENARIOS[scenario].get("expected_console", ""))
            self.assertEqual(summary.get("runtime_exit_status"), 0)

            raw_expected_objects = self.pipeline_module.SCENARIOS[scenario].get("expected_objects")
            if raw_expected_objects is None:
                expected_main_object = self.pipeline_module.SCENARIOS[scenario]["expected_avo"]
            else:
                expected_main_object = raw_expected_objects.get("MAIN")
            expected_prg = self.pipeline_module.SCENARIOS[scenario]["expected_prg"]
            if expected_main_object is not None:
                expected_avo = expected_main_object.encode("ascii")
                self.assertTrue(actc_object_path.is_file(), msg=output)
                self.assertEqual(actc_object_path.stat().st_size, len(expected_avo))
            self.assertEqual(artifact_path.stat().st_size, len(expected_prg))
            self.assertEqual(artifact_path.read_bytes(), expected_prg)

    def run_actc_failure_source(self, source: str, expected_console_fragment: str) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        for script in ("build_tool_abi_harness.sh", "build_actc_harness_udos.sh"):
            result = subprocess.run(
                ["bash", str(self.root / "tools" / script)],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-actc-fail"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(source, encoding="ascii")

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(self.root / "build" / "udos_tools" / "ACTC_HARNESS.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--labels",
                    str(self.root / "build" / "udos_tools" / "actc_harness.current.labels"),
                    "--max-steps",
                    "4000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )

            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, msg=output)
            summary = json.loads(result.stdout)
            self.assertNotEqual(summary["exit_status"], 0, msg=output)
            self.assertIn(expected_console_fragment, summary.get("console", ""))

    def build_harness_tools(self, *scripts: str) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        requested_scripts = list(scripts)
        for script in requested_scripts:
            result = subprocess.run(
                ["bash", str(self.root / "tools" / script)],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        image_root = self.base_fs / "IMAGES" / "ACTION.DNP"
        if image_root.is_dir():
            for helper_name in ("RT_PRINT_STD_HELPER.BIN", "RT_PRINT_F_HELPER.BIN"):
                helper_src = self.root / "build" / "udos_tools" / helper_name
                if helper_src.is_file():
                    shutil.copy2(helper_src, image_root / helper_name)

    def run_harness_process(
        self,
        prg_name: str,
        workspace: Path,
        cmdline: str,
        labels_name: str,
        *,
        max_steps: int = 12000000,
        extra: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        extra = extra or []
        return subprocess.run(
            [
                str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                "--prg",
                str(self.root / "build" / "udos_tools" / prg_name),
                "--workspace",
                str(workspace),
                "--cmdline",
                cmdline,
                "--services-inc",
                str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                "--labels",
                str(self.root / "build" / "udos_tools" / labels_name),
                "--max-steps",
                str(max_steps),
                *extra,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )

    def run_harness_json(
        self,
        prg_name: str,
        workspace: Path,
        cmdline: str,
        labels_name: str,
        *,
        max_steps: int = 12000000,
        extra: list[str] | None = None,
    ) -> dict:
        result = self.run_harness_process(
            prg_name,
            workspace,
            cmdline,
            labels_name,
            max_steps=max_steps,
            extra=extra,
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, msg=output)
        return json.loads(result.stdout)

    def test_additive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("additive")

    def test_precedence_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("precedence")

    def test_comparisons_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparisons")

    def test_int_vars_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_basic")

    def test_helper_free_word_load_store_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_word_load_store")

    def test_helper_free_if_eq_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_if_eq")

    def test_helper_free_nested_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_nested_else")

    def test_helper_free_if_local_call_do_until_eq_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_if_local_call_do_until_eq")

    def test_helper_free_if_else_local_call_chain_nested_do_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_if_else_local_call_chain_nested_do_if_else")

    def test_helper_free_nested_else_local_call_chain_nested_do_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("helper_free_nested_else_local_call_chain_nested_do_if_else")

    def test_printstd_string_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printstd_string_direct_prg")

    def test_printstd_integer_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printstd_integer_direct_prg")

    def test_printstd_string_integer_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printstd_string_integer_direct_prg")

    def test_int_vars_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_do_until")

    def test_int_vars_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_if_else")

    def test_int_vars_while_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_while")

    def test_int_vars_branch_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_branch_calls")

    def test_int_vars_while_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_while_external")

    def test_int_vars_multi_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_basic")

    def test_byte_card_vars_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("byte_card_vars_basic")

    def test_real_decl_storage_width_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_decl_storage_width")

    def test_real_zero_initializer_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_zero_initializer")

    def test_real_decl_offsets_following_int_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_decl_offsets_following_int")

    def test_real_copy_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_copy_assignment_runtime")

    def test_real_zero_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_zero_assignment_runtime")

    def test_real_small_expr_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_small_expr_assignment_runtime")

    def test_rt_i_to_f_runtime_module_converts_256_to_real_high_word_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-rt-i-to-f"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 10\n"
                "b p0u0zr\n"
                "u rt_i_to_f\n"
                "i 256\n"
                "k 28\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "17280\n")

    def test_rt_s_to_f_runtime_module_converts_negative_seven_to_real_high_word_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-rt-s-to-f"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 10\n"
                "b p0u0zr\n"
                "u rt_s_to_f\n"
                "i 65529\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "49376\n")

    def test_real_card_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-card-bridge"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD A=[255]\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=A+1\r"
                "X=A\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            save_ops = [op for op in actc.get("ops", []) if op.get("kind") == "save"]
            self.assertTrue(save_ops, msg=actc)
            object_path = Path(save_ops[-1]["full_path"])
            self.assertTrue(object_path.is_file(), msg=str(object_path))
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b L0p0aS0L0u0T1S1e0r\n", object_text)
            self.assertIn("u rt_i_to_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_int_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-int-bridge"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT A=[0]\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=0-7\r"
                "X=A\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            save_ops = [op for op in actc.get("ops", []) if op.get("kind") == "save"]
            self.assertTrue(save_ops, msg=actc)
            object_path = Path(save_ops[-1]["full_path"])
            self.assertTrue(object_path.is_file(), msg=str(object_path))
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0p1mS0L0u0T1S1e0r\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_runtime_library_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("runtime_library_external")

    def test_dead_runtime_library_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dead_runtime_library_external")

    def test_real_add_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_assignment_runtime")

    def test_real_add_left_zero_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_left_zero_runtime")

    def test_real_add_two_plus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_two_plus_two_runtime")

    def test_real_add_one_plus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_plus_one_runtime")

    def test_real_add_four_plus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_four_plus_four_runtime")

    def test_real_add_negative_two_plus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_two_plus_negative_two_runtime")

    def test_real_add_two_plus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_two_plus_negative_two_runtime")

    def test_real_add_one_point_five_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_point_five_runtime")

    def test_real_add_two_plus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_two_plus_one_runtime")

    def test_real_add_one_plus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_plus_two_runtime")

    def test_real_add_negative_two_plus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_two_plus_negative_one_runtime")

    def test_real_add_two_plus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_two_plus_negative_one_runtime")

    def test_real_add_one_plus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_plus_negative_two_runtime")

    def test_real_add_negative_two_plus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_two_plus_one_runtime")

    def test_real_add_negative_one_plus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_one_plus_two_runtime")

    def test_real_add_four_plus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_four_plus_one_runtime")

    def test_real_add_one_plus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_plus_four_runtime")

    def test_real_add_negative_four_plus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_four_plus_negative_one_runtime")

    def test_real_add_four_plus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_four_plus_negative_one_runtime")

    def test_real_add_one_plus_negative_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_one_plus_negative_four_runtime")

    def test_real_add_negative_four_plus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_four_plus_one_runtime")

    def test_real_add_negative_one_plus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_add_negative_one_plus_four_runtime")

    def test_real_sub_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_assignment_runtime")

    def test_real_sub_two_minus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_two_minus_one_runtime")

    def test_real_sub_two_minus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_two_minus_two_runtime")

    def test_real_sub_zero_minus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_zero_minus_one_runtime")

    def test_real_sub_negative_two_minus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_two_minus_negative_two_runtime")

    def test_real_sub_zero_minus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_zero_minus_negative_one_runtime")

    def test_real_sub_four_minus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_four_minus_two_runtime")

    def test_real_sub_two_minus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_two_minus_four_runtime")

    def test_real_sub_negative_four_minus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_four_minus_negative_two_runtime")

    def test_real_sub_four_minus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_four_minus_one_runtime")

    def test_real_sub_one_minus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_one_minus_four_runtime")

    def test_real_sub_negative_four_minus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_four_minus_negative_one_runtime")

    def test_real_sub_two_minus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_two_minus_negative_one_runtime")

    def test_real_sub_one_minus_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_one_minus_negative_two_runtime")

    def test_real_sub_negative_two_minus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_two_minus_one_runtime")

    def test_real_sub_negative_one_minus_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_one_minus_two_runtime")

    def test_real_sub_four_minus_negative_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_four_minus_negative_one_runtime")

    def test_real_sub_one_minus_negative_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_one_minus_negative_four_runtime")

    def test_real_sub_negative_four_minus_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_four_minus_one_runtime")

    def test_real_sub_negative_one_minus_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_sub_negative_one_minus_four_runtime")

    def test_real_mul_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_assignment_runtime")

    def test_real_mul_two_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_two_times_two_runtime")

    def test_real_mul_four_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_four_times_two_runtime")

    def test_real_mul_one_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_one_times_two_runtime")

    def test_real_mul_zero_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_zero_times_two_runtime")

    def test_real_mul_negative_two_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_negative_two_times_two_runtime")

    def test_real_mul_negative_two_times_negative_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_negative_two_times_negative_two_runtime")

    def test_real_mul_one_point_five_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_one_point_five_times_two_runtime")

    def test_real_mul_two_times_one_point_five_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_two_times_one_point_five_runtime")

    def test_real_mul_negative_one_point_five_times_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_mul_negative_one_point_five_times_two_runtime")

    def test_real_div_assignment_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_assignment_runtime")

    def test_real_div_four_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_four_div_two_runtime")

    def test_real_div_eight_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_eight_div_two_runtime")

    def test_real_div_two_div_one_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_two_div_one_runtime")

    def test_real_div_two_div_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_two_div_four_runtime")

    def test_real_div_zero_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_zero_div_two_runtime")

    def test_real_div_negative_four_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_negative_four_div_two_runtime")

    def test_real_div_two_div_negative_four_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_two_div_negative_four_runtime")

    def test_real_div_three_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_three_div_two_runtime")

    def test_real_div_one_point_five_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_one_point_five_div_two_runtime")

    def test_real_div_negative_three_div_two_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("real_div_negative_three_div_two_runtime")

    def test_real_integer_print_is_rejected_until_real_lowering_exists(self) -> None:
        self.run_actc_failure_source(
            'MODULE MAIN\rREAL X\rPROC MAIN()\rPrintIE(X)\rRETURN\r',
            "BAD LITERAL",
        )

    def test_nonzero_real_initializer_is_rejected_until_real_lowering_exists(self) -> None:
        self.run_actc_failure_source(
            'MODULE MAIN\rREAL X=[1]\rPROC MAIN()\rPrintIE(7)\rRETURN\r',
            "BAD VAR",
        )

    def test_real_large_integer_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-large-int"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=256\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            save_ops = [op for op in actc.get("ops", []) if op.get("kind") == "save"]
            self.assertTrue(save_ops, msg=actc)
            object_path = Path(save_ops[-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_large_sum_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-large-sum"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=(255+1)\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            save_ops = [op for op in actc.get("ops", []) if op.get("kind") == "save"]
            self.assertTrue(save_ops, msg=actc)
            object_path = Path(save_ops[-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_large_negative_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-large-negative"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=0-256\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("i 65280\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_explicit_card_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-explicit-card"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD A=[255]\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=A+1\r"
                "X=REAL(A)\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_explicit_int_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-explicit-int"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT A=[0]\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=0-7\r"
                "X=REAL(A)\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_explicit_large_sum_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-explicit-sum"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(255+1)\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_explicit_large_negative_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-explicit-negative"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(0-256)\r"
                "PrintE(\"DONE\")\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("i 65280\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "DONE\n")

    def test_real_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(7)\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p1u0T0S0L0U0p2u1r\n", object_text)
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_PRINT_F_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )
            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertEqual(avm_bytes[9], 0x03)
            self.assertIn(bytes([0x49, 0x32, 0xFE]), payload)
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 1)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(len(helper_blob), helper_len)
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 1)
            helper_entry = helper_blob[6] | (helper_blob[7] << 8)
            helper_total = helper_blob[8] | (helper_blob[9] << 8)
            self.assertGreaterEqual(helper_entry, 10)
            self.assertEqual(helper_total, helper_len)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "7\n")
            self.assertTrue(any(op.get("kind") == "rsta" and op.get("path") == "!AVMRUN_OVL1.BIN" for op in avmrun.get("ops", [])), msg=avmrun)
            self.assertTrue(any(op.get("kind") == "rsta" and op.get("path") == "!AVMRUN_OVL2.BIN" for op in avmrun.get("ops", [])), msg=avmrun)
            self.assertTrue(any(op.get("kind") == "rsta" and op.get("path") == "!AVMRUN_OVL3.BIN" for op in avmrun.get("ops", [])), msg=avmrun)
            self.assertTrue(any(op.get("kind") == "rrd" for op in avmrun.get("ops", [])), msg=avmrun)

    def test_standard_print_runtime_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_PRINT_STD_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-std-print"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "PROC MAIN()\r"
                'PrintE("HELLO")\r'
                "PrintIE(7)\r"
                "RETURN\r",
                encoding="ascii",
            )
            for artifact_name in ("MAIN.PRG", "MAIN.AVM"):
                artifact_path = project_root / "bin" / artifact_name
                if artifact_path.exists():
                    artifact_path.unlink()

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            staged_paths = {op.get("path") for op in alink.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_PRINT_STD_HELPER.BIN", staged_paths, msg=alink)

            prg_path = project_root / "bin" / "MAIN.PRG"
            avm_path = project_root / "bin" / "MAIN.AVM"
            self.assertTrue(prg_path.is_file(), msg=alink)
            self.assertFalse(avm_path.exists(), msg=alink)

            runtime = self.pipeline_module.run_direct_prg(project_root, prg_path)
            self.assertEqual(runtime["exit_status"], 0)
            self.assertEqual(runtime.get("console", ""), "HELLO\n7\n")

    def test_sidspr_helper_family_trailer_is_emitted_when_runtime_wrappers_are_live(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_SIDSPR1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 4)
        self.assertEqual(helper_blob[10], 12)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 19\n"
                "b u0u1u2u3u4u5r\n"
                "u rt_sid_ad\n"
                "u rt_sid_sr\n"
                "u rt_sprite_color\n"
                "u rt_sprite_pos\n"
                "u rt_sid_freq\n"
                "u rt_sprite_data\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_SIDSPR1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 4)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 4)
            self.assertEqual(helper_blob[10], 12)
            self.assertIn(bytes((0x49, 0x03, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x04, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x10, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x12, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x13, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x05, 0xFD)), payload)

    def test_dbf_helper_family_trailer_is_emitted_when_runtime_wrappers_are_live(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_DBF1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 5)
        self.assertEqual(helper_blob[10], 9)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-dbf-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 28\n"
                "b u0u1u2u3u4u5u6u7u8r\n"
                "u rt_dbf_create\n"
                "u rt_dbf_open\n"
                "u rt_dbf_currrecno\n"
                "u rt_dbf_totalrecs\n"
                "u rt_dbf_close\n"
                "u rt_dbf_appendblank\n"
                "u rt_dbf_go\n"
                "u rt_dbf_readfield\n"
                "u rt_dbf_writefield\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_DBF1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 5)
            self.assertIn(bytes((0x49, 0x01, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x05, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x02, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x03, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x04, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x06, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x07, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x08, 0xFB)), payload)
            self.assertIn(bytes((0x49, 0x09, 0xFB)), payload)

    def test_math_helper_family_trailer_is_emitted_when_runtime_wrappers_are_live(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_MATH1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 6)
        self.assertEqual(helper_blob[10], 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-math-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_f_abs\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_MATH1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 6)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 6)
            self.assertEqual(helper_blob[10], 2)
            self.assertIn(bytes((0x49, 0x01, 0xFA)), payload)

    def test_math_fsqrt_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_MATH1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 6)
        self.assertEqual(helper_blob[10], 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-math-fsqrt-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_f_sqrt\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_MATH1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 6)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 6)
            self.assertEqual(helper_blob[10], 2)
            self.assertIn(bytes((0x49, 0x02, 0xFA)), payload)

    def test_math_fabs_runtime_pipeline_is_green_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        math_helper_blob = (self.root / "build" / "udos_tools" / "RT_MATH1_HELPER.BIN").read_bytes()
        print_helper_blob = (self.root / "build" / "udos_tools" / "RT_PRINT_F_HELPER.BIN").read_bytes()
        self.assertEqual(math_helper_blob[:4], b"AVNH")
        self.assertEqual(math_helper_blob[4], 1)
        self.assertEqual(math_helper_blob[5], 6)
        self.assertEqual(math_helper_blob[10], 2)
        self.assertEqual(print_helper_blob[:4], b"AVNH")
        self.assertEqual(print_helper_blob[5], 1)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_math_fabs = 0xFA01
        intrinsic_linked_printreal = 0xFE32
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray()
        exec_code.extend((opcode_push16, 0x00, 0x00))
        exec_code.extend((opcode_push16, 0xE0, 0xC0))
        exec_code.extend((opcode_calln, intrinsic_linked_math_fabs & 0xFF, intrinsic_linked_math_fabs >> 8))
        exec_code.extend((opcode_push16, 0x01, 0x00))
        exec_code.extend((opcode_calln, intrinsic_linked_printreal & 0xFF, intrinsic_linked_printreal >> 8))
        exec_code.extend((opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8))
        payload = bytes(exec_code)

        trailer = bytearray(b"AVH1")
        trailer.append(2)
        trailer.append(6)
        trailer.extend((len(math_helper_blob) & 0xFF, (len(math_helper_blob) >> 8) & 0xFF))
        trailer.extend(math_helper_blob)
        trailer.append(1)
        trailer.extend((len(print_helper_blob) & 0xFF, (len(print_helper_blob) >> 8) & 0xFF))
        trailer.extend(print_helper_blob)

        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-math-fabs"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            for removable in ("RT_MATH1_HELPER.BIN", "RT_PRINT_F_HELPER.BIN"):
                helper_path = image_root / removable
                if helper_path.exists():
                    helper_path.unlink()

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "7\n", msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_MATH1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertNotIn("!RT_PRINT_F_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL1.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_math_fsqrt_runtime_pipeline_handles_integer_and_fractional_inputs_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        math_helper_blob = (self.root / "build" / "udos_tools" / "RT_MATH1_HELPER.BIN").read_bytes()
        print_helper_blob = (self.root / "build" / "udos_tools" / "RT_PRINT_F_HELPER.BIN").read_bytes()
        self.assertEqual(math_helper_blob[:4], b"AVNH")
        self.assertEqual(math_helper_blob[4], 1)
        self.assertEqual(math_helper_blob[5], 6)
        self.assertEqual(math_helper_blob[10], 2)
        self.assertEqual(print_helper_blob[:4], b"AVNH")
        self.assertEqual(print_helper_blob[5], 1)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_math_fsqrt = 0xFA02
        intrinsic_linked_printreal = 0xFE32
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray()
        exec_code.extend((opcode_push16, 0x00, 0x00))
        exec_code.extend((opcode_push16, 0x10, 0x41))
        exec_code.extend((opcode_calln, intrinsic_linked_math_fsqrt & 0xFF, intrinsic_linked_math_fsqrt >> 8))
        exec_code.extend((opcode_push16, 0x01, 0x00))
        exec_code.extend((opcode_calln, intrinsic_linked_printreal & 0xFF, intrinsic_linked_printreal >> 8))
        exec_code.extend((opcode_push16, 0x00, 0x00))
        exec_code.extend((opcode_push16, 0x80, 0x3E))
        exec_code.extend((opcode_calln, intrinsic_linked_math_fsqrt & 0xFF, intrinsic_linked_math_fsqrt >> 8))
        exec_code.extend((opcode_push16, 0x01, 0x00))
        exec_code.extend((opcode_calln, intrinsic_linked_printreal & 0xFF, intrinsic_linked_printreal >> 8))
        exec_code.extend((opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8))
        payload = bytes(exec_code)

        trailer = bytearray(b"AVH1")
        trailer.append(2)
        trailer.append(6)
        trailer.extend((len(math_helper_blob) & 0xFF, (len(math_helper_blob) >> 8) & 0xFF))
        trailer.extend(math_helper_blob)
        trailer.append(1)
        trailer.extend((len(print_helper_blob) & 0xFF, (len(print_helper_blob) >> 8) & 0xFF))
        trailer.extend(print_helper_blob)

        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-math-fsqrt"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            for removable in ("RT_MATH1_HELPER.BIN", "RT_PRINT_F_HELPER.BIN"):
                helper_path = image_root / removable
                if helper_path.exists():
                    helper_path.unlink()

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "3\n0.5\n", msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_MATH1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertNotIn("!RT_PRINT_F_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL1.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_dbf_runtime_pipeline_tracks_handle_state_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_DBF1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 5)
        self.assertEqual(helper_blob[10], 9)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_dbf_create = 0xFB01
        intrinsic_linked_dbf_currrecno = 0xFB02
        intrinsic_linked_dbf_totalrecs = 0xFB03
        intrinsic_linked_dbf_close = 0xFB04
        intrinsic_linked_dbf_open = 0xFB05
        intrinsic_linked_dbf_appendblank = 0xFB06
        intrinsic_linked_dbf_go = 0xFB07
        intrinsic_linked_dbf_readfield = 0xFB08
        intrinsic_linked_dbf_writefield = 0xFB09
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12
        request_size = 14
        filename_bytes = b"TEST.DBF\x00"

        def make_request(
            *,
            handle: int = 0,
            field_count: int = 3,
            curr: int = 0,
            field_index: int = 0,
            value: int = 0,
        ) -> bytearray:
            return bytearray(
                (
                    0x00,
                    handle & 0xFF,
                    field_count & 0xFF,
                    (field_count >> 8) & 0xFF,
                    0x00,
                    0x00,
                    curr & 0xFF,
                    (curr >> 8) & 0xFF,
                    0x00,
                    0x00,
                    field_index & 0xFF,
                    (field_index >> 8) & 0xFF,
                    value & 0xFF,
                    (value >> 8) & 0xFF,
                )
            )

        request_blocks = [
            make_request(handle=0),                 # create
            make_request(handle=1),                 # append 1
            make_request(handle=1, field_index=0, value=0x1234),  # write rec1 field0
            make_request(handle=1, field_index=2, value=0x5678),  # write rec1 field2
            make_request(handle=1),                 # append 2
            make_request(handle=1, field_index=1, value=0x9ABC),  # write rec2 field1
            make_request(handle=1),                 # close
            make_request(handle=0),                 # open
            make_request(handle=1, curr=1),        # go rec1
            make_request(handle=1, field_index=0), # read rec1 field0
            make_request(handle=1, field_index=2), # read rec1 field2
            make_request(handle=1, curr=2),        # go rec2
            make_request(handle=1, field_index=1), # read rec2 field1
            make_request(handle=1),                # meta curr/total
        ]
        operations = [
            intrinsic_linked_dbf_create,
            intrinsic_linked_dbf_appendblank,
            intrinsic_linked_dbf_writefield,
            intrinsic_linked_dbf_writefield,
            intrinsic_linked_dbf_appendblank,
            intrinsic_linked_dbf_writefield,
            intrinsic_linked_dbf_close,
            intrinsic_linked_dbf_open,
            intrinsic_linked_dbf_go,
            intrinsic_linked_dbf_readfield,
            intrinsic_linked_dbf_readfield,
            intrinsic_linked_dbf_go,
            intrinsic_linked_dbf_readfield,
            intrinsic_linked_dbf_currrecno,
            intrinsic_linked_dbf_totalrecs,
        ]
        request_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 13]
        exec_len = len(operations) * 6 + 3
        requests_base = file_buffer_addr + avm_header_size_v2 + exec_len
        path_abs = requests_base + len(request_blocks) * request_size
        for block in request_blocks:
            block[8] = path_abs & 0xFF
            block[9] = (path_abs >> 8) & 0xFF

        request_addrs = [requests_base + i * request_size for i in range(len(request_blocks))]
        exec_code = bytearray()
        for req_index, intrinsic in zip(request_indices, operations):
            request_abs = request_addrs[req_index]
            exec_code.extend(
                (
                    opcode_push16,
                    request_abs & 0xFF,
                    request_abs >> 8,
                    opcode_calln,
                    intrinsic & 0xFF,
                    intrinsic >> 8,
                )
            )
        exec_code.extend((opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8))
        payload = bytes(exec_code + b"".join(bytes(block) for block in request_blocks) + filename_bytes)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(5)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((exec_len & 0xFF, (exec_len >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-dbf-compat"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_DBF1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            dump_keys = {
                "open": f"0x{request_addrs[7]:04x}",
                "read_r1_f0": f"0x{request_addrs[9]:04x}",
                "read_r1_f2": f"0x{request_addrs[10]:04x}",
                "read_r2_f1": f"0x{request_addrs[12]:04x}",
                "meta": f"0x{request_addrs[13]:04x}",
            }
            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", f"{dump_keys['open']}:14",
                    "--dump", f"{dump_keys['read_r1_f0']}:14",
                    "--dump", f"{dump_keys['read_r1_f2']}:14",
                    "--dump", f"{dump_keys['read_r2_f1']}:14",
                    "--dump", f"{dump_keys['meta']}:14",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(
                avmrun["dumps"][dump_keys["open"]],
                [0x01, 0x01, 0x03, 0x00, 0x02, 0x00, 0x02, 0x00, path_abs & 0xFF, (path_abs >> 8) & 0xFF, 0x00, 0x00, 0x00, 0x00],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"][dump_keys["read_r1_f0"]],
                [0x01, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, path_abs & 0xFF, (path_abs >> 8) & 0xFF, 0x00, 0x00, 0x34, 0x12],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"][dump_keys["read_r1_f2"]],
                [0x01, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, path_abs & 0xFF, (path_abs >> 8) & 0xFF, 0x02, 0x00, 0x78, 0x56],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"][dump_keys["read_r2_f1"]],
                [0x01, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, path_abs & 0xFF, (path_abs >> 8) & 0xFF, 0x01, 0x00, 0xBC, 0x9A],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"][dump_keys["meta"]],
                [0x01, 0x01, 0x03, 0x00, 0x02, 0x00, 0x02, 0x00, path_abs & 0xFF, (path_abs >> 8) & 0xFF, 0x00, 0x00, 0x00, 0x00],
                msg=avmrun,
            )
            dbf_path = project_root / "TEST.DBF"
            self.assertTrue(dbf_path.exists(), msg=avmrun)
            self.assertEqual(
                dbf_path.read_bytes(),
                bytes(
                    (
                        ord("D"), ord("B"), ord("F"), ord("1"),
                        0x03, 0x00,
                        0x02, 0x00,
                        0x02, 0x00,
                        0x34, 0x12, 0x00, 0x00, 0x78, 0x56,
                        0x00, 0x00, 0xBC, 0x9A, 0x00, 0x00,
                    )
                ),
            )
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_DBF1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_dbf_native_fast_path_reports_harness_no_acheron_under_production_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_DBF1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 5)
        self.assertEqual(helper_blob[10], 9)

        opcode_setp16 = 0x61
        opcode_calln = 0x49
        intrinsic_linked_dbf_create = 0xFB01
        intrinsic_linked_dbf_currrecno = 0xFB02
        intrinsic_linked_dbf_totalrecs = 0xFB03
        intrinsic_linked_dbf_close = 0xFB04
        intrinsic_linked_dbf_open = 0xFB05
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12
        request_size = 14
        filename_bytes = b"TEST.DBF\x00"

        def make_request(
            *,
            handle: int = 0,
            field_count: int = 3,
            curr: int = 0,
        ) -> bytearray:
            return bytearray(
                (
                    0x00,
                    handle & 0xFF,
                    field_count & 0xFF,
                    (field_count >> 8) & 0xFF,
                    0x00,
                    0x00,
                    curr & 0xFF,
                    (curr >> 8) & 0xFF,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                )
            )

        request_blocks = [
            make_request(handle=0),  # create
            make_request(handle=1),  # close
            make_request(handle=0),  # open
            make_request(handle=1),  # curr
            make_request(handle=1),  # total
        ]
        operations = [
            intrinsic_linked_dbf_create,
            intrinsic_linked_dbf_close,
            intrinsic_linked_dbf_open,
            intrinsic_linked_dbf_currrecno,
            intrinsic_linked_dbf_totalrecs,
        ]
        exec_len = len(operations) * 6 + 3
        requests_base = file_buffer_addr + avm_header_size_v2 + exec_len
        path_abs = requests_base + len(request_blocks) * request_size
        for block in request_blocks:
            block[8] = path_abs & 0xFF
            block[9] = (path_abs >> 8) & 0xFF

        request_addrs = [requests_base + i * request_size for i in range(len(request_blocks))]
        request_offsets = [exec_len + i * request_size for i in range(len(request_blocks))]
        exec_code = bytearray()
        for request_offset, intrinsic in zip(request_offsets, operations):
            exec_code.extend(
                (
                    opcode_setp16,
                    request_offset & 0xFF,
                    request_offset >> 8,
                    opcode_calln,
                    intrinsic & 0xFF,
                    intrinsic >> 8,
                )
            )
        exec_code.extend((opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8))
        payload = bytes(exec_code + b"".join(bytes(block) for block in request_blocks) + filename_bytes)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(5)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((exec_len & 0xFF, (exec_len >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-dbf-production"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_DBF1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            dump_keys = {
                "close": f"0x{request_addrs[1]:04x}",
                "open": f"0x{request_addrs[2]:04x}",
                "curr": f"0x{request_addrs[3]:04x}",
                "total": f"0x{request_addrs[4]:04x}",
            }
            result = self.run_harness_process(
                self.prod_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.prod_avmrun_labels,
                extra=[
                    "--dump", f"{dump_keys['close']}:14",
                    "--dump", f"{dump_keys['open']}:14",
                    "--dump", f"{dump_keys['curr']}:14",
                    "--dump", f"{dump_keys['total']}:14",
                ],
            )
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 1, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "HARNESS NO ACHERON\n", msg=avmrun)
            self.assertEqual(avmrun["dumps"][dump_keys["close"]], [0x00] * request_size, msg=avmrun)
            self.assertEqual(avmrun["dumps"][dump_keys["open"]], [0x00] * request_size, msg=avmrun)
            self.assertEqual(avmrun["dumps"][dump_keys["curr"]], [0x00] * request_size, msg=avmrun)
            self.assertEqual(avmrun["dumps"][dump_keys["total"]], [0x00] * request_size, msg=avmrun)
            dbf_path = project_root / "TEST.DBF"
            self.assertFalse(dbf_path.exists(), msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_DBF1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertNotIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_helper_family_trailer_is_emitted_when_runtime_wrappers_are_live(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 49\n"
                "b u0u1u2u3u4u5u6u7u8u9uAuBuCuDuEuFr\n"
                "u rt_gfx_bitmap_on\n"
                "u rt_gfx_bitmap_off\n"
                "u rt_gfx_mbitmap_on\n"
                "u rt_gfx_bgcolor\n"
                "u rt_gfx_bordercolor\n"
                "u rt_gfx_vic_bank\n"
                "u rt_gfx_screen_base\n"
                "u rt_gfx_bitmap_base\n"
                "u rt_gfx_bitmap_fill\n"
                "u rt_gfx_screen_cell\n"
                "u rt_gfx_bitmap_show\n"
                "u rt_gfx_bitmap_hide\n"
                "u rt_gfx_screen_copy\n"
                "u rt_gfx_color_copy\n"
                "u rt_gfx_bm_cell_colors\n"
                "u rt_gfx_bm_cell_data\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x01, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x02, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x03, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x04, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x05, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x06, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x07, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x08, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x09, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x0A, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x0C, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x0D, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x0F, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x10, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x11, 0xFC)), payload)
            self.assertIn(bytes((0x49, 0x12, 0xFC)), payload)

    def test_gfx_bitmap_copy_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-copy-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_bitmap_copy\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x0E, 0xFC)), payload)

    def test_gfx_bitmap_cell_data_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-cell-data-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_bm_cell_data\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x12, 0xFC)), payload)

    def test_gfx_bitmap_blit_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-blit-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_bitmap_blit\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x13, 0xFC)), payload)

    def test_gfx_bitmap_mask_blit_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-mask-blit-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_bitmap_mask_blit\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x16, 0xFC)), payload)

    def test_gfx_tile_mask_draw_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-mask-draw-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tile_mask_draw\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x17, 0xFC)), payload)

    def test_gfx_tileset_draw_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-draw-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tileset_draw\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x18, 0xFC)), payload)

    def test_gfx_tileset_rect_fill_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-rect-fill-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tset_rect_fill\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x19, 0xFC)), payload)

    def test_gfx_tileset_mask_draw_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-mask-draw-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tset_mask_draw\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x1A, 0xFC)), payload)

    def test_gfx_tileset_mask_rect_fill_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-mask-rect-fill-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tset_mask_rfill\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x1B, 0xFC)), payload)

    def test_gfx_tile_draw_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-draw-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tile_draw\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x14, 0xFC)), payload)

    def test_gfx_tile_rect_fill_wrapper_emits_helper_trailer_and_linked_call(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-rect-fill-helper"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 4\n"
                "b u0r\n"
                "u rt_gfx_tile_rect_fill\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0, msg=alink)
            self.assertTrue(
                any(op.get("kind") == "rsta" and op.get("path") == "!RT_GFX1_HELPER.BIN" for op in alink.get("ops", [])),
                msg=alink,
            )

            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            trailer = avm_bytes[12 + payload_len :]
            self.assertGreater(len(trailer), 8)
            self.assertEqual(trailer[:4], b"AVH1")
            self.assertEqual(trailer[4], 1)
            self.assertEqual(trailer[5], 3)
            helper_len = trailer[6] | (trailer[7] << 8)
            self.assertGreater(helper_len, 0)
            helper_blob = trailer[8 : 8 + helper_len]
            self.assertEqual(helper_blob[:4], b"AVNH")
            self.assertEqual(helper_blob[4], 1)
            self.assertEqual(helper_blob[5], 3)
            self.assertEqual(helper_blob[10], 23)
            self.assertIn(bytes((0x49, 0x15, 0xFC)), payload)

    def test_gfx_runtime_pipeline_updates_multicolor_bitmap_mode_and_colors_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_mbitmap_on = 0xFC03
        intrinsic_linked_gfx_bg_color = 0xFC04
        intrinsic_linked_gfx_border_color = 0xFC05
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 0x06, 0x00,
                opcode_calln, intrinsic_linked_gfx_bg_color & 0xFF, intrinsic_linked_gfx_bg_color >> 8,
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_border_color & 0xFF, intrinsic_linked_gfx_border_color >> 8,
                opcode_calln, intrinsic_linked_gfx_mbitmap_on & 0xFF, intrinsic_linked_gfx_mbitmap_on >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-compat-on"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xd020:1",
                    "--dump", "0xd021:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd020"], [0x02], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd021"], [0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x20, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x10, msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_runtime_pipeline_turns_bitmap_mode_off_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_mbitmap_on = 0xFC03
        intrinsic_linked_gfx_bg_color = 0xFC04
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bg_color & 0xFF, intrinsic_linked_gfx_bg_color >> 8,
                opcode_calln, intrinsic_linked_gfx_mbitmap_on & 0xFF, intrinsic_linked_gfx_mbitmap_on >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-compat-off"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_runtime_pipeline_updates_bank_bases_fill_and_cells_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bitmap_on = 0xFC01
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_fill = 0xFC09
        intrinsic_linked_gfx_screen_cell = 0xFC0A
        intrinsic_linked_gfx_color_cell = 0xFC0B
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_on & 0xFF, intrinsic_linked_gfx_bitmap_on >> 8,
                opcode_push16, 0xAA, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_fill & 0xFF, intrinsic_linked_gfx_bitmap_fill >> 8,
                opcode_push16, 0x02, 0x00,
                opcode_push16, 0x3C, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_cell & 0xFF, intrinsic_linked_gfx_screen_cell >> 8,
                opcode_push16, 0x02, 0x00,
                opcode_push16, 0x09, 0x00,
                opcode_calln, intrinsic_linked_gfx_color_cell & 0xFF, intrinsic_linked_gfx_color_cell >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-compat-bases"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xd011:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xdd00:1",
                    "--dump", "0x8402:1",
                    "--dump", "0xd802:1",
                    "--dump", "0xa000:1",
                    "--dump", "0xa800:1",
                    "--dump", "0xbf3f:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x20, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8402"], [0x3C], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd802"], [0x09], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa000"], [0xAA], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa800"], [0xAA], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xbf3f"], [0xAA], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_show_descriptor_stages_bitmap_screen_and_color_data_then_hide_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bitmap_show = 0xFC0C
        intrinsic_linked_gfx_bitmap_hide = 0xFC0D
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        bitmap_data = bytearray(0x2000)
        bitmap_data[0x0000] = 0x12
        bitmap_data[0x0800] = 0x34
        bitmap_data[0x1FFF] = 0x56
        screen_data = bytearray(1000)
        screen_data[0x0002] = 0x9A
        screen_data[0x03E7] = 0x7B
        color_data = bytearray(1000)
        color_data[0x0002] = 0xC5
        color_data[0x03E7] = 0x1E
        descriptor = bytearray((0x0E, 0x02, 0x01, 0x01, 0x06, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
        exec_code = bytearray(
            [
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_show & 0xFF, intrinsic_linked_gfx_bitmap_show >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_hide & 0xFF, intrinsic_linked_gfx_bitmap_hide >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        descriptor_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        bitmap_data_addr = descriptor_addr + len(descriptor)
        screen_data_addr = bitmap_data_addr + len(bitmap_data)
        color_data_addr = screen_data_addr + len(screen_data)
        exec_code[1] = descriptor_addr & 0xFF
        exec_code[2] = descriptor_addr >> 8
        descriptor[6] = bitmap_data_addr & 0xFF
        descriptor[7] = bitmap_data_addr >> 8
        descriptor[8] = screen_data_addr & 0xFF
        descriptor[9] = screen_data_addr >> 8
        descriptor[10] = color_data_addr & 0xFF
        descriptor[11] = color_data_addr >> 8
        payload = bytes(exec_code) + bytes(descriptor) + bytes(bitmap_data) + bytes(screen_data) + bytes(color_data)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-bitmap-show-hide"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd020:1",
                    "--dump", "0xd021:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa000:1",
                    "--dump", "0xa800:1",
                    "--dump", "0xbfff:1",
                    "--dump", "0x8402:1",
                    "--dump", "0x87e7:1",
                    "--dump", "0xd802:1",
                    "--dump", "0xdbe7:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd021"], [0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd020"], [0x02], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa000"], [0x12], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa800"], [0x34], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xbfff"], [0x56], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8402"], [0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x87e7"], [0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd802"], [0x05], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdbe7"], [0x0E], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_copy_descriptor_stages_bitmap_screen_and_color_data_without_mode_side_effects_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bg_color = 0xFC04
        intrinsic_linked_gfx_border_color = 0xFC05
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_copy = 0xFC0E
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        bitmap_data = bytearray(0x2000)
        bitmap_data[0x0000] = 0x12
        bitmap_data[0x0800] = 0x34
        bitmap_data[0x1FFF] = 0x56
        screen_data = bytearray(1000)
        screen_data[0x0002] = 0x9A
        screen_data[0x03E7] = 0x7B
        color_data = bytearray(1000)
        color_data[0x0002] = 0xC5
        color_data[0x03E7] = 0x1E
        descriptor = bytearray((0x0E, 0x02, 0x01, 0x01, 0x06, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
        exec_code = bytearray(
            [
                opcode_push16, 0x03, 0x00,
                opcode_calln, intrinsic_linked_gfx_bg_color & 0xFF, intrinsic_linked_gfx_bg_color >> 8,
                opcode_push16, 0x04, 0x00,
                opcode_calln, intrinsic_linked_gfx_border_color & 0xFF, intrinsic_linked_gfx_border_color >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_copy & 0xFF, intrinsic_linked_gfx_bitmap_copy >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        descriptor_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        bitmap_data_addr = descriptor_addr + len(descriptor)
        screen_data_addr = bitmap_data_addr + len(bitmap_data)
        color_data_addr = screen_data_addr + len(screen_data)
        exec_code[34] = descriptor_addr & 0xFF
        exec_code[35] = descriptor_addr >> 8
        descriptor[6] = bitmap_data_addr & 0xFF
        descriptor[7] = bitmap_data_addr >> 8
        descriptor[8] = screen_data_addr & 0xFF
        descriptor[9] = screen_data_addr >> 8
        descriptor[10] = color_data_addr & 0xFF
        descriptor[11] = color_data_addr >> 8
        payload = bytes(exec_code) + bytes(descriptor) + bytes(bitmap_data) + bytes(screen_data) + bytes(color_data)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-bitmap-copy"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd020:1",
                    "--dump", "0xd021:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa000:1",
                    "--dump", "0xa800:1",
                    "--dump", "0xbfff:1",
                    "--dump", "0x8402:1",
                    "--dump", "0x87e7:1",
                    "--dump", "0xd802:1",
                    "--dump", "0xdbe7:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x03, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd021"], [0x03], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd020"], [0x04], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa000"], [0x12], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa800"], [0x34], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xbfff"], [0x56], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8402"], [0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x87e7"], [0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd802"], [0x05], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdbe7"], [0x0E], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_screen_copy_and_color_copy_write_active_planes_without_mode_side_effects_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_screen_copy = 0xFC0F
        intrinsic_linked_gfx_color_copy = 0xFC10
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        screen_data = bytearray(1000)
        screen_data[0x0002] = 0x9A
        screen_data[0x03E7] = 0x7B
        color_data = bytearray(1000)
        color_data[0x0002] = 0xC5
        color_data[0x03E7] = 0x1E
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_copy & 0xFF, intrinsic_linked_gfx_screen_copy >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_color_copy & 0xFF, intrinsic_linked_gfx_color_copy >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        screen_data_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        color_data_addr = screen_data_addr + len(screen_data)
        exec_code[16] = screen_data_addr & 0xFF
        exec_code[17] = screen_data_addr >> 8
        exec_code[22] = color_data_addr & 0xFF
        exec_code[23] = color_data_addr >> 8
        payload = bytes(exec_code) + bytes(screen_data) + bytes(color_data)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-screen-color-copy"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0x8402:1",
                    "--dump", "0x87e7:1",
                    "--dump", "0xd802:1",
                    "--dump", "0xdbe7:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8402"], [0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x87e7"], [0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd802"], [0x05], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdbe7"], [0x0E], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_cell_colors_writes_active_screen_and_color_at_cell_coordinates_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_cell_colors = 0xFC11
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x02, 0x01,
                opcode_push16, 0x9A, 0x05,
                opcode_calln, intrinsic_linked_gfx_bitmap_cell_colors & 0xFF, intrinsic_linked_gfx_bitmap_cell_colors >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-bitmap-cell-colors"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0x842a:1",
                    "--dump", "0xd82a:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x842a"], [0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd82a"], [0x05], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_cell_data_writes_active_bitmap_cell_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_cell_data = 0xFC12
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        cell_data = bytes((0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88))
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x02, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_cell_data & 0xFF, intrinsic_linked_gfx_bitmap_cell_data >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        cell_data_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[19] = cell_data_addr & 0xFF
        exec_code[20] = cell_data_addr >> 8
        payload = bytes(exec_code) + cell_data
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-bitmap-cell-data"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa150:8",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_blit_descriptor_writes_active_bitmap_screen_and_color_planes_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_blit = 0xFC13
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        bitmap_data = bytes(
            (
                0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
            )
        )
        screen_data = bytes((0x9A, 0x7B, 0x4C, 0x2D))
        color_data = bytes((0x15, 0x26, 0x37, 0x48))
        descriptor = bytearray((0x02, 0x02, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00))
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_blit & 0xFF, intrinsic_linked_gfx_bitmap_blit >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        descriptor_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        bitmap_data_addr = descriptor_addr + len(descriptor)
        screen_data_addr = bitmap_data_addr + len(bitmap_data)
        color_data_addr = screen_data_addr + len(screen_data)
        exec_code[22] = descriptor_addr & 0xFF
        exec_code[23] = descriptor_addr >> 8
        descriptor[4] = bitmap_data_addr & 0xFF
        descriptor[5] = bitmap_data_addr >> 8
        descriptor[6] = screen_data_addr & 0xFF
        descriptor[7] = screen_data_addr >> 8
        descriptor[8] = color_data_addr & 0xFF
        descriptor[9] = color_data_addr >> 8
        payload = bytes(exec_code) + bytes(descriptor) + bitmap_data + screen_data + color_data
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-bitmap-blit"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x07, 0x08], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_bitmap_mask_blit_descriptor_masks_active_bitmap_plane_without_screen_or_color_side_effects_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_fill = 0xFC09
        intrinsic_linked_gfx_bitmap_mask_blit = 0xFC16
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        bitmap_data = bytes((0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08))
        mask_data = bytes((0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F))
        descriptor = bytearray((0x02, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00))
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0xAA, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_fill & 0xFF, intrinsic_linked_gfx_bitmap_fill >> 8,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_mask_blit & 0xFF, intrinsic_linked_gfx_bitmap_mask_blit >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        descriptor_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        bitmap_data_addr = descriptor_addr + len(descriptor)
        mask_data_addr = bitmap_data_addr + len(bitmap_data)
        exec_code[28] = descriptor_addr & 0xFF
        exec_code[29] = descriptor_addr >> 8
        descriptor[4] = bitmap_data_addr & 0xFF
        descriptor[5] = bitmap_data_addr >> 8
        descriptor[6] = mask_data_addr & 0xFF
        descriptor[7] = mask_data_addr >> 8
        payload = bytes(exec_code) + bytes(descriptor) + bitmap_data + mask_data
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-mask-blit"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0x8429:2",
                    "--dump", "0xd829:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x00, 0x00], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x00, 0x00], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tile_draw_resource_writes_active_bitmap_screen_and_color_planes_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_tile_draw = 0xFC14
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        resource = bytes(
            (
                0x02, 0x02,
                0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
                0x9A, 0x7B, 0x4C, 0x2D,
                0x15, 0x26, 0x37, 0x48,
            )
        )
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tile_draw & 0xFF, intrinsic_linked_gfx_tile_draw >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        resource_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[25] = resource_addr & 0xFF
        exec_code[26] = resource_addr >> 8
        payload = bytes(exec_code) + resource
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-draw"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x07, 0x08], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tile_mask_draw_resource_masks_bitmap_plane_and_updates_screen_color_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_fill = 0xFC09
        intrinsic_linked_gfx_tile_mask_draw = 0xFC17
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        resource = bytes(
            (
                0x02, 0x02,
                0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80,
                0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
                0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0,
                0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F,
                0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x9A, 0x7B, 0x4C, 0x2D,
                0xC5, 0xD6, 0xE7, 0xF8,
            )
        )
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0xAA, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_fill & 0xFF, intrinsic_linked_gfx_bitmap_fill >> 8,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tile_mask_draw & 0xFF, intrinsic_linked_gfx_tile_mask_draw >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        resource_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[31] = resource_addr & 0xFF
        exec_code[32] = resource_addr >> 8
        payload = bytes(exec_code) + resource
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-mask-draw"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x07, 0x08], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tileset_draw_selects_indexed_tile_resource_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_tileset_draw = 0xFC18
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        tile0 = bytes(
            (
                0x02, 0x02,
                0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
                0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
                0x9A, 0x7B, 0x4C, 0x2D,
                0x15, 0x26, 0x37, 0x48,
            )
        )
        tile1 = bytes(
            (
                0x02, 0x02,
                0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
                0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
                0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
                0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88,
                0xAA, 0xBB, 0xCC, 0xDD,
                0x19, 0x2A, 0x3B, 0x4C,
            )
        )
        tileset = bytes((0x02, 0x00)) + tile0 + tile1
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tileset_draw & 0xFF, intrinsic_linked_gfx_tileset_draw >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        tileset_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[28] = tileset_addr & 0xFF
        exec_code[29] = tileset_addr >> 8
        payload = bytes(exec_code) + tileset
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-draw"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0xAA, 0xBB], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0xCC, 0xDD], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x09, 0x0A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x0B, 0x0C], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tileset_rect_fill_selects_indexed_fill_tile_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_tileset_rect_fill = 0xFC19
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        tile0 = bytes((0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x9A, 0x05))
        tile1 = bytes((0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0xAB, 0x0C))
        tileset = bytes((0x02, 0x00)) + tile0 + tile1
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_push16, 0x02, 0x02,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tileset_rect_fill & 0xFF, intrinsic_linked_gfx_tileset_rect_fill >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        tileset_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[31] = tileset_addr & 0xFF
        exec_code[32] = tileset_addr >> 8
        payload = bytes(exec_code) + tileset
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-rect-fill"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0xAB, 0xAB], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0xAB, 0xAB], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x0C, 0x0C], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x0C, 0x0C], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tileset_mask_draw_selects_indexed_mask_tile_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_fill = 0xFC09
        intrinsic_linked_gfx_tileset_mask_draw = 0xFC1A
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        tile0 = bytes(
            (
                0x02, 0x02,
                0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
                0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8,
                0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8,
                0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8,
                0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
                0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
                0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F,
                0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0,
                0x11, 0x22, 0x33, 0x44,
                0x05, 0x06, 0x07, 0x08,
            )
        )
        tile1 = bytes(
            (
                0x02, 0x02,
                0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80,
                0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
                0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0,
                0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F,
                0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x9A, 0x7B, 0x4C, 0x2D,
                0xC5, 0xD6, 0xE7, 0xF8,
            )
        )
        tileset = bytes((0x02, 0x00)) + tile0 + tile1
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0xAA, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_fill & 0xFF, intrinsic_linked_gfx_bitmap_fill >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tileset_mask_draw & 0xFF, intrinsic_linked_gfx_tileset_mask_draw >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        tileset_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[34] = tileset_addr & 0xFF
        exec_code[35] = tileset_addr >> 8
        payload = bytes(exec_code) + tileset
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-mask-draw"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x07, 0x08], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tileset_mask_rect_fill_repeats_indexed_mask_tile_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_bitmap_fill = 0xFC09
        intrinsic_linked_gfx_tileset_mask_rect_fill = 0xFC1B
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        tile0 = bytes(
            (
                0x02, 0x02,
                0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
                0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8,
                0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8,
                0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8,
                0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00,
                0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0xFF,
                0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F,
                0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0,
                0x11, 0x22, 0x33, 0x44,
                0x05, 0x06, 0x07, 0x08,
            )
        )
        tile1 = bytes(
            (
                0x02, 0x02,
                0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80,
                0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
                0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0,
                0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F,
                0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x9A, 0x7B, 0x4C, 0x2D,
                0xC5, 0xD6, 0xE7, 0xF8,
            )
        )
        tileset = bytes((0x02, 0x00)) + tile0 + tile1
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0xAA, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_fill & 0xFF, intrinsic_linked_gfx_bitmap_fill >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_push16, 0x02, 0x02,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tileset_mask_rect_fill & 0xFF, intrinsic_linked_gfx_tileset_mask_rect_fill >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        tileset_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[37] = tileset_addr & 0xFF
        exec_code[38] = tileset_addr >> 8
        payload = bytes(exec_code) + tileset
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(exec_code) & 0xFF, (len(exec_code) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tileset-mask-rect-fill"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:32",
                    "--dump", "0xa288:32",
                    "--dump", "0xa3c8:32",
                    "--dump", "0xa508:32",
                    "--dump", "0x8429:4",
                    "--dump", "0x8451:4",
                    "--dump", "0x8479:4",
                    "--dump", "0x84a1:4",
                    "--dump", "0xd829:4",
                    "--dump", "0xd851:4",
                    "--dump", "0xd879:4",
                    "--dump", "0xd8a1:4",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(
                avmrun["dumps"]["0xa148"],
                [0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A,
                 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8,
                 0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A,
                 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"]["0xa288"],
                [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA,
                 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"]["0xa3c8"],
                [0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A,
                 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8,
                 0x1A, 0x2A, 0x3A, 0x4A, 0x5A, 0x6A, 0x7A, 0x8A,
                 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8],
                msg=avmrun,
            )
            self.assertEqual(
                avmrun["dumps"]["0xa508"],
                [0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA,
                 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
                 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA],
                msg=avmrun,
            )
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x7B, 0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x4C, 0x2D, 0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8479"], [0x9A, 0x7B, 0x9A, 0x7B], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x84a1"], [0x4C, 0x2D, 0x4C, 0x2D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x06, 0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x07, 0x08, 0x07, 0x08], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd879"], [0x05, 0x06, 0x05, 0x06], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd8a1"], [0x07, 0x08, 0x07, 0x08], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_gfx_tile_rect_fill_resource_repeats_single_tile_across_active_planes_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_GFX1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 3)
        self.assertEqual(helper_blob[10], 23)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_gfx_vic_bank = 0xFC06
        intrinsic_linked_gfx_screen_base = 0xFC07
        intrinsic_linked_gfx_bitmap_base = 0xFC08
        intrinsic_linked_gfx_bitmap_off = 0xFC02
        intrinsic_linked_gfx_tile_rect_fill = 0xFC15
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2
        file_buffer_addr = 0x4B40
        avm_header_size_v2 = 12

        resource = bytes((0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x9A, 0x05))
        exec_code = bytearray(
            [
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_gfx_vic_bank & 0xFF, intrinsic_linked_gfx_vic_bank >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_screen_base & 0xFF, intrinsic_linked_gfx_screen_base >> 8,
                opcode_push16, 0x01, 0x00,
                opcode_calln, intrinsic_linked_gfx_bitmap_base & 0xFF, intrinsic_linked_gfx_bitmap_base >> 8,
                opcode_calln, intrinsic_linked_gfx_bitmap_off & 0xFF, intrinsic_linked_gfx_bitmap_off >> 8,
                opcode_push16, 0x02, 0x02,
                opcode_push16, 0x01, 0x01,
                opcode_push16, 0x00, 0x00,
                opcode_calln, intrinsic_linked_gfx_tile_rect_fill & 0xFF, intrinsic_linked_gfx_tile_rect_fill >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        resource_addr = file_buffer_addr + avm_header_size_v2 + len(exec_code)
        exec_code[28] = resource_addr & 0xFF
        exec_code[29] = resource_addr >> 8
        payload = bytes(exec_code) + resource
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(3)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-gfx-tile-rect-fill"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_GFX1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xdd00:1",
                    "--dump", "0xd018:1",
                    "--dump", "0xd011:1",
                    "--dump", "0xd016:1",
                    "--dump", "0xa148:8",
                    "--dump", "0xa150:8",
                    "--dump", "0xa288:8",
                    "--dump", "0xa290:8",
                    "--dump", "0x8429:2",
                    "--dump", "0x8451:2",
                    "--dump", "0xd829:2",
                    "--dump", "0xd851:2",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xdd00"][0] & 0x03, 0x01, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0xF0, 0x10, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd018"][0] & 0x08, 0x08, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd011"][0] & 0x20, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd016"][0] & 0x10, 0x00, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa148"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa150"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa288"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xa290"], [0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8429"], [0x9A, 0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x8451"], [0x9A, 0x9A], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd829"], [0x05, 0x05], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd851"], [0x05, 0x05], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_GFX1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_sidspr_native_fast_path_reports_harness_no_acheron_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_SIDSPR1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 4)

        opcode_setp16 = 0x61
        opcode_calln = 0x49
        intrinsic_linked_sidspr_sid_vol = 0xFD16
        intrinsic_linked_sidspr_sprite_on = 0xFD01
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_setp16, 0x0F, 0x00,
                opcode_calln, intrinsic_linked_sidspr_sid_vol & 0xFF, intrinsic_linked_sidspr_sid_vol >> 8,
                opcode_setp16, 0x11, 0x00,
                opcode_calln, intrinsic_linked_sidspr_sprite_on & 0xFF, intrinsic_linked_sidspr_sprite_on >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code + bytearray([7, 0, 3, 0]))
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(4)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((0x00, 0x00))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-runtime"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_SIDSPR1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.prod_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.prod_avmrun_labels,
                extra=["--dump", "0xd015:1", "--dump", "0xd418:1"],
            )
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 1, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "HARNESS NO ACHERON\n", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd015"], [0x00], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd418"], [0x00], msg=avmrun)

    def test_sidspr_runtime_pipeline_updates_registers_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_SIDSPR1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 4)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_sidspr_sid_vol = 0xFD16
        intrinsic_linked_sidspr_sprite_on = 0xFD01
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 7, 0,
                opcode_calln, intrinsic_linked_sidspr_sid_vol & 0xFF, intrinsic_linked_sidspr_sid_vol >> 8,
                opcode_push16, 3, 0,
                opcode_calln, intrinsic_linked_sidspr_sprite_on & 0xFF, intrinsic_linked_sidspr_sprite_on >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(4)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-compat"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_SIDSPR1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=["--dump", "0xd015:1", "--dump", "0xd418:1"],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd418"], [0x07], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd015"][0] & 0x08, 0x08, msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_SIDSPR1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_sidspr_runtime_wrappers_handle_multiword_spritepos_and_sidfreq_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-wrapper-multiword"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "obj").mkdir(exist_ok=True)
            (project_root / "lib").mkdir(exist_ok=True)
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 28\n"
                "b p4p5u2p0p1u0p2p3u1r\n"
                "u rt_sprite_pos\n"
                "u rt_sid_freq\n"
                "u rt_sprite_data\n"
                "i 300\n"
                "i 552\n"
                "i 13398\n"
                "i 2\n"
                "i 832\n"
                "i 2\n"
                "k 0\n"
                "n main\n",
                encoding="ascii",
            )
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avm_path = Path(
                [
                    op
                    for op in alink.get("ops", [])
                    if str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM")
                ][-1]["full_path"]
            )
            avm_bytes = avm_path.read_bytes()
            payload_len = avm_bytes[5] | (avm_bytes[6] << 8)
            payload = avm_bytes[12 : 12 + payload_len]
            self.assertIn(bytes((0x49, 0x03, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x04, 0xFD)), payload)
            self.assertIn(bytes((0x49, 0x10, 0xFD)), payload)

            helper_path = image_root / "RT_SIDSPR1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0x07fa:1",
                    "--dump", "0xd004:1",
                    "--dump", "0xd005:1",
                    "--dump", "0xd010:1",
                    "--dump", "0xd40e:1",
                    "--dump", "0xd40f:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x07fa"], [0x0D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd004"], [0x2C], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd005"], [0x28], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd010"][0] & 0x04, 0x04, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd40e"], [0x56], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd40f"], [0x34], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_SIDSPR1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_sidspr_runtime_pipeline_forms_coherent_basic_sprite_demo_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_SIDSPR1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 4)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_sidspr_sprite_on = 0xFD01
        intrinsic_linked_sidspr_sprite_pos = 0xFD03
        intrinsic_linked_sidspr_sprite_data = 0xFD04
        intrinsic_linked_sidspr_sprite_color = 0xFD05
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 0x40, 0x03,
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_sidspr_sprite_data & 0xFF, intrinsic_linked_sidspr_sprite_data >> 8,
                opcode_push16, 0x05, 0x02,
                opcode_calln, intrinsic_linked_sidspr_sprite_color & 0xFF, intrinsic_linked_sidspr_sprite_color >> 8,
                opcode_push16, 0x2C, 0x01,
                opcode_push16, 0x28, 0x02,
                opcode_calln, intrinsic_linked_sidspr_sprite_pos & 0xFF, intrinsic_linked_sidspr_sprite_pos >> 8,
                opcode_push16, 0x02, 0x00,
                opcode_calln, intrinsic_linked_sidspr_sprite_on & 0xFF, intrinsic_linked_sidspr_sprite_on >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(4)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-sprite-demo"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_SIDSPR1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0x07fa:1",
                    "--dump", "0xd004:1",
                    "--dump", "0xd005:1",
                    "--dump", "0xd010:1",
                    "--dump", "0xd015:1",
                    "--dump", "0xd029:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0x07fa"], [0x0D], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd004"], [0x2C], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd005"], [0x28], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd010"][0] & 0x04, 0x04, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd015"][0] & 0x04, 0x04, msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd029"], [0x05], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_SIDSPR1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_sidspr_runtime_pipeline_updates_wave_adsr_gate_and_sprite_color_under_compat_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_avm_helper_assets_udos.sh",
        )

        helper_blob = (self.root / "build" / "udos_tools" / "RT_SIDSPR1_HELPER.BIN").read_bytes()
        self.assertEqual(helper_blob[:4], b"AVNH")
        self.assertEqual(helper_blob[4], 1)
        self.assertEqual(helper_blob[5], 4)

        opcode_push16 = 0x11
        opcode_calln = 0x49
        intrinsic_linked_sidspr_sprite_color = 0xFD05
        intrinsic_linked_sidspr_sid_wave = 0xFD11
        intrinsic_linked_sidspr_sid_ad = 0xFD12
        intrinsic_linked_sidspr_sid_sr = 0xFD13
        intrinsic_linked_sidspr_sid_on = 0xFD14
        intrinsic_linked_sidspr_sid_off = 0xFD15
        intrinsic_exit = 0xFF20
        avm_version_v2 = 2
        avm_flag_acheron = 1
        avm_flag_native_helpers = 2

        exec_code = bytearray(
            [
                opcode_push16, 5, 3,
                opcode_calln, intrinsic_linked_sidspr_sprite_color & 0xFF, intrinsic_linked_sidspr_sprite_color >> 8,
                opcode_push16, 0x20, 0,
                opcode_calln, intrinsic_linked_sidspr_sid_wave & 0xFF, intrinsic_linked_sidspr_sid_wave >> 8,
                opcode_push16, 0, 0,
                opcode_calln, intrinsic_linked_sidspr_sid_on & 0xFF, intrinsic_linked_sidspr_sid_on >> 8,
                opcode_push16, 0x40, 1,
                opcode_calln, intrinsic_linked_sidspr_sid_wave & 0xFF, intrinsic_linked_sidspr_sid_wave >> 8,
                opcode_push16, 1, 0,
                opcode_calln, intrinsic_linked_sidspr_sid_on & 0xFF, intrinsic_linked_sidspr_sid_on >> 8,
                opcode_push16, 0xAB, 2,
                opcode_calln, intrinsic_linked_sidspr_sid_ad & 0xFF, intrinsic_linked_sidspr_sid_ad >> 8,
                opcode_push16, 0xCD, 1,
                opcode_calln, intrinsic_linked_sidspr_sid_sr & 0xFF, intrinsic_linked_sidspr_sid_sr >> 8,
                opcode_push16, 0, 0,
                opcode_calln, intrinsic_linked_sidspr_sid_off & 0xFF, intrinsic_linked_sidspr_sid_off >> 8,
                opcode_calln, intrinsic_exit & 0xFF, intrinsic_exit >> 8,
            ]
        )
        payload = bytes(exec_code)
        trailer = bytearray(b"AVH1")
        trailer.append(1)
        trailer.append(4)
        trailer.extend((len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF))
        trailer.extend(helper_blob)
        header = bytearray(b"AVM1")
        header.append(avm_version_v2)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        header.extend((0x00, 0x00))
        header.append(avm_flag_acheron | avm_flag_native_helpers)
        header.extend((len(payload) & 0xFF, (len(payload) >> 8) & 0xFF))
        avm_bytes = bytes(header + payload + trailer)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-sidspr-compat-2"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text("MODULE MAIN\rPROC MAIN()\rRETURN\r", encoding="ascii")
            (project_root / "bin").mkdir(exist_ok=True)
            (project_root / "bin" / "MAIN.AVM").write_bytes(avm_bytes)

            helper_path = image_root / "RT_SIDSPR1_HELPER.BIN"
            if helper_path.exists():
                helper_path.unlink()

            result = self.run_harness_process(
                self.compat_avmrun_prg,
                project_root,
                "BIN/MAIN.AVM",
                self.compat_avmrun_labels,
                extra=[
                    "--dump", "0xd02a:1",
                    "--dump", "0xd404:1",
                    "--dump", "0xd40b:1",
                    "--dump", "0xd40d:1",
                    "--dump", "0xd413:1",
                ],
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 0, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "", msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd02a"], [0x05], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd404"], [0x20], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd40b"], [0x41], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd40d"], [0xCD], msg=avmrun)
            self.assertEqual(avmrun["dumps"]["0xd413"], [0xAB], msg=avmrun)
            staged_paths = {op.get("path") for op in avmrun.get("ops", []) if op.get("kind") == "rsta"}
            self.assertNotIn("!RT_SIDSPR1_HELPER.BIN", staged_paths, msg=avmrun)
            self.assertIn("!AVMRUN_OVL3.BIN", staged_paths, msg=avmrun)

    def test_standard_printe_native_fast_path_reports_harness_no_acheron_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-std-printe-fast"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "PROC MAIN()\r"
                'PrintE("HELLO")\r'
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            result = self.run_harness_process(self.prod_avmrun_prg, project_root, "BIN/MAIN.AVM", self.prod_avmrun_labels)
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 1, msg=avmrun)
            self.assertTrue(avmrun.get("exited", False), msg=avmrun)
            self.assertFalse(avmrun.get("hit_limit", False), msg=avmrun)
            self.assertEqual(avmrun.get("console", ""), "HARNESS NO ACHERON\n", msg=avmrun)

    def test_alink_emits_helper_free_prg_that_reaches_resident_acheron_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "PROC A()\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "A()\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(prg_bytes[12:15], bytes((0x20, 0x3F, 0xCF)))
            self.assertEqual(prg_bytes[23:26], bytes((0x4C, 0x0F, 0xCF)))
            self.assertEqual(prg_bytes[-7:], bytes((0x48, 0x45, 0x20, 0x10, 0x49, 0x18, 0x10)))

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 1, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "HARNESS NO ACHERON\n", msg=native_prg)

    def test_alink_emits_helper_free_fanout_prg_that_reaches_resident_acheron_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-fanout"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "PROC A()\r"
                "RETURN\r"
                "PROC B()\r"
                "A()\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "A()\r"
                "B()\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(prg_bytes[12:15], bytes((0x20, 0x3F, 0xCF)))
            self.assertEqual(prg_bytes[23:26], bytes((0x4C, 0x0F, 0xCF)))
            self.assertEqual(prg_bytes[-14:], bytes((0x48, 0x45, 0x20, 0x10, 0x48, 0x45, 0x20, 0x10, 0x45, 0x21, 0x10, 0x49, 0x18, 0x10)))

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 1, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "HARNESS NO ACHERON\n", msg=native_prg)

    def test_alink_emits_helper_free_seeded_word_store_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-word-store"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "obj" / "MAIN.OBJ",
                project_root / "obj" / "main.obj",
                project_root / "MAIN.OBJ",
                project_root / "main.obj",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "obj" / "MAIN.OBJ").write_text(
                "AVO1\n"
                "x main 0 7\n"
                "b p0S0r\n"
                "i 7\n"
                "v x 0\n",
                encoding="ascii",
            )

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )
            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A907A2008D22108E23108DD1038ED203A9A58DD003A90085028503A2024C0FCF00000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_word_load_store_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-word-load-store"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=7\r"
                "Y=X\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0L0S1r\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A907A2008D2E108E2F10AD2E10AE2F108D30108E31108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=7\r"
                "IF X=7 THEN\r"
                "Y=1\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0L0p1qhp2S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A907A2008D49108E4A10AD4910AE4A108D47108E4810A907A200EC4810D005CD4710F0034C3110A901A2008D4B108E4C108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_lt_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-lt"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=2\r"
                "IF X<Y THEN\r"
                "Y=3\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1lhp2S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D65108E6610A902A2008D67108E6810AD6510AE66108D63108E6410AD6710AE6810EC6410900DD007CD63109006F004A901D002A900A200C900D0034C4D10A903A2008D67108E68108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_gt_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-gt"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=2\r"
                "Y=1\r"
                "IF X>Y THEN\r"
                "Y=3\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1ghp2S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A902A2008D65108E6610A901A2008D67108E6810AD6510AE66108D63108E6410AD6710AE6810EC64109007D00DCD63109002F004A901D002A900A200C900D0034C4D10A903A2008D67108E68108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_ge_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-ge"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=2\r"
                "Y=1\r"
                "IF X>=Y THEN\r"
                "Y=3\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1lp2qhp3S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A902A2008D75108E7610A901A2008D77108E7810AD7510AE76108D73108E7410AD7710AE7810EC7410900DD007CD73109006F004A901D002A900A2008D73108E7410A900A200EC7410D005CD7310F0034C5D10A903A2008D77108E78108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_ne_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-ne"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=2\r"
                "Y=1\r"
                "IF X<>Y THEN\r"
                "Y=3\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1nhp2S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A902A2008D61108E6210A901A2008D63108E6410AD6110AE62108D5F108E6010AD6310AE6410EC6010D005CD5F10F004A901D002A900A200C900D0034C4910A903A2008D63108E64108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_le_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-le"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=1\r"
                "IF X<=Y THEN\r"
                "Y=3\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1gp2qhp3S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D75108E7610A901A2008D77108E7810AD7510AE76108D73108E7410AD7710AE7810EC74109007D00DCD73109002F004A901D002A900A2008D73108E7410A900A200EC7410D005CD7310F0034C5D10A903A2008D77108E78108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=7\r"
                "IF X=8 THEN\r"
                "Y=1\r"
                "ELSE\r"
                "Y=2\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0L0p1qhp2S1wp3S1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A907A2008D56108E5710AD5610AE57108D54108E5510A908A200EC5510D005CD5410F0034C3410A901A2008D58108E59104C3E10A902A2008D58108E59108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_if_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-if"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "CARD Z\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=2\r"
                "IF X<Y THEN\r"
                "IF Y>1 THEN\r"
                "Z=3\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1lhL1p2ghp3S2vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D92108E9310A902A2008D94108E9510AD9210AE93108D90108E9110AD9410AE9510EC9110900DD007CD90109006F004A901D002A900A200C900D0034C7A10AD9410AE95108D90108E9110A901A200EC91109007D00DCD90109002F004A901D002A900A200C900D0034C7A10A903A2008D96108E97108DD1038ED203A9A58DD003A90085028503A2024C0FCF0000000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "CARD Z\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=2\r"
                "IF X<Y THEN\r"
                "IF Y>2 THEN\r"
                "Z=3\r"
                "ELSE\r"
                "Z=4\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0L1lhL1p2ghp3S2wp4S2vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D9F108EA010A902A2008DA1108EA210AD9F10AEA0108D9D108E9E10ADA110AEA210EC9E10900DD007CD9D109006F004A901D002A900A200C900D0034C8710ADA110AEA2108D9D108E9E10A902A200EC9E109007D00DCD9D109002F004A901D002A900A200C900D0034C7D10A903A2008DA3108EA4104C8710A904A2008DA3108EA4108DD1038ED203A9A58DD003A90085028503A2024C0FCF0000000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=0\r"
                "Y=0\r"
                "DO\r"
                "X=1\r"
                "DO\r"
                "Y=2\r"
                "UNTIL Y=2\r"
                "OD\r"
                "UNTIL X=1\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1dp2S0dp3S1L1p4qtoL0p5qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008D7A108E7B10A900A2008D7C108E7D10A901A2008D7A108E7B10A902A2008D7C108E7D10AD7C10AE7D108D78108E7910A902A200EC7910D005CD7810F0034C1E10AD7A10AE7B108D78108E7910A901A200EC7910D005CD7810F0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_do_if_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-do-if-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=0\r"
                "Y=0\r"
                "DO\r"
                "X=1\r"
                "IF X=1 THEN\r"
                "Y=2\r"
                "FI\r"
                "UNTIL Y=2\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1dp2S0L0p3qhp4S1vL1p5qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008D7A108E7B10A900A2008D7C108E7D10A901A2008D7A108E7B10AD7A10AE7B108D78108E7910A901A200EC7910D005CD7810F0034C4510A902A2008D7C108E7D10AD7C10AE7D108D78108E7910A902A200EC7910D005CD7810F0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_do_if_else_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-do-if-else-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=0\r"
                "Y=0\r"
                "DO\r"
                "X=1\r"
                "IF X=2 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=4\r"
                "FI\r"
                "UNTIL Y=4\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1dp2S0L0p3qhp4S1wp5S1vL1p6qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008D87108E8810A900A2008D89108E8A10A901A2008D87108E8810AD8710AE88108D85108E8610A902A200EC8610D005CD8510F0034C4810A903A2008D89108E8A104C5210A904A2008D89108E8A10AD8910AE8A108D85108E8610A904A200EC8610D005CD8510F0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "DO\r"
                "Y=2\r"
                "UNTIL Y=2\r"
                "OD\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0p2qhdp3S1L1p4qtovr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D70108E7110A900A2008D72108E7310AD7010AE71108D6E008E6F00A901A200EC6F00D005CD6E00F0034C5810A902A2008D72108E7310AD7210AE73108D6E008E6F00A902A200EC6F00D005CD6E00F0034C31108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_else_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-else-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=2 THEN\r"
                "DO\r"
                "Y=3\r"
                "UNTIL Y=3\r"
                "OD\r"
                "ELSE\r"
                "DO\r"
                "Y=4\r"
                "UNTIL Y=4\r"
                "OD\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1L0p2qhdp3S1L1p4qtowdp5S1L1p6qtovr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D9A108E9B10A900A2008D9C108E9D10AD9A10AE9B108D98108E9910A902A200EC9910D005CD9810F0034C5B10A903A2008D9C108E9D10AD9C10AE9D108D98108E9910A903A200EC9910D005CD9810F0034C31104C8210A904A2008D9C108E9D10AD9C10AE9D108D98108E9910A904A200EC9910D005CD9810F0034C5B108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_local_call_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-local-call-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "DO\r"
                "Y=2\r"
                "UNTIL Y=2\r"
                "OD\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "A()\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 17\n", object_text)
            self.assertIn("x main 17 26\n", object_text)
            self.assertIn("b dp0S1L1p1qtor\n", object_text)
            self.assertIn("b p2S0p3S1L0p4qhc0vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D74108E7510A900A2008D76108E7710AD7410AE75108D72008E7300A901A200EC7300D005CD7200F0034C3410204A108DD1038ED203A9A58DD003A90085028503A2024C0FCFA902A2008D76108E7710AD7610AE77108D4A008E4B00A902A200EC4B00D005CD4A00F0034C001060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_else_local_call_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-else-local-call-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "DO\r"
                "Y=4\r"
                "UNTIL Y=4\r"
                "OD\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=2 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 17\n", object_text)
            self.assertIn("x main 17 35\n", object_text)
            self.assertIn("b dp0S1L1p1qtor\n", object_text)
            self.assertIn("b p2S0p3S1L0p4qhp5S1wc0vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D81108E8210A900A2008D83108E8410AD8110AE82108D7F008E8000A902A200EC8000D005CD7F00F0034C3E10A903A2008D83108E84104C41102057108DD1038ED203A9A58DD003A90085028503A2024C0FCFA904A2008D83108E8410AD8310AE84108D57008E5800A904A200EC5800D005CD5700F0034C001060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_if_local_call_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-if-local-call"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "Y=5\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "IF Y=0 THEN\r"
                "A()\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 7\n", object_text)
            self.assertIn("x main 7 36\n", object_text)
            self.assertIn("b p0S1r\n", object_text)
            self.assertIn("b p1S0p2S1L0p3qhL1p4qhc0vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D74108E7510A900A2008D76108E7710AD7410AE75108D72008E7300A901A200EC7300D005CD7200F0034C5110AD7610AE77108D72008E7300A900A200EC7300D005CD7200F0034C51102067108DD1038ED203A9A58DD003A90085028503A2024C0FCFA905A2008D76108E771060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_else_local_call_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-else-local-call"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "Y=6\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 7\n", object_text)
            self.assertIn("x main 7 45\n", object_text)
            self.assertIn("b p0S1r\n", object_text)
            self.assertIn("b p1S0p2S1L0p3qhL1p4qhp5S1wc0vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D81108E8210A900A2008D83108E8410AD8110AE82108D7F008E8000A901A200EC8000D005CD7F00F0034C5E10AD8310AE84108D7F008E8000A901A200EC8000D005CD7F00F0034C5B10A903A2008D83108E84104C5E102074108DD1038ED203A9A58DD003A90085028503A2024C0FCFA906A2008D83108E841060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_do_local_call_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-do-local-call"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "Y=7\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=0\r"
                "Y=0\r"
                "DO\r"
                "X=1\r"
                "DO\r"
                "A()\r"
                "UNTIL Y=7\r"
                "OD\r"
                "UNTIL X=1\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 7\n", object_text)
            self.assertIn("x main 7 42\n", object_text)
            self.assertIn("b p0S1r\n", object_text)
            self.assertIn("b p1S0p2S1dp3S0dc0L1p4qtoL0p5qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008D7E108E7F10A900A2008D80108E8110A901A2008D7E108E7F10207110AD8010AE81108D71008E7200A907A200EC7200D005CD7100F0034C1E10AD7E10AE7F108D71008E7200A901A200EC7200D005CD7100F0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCFA907A2008D80108E811060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_do_if_else_local_call_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-do-if-else-local-call"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "Y=8\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=0\r"
                "Y=0\r"
                "DO\r"
                "X=1\r"
                "DO\r"
                "IF X=2 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "UNTIL Y=8\r"
                "OD\r"
                "UNTIL X=1\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 7\n", object_text)
            self.assertIn("x main 7 61\n", object_text)
            self.assertIn("b p0S1r\n", object_text)
            self.assertIn("b p1S0p2S1dp3S0dL0p4qhp5S1wc0vL1p6qtoL0p7qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008DA8108EA910A900A2008DAA108EAB10A901A2008DA8108EA910ADA810AEA9108DA6008EA700A902A200ECA700D005CDA600F0034C4810A903A2008DAA108EAB104C4B10209B10ADAA10AEAB108D9B008E9C00A908A200EC9C00D005CD9B00F0034C1E10ADA810AEA9108D9B008E9C00A901A200EC9C00D005CD9B00F0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCFA908A2008DAA108EAB1060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_local_call_nested_do_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-local-call-nested-do-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "DO\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=9\r"
                "FI\r"
                "UNTIL Y=9\r"
                "OD\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "A()\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 36\n", object_text)
            self.assertIn("x main 36 26\n", object_text)
            self.assertIn("b dL1p0qhp1S1wp2S1vL1p3qtor\n", object_text)
            self.assertIn("b p4S0p5S1L0p6qhc0vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D9E108E9F10A900A2008DA0108EA110AD9E10AE9F108D9C008E9D00A901A200EC9D00D005CD9C00F0034C3410204A108DD1038ED203A9A58DD003A90085028503A2024C0FCFADA010AEA1108D4A008E4B00A901A200EC4B00D005CD4A00F0034C7410A903A2008DA0108EA1104C7E10A909A2008DA0108EA110ADA010AEA1108D4A008E4B00A909A200EC4B00D005CD4A00F0034C4A1060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_else_local_call_nested_do_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-else-local-call-nested-do-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "DO\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=10\r"
                "FI\r"
                "UNTIL Y=10\r"
                "OD\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=2 THEN\r"
                "Y=4\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 36\n", object_text)
            self.assertIn("x main 36 35\n", object_text)
            self.assertIn("b dL1p0qhp1S1wp2S1vL1p3qtor\n", object_text)
            self.assertIn("b p4S0p5S1L0p6qhp7S1wc0vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008DAB108EAC10A900A2008DAD108EAE10ADAB10AEAC108DA9008EAA00A902A200ECAA00D005CDA900F0034C3E10A904A2008DAD108EAE104C41102057108DD1038ED203A9A58DD003A90085028503A2024C0FCFADAD10AEAE108D57008E5800A901A200EC5800D005CD5700F0034C8110A903A2008DAD108EAE104C8B10A90AA2008DAD108EAE10ADAD10AEAE108D57008E5800A90AA200EC5800D005CD5700F0034C571060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_else_local_call_nested_do_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-else-local-call-nested-do-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC A()\r"
                "DO\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=11\r"
                "FI\r"
                "UNTIL Y=11\r"
                "OD\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "IF Y=1 THEN\r"
                "Y=4\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x a 0 36\n", object_text)
            self.assertIn("x main 36 45\n", object_text)
            self.assertIn("b dL1p0qhp1S1wp2S1vL1p3qtor\n", object_text)
            self.assertIn("b p4S0p5S1L0p6qhL1p7qhp8S1wc0vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008DC8108EC910A900A2008DCA108ECB10ADC810AEC9108DC6008EC700A901A200ECC700D005CDC600F0034C5E10ADCA10AECB108D00008E0100A901A200EC0100D005CD0000F0034C5B10A904A2008DCA108ECB104C5E102074108DD1038ED203A9A58DD003A90085028503A2024C0FCFADCA10AECB108D74008E7500A901A200EC7500D005CD7400F0034C9E10A903A2008DCA108ECB104CA810A90BA2008DCA108ECB10ADCA10AECB108D74008E7500A90BA200EC7500D005CD7400F0034C741060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_if_else_local_call_chain_nested_do_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-if-else-local-call-chain-nested-do-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC B()\r"
                "DO\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=12\r"
                "FI\r"
                "UNTIL Y=12\r"
                "OD\r"
                "RETURN\r"
                "PROC A()\r"
                "B()\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=2 THEN\r"
                "Y=4\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x b 0 36\n", object_text)
            self.assertIn("x a 36 4\n", object_text)
            self.assertIn("x main 40 35\n", object_text)
            self.assertIn("b dL1p0qhp1S1wp2S1vL1p3qtor\n", object_text)
            self.assertIn("b c0r\n", object_text)
            self.assertIn("b p4S0p5S1L0p6qhp7S1wc1vr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008DAF108EB010A900A2008DB1108EB210ADAF10AEB0108DAD008EAE00A902A200ECAE00D005CDAD00F0034C3E10A904A2008DB1108EB2104C411020A9108DD1038ED203A9A58DD003A90085028503A2024C0FCFADB110AEB2108DA9008EAA00A901A200ECAA00D005CDA900F0034C8110A903A2008DB1108EB2104C8B10A90CA2008DB1108EB210ADB110AEB2108D57008E5800A90CA200EC5800D005CD5700F0034C57106020571060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_nested_else_local_call_chain_nested_do_if_else_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-nested-else-local-call-chain-nested-do-if-else"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC B()\r"
                "DO\r"
                "IF Y=1 THEN\r"
                "Y=3\r"
                "ELSE\r"
                "Y=13\r"
                "FI\r"
                "UNTIL Y=13\r"
                "OD\r"
                "RETURN\r"
                "PROC A()\r"
                "B()\r"
                "RETURN\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=0\r"
                "IF X=1 THEN\r"
                "IF Y=1 THEN\r"
                "Y=4\r"
                "ELSE\r"
                "A()\r"
                "FI\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("x b 0 36\n", object_text)
            self.assertIn("x a 36 4\n", object_text)
            self.assertIn("x main 40 45\n", object_text)
            self.assertIn("b dL1p0qhp1S1wp2S1vL1p3qtor\n", object_text)
            self.assertIn("b c0r\n", object_text)
            self.assertIn("b p4S0p5S1L0p6qhL1p7qhp8S1wc1vvr\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008DCC108ECD10A900A2008DCE108ECF10ADCC10AECD108DCA008ECB00A901A200ECCB00D005CDCA00F0034C5E10ADCE10AECF108D00008E0100A901A200EC0100D005CD0000F0034C5B10A904A2008DCE108ECF104C5E1020C6108DD1038ED203A9A58DD003A90085028503A2024C0FCFADCE10AECF108DC6008EC700A901A200ECC700D005CDC600F0034C9E10A903A2008DCE108ECF104CA810A90DA2008DCE108ECF10ADCE10AECF108D74008E7500A90DA200EC7500D005CD7400F0034C74106020741060000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_do_until_eq_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-do-until-eq"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "PROC MAIN()\r"
                "X=0\r"
                "DO\r"
                "X=1\r"
                "UNTIL X=1\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0dp1S0L0p2qtor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A900A2008D49108E4A10A901A2008D49108E4A10AD4910AE4A108D47108E4810A901A200EC4810D005CD4710F0034C0A108DD1038ED203A9A58DD003A90085028503A2024C0FCF00000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)

    def test_alink_emits_helper_free_compiled_do_until_lt_prg_that_exits_natively_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-alink-prg-do-until-lt"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            for stale in (
                project_root / "bin" / "MAIN.PRG",
                project_root / "bin" / "main.prg",
                project_root / "bin" / "MAIN.AVM",
                project_root / "bin" / "main.avm",
                project_root / "MAIN.PRG",
                project_root / "main.prg",
                project_root / "MAIN.AVM",
                project_root / "main.avm",
            ):
                if stale.exists():
                    stale.unlink()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "CARD X\r"
                "CARD Y\r"
                "PROC MAIN()\r"
                "X=1\r"
                "Y=2\r"
                "DO\r"
                "X=1\r"
                "UNTIL X<Y\r"
                "OD\r"
                "RETURN\r",
                encoding="ascii",
            )

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p0S0p1S1dp2S0L0L1ltor\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            self.assertTrue(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.PRG") for op in alink.get("ops", [])),
                msg=alink,
            )
            self.assertFalse(
                any(str(op.get("full_path", "")).upper().endswith("/BIN/MAIN.AVM") for op in alink.get("ops", [])),
                msg=alink,
            )

            prg_path = project_root / "bin" / "MAIN.PRG"
            self.assertTrue(prg_path.is_file(), msg=alink)
            prg_bytes = prg_path.read_bytes()
            self.assertEqual(prg_bytes[:2], b"\x00\x10")
            self.assertEqual(
                prg_bytes[2:],
                bytes.fromhex("A901A2008D65108E6610A902A2008D67108E6810A901A2008D65108E6610AD6510AE66108D63108E6410AD6710AE6810EC6410900DD007CD63109006F004A901D002A900A200C900D0034C14108DD1038ED203A9A58DD003A90085028503A2024C0FCF000000000000"),
            )

            result = subprocess.run(
                [
                    str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                    "--prg",
                    str(prg_path),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "",
                    "--services-inc",
                    str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                    "--entry-addr",
                    "0x1000",
                    "--max-steps",
                    "12000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, msg=output)
            native_prg = json.loads(result.stdout)
            self.assertEqual(native_prg["exit_status"], 0, msg=native_prg)
            self.assertTrue(native_prg.get("exited", False), msg=native_prg)
            self.assertFalse(native_prg.get("hit_limit", False), msg=native_prg)
            self.assertEqual(native_prg.get("console", ""), "", msg=native_prg)


    def test_real_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("b p1u0T0S0p3u0T1S1L0U0L1U1u1T2S2L2U2p4u2r\n", object_text)
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.prod_avmrun_prg, project_root, "BIN/MAIN.AVM", self.prod_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1.5\n")

    def test_real_fractional_print_runtime_pipeline_handles_quarters_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-quarter"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "X=A/B\r"
                "X=X/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.75\n")

    def test_real_fractional_print_runtime_pipeline_handles_negative_half_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-negative-half"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(N)\r"
                "B=REAL(2)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-0.5\n")

    def test_real_fractional_print_runtime_pipeline_handles_eighths_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-eighth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(8)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.125\n")

    def test_real_print_runtime_pipeline_uses_program_owned_helper_without_sidecars_or_overlays(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-native-only"
            shutil.copytree(self.base_fs, out_fs)
            image_root = out_fs / "IMAGES" / "ACTION.DNP"
            project_root = image_root / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(8)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)

            for helper_name in (
                "RT_PRINT_F_HELPER.BIN",
                "RT_PRINT_STD_HELPER.BIN",
                "AVMRUN_OVL1.BIN",
                "AVMRUN_OVL2.BIN",
                "AVMRUN_OVL3.BIN",
            ):
                helper_path = image_root / helper_name
                if helper_path.exists():
                    helper_path.unlink()

            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.125\n")

    def test_real_fractional_print_runtime_pipeline_handles_lowword_nonzero_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-lowword-nonzero"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(129)\r"
                "B=REAL(256)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.50390625\n")

    def test_real_fractional_print_runtime_pipeline_handles_thirtyseconds_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-thirtysecond"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(32)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.03125\n")

    def test_real_fractional_print_runtime_pipeline_handles_sixtyfourths_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-sixtyfourth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(64)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.015625\n")

    def test_real_fractional_print_runtime_pipeline_handles_twohundredfiftysixths_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-twohundredfiftysixth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(256)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.00390625\n")

    def test_real_fractional_print_runtime_pipeline_handles_thirtytwothousandsevenhundredsixtyeighths_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-print-thirtytwothousandsevenhundredsixtyeighth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(32768)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.000030517578125\n")

    def test_real_add_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-print-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "X=A/B\r"
                "A=A/B\r"
                "X=X+A\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_add\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_add_gap_two_mixed_sign_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-print-gap-two-mixed-sign"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(4)\r"
                "B=REAL(N)\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_add\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_add_gap_two_mixed_sign_negative_result_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-print-gap-two-mixed-sign-negative"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-4\r"
                "A=REAL(1)\r"
                "B=REAL(N)\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_add\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-3\n")

    def test_real_add_gap_two_mixed_sign_swapped_operands_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-print-gap-two-mixed-sign-swapped"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(N)\r"
                "B=REAL(4)\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_add\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_sub_gap_two_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-sub-print-gap-two"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(4)\r"
                "B=REAL(1)\r"
                "X=A-B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_sub\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_sub_gap_two_mixed_sign_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-sub-print-gap-two-mixed-sign"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(4)\r"
                "B=REAL(N)\r"
                "X=A-B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_sub\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "5\n")

    def test_real_sub_gap_two_negative_result_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-sub-print-gap-two-negative"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(N)\r"
                "B=REAL(4)\r"
                "X=A-B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_sub\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-5\n")

    def test_real_add_adjacent_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-adjacent-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=REAL(2)\r"
                "B=A/B\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_add\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.75\n")

    def test_real_sub_adjacent_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-sub-adjacent-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=REAL(2)\r"
                "B=A/B\r"
                "X=A-B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_sub\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.25\n")

    def test_real_mul_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_mul_one_point_five_by_one_point_five_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-one-point-five-square"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=A\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "2.25\n")

    def test_real_div_one_point_five_by_one_point_five_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-one-point-five-over-one-point-five"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=A\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_mul_three_quarters_by_three_quarters_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-three-quarters-square"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(4)\r"
                "A=A/B\r"
                "B=A\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5625\n")

    def test_real_div_one_point_five_by_three_quarters_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-one-point-five-over-three-quarters"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=REAL(3)\r"
                "X=REAL(4)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "2\n")

    def test_real_div_one_by_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-one-third"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(3)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.3333333432674407958984375\n")

    def test_real_div_one_by_ten_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-one-tenth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.100000001490116119384765625\n")

    def test_real_div_one_by_three_times_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-third-times-three"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(3)\r"
                "A=A/B\r"
                "B=REAL(3)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_div_one_by_ten_times_ten_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-tenth-times-ten"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(10)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_div_two_by_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-three"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(3)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.666666686534881591796875\n")

    def test_real_div_one_by_seven_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-seven"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(7)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.14285714924335479736328125\n")

    def test_real_mul_one_fifth_by_one_fifth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-fifth-by-one-fifth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL C\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(5)\r"
                "A=A/B\r"
                "C=REAL(1)\r"
                "B=REAL(5)\r"
                "C=C/B\r"
                "X=A*C\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.0400000028312206268310546875\n")

    def test_real_div_six_fifths_by_three_tenths_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-six-fifths-by-three-tenths"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(6)\r"
                "B=REAL(5)\r"
                "A=A/B\r"
                "B=REAL(3)\r"
                "X=REAL(10)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "4\n")

    def test_real_div_one_by_nine_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-nine"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(9)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.111111111938953399658203125\n")

    def test_real_div_two_by_nine_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-nine"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(9)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.22222222387790679931640625\n")

    def test_real_mul_one_by_seven_times_seven_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-seven-times-seven"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(7)\r"
                "A=A/B\r"
                "B=REAL(7)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_mul_one_by_nine_times_nine_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-nine-times-nine"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(9)\r"
                "A=A/B\r"
                "B=REAL(9)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_div_one_tenth_by_one_fifth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-tenth-by-one-fifth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(5)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5\n")

    def test_real_div_one_by_eleven_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-eleven"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(11)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.0909090936183929443359375\n")

    def test_real_div_two_by_eleven_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-eleven"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(11)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.181818187236785888671875\n")

    def test_real_mul_one_by_eleven_times_eleven_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-eleven-times-eleven"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(11)\r"
                "A=A/B\r"
                "B=REAL(11)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_add_one_tenth_plus_one_fifth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-one-tenth-plus-one-fifth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(5)\r"
                "B=B/X\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.300000011920928955078125\n")

    def test_real_sub_one_half_minus_one_tenth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-sub-one-half-minus-one-tenth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(10)\r"
                "B=B/X\r"
                "X=A-B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.4000000059604644775390625\n")

    def test_real_add_sub_chain_cancels_cleanly_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-sub-chain-cancels-cleanly"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL C\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(10)\r"
                "B=B/X\r"
                "C=REAL(1)\r"
                "X=REAL(5)\r"
                "C=C/X\r"
                "X=A+B\r"
                "X=X-C\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0\n")

    def test_real_div_one_by_thirteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-thirteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(13)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.076923079788684844970703125\n")

    def test_real_div_two_by_thirteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-thirteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(13)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.15384615957736968994140625\n")

    def test_real_mul_one_by_thirteen_times_thirteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-thirteen-times-thirteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(13)\r"
                "A=A/B\r"
                "B=REAL(13)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_add_non_dyadic_chain_to_half_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-non-dyadic-chain-to-half"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(5)\r"
                "B=B/X\r"
                "X=A+B\r"
                "B=REAL(1)\r"
                "A=REAL(5)\r"
                "B=B/A\r"
                "X=X+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5\n")

    def test_real_add_three_tenths_times_ten_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-three-tenths-times-ten"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(10)\r"
                "B=B/X\r"
                "X=A+B\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "X=X+A\r"
                "A=REAL(10)\r"
                "X=X*A\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_add_two_thirteenths_plus_one_thirteenth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-two-thirteenths-plus-one-thirteenth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(13)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(13)\r"
                "B=B/X\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.2307692468166351318359375\n")

    def test_real_div_one_by_seventeen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-seventeen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(17)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.0588235296308994293212890625\n")

    def test_real_div_two_by_seventeen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-seventeen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(17)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.117647059261798858642578125\n")

    def test_real_mul_one_by_seventeen_times_seventeen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-seventeen-times-seventeen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(17)\r"
                "A=A/B\r"
                "B=REAL(17)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_add_two_seventeenths_plus_one_seventeenth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-two-seventeenths-plus-one-seventeenth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(17)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(17)\r"
                "B=B/X\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.17647059261798858642578125\n")

    def test_real_div_one_seventeenth_by_two_seventeenths_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-seventeenth-by-two-seventeenths"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(17)\r"
                "A=A/B\r"
                "B=REAL(2)\r"
                "X=REAL(17)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5\n")

    def test_real_div_one_by_nineteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-nineteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(19)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.052631579339504241943359375\n")

    def test_real_div_two_by_nineteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-nineteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(19)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.10526315867900848388671875\n")

    def test_real_mul_one_by_nineteen_times_nineteen_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-nineteen-times-nineteen"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(19)\r"
                "A=A/B\r"
                "B=REAL(19)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_add_two_nineteenths_plus_one_nineteenth_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-two-nineteenths-plus-one-nineteenth"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(19)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(19)\r"
                "B=B/X\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.15789473056793212890625\n")

    def test_real_div_one_nineteenth_by_two_nineteenths_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-nineteenth-by-two-nineteenths"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(19)\r"
                "A=A/B\r"
                "B=REAL(2)\r"
                "X=REAL(19)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5\n")

    def test_real_div_one_by_twenty_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-by-twenty-three"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(23)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.0434782616794109344482421875\n")

    def test_real_div_two_by_twenty_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-two-by-twenty-three"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(23)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.086956523358821868896484375\n")

    def test_real_mul_one_by_twenty_three_times_twenty_three_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-one-by-twenty-three-times-twenty-three"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(23)\r"
                "A=A/B\r"
                "B=REAL(23)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_add_two_twenty_thirds_plus_one_twenty_third_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-add-two-twenty-thirds-plus-one-twenty-third"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(2)\r"
                "B=REAL(23)\r"
                "A=A/B\r"
                "B=REAL(1)\r"
                "X=REAL(23)\r"
                "B=B/X\r"
                "X=A+B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.1304347813129425048828125\n")

    def test_real_div_one_twenty_third_by_two_twenty_thirds_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-one-twenty-third-by-two-twenty-thirds"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(23)\r"
                "A=A/B\r"
                "B=REAL(2)\r"
                "X=REAL(23)\r"
                "B=B/X\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0.5\n")

    def test_int_of_real_var_truncates_positive_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-positive"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_to_i\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_int_of_real_var_handles_positive_boundary_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-positive-boundary"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(32767)\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_to_i\n", object_text)
            self.assertIn("i 32767\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "32767\n")

    def test_int_of_real_var_handles_negative_boundary_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-negative-boundary"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(0-32768)\r"
                "X=INT(A)\r"
                "B=REAL(X)\r"
                "IF A=B THEN\r"
                "PrintIE(1)\r"
                "ENDIF\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_int_of_real_var_rejects_positive_overflow_runtime_pipeline_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-positive-overflow"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(32768)\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            result = self.run_harness_process(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 1)
            self.assertEqual(avmrun.get("console", ""), "REAL->INT RANGE\n")

    def test_int_of_real_var_rejects_negative_overflow_runtime_pipeline_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-negative-overflow"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(0-32768)\r"
                "B=REAL(1)\r"
                "A=A-B\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            result = self.run_harness_process(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            avmrun = json.loads(result.stdout)
            self.assertEqual(avmrun["exit_status"], 1)
            self.assertEqual(avmrun.get("console", ""), "REAL->INT RANGE\n")

    def test_int_of_real_var_truncates_negative_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-negative"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "INT X\r"
                "REAL A\r"
                "REAL B\r"
                "PROC MAIN()\r"
                "N=0-3\r"
                "A=REAL(N)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "X=INT(A)\r"
                "N=0-1\r"
                "IF X=N THEN\r"
                "PrintIE(1)\r"
                "ENDIF\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_to_i\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_int_of_real_non_dyadic_positive_fraction_truncates_to_zero_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-positive-third"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(3)\r"
                "A=A/B\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0\n")

    def test_int_of_real_non_dyadic_negative_fraction_truncates_to_zero_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-negative-third"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "N=0-1\r"
                "A=REAL(N)\r"
                "B=REAL(3)\r"
                "A=A/B\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "0\n")

    def test_int_of_real_non_dyadic_roundtrip_still_lands_on_one_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-int-of-real-one-tenth-times-ten"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "INT X\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(10)\r"
                "A=A/B\r"
                "B=REAL(10)\r"
                "A=A*B\r"
                "X=INT(A)\r"
                "PrintIE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1\n")

    def test_real_explicit_value_handles_positive_boundary_print_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-explicit-boundary-print"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "PROC MAIN()\r"
                "A=REAL(32767)\r"
                "PrintRE(A)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 32767\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "32767\n")

    def test_real_mul_negative_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-negative-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-3\r"
                "A=REAL(N)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-3\n")

    def test_real_mul_negative_fractional_swapped_operands_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-negative-fraction-swapped"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "N=0-2\r"
                "B=REAL(N)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-3\n")

    def test_real_mul_negative_fractional_both_negative_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-mul-print-both-negative-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-3\r"
                "A=REAL(N)\r"
                "B=REAL(2)\r"
                "A=A/B\r"
                "N=0-2\r"
                "B=REAL(N)\r"
                "X=A*B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_f_mul\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "3\n")

    def test_real_div_negative_fractional_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-negative-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-3\r"
                "A=REAL(N)\r"
                "B=REAL(2)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-1.5\n")

    def test_real_div_negative_fractional_swapped_operands_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-negative-fraction-swapped"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "A=REAL(3)\r"
                "N=0-2\r"
                "B=REAL(N)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-1.5\n")

    def test_real_div_negative_fractional_both_negative_print_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-div-print-both-negative-fraction"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "INT N=[0]\r"
                "REAL A\r"
                "REAL B\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "N=0-3\r"
                "A=REAL(N)\r"
                "N=0-2\r"
                "B=REAL(N)\r"
                "X=A/B\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_f_div\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "1.5\n")

    def test_real_compare_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-compare-prod-alink"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL A\r"
                "REAL B\r"
                "REAL C\r"
                "PROC MAIN()\r"
                "A=REAL(1)\r"
                "B=REAL(2)\r"
                "C=REAL(2)\r"
                "IF A<B THEN\r"
                "PrintE(\"LT\")\r"
                "FI\r"
                "IF B=C THEN\r"
                "PrintE(\"EQ\")\r"
                "FI\r"
                "IF C>=B THEN\r"
                "PrintE(\"GE\")\r"
                "FI\r"
                "IF A<>C THEN\r"
                "PrintE(\"NE\")\r"
                "FI\r"
                "IF B>A THEN\r"
                "PrintE(\"GT\")\r"
                "FI\r"
                "IF A<=B THEN\r"
                "PrintE(\"LE\")\r"
                "FI\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_f_cmp\n", object_text)
            self.assertIn("s LT\n", object_text)
            self.assertIn("s EQ\n", object_text)
            self.assertIn("s GE\n", object_text)
            self.assertIn("s NE\n", object_text)
            self.assertIn("s GT\n", object_text)
            self.assertIn("s LE\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels", max_steps=30000000)
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels, max_steps=50000000)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "LT\nEQ\nGE\nNE\nGT\nLE\n")

    def test_wide_real_mul_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-wide-mul"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=(128*2)\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "256\n")

    def test_wide_real_div_explicit_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-wide-div-explicit"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(512/2)\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "256\n")

    def test_wide_real_mul_explicit_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-wide-mul-explicit"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(128*2)\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_i_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 256\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "256\n")

    def test_signed_wide_real_mul_assignment_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-signed-wide-mul"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=0-(128*2)\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 65280\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-256\n")

    def test_signed_wide_real_mul_explicit_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-signed-wide-mul-explicit"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(0-(128*2))\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 65280\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-256\n")

    def test_signed_wide_real_div_explicit_conversion_runtime_pipeline_is_green_under_harness(self) -> None:
        self.build_harness_tools(
            "build_tool_abi_harness.sh",
            "build_actc_harness_udos.sh",
            "build_alink_harness_udos.sh",
            "build_avm_helper_assets_udos.sh",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "harness-real-signed-wide-div-explicit"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")
            (project_root / "src" / "main.act").write_text(
                "MODULE MAIN\r"
                "REAL X\r"
                "PROC MAIN()\r"
                "X=REAL(0-(512/2))\r"
                "PrintRE(X)\r"
                "RETURN\r",
                encoding="ascii",
            )
            (project_root / "lib").mkdir(exist_ok=True)
            for runtime_object in sorted((self.root / "src" / "runtime" / "udos_modules").glob("*.obj")):
                shutil.copy2(runtime_object, project_root / "lib" / runtime_object.name.upper())

            actc = self.run_harness_json("ACTC_HARNESS.PRG", project_root, "MAIN", "actc_harness.current.labels")
            self.assertEqual(actc["exit_status"], 0)
            object_path = Path([op for op in actc.get("ops", []) if op.get("kind") == "save"][-1]["full_path"])
            object_text = object_path.read_text(encoding="ascii")
            self.assertIn("u rt_s_to_f\n", object_text)
            self.assertIn("u rt_print_f\n", object_text)
            self.assertIn("i 65280\n", object_text)

            alink = self.run_harness_json("ALINK.PRG", project_root, "MAIN", "alink.current.labels")
            self.assertEqual(alink["exit_status"], 0)
            avmrun = self.run_harness_json(self.compat_avmrun_prg, project_root, "BIN/MAIN.AVM", self.compat_avmrun_labels)
            self.assertEqual(avmrun["exit_status"], 0)
            self.assertEqual(avmrun.get("console", ""), "-256\n")

    def test_int_vars_multi_while_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_while")

    def test_int_vars_multi_branch_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_branch_calls")

    def test_int_vars_multi_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_branch_shared_transitive")

    def test_int_vars_multi_while_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_while_shared_transitive")

    def test_int_vars_multi_add_rhs_var_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int_vars_multi_add_rhs_var")

    def test_return_local_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_local_basic")

    def test_return_local_add_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_local_add")

    def test_return_external_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_external_basic")

    def test_return_assign_local_var_expr_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_assign_local_var_expr")

    def test_return_condition_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_condition_external")

    def test_return_external_add_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_external_add")

    def test_bool_return_local_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_return_local")

    def test_local_args_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("local_args_basic")

    def test_local_args_multi_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("local_args_multi")

    def test_external_args_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("external_args_basic")

    def test_external_args_multi_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("external_args_multi")

    def test_nested_call_arg_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_call_arg")

    def test_if_local_args_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_local_args")

    def test_while_external_args_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_external_args")

    def test_bool_compound_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_compound")

    def test_bool_compound_args_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_compound_args")

    def test_bool_local_external_args_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_local_external_args")

    def test_bool_assign_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_assign_external")

    def test_bool_arg_local_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_arg_local_external")

    def test_printie_bool_compound_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printie_bool_compound")

    def test_printie_bool_local_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printie_bool_local_external")

    def test_printi_bool_compound_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printi_bool_compound")

    def test_return_bool_plus_one_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("return_bool_plus_one")

    def test_assign_bool_plus_one_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("assign_bool_plus_one")

    def test_arg_bool_plus_one_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("arg_bool_plus_one")

    def test_printie_bool_plus_one_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("printie_bool_plus_one")

    def test_init_bool_compound_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("init_bool_compound")

    def test_init_bool_plus_one_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("init_bool_plus_one")

    def test_proc_local_reinit_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("proc_local_reinit")

    def test_byte_proc_local_reinit_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("byte_proc_local_reinit")

    def test_proc_local_param_loop_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("proc_local_param_loop")

    def test_var16_module_slots_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("var16_module_slots")

    def test_var16_proc_slots_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("var16_proc_slots")

    def test_digit_symbol_names_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("digit_symbol_names")

    def test_digit_external_module_names_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("digit_external_module_names")

    def test_large_object_proc_local_inits_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("large_object_proc_local_inits")

    def test_export16_local_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("export16_local_calls")

    def test_external10_child_queue_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("external10_child_queue")

    def test_loop9_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("loop9_do_until")

    def test_loop9_while_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("loop9_while")

    def test_string36_high_index_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("string36_high_index")

    def test_int36_high_index_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("int36_high_index")

    def test_body152_local_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("body152_local_calls")

    def test_payload265_local_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("payload265_local_calls")

    def test_payload269_local_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("payload269_local_calls")

    def test_code268_dead_local_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("code268_dead_local_calls")

    def test_proc259_dead_printi_var_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("proc259_dead_printi_var")

    def test_bool_not_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("bool_not_external")

    def test_comparison_ops_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_ops")

    def test_many_string_indices_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_indices")

    def test_many_string_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_if_else")

    def test_many_string_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_do_until")

    def test_many_string_do_until_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_do_until_if_else")

    def test_many_int_indices_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_int_indices")

    def test_many_int_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_int_if_else")

    def test_many_int_do_until_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_int_do_until_if_else")

    def test_comparison_ops_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_ops_if_else")

    def test_comparison_ops_loops_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_ops_loops")

    def test_comparison_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_else")

    def test_comparison_ops_branch_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_ops_branch_calls")

    def test_many_string_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_branch_external")

    def test_many_string_branch_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_branch_transitive")

    def test_many_string_nested_loops_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_nested_loops_external")

    def test_many_string_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_branch_shared_transitive")

    def test_many_string17_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string17_branch_shared_transitive")

    def test_dense_return_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dense_return_branch_shared_transitive")

    def test_many_string_do_until_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_do_until_shared_transitive")

    def test_many_string_nested_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_nested_branch_shared_transitive")

    def test_many_int_nested_loops_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_int_nested_loops_if_else")

    def test_many_string_nested_loops_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("many_string_nested_loops_if_else")

    def test_branch_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("branch_calls")

    def test_comparison_branch_calls_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("comparison_branch_calls")

    def test_nested_branch_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_branch_calls")

    def test_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("branch_external")

    def test_nested_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_branch_external")

    def test_transitive_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("transitive_external")

    def test_transitive_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("transitive_branch_external")

    def test_sibling_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("sibling_externals")

    def test_child_sibling_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("child_sibling_externals")

    def test_branch_transitive_local_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("branch_transitive_local")

    def test_repeated_root_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("repeated_root_externals")

    def test_shared_transitive_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("shared_transitive_external")

    def test_branch_sibling_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("branch_sibling_externals")

    def test_branch_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("branch_shared_transitive")

    def test_procedure_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("procedures")

    def test_if_block_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_blocks")

    def test_else_block_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("else_blocks")

    def test_nested_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_else")

    def test_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until")

    def test_do_until_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_calls")

    def test_do_until_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_if_else")

    def test_do_until_branch_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_branch_calls")

    def test_do_until_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_branch_external")

    def test_nested_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_do_until")

    def test_nested_do_until_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_do_until_calls")

    def test_nested_do_until_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_do_until_if_else")

    def test_nested_do_until_branch_mixed_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_do_until_branch_mixed")

    def test_while_block_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_blocks")

    def test_while_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_calls")

    def test_while_if_else_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_if_else")

    def test_while_branch_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_branch_calls")

    def test_while_branch_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_branch_external")

    def test_nested_while_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_while")

    def test_nested_while_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_while_calls")

    def test_nested_while_branch_mixed_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_while_branch_mixed")

    def test_while_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_shared_transitive")

    def test_do_until_nested_while_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_nested_while")

    def test_while_nested_do_until_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_nested_do_until")

    def test_do_until_nested_while_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_nested_while_calls")

    def test_while_nested_do_until_call_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_nested_do_until_calls")

    def test_do_until_nested_while_branch_mixed_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_nested_while_branch_mixed")

    def test_while_nested_do_until_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_nested_do_until_shared_transitive")

    def test_nested_if_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_if")

    def test_if_early_return_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_early_return")

    def test_else_early_return_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("else_early_return")

    def test_do_until_early_return_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_early_return")

    def test_while_early_return_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_early_return")

    def test_nested_if_early_return_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_if_early_return")

    def test_if_return_local_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_return_local")

    def test_if_return_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_return_external")

    def test_if_return_external_args_multi_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("if_return_external_args_multi")

    def test_else_return_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("else_return_external")

    def test_do_until_return_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_return_external")

    def test_while_return_local_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_return_local_external")

    def test_nested_if_return_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_if_return_transitive")

    def test_do_until_return_branch_mixed_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_return_branch_mixed")

    def test_do_until_return_branch_args_mixed_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("do_until_return_branch_args_mixed")

    def test_nested_do_until_return_external_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("nested_do_until_return_external")

    def test_while_return_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_return_transitive")

    def test_while_nested_do_until_return_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_nested_do_until_return_transitive")

    def test_while_nested_do_until_return_args_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("while_nested_do_until_return_args_transitive")

    def test_dense_mixed_nested_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dense_mixed_nested_shared_transitive")

    def test_dense_return_nested_mixed_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dense_return_nested_mixed_shared_transitive")

    def test_dense_return_branch_nested_mixed_shared_transitive_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dense_return_branch_nested_mixed_shared_transitive")

    def test_dup_basic_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("dup_basic")

    def test_drop_depth4_pipeline_prefers_direct_prg_under_harness(self) -> None:
        self.run_direct_prg_scenario("drop_depth4")


if __name__ == "__main__":
    unittest.main()
