from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import unittest


class TestAvmrunCapacity(unittest.TestCase):
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

    def write_exit_avm(self, path: Path, size: int) -> None:
        payload_len = size - 12
        self.assertGreaterEqual(payload_len, 3)
        self.assertLessEqual(payload_len, 0xFFFF)
        payload = bytearray(payload_len)
        entry_offset = payload_len - 3
        payload[entry_offset:entry_offset + 3] = bytes([0x49, 0x20, 0xFF])
        header = (
            b"AVM1"
            + bytes(
                [
                    2,
                    payload_len & 0xFF,
                    payload_len >> 8,
                    entry_offset & 0xFF,
                    entry_offset >> 8,
                    1,
                    payload_len & 0xFF,
                    payload_len >> 8,
                ]
            )
        )
        path.write_bytes(header + payload)

    def write_text_exit_avt(self, path: Path) -> None:
        path.write_text("entry 0\nhex 4920ff\n", encoding="ascii")

    def assert_avm_load_window_does_not_overlap_tool(self) -> None:
        map_text = (self.build_dir / "avmrun.current.map").read_text(encoding="ascii")
        match = re.search(r"^BSS\s+([0-9A-Fa-f]{6})\s+([0-9A-Fa-f]{6})\s+", map_text, re.MULTILINE)
        if match is not None:
            tool_end = int(match.group(2), 16)
        else:
            code_match = re.search(r"^CODE\s+([0-9A-Fa-f]{6})\s+([0-9A-Fa-f]{6})\s+", map_text, re.MULTILINE)
            self.assertIsNotNone(code_match, msg=map_text)
            tool_end = int(code_match.group(2), 16)
        self.assertLess(tool_end, 0x39C0, msg=map_text)

    def test_binary_avm_can_execute_from_runtime_window_up_to_40640_bytes(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        # Capacity tests exercise the production runner image itself, not just
        # compat labels or helper assets.
        self.run_checked([str(self.root / "tools" / "build_avmrun_udos.sh")])
        self.assert_avm_load_window_does_not_overlap_tool()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            avm_path = workspace / "BIG.AVM"
            self.write_exit_avm(avm_path, 0x9EC0)

            result = self.run_checked(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "AVMRUNC.PRG"),
                    "--workspace",
                    str(workspace),
                    "--cmdline",
                    "BIG.AVM",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "avmrunc.current.labels"),
                    "--poke-byte",
                    "0x0001=0x37",
                    "--op-dump",
                    "c64_memcfg:1",
                    "--dump",
                    "0x0001:1",
                    "--max-steps",
                    "4000000",
                ]
            )

        summary = json.loads(result.stdout)
        self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
        self.assertFalse(summary["hit_limit"], msg=result.stdout)
        self.assertEqual(summary["console"], "")
        self.assertGreaterEqual(len(summary["ops"]), 1)
        load_op = summary["ops"][0]
        self.assertEqual(load_op["kind"], "load")
        self.assertEqual(load_op["ptr"], 0x4B40)
        self.assertEqual(load_op["limit"], 0xC000)
        self.assertEqual(load_op["actual_len"], 0x9EC0)
        self.assertEqual(load_op["status"], 1)
        self.assertEqual(load_op["trace"]["c64_memcfg"], [0x36])
        self.assertTrue(any(op.get("kind") == "rsta" and op.get("path") == "!AVMRUN_OVL3.BIN" for op in summary["ops"]), msg=result.stdout)
        self.assertTrue(any(op.get("kind") == "rrd" for op in summary["ops"]), msg=result.stdout)
        self.assertEqual(summary["dumps"]["0x0001"], [0x37])

    def test_production_avm_can_load_binary_up_to_43184_bytes_below_printreal_helper_window(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_avmrun_udos.sh")])
        self.assert_avm_load_window_does_not_overlap_tool()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            avm_path = workspace / "BIG.AVM"
            self.write_exit_avm(avm_path, 0xA8B0)

            result = subprocess.run(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "AVMRUN.PRG"),
                    "--workspace",
                    str(workspace),
                    "--cmdline",
                    "BIG.AVM",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "avmrun.current.labels"),
                    "--poke-byte",
                    "0x0001=0x37",
                    "--op-dump",
                    "c64_memcfg:1",
                    "--dump",
                    "0x0001:1",
                    "--max-steps",
                    "4000000",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )

        summary = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertEqual(summary["exit_status"], 1, msg=result.stdout)
        self.assertGreaterEqual(len(summary["ops"]), 1)
        load_op = summary["ops"][0]
        self.assertEqual(load_op["kind"], "load")
        self.assertEqual(load_op["ptr"], 0x4750)
        self.assertEqual(load_op["limit"], 0xC000)
        self.assertEqual(load_op["actual_len"], 0xA8B0)
        self.assertEqual(load_op["status"], 1)
        self.assertEqual(load_op["trace"]["c64_memcfg"], [0x36])
        self.assertEqual(summary.get("console", ""), "NEEDS AVMRUN COMPAT\n")
        self.assertEqual(summary["dumps"]["0x0001"], [0x37])
        self.assertEqual(0xF000 - load_op["ptr"], 0xA8B0)

    def test_production_avmrun_rejects_text_avm_input(self) -> None:
        self.require_toolchain()
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_avmrun_udos.sh")])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            avt_path = workspace / "OLD.AVT"
            self.write_text_exit_avt(avt_path)

            result = subprocess.run(
                [
                    str(self.build_dir / "tool_abi_harness"),
                    "--prg",
                    str(self.build_dir / "AVMRUN.PRG"),
                    "--workspace",
                    str(workspace),
                    "--cmdline",
                    "OLD.AVT",
                    "--services-inc",
                    str(self.build_dir / "udos_services.inc"),
                    "--labels",
                    str(self.build_dir / "avmrun.current.labels"),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["exit_status"], 1, msg=result.stdout)
        self.assertEqual(summary.get("console", ""), "BAD AVM\n")


if __name__ == "__main__":
    unittest.main()
