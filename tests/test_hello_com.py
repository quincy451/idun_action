from pathlib import Path
import subprocess
import sys
import unittest


class TestHelloCom(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.build_script = self.root / "tools" / "build_hello.sh"
        self.runner = self.root / "tools" / "cpmemu_runner.py"
        self.out_com = self.root / "build" / "hello.com"
        self.cpmemu = self.root.parent / "cpm65-u64" / "bin" / "cpmemu"

    def test_hello_com_smoke(self) -> None:
        build_result = subprocess.run(
            [str(self.build_script)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        build_output = build_result.stdout + build_result.stderr

        if build_result.returncode != 0:
            if (
                build_result.returncode == 2
                or "No supported hello.com build path is available." in build_output
            ):
                self.skipTest(
                    "hello.com build unavailable; install cpmemu+asm.com or llvm-mos. "
                    f"See docs/cpmemu.md. Details: {build_output.strip()}"
                )
            self.fail(build_output)

        if not self.out_com.is_file():
            self.fail(f"build succeeded but {self.out_com} is missing")

        if not self.cpmemu.is_file():
            self.skipTest("hello.com built, but cpmemu is missing. See docs/cpmemu.md")

        run_result = subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "--cwd",
                str(self.root / "build"),
                "hello.com",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        run_output = run_result.stdout + run_result.stderr

        self.assertEqual(run_result.returncode, 0, msg=run_output)
        self.assertIn("HELLO FROM ACTIONC64U", run_output)


if __name__ == "__main__":
    unittest.main()
