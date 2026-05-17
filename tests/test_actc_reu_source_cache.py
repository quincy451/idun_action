from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import unittest


def count_body_ops(body: str) -> int:
    match = re.search(r"^b ([^\n]*)$", body, re.MULTILINE)
    if match is None:
        return 0
    stream = match.group(1)
    count = 0
    index = 0
    while index < len(stream):
        count += 1
        index += 1
        if index < len(stream) and stream[index] in "0123456789ABCDEF":
            index += 1
    return count


class TestActcReuSourceCache(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.build_dir = self.root / "build" / "udos_tools"

    def require_toolchain(self) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

    def run_checked(self, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args,
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        return result

    def assert_single_proc_object(self, text: str, body: str, min_line: int = 2) -> None:
        match = re.match(r"^OBJ1\nf 0 src/main\.act\nq 0 0 (\d+) (\d+)\n((?:l 0 \d+ 0 \d+ \d+\n)*)", text)
        self.assertIsNotNone(match, msg=text)
        assert match is not None
        self.assertGreaterEqual(int(match.group(1)), min_line, msg=text)
        self.assertEqual(int(match.group(2)), 6, msg=text)
        debug_lines = [line for line in match.group(3).splitlines() if line]
        self.assertEqual(len(debug_lines), count_body_ops(body), msg=text)
        for index, line in enumerate(debug_lines):
            self.assertRegex(line, rf"^l 0 {index} 0 \d+ \d+$", msg=text)
        remainder = text[match.end() :]
        var_debug_prefix = re.match(
            r"^((?:V g [ibcr] \d+ 0 \d+ \d+\n|V [pl] [ibcr] \d+ \d+ 0 \d+ \d+\n)*)",
            remainder,
        )
        assert var_debug_prefix is not None
        self.assertEqual(remainder[var_debug_prefix.end() :], body, msg=text)

    def test_reu_source_cache_stages_large_source_and_pages_compile_window(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-source"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            source = 'MODULE MAIN\rPROC MAIN()\rPrintE("OK")\rRETURN\r' + ("\r" * 21000)
            source_path = source_dir / "main.act"
            source_path.write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "10000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\nb e0r\ns OK\nk 2\nn main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        reu_read = next(op for op in summary["ops"] if op["kind"] == "rrd")
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertEqual(reu_stage["status"], 1)
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertEqual(reu_stage["params"][2:5], [0, 0, 1])
        self.assertEqual(reu_read["status"], 1)
        self.assertGreater(reu_read["actual_len"], 20480)
        self.assertEqual(reu_read["actual_len"], reu_read["limit"])

    def test_reu_source_cache_compiles_proc_name_crossing_window_boundary(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-paged"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            module_header = "MODULE MAIN\r"
            proc_prefix = "PROC "
            name_offset = 20478
            filler_len = name_offset - len(module_header) - len(proc_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = module_header + ("\r" * filler_len) + proc_prefix + 'MAIN()\rPrintE("OK")\rRETURN\r'
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "12000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\nb e0r\ns OK\nk 2\nn main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        tail_read = next(
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        )
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertGreater(tail_read["actual_len"], 0)

    def test_reu_source_cache_compiles_string_literal_crossing_window_boundary(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-string-lookahead"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\rPROC MAIN()\r"
            print_prefix = 'PrintE("'
            literal_offset = 20479
            filler_len = literal_offset - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = prefix + ("\r" * filler_len) + print_prefix + 'OK")\rRETURN\r'
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "12000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\nb e0r\ns OK\nk 2\nn main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        tail_read = next(
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        )
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertGreater(tail_read["actual_len"], 0)

    def test_reu_source_cache_commits_long_inline_spaces_across_window_boundary(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-space-commit"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\rPROC MAIN()\r"
            print_prefix = "PrintIE("
            filler_len = 20470 - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = prefix + ("\r" * filler_len) + print_prefix + (" " * 320) + "7)\rRETURN\r"
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "12000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\nb i0r\ni 7\nk 6\nn main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertTrue(later_reads, msg=result.stdout)

    def test_reu_source_cache_commits_long_expression_across_window_boundary(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-expression-commit"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            long_name = "ABCDEFGHIJKLMNOPQRSTUVW"
            expression = "+".join([long_name] * 12)
            prefix = f"MODULE MAIN\rINT {long_name}=[1]\rPROC MAIN()\r"
            print_prefix = "PrintIE("
            expression_offset = 20470
            filler_len = expression_offset - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = prefix + ("\r" * filler_len) + print_prefix + expression + ")\rRETURN\r"
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "16000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 51\n"
                "b L0L0aL0aL0aL0aL0aL0aL0aL0aL0aL0aL0azr\n"
                "v abcdefghijklmnopqrstuvw 1\n"
                "k 6\n"
                "n main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertTrue(later_reads, msg=result.stdout)

    def test_reu_source_cache_restores_window_after_failed_keyword_probe(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-keyword-restore"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            long_name = "ABCDEFGHIJKLMNOPQRSTUVW"
            prefix = f"MODULE MAIN\rINT {long_name}=[1]\rPROC MAIN()\r"
            print_prefix = "PrintIE("
            filler_len = 20470 - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = prefix + ("\r" * filler_len) + print_prefix + (" " * 250) + long_name + ")\rRETURN\r"
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "18000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\n"
                "b L0zr\n"
                "v abcdefghijklmnopqrstuvw 1\n"
                "k 6\n"
                "n main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        rewound_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1]
        ]
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertTrue(later_reads, msg=result.stdout)
        self.assertTrue(rewound_reads, msg=result.stdout)

    def test_reu_source_cache_assignment_operator_can_sit_at_y_wrap(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-assignment-wrap"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\rINT A=[1]\rPROC MAIN()\r"
            filler_len = 20470 - len(prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = prefix + ("\r" * filler_len) + "A" + (" " * 254) + "=2\rRETURN\r"
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "18000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\n"
                "b p0S0r\n"
                "i 2\n"
                "v a 1\n"
                "k 0\n"
                "n main\n",
                min_line=3,
            )

        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        self.assertTrue(later_reads, msg=result.stdout)

    def test_reu_source_cache_proc_param_open_paren_can_sit_at_y_wrap(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-param-wrap"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\r"
            proc_prefix = "PROC "
            proc_name_offset = 20470
            filler_len = proc_name_offset - len(prefix) - len(proc_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = (
                prefix
                + ("\r" * filler_len)
                + proc_prefix
                + "MAIN"
                + (" " * 251)
                + "(N)\rRETURN N\r"
            )
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "18000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\n"
                "b S0L0r\n"
                "v n 0\n"
                "k 0\n"
                "n main\n",
            )

        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        self.assertTrue(later_reads, msg=result.stdout)

    def test_reu_source_cache_runtime_group_restore_crosses_y_wrap(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-runtime-group-restore"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\rPROC MAIN()\r"
            print_prefix = "PrintIE("
            filler_len = 20470 - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = (
                prefix
                + ("\r" * filler_len)
                + print_prefix
                + "("
                + "1"
                + (" " * 254)
                + ")=1)\rRETURN\r"
            )
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "25000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\n"
                "b i0r\n"
                "i 1\n"
                "k 6\n"
                "n main\n",
            )

        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        rewound_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1]
        ]
        self.assertTrue(later_reads, msg=result.stdout)
        self.assertTrue(rewound_reads, msg=result.stdout)

    def test_reu_source_cache_const_group_restore_crosses_y_wrap(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-const-group-restore"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\r"
            decl_prefix = "INT X=["
            filler_len = 20470 - len(prefix) - len(decl_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = (
                prefix
                + ("\r" * filler_len)
                + decl_prefix
                + "("
                + "1"
                + (" " * 254)
                + ")=1]\rPROC MAIN()\rRETURN\r"
            )
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "25000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 1\n"
                "b r\n"
                "v x 1\n"
                "k 0\n"
                "n main\n",
                min_line=20000,
            )

        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        rewound_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1]
        ]
        self.assertTrue(later_reads, msg=result.stdout)
        self.assertTrue(rewound_reads, msg=result.stdout)

    def test_reu_source_cache_routes_long_boolean_scan_across_window_boundary(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actc_reu_cache_harness_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "actc-reu-boolean-prescan"
            project_root = workspace / "IMAGES" / "ACTION.DNP" / "PROJ3"
            source_dir = project_root / "src"
            object_dir = project_root / "obj"
            source_dir.mkdir(parents=True)
            object_dir.mkdir()
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            prefix = "MODULE MAIN\rPROC MAIN()\r"
            print_prefix = "PrintIE("
            filler_len = 20470 - len(prefix) - len(print_prefix)
            self.assertGreaterEqual(filler_len, 0)
            source = (
                prefix
                + ("\r" * filler_len)
                + print_prefix
                + "1"
                + (" " * 320)
                + "AND 1)\rRETURN\r"
            )
            (source_dir / "main.act").write_text(source, encoding="ascii")

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "ACTC_REU.PRG"),
                    "--workspace",
                    str(project_root),
                    "--cmdline",
                    "MAIN",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "actc.reu.current.labels"),
                    "--max-steps",
                    "16000000",
                ]
            )

            summary = json.loads(result.stdout)
            self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
            self.assertFalse(summary["hit_limit"], msg=result.stdout)
            self.assert_single_proc_object(
                (object_dir / "MAIN.OBJ").read_text(encoding="ascii"),
                "x main 0 7\n"
                "b i0r\n"
                "i 1\n"
                "k 6\n"
                "n main\n",
            )

        reu_stage = next(op for op in summary["ops"] if op["kind"] == "rsta")
        later_reads = [
            op
            for op in summary["ops"]
            if op["kind"] == "rrd" and op["params"][0:3] == [0, 80, 1]
        ]
        self.assertEqual(reu_stage["path"], "SRC/MAIN.ACT")
        self.assertGreater(reu_stage["actual_len"], 20480)
        self.assertTrue(later_reads, msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
