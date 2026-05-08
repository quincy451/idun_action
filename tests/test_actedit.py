from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest

import sys


class TestActedit(unittest.TestCase):
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
        self.run_checked([str(self.root / "tools" / "build_actedit_udos.sh")])

    def make_workspace(self, tmpdir: str, source_text: str) -> Path:
        workspace = Path(tmpdir) / "ws"
        (workspace / "src").mkdir(parents=True)
        (workspace / "bin").mkdir()
        (workspace / "src" / "main.act").write_text(source_text, encoding="ascii")
        return workspace

    def run_actedit(self, workspace: Path, cmdline: str, *, key_bytes: list[int]) -> dict:
        cmd = [
            str(self.build_dir / "tool_abi_harness"),
            "--prg",
            str(self.build_dir / "ACTEDIT.PRG"),
            "--workspace",
            str(workspace),
            "--cmdline",
            cmdline,
            "--services-inc",
            str(self.build_dir / "udos_services.inc"),
            "--labels",
            str(self.build_dir / "actedit.current.labels"),
            "--poke-byte",
            "actedit_test_mode=1",
            "--poke-byte",
            f"actedit_test_key_count={len(key_bytes)}",
            "--dump",
            "0x0400:1000",
            "--dump-cstr",
            "actedit_source_path:128",
            "--dump",
            "actedit_current_line_lo:1",
            "--dump",
            "actedit_current_line_hi:1",
            "--dump",
            "actedit_left_col:1",
            "--dump",
            "actedit_cursor_col:1",
            "--dump",
            "actedit_dirty:1",
            "--max-steps",
            "1500000",
        ]
        for index, value in enumerate(key_bytes):
            cmd.extend(["--poke-byte", f"actedit_test_key{index}=0x{value:02X}"])
        result = self.run_checked(cmd)
        summary = json.loads(result.stdout)
        self.assertTrue(summary["exited"], msg=result.stdout)
        self.assertFalse(summary["hit_limit"], msg=result.stdout)
        self.assertEqual(summary["exit_status"], 0, msg=result.stdout)
        return summary

    def test_actedit_builds(self) -> None:
        self.require_toolchain()
        result = self.run_checked([str(self.root / "tools" / "build_actedit_udos.sh")])
        built = Path(result.stdout.strip().splitlines()[-1])
        labels = self.build_dir / "actedit.current.labels"
        self.assertTrue(built.is_file())
        self.assertGreater(built.stat().st_size, 2)
        self.assertTrue(labels.is_file())
        self.assertIn("actedit_source_path", labels.read_text(encoding="ascii"))

    def test_actedit_loads_module_source_and_quits(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(workspace, "MAIN", key_bytes=[0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_source_path"], "src/main.act")
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [1])
        self.assertEqual(summary["dumps"]["actedit_current_line_hi"], [0])
        self.assertEqual(summary["dumps"]["actedit_left_col"], [0])
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0])
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0])
        self.assertIn("actedit src/main.act", screen)
        self.assertIn("> proc main()", screen)
        self.assertIn('  print "hello"', screen)

    def test_actedit_loads_direct_source_path_and_quits(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(workspace, "src/main.act", key_bytes=[0xFF])

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_source_path"], "src/main.act")
        self.assertIn("actedit src/main.act", screen)
        self.assertIn("> proc main()", screen)

    def test_actedit_scrolls_vertically_and_horizontally(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2])
        self.assertEqual(summary["dumps"]["actedit_current_line_hi"], [0])
        self.assertEqual(summary["dumps"]["actedit_left_col"], [0])
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [2])
        self.assertIn('> print "0123456789abcdefghijklmnopqrst', screen)

    def test_actedit_home_moves_to_line_start_then_file_top(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT ABC\rPRINT DEF\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x13, 0x13, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [1], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0], msg=screen)
        self.assertIn("> proc main()", screen)

    def test_actedit_page_and_file_navigation_keys(self) -> None:
        self.require_toolchain()
        self.build_tools()

        body = "".join(f"L{index:02d}\r" for index in range(1, 26))
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\r" + body + "ENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x8C, 0x93, 0x94, 0x94, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [27], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [7], msg=screen)
        self.assertIn("> endproc", screen)

    def test_actedit_insert_persists_across_line_navigation(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x11, 0x91, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2])
        self.assertEqual(summary["dumps"]["actedit_dirty"], [1])
        self.assertIn('> print "xhello"', screen)

    def test_actedit_undo_restores_last_insert(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x55, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "hello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r')

    def test_actedit_multi_step_undo_walks_back_multiple_edits(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x59, 0x55, 0x55, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "hello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r')

    def test_actedit_undo_journal_keeps_more_than_four_steps(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[
                    0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D,
                    0x41, 0x42, 0x43, 0x44, 0x45,
                    0x55, 0x55, 0x55, 0x55, 0x55,
                    0x85, 0xFF,
                ],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "hello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r')

    def test_actedit_redo_restores_last_undone_insert(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x55, 0x59, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "xhello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "XHELLO"\rENDPROC\r')

    def test_actedit_new_edit_clears_redo_history(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x55, 0x5A, 0x59, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "zhello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "ZHELLO"\rENDPROC\r')

    def test_actedit_save_writes_modified_source(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x58, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print "xhello"', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT "XHELLO"\rENDPROC\r')
        self.assertTrue(any(op["kind"] == "wopn" and op["path"] == "src/main.act" for op in summary["ops"]))
        self.assertTrue(any(op["kind"] == "wrte" and op["status"] == 1 for op in summary["ops"]))
        self.assertTrue(any(op["kind"] == "wcls" and op["status"] == 1 for op in summary["ops"]))

    def test_actedit_mark_copy_and_paste_duplicate_current_line_selection(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x86, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x87, 0x88, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_dirty"], [1], msg=screen)
        self.assertIn('> print "hellohello"', screen)

    def test_actedit_cut_selection_and_save_updates_source(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                'PROC MAIN()\rPRINT "HELLO"\rENDPROC\r',
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x86, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x8B, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn('> print ""', screen)
        self.assertEqual(saved, 'PROC MAIN()\rPRINT ""\rENDPROC\r')

    def test_actedit_find_next_token_moves_to_next_match(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT A\rPRINT B\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x89, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0], msg=screen)
        self.assertIn("> print b", screen)

    def test_actedit_find_prev_token_moves_to_previous_match(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT A\rPRINT B\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x11, 0x8A, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0], msg=screen)
        self.assertIn("> print a", screen)

    def test_actedit_goto_line_moves_to_requested_line(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT A\rPRINT B\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x47, 0x33, 0x0D, 0xFF],
            )

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0], msg=screen)
        self.assertIn("> print b", screen)

    def test_actedit_replace_next_and_save_updates_source(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT A\rPRINT A\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x52, 0x5A, 0x0D, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertIn("> print z", screen)
        self.assertEqual(saved, "PROC MAIN()\rPRINT Z\rPRINT A\rENDPROC\r")

    def test_actedit_split_line_and_save_updates_source(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT A\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x1D, 0x0D, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [3], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn("> a", screen)
        self.assertEqual(saved, "PROC MAIN()\rPRINT \rA\rENDPROC\r")

    def test_actedit_join_line_with_delete_at_column_zero(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rPRINT \rA\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x11, 0x14, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [7], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn("> print a", screen)
        self.assertEqual(saved, "PROC MAIN()\rPRINT A\rENDPROC\r")

    def test_actedit_multiline_cut_merges_endpoints(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rAX\rBY\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x86, 0x11, 0x8B, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_cursor_col"], [1], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn("> ay", screen)
        self.assertEqual(saved, "PROC MAIN()\rAY\rENDPROC\r")

    def test_actedit_undo_restores_multiline_cut(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rAX\rBY\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x1D, 0x86, 0x11, 0x8B, 0x55, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [3], msg=screen)
        self.assertIn("> by", screen)
        self.assertEqual(saved, "PROC MAIN()\rAX\rBY\rENDPROC\r")

    def test_actedit_multiline_copy_and_paste_preserves_line_breaks(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rA\rB\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x86, 0x11, 0x1D, 0x87, 0x11, 0x9D, 0x0D, 0x91, 0x88, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertIn("> b", screen)
        self.assertEqual(saved, "PROC MAIN()\rA\rB\rA\rB\rENDPROC\r")

    def test_actedit_multiline_delete_preserves_clipboard(self) -> None:
        self.require_toolchain()
        self.build_tools()

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = self.make_workspace(
                tmpdir,
                "PROC MAIN()\rZ\rAX\rBY\rENDPROC\r",
            )
            summary = self.run_actedit(
                workspace,
                "MAIN",
                key_bytes=[0x11, 0x86, 0x1D, 0x87, 0x11, 0x86, 0x11, 0x14, 0x91, 0x88, 0x85, 0xFF],
            )
            saved = (workspace / "src" / "main.act").read_bytes().decode("ascii")

        screen = self.screen_ram_to_text(bytes(summary["dumps"]["0x0400"]))
        self.assertEqual(summary["dumps"]["actedit_dirty"], [0], msg=screen)
        self.assertEqual(summary["dumps"]["actedit_current_line_lo"], [2], msg=screen)
        self.assertIn("> zz", screen)
        self.assertEqual(saved, "PROC MAIN()\rZZ\rAY\rENDPROC\r")


if __name__ == "__main__":
    unittest.main()
