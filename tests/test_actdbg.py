from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest

import sys


class TestActdbg(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(self.root / "tools"))
        from vice_harness import screen_ram_to_text  # type: ignore

        self.screen_ram_to_text = screen_ram_to_text
        self.build_dir = self.root / "build" / "udos_tools"

    def require_toolchain(self) -> None:
        for tool in ("cc", "ca65", "ld65", "make"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

    def run_checked(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            cmd,
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        return result

    def build_tools(self) -> None:
        self.run_checked([str(self.root / "tools" / "build_tool_abi_harness.sh")])
        self.run_checked([str(self.root / "tools" / "build_actdbg_udos.sh")])

    def make_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes(
            [
                0x61,
                0x11,
                0x00,
                0x49,
                0x10,
                0xFF,
                0x49,
                0x20,
                0xFF,
                0x34,
                0x12,
                0x78,
                0x56,
                0x9A,
                0xBC,
                0xDE,
                0xF0,
            ]
        ) + b"HELLO\x00"
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, 0x09, 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n"
            "v g i 0 0 9 2 0 2 5 x\n"
            "v p i 0 0 1 11 2 0 1 11 p\n"
            "v l r 0 0 2 13 4 0 2 7 t\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            encoding="ascii",
        )
        return workspace

    def make_typed_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes(
            [
                0x49,
                0x20,
                0xFF,
                0xDC,
                0xFE,
                0xFE,
                0xFF,
                0x00,
                0x00,
                0x80,
                0x3F,
                0x7F,
            ]
        )
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, 0x03, 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n"
            "v g b 0 0 11 2 0 2 5 b\n"
            "v g c 0 1 3 2 0 2 12 c\n"
            "v p i 0 0 2 5 2 0 1 11 n\n"
            "v l r 0 0 3 7 4 0 2 7 r\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            "PROC MAIN(N)\rBYTE B\rCARD C\rREAL R\rENDPROC\r",
            encoding="ascii",
        )
        return workspace

    def make_loop_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes([0x19, 0x00, 0x00])
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, len(payload), 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            "PROC MAIN()\rLOOP\rENDPROC\r",
            encoding="ascii",
        )
        return workspace

    def make_call_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes(
            [
                0x45,
                0x06,
                0x00,
                0x49,
                0x20,
                0xFF,
                0x10,
                0x01,
                0x1B,
                0x48,
            ]
        )
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, 0x0A, 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n"
            "l 0 0 3 0 3 1\n"
            "q 0 1 6 0 5 1 SUB\n"
            "l 0 1 6 0 6 1\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            "PROC MAIN()\rSUB()\rENDPROC\r\rPROC SUB()\rX=1\rENDPROC\r",
            encoding="ascii",
        )
        return workspace

    def make_multifile_call_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes(
            [
                0x45,
                0x06,
                0x00,
                0x49,
                0x20,
                0xFF,
                0x10,
                0x01,
                0x1B,
                0x48,
            ]
        )
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, 0x0A, 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "f 0 1 src/sub.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n"
            "l 0 0 3 0 3 1\n"
            "q 0 1 6 1 1 1 SUB\n"
            "l 0 1 6 1 2 1\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            "PROC MAIN()\rSUB()\rENDPROC\r",
            encoding="ascii",
        )
        (workspace / "src" / "sub.act").write_text(
            "PROC SUB()\rX=1\rENDPROC\r",
            encoding="ascii",
        )
        return workspace

    def make_wide_workspace(self, tmpdir: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "bin").mkdir(parents=True)
        (workspace / "src").mkdir()
        payload = bytes([0x49, 0x20, 0xFF])
        (workspace / "bin" / "MAIN.AVM").write_bytes(
            b"AVM1"
            + bytes([0x02, len(payload), 0x00, 0x00, 0x00, 0x01, len(payload), 0x00])
            + payload
        )
        (workspace / "bin" / "MAIN.DBG").write_text(
            "DBG1\n"
            "m 0 MAIN\n"
            "f 0 0 src/main.act\n"
            "q 0 0 0 0 1 1 MAIN\n"
            "l 0 0 0 0 2 1\n",
            encoding="ascii",
        )
        (workspace / "src" / "main.act").write_text(
            'PROC MAIN()\rPRINT "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"\rENDPROC\r',
            encoding="ascii",
        )
        return workspace

    def run_actdbg(self, workspace: Path, cmdline: str, *, key_bytes: list[int]) -> dict:
        cmd = [
            str(self.build_dir / "tool_abi_harness"),
            "--prg",
            str(self.build_dir / "ACTDBG.PRG"),
            "--workspace",
            str(workspace),
            "--cmdline",
            cmdline,
            "--services-inc",
            str(self.build_dir / "udos_services.inc"),
            "--labels",
            str(self.build_dir / "actdbg.current.labels"),
            "--poke-byte",
            "actdbg_test_mode=1",
            "--poke-byte",
            f"actdbg_test_key_count={len(key_bytes)}",
            "--dump",
            "0x0400:1000",
            "--dump",
            "actdbg_view_mode:1",
            "--dump-cstr",
            "actdbg_source_path:128",
            "--dump-cstr",
            "actdbg_module_name:32",
            "--dump",
            "actdbg_vm_done:1",
            "--dump",
            "actdbg_current_pc_lo:1",
            "--dump",
            "actdbg_current_pc_hi:1",
            "--max-steps",
            "4000000",
        ]
        for index, value in enumerate(key_bytes):
            cmd.extend(["--poke-byte", f"actdbg_test_key{index}=0x{value:02X}"])
        result = self.run_checked(cmd)
        summary = json.loads(result.stdout)
        self.assertTrue(summary["exited"], msg=result.stdout)
        self.assertFalse(summary["hit_limit"], msg=result.stdout)
        self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
        return summary

    def test_actdbg_toggles_output_and_breaks_back_to_source(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x88, 0x03, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_view_mode"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/main.act")
        self.assertEqual(summary["dumps"]["actdbg_module_name"], "MAIN")
        self.assertIn("actdbg main", screen)
        self.assertIn("proc: main", screen)
        self.assertIn("src/main.act", screen)
        self.assertIn('> print "hello"', screen)
        self.assertIn("g: x=4660", screen)
        self.assertIn("p: p=22136", screen)
        self.assertIn("l: t=$f0debc9a", screen)
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 3] and op["actual_len"] == 40 for op in summary["ops"])
        )
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)

    def test_actdbg_accepts_explicit_avm_path(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "BIN/MAIN.AVM", key_bytes=[0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_view_mode"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/main.act")
        self.assertEqual(summary["dumps"]["actdbg_module_name"], "MAIN")
        self.assertIn("actdbg main", screen)
        self.assertIn("proc: main", screen)
        self.assertIn('> print "hello"', screen)
        self.assertIn("g: x=4660", screen)
        self.assertIn("p: p=22136", screen)
        self.assertIn("l: t=$f0debc9a", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL2.BIN" and op["status"] == 1 for op in summary["ops"])
        )

    def test_actdbg_step_updates_pc_without_finishing_program(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x86, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn('> print "hello"', screen)
        self.assertIn("g: x=4660", screen)
        self.assertIn("p: p=22136", screen)
        self.assertIn("l: t=$f0debc9a", screen)
        self.assertTrue(
            any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0, 3] and op["actual_len"] == 40 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL2.BIN" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "BIN/MAIN.AVM" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "BIN/MAIN.AVM" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 0] and op["actual_len"] == 16 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [12, 0, 0] and op["actual_len"] == 3 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "BIN/MAIN.DBG" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "BIN/MAIN.DBG" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1] and op["actual_len"] == 4 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1] and op["actual_len"] >= 128 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "src/main.act" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "src/main.act" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 2] and op["actual_len"] == 34 for op in summary["ops"])
        )

    def test_actdbg_continue_runs_program_into_output_buffer(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x87, 0x88, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [1], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [9], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_view_mode"], [1], msg=screen)
        self.assertIn("hello", screen)
        self.assertTrue(
            any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0, 3] and op["actual_len"] == 40 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 3] and op["actual_len"] == 40 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "BIN/MAIN.AVM" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "BIN/MAIN.AVM" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 0] and op["actual_len"] == 16 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [12, 0, 0] and op["actual_len"] == 3 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "BIN/MAIN.DBG" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "BIN/MAIN.DBG" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1] and op["actual_len"] == 4 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 1] and op["actual_len"] >= 128 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "src/main.act" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertFalse(any(op["kind"] == "load" and op["path"] == "src/main.act" for op in summary["ops"]))
        self.assertTrue(
            any(op["kind"] == "rrd" and op["params"][0:3] == [0, 0, 2] and op["actual_len"] == 34 for op in summary["ops"])
        )

    def test_actdbg_breakpoint_toggle_and_continue_stop_on_source_line(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_loop_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x42, 0x87, 0x51])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_view_mode"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn("*> loop", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL1.BIN" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL2.BIN" and op["status"] == 1 for op in summary["ops"])
        )
        self.assertTrue(
            any(op["kind"] == "rwr" and op["params"][0:3] == [0, 0, 3] and op["actual_len"] == 40 for op in summary["ops"])
        )

    def test_actdbg_formats_byte_card_int_and_real_by_type(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_typed_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertIn("g: b=127, c=65244", screen)
        self.assertIn("p: n=-2", screen)
        self.assertIn("l: r=1.0", screen)

    def test_actdbg_step_over_stops_after_call_returns(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x8A, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn("> endproc", screen)

    def test_actdbg_cursor_breakpoint_can_target_a_browsed_line(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x11, 0x42, 0x87, 0x51])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn("*> endproc", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL1.BIN" and op["status"] == 1 for op in summary["ops"])
        )

    def test_actdbg_cursor_right_scrolls_wide_source_lines(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_wide_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertIn("> 0123456789abcdefghijklmnopqrstuvwxyz0", screen)
        self.assertNotIn('> print "0123456789abcdefghijklmnopq', screen)

    def test_actdbg_step_into_displays_backtrace_chain(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x86, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [6], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn("proc: sub", screen)
        self.assertIn("bt: sub <- main", screen)
        self.assertIn("x=1", screen)

    def test_actdbg_step_into_loads_cross_file_source_from_dbg_records(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_multifile_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x86, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/sub.act")
        self.assertIn("src/sub.act", screen)
        self.assertIn("> x=1", screen)

    def test_actdbg_next_proc_jump_can_move_to_another_source_file(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_multifile_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x4D, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/sub.act")
        self.assertIn("src/sub.act", screen)
        self.assertIn("> x=1", screen)

    def test_actdbg_next_line_jump_follows_linked_line_order(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_multifile_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x4E, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/main.act")
        self.assertIn("> endproc", screen)

    def test_actdbg_file_cycle_moves_between_dbg_source_records(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_multifile_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x2E, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_source_path"], "src/sub.act")
        self.assertIn("src/sub.act", screen)
        self.assertIn("> x=1", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL1.BIN" and op["status"] == 1 for op in summary["ops"])
        )

    def test_actdbg_breakpoint_list_and_clear_all(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_loop_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x42, 0x4C, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertIn("0: src/main.act:2", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL1.BIN" and op["status"] == 1 for op in summary["ops"])
        )

    def test_actdbg_clear_all_breakpoints_empties_breakpoint_list(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_loop_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x42, 0x43, 0x4C, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertIn("0: none", screen)

    def test_actdbg_trace_toggle_shows_detailed_frames(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x86, 0x54, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertIn("bt: sub <- main", screen)
        self.assertIn("0: sub $0006", screen)
        self.assertIn("1: main $0003", screen)
        self.assertTrue(
            any(op["kind"] == "rsta" and op["path"] == "!ACTDBG_OVL1.BIN" and op["status"] == 1 for op in summary["ops"])
        )

    def test_actdbg_step_out_returns_to_caller(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_call_workspace(tmpdir)
            summary = self.run_actdbg(workspace, "MAIN", key_bytes=[0x86, 0x8B, 0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actdbg_vm_done"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actdbg_current_pc_hi"], [0], msg=screen)
        self.assertIn("> endproc", screen)


if __name__ == "__main__":
    unittest.main()
