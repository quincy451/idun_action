from __future__ import annotations

from contextlib import closing
import fcntl
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


class TestCodeMap(unittest.TestCase):
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

    def make_linked_project(self, root: Path) -> Path:
        self.run_tool(root, "actnew", "demo")
        project = root / "DEMO"
        (project / "SRC" / "MAIN.ACT").write_text(
            "PROC HELPER(CARD value)\n"
            "RETURN\n"
            "ENDPROC\n"
            "PROC MAIN()\n"
            "HELPER(7)\n"
            "RETURN\n"
            "ENDPROC\n",
            encoding="ascii",
        )
        self.run_tool(project, "actc", "main")
        self.run_tool(project, "alink", "main")
        return project

    def test_alink_builds_transactional_semantic_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_linked_project(Path(tmp))
            database_path = project / ".action" / "code-map.sqlite3"
            self.assertTrue(database_path.is_file())

            with closing(sqlite3.connect(database_path)) as database:
                self.assertEqual(database.execute("PRAGMA user_version").fetchone()[0], 1)
                self.assertEqual(database.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                build = database.execute(
                    "SELECT entry_module,length(fingerprint),load_address,image_size FROM build"
                ).fetchone()
                self.assertEqual(build[0:3], ("MAIN", 16, 0x1000))
                self.assertGreater(build[3], 0)
                definitions = database.execute(
                    "SELECT name,kind,path,line,address,size FROM definitions ORDER BY line"
                ).fetchall()
                self.assertEqual(
                    [(row[0], row[1], row[2], row[3]) for row in definitions],
                    [
                        ("HELPER", "PROC", "SRC/MAIN.ACT", 1),
                        ("MAIN", "PROC", "SRC/MAIN.ACT", 4),
                    ],
                )
                self.assertTrue(all(row[4] is not None and row[5] > 0 for row in definitions))
                reference = database.execute(
                    "SELECT name,kind,caller,path,line,column_no,address "
                    "FROM references_map WHERE name='HELPER'"
                ).fetchone()
                self.assertEqual(reference[:6], ("HELPER", "CALL", "MAIN", "SRC/MAIN.ACT", 5, 1))
                self.assertIsNotNone(reference[6])

            summary = self.run_tool(project, "actedit", "main", "map")
            self.assertIn("CODE MAP MAIN\n", summary.stdout)
            self.assertIn("DEFINITIONS 2\n", summary.stdout)
            self.assertIn("REFERENCES 1\n", summary.stdout)

            definition = self.run_tool(
                project, "actedit", "main", "definition", "helper"
            )
            self.assertIn("DEFINITION PROC HELPER SRC/MAIN.ACT:1:6", definition.stdout)
            self.assertIn("SIGNATURE PROC HELPER(CARD value)\n", definition.stdout)

            references = self.run_tool(
                project, "actedit", "main", "references", "helper"
            )
            self.assertIn(
                "REFERENCE CALL HELPER SRC/MAIN.ACT:5:1", references.stdout
            )
            self.assertIn("CALLER MAIN", references.stdout)
            self.assertTrue(references.stdout.endswith("REFERENCES 1\n"))

    def test_f5_and_f7_navigate_linked_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_linked_project(Path(tmp))
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
                self.assertTrue(read_until(b"ACTEDIT"), captured.decode(errors="replace"))
                os.write(master, b"\x1b[B" * 4)
                os.write(master, b"\x1b[15~")
                self.assertTrue(
                    read_until(b"Definition HELPER -> SRC/MAIN.ACT:1"),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x1b[18~")
                self.assertTrue(
                    read_until(b"References to HELPER (1)"),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\r")
                self.assertTrue(
                    read_until(b"Definition HELPER -> SRC/MAIN.ACT:5"),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)

    def test_ctrl_click_navigates_to_linked_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_linked_project(Path(tmp))
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
                self.assertTrue(read_until(b"ACTEDIT"), captured.decode(errors="replace"))
                # SGR mouse: Ctrl + left press at source line 5, column 1.
                # The five-column gutter places that source character at x=6;
                # the title row places source line 5 at terminal row y=6.
                os.write(master, b"\x1b[<16;6;6M")
                self.assertTrue(
                    read_until(b"Definition HELPER -> SRC/MAIN.ACT:1"),
                    captured.decode(errors="replace"),
                )
                os.write(master, b"\x11")
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                os.close(master)


if __name__ == "__main__":
    unittest.main()
