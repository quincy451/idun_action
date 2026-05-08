from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest


class TestAlinkCapacity(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.base_fs = self.root.parent / "udos" / "build" / "udos-release-fs-manual-pipeline-44"

    def build_tool(self, script_name: str) -> None:
        result = subprocess.run(
            ["bash", str(self.root / "tools" / script_name)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def run_alink(self, project_root: Path) -> dict:
        result = subprocess.run(
            [
                str(self.root / "build" / "udos_tools" / "tool_abi_harness"),
                "--prg",
                str(self.root / "build" / "udos_tools" / "ALINK.PRG"),
                "--workspace",
                str(project_root),
                "--cmdline",
                "MAIN",
                "--services-inc",
                str(self.root / "build" / "udos_tools" / "udos_services.inc"),
                "--labels",
                str(self.root / "build" / "udos_tools" / "alink.current.labels"),
                "--max-steps",
                "40000000",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_production_alink_emits_multi_kilobyte_avm(self) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        self.build_tool("build_tool_abi_harness.sh")
        self.build_tool("build_alink_udos.sh")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "alink-capacity"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            obj_dir = project_root / "obj"
            obj_dir.mkdir(exist_ok=True)
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            external_count = 32
            child_repeats0 = 124
            child_repeats1 = 125
            child_body0 = ("i0" * child_repeats0) + "c1r"
            child_body1 = ("i0" * child_repeats1) + "r"
            child_size0 = (child_repeats0 * 6) + 3 + 1
            child_size1 = (child_repeats1 * 6) + 1
            child_size = child_size0 + child_size1
            def body_index(value: int) -> str:
                return str(value) if value < 10 else chr(ord("A") + value - 10)

            root_body = "".join(f"u{body_index(i)}" for i in range(external_count)) + "r"
            root_declared_size = (external_count * 3) + 1
            root_emitted_size = (external_count * 3) + 3

            root_object = (
                "AVO1\n"
                "f 0 src/main.act\n"
                "q 0 0 1 1\n"
                "l 0 0 0 2 1\n"
                "V g i 0 0 2 5\n"
                f"x main 0 {root_declared_size}\n"
                f"b {root_body}\n"
                "v x 0\n"
                "s ROOT_UNUSED\n"
                + "".join(f"u E{i}\n" for i in range(external_count))
                + f"k {root_declared_size}\n"
                "n main\n"
            )
            (obj_dir / "MAIN.OBJ").write_text(root_object, encoding="ascii")

            for i in range(external_count):
                child_object = (
                    "AVO1\n"
                    f"f 0 src/e{i}.act\n"
                    "q 0 0 1 1\n"
                    "l 0 0 0 2 1\n"
                    f"x e{i} 0 {child_size0}\n"
                    f"x e{i}b {child_size0} {child_size1}\n"
                    f"b {child_body0}\n"
                    f"b {child_body1}\n"
                    "i 0\n"
                    f"k {child_size}\n"
                    f"n e{i}\n"
                )
                (obj_dir / f"E{i}.OBJ").write_text(child_object, encoding="ascii")

            summary = self.run_alink(project_root)
            self.assertEqual(summary["exit_status"], 0, msg=json.dumps(summary, indent=2))

            reu_stage_ops = [op for op in summary["ops"] if op["kind"] == "rsta"]
            reu_read_ops = [op for op in summary["ops"] if op["kind"] == "rrd"]
            open_ops = [op for op in summary["ops"] if op["kind"] == "wopn"]
            write_ops = [op for op in summary["ops"] if op["kind"] == "wrte"]
            close_ops = [op for op in summary["ops"] if op["kind"] == "wcls"]
            avm_open_ops = [op for op in open_ops if op["full_path"].endswith("/MAIN.AVM")]
            dbg_open_ops = [op for op in open_ops if op["full_path"].endswith("/MAIN.DBG")]
            avm_write_ops = [op for op in write_ops if op["full_path"].endswith("/MAIN.AVM")]
            dbg_write_ops = [op for op in write_ops if op["full_path"].endswith("/MAIN.DBG")]
            avm_close_ops = [op for op in close_ops if op["full_path"].endswith("/MAIN.AVM")]
            dbg_close_ops = [op for op in close_ops if op["full_path"].endswith("/MAIN.DBG")]
            self.assertTrue(reu_stage_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(reu_read_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(avm_open_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(dbg_open_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(avm_write_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(dbg_write_ops, msg=json.dumps(summary, indent=2))
            self.assertTrue(close_ops, msg=json.dumps(summary, indent=2))
            main_stage = next(op for op in reu_stage_ops if op["path"] == "OBJ/MAIN.OBJ")
            self.assertEqual(main_stage["actual_len"], len(root_object.encode("ascii")))
            self.assertEqual(main_stage["status"], 1)
            self.assertTrue(
                any(
                    op["params"][2] == 1
                    and ((op["params"][1] << 8) | op["params"][0]) >= 0x0200
                    for op in reu_read_ops
                ),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0xF8, 0] and op["actual_len"] == 25 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0xF8, 0] and op["actual_len"] == 25 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0xFA, 0] and op["actual_len"] == 25 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0, 2] and op["actual_len"] == 24 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 2] and op["actual_len"] == 24 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rwr" and op["params"][0:3] == [0x60, 0x03, 2] and op["actual_len"] == 24 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(op["kind"] == "rrd" and op["params"][0:3] == [0x60, 0x03, 2] and op["actual_len"] == 24 for op in summary["ops"]),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(
                    op["kind"] == "rwr"
                    and op["params"][2] == 2
                    and op["params"][1] == 0x05
                    and 0x00 <= op["params"][0] < 0x00 + (8 * 11)
                    and op["actual_len"] == 8
                    for op in summary["ops"]
                ),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(
                    op["kind"] == "rrd"
                    and op["params"][2] == 2
                    and op["params"][1] == 0x05
                    and 0x00 <= op["params"][0] < 0x00 + (8 * 11)
                    and op["actual_len"] == 8
                    for op in summary["ops"]
                ),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(
                any(
                    op["kind"] == "rwr"
                    and op["params"][2] == 2
                    and op["params"][1] == 0x05
                    and 0x60 <= op["params"][0] < 0x60 + (4 * 16)
                    and op["actual_len"] == 2
                    for op in summary["ops"]
                ),
                msg=json.dumps(summary, indent=2),
            )
            self.assertTrue(avm_open_ops[-1]["full_path"].endswith("/MAIN.AVM"))
            self.assertTrue(dbg_open_ops[-1]["full_path"].endswith("/MAIN.DBG"))

            output_path = project_root / "bin" / "MAIN.AVM"
            data = output_path.read_bytes()
            dbg_path = project_root / "bin" / "MAIN.DBG"
            dbg_text = dbg_path.read_text(encoding="ascii")
            expected_code_limit = root_emitted_size + (external_count * child_size)
            expected_payload_len = expected_code_limit + 2
            print_helper_blob = (self.root / "build" / "udos_tools" / "RT_PRINT_STD_HELPER.BIN").read_bytes()
            expected_trailer = (
                b"AVH1"
                + bytes([1, 2, len(print_helper_blob) & 0xFF, (len(print_helper_blob) >> 8) & 0xFF])
                + print_helper_blob
            )
            expected_file_len = 12 + expected_payload_len + len(expected_trailer)
            trailer_offset = 12 + expected_payload_len

            self.assertEqual(sum(op["actual_len"] for op in avm_write_ops), expected_file_len)
            self.assertEqual(len(data), expected_file_len)
            self.assertGreater(len(data), 45000)
            self.assertLessEqual(int.from_bytes(data[5:7], "little"), 0xC000)
            self.assertEqual(data[:4], b"AVM1")
            self.assertEqual(data[4], 2)
            self.assertEqual(int.from_bytes(data[5:7], "little"), expected_payload_len)
            self.assertEqual(int.from_bytes(data[7:9], "little"), 0)
            self.assertEqual(data[9] & 0x01, 1)
            self.assertEqual(int.from_bytes(data[10:12], "little"), expected_code_limit)
            self.assertEqual(data[trailer_offset:], expected_trailer)
            self.assertTrue(dbg_text.startswith("DBG1\n"), dbg_text)
            self.assertIn("m 0 MAIN\n", dbg_text)
            self.assertIn("f 0 0 src/main.act\n", dbg_text)
            self.assertIn("q 0 0 0 0 1 1 main\n", dbg_text)
            self.assertIn("l 0 0 0 0 2 1\n", dbg_text)
            self.assertIn(f"v g i 0 0 {expected_code_limit} 2 0 2 5 x\n", dbg_text)
            self.assertIn("m 1 e0\n", dbg_text)
            self.assertIn("f 1 0 src/e0.act\n", dbg_text)
            self.assertIn(f"q 1 0 {root_emitted_size} 0 1 1 e0\n", dbg_text)
            self.assertIn(f"l 1 0 {root_emitted_size} 0 2 1\n", dbg_text)

    def test_production_alink_emits_param_and_local_debug_records(self) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        if not self.base_fs.is_dir():
            self.skipTest(f"missing base fs tree: {self.base_fs}")

        self.build_tool("build_tool_abi_harness.sh")
        self.build_tool("build_alink_udos.sh")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_fs = Path(tmpdir) / "alink-debug-vars"
            shutil.copytree(self.base_fs, out_fs)
            project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
            obj_dir = project_root / "obj"
            obj_dir.mkdir(exist_ok=True)
            (project_root / "ACTION.PROJ").write_text("ACTION PROJECT\rMAIN.ACT\r", encoding="ascii")

            root_object = (
                "AVO1\n"
                "f 0 src/main.act\n"
                "q 0 0 1 1\n"
                "l 0 0 0 2 1\n"
                "V g i 0 0 2 5\n"
                "V p i 0 1 0 3 11\n"
                "V l i 0 2 0 4 5\n"
                "x main 0 1\n"
                "b r\n"
                "v x 0\n"
                "v p 0\n"
                "v t 0\n"
                "k 1\n"
                "n main\n"
            )
            (obj_dir / "MAIN.OBJ").write_text(root_object, encoding="ascii")

            summary = self.run_alink(project_root)
            self.assertEqual(summary["exit_status"], 0, msg=json.dumps(summary, indent=2))

            dbg_path = project_root / "bin" / "MAIN.DBG"
            dbg_text = dbg_path.read_text(encoding="ascii")
            self.assertTrue(dbg_text.startswith("DBG1\n"), dbg_text)
            self.assertIn("v g i 0 0 3 2 0 2 5 x\n", dbg_text)
            self.assertIn("v p i 0 0 1 5 2 0 3 11 p\n", dbg_text)
            self.assertIn("v l i 0 0 2 7 2 0 4 5 t\n", dbg_text)


if __name__ == "__main__":
    unittest.main()
