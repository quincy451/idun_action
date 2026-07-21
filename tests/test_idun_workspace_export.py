from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


class TestIdunWorkspaceExport(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def test_export_contains_linux_tools_without_udos_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "idun-action"
            result = subprocess.run(
                [
                    "python3",
                    str(self.root / "tools" / "export_idun_workspace.py"),
                    "--output",
                    str(out),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertTrue((out / "TOOLS" / "actnew").is_file())
            self.assertTrue((out / "TOOLS" / "actchk").is_file())
            self.assertTrue((out / "TOOLS" / "actcopy").is_file())
            self.assertTrue((out / "TOOLS" / "actmove").is_file())
            self.assertTrue((out / "TOOLS" / "actmon").is_file())
            self.assertTrue((out / "TOOLS" / "actdbg").is_file())
            self.assertTrue((out / "TOOLS" / "actprof").is_file())
            self.assertTrue((out / "TOOLS" / "actsvc").is_file())
            self.assertEqual(
                (out / "TOOLS" / "actsvc").read_bytes()[:8],
                bytes.fromhex("4c086dcb06104000"),
            )
            self.assertTrue((out / "TOOLS" / "xcopy").is_file())
            self.assertTrue((out / "TOOLS" / "deltree").is_file())
            self.assertTrue((out / "TOOLS" / "actspc").is_file())
            self.assertTrue((out / "TOOLS" / "actsprite").is_file())
            self.assertTrue((out / "TOOLS" / "actbitmap").is_file())
            self.assertTrue((out / "TOOLS" / "actedit").is_file())
            self.assertTrue((out / "TOOLS" / "acthelp").is_file())
            self.assertTrue((out / "TOOLS" / "actc").is_file())
            self.assertTrue((out / "TOOLS" / "alink").is_file())
            self.assertTrue((out / "SRC").is_dir())
            self.assertTrue((out / "PLAYGROUND").is_dir())
            self.assertTrue((out / "OBJ").is_dir())
            self.assertTrue((out / "BIN").is_dir())
            self.assertTrue((out / "LIB").is_dir())
            manifest = (out / "ACTION.PROJ").read_text(encoding="ascii")
            self.assertTrue(manifest.startswith("ACTION PROJECT\n"))
            self.assertIn("HELLO.ACT\n", manifest)
            self.assertTrue((out / "PLAYGROUND" / "HELLO.ACT").is_file())
            self.assertTrue((out / "PLAYGROUND" / "MATH1_DEMO.ACT").is_file())
            self.assertTrue((out / "PLAYGROUND" / "GFX_RESOURCE_DEMO.ACT").is_file())
            self.assertTrue((out / "PLAYGROUND" / "PLAYER.SPR").is_file())
            self.assertTrue((out / "PLAYGROUND" / "MARKER.ABM").is_file())
            self.assertTrue((out / "PLAYGROUND" / "PRIME_REAL.ACT").is_file())
            self.assertTrue((out / "PLAYGROUND" / "REU_DBF_SORT.ACT").is_file())
            self.assertTrue((out / "PLAYGROUND" / "ASMBLOCK_DEMO.ACT").is_file())
            self.assertTrue((out / "install-user.sh").is_file())
            self.assertNotEqual((out / "install-user.sh").stat().st_mode & 0o111, 0)
            install_bin = Path(tmp) / "installed-bin"
            installed = subprocess.run(
                [str(out / "install-user.sh"), "--bin-dir", str(install_bin)],
                cwd=out,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                installed.returncode,
                0,
                msg=installed.stdout + installed.stderr,
            )
            self.assertTrue((install_bin / "actc").is_symlink())
            self.assertTrue((install_bin / "actspc").is_symlink())
            self.assertTrue((install_bin / "actsprite").is_symlink())
            self.assertTrue((install_bin / "actbitmap").is_symlink())
            self.assertEqual(
                (install_bin / "actc").resolve(),
                (out / "TOOLS" / "actc").resolve(),
            )
            self.assertTrue((out / "LIB" / "RT_PRINT_I.OBJ").is_file())
            self.assertTrue((out / "LIB" / "RT_I_MUL.OBJ").is_file())
            self.assertTrue((out / "LIB" / "RT_I_DIV.OBJ").is_file())
            self.assertTrue((out / "LIB" / "RT_I_MOD.OBJ").is_file())
            self.assertTrue((out / "LIB" / "RT_GFX_SCREEN_CELL.OBJ").is_file())
            self.assertTrue((out / "LIB" / "RT_GFX_COLOR_CELL.OBJ").is_file())
            for name in (
                "RT_GFX_VIC_BANK.OBJ",
                "RT_GFX_BGCOLOR.OBJ",
                "RT_GFX_BORDERCOLOR.OBJ",
                "RT_GFX_SCREEN_BASE.OBJ",
                "RT_GFX_BITMAP_BASE.OBJ",
                "RT_GFX_SCREEN_COPY.OBJ",
                "RT_GFX_COLOR_COPY.OBJ",
                "RT_GFX_BITMAP_FILL.OBJ",
                "RT_GFX_BITMAP_COPY.OBJ",
                "RT_GFX_BITMAP_ON.OBJ",
                "RT_GFX_BITMAP_OFF.OBJ",
                "RT_GFX_MBITMAP_ON.OBJ",
                "RT_GFX_MBITMAP_OFF.OBJ",
            ):
                self.assertTrue((out / "LIB" / name).is_file())
            for pattern in ("rt_sid_*.obj", "rt_sprite_*.obj"):
                for source in (self.root / "src" / "runtime" / "modules").glob(pattern):
                    self.assertTrue((out / "LIB" / source.name.upper()).is_file())
            for name in (
                "RT_JOY.OBJ",
                "RT_JS.OBJ",
                "RT_JP.OBJ",
                "RT_JB1.OBJ",
                "RT_JB2.OBJ",
                "RT_MS.OBJ",
                "RT_MP.OBJ",
                "RT_MSEEN.OBJ",
                "RT_MX.OBJ",
                "RT_MY.OBJ",
                "RT_MB.OBJ",
                "RT_MB1.OBJ",
                "RT_MB2.OBJ",
            ):
                self.assertTrue((out / "LIB" / name).is_file())
            for name in (
                "RT_OVL_LOAD.OBJ",
                "RT_PRINT_LINE.OBJ",
                "RT_PRINT_STR.OBJ",
                "RT_REU_COPY.OBJ",
                "RT_REU_FREE.OBJ",
                "RT_REU_PEEK32.OBJ",
                "RT_REU_POKE32.OBJ",
            ):
                self.assertFalse((out / "LIB" / name).exists())
            for name in (
                "RT_REU_ALLOC.OBJ",
                "RT_REU_STATE.OBJ",
                "RT_REU_RESOLVE.OBJ",
                "RT_REU_TRANSFER.OBJ",
                "RT_REU_PEEK8.OBJ",
                "RT_REU_PEEK16.OBJ",
                "RT_REU_POKE8.OBJ",
                "RT_REU_POKE16.OBJ",
            ):
                self.assertTrue((out / "LIB" / name).is_file())
            for name in (
                "RT_F_ABS.OBJ",
                "RT_F_ADD.OBJ",
                "RT_F_CMP.OBJ",
                "RT_F_CLAMP.OBJ",
                "RT_F_DIV.OBJ",
                "RT_F_FLOOR.OBJ",
                "RT_F_CEIL.OBJ",
                "RT_F_ROUND.OBJ",
                "RT_F_FRAC.OBJ",
                "RT_F_MAX.OBJ",
                "RT_F_MIN.OBJ",
                "RT_F_MUL.OBJ",
                "RT_F_SIGN.OBJ",
                "RT_F_SQRT.OBJ",
                "RT_F_SUB.OBJ",
                "RT_F_TRUNC.OBJ",
                "RT_F_TO_I.OBJ",
                "RT_I_TO_F.OBJ",
                "RT_PRINT_F.OBJ",
                "RT_S_TO_F.OBJ",
            ):
                self.assertTrue((out / "LIB" / name).is_file())
            trunc_object = (out / "LIB" / "RT_F_TRUNC.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("x rt_f_trunc 0 107", trunc_object)
            self.assertIn("b M", trunc_object)
            self.assertIn("n rt_f_trunc", trunc_object)
            floor_object = (out / "LIB" / "RT_F_FLOOR.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("x rt_f_floor 0 135", floor_object)
            self.assertIn("u rt_f_trunc", floor_object)
            self.assertIn("n rt_f_floor", floor_object)
            ceil_object = (out / "LIB" / "RT_F_CEIL.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("x rt_f_ceil 0 42", ceil_object)
            self.assertIn("u rt_f_floor", ceil_object)
            self.assertIn("n rt_f_ceil", ceil_object)
            round_object = (out / "LIB" / "RT_F_ROUND.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("x rt_f_round 0 152", round_object)
            self.assertIn("u rt_f_trunc", round_object)
            self.assertIn("n rt_f_round", round_object)
            frac_object = (out / "LIB" / "RT_F_FRAC.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("x rt_f_frac 0 93", frac_object)
            self.assertIn("u rt_f_trunc", frac_object)
            self.assertIn("u rt_f_sub", frac_object)
            self.assertIn("r 43 u0", frac_object)
            self.assertIn("r 76 u1", frac_object)
            self.assertIn("n rt_f_frac", frac_object)
            self.assertFalse(any((out / "LIB").glob("*.MOD")))
            self.assertTrue((out / "LIB" / "DBF1.ACT").is_file())
            self.assertTrue((out / "LIB" / "MATH1.ACT").is_file())
            self.assertTrue((out / "LIB" / "GFX1.ACT").is_file())
            self.assertTrue((out / "RES" / "PLAYER.SPR").is_file())
            self.assertTrue((out / "RES" / "MARKER.ABM").is_file())
            self.assertTrue((out / "DOC" / "NEW_MATH_FUNC.TXT").is_file())
            self.assertTrue((out / "DOC" / "NEW_GFX_FUNC.TXT").is_file())
            for name in (
                "DBF1_DEMO.ACT",
            ):
                self.assertTrue((out / "SRC" / name).is_file())
            for name in (
                "ASMBLOCK_DEMO.ACT",
                "MATH1_DEMO.ACT",
                "OVL_DEMO.ACT",
                "PRIME_REAL.ACT",
                "REAL_CMP.ACT",
                "REAL_DEMO.ACT",
                "REAL_MATH.ACT",
                "REU_DEMO.ACT",
                "REU_DBF_SORT.ACT",
            ):
                self.assertTrue((out / "SRC" / name).is_file())
            self.assertFalse((out / "UDOSDIR.TXT").exists())
            self.assertFalse((out / "TOOLS" / "ACTNEW.PRG").exists())
            self.assertFalse((out / "TOOLS" / "ACT2SAVE.PRG").exists())
            self.assertFalse((out / "TOOLS" / "ACTCOPY.PRG").exists())
            self.assertFalse((out / "TOOLS" / "ACTDBG.PRG").exists())
            self.assertFalse((out / "TOOLS" / "ACTMON.PRG").exists())
            self.assertFalse((out / "TOOLS" / "XCOPY.OVL").exists())
            help_database = out / "DOC" / "action-help.sqlite3"
            self.assertTrue(help_database.is_file())

            exported_names = {path.name.upper() for path in out.rglob("*")}
            self.assertNotIn("UDOS_SERVICES.INC", exported_names)
            self.assertNotIn("UDOSDIR.TXT", exported_names)
            for name in (
                "RT_DBF_SAVE.OBJ",
                "RT_DBF_ADAPTER_STATE.OBJ",
                "RT_DBF_ENSURE_REU.OBJ",
                "RT_DBF_FILE_LOAD_REU.OBJ",
                "RT_DBF_RAW_REU_READ.OBJ",
                "RT_DBF_RAW_REU_WRITE.OBJ",
                "RT_DBF_FILE_OPEN_WRITE.OBJ",
                "RT_DBF_FILE_WRITE_BYTE.OBJ",
                "RT_DBF_FILE_CLOSE.OBJ",
            ):
                self.assertIn(name, exported_names)

            readme = (out / "DOC" / "README.txt").read_text(encoding="ascii")
            self.assertIn("does not require UDOS", readme)
            self.assertIn("Linux executables", readme)
            self.assertIn("TOOLS/actc hello and TOOLS/alink hello", readme)
            self.assertIn("PLAYGROUND", readme)
            self.assertIn("./install-user.sh", readme)
            operator = (out / "DOC" / "operator.txt").read_text(encoding="ascii")
            self.assertIn("Run TOOLS/actc <module> and TOOLS/alink <module>", operator)
            self.assertIn("Run TOOLS/actspc <file-or-filespec>", operator)
            self.assertIn("Quoted wildcards such as '*.act'", operator)
            self.assertIn("TOOLS/actedit <module> index, find <text>, or symbols", operator)
            self.assertIn("compile, build, and debug modes", operator)
            self.assertIn("provides Ctrl-S save, Ctrl-Q quit, F1", operator)
            self.assertIn("F2 editor-command help", operator)
            self.assertIn("F3 complete language reference", operator)
            self.assertIn("F4 library/feature/example browsing", operator)
            self.assertIn("F5 definitions", operator)
            self.assertIn("F6 ACTSPC formatting", operator)
            self.assertIn("F7 references", operator)
            self.assertIn("F8 graphics-resource editing", operator)
            self.assertIn("GFX_RESOURCE_DEMO.ACT declares external", operator)
            self.assertIn("press F8; arrows move", operator)
            self.assertIn("Ctrl-B marks a block", operator)
            self.assertIn("Ctrl-X, and Ctrl-V copy, cut, and paste", operator)
            self.assertIn("Ctrl-click navigation", operator)
            self.assertIn("flat current-directory workflow", operator)
            self.assertIn("blinking block", operator)
            self.assertIn("Plain actedit uses an uncolored display", operator)
            self.assertIn("tui for syntax highlighting", operator)
            self.assertIn("one through ten START,LENGTH,A|D", operator)
            self.assertIn("ASMBLOCK_DEMO.ACT", operator)
            self.assertIn("MAIN(CARD argc,CARD ARRAY argv)", operator)
            self.assertIn("never launches EDITOR", operator)
            self.assertIn("PRIME_REAL.ACT demonstrates REAL", operator)
            self.assertIn("REU_DBF_SORT.ACT demonstrates stable", operator)
            self.assertIn("TOOLS/acthelp <keyword-or-function>", operator)
            self.assertIn("DOC/action-help.sqlite3 remains outside C64 memory", operator)
            self.assertIn("TOOLS/actmon edit, compile, build, or debug <module>", operator)
            self.assertIn(".action/workspace.sqlite3", operator)
            self.assertIn("TOOLS/actdbg <module> source <address>", operator)
            self.assertIn(".action/debug.sqlite3", operator)
            self.assertIn("live mode launches the bundled C64", operator)
            self.assertIn("instruction step, and persistent-breakpoint control", operator)
            self.assertIn("TOOLS/actprof <module> live [seconds]", operator)
            self.assertIn(".action/profile.sqlite3", operator)
            self.assertIn(".action/code-map.sqlite3", operator)
            self.assertNotIn("will be Linux tools", operator)
            runtime_status = (out / "DOC" / "runtime-status.txt").read_text(encoding="ascii")
            self.assertIn("RT_GFX_SCREEN_CELL.OBJ", runtime_status)
            self.assertIn("Legacy placeholders not exported", runtime_status)
            self.assertIn("RT_REU_COPY.OBJ", runtime_status)
            self.assertIn("REAL and signed INT source lowering is active", runtime_status)
            self.assertIn("BYTE/CARD/INT/REAL arrays, typed pointers", runtime_status)
            self.assertIn("BYTE/CARD/INT/REAL user functions are active", runtime_status)
            self.assertIn("preserved across recursive calls", runtime_status)
            self.assertIn("REU BYTE ARRAY allocation and 8/16-bit peek/poke are active", runtime_status)
            self.assertIn("OVERLAY blocks are active as resident program-owned PRG sections", runtime_status)
            self.assertIn("DBF1 compiler lowering and link-selected DBF modules are active", runtime_status)
            self.assertIn("DBF path is proven in headless VICE with D64 I/O", runtime_status)
            self.assertIn("physical Idun/C64/REU validation remains pending", runtime_status)

            for tool in ("actc", "alink"):
                compiled = subprocess.run(
                    [str(out / "TOOLS" / tool), "hello"],
                    cwd=out,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(
                    compiled.returncode,
                    0,
                    msg=compiled.stdout + compiled.stderr,
                )
            self.assertGreater((out / "BIN" / "HELLO.PRG").stat().st_size, 2)
            self.assertTrue((out / ".action" / "code-map.sqlite3").is_file())

            for module in ("hello", "math1_demo", "gfx_resource_demo"):
                for tool in ("actc", "alink"):
                    flat = subprocess.run(
                        [str(out / "TOOLS" / tool), module],
                        cwd=out / "PLAYGROUND",
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                    self.assertEqual(
                        flat.returncode, 0, msg=flat.stdout + flat.stderr
                    )
            self.assertTrue((out / "PLAYGROUND" / "HELLO.OBJ").is_file())
            self.assertTrue((out / "PLAYGROUND" / "HELLO.PRG").is_file())
            self.assertTrue((out / "PLAYGROUND" / "HELLO.DBG").is_file())
            self.assertTrue((out / "PLAYGROUND" / "MATH1_DEMO.PRG").is_file())
            self.assertTrue((out / "PLAYGROUND" / "GFX_RESOURCE_DEMO.PRG").is_file())
            self.assertFalse((out / "PLAYGROUND" / "OBJ").exists())
            self.assertFalse((out / "PLAYGROUND" / "BIN").exists())

    def test_export_refuses_to_replace_an_unmarked_external_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "existing"
            out.mkdir()
            keep = out / "keep.txt"
            keep.write_text("user data\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(self.root / "tools" / "export_idun_workspace.py"),
                    "--output",
                    str(out),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing to replace unmarked export directory", result.stderr)
            self.assertEqual(keep.read_text(encoding="utf-8"), "user data\n")

    def test_export_can_refresh_its_own_marked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "idun-action"
            command = [
                "python3",
                str(self.root / "tools" / "export_idun_workspace.py"),
                "--output",
                str(out),
            ]
            first = subprocess.run(
                command,
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
            marker = out / ".actionc64u-idun-export"
            self.assertTrue(marker.is_file())
            (out / "generated-junk.txt").write_text("replace me\n", encoding="utf-8")

            second = subprocess.run(
                command,
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
            self.assertTrue(marker.is_file())
            self.assertFalse((out / "generated-junk.txt").exists())

    def test_export_and_verifier_accept_explicit_tool_build_directory(self) -> None:
        build = subprocess.run(
            ["bash", str(self.root / "tools" / "build_linux_tools.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        source_tools = self.root / "build" / "linux_tools"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "explicit-tools"
            exported = subprocess.run(
                [
                    "python3",
                    str(self.root / "tools" / "export_idun_workspace.py"),
                    "--output",
                    str(out),
                    "--tools-source",
                    str(source_tools),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(exported.returncode, 0, exported.stdout + exported.stderr)
            self.assertEqual(
                (out / "TOOLS" / "actc").read_bytes(),
                (source_tools / "action-workspace-tools").read_bytes(),
            )
            verified = subprocess.run(
                [
                    "python3",
                    str(self.root / "tools" / "verify_idun_artifacts.py"),
                    "--build-tools",
                    str(source_tools),
                    "--export",
                    str(out),
                ],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertIn("idun_artifacts=PASS", verified.stdout)


if __name__ == "__main__":
    unittest.main()
