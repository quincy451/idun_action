from pathlib import Path
import subprocess
import sys
import unittest


class TestVmHello(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.build_script = self.root / "tools" / "build_vmhello.sh"
        self.runner = self.root / "tools" / "cpmemu_runner.py"
        self.out_com = self.root / "build" / "vmhello.com"

    def test_vmhello_smoke(self) -> None:
        build_result = subprocess.run(
            [str(self.build_script)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        build_output = build_result.stdout + build_result.stderr

        if build_result.returncode != 0:
            if build_result.returncode == 2 or "docs/blockers.md" in build_output:
                self.skipTest(
                    "vmhello build unavailable; see docs/blockers.md. "
                    f"Details: {build_output.strip()}"
                )
            self.fail(build_output)

        if not self.out_com.is_file():
            self.fail(f"build succeeded but {self.out_com} is missing")

        run_result = subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "--cwd",
                str(self.root / "build"),
                "vmhello.com",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        run_output = run_result.stdout + run_result.stderr

        self.assertEqual(run_result.returncode, 0, msg=run_output)
        self.assertIn("HELLO FROM ACHERONVM", run_output)


if __name__ == "__main__":
    unittest.main()
