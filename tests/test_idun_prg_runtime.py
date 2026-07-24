from __future__ import annotations

import math
import random
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

from vice_harness import (  # noqa: E402
    ViceHarness,
    ViceProtocolError,
    ViceUnavailable,
    locate_x64sc,
    vice_version,
)


def vice_37_has_unreliable_dbf_monitor_execution() -> bool:
    try:
        return vice_version(locate_x64sc()).startswith("x64sc (VICE 3.7")
    except ViceUnavailable:
        return False


def float32_from_bits(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]


def float32_bits(value: float) -> int:
    try:
        return struct.unpack("<I", struct.pack("<f", value))[0]
    except OverflowError:
        return 0xFF800000 if math.copysign(1.0, value) < 0.0 else 0x7F800000


def binary32_is_nan(value: int) -> bool:
    return (value & 0x7F800000) == 0x7F800000 and (value & 0x007FFFFF) != 0


def exact_binary32_decimal(value: int) -> str:
    sign = "-" if value & 0x80000000 else ""
    exponent_field = (value >> 23) & 0xFF
    fraction = value & 0x007FFFFF
    if exponent_field == 0xFF:
        return "NAN" if fraction else sign + "INF"
    if exponent_field == 0:
        if fraction == 0:
            return sign + "0"
        significand = fraction
        exponent = -126
    else:
        significand = 0x00800000 | fraction
        exponent = exponent_field - 127
    power = exponent - 23
    if power >= 0:
        return sign + str(significand << power)
    scale = -power
    digits = str(significand * (5**scale))
    if len(digits) <= scale:
        body = "0." + ("0" * (scale - len(digits))) + digits
    else:
        body = digits[:-scale] + "." + digits[-scale:]
    body = body.rstrip("0").rstrip(".")
    return sign + body


@unittest.skipUnless(shutil.which("x64sc"), "x64sc is required for direct PRG execution")
class TestIdunPrgRuntime(unittest.TestCase):
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

    def run_tool(self, project: Path, tool: str, module: str) -> None:
        result = subprocess.run(
            [str(self.tool_dir / tool), module],
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

    def test_prime_real_sample_finds_thirty_primes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for name in (
                "rt_f_sqrt.obj",
                "rt_f_to_i.obj",
                "rt_i_mod.obj",
                "rt_i_to_f.obj",
                "rt_print_i.obj",
            ):
                shutil.copy2(
                    ROOT / "src" / "runtime" / "modules" / name,
                    shared_lib / name.upper(),
                )

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            shutil.copy2(
                ROOT / "examples" / "prime_real.act",
                project / "SRC" / "MAIN.ACT",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            debug_lines = (project / "BIN" / "MAIN.DBG").read_text(
                encoding="ascii"
            ).splitlines()
            prime_count_address = next(
                int(parts[1])
                for line in debug_lines
                if len(parts := line.split()) == 4
                and parts[0] == "y"
                and parts[3] == "MAIN_PRIMECOUNT_LO"
            )

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
                # PrintE/PrintIE call the C64 KERNAL.  On slower hosts the
                # binary monitor is available before KERNAL/BASIC startup has
                # initialized the output path, so wait for the real readiness
                # condition instead of guessing with a host-time delay.
                vice_context.wait_for_screen_contains("ready.", timeout=12.0)
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(prime_count_address, b"\x00")
                vice_context.monitor.resume()

                deadline = time.monotonic() + 8.0
                count = 0
                while time.monotonic() < deadline:
                    time.sleep(0.05)
                    count = vice_context.monitor.memory_get(
                        prime_count_address, prime_count_address
                    )[0]
                    if count == 30:
                        time.sleep(0.25)
                        count = vice_context.monitor.memory_get(
                            prime_count_address, prime_count_address
                        )[0]
                        break
                self.assertEqual(count, 30, "prime sample produced the wrong count")
            finally:
                vice_context.stop()

    def _assert_real_function_fixture_executes(
        self,
        fixture_name: str,
        expected_values: dict[str, float],
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for name in (
                "rt_f_abs.obj",
                "rt_f_add.obj",
                "rt_f_addsub_core.obj",
                "rt_f_cmp.obj",
                "rt_f_div.obj",
                "rt_f_hypot.obj",
                "rt_f_max.obj",
                "rt_f_min.obj",
                "rt_f_mul.obj",
                "rt_f_special.obj",
                "rt_f_sqrt.obj",
                "rt_print_f.obj",
            ):
                shutil.copy2(
                    ROOT / "src" / "runtime" / "modules" / name,
                    shared_lib / name.upper(),
                )

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            shutil.copy2(
                ROOT / "tests" / "parity" / fixture_name,
                project / "SRC" / "MAIN.ACT",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            debug_lines = (project / "BIN" / "MAIN.DBG").read_text(
                encoding="ascii"
            ).splitlines()
            result_addresses = {
                name: next(
                    int(parts[1])
                    for line in debug_lines
                    if len(parts := line.split()) == 4
                    and parts[0] == "y"
                    and parts[3] == f"MAIN_{name}_B0"
                )
                for name in expected_values
            }
            expected_bytes = {
                name: struct.pack("<f", value)
                for name, value in expected_values.items()
            }

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                time.sleep(1.0)
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                for result_address in result_addresses.values():
                    vice_context.monitor.memory_set(result_address, b"\x55" * 4)
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                actual = {}
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    actual = {
                        name: vice_context.monitor.memory_get(address, address + 3)
                        for name, address in result_addresses.items()
                    }
                    if actual == expected_bytes:
                        break
                self.assertEqual(
                    actual,
                    expected_bytes,
                    "REAL function returned the wrong value",
                )
            finally:
                vice_context.stop()

    def test_native_real_function_parity_fixtures_execute(self) -> None:
        for fixture_name, expected_values in (
            ("finite_real_min.act", {"RESULT": 1.0}),
            ("finite_real_min_permuted.act", {"RESULT": 1.0}),
            ("two_real_second_return_permuted.act", {"RESULT": 2.0}),
            ("real_function_binary_hypot.act", {"RESULT": 5.0}),
            (
                "real_two_function_nested_postfix.act",
                {"LONGRESULT": 5.0, "SHORTRESULT": 3.0},
            ),
            ("real_function_call_chain_postfix.act", {"RESULT": 5.0}),
            ("real_function_nested_local_call_postfix.act", {"RESULT": 5.0}),
            ("real_function_user_call_arguments_postfix.act", {"RESULT": 3.0}),
            ("real_function_forward_frame_postfix.act", {"RESULT": 3.0}),
            (
                "real_function_if_else_postfix.act",
                {"FIRST": 3.0, "SECOND": 4.0},
            ),
            (
                "real_function_sequential_if_else_postfix.act",
                {"FIRST": 4.0, "SECOND": 3.0},
            ),
            (
                "real_function_nested_if_else_postfix.act",
                {"FIRST": 1.0, "SECOND": 4.0, "THIRD": 3.0},
            ),
            (
                "real_function_four_sequential_if_postfix.act",
                {"FIRST": 4.0, "SECOND": 3.0},
            ),
            (
                "real_function_four_deep_if_postfix.act",
                {"FIRST": 1.0, "SECOND": 5.0, "THIRD": 4.0},
            ),
            (
                "real_function_early_return_if_postfix.act",
                {"FIRST": 3.0, "SECOND": 3.0},
            ),
            (
                "real_function_early_return_four_deep_postfix.act",
                {"FIRST": 1.0, "SECOND": 5.0, "THIRD": 4.0},
            ),
            (
                "real_function_loops_postfix.act",
                {"FIRST": 4.0, "SECOND": 3.0},
            ),
            (
                "real_function_loop_exit_postfix.act",
                {"FIRST": 4.0, "SECOND": 3.0},
            ),
            (
                "real_function_for_postfix.act",
                {"ASCENDING": 4.0, "DESCENDING": 7.0},
            ),
            (
                "real_function_dynamic_for_postfix.act",
                {"LOWER": 7.0, "UPPER": 7.0},
            ),
            (
                "real_function_literal_clamp_comma_locals_postfix.act",
                {
                    "LOW_RESULT": -1.0,
                    "ZERO_RESULT": 0.0,
                    "HIGH_RESULT": 1.0,
                },
            ),
        ):
            with self.subTest(fixture=fixture_name):
                self._assert_real_function_fixture_executes(
                    fixture_name,
                    expected_values,
                )

    def test_math1_transcendental_functions_execute_on_6502(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for source in (ROOT / "src" / "runtime" / "modules").glob("*.obj"):
                shutil.copy2(source, shared_lib / source.name.upper())
            shutil.copy2(ROOT / "lib" / "math1.act", shared_lib / "MATH1.ACT")

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "MATH1"\n'
                "MODULE MAIN\n"
                "PROC MAIN()\n"
                "REAL r0=$C200,r1=$C204,r2=$C208,r3=$C20C\n"
                "REAL r4=$C210,r5=$C214,r6=$C218,r7=$C21C\n"
                "REAL r8=$C220,r9=$C224,r10=$C228,r11=$C22C\n"
                "REAL r12=$C230,r13=$C234,r14=$C238,r15=$C23C\n"
                "REAL r16=$C240,r17=$C244,r18=$C248,r19=$C24C\n"
                "REAL r20=$C250,r21=$C254,r22=$C258\n"
                "BYTE done=$C25C\n"
                "r0=FSin(MATH_HALF_PI)\n"
                "r1=FCos(MATH_PI)\n"
                "r2=FTan(MATH_QUARTER_PI)\n"
                "r3=FATan(-2.0)\n"
                "r4=FATan2(-1.0,-1.0)\n"
                "r5=FASin(0.5)\n"
                "r6=FACos(-0.5)\n"
                "r7=FExp(1.0)\n"
                "r8=FLn(MATH_E)\n"
                "r9=FLog10(1000.0)\n"
                "r10=FPow(2.0,10.0)\n"
                "r11=FHypot(3.0,4.0)\n"
                "r12=FSinh(1.0)\n"
                "r13=FCosh(1.0)\n"
                "r14=FTanh(1.0)\n"
                "r15=FATanh(0.5)\n"
                "r16=FLog2(8.0)\n"
                "r17=FSec(0.0)\n"
                "r18=FCsc(MATH_HALF_PI)\n"
                "r19=FCot(MATH_QUARTER_PI)\n"
                "r20=FASec(2.0)\n"
                "r21=FACsc(2.0)\n"
                "r22=FACot(1.0)\n"
                "done=1\n"
                "DO\n"
                "OD\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            main_object = (project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("\nu RT_F_SIN\n", main_object)
            self.assertNotIn("\nx FSIN ", main_object)
            self.assertIn("\nu RT_F_COS\n", main_object)
            self.assertNotIn("\nx FCOS ", main_object)
            self.assertIn("\nu RT_F_TAN\n", main_object)
            self.assertNotIn("\nx FTAN ", main_object)
            self.assertIn("\nu RT_F_ATAN\n", main_object)
            self.assertNotIn("\nx FATAN ", main_object)
            self.assertIn("\nu RT_F_ATAN2\n", main_object)
            self.assertNotIn("\nx FATAN2 ", main_object)
            self.assertIn("\nu RT_F_ASIN\n", main_object)
            self.assertNotIn("\nx FASIN ", main_object)
            self.assertIn("\nu RT_F_ACOS\n", main_object)
            self.assertNotIn("\nx FACOS ", main_object)
            self.assertIn("\nu RT_F_SEC\n", main_object)
            self.assertNotIn("\nx FSEC ", main_object)
            self.assertIn("\nu RT_F_CSC\n", main_object)
            self.assertNotIn("\nx FCSC ", main_object)
            self.assertIn("\nu RT_F_COT\n", main_object)
            self.assertNotIn("\nx FCOT ", main_object)
            self.assertIn("\nu RT_F_ASEC\n", main_object)
            self.assertNotIn("\nx FASEC ", main_object)
            self.assertIn("\nu RT_F_ACSC\n", main_object)
            self.assertNotIn("\nx FACSC ", main_object)
            self.assertIn("\nu RT_F_ACOT\n", main_object)
            self.assertNotIn("\nx FACOT ", main_object)
            self.assertIn("\nu RT_F_POW\n", main_object)
            self.assertNotIn("\nx FPOW ", main_object)
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=6.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC200, bytes(93))
                vice_context.monitor.resume()
                deadline = time.monotonic() + 12.0
                snapshot = bytes(93)
                while time.monotonic() < deadline:
                    time.sleep(0.05)
                    snapshot = vice_context.monitor.memory_get(0xC200, 0xC25C)
                    if snapshot[92] == 1:
                        break
                self.assertEqual(snapshot[92], 1, "MATH1 test PRG did not finish")
            finally:
                vice_context.stop()

            actual = struct.unpack("<23f", snapshot[:92])
            expected = (
                1.0,
                -1.0,
                1.0,
                math.atan(-2.0),
                math.atan2(-1.0, -1.0),
                math.asin(0.5),
                math.acos(-0.5),
                math.e,
                1.0,
                3.0,
                1024.0,
                5.0,
                math.sinh(1.0),
                math.cosh(1.0),
                math.tanh(1.0),
                math.atanh(0.5),
                3.0,
                1.0,
                1.0,
                1.0,
                math.acos(0.5),
                math.asin(0.5),
                math.atan2(1.0, 1.0),
            )
            for index, (observed, wanted) in enumerate(zip(actual, expected)):
                self.assertTrue(math.isfinite(observed), f"result {index} is not finite")
                self.assertAlmostEqual(
                    observed,
                    wanted,
                    delta=max(0.005, abs(wanted) * 0.005),
                    msg=f"MATH1 result {index}",
                )

    def test_gfx1_bank2_pixels_resources_and_sprite_staging_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for source in (ROOT / "src" / "runtime" / "modules").glob("*.obj"):
                shutil.copy2(source, shared_lib / source.name.upper())
            shutil.copy2(ROOT / "lib" / "gfx1.act", shared_lib / "GFX1.ACT")

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            sprite = project / "RES" / "player.spr"
            bitmap = project / "RES" / "marker.abm"
            for command in (
                ("actsprite", str(sprite), "new"),
                ("actsprite", str(sprite), "set", "0", "0", "1"),
                ("actsprite", str(sprite), "color", "14"),
                ("actbitmap", str(bitmap), "new", "16", "8"),
                ("actbitmap", str(bitmap), "set", "2", "3", "1"),
            ):
                edited = subprocess.run(
                    [str(self.tool_dir / command[0]), *command[1:]],
                    cwd=project,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(
                    edited.returncode, 0, msg=edited.stdout + edited.stderr
                )

            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "GFX1"\n'
                'SPRITE Player=RESOURCE "player.spr"\n'
                'BITMAP Marker=RESOURCE "marker.abm"\n'
                "MODULE MAIN\n"
                "PROC MAIN()\n"
                "BYTE cleared=$C280,corner=$C281,linePixel=$C282\n"
                "BYTE xorPixel=$C283,resourcePixel=$C284,multiPixel=$C285\n"
                "BYTE spriteByte=$C286,spritePointer=$C287,screenByte=$C288\n"
                "BYTE cpuPortResult=$C289\n"
                "CARD vicBaseResult=$C28A,spriteBaseResult=$C28C\n"
                "BYTE assetByte=$C28E,assetColor=$C28F,assetMode=$C290\n"
                "BYTE done=$C291\n"
                "BYTE cpuPort=$01\n"
                "BYTE POINTER address\n"
                "GfxHires($8400,$A000)\n"
                "GfxUseSprites($8800)\n"
                "GfxBitmapClear(0)\n"
                "GfxScreenClear(0,GFX_BLACK)\n"
                "Plot(0,0)\n"
                "Unplot(0,0)\n"
                "cleared=Point(0,0)\n"
                "Plot(319,199)\n"
                "corner=Point(319,199)\n"
                "LineDraw(0,1,7,1)\n"
                "linePixel=Point(2,1)\n"
                "PlotXor(3,1)\n"
                "xorPixel=Point(3,1)\n"
                "BitmapStamp(Marker,16,16)\n"
                "resourcePixel=Point(18,19)\n"
                "MPlot(10,50,3)\n"
                "multiPixel=MPoint(10,50)\n"
                "GfxCellColors(0,0,GFX_WHITE,GFX_BLACK)\n"
                "SpritePlace(0,Player,120,80)\n"
                "address=$8800\n"
                "spriteByte=address^\n"
                "address=$87F8\n"
                "spritePointer=address^\n"
                "address=$8400\n"
                "screenByte=address^\n"
                "cpuPortResult=cpuPort\n"
                "vicBaseResult=_GfxVicBase\n"
                "spriteBaseResult=_GfxSpriteMemory\n"
                "assetByte=_GfxReadByte(Player,0)\n"
                "assetColor=SpriteDefaultColor(Player)\n"
                "assetMode=SpriteIsMulticolor(Player)\n"
                "done=1\n"
                "DO\n"
                "OD\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=6.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC280, bytes(18))
                vice_context.monitor.resume()
                deadline = time.monotonic() + 12.0
                snapshot = bytes(18)
                while time.monotonic() < deadline:
                    time.sleep(0.05)
                    snapshot = vice_context.monitor.memory_get(0xC280, 0xC291)
                    if snapshot[17] == 1:
                        break
                self.assertEqual(snapshot[17], 1, "GFX1 test PRG did not finish")
                sprite_registers = vice_context.monitor.memory_get(0xD000, 0xD02E)
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[:6], bytes([0, 1, 1, 0, 1, 3]))
            self.assertEqual(snapshot[6], 0x80, snapshot.hex())
            self.assertEqual(snapshot[7], 0x20)
            self.assertEqual(snapshot[8], 0x10)
            self.assertEqual(snapshot[9] & 0x07, 0x07)
            self.assertEqual(int.from_bytes(snapshot[10:12], "little"), 0x8000)
            self.assertEqual(int.from_bytes(snapshot[12:14], "little"), 0x8800)
            self.assertEqual(snapshot[14:17], bytes([0x80, 14, 0]))
            self.assertEqual(sprite_registers[0], 120)
            self.assertEqual(sprite_registers[1], 80)
            self.assertEqual(sprite_registers[0x15] & 1, 1)
            self.assertEqual(sprite_registers[0x1C] & 1, 0)
            self.assertEqual(sprite_registers[0x27] & 15, 14)

    def test_ieee_binary32_runtime_matches_edge_and_random_vectors(self) -> None:
        runtime_names = (
            "rt_f_abs.obj",
            "rt_f_add.obj",
            "rt_f_cmp.obj",
            "rt_f_div.obj",
            "rt_f_floor.obj",
            "rt_f_ceil.obj",
            "rt_f_round.obj",
            "rt_f_frac.obj",
            "rt_f_mod.obj",
            "rt_f_hypot.obj",
            "rt_f_min.obj",
            "rt_f_max.obj",
            "rt_f_mul.obj",
            "rt_f_sqrt.obj",
            "rt_f_sub.obj",
            "rt_f_trunc.obj",
            "rt_f_to_i.obj",
            "rt_i_to_f.obj",
            "rt_s_to_f.obj",
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for name in runtime_names:
                shutil.copy2(
                    ROOT / "src" / "runtime" / "modules" / name,
                    shared_lib / name.upper(),
                )

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "REAL a=$C000,b=$C004\n"
                "REAL addresult=$C008,subresult=$C00C\n"
                "REAL mulresult=$C010,divresult=$C014\n"
                "REAL sqrtresult=$C018,absresult=$C01C\n"
                "REAL fromcard=$C020,fromint=$C024\n"
                "INT intresult=$C028\n"
                "BYTE eqresult=$C02A,neresult=$C02B,ltresult=$C02C\n"
                "BYTE leresult=$C02D,gtresult=$C02E,geresult=$C02F\n"
                "CARD cardinput=$C030\n"
                "INT intinput=$C032\n"
                "BYTE done=$C034\n"
                "REAL truncresult=$C035\n"
                "REAL floorresult=$C039\n"
                "REAL ceilresult=$C03D\n"
                "REAL roundresult=$C041\n"
                "REAL fracresult=$C045\n"
                "REAL modresult=$C049\n"
                "REAL hypotresult=$C04D\n"
                "PROC MAIN()\n"
                "addresult=a+b\n"
                "subresult=a-b\n"
                "mulresult=a*b\n"
                "divresult=a/b\n"
                "sqrtresult=FSqrt(a)\n"
                "absresult=FAbs(a)\n"
                "fromcard=REAL(cardinput)\n"
                "fromint=REAL(intinput)\n"
                "intresult=INT(a)\n"
                "truncresult=FTrunc(a)\n"
                "floorresult=FFloor(a)\n"
                "ceilresult=FCeil(a)\n"
                "roundresult=FRound(a)\n"
                "fracresult=FFrac(a)\n"
                "modresult=FMod(a,b)\n"
                "hypotresult=FHypot(a,b)\n"
                "eqresult=0\n"
                "neresult=0\n"
                "ltresult=0\n"
                "leresult=0\n"
                "gtresult=0\n"
                "geresult=0\n"
                "IF a=b THEN\n"
                "eqresult=1\n"
                "FI\n"
                "IF a<>b THEN\n"
                "neresult=1\n"
                "FI\n"
                "IF a<b THEN\n"
                "ltresult=1\n"
                "FI\n"
                "IF a<=b THEN\n"
                "leresult=1\n"
                "FI\n"
                "IF a>b THEN\n"
                "gtresult=1\n"
                "FI\n"
                "IF a>=b THEN\n"
                "geresult=1\n"
                "FI\n"
                "done=1\n"
                "DO\n"
                "OD\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            vectors = [
                (0x3FC00000, 0x40100000),
                (0xBF800000, 0x40000000),
                (0x7F7FFFFF, 0x7F7FFFFF),
                (0x00800000, 0x807FFFFF),
                (0x00000001, 0x00000002),
                (0x00000001, 0x7F7FFFFF),
                (0x7F800000, 0x00000000),
                (0x7F800000, 0xFF800000),
                (0x00000000, 0x00000000),
                (0x80000000, 0x40000000),
                (0x80000000, 0xC0000000),
                (0x7FC12345, 0x3F800000),
                (0xBF800000, 0x00000000),
                (0x3F800000, 0x80000000),
                (0xFF800000, 0x40000000),
                (0x3F800000, 0x7F800000),
                (0x3F800000, 0x33800000),
                (0x3F800001, 0x33800000),
                (float32_bits(-32768.5), 0x3F800000),
                (float32_bits(32767.75), 0x3F800000),
                (float32_bits(0.25), 0x3F800000),
                (float32_bits(-0.25), 0x3F800000),
                (float32_bits(0.5), 0x3F800000),
                (float32_bits(-0.5), 0x3F800000),
                (float32_bits(1.5), 0x3F800000),
                (float32_bits(-1.5), 0x3F800000),
                (float32_bits(2.5), 0x3F800000),
                (float32_bits(-2.5), 0x3F800000),
                (float32_bits(8388607.5), 0x3F800000),
                (float32_bits(8388609.0), 0x3F800000),
            ]
            random_source = random.Random(0x754)
            while len(vectors) < 116:
                left = random_source.getrandbits(32)
                right = random_source.getrandbits(32)
                if (left & 0x7F800000) != 0x7F800000 and (
                    right & 0x7F800000
                ) != 0x7F800000:
                    vectors.append((left, right))

            def reference_divide(
                left_bits: int,
                right_bits: int,
                left: float,
                right: float,
            ) -> int:
                if (
                    binary32_is_nan(left_bits)
                    or binary32_is_nan(right_bits)
                    or (math.isinf(left) and math.isinf(right))
                    or (left == 0.0 and right == 0.0)
                ):
                    return 0x7FC00000
                sign = (left_bits ^ right_bits) & 0x80000000
                if right == 0.0:
                    return sign | 0x7F800000
                if math.isinf(left):
                    return sign | 0x7F800000
                if math.isinf(right):
                    return sign
                return float32_bits(left / right)

            def reference_truncate(value_bits: int) -> int:
                exponent = (value_bits >> 23) & 0xFF
                if exponent >= 150:
                    return value_bits
                if exponent < 127:
                    return value_bits & 0x80000000
                return value_bits & ~((1 << (150 - exponent)) - 1)

            def reference_multiply(left_bits: int, right_bits: int) -> int:
                if binary32_is_nan(left_bits) or binary32_is_nan(right_bits):
                    return 0x7FC00000
                sign = (left_bits ^ right_bits) & 0x80000000
                left_zero = left_bits & 0x7FFFFFFF == 0
                right_zero = right_bits & 0x7FFFFFFF == 0
                left_infinite = left_bits & 0x7FFFFFFF == 0x7F800000
                right_infinite = right_bits & 0x7FFFFFFF == 0x7F800000
                if (left_infinite and right_zero) or (
                    right_infinite and left_zero
                ):
                    return 0x7FC00000
                if left_infinite or right_infinite:
                    return sign | 0x7F800000
                if left_zero or right_zero:
                    return sign
                return float32_bits(
                    float32_from_bits(left_bits) * float32_from_bits(right_bits)
                )

            def reference_subtract(left_bits: int, right_bits: int) -> int:
                effective_right = right_bits ^ 0x80000000
                if binary32_is_nan(left_bits) or binary32_is_nan(effective_right):
                    return 0x7FC00000
                left_infinite = left_bits & 0x7FFFFFFF == 0x7F800000
                right_infinite = effective_right & 0x7FFFFFFF == 0x7F800000
                if left_infinite:
                    if right_infinite and (left_bits ^ effective_right) & 0x80000000:
                        return 0x7FC00000
                    return left_bits & 0xFF800000
                if right_infinite:
                    return effective_right & 0xFF800000
                return float32_bits(
                    float32_from_bits(left_bits) - float32_from_bits(right_bits)
                )

            def reference_mod(left_bits: int, right_bits: int) -> int:
                if binary32_is_nan(left_bits) or binary32_is_nan(right_bits):
                    return 0x7FC00000
                if right_bits & 0x7FFFFFFF == 0:
                    return 0x7FC00000
                if left_bits & 0x7FFFFFFF == 0x7F800000:
                    return 0x7FC00000
                if right_bits & 0x7FFFFFFF == 0x7F800000:
                    return left_bits
                quotient = reference_divide(
                    left_bits,
                    right_bits,
                    float32_from_bits(left_bits),
                    float32_from_bits(right_bits),
                )
                truncated = reference_truncate(quotient)
                product = reference_multiply(truncated, right_bits)
                return reference_subtract(left_bits, product)

            def reference_hypot(left_bits: int, right_bits: int) -> int:
                left_abs = left_bits & 0x7FFFFFFF
                right_abs = right_bits & 0x7FFFFFFF
                if binary32_is_nan(left_abs):
                    largest = smallest = right_abs
                elif binary32_is_nan(right_abs):
                    largest = smallest = left_abs
                else:
                    largest = max(left_abs, right_abs)
                    smallest = min(left_abs, right_abs)
                if largest in (0, 0x7F800000):
                    return largest
                ratio = reference_divide(
                    smallest,
                    largest,
                    float32_from_bits(smallest),
                    float32_from_bits(largest),
                )
                square = reference_multiply(ratio, ratio)
                total = float32_bits(1.0 + float32_from_bits(square))
                root = float32_bits(math.sqrt(float32_from_bits(total)))
                return reference_multiply(largest, root)

            def same_binary32(actual: int, expected: int) -> bool:
                return actual == expected or (
                    binary32_is_nan(actual) and binary32_is_nan(expected)
                )

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                for index, (left_bits, right_bits) in enumerate(vectors):
                    with self.subTest(
                        index=index,
                        left=f"{left_bits:08X}",
                        right=f"{right_bits:08X}",
                    ):
                        left = float32_from_bits(left_bits)
                        right = float32_from_bits(right_bits)
                        card_input = (index * 997) & 0xFFFF
                        int_input = ((index * 613) & 0xFFFF) - 32768
                        memory = bytearray(0x51)
                        struct.pack_into("<II", memory, 0, left_bits, right_bits)
                        struct.pack_into("<Hh", memory, 0x30, card_input, int_input)
                        vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                        vice_context.monitor.memory_set(0xC000, memory)
                        vice_context.monitor.resume()
                        deadline = time.monotonic() + 3.0
                        while time.monotonic() < deadline:
                            if vice_context.monitor.memory_get(0xC034, 0xC034)[0] == 1:
                                break
                            time.sleep(0.002)
                        self.assertEqual(
                            vice_context.monitor.memory_get(0xC034, 0xC034)[0],
                            1,
                            "generated IEEE runtime probe did not finish",
                        )
                        output = vice_context.monitor.memory_get(0xC008, 0xC050)
                        actual_reals = [
                            struct.unpack_from("<I", output, offset)[0]
                            for offset in range(0, 32, 4)
                        ]
                        expected_reals = [
                            float32_bits(left + right),
                            float32_bits(left - right),
                            float32_bits(left * right),
                            reference_divide(left_bits, right_bits, left, right),
                            0x7FC00000
                            if binary32_is_nan(left_bits)
                            or ((left_bits & 0x80000000) and left_bits != 0x80000000)
                            else float32_bits(math.sqrt(left)),
                            left_bits & 0x7FFFFFFF,
                            float32_bits(float(card_input)),
                            float32_bits(float(int_input)),
                        ]
                        for operation, actual, expected in zip(
                            ("add", "sub", "mul", "div", "sqrt", "abs", "card", "int"),
                            actual_reals,
                            expected_reals,
                        ):
                            self.assertTrue(
                                same_binary32(actual, expected),
                                f"{operation}: got {actual:08X}, expected {expected:08X}",
                            )
                        if math.isfinite(left):
                            truncated = math.trunc(left)
                            expected_integer = (
                                truncated if -32768 <= truncated <= 32767 else 0
                            )
                        else:
                            expected_integer = 0
                        self.assertEqual(
                            struct.unpack_from("<h", output, 0x20)[0],
                            expected_integer,
                        )
                        self.assertEqual(
                            list(output[0x22:0x28]),
                            [
                                int(left == right),
                                int(left != right),
                                int(left < right),
                                int(left <= right),
                                int(left > right),
                                int(left >= right),
                            ],
                        )
                        exponent = (left_bits >> 23) & 0xFF
                        expected_trunc = reference_truncate(left_bits)
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x2D)[0],
                            expected_trunc,
                        )
                        expected_floor = expected_trunc
                        if (
                            (left_bits & 0x80000000)
                            and not binary32_is_nan(left_bits)
                            and not math.isinf(left)
                            and expected_trunc != left_bits
                        ):
                            expected_floor = float32_bits(float(math.floor(left)))
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x31)[0],
                            expected_floor,
                        )
                        expected_ceil = expected_trunc
                        if (
                            not (left_bits & 0x80000000)
                            and not binary32_is_nan(left_bits)
                            and not math.isinf(left)
                            and expected_trunc != left_bits
                        ):
                            expected_ceil = float32_bits(float(math.ceil(left)))
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x35)[0],
                            expected_ceil,
                        )
                        if binary32_is_nan(left_bits) or math.isinf(left):
                            expected_round = left_bits
                        elif expected_trunc == left_bits:
                            expected_round = left_bits
                        elif abs(left) < 0.5:
                            expected_round = left_bits & 0x80000000
                        else:
                            magnitude = math.floor(abs(left) + 0.5)
                            expected_round = float32_bits(
                                -float(magnitude)
                                if left_bits & 0x80000000
                                else float(magnitude)
                            )
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x39)[0],
                            expected_round,
                        )
                        expected_frac = (
                            0x7FC00000
                            if binary32_is_nan(left_bits) or math.isinf(left)
                            else float32_bits(
                                left - float32_from_bits(expected_trunc)
                            )
                        )
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x3D)[0],
                            expected_frac,
                        )
                        self.assertEqual(
                            struct.unpack_from("<I", output, 0x41)[0],
                            reference_mod(left_bits, right_bits),
                        )
                        self.assertTrue(
                            same_binary32(
                                struct.unpack_from("<I", output, 0x45)[0],
                                reference_hypot(left_bits, right_bits),
                            )
                        )
            finally:
                vice_context.stop()

    def test_ieee_binary32_prints_exact_full_domain_values(self) -> None:
        values = (
            0x00000000,
            0x80000000,
            0x00000001,
            0x007FFFFF,
            0x00800000,
            0x3DCCCCCD,
            0x3FC00000,
            0x7F7FFFFF,
            0xFF7FFFFF,
            0x7F800000,
            0xFF800000,
            0x7FC12345,
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            shutil.copy2(
                ROOT / "src" / "runtime" / "modules" / "rt_print_f.obj",
                shared_lib / "RT_PRINT_F.OBJ",
            )
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            declarations = "".join(
                f"REAL value{index}=${0xC000 + index * 4:04X}\n"
                for index in range(len(values))
            )
            output = "".join(
                f"PrintR(value{index})\nPrintE(\"|\")\n"
                for index in range(len(values))
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                declarations
                + "BYTE done=$C080\n"
                + "PROC MAIN()\n"
                + output
                + "done=1\nDO\nOD\nENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
                vice_context.wait_for_screen_contains("ready.", timeout=12.0)
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                raw_values = b"".join(struct.pack("<I", value) for value in values)
                vice_context.monitor.memory_set(0xC000, raw_values)
                vice_context.monitor.memory_set(0xC080, b"\x00")
                vice_context.monitor.resume()
                # Exact expansion of several 128-151 digit subnormals is the
                # deliberate worst case for the 6502 big-integer formatter.
                # A Pi Zero 2W running VICE can need substantially longer than
                # an x86 host even though the target code is making progress.
                deadline = time.monotonic() + 60.0
                while time.monotonic() < deadline:
                    if vice_context.monitor.memory_get(0xC080, 0xC080)[0] == 1:
                        break
                    time.sleep(0.01)
                self.assertEqual(
                    vice_context.monitor.memory_get(0xC080, 0xC080)[0],
                    1,
                    "generated exact REAL printer probe did not finish",
                )
                screen = vice_context.read_screen_text()
                rendered = "".join(screen.split("ready.", 1)[-1].split()).upper()
                expected = "".join(
                    exact_binary32_decimal(value) + "|" for value in values
                )
                self.assertEqual(rendered, expected)
            finally:
                vice_context.stop()

    def test_recursive_word_array_and_real_frames_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for name in ("rt_f_add.obj", "rt_s_to_f.obj"):
                shutil.copy2(
                    ROOT / "src" / "runtime" / "modules" / name,
                    shared_lib / name.upper(),
                )

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "CARD FUNC Sum(CARD value)\n"
                "BYTE ARRAY saved(1)\n"
                "saved(0)=value\n"
                "IF value=0 THEN\n"
                "RETURN(0)\n"
                "FI\n"
                "RETURN(saved(0)+Sum(value-1))\n"
                "REAL FUNC Accumulate(CARD count,REAL value)\n"
                "REAL saved\n"
                "saved=value\n"
                "IF count=0 THEN\n"
                "RETURN(saved)\n"
                "FI\n"
                "RETURN(Accumulate(count-1,saved+1.5))\n"
                "CARD FUNC MutualA(CARD value)\n"
                "BYTE saved\n"
                "saved=value\n"
                "IF value=0 THEN\n"
                "RETURN(0)\n"
                "FI\n"
                "RETURN(saved+MutualB(value-1))\n"
                "CARD FUNC MutualB(CARD value)\n"
                "BYTE saved\n"
                "saved=value\n"
                "IF value=0 THEN\n"
                "RETURN(0)\n"
                "FI\n"
                "RETURN(saved+MutualA(value-1))\n"
                "PROC MAIN()\n"
                "CARD wordresult=$C000\n"
                "CARD mutualresult=$C002\n"
                "REAL realresult=$C010\n"
                "BYTE done=$C020\n"
                "wordresult=Sum(5)\n"
                "mutualresult=MutualA(4)\n"
                "realresult=Accumulate(3,1.0)+Accumulate(2,2.0)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                # Allow the C64 KERNAL and attached IEC device to finish their
                # reset paths before jumping directly into the linked PRG.
                time.sleep(1.0)
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC000, bytes(0x21))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(0x21)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC000, 0xC020)
                    if snapshot[0x20] == 1:
                        break
                self.assertEqual(snapshot[0x20], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(int.from_bytes(snapshot[0:2], "little"), 15)
            self.assertEqual(int.from_bytes(snapshot[2:4], "little"), 10)
            self.assertEqual(struct.unpack("<f", snapshot[0x10:0x14])[0], 10.5)

    def test_action_integer_operator_family_executes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            shutil.copy2(
                ROOT / "src" / "runtime" / "modules" / "rt_i_mod.obj",
                shared_lib / "RT_I_MOD.OBJ",
            )

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n"
                "CARD modresult=$C100\n"
                "CARD andresult=$C102\n"
                "CARD orresult=$C104\n"
                "CARD xorresult=$C106\n"
                "CARD shiftresult=$C108\n"
                "CARD divisor,mask,low,one\n"
                "CHAR charresult=$C10C\n"
                "BYTE shorthand=$C10D\n"
                "BYTE done=$C10F\n"
                "BYTE bytewrap=$C110,byteshift=$C111,positive=$C112,negative=$C113,zerostep=$C114,constwrap=$C115\n"
                "CARD highshift=$C116,mixedresult=$C118,count\n"
                "BYTE left,right,i\n"
                "INT step,signedone\n"
                "divisor=5\n"
                "mask=$0FF0\n"
                "low=$00AA\n"
                "one=1\n"
                "modresult=13 MOD divisor\n"
                "andresult=$55AA & mask\n"
                "orresult=$5500 % low\n"
                "xorresult=$55AA XOR mask\n"
                "shiftresult=(1 LSH divisor) RSH one\n"
                "shorthand=1\n"
                "shorthand==+2\n"
                "shorthand==LSH 1\n"
                "shorthand==& $0F\n"
                "charresult='Z\n"
                "left=200\n"
                "right=100\n"
                "bytewrap=left+right\n"
                "byteshift=left LSH one\n"
                "count=256\n"
                "highshift=one LSH count\n"
                "positive=0\n"
                "step=2\n"
                "FOR i=1 TO 5 STEP step\n"
                "DO\n"
                "positive==+i\n"
                "OD\n"
                "negative=0\n"
                "step=-2\n"
                "FOR i=5 TO 1 STEP step\n"
                "DO\n"
                "negative==+i\n"
                "OD\n"
                "zerostep=7\n"
                "step=0\n"
                "FOR i=1 TO 3 STEP step\n"
                "DO\n"
                "zerostep=0\n"
                "OD\n"
                "constwrap=200+100\n"
                "signedone=-1\n"
                "mixedresult=0\n"
                "IF signedone > one THEN\n"
                "mixedresult=1\n"
                "FI\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC100, bytes(0x10))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(0x1A)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC100, 0xC119)
                    if snapshot[0x0F] == 1:
                        break
                self.assertEqual(
                    snapshot[0x0F],
                    1,
                    f"generated PRG did not reach completion: {snapshot.hex()}",
                )
            finally:
                vice_context.stop()

            self.assertEqual(int.from_bytes(snapshot[0x00:0x02], "little"), 3)
            self.assertEqual(int.from_bytes(snapshot[0x02:0x04], "little"), 0x05A0)
            self.assertEqual(int.from_bytes(snapshot[0x04:0x06], "little"), 0x55AA)
            self.assertEqual(int.from_bytes(snapshot[0x06:0x08], "little"), 0x5A5A)
            self.assertEqual(int.from_bytes(snapshot[0x08:0x0A], "little"), 16)
            self.assertEqual(snapshot[0x0C], ord("Z"))
            self.assertEqual(snapshot[0x0D], 6)
            self.assertEqual(snapshot[0x10], 44)
            self.assertEqual(snapshot[0x11], 144)
            self.assertEqual(snapshot[0x12], 9)
            self.assertEqual(snapshot[0x13], 9)
            self.assertEqual(snapshot[0x14], 7)
            self.assertEqual(snapshot[0x15], 44)
            self.assertEqual(int.from_bytes(snapshot[0x16:0x18], "little"), 0)
            self.assertEqual(int.from_bytes(snapshot[0x18:0x1A], "little"), 1)

    def test_logical_conditions_short_circuit_and_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE probe=$C120\n"
                "BYTE result=$C121\n"
                "BYTE done=$C122\n"
                "BYTE FUNC Touch(BYTE value)\n"
                "probe==+1\n"
                "RETURN(value)\n"
                "PROC MAIN()\n"
                "BYTE a\n"
                "probe=0\n"
                "result=0\n"
                "a=1\n"
                "IF a=1 OR Touch(0)=1 THEN\n"
                "result==+1\n"
                "FI\n"
                "IF a=0 AND Touch(1)=1 THEN\n"
                "result==+2\n"
                "FI\n"
                "IF (a=0 OR a=1) AND (a=1 OR Touch(0)=1) THEN\n"
                "result==+4\n"
                "FI\n"
                "IF a=0 OR a=1 AND a=1 THEN\n"
                "result==+8\n"
                "FI\n"
                "IF 0 OR 1 AND 1 THEN\n"
                "result==+16\n"
                "FI\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC120, bytes(3))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(3)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC120, 0xC122)
                    if snapshot[2] == 1:
                        break
                self.assertEqual(snapshot[2], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 0, "short-circuited function was called")
            self.assertEqual(snapshot[1], 29)

    def test_typed_constants_and_multiline_declarations_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "CARD CONST OUTPUT_ADDR=$C130,\n"
                " VALUE=7\n"
                "CARD CONST SHIFTED=VALUE LSH 4\n"
                "INT CONST NEG=-2\n"
                "REAL CONST SCALE=1.5\n"
                "PROC MAIN()\n"
                "BYTE first,\n"
                " second,\n"
                " output=OUTPUT_ADDR,\n"
                " done=$C138\n"
                "CARD word=$C132\n"
                "REAL realout=$C134\n"
                "first=VALUE\n"
                "second=VALUE+1\n"
                "output=first+second\n"
                "word=SHIFTED+NEG\n"
                "realout=SCALE+0.5\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC130, bytes(9))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(9)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC130, 0xC138)
                    if snapshot[8] == 1:
                        break
                self.assertEqual(snapshot[8], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 15)
            self.assertEqual(int.from_bytes(snapshot[2:4], "little"), 110)
            self.assertEqual(struct.unpack("<f", snapshot[4:8])[0], 2.0)

    def test_define_and_nested_include_output_executes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            (shared_lib / "BASE.ACT").write_text(
                "MODULE\nCARD CONST TARGET=$C140\n",
                encoding="ascii",
            )
            (shared_lib / "WRAP.ACT").write_text(
                'INCLUDE "base.act"\nDEFINE U8="BYTE",\n DOUBLE="LSH ONE", ONE=1\n',
                encoding="ascii",
            )
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "wrap.act"\n'
                "PROC MAIN()\n"
                "U8 seed,result=TARGET,done=$C141\n"
                "seed=3\n"
                "result=seed DOUBLE\n"
                "IF ONE THEN\n"
                "result==+1\n"
                "FI\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC140, bytes(2))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(2)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC140, 0xC141)
                    if snapshot[1] == 1:
                        break
                self.assertEqual(snapshot[1], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 7)

    def test_record_storage_addresses_and_pointer_fields_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "TYPE Pair=[BYTE tag\n"
                " CARD value\n"
                " INT delta]\n"
                "Pair direct=$C150\n"
                "PROC Adjust(BYTE amount, Pair POINTER item)\n"
                "item.tag==+amount\n"
                "item.value==+amount\n"
                "RETURN\n"
                "PROC Mark(Pair item)\n"
                "item.tag==+1\n"
                "RETURN\n"
                "PROC MAIN()\n"
                "Pair stored\n"
                "Pair POINTER ptr\n"
                "BYTE done=$C160\n"
                "direct.tag=7\n"
                "direct.value=$1234\n"
                "direct.delta=-2\n"
                "stored.tag=direct.tag+1\n"
                "stored.value=direct.value+1\n"
                "stored.delta=direct.delta-1\n"
                "ptr=@stored\n"
                "ptr.tag==+1\n"
                "ptr.value==+2\n"
                "ptr.delta==+1\n"
                "direct.tag=ptr.tag\n"
                "direct.value=ptr.value\n"
                "direct.delta=ptr.delta\n"
                "Adjust(2,direct)\n"
                "Mark(direct)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC150, bytes(0x11))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(0x11)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC150, 0xC160)
                    if snapshot[0x10] == 1:
                        break
                self.assertEqual(snapshot[0x10], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 12)
            self.assertEqual(int.from_bytes(snapshot[1:3], "little"), 0x1239)
            self.assertEqual(int.from_bytes(snapshot[3:5], "little", signed=True), -2)

    def test_relocatable_declaration_compiler_constants_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "TYPE Pair=[BYTE tag CARD value]\n"
                "BYTE ARRAY storage(2)\n"
                "BYTE first=storage\n"
                "BYTE second=storage+1\n"
                "BYTE POINTER ptr=storage+1\n"
                "BYTE ARRAY tail=storage+1\n"
                "Pair original\n"
                "Pair mirror=original\n"
                "CARD ARRAY table(0)=[storage storage+1 original]\n"
                "PROC MAIN()\n"
                "BYTE POINTER selected\n"
                "BYTE prior\n"
                "BYTE outfirst=$C170,outsecond=$C171,outptr=$C172,outtable=$C173\n"
                "BYTE outtag=$C174\n"
                "CARD outvalue=$C175\n"
                "BYTE done=$C177\n"
                "first=11\n"
                "second=22\n"
                "prior=ptr^\n"
                "tail(0)=33\n"
                "original.tag=44\n"
                "mirror.value=$5678\n"
                "selected=table(0)\n"
                "outfirst=first\n"
                "outsecond=second\n"
                "outptr=prior\n"
                "outtable=selected^\n"
                "outtag=mirror.tag\n"
                "outvalue=original.value\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC170, bytes(8))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(8)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC170, 0xC177)
                    if snapshot[7] == 1:
                        break
                self.assertEqual(snapshot[7], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0:5], bytes((11, 33, 22, 11, 44)))
            self.assertEqual(int.from_bytes(snapshot[5:7], "little"), 0x5678)

    def test_code_blocks_and_fixed_address_routines_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE FUNC Seven=*()\n"
                "[$A9 7 $60]\n"
                "CARD FUNC Pair=*(BYTE low,high)\n"
                "[$60]\n"
                "BYTE FUNC Fourth=*(BYTE a,b,c,d)\n"
                "[$A3AD 0 $60]\n"
                "PROC KernalOut=$FFD2(BYTE value)\n"
                "PROC MAIN()\n"
                "CARD word\n"
                "BYTE fourthvalue\n"
                "CARD result=$C200\n"
                "BYTE done=$C202\n"
                "CARD packed=$C203\n"
                "BYTE fourthout=$C205\n"
                "[$A9 $34 $8D word $A9 $12 $8D word+1]\n"
                "result=word+Seven()\n"
                "packed=Pair($34,$12)\n"
                "fourthvalue=Fourth(1,2,3,77)\n"
                "KernalOut('A)\n"
                "fourthout=fourthvalue\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
                # KernalOut below calls $FFD2, which is only a valid execution
                # target after the emulated KERNAL has completed startup.
                vice_context.wait_for_screen_contains("ready.", timeout=12.0)
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC200, bytes(6))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(6)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC200, 0xC205)
                    if snapshot[2] == 1:
                        break
                self.assertEqual(snapshot[2], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(int.from_bytes(snapshot[0:2], "little"), 0x123B)
            self.assertEqual(int.from_bytes(snapshot[3:5], "little"), 0x1234)
            self.assertEqual(snapshot[5], 77, snapshot.hex())

    def test_idun_main_arguments_and_asmblock_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE argcLow=$C240,argcHigh=$C241\n"
                "BYTE firstChar=$C242,secondChar=$C243\n"
                "CARD workerResult=$C244\n"
                "BYTE registerResult=$C246,done=$C247\n"
                "PROC Worker(CARD addend)\n"
                "    CARD localValue\n"
                "    ASMBLOCK [\n"
                "        lda addend\n"
                "        clc\n"
                "        adc #1\n"
                "        sta localValue\n"
                "        lda addend+1\n"
                "        adc #0\n"
                "        sta localValue+1\n"
                "        ldx #3\n"
                "    delay:\n"
                "        dex\n"
                "        bne delay\n"
                "        lda localValue\n"
                "        sta workerResult\n"
                "        lda localValue+1\n"
                "        sta workerResult+1\n"
                "    ]\n"
                "    RETURN\n"
                "ENDPROC\n"
                "BYTE FUNC RegisterPlusOne=*(BYTE value)\n"
                "    ASMBLOCK [\n"
                "        clc\n"
                "        adc #1\n"
                "        rts\n"
                "    ]\n"
                "ENDFUNC\n"
                "PROC MAIN(CARD argc,CARD ARRAY argv)\n"
                "    BYTE POINTER firstArgument,secondArgument\n"
                "    argcLow=argc\n"
                "    argcHigh=argc RSH 8\n"
                "    firstArgument=argv(1)\n"
                "    secondArgument=argv(2)\n"
                "    firstChar=firstArgument^\n"
                "    secondChar=secondArgument^\n"
                "    Worker(argc)\n"
                "    registerResult=RegisterPlusOne(40)\n"
                "    done=1\n"
                "    RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC240, bytes(8))
                vice_context.monitor.memory_set(0x0F04, bytes((3, 0, 0x00, 0xC4)))
                vice_context.monitor.memory_set(
                    0xC400,
                    bytes((0x10, 0xC4, 0x18, 0xC4, 0x20, 0xC4, 0x00, 0x00)),
                )
                vice_context.monitor.memory_set(0xC410, b"main\x00")
                vice_context.monitor.memory_set(0xC418, b"alpha\x00")
                vice_context.monitor.memory_set(0xC420, b"beta\x00")
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(8)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC240, 0xC247)
                    if snapshot[7] == 1:
                        break
                self.assertEqual(snapshot[7], 1, "generated PRG did not finish")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0:4], bytes((3, 0, ord("a"), ord("b"))))
            self.assertEqual(int.from_bytes(snapshot[4:6], "little"), 4)
            self.assertEqual(snapshot[6], 41)

    def test_array_addresses_omitted_arguments_and_signed_division_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for name in ("rt_i_div.obj", "rt_i_mod.obj"):
                shutil.copy2(
                    ROOT / "src" / "runtime" / "modules" / name,
                    shared_lib / name.upper(),
                )
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "CARD FUNC Add(CARD a,b)\n"
                "RETURN(a+b)\n"
                "PROC MAIN()\n"
                "BYTE ARRAY values(4)\n"
                "BYTE POINTER ptr\n"
                "INT dividend,divisor\n"
                "INT quotient=$C210\n"
                "INT remainder=$C212\n"
                "BYTE arrayresult=$C214\n"
                "CARD omitted=$C216\n"
                "BYTE done=$C218\n"
                "dividend=-13\n"
                "divisor=5\n"
                "quotient=dividend/divisor\n"
                "remainder=dividend MOD divisor\n"
                "values(1)=42\n"
                "ptr=@values(1)\n"
                "arrayresult=ptr^\n"
                "omitted=Add(2,3)\n"
                "omitted=Add(4)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC210, bytes(9))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(9)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC210, 0xC218)
                    if snapshot[8] == 1:
                        break
                self.assertEqual(snapshot[8], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(int.from_bytes(snapshot[0:2], "little", signed=True), -2)
            self.assertEqual(int.from_bytes(snapshot[2:4], "little", signed=True), -3)
            self.assertEqual(snapshot[4], 42)
            self.assertEqual(int.from_bytes(snapshot[6:8], "little"), 7)

    def test_assignable_routines_and_action_quoted_strings_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'BYTE ARRAY text="A""B"\n'
                'CARD ARRAY messages(2)=["ONE" "T""WO"]\n'
                "BYTE output=$C220\n"
                "PROC First()\n"
                "output=1\n"
                "RETURN\n"
                "PROC Second()\n"
                "output=2\n"
                "RETURN\n"
                "MODULE\n"
                "CARD ARRAY routines(9)=[First Second+0]\n"
                "PROC MAIN()\n"
                "CARD saved\n"
                "BYTE ARRAY selected\n"
                "BYTE redirected=$C221,quote=$C222,length=$C223,done=$C224\n"
                "BYTE tablelength=$C225,tablequote=$C226,tablelast=$C227\n"
                "saved=First\n"
                "First=routines(1)\n"
                "First()\n"
                "redirected=output\n"
                "First=saved\n"
                "First()\n"
                "quote=text(2)\n"
                "length=text(0)\n"
                "selected=messages(1)\n"
                "tablelength=selected(0)\n"
                "tablequote=selected(2)\n"
                "tablelast=selected(4)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC220, bytes(8))
                vice_context.monitor.resume()

                deadline = time.monotonic() + 5.0
                snapshot = bytes(8)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC220, 0xC227)
                    if snapshot[4] == 1:
                        break
                self.assertEqual(snapshot[4], 1, "generated PRG did not reach completion")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 1)
            self.assertEqual(snapshot[1], 2)
            self.assertEqual(snapshot[2], ord('"'))
            self.assertEqual(snapshot[3], 3)
            self.assertEqual(snapshot[5], 4)
            self.assertEqual(snapshot[6], ord('"'))
            self.assertEqual(snapshot[7], ord("O"))

    def test_gfx_sid_and_sprite_libraries_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for pattern in (
                "rt_gfx_*.obj",
                "rt_sid_*.obj",
                "rt_sprite_*.obj",
                "rt_j*.obj",
                "rt_m*.obj",
            ):
                for source in (ROOT / "src" / "runtime" / "modules").glob(pattern):
                    shutil.copy2(source, shared_lib / source.name.upper())
            for name in ("gfx1.act", "input1.act", "sidspr1.act"):
                shutil.copy2(ROOT / "lib" / name, shared_lib / name.upper())

            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "gfx1.act"\n'
                'INCLUDE "input1.act"\n'
                'INCLUDE "sidspr1.act"\n'
                "PROC MAIN()\n"
                "BYTE done=$C300\n"
                "BYTE joyvalue=$C301,joyseen=$C302,joybutton=$C303,mousex=$C304\n"
                "BgColor(6)\n"
                "BorderColor(2)\n"
                "ScreenCell(3,2,'A)\n"
                "ColorCell(3,2,14)\n"
                "SpriteOn(3)\n"
                "SpritePos(3,300,77)\n"
                "SpriteColor(3,5)\n"
                "SetSpriteMC(8,9)\n"
                "SidFreq(1,$1234)\n"
                "SidWave(1,SID_SAW)\n"
                "SidAD(1,$AB)\n"
                "SidSR(1,$CD)\n"
                "SidOn(1)\n"
                "SidVol(9)\n"
                "joyvalue=Joy(1)\n"
                "joyseen=JoySeen(1)\n"
                "joybutton=JoyBtn1(1)\n"
                "mousex=MouseX()\n"
                "done=1\n"
                "DO\n"
                "OD\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC300, bytes(5))
                vice_context.monitor.resume()
                deadline = time.monotonic() + 5.0
                done = 0
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    done = vice_context.monitor.memory_get(0xC300, 0xC300)[0]
                    if done == 1:
                        break
                self.assertEqual(done, 1, "generated hardware-library PRG did not finish")

                io_bank = vice_context.monitor.banks_available()["io"]
                vic = vice_context.monitor.memory_get(
                    0xD000, 0xD02A, bank=io_bank
                )
                screen = vice_context.monitor.memory_get(0x0453, 0x0453)
                color = vice_context.monitor.memory_get(
                    0xD853, 0xD853, bank=io_bank
                )
                sid = vice_context.monitor.memory_get(
                    0xD407, 0xD418, bank=io_bank
                )
                input_state = vice_context.monitor.memory_get(0xC301, 0xC304)
            finally:
                vice_context.stop()

            self.assertEqual(vic[0x20] & 0x0F, 2)
            self.assertEqual(vic[0x21] & 0x0F, 6)
            self.assertEqual(screen[0], ord("A"))
            self.assertEqual(color[0] & 0x0F, 14)
            self.assertEqual(vic[0x15] & 0x08, 0x08)
            self.assertEqual(vic[0x10] & 0x08, 0x08)
            self.assertEqual(vic[0x06], 300 & 0xFF)
            self.assertEqual(vic[0x07], 77)
            self.assertEqual(vic[0x2A] & 0x0F, 5)
            self.assertEqual(vic[0x25] & 0x0F, 8)
            self.assertEqual(vic[0x26] & 0x0F, 9)
            self.assertEqual(sid[0], 0x34)
            self.assertEqual(sid[1], 0x12)
            self.assertEqual(sid[4], 0x21)
            self.assertEqual(sid[5], 0xAB)
            self.assertEqual(sid[6], 0xCD)
            self.assertEqual(sid[0x11] & 0x0F, 9)
            self.assertEqual(input_state, bytes(4))

    def test_reu_library_round_trip_executes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for source in (ROOT / "src" / "runtime" / "modules").glob("rt_reu_*.obj"):
                shutil.copy2(source, shared_lib / source.name.upper())
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "REU BYTE ARRAY far(64)\n"
                "PROC MAIN()\n"
                "BYTE bytevalue=$C310,ok8=$C311,ok16=$C312,done=$C313\n"
                "CARD wordvalue=$C314\n"
                "ReuPoke8(far,5,123)\n"
                "bytevalue=ReuPeek8(far,5)\n"
                "ok8=1\n"
                "ReuPoke16(far,20,$BEEF)\n"
                "wordvalue=ReuPeek16(far,20)\n"
                "ok16=1\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                vice_context = ViceHarness(timeout=5.0)
                vice_context.start()
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC310, bytes(6))
                vice_context.monitor.resume()
                deadline = time.monotonic() + 5.0
                snapshot = bytes(6)
                while time.monotonic() < deadline:
                    time.sleep(0.02)
                    snapshot = vice_context.monitor.memory_get(0xC310, 0xC315)
                    if snapshot[3] == 1:
                        break
                self.assertEqual(snapshot[3], 1, "generated REU PRG did not finish")
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 123)
            self.assertEqual(snapshot[1], 1)
            self.assertEqual(snapshot[2], 1)
            self.assertEqual(int.from_bytes(snapshot[4:6], "little"), 0xBEEF)

    @unittest.skipUnless(shutil.which("c1541"), "c1541 is required for DBF disk verification")
    @unittest.skipIf(
        vice_37_has_unreliable_dbf_monitor_execution(),
        "VICE 3.7 is unreliable for the long REU plus disk monitor case",
    )
    def test_dbf_library_create_append_and_save_executes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            disk_image = workspace / "dbf-test.d64"
            formatted = subprocess.run(
                ["c1541", "-format", "dbftest,00", "d64", str(disk_image)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                formatted.returncode, 0, msg=formatted.stdout + formatted.stderr
            )
            shared_lib = workspace / "LIB"
            shared_lib.mkdir()
            for pattern in ("rt_dbf_*.obj", "rt_reu_*.obj"):
                for source in (ROOT / "src" / "runtime" / "modules").glob(pattern):
                    shutil.copy2(source, shared_lib / source.name.upper())
            shutil.copy2(ROOT / "lib" / "dbf1.act", shared_lib / "DBF1.ACT")
            create = subprocess.run(
                [str(self.tool_dir / "actnew"), "demo"],
                cwd=workspace,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(create.returncode, 0, msg=create.stdout + create.stderr)
            project = workspace / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "dbf1.act"\n'
                "BYTE ARRAY filename=[84 69 83 84 68 66 70 0]\n"
                "PROC MAIN()\n"
                "BYTE handle=$C320,headerlen=$C321,recordlen=$C322\n"
                "BYTE appendok=$C323,total=$C324,current=$C325,gook=$C326\n"
                "BYTE deleteok=$C327,deleted=$C328,undeleteok=$C329\n"
                "BYTE restored=$C32A,saveok=$C32B,done=$C32C\n"
                "BYTE resaveok=$C32D\n"
                "done=10\n"
                "handle=DbfCreate(filename)\n"
                "done=11\n"
                "headerlen=DbfHeaderLen(handle)\n"
                "recordlen=DbfRecordLen(handle)\n"
                "appendok=DbfAppend(handle)\n"
                "total=DbfTotalRecs(handle)\n"
                "current=DbfCurrRecNo(handle)\n"
                "gook=DbfGo(handle,1)\n"
                "deleteok=DbfDelete(handle)\n"
                "deleted=DbfDeleted(handle)\n"
                "undeleteok=DbfUndelete(handle)\n"
                "restored=DbfDeleted(handle)\n"
                "saveok=DbfSave(handle)\n"
                "resaveok=DbfSave(handle)\n"
                "done=1\n"
                "DO\n"
                "OD\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            try:
                # The test validates the generated KERNAL calls and resulting
                # D64 bytes.  Virtual IEC avoids coupling that contract to
                # cycle-exact 1541 reset timing.  VICE 3.7 also needs a brief
                # gap after the preceding emulator exits before a disk-backed
                # instance can safely take over its IEC worker state.
                time.sleep(1.0)
                vice_context = ViceHarness(
                    disk_image=disk_image,
                    true_drive=False,
                    timeout=8.0,
                )
                vice_context.start()
                vice_context.wait_for_screen_contains("ready.", timeout=12.0)
            except ViceUnavailable as exc:
                self.skipTest(str(exc))
            try:
                vice_context.load_prg(project / "BIN" / "MAIN.PRG")
                vice_context.monitor.memory_set(0xC320, bytes(14))
                vice_context.monitor.resume()
                # Let both serialized disk writes complete before the first
                # monitor stop so the disk-image assertion is stable.
                time.sleep(1.0)
                deadline = time.monotonic() + 10.0
                snapshot = bytes(14)
                while time.monotonic() < deadline:
                    time.sleep(0.25)
                    try:
                        snapshot = vice_context.monitor.memory_get(0xC320, 0xC32D)
                    except ViceProtocolError as exc:
                        process = vice_context.process
                        if process is None or process.poll() is None:
                            raise
                        stdout, stderr = process.communicate(timeout=1)
                        vice_context.process = None
                        self.fail(
                            f"{exc}; x64sc exited with {process.returncode}\n"
                            f"stdout:\n{stdout}\nstderr:\n{stderr}"
                        )
                    if snapshot[12] == 1:
                        break
                registers = ""
                if snapshot[12] != 1:
                    register_ids = vice_context.monitor.register_ids()
                    register_values = vice_context.monitor.registers_get()
                    registers = " ".join(
                        f"{name}=${register_values.get(register_id, 0):04X}"
                        for name, register_id in register_ids.items()
                        if name in {"A", "X", "Y", "SP", "PC"}
                    )
                self.assertEqual(
                    snapshot[12],
                    1,
                    f"generated DBF PRG did not finish: {snapshot.hex()} {registers}",
                )
            finally:
                vice_context.stop()

            self.assertEqual(snapshot[0], 1)
            self.assertEqual(snapshot[1], 33)
            self.assertEqual(snapshot[2], 1)
            self.assertEqual(snapshot[3:10], bytes([1, 1, 1, 1, 1, 1, 1]))
            self.assertEqual(snapshot[10], 0)
            self.assertEqual(snapshot[11], 1)
            self.assertEqual(snapshot[13], 1)

            listing = subprocess.run(
                ["c1541", "-attach", str(disk_image), "-dir"],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(listing.returncode, 0, msg=listing.stdout + listing.stderr)
            self.assertIn('"testdbf"', listing.stdout.lower())

            extracted = workspace / "testdbf.bin"
            read_back = subprocess.run(
                ["c1541", str(disk_image), "-read", "testdbf,s", str(extracted)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                read_back.returncode, 0, msg=read_back.stdout + read_back.stderr
            )
            self.assertEqual(
                extracted.read_bytes(),
                bytes(
                    [3, 0, 0, 0, 1, 0, 0, 0, 33, 0, 1, 0]
                    + [0] * 20
                    + [0x0D, 0x20]
                ),
            )


if __name__ == "__main__":
    unittest.main()
