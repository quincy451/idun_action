from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from vice_harness import ViceHarness, ViceUnavailable  # noqa: E402


# These bodies come from the native direct-PRG matrix. Fixed result addresses
# and a completion loop are the only adaptations needed by the VICE harness.
NATIVE_CASES = {
    "actc_runtime_integer_nested_for_exit_linked": (
        "MODULE MAIN\n"
        "CARD I\n"
        "CARD J\n"
        "CARD S\n"
        "BYTE DONE=$C400\n"
        "CARD RESULT=$C402\n"
        "PROC MAIN()\n"
        "S=0\n"
        "FOR I=1 TO 2\n"
        "DO\n"
        "FOR J=1 TO 5\n"
        "DO\n"
        "S=S+J\n"
        "EXIT\n"
        "OD\n"
        "S=S+10\n"
        "OD\n"
        "RESULT=S\n"
        "DONE=1\n"
        "DO\n"
        "OD\n"
        "ENDPROC\n",
        bytes.fromhex("0100160000000000"),
    ),
    "actc_runtime_integer_dynamic_while_mul_div_exit_linked": (
        "MODULE MAIN\n"
        "CARD I\n"
        "CARD S\n"
        "BYTE DONE=$C400\n"
        "CARD RESULT=$C402\n"
        "PROC MAIN()\n"
        "I=1\n"
        "S=0\n"
        "WHILE I<20 DO\n"
        "I=I*2\n"
        "I=I/1\n"
        "IF I=6 THEN\n"
        "EXIT\n"
        "FI\n"
        "I=I+1\n"
        "OD\n"
        "S=I\n"
        "RESULT=S\n"
        "DONE=1\n"
        "DO\n"
        "OD\n"
        "ENDPROC\n",
        bytes.fromhex("0100060000000000"),
    ),
    "nested_else_local_call_chain_nested_do_if_else": (
        "MODULE MAIN\n"
        "CARD X\n"
        "CARD Y\n"
        "BYTE DONE=$C400\n"
        "CARD RESULT=$C402\n"
        "PROC B()\n"
        "DO\n"
        "IF Y=1 THEN\n"
        "Y=3\n"
        "ELSE\n"
        "Y=13\n"
        "FI\n"
        "UNTIL Y=13\n"
        "OD\n"
        "RETURN\n"
        "PROC A()\n"
        "B()\n"
        "RETURN\n"
        "PROC MAIN()\n"
        "X=1\n"
        "Y=0\n"
        "IF X=1 THEN\n"
        "IF Y=1 THEN\n"
        "Y=4\n"
        "ELSE\n"
        "A()\n"
        "FI\n"
        "FI\n"
        "RESULT=Y\n"
        "DONE=1\n"
        "DO\n"
        "OD\n"
        "ENDPROC\n",
        bytes.fromhex("01000D0000000000"),
    ),
    "actc_runtime_integer_for_ascending_wrap_linked": (
        "MODULE MAIN\n"
        "CARD I\n"
        "CARD S\n"
        "BYTE DONE=$C400\n"
        "CARD RESULT=$C402\n"
        "PROC MAIN()\n"
        "S=0\n"
        "FOR I=1 TO 3\n"
        "DO\n"
        "S=S+I\n"
        "OD\n"
        "FOR I=65535 TO 65535\n"
        "DO\n"
        "S=S+1\n"
        "OD\n"
        "RESULT=S\n"
        "DONE=1\n"
        "DO\n"
        "OD\n"
        "ENDPROC\n",
        bytes.fromhex("0100070000000000"),
    ),
    "real_do_until_gt_real_add_loop": (
        "MODULE MAIN\n"
        "REAL A=$C404\n"
        "REAL B\n"
        "REAL C\n"
        "CARD Y=$C402\n"
        "BYTE DONE=$C400\n"
        "PROC MAIN()\n"
        "A=REAL(0)\n"
        "B=REAL(3)\n"
        "C=REAL(1)\n"
        "DO\n"
        "A=A+C\n"
        "UNTIL A>B\n"
        "OD\n"
        "Y=7\n"
        "DONE=1\n"
        "DO\n"
        "OD\n"
        "ENDPROC\n",
        bytes.fromhex("01000700") + struct.pack("<f", 4.0),
    ),
}


@unittest.skipUnless(shutil.which("x64sc"), "x64sc is required for direct PRG execution")
class TestNativeSuiteCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "tools" / "build_linux_tools.sh")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        cls.tool_dir = Path(result.stdout.strip().splitlines()[-1])

    def run_tool(self, project: Path, tool: str) -> None:
        result = subprocess.run(
            [str(self.tool_dir / tool), "main"],
            cwd=project,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"{tool} stdout:\n{result.stdout}\n{tool} stderr:\n{result.stderr}",
        )

    def test_native_direct_prg_control_flow_cases_execute(self) -> None:
        for case_name, (source, expected) in NATIVE_CASES.items():
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp)
                shared_lib = workspace / "LIB"
                shared_lib.mkdir()
                for runtime_object in (ROOT / "src" / "runtime" / "modules").glob(
                    "*.obj"
                ):
                    shutil.copy2(
                        runtime_object,
                        shared_lib / runtime_object.name.upper(),
                    )

                create = subprocess.run(
                    [str(self.tool_dir / "actnew"), "demo"],
                    cwd=workspace,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(
                    create.returncode,
                    0,
                    msg=create.stdout + create.stderr,
                )
                project = workspace / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    source,
                    encoding="ascii",
                )
                self.run_tool(project, "actc")
                self.run_tool(project, "alink")

                vice_context = ViceHarness(timeout=5.0)
                try:
                    vice_context.start()
                except ViceUnavailable as exc:
                    self.skipTest(str(exc))
                try:
                    vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                    vice_context.monitor.memory_set(0xC400, bytes(8))
                    vice_context.monitor.resume()
                    snapshot = bytes(8)
                    deadline = time.monotonic() + 5.0
                    while time.monotonic() < deadline:
                        time.sleep(0.02)
                        snapshot = vice_context.monitor.memory_get(0xC400, 0xC407)
                        if snapshot[0] == 1:
                            break
                finally:
                    vice_context.stop()

                self.assertEqual(
                    snapshot,
                    expected,
                    f"native matrix case {case_name} produced the wrong result",
                )
