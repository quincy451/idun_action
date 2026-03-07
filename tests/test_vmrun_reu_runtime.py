from pathlib import Path
import os
import subprocess
import sys
import unittest


class TestVmRunReuRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.pack_tool = self.root / "tools" / "avm_pack.py"
        self.runner = self.root / "tools" / "cpmemu_runner.py"
        self.build_vm = self.root / "tools" / "build_vmrun.sh"
        self.build_actc = self.root / "tools" / "build_actc.sh"
        self.build_actmon = self.root / "tools" / "build_actmon.sh"
        self.example_text = self.root / "examples" / "reu_runtime.avm.txt"
        self.example_avm = self.root / "examples" / "reurun.avm"
        self.echo_text = self.root / "examples" / "vmecho.avm.txt"
        self.echo_avm = self.root / "examples" / "vmecho.avm"
        self.out_vm = self.root / "build" / "vm.com"

    def run_build(self, script: Path, *, env: dict[str, str] | None = None) -> str:
        result = subprocess.run(
            [str(script)],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            if result.returncode == 2 or "docs/blockers.md" in output:
                self.skipTest(f"required CP/M tool build unavailable: {output.strip()}")
            self.fail(output)
        return output

    def test_vmrun_executes_reu_program_at_runtime(self) -> None:
        pack = subprocess.run(
            [
                sys.executable,
                str(self.pack_tool),
                str(self.example_text),
                "--text",
                "--output",
                str(self.example_avm),
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(pack.returncode, 0, msg=pack.stdout + pack.stderr)
        self.assertTrue(self.example_avm.is_file())

        self.run_build(self.build_vm)

        run_result = subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "--cwd",
                str(self.root / "examples"),
                str(self.out_vm),
                self.example_avm.name,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        output = run_result.stdout + run_result.stderr
        self.assertEqual(run_result.returncode, 0, msg=output)
        self.assertIn("65", output)
        self.assertNotIn("REU FAIL", output)

    def test_vmrun_can_read_console_input_and_replay_from_reu(self) -> None:
        pack = subprocess.run(
            [
                sys.executable,
                str(self.pack_tool),
                str(self.echo_text),
                "--text",
                "--output",
                str(self.echo_avm),
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(pack.returncode, 0, msg=pack.stdout + pack.stderr)
        self.assertTrue(self.echo_avm.is_file())

        self.run_build(self.build_vm)

        run_result = subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "--stdin-text",
                "abc\r",
                "--cwd",
                str(self.root / "examples"),
                str(self.out_vm),
                self.echo_avm.name,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        output = run_result.stdout + run_result.stderr
        self.assertEqual(run_result.returncode, 0, msg=output)
        self.assertIn("type>", output)
        self.assertIn("stored:abc", output.replace("\r", "").replace("\n", ""))

    def test_hw_backend_build_scripts_succeed(self) -> None:
        hw_env = dict(os.environ)
        hw_env["ACTIONC64U_REU_BACKEND"] = "hw"

        try:
            self.run_build(self.build_vm, env=hw_env)
            self.run_build(self.build_actc, env=hw_env)
            self.run_build(self.build_actmon, env=hw_env)
        finally:
            self.run_build(self.build_vm)
            self.run_build(self.build_actc)
            self.run_build(self.build_actmon)


if __name__ == "__main__":
    unittest.main()
