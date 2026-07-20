from __future__ import annotations

from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import sqlite3
import struct
import subprocess
import tempfile
import termios
import time
import unittest


class TestActionHelp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["bash", str(cls.root / "tools" / "build_linux_tools.sh")],
            cwd=cls.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        cls.tool_dir = Path(result.stdout.strip().splitlines()[-1])
        cls.help_db = cls.tool_dir / "action-help.sqlite3"

    def run_tool(
        self,
        workspace: Path,
        tool: str,
        *args: str,
        expected_status: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.tool_dir / tool), *args],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            expected_status,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def make_project(self, root: Path) -> Path:
        self.run_tool(root, "actnew", "demo")
        return root / "DEMO"

    def test_catalog_is_external_validated_sqlite(self) -> None:
        checked = subprocess.run(
            [
                "python3",
                str(self.root / "tools" / "build_action_help.py"),
                "--check-only",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(checked.returncode, 0, msg=checked.stdout + checked.stderr)
        self.assertIn("validated 260 help topics", checked.stdout)

        payload = json.loads(
            (self.root / "resources" / "action_help.json").read_text(encoding="utf-8")
        )
        authored_count = len(payload["topics"]) + sum(
            len(library["topics"]) for library in payload["libraries"]
        )
        with closing(
            sqlite3.connect(f"file:{self.help_db}?mode=ro", uri=True)
        ) as database:
            database_count = database.execute("SELECT count(*) FROM topics").fetchone()[0]
            integrity = database.execute("PRAGMA integrity_check").fetchone()[0]
            kinds = dict(database.execute("SELECT kind,count(*) FROM topics GROUP BY kind"))
            missing_examples = database.execute(
                "SELECT count(*) FROM topics WHERE trim(example)=''"
            ).fetchone()[0]
        self.assertEqual(database_count, authored_count)
        self.assertEqual(integrity, "ok")
        self.assertGreater(kinds["builtin"], 70)
        self.assertGreater(kinds["keyword"], 20)
        self.assertGreater(kinds["constant"], 10)
        self.assertEqual(missing_examples, 0)

        with tempfile.TemporaryDirectory() as tmp:
            incomplete = json.loads(json.dumps(payload))
            print_r = next(
                topic
                for library in incomplete["libraries"]
                for topic in library["topics"]
                if topic["token"].upper() == "PRINTR"
            )
            print_r.pop("example")
            incomplete_path = Path(tmp) / "incomplete-help.json"
            incomplete_path.write_text(
                json.dumps(incomplete), encoding="utf-8"
            )
            rejected = subprocess.run(
                [
                    "python3",
                    str(self.root / "tools" / "build_action_help.py"),
                    "--source",
                    str(incomplete_path),
                    "--check-only",
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("missing topic examples: PrintR", rejected.stderr)

    def test_acthelp_exact_search_list_and_unknown(self) -> None:
        exact = self.run_tool(self.root, "acthelp", "if")
        self.assertIn("IF [keyword]", exact.stdout)
        self.assertIn("IF condition THEN", exact.stdout)
        self.assertIn("Begins a conditional branch.", exact.stdout)

        builtin = self.run_tool(self.root, "acthelp", "DbfSave")
        self.assertIn("DBF1", builtin.stdout)
        self.assertIn("Writes the staged DBF image", builtin.stdout)

        assembly = self.run_tool(self.root, "acthelp", "asmblock")
        self.assertIn("ASMBLOCK [keyword]", assembly.stdout)
        self.assertIn("Assembles validated NMOS 6502", assembly.stdout)
        self.assertIn("#<symbol", assembly.stdout)

        infinity = self.run_tool(self.root, "acthelp", "infinity")
        self.assertIn("INF [constant]", infinity.stdout)
        self.assertIn("positive IEEE-754 REAL infinity", infinity.stdout)

        searched = self.run_tool(self.root, "acthelp", "search", "joystick")
        self.assertIn("Joy [builtin]", searched.stdout)
        self.assertRegex(searched.stdout, r"MATCHES [1-9][0-9]*\n")

        listed = self.run_tool(self.root, "acthelp", "list", "type")
        self.assertEqual(
            [line.split()[0] for line in listed.stdout.splitlines()],
            ["BITMAP", "BYTE", "CARD", "CHAR", "INT", "MBITMAP", "MSPRITE", "REAL", "SPRITE"],
        )

        missing = self.run_tool(
            self.root, "acthelp", "not_a_language_token", expected_status=1
        )
        self.assertEqual(missing.stderr, "NO HELP FOR not_a_language_token\n")

    def test_acthelp_rejects_wrong_schema_and_corrupt_catalogs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrong_schema = root / "wrong-schema.sqlite3"
            with closing(sqlite3.connect(wrong_schema)) as database, database:
                database.execute("PRAGMA user_version=999")

            corrupt = root / "corrupt.sqlite3"
            corrupt.write_bytes(b"not a sqlite database\x00\xff")

            for catalog, expected in (
                (wrong_schema, "HELP DATABASE SCHEMA 999 (expected 1)"),
                (corrupt, "HELP DATABASE SCHEMA READ FAILED"),
            ):
                environment = os.environ.copy()
                environment["ACTION_HELP_DB"] = str(catalog)
                result = subprocess.run(
                    [str(self.tool_dir / "acthelp"), "IF"],
                    cwd=self.root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(expected, result.stderr)

    def test_actedit_highlight_is_quote_and_comment_aware(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE demo\n"
                "PROC main()\n"
                "  ASMBLOCK [ nop ]\n"
                "  REAL limit=INF\n"
                "  REAL missing=NAN\n"
                "  BgColor(6) ; PrintE is a comment here\n"
                "  PrintE(\"IF is text\")\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            highlighted = self.run_tool(project, "actedit", "main", "highlight")
            self.assertIn("\x1b[1;36mMODULE\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[1;36mASMBLOCK\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[35mINF\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[35mNAN\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[32mBgColor\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[34m6\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[2;37m; PrintE is a comment here\x1b[0m", highlighted.stdout)
            self.assertIn("\x1b[33m\"IF is text\"\x1b[0m", highlighted.stdout)

    def test_plain_actedit_ignores_editor_and_uses_uncolored_builtin_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE demo\nPROC main()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            master, slave = pty.openpty()
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", 30, 100, 0, 0),
            )
            environment = os.environ.copy()
            environment["EDITOR"] = "false"
            process = subprocess.Popen(
                [str(self.tool_dir / "actedit"), "main"],
                cwd=project,
                env=environment,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)
            captured = bytearray()

            def read_until(needle: bytes, timeout: float) -> bool:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], 0.1)
                    if not readable:
                        continue
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if needle in captured:
                        return True
                return needle in captured

            try:
                self.assertTrue(
                    read_until(b"ACTEDIT PLAIN", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIsNone(process.poll())
                self.assertIn(b"MODULE demo", captured)
                self.assertNotIn(b"\x1b[1;36mMODULE\x1b[0m", captured)
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
                read_until(b"ACTEDIT OK", 0.5)
                self.assertIn(b"ACTEDIT OK", captured)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

    def test_terminal_editor_help_and_reference_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE demo\nPROC main()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            master, slave = pty.openpty()
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", 30, 100, 0, 0),
            )
            process = subprocess.Popen(
                [str(self.tool_dir / "actedit"), "main", "tui"],
                cwd=project,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)
            captured = bytearray()

            def read_until(needle: bytes, timeout: float) -> bool:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], 0.1)
                    if not readable:
                        continue
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if needle in captured:
                        return True
                return needle in captured

            try:
                self.assertTrue(
                    read_until(b"ACTEDIT TUI", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"\x1b[1;36mMODULE\x1b[0m", captured)
                self.assertIn(b"\x1b[1 q", captured)
                self.assertIn(b"\x1b[1;7mM\x1b[0m", captured)
                os.write(master, b"\x1bOQ")
                self.assertTrue(
                    read_until(b"ACTEDIT KEYS [editor]", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"Ctrl-S saves atomically", captured)
                self.assertIn(b"F1 explains the Action keyword", captured)
                self.assertIn(b"Ctrl-B sets or clears", captured)
                os.write(master, b"\x1b[6~")
                self.assertTrue(
                    read_until(b"F6 applies ACTSPC", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"F5 opens a definition", captured)
                os.write(master, b"\x1b")
                time.sleep(0.1)
                os.write(master, b"\x1bOP")
                self.assertTrue(
                    read_until(b"Starts another group of global declarations.", 3.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x1b")
                time.sleep(0.1)
                os.write(master, b"\x1bOR")
                self.assertTrue(
                    read_until(b"ACTION LANGUAGE REFERENCE", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"KEYWORDS (", captured)
                self.assertIn(b"CORE BUILTINS (", captured)
                os.write(master, b"\r")
                self.assertTrue(
                    read_until(b"F3 - complete language reference", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"Browse every cataloged Action keyword", captured)
                os.write(master, b"\x1b")
                time.sleep(0.1)
                os.write(master, b"\x1bOS")
                self.assertTrue(
                    read_until(b"ACTION LIBRARIES", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertIn(b"DBF1 (20 features)", captured)
                self.assertIn(b"MATH1 (51 features)", captured)
                self.assertIn(b"GFX1 (76 features)", captured)
                os.write(master, b"\r")
                self.assertTrue(
                    read_until(b"LIBRARY DBF1", 3.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x1b[B")
                os.write(master, b"\r")
                self.assertTrue(
                    read_until(b"DbfAppend [builtin]", 3.0),
                    captured.decode(errors="replace"),
                )
                self.assertTrue(
                    read_until(b"ok=DbfAppend(handle)", 3.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x1bOS")
                self.assertTrue(read_until(b"ACTION LIBRARIES", 1.0))
                os.write(master, b"\x1b")
                time.sleep(0.1)
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
                read_until(b"ACTEDIT OK", 0.5)
                self.assertIn(b"ACTEDIT OK", captured)
                self.assertIn(b"\x1b[0 q", captured)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

    def test_terminal_editor_f8_launches_sprite_resource_editor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            resource_dir = project / "RES"
            resource_dir.mkdir()
            sprite = resource_dir / "PLAYER.SPR"
            self.run_tool(project, "actsprite", str(sprite), "new", "multicolor")
            (project / "SRC" / "MAIN.ACT").write_text(
                'MSPRITE Player=RESOURCE "player.spr"\n'
                "PROC MAIN()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            master, slave = pty.openpty()
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", 30, 100, 0, 0),
            )
            process = subprocess.Popen(
                [str(self.tool_dir / "actedit"), "main", "tui"],
                cwd=project,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)
            captured = bytearray()

            def read_until(needle: bytes, timeout: float) -> bool:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], 0.1)
                    if not readable:
                        continue
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if needle in captured:
                        return True
                return needle in captured

            try:
                self.assertTrue(read_until(b"ACTEDIT TUI", 3.0))
                os.write(master, b"\x1b[19~")
                self.assertTrue(
                    read_until(b"ACTSPRITE", 3.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b" \x13\x11")
                self.assertTrue(
                    read_until(b"actsprite updated", 4.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

            self.assertEqual(sprite.read_bytes()[4], 1)
            self.assertEqual(sprite.read_bytes()[8] & 0xC0, 0x40)
            self.assertFalse((resource_dir / "player.spr").exists())

    def test_terminal_editor_f8_creates_multicolor_bitmap_resource(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            resource_dir = project / "RES"
            resource_dir.mkdir()
            bitmap = resource_dir / "tile.abm"
            (project / "SRC" / "MAIN.ACT").write_text(
                'MBITMAP Tile=RESOURCE "tile.abm"\n'
                "PROC MAIN()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            master, slave = pty.openpty()
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", 30, 100, 0, 0),
            )
            process = subprocess.Popen(
                [str(self.tool_dir / "actedit"), "main", "tui"],
                cwd=project,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)
            captured = bytearray()

            def read_until(needle: bytes, timeout: float) -> bool:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], 0.1)
                    if not readable:
                        continue
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if needle in captured:
                        return True
                return needle in captured

            try:
                self.assertTrue(read_until(b"ACTEDIT TUI", 3.0))
                os.write(master, b"\x1b[19~")
                self.assertTrue(
                    read_until(b"ACTBITMAP", 3.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b" \x13\x11")
                self.assertTrue(
                    read_until(b"actbitmap updated", 4.0),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

            payload = bitmap.read_bytes()
            self.assertEqual(payload[:5], b"ABM1\x01")
            self.assertEqual(payload[8:12], b"\x20\x00\x20\x00")
            self.assertEqual(payload[16] & 0xC0, 0x40)

    def test_terminal_editor_f6_format_and_block_clipboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(Path(tmp))
            source = project / "SRC" / "MAIN.ACT"
            source.write_text(
                "MODULE   demo\n"
                "PROC   main()\n"
                "PrintE( \"ONE\" )\n"
                "IF   1 = 1   THEN\n"
                "PrintE(\"TWO\")\n"
                "FI\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            master, slave = pty.openpty()
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", 30, 110, 0, 0),
            )
            process = subprocess.Popen(
                [str(self.tool_dir / "actedit"), "main", "tui"],
                cwd=project,
                stdin=slave,
                stdout=slave,
                stderr=slave,
                close_fds=True,
            )
            os.close(slave)
            captured = bytearray()

            def read_until(needle: bytes, timeout: float = 3.0) -> bool:
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    readable, _, _ = select.select([master], [], [], 0.1)
                    if not readable:
                        continue
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if needle in captured:
                        return True
                return needle in captured

            try:
                self.assertTrue(read_until(b"ACTEDIT TUI"))
                os.write(master, b"\x1b[17~")
                self.assertTrue(
                    read_until(b"Formatted buffer; press Ctrl-S to save"),
                    captured.decode(errors="replace"),
                )

                os.write(master, b"\x02")
                self.assertTrue(read_until(b"Block mark set"))
                os.write(master, b"\x1b[C" * 6)
                os.write(master, b"\x03")
                self.assertTrue(read_until(b"Copied 6 characters"))
                os.write(master, b"\x18")
                self.assertTrue(read_until(b"Cut 6 characters"))
                os.write(master, b"\x16")
                self.assertTrue(read_until(b"Pasted 6 characters"))

                os.write(master, b"\x1b[H")
                os.write(master, b"\x02")
                os.write(master, b"\x1b[B" * 2)
                os.write(master, b"\x18")
                self.assertTrue(read_until(b"Cut 24 characters"))
                os.write(master, b"\x16")
                self.assertTrue(read_until(b"Pasted 24 characters"))

                os.write(master, b"\x01")
                self.assertTrue(read_until(b"Selected entire buffer"))
                os.write(master, b"\x03")
                self.assertTrue(read_until(b"Copied 105 characters"))
                os.write(master, b"\x1b")
                time.sleep(0.1)

                captured.clear()
                os.write(master, b"\x1b[<0;6;2M")
                os.write(master, b"\x1b[<32;12;2M")
                os.write(master, b"\x1b[<0;12;2m")
                os.write(master, b"\x03")
                self.assertTrue(read_until(b"Copied 6 characters"))
                os.write(master, b"\x1b")
                time.sleep(0.1)

                os.write(master, b"\x13")
                self.assertTrue(read_until(b"Saved "))
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

            self.assertEqual(
                source.read_text(encoding="ascii"),
                "MODULE demo\n"
                "PROC main()\n"
                "    PrintE(\"ONE\")\n"
                "    IF 1=1 THEN\n"
                "        PrintE(\"TWO\")\n"
                "    FI\n"
                "    RETURN\n"
                "ENDPROC\n",
            )


if __name__ == "__main__":
    unittest.main()
