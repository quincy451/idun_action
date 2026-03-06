from pathlib import Path
import subprocess
import sys
import unittest


class TestCpmemuAvailability(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.cpm_root = self.root.parent / "cpm65-u64"
        self.cpmemu = self.cpm_root / "bin" / "cpmemu"
        self.dump_com = self.cpm_root / ".obj" / "dump.com"

    def test_cpmemu_help(self) -> None:
        if not self.cpmemu.is_file():
            self.skipTest("cpmemu not found; build ../cpm65-u64 first. See docs/cpmemu.md")

        result = subprocess.run(
            [str(self.cpmemu), "-h"],
            cwd=self.cpm_root,
            text=True,
            capture_output=True,
            check=False,
        )

        combined = result.stdout + result.stderr
        self.assertIn("cpm", combined.lower())
        self.assertTrue(result.returncode == 0 or "-h" in combined or "usage" in combined.lower())

    def test_dump_com_sample_if_available(self) -> None:
        if not self.cpmemu.is_file():
            self.skipTest("cpmemu not found; build ../cpm65-u64 first. See docs/cpmemu.md")
        if not self.dump_com.is_file():
            self.skipTest("dump.com not found in ../cpm65-u64/.obj; build CP/M-65 first. See docs/cpmemu.md")

        result = subprocess.run(
            [
                sys.executable,
                str(self.root / "tools" / "cpmemu_runner.py"),
                ".obj/dump.com",
                "--diskdefs-arg",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 2, msg=combined)
        self.assertNotIn("Missing cpmemu binary", combined)


if __name__ == "__main__":
    unittest.main()
