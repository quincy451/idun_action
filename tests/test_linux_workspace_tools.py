from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestLinuxWorkspaceTools(unittest.TestCase):
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

    def test_project_workflow_uses_host_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            created = self.run_tool(root, "actnew", "demo")
            self.assertEqual(created.stdout, "ACTNEW OK\n")

            project = root / "DEMO"
            self.assertTrue((project / "ACTION.PROJ").is_file())
            self.assertTrue((project / "SRC" / "MAIN.ACT").is_file())
            self.assertTrue((project / "BIN").is_dir())
            self.assertTrue((project / "OBJ").is_dir())
            self.assertFalse((project / "UDOSDIR.TXT").exists())
            self.assertFalse((project / "SRC" / "UDOSDIR.TXT").exists())

            added = self.run_tool(project, "actadd", "worker")
            self.assertEqual(added.stdout, "ACTADD OK\n")
            self.assertIn("WORKER.ACT", (project / "ACTION.PROJ").read_text(encoding="ascii"))
            self.assertEqual(
                (project / "SRC" / "WORKER.ACT").read_text(encoding="ascii"),
                "PROC WORKER()\nENDPROC\n",
            )
            self.assertFalse((project / "SRC" / "UDOSDIR.TXT").exists())

            sources = self.run_tool(project, "actsrc")
            self.assertEqual(sources.stdout.splitlines(), ["MAIN.ACT", "WORKER.ACT"])

            work = self.run_tool(project, "actwork")
            self.assertEqual(
                work.stdout.splitlines(),
                ["PROJECT YES", "SRC YES", "BIN YES", "OBJ YES", "MODULES 2"],
            )

            check = self.run_tool(project, "actchk")
            self.assertIn("ACTCHK OK\n", check.stdout)

    def test_graphics_resource_editors_and_compiler_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resources = root / "assets"
            resources.mkdir()
            sprite = resources / "player.spr"
            bitmap = resources / "marker.abm"

            self.run_tool(root, "actsprite", str(sprite), "new")
            self.run_tool(root, "actsprite", str(sprite), "set", "3", "4", "1")
            self.run_tool(root, "actsprite", str(sprite), "color", "14")
            sprite_info = self.run_tool(root, "actsprite", str(sprite), "info")
            self.assertIn("24x21 hires color=14", sprite_info.stdout)
            self.assertEqual(sprite.read_bytes()[:8], b"ASP1\x00\x0e\x07\x0a")
            self.assertEqual(len(sprite.read_bytes()), 71)

            self.run_tool(root, "actbitmap", str(bitmap), "new", "16", "8")
            self.run_tool(root, "actbitmap", str(bitmap), "set", "2", "3", "1")
            bitmap_info = self.run_tool(root, "actbitmap", str(bitmap), "info")
            self.assertIn("16x8 hires bytes=16", bitmap_info.stdout)
            self.assertEqual(bitmap.read_bytes()[:4], b"ABM1")

            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "RES").mkdir()
            (project / "LIB" / "GFX1.ACT").write_bytes(
                (self.root / "lib" / "gfx1.act").read_bytes()
            )
            (project / "RES" / sprite.name.upper()).write_bytes(sprite.read_bytes())
            (project / "RES" / bitmap.name.upper()).write_bytes(bitmap.read_bytes())
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "GFX1"\n'
                'SPRITE Player=RESOURCE "player.spr"\n'
                'BITMAP Marker=RESOURCE "marker.abm"\n'
                "MODULE MAIN\n"
                "PROC MAIN()\n"
                "SpritePlace(0,Player,120,80)\n"
                "BitmapStamp(Marker,20,20)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            object_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            sprite_export = re.search(
                r"(?m)^x MAIN_PLAYER_DATA (\d+) 64$", object_text
            )
            self.assertIsNotNone(sprite_export)
            self.assertEqual(int(sprite_export.group(1)) % 64, 0)
            self.assertRegex(object_text, r"(?m)^x MAIN_MARKER_DATA \d+ 32$")
            self.run_tool(project, "alink", "main")
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            player_address = next(
                int(parts[1])
                for line in debug.splitlines()
                if len(parts := line.split()) == 4
                and parts[0] == "y"
                and parts[3] == "MAIN_PLAYER_DATA"
            )
            self.assertEqual(player_address % 64, 0)

            (project / "SRC" / "MAIN.ACT").write_text(
                'MSPRITE Wrong=RESOURCE "player.spr"\n'
                "PROC MAIN()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )
            rejected = self.run_tool(
                project, "actc", "main", expected_status=1
            )
            self.assertIn("MODE DOES NOT MATCH DECLARATION", rejected.stderr)

    def test_complete_math_and_gfx_libraries_compile_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "mathdemo")
            math_project = root / "MATHDEMO"
            (math_project / "LIB").mkdir()
            (math_project / "LIB" / "MATH1.ACT").write_bytes(
                (self.root / "lib" / "math1.act").read_bytes()
            )
            (math_project / "SRC" / "MAIN.ACT").write_bytes(
                (self.root / "examples" / "math1_demo.act").read_bytes()
            )
            self.run_tool(math_project, "actc", "main")
            math_object = (math_project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            for symbol in (
                "FATAN2",
                "FATAN",
                "FLOG2",
                "FLOG10",
                "FASIN",
                "FACOS",
                "FASINH",
                "FATANH",
                "DEGTORAD",
                "RADTODEG",
            ):
                self.assertNotRegex(
                    math_object, rf"(?m)^x {symbol} \d+ \d+$"
                )
            self.assertNotRegex(math_object, r"(?m)^x FTRUNC \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FFLOOR \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FCEIL \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FROUND \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FFRAC \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FMOD \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FHYPOT \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FEXP \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FLN \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FLOG2 \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FLOG10 \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FPOW \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FSIN \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FCOS \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x FTAN \d+ \d+$")
            self.assertNotRegex(math_object, r"(?m)^x _MATHWRAPPI \d+ \d+$")
            self.assertNotIn("\nu RT_F_TRUNC\n", math_object)
            self.assertNotIn("\nu RT_F_FLOOR\n", math_object)
            self.assertNotIn("\nu RT_F_CEIL\n", math_object)
            self.assertNotIn("\nu RT_F_ROUND\n", math_object)
            self.assertNotIn("\nu RT_F_FRAC\n", math_object)
            self.assertNotIn("\nu RT_F_MOD\n", math_object)
            self.assertIn("\nu RT_F_POW\n", math_object)
            self.assertIn("\nu RT_F_SIN\n", math_object)
            self.assertIn("\nu RT_F_COS\n", math_object)
            self.assertNotIn("\nu RT_F_TAN\n", math_object)
            self.assertNotIn("\nu RT_F_ATAN\n", math_object)
            self.assertIn("\nu RT_F_ATAN2\n", math_object)
            self.assertNotIn("\nu RT_F_EXP\n", math_object)
            self.assertIn("\nu RT_F_LN\n", math_object)
            self.assertNotIn("\nu RT_F_DEG_TO_RAD\n", math_object)
            self.assertIn("\nu RT_F_RAD_TO_DEG\n", math_object)
            self.run_tool(math_project, "alink", "main")

            self.run_tool(root, "actnew", "gfxdemo")
            gfx_project = root / "GFXDEMO"
            (gfx_project / "LIB").mkdir()
            (gfx_project / "LIB" / "GFX1.ACT").write_bytes(
                (self.root / "lib" / "gfx1.act").read_bytes()
            )
            (gfx_project / "SRC" / "MAIN.ACT").write_bytes(
                (self.root / "examples" / "gfx1_demo.act").read_bytes()
            )
            self.run_tool(gfx_project, "actc", "main")
            gfx_object = (gfx_project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            for symbol in (
                "GFXHIRES",
                "GFXUSESPRITES",
                "GFXBITMAPCLEAR",
                "GFXSCREENCLEAR",
                "GFXCELLCOLORS",
                "PLOT",
                "HLINEDRAW",
                "VLINEDRAW",
                "LINEDRAW",
                "CIRCLEDRAW",
                "RECTANGLEDRAW",
                "SQUAREDRAW",
                "TRIANGLEDRAW",
                "_GFXIABS",
                "_GFXINSIDE",
            ):
                self.assertRegex(gfx_object, rf"(?m)^x {symbol} \d+ \d+$")
            for symbol in (
                "UNPLOT",
                "RECTANGLEFILL",
                "CIRCLEFILL",
                "BITMAPMOVE",
                "SPRITEPLACE",
            ):
                self.assertNotRegex(
                    gfx_object, rf"(?m)^x {symbol} \d+ \d+$"
                )
            self.run_tool(gfx_project, "alink", "main")

    def test_actc_prunes_unreachable_included_source_routines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "prunedemo")
            project = root / "PRUNEDEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "CHAIN.ACT").write_text(
                "MODULE CHAIN\n"
                "PROC USEDLEAF()\n"
                "PrintE(\"LEAF\")\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC USED()\n"
                "USEDLEAF()\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC UNUSED()\n"
                "PrintE(\"UNUSED\")\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC ADDRESSONLY()\n"
                "PrintE(\"ADDRESS\")\n"
                "RETURN\n"
                "ENDPROC\n"
                "OVERLAY USEDOVERLAY\n"
                "PrintE(\"OVERLAY\")\n"
                "ENDOVERLAY\n"
                "OVERLAY UNUSEDOVERLAY\n"
                "PrintE(\"UNUSED OVERLAY\")\n"
                "ENDOVERLAY\n"
                "MODULE\n",
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "CHAIN"\n'
                "MODULE MAIN\n"
                "CARD ARRAY CALLBACKS(0)=[ADDRESSONLY]\n"
                "PROC PROJECTLOCAL()\n"
                "USED()\n"
                "OverlayCall(USEDOVERLAY)\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC MAIN()\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            object_text = (project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            self.assertRegex(object_text, r"(?m)^x MAIN \d+ \d+$")
            self.assertRegex(object_text, r"(?m)^x PROJECTLOCAL \d+ \d+$")
            self.assertRegex(object_text, r"(?m)^x USED \d+ \d+$")
            self.assertRegex(object_text, r"(?m)^x USEDLEAF \d+ \d+$")
            self.assertRegex(object_text, r"(?m)^x ADDRESSONLY \d+ \d+$")
            self.assertRegex(object_text, r"(?m)^x USEDOVERLAY \d+ \d+$")
            self.assertNotRegex(object_text, r"(?m)^x UNUSED \d+ \d+$")
            self.assertNotRegex(
                object_text, r"(?m)^x UNUSEDOVERLAY \d+ \d+$"
            )
            self.run_tool(project, "alink", "main")
            self.assertTrue((project / "BIN" / "MAIN.PRG").is_file())

    def test_math1_constant_include_matches_shared_native_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "MATH1.ACT").write_bytes(
                (self.root / "lib" / "math1.act").read_bytes()
            )
            (project / "SRC" / "MAIN.ACT").write_bytes(
                (
                    self.root
                    / "tests"
                    / "parity"
                    / "math1_constants_include.act"
                ).read_bytes()
            )

            self.run_tool(project, "actc", "main")
            object_text = (project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("MAIN_RESULT_B0", object_text)
            self.assertNotIn("MAIN_MATH_PI_LO", object_text)
            self.run_tool(project, "alink", "main")
            self.assertTrue((project / "BIN" / "MAIN.PRG").is_file())

    def test_actfile_has_no_255_byte_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            long_source = "PROC MAIN()\n" + ("; comment line\n" * 80) + "ENDPROC\n"
            self.assertGreater(len(long_source), 255)
            (project / "SRC" / "MAIN.ACT").write_text(long_source, encoding="ascii")

            result = self.run_tool(project, "actfile", "main")
            self.assertEqual(result.stdout, long_source)
            self.assertNotIn("TRUNCATED", result.stdout)

    def test_crlf_sources_keep_logical_line_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_bytes(
                b"PROC MAIN()\r\nBYTE value\r\nBOGUS TOKEN\r\nENDPROC\r\n"
            )

            symbols = self.run_tool(project, "actedit", "main", "symbols")
            self.assertIn("BYTE VALUE SRC/MAIN.ACT:2\n", symbols.stdout)
            result = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertEqual(result.stderr, "UNSUPPORTED LINE 3: BOGUS TOKEN\n")

    def test_actedit_line_operations_are_linux_side(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"

            self.run_tool(project, "actedit", "main", "replace", "1", "PROC MAIN()")
            self.run_tool(project, "actedit", "main", "insert", "2", "HELPER()")
            self.run_tool(project, "actedit", "main", "append", "RETURN")
            self.run_tool(project, "actedit", "main", "delete", "3")

            source = (project / "SRC" / "MAIN.ACT").read_text(encoding="ascii")
            self.assertEqual(source, "PROC MAIN()\nHELPER()\nRETURN\n")
            printed = self.run_tool(project, "actedit", "main", "print")
            self.assertEqual(printed.stdout, source)
            indexed = self.run_tool(project, "actedit", "main", "index")
            self.assertEqual(indexed.stdout, "ACTEDIT INDEXED\n")
            found = self.run_tool(project, "actedit", "main", "find", "HELPER")
            self.assertEqual(found.stdout, "SRC/MAIN.ACT:2:HELPER()\n")
            symbols = self.run_tool(project, "actedit", "main", "symbols")
            self.assertIn("PROC MAIN SRC/MAIN.ACT:1\n", symbols.stdout)
            self.assertTrue((project / ".action" / "workspace.sqlite3").is_file())
            self.assertFalse((project / "SRC" / "UDOSDIR.TXT").exists())

    def test_actedit_prefers_current_source_and_project_tools_find_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            project_source = "PROC MAIN()\nRETURN\nENDPROC\n"
            current_source = "; current-directory source\n"
            (project / "SRC" / "MAIN.ACT").write_text(
                project_source, encoding="ascii"
            )
            (project / "MAIN.ACT").write_text(current_source, encoding="ascii")

            current = self.run_tool(project, "actedit", "main", "print")
            self.assertEqual(current.stdout, current_source)
            explicit = self.run_tool(
                project, "actedit", "SRC/main.act", "print"
            )
            self.assertEqual(explicit.stdout, project_source)

            compiled = self.run_tool(project / "SRC", "actc", "main")
            self.assertEqual(compiled.stdout, "ACTC OK\n")
            self.assertTrue((project / "SRC" / "MAIN.OBJ").is_file())
            self.assertFalse((project / "OBJ" / "MAIN.OBJ").exists())
            linked = self.run_tool(project / "SRC", "alink", "main")
            self.assertEqual(linked.stdout, "ALINK OK\n")
            self.assertTrue((project / "SRC" / "MAIN.PRG").is_file())
            self.assertTrue((project / "SRC" / "MAIN.DBG").is_file())

            selected = subprocess.run(
                [str(self.tool_dir / "actedit"), "SRC/main.act", "print"],
                cwd=root,
                env={**os.environ, "ACTION_PROJECT": str(project)},
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(selected.returncode, 0, msg=selected.stderr)
            self.assertEqual(selected.stdout, project_source)

    def test_actc_and_alink_use_flat_current_directory_when_source_is_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = (self.root / "examples" / "math1_demo.act").read_text(
                encoding="ascii"
            )
            (root / "MATH1_DEMO.ACT").write_text(source, encoding="ascii")

            compiled = self.run_tool(root, "actc", "math1_demo")
            self.assertEqual(compiled.stdout, "ACTC OK\n")
            self.assertTrue((root / "MATH1_DEMO.OBJ").is_file())
            self.assertFalse((root / "OBJ").exists())

            linked = self.run_tool(root, "alink", "math1_demo")
            self.assertEqual(linked.stdout, "ALINK OK\n")
            self.assertTrue((root / "MATH1_DEMO.PRG").is_file())
            self.assertTrue((root / "MATH1_DEMO.DBG").is_file())
            self.assertFalse((root / "BIN").exists())
            self.assertTrue((root / ".action" / "code-map.sqlite3").is_file())

            edited_build = self.run_tool(
                root, "actedit", "math1_demo", "build"
            )
            self.assertEqual(edited_build.stdout, "ACTC OK\nALINK OK\n")

    def test_user_install_exposes_linux_commands_from_any_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            installed = subprocess.run(
                [
                    "bash",
                    str(self.root / "tools" / "install_linux_tools.sh"),
                    "--tools",
                    str(self.tool_dir),
                    "--bin-dir",
                    str(bin_dir),
                ],
                cwd=root,
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
            self.assertIn("Installed 31 Action Linux commands", installed.stdout)
            for name in (
                "actc",
                "actedit",
                "actspc",
                "actsprite",
                "actbitmap",
                "alink",
                "acthelp",
            ):
                self.assertTrue((bin_dir / name).is_symlink())

            help_result = subprocess.run(
                [str(bin_dir / "acthelp"), "IF"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(help_result.returncode, 0, msg=help_result.stderr)
            self.assertIn("IF [keyword]", help_result.stdout)

    def test_actspc_formats_action_source_atomically_and_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "messy.act"
            source.write_bytes(
                b"; header  \r\n"
                b"MODULE   demo\r\n\r\n\r\n"
                b"PROC   main( CARD argc , CARD ARRAY argv )\r\n"
                b"CARD   x \t\r\n"
                b"x = ( 2 + 3 ) * 4 ; keep  two  spaces\r\n"
                b"IF   x >= 4   THEN\r\n"
                b"PrintE( \"A  B;C\" )\r\n"
                b"ELSE\r\n"
                b"PrintE(\"NO\")\r\n"
                b"FI\r\n"
                b"ASMBLOCK   [\r\n"
                b"lda   x\r\n"
                b"loop:\r\n"
                b"dex\r\n"
                b"bne   loop\r\n"
                b"]\r\n"
                b"RETURN\r\n"
                b"ENDPROC\r\n\r\n"
            )
            source.chmod(0o640)

            formatted = self.run_tool(root, "actspc", "messy.act")
            self.assertEqual(
                formatted.stdout,
                "FORMATTED messy.act\n"
                "ACTSPC OK files=1 changed=1 unchanged=0\n",
            )
            self.assertEqual(source.stat().st_mode & 0o777, 0o640)
            self.assertEqual(
                source.read_text(encoding="ascii"),
                "; header\n"
                "MODULE demo\n\n"
                "PROC main(CARD argc,CARD ARRAY argv)\n"
                "    CARD x\n"
                "    x=(2+3)*4  ; keep  two  spaces\n"
                "    IF x>=4 THEN\n"
                "        PrintE(\"A  B;C\")\n"
                "    ELSE\n"
                "        PrintE(\"NO\")\n"
                "    FI\n"
                "    ASMBLOCK [\n"
                "        lda x\n"
                "    loop:\n"
                "        dex\n"
                "        bne loop\n"
                "    ]\n"
                "    RETURN\n"
                "ENDPROC\n",
            )

            unchanged = self.run_tool(root, "actspc", "messy")
            self.assertEqual(
                unchanged.stdout,
                "UNCHANGED messy.act\n"
                "ACTSPC OK files=1 changed=0 unchanged=1\n",
            )
            self.run_tool(root, "actc", "messy")
            self.run_tool(root, "alink", "messy")

    def test_actspc_expands_case_insensitive_wildcards_and_validates_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lower = root / "one.act"
            upper = root / "TWO.ACT"
            lower.write_text(
                "MODULE one\nPROC main()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )
            upper.write_text(
                "MODULE   api\nPROC   First( BYTE value )\n"
                "PROC Second()\nMODULE\n",
                encoding="ascii",
            )
            (root / "notes.txt").write_text("not Action\n", encoding="ascii")

            no_match = self.run_tool(
                root,
                "actspc",
                "one.act",
                "missing*.act",
                expected_status=1,
            )
            self.assertEqual(no_match.stderr, "ACTSPC NO MATCH: missing*.act\n")
            self.assertIn("PROC main()\nRETURN", lower.read_text(encoding="ascii"))

            formatted = self.run_tool(root, "actspc", "*.act")
            self.assertIn("FORMATTED one.act\n", formatted.stdout)
            self.assertIn("FORMATTED TWO.ACT\n", formatted.stdout)
            self.assertTrue(
                formatted.stdout.endswith(
                    "ACTSPC OK files=2 changed=2 unchanged=0\n"
                )
            )
            self.assertEqual(
                upper.read_text(encoding="ascii"),
                "MODULE api\n"
                "PROC First(BYTE value)\n"
                "PROC Second()\n"
                "MODULE\n",
            )

            deduplicated = self.run_tool(
                root, "actspc", "one.act", "TWO.ACT", "one.act"
            )
            self.assertTrue(
                deduplicated.stdout.endswith(
                    "ACTSPC OK files=2 changed=0 unchanged=2\n"
                )
            )

            no_args = self.run_tool(root, "actspc", expected_status=1)
            self.assertEqual(no_args.stderr, "ACTSPC NO FILESPEC\n")

    def test_actspc_formatted_shipped_examples_still_compile_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            examples = sorted((self.root / "examples").glob("*.act"))
            for source in examples:
                (root / source.name).write_bytes(source.read_bytes())
            for resource in (self.root / "examples" / "assets").iterdir():
                if resource.is_file():
                    (root / resource.name).write_bytes(resource.read_bytes())

            self.run_tool(root, "actspc", "*.act")
            second_pass = self.run_tool(root, "actspc", "*.act")
            self.assertTrue(
                second_pass.stdout.endswith(
                    f"ACTSPC OK files={len(examples)} changed=0 "
                    f"unchanged={len(examples)}\n"
                )
            )
            for source in examples:
                with self.subTest(module=source.stem):
                    self.run_tool(root, "actc", source.stem)
                    self.run_tool(root, "alink", source.stem)

    def test_actedit_and_actmon_drive_linux_build_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nPrintE(\"WORKFLOW\")\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            compiled = self.run_tool(project, "actedit", "main", "compile")
            self.assertEqual(compiled.stdout, "ACTC OK\n")
            self.assertTrue((project / "OBJ" / "MAIN.OBJ").is_file())

            built = self.run_tool(project, "actedit", "main", "build")
            self.assertEqual(built.stdout, "ACTC OK\nALINK OK\n")
            self.assertTrue((project / "BIN" / "MAIN.PRG").is_file())
            self.assertTrue((project / "BIN" / "MAIN.DBG").is_file())

            debugged = self.run_tool(project, "actedit", "main", "debug")
            self.assertIn("ACTC OK\nALINK OK\nACTDBG INFO\n", debugged.stdout)

            sources = self.run_tool(project, "actmon", "sources")
            self.assertEqual(sources.stdout, "MAIN.ACT\n")
            checked = self.run_tool(project, "actmon", "check")
            self.assertIn("ACTCHK OK\n", checked.stdout)
            monitored_build = self.run_tool(project, "actmon", "build", "main")
            self.assertEqual(monitored_build.stdout, "ACTC OK\nALINK OK\n")
            monitored_debug = self.run_tool(project, "actmon", "debug", "main")
            self.assertIn("ACTDBG INFO\n", monitored_debug.stdout)

    def test_linux_filesystem_tools_do_not_need_udos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write = self.run_tool(root, "actwrite", "one.txt", "hello", "world")
            self.assertEqual(write.stdout, "ACTWRITE OK\n")
            self.assertEqual((root / "one.txt").read_text(encoding="ascii"), "hello world\n")

            mkdir = self.run_tool(root, "actmkdir", "sub")
            self.assertEqual(mkdir.stdout, "ACTMKDIR OK\n")
            self.assertTrue((root / "sub").is_dir())

            copy = self.run_tool(root, "actcopy", "one.txt", "sub/two.txt")
            self.assertEqual(copy.stdout, "ACTCOPY OK\n")
            self.assertEqual((root / "sub" / "two.txt").read_text(encoding="ascii"), "hello world\n")

            directory = self.run_tool(root, "actdir")
            self.assertIn("F one.txt", directory.stdout)
            self.assertIn("D sub", directory.stdout)

            move = self.run_tool(root, "actmove", "sub/two.txt", "sub/three.txt")
            self.assertEqual(move.stdout, "ACTMOVE OK\n")
            self.assertFalse((root / "sub" / "two.txt").exists())
            self.assertTrue((root / "sub" / "three.txt").is_file())

            tree = self.run_tool(root, "acttree")
            self.assertIn("F one.txt", tree.stdout)
            self.assertIn("F sub/three.txt", tree.stdout)

            delete = self.run_tool(root, "actdel", "sub/three.txt")
            self.assertEqual(delete.stdout, "ACTDEL OK\n")
            self.assertFalse((root / "sub" / "three.txt").exists())

            rmdir = self.run_tool(root, "actrmdir", "sub")
            self.assertEqual(rmdir.stdout, "ACTRMDIR OK\n")
            self.assertFalse((root / "sub").exists())
            self.assertFalse((root / "UDOSDIR.TXT").exists())

    def test_recursive_linux_filesystem_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "nested").mkdir(parents=True)
            (root / "src" / "nested" / "file.txt").write_text("payload\n", encoding="ascii")

            copied = self.run_tool(root, "xcopy", "src", "dst")
            self.assertEqual(copied.stdout, "XCOPY OK\n")
            self.assertEqual((root / "dst" / "nested" / "file.txt").read_text(encoding="ascii"), "payload\n")

            removed = self.run_tool(root, "deltree", "dst")
            self.assertEqual(removed.stdout, "DELTREE OK\n")
            self.assertFalse((root / "dst").exists())

            info = self.run_tool(root, "actinfo")
            self.assertIn("ACTIONC64U IDUN LINUX TOOLS", info.stdout)

    def test_recursive_filesystem_tools_refuse_self_copy_and_unsafe_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "nested").mkdir(parents=True)
            (root / "src" / "nested" / "file.txt").write_text(
                "payload\n", encoding="ascii"
            )

            copied = self.run_tool(
                root,
                "xcopy",
                "src",
                "src/copy",
                expected_status=1,
            )
            self.assertEqual(copied.stderr, "COPY INTO SELF\n")
            self.assertFalse((root / "src" / "copy").exists())

            current = self.run_tool(root, "deltree", ".", expected_status=1)
            self.assertEqual(current.stderr, "REFUSE DANGEROUS DELETE\n")
            self.assertTrue(root.is_dir())

            parent = self.run_tool(root, "deltree", "..", expected_status=1)
            self.assertEqual(parent.stderr, "REFUSE DANGEROUS DELETE\n")
            self.assertTrue(root.parent.is_dir())

    def test_actchk_reports_missing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").unlink()

            result = self.run_tool(project, "actchk", expected_status=1)
            self.assertIn("MISSING 1\n", result.stdout)
            self.assertIn("MISSING MAIN.ACT\n", result.stdout)
            self.assertIn("ACTCHK BROKEN\n", result.stdout)

    def test_act2save_compatibility_name_uses_real_linker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "OBJ" / "MAIN.OBJ").write_text("OBJ1\nx MAIN 0 1\nb M\nm 60\n", encoding="ascii")

            result = self.run_tool(project, "act2save")
            self.assertEqual(result.stdout, "ALINK OK\nACT2SAVE OK\n")
            self.assertEqual((project / "BIN" / "MAIN.PRG").read_bytes(), bytes([0x00, 0x10, 0x60]))

    def test_actc_alink_write_direct_prg_without_udos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"

            compiled = self.run_tool(project, "actc", "main")
            self.assertEqual(compiled.stdout, "ACTC OK\n")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("OBJ1\n", obj_text)
            self.assertIn("x MAIN 0 4\n", obj_text)
            self.assertIn("x MAIN_MAIN_BODY_0 3 1\n", obj_text)
            self.assertIn("m 4C000060\n", obj_text)

            linked = self.run_tool(project, "alink", "main")
            self.assertEqual(linked.stdout, "ALINK OK\n")
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes(),
                bytes([0x00, 0x10, 0x4C, 0x03, 0x10, 0x60]),
            )
            self.assertTrue((project / "BIN" / "MAIN.DBG").is_file())

            debug = self.run_tool(project, "actdbg", "main")
            self.assertIn("ACTDBG INFO\n", debug.stdout)
            self.assertIn("MODULE MAIN\n", debug.stdout)
            self.assertIn("LOAD 4096\n", debug.stdout)
            self.assertIn("SIZE 4\n", debug.stdout)
            self.assertIn("e 4096\n", debug.stdout)
            self.assertIn("f 0 SRC/MAIN.ACT\n", debug.stdout)
            self.assertIn("l 4096 0 1\n", debug.stdout)
            self.assertIn("y 4096 4 MAIN\n", debug.stdout)

            line = self.run_tool(project, "actdbg", "main", "line", "1")
            self.assertEqual(line.stdout, "ADDRESS 4096 SRC/MAIN.ACT:1\n")
            source = self.run_tool(project, "actdbg", "main", "source", "$1000")
            self.assertEqual(source.stdout, "SOURCE 4096 SRC/MAIN.ACT:1\n")
            symbols = self.run_tool(project, "actdbg", "main", "symbols", "MAIN")
            self.assertIn("SYMBOL 4096 4 MAIN\n", symbols.stdout)

            stored = self.run_tool(project, "actdbg", "main", "break", "1")
            self.assertIn(" 4096 SRC/MAIN.ACT:1\n", stored.stdout)
            breakpoint_id = stored.stdout.split()[1]
            listed = self.run_tool(project, "actdbg", "main", "breaks")
            self.assertIn(
                f"BREAKPOINT {breakpoint_id} 4096 SRC/MAIN.ACT:1 ENABLED\n",
                listed.stdout,
            )
            cleared = self.run_tool(
                project, "actdbg", "main", "clear", breakpoint_id
            )
            self.assertEqual(
                cleared.stdout, f"BREAKPOINT CLEARED {breakpoint_id}\n"
            )
            self.assertTrue((project / ".action" / "debug.sqlite3").is_file())

            monitor = self.run_tool(project, "actmon")
            self.assertIn("ACTIONC64U MONITOR\n", monitor.stdout)
            self.assertIn("PROJECT YES\n", monitor.stdout)
            self.assertIn("MAIN.ACT\n", monitor.stdout)
            self.assertIn("COMMANDS actnew actadd actedit actc alink actdbg actchk\n", monitor.stdout)

    def test_actc_alink_patch_local_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC HELPER()\nRETURN\nENDPROC\nPROC MAIN()\nHELPER()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertEqual(
                prg,
                bytes(
                    [
                        0x00,
                        0x10,
                        0x4C,
                        0x03,
                        0x10,  # MAIN's assignable JMP entry
                        0x20,
                        0x07,
                        0x10,  # JSR HELPER's assignable entry
                        0x60,
                        0x4C,
                        0x0A,
                        0x10,  # HELPER's assignable JMP entry
                        0x60,
                    ]
                ),
            )

    def test_actc_module_globals_are_shared_across_procedures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(
                    encoding="ascii"
                ),
                encoding="ascii",
            )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "MODULE MAIN",
                        "CARD counter",
                        "PROC BUMP()",
                        "counter = counter + 1",
                        "RETURN",
                        "PROC MAIN()",
                        "counter = 5 ; inline comments are ignored",
                        "BUMP()",
                        "PrintI(counter)",
                        "RETURN",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertEqual(obj_text.count("x MAIN_COUNTER_LO "), 1)
            self.assertEqual(obj_text.count("x MAIN_COUNTER_HI "), 1)
            self.assertIn("x BUMP ", obj_text)
            self.assertGreaterEqual(obj_text.count("x MAIN_COUNTER_LO"), 1)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0x20]), prg)
            self.assertIn(bytes.fromhex("85FB86FC"), prg)

    def test_actc_bracket_initializers_become_linked_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "MODULE MAIN",
                        "BYTE flag=[$7F]",
                        "CARD count=[$1234]",
                        "PROC MAIN()",
                        "BYTE local=[2 + 3]",
                        "flag = local + 0",
                        "count = count + 0",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("x MAIN_FLAG_LO", obj_text)
            self.assertIn("x MAIN_COUNT_HI", obj_text)
            self.assertIn("x MAIN_LOCAL_LO", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertTrue(prg.endswith(bytes([0x7F, 0x34, 0x12, 0x05])))

    def test_actc_address_bound_variables_use_direct_c64_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "MODULE MAIN",
                        "BYTE border=$D020",
                        "CARD clock=$00A0",
                        "PROC MAIN()",
                        "BYTE copy",
                        "border = 6",
                        "clock = $1234",
                        "copy = border + 0",
                        "copy = copy + border",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("MAIN_BORDER_LO", obj_text)
            self.assertNotIn("MAIN_CLOCK_LO", obj_text)
            self.assertIn("8D20D0", obj_text)
            self.assertIn("8DA000", obj_text)
            self.assertIn("8EA100", obj_text)
            self.assertIn("AD20D0", obj_text)
            self.assertIn("6D20D0", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_rejects_declaration_binding_ranges(self) -> None:
        cases = {
            "byte_initializer": (
                "MODULE MAIN\nBYTE x=[256]\nPROC MAIN()\nENDPROC\n",
                "INITIALIZER RANGE LINE 2: X\n",
            ),
            "card_address": (
                "MODULE MAIN\nCARD x=$FFFF\nPROC MAIN()\nENDPROC\n",
                "ADDRESS RANGE LINE 2: X\n",
            ),
        }
        for name, (source, expected_error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(source, encoding="ascii")
                result = self.run_tool(project, "actc", "main", expected_status=1)
                self.assertEqual(result.stderr, expected_error)

    def test_actc_arrays_pointers_strings_and_local_procedure_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE main\n"
                'BYTE ARRAY greeting="HI"\n'
                "BYTE ARRAY bytes(4)=[1 2 3 4]\n"
                "CARD ARRAY words(3)=[256 512 768]\n"
                'CARD ARRAY messages(2)=["ONE" "T""WO"]\n'
                "BYTE value\n"
                "BYTE ARRAY selected\n"
                "CARD wide\n"
                "BYTE POINTER ptr\n"
                "PROC consume(BYTE n,CARD w,BYTE ARRAY text,BYTE POINTER out)\n"
                "out^=n\n"
                "bytes(2)=out^+1\n"
                "words(1)=w+bytes(2)\n"
                "PrintE(text)\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC main()\n"
                "ptr=@value\n"
                "consume(7,500,greeting,ptr)\n"
                'consume(9,600,"OK",ptr)\n'
                "selected=messages(1)\n"
                "consume(3,700,selected,ptr)\n"
                'consume(4,800,"A,""B",ptr)\n'
                "wide=words(1)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "MAIN_GREETING_DATA",
                "MAIN_BYTES_DATA",
                "MAIN_WORDS_DATA",
                "MAIN_MESSAGES_DATA",
                "CONSUME_N_LO",
                "CONSUME_W_HI",
                "CONSUME_TEXT_LO",
                "CONSUME_OUT_HI",
            ):
                self.assertIn(symbol, obj_text)
            self.assertIn("\nx CONSUME ", obj_text)
            self.assertIn("024849", obj_text)
            self.assertIn("024F4B", obj_text)
            self.assertIn("034F4E45", obj_text)
            self.assertIn("045422574F", obj_text)
            self.assertIn("04412C2242", obj_text)
            self.assertGreaterEqual(len(re.findall(r"r \d+ x MAIN___STRING_", obj_text)), 2)
            self.assertNotIn("\nu ", obj_text)

            self.run_tool(project, "alink", "main")
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("MAIN", debug)
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2],
                bytes([0x00, 0x10]),
            )

    def test_actc_real_arrays_pointers_and_indirect_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in (
                "rt_f_add.obj",
                "rt_f_cmp.obj",
                "rt_print_f.obj",
                "rt_s_to_f.obj",
            ):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "REAL ARRAY samples(3)=[1.25,2.5,3.75]\n"
                "PROC CopyAndAdd(REAL ARRAY source,REAL POINTER destination)\n"
                "destination^=source(1)+source(0)\n"
                "RETURN\n"
                "ENDPROC\n"
                "PROC MAIN()\n"
                "REAL ARRAY local(2)=[4.0,5.5]\n"
                "REAL result\n"
                "REAL POINTER ptr\n"
                "ptr=@result\n"
                "CopyAndAdd(samples,ptr)\n"
                "local(1)=result+local(0)\n"
                "PrintRE(local(1))\n"
                "IF local(1)>samples(2) THEN\n"
                "PrintRE(ptr^)\n"
                "FI\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "MAIN_SAMPLES_DATA",
                "MAIN_SAMPLES_PTR_LO",
                "MAIN_LOCAL_DATA",
                "MAIN_RESULT_B0",
                "MAIN_PTR_LO",
                "COPYANDADD_SOURCE_LO",
                "COPYANDADD_DESTINATION_HI",
            ):
                self.assertIn(symbol, obj_text)
            self.assertIn("0000A03F0000204000007040", obj_text)
            self.assertIn("\nu RT_F_ADD\n", obj_text)
            self.assertIn("\nu RT_F_CMP\n", obj_text)
            self.assertIn("\nu RT_PRINT_F\n", obj_text)

            self.run_tool(project, "alink", "main")
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2],
                bytes([0x00, 0x10]),
            )
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("COPYANDADD", debug)
            self.assertIn("RT_F_ADD", debug)

    def test_actc_user_functions_return_word_and_real_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in (
                "rt_f_add.obj",
                "rt_i_mul.obj",
                "rt_i_to_f.obj",
                "rt_print_f.obj",
                "rt_print_i.obj",
                "rt_s_to_f.obj",
            ):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "CARD FUNC Square(CARD value)\n"
                "RETURN (value*value)\n"
                "BYTE FUNC Limit(BYTE value)\n"
                "IF value>10 THEN\n"
                "RETURN(10)\n"
                "FI\n"
                "RETURN (value)\n"
                "INT FUNC Negate(INT value)\n"
                "RETURN (-value)\n"
                "REAL FUNC Twice(REAL value)\n"
                "RETURN (value+value)\n"
                "PROC MAIN()\n"
                "CARD total\n"
                "INT signed\n"
                "REAL doubled\n"
                "total=Square(9)+Limit(12)\n"
                "signed=Negate(7)\n"
                "doubled=Twice(1.5)+REAL(total)\n"
                "PrintIE(total)\n"
                "PrintIE(signed)\n"
                "PrintRE(doubled)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for function in ("SQUARE", "LIMIT", "NEGATE", "TWICE"):
                self.assertIn(f"\nx {function} ", obj_text)
                self.assertNotIn(f"\nu {function}\n", obj_text)
            for symbol in (
                "SQUARE_VALUE_HI",
                "LIMIT_VALUE_LO",
                "NEGATE_VALUE_HI",
                "TWICE_VALUE_B0",
                "TWICE_RETURN_B0",
                "TWICE_RETURN_PTR_LO",
            ):
                self.assertIn(symbol, obj_text)
            self.assertIn("\nu RT_I_MUL\n", obj_text)
            self.assertIn("\nu RT_F_ADD\n", obj_text)
            self.assertIn("\nu RT_I_TO_F\n", obj_text)

            self.run_tool(project, "alink", "main")
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2],
                bytes([0x00, 0x10]),
            )
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for function in ("SQUARE", "LIMIT", "NEGATE", "TWICE"):
                self.assertIn(function, debug)

    def _compile_and_link_real_function_fixture(
        self,
        fixture_name: str,
        export_names: str | tuple[str, ...],
        expected_imports: str | tuple[str, ...] | None,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_bytes(
                (self.root / "tests" / "parity" / fixture_name).read_bytes()
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            if isinstance(export_names, str):
                export_names = (export_names,)
            for export_name in export_names:
                self.assertRegex(obj_text, rf"(?m)^x {export_name} \d+ \d+$")
            if expected_imports is None:
                self.assertNotIn("\nu RT_F_CMP\n", obj_text)
            else:
                if isinstance(expected_imports, str):
                    expected_imports = (expected_imports,)
                for expected_import in expected_imports:
                    self.assertIn(f"\nu {expected_import}\n", obj_text)
            self.assertNotIn("\nu RT_I_TO_F\n", obj_text)

            self.run_tool(project, "alink", "main")
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2],
                bytes([0x00, 0x10]),
            )

    def test_native_real_function_parity_fixtures_compile_and_link(self) -> None:
        for fixture_name, export_names, expected_imports in (
            ("finite_real_min.act", "MIN2", "RT_F_CMP"),
            ("finite_real_min_permuted.act", "MIN2", "RT_F_CMP"),
            ("two_real_second_return_permuted.act", "SECOND", None),
            ("real_function_binary_hypot.act", "LENGTH", "RT_F_HYPOT"),
            ("real_function_nested_postfix.act", "LENGTH", "RT_F_HYPOT"),
            ("real_function_local_nested_postfix.act", "LENGTH", "RT_F_HYPOT"),
            (
                "real_two_function_nested_postfix.act",
                ("LENGTH", "SHORTER"),
                ("RT_F_HYPOT", "RT_F_MIN"),
            ),
            (
                "real_function_call_chain_postfix.act",
                ("LENGTH", "CHAIN"),
                ("RT_F_HYPOT", "RT_F_MAX"),
            ),
            (
                "real_function_nested_local_call_postfix.act",
                ("LENGTH", "CHAIN"),
                ("RT_F_HYPOT", "RT_F_MAX"),
            ),
            (
                "real_function_user_call_arguments_postfix.act",
                ("LOWER", "CHAIN"),
                ("RT_F_MIN",),
            ),
            (
                "real_function_forward_frame_postfix.act",
                ("FIRST", "SECOND"),
                ("RT_F_ABS", "RT_F_MAX", "RT_F_MIN"),
            ),
            (
                "real_function_if_else_postfix.act",
                ("PICK",),
                ("RT_F_CMP", "RT_F_MAX"),
            ),
            (
                "real_function_sequential_if_else_postfix.act",
                ("PICK",),
                ("RT_F_CMP", "RT_F_MAX", "RT_F_MIN"),
            ),
            (
                "real_function_nested_if_else_postfix.act",
                ("PICK",),
                ("RT_F_CMP", "RT_F_MAX", "RT_F_MIN"),
            ),
            (
                "real_function_four_sequential_if_postfix.act",
                ("PICK",),
                ("RT_F_CMP",),
            ),
            (
                "real_function_four_deep_if_postfix.act",
                ("PICK",),
                ("RT_F_CMP",),
            ),
            (
                "real_function_early_return_if_postfix.act",
                ("PICK",),
                ("RT_F_CMP",),
            ),
            (
                "real_function_early_return_four_deep_postfix.act",
                ("PICK",),
                ("RT_F_CMP",),
            ),
            (
                "real_function_loops_postfix.act",
                ("UP", "DOWN"),
                ("RT_F_CMP",),
            ),
            (
                "real_function_loop_exit_postfix.act",
                ("PLAIN", "GUARDED"),
                ("RT_F_CMP",),
            ),
            (
                "real_function_for_postfix.act",
                ("ASCEND", "DESCEND"),
                ("RT_F_ADD",),
            ),
            (
                "real_function_dynamic_for_postfix.act",
                ("FROMOUTER", "TOOUTER"),
                ("RT_F_ADD",),
            ),
            (
                "math1_angle_conversions_postfix.act",
                ("LOCALD2R", "LOCALR2D"),
                ("RT_F_DIV", "RT_F_MUL"),
            ),
            (
                "real_function_literal_clamp_comma_locals_postfix.act",
                ("LIMIT",),
                ("RT_F_CMP", "RT_F_MUL"),
            ),
        ):
            with self.subTest(fixture=fixture_name):
                self._compile_and_link_real_function_fixture(
                    fixture_name,
                    export_names,
                    expected_imports,
                )

    def test_actc_reentrant_routine_frames_compile_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in ("rt_f_add.obj", "rt_s_to_f.obj"):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
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
                "wordresult=Sum(5)\n"
                "mutualresult=MutualA(4)\n"
                "realresult=Accumulate(3,1.0)+Accumulate(2,2.0)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "SUM_VALUE_LO",
                "SUM_VALUE_HI",
                "SUM_SAVED_DATA_FRAME_0",
                "ACCUMULATE_COUNT_LO",
                "ACCUMULATE_COUNT_HI",
                "ACCUMULATE_VALUE_B0",
                "ACCUMULATE_SAVED_B0",
                "MUTUALA_SAVED_LO",
                "MUTUALB_SAVED_LO",
            ):
                self.assertIn(f"x {symbol} ", obj_text)
            self.assertIn("\nu RT_F_ADD\n", obj_text)
            self.run_tool(project, "alink", "main")
            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2],
                bytes([0x00, 0x10]),
            )

    def test_actc_limits_only_frames_on_recursive_call_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC Leaf()\n"
                "RETURN\n"
                "PROC Worker()\n"
                "BYTE ARRAY data(300)\n"
                "Leaf()\n"
                "RETURN\n"
                "PROC MAIN()\n"
                "Worker()\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC Recurse()\n"
                "BYTE ARRAY data(225)\n"
                "Recurse()\n"
                "RETURN\n"
                "PROC MAIN()\n"
                "Recurse()\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            result = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertEqual(result.stderr, "REENTRANT FRAME TOO LARGE RECURSE\n")
            self.assertFalse((project / "OBJ" / "MAIN.OBJ").exists())

    def test_actc_diagnoses_invalid_function_returns(self) -> None:
        cases = {
            "missing": (
                "BYTE FUNC Missing()\nBYTE value\nPROC MAIN()\nRETURN\nENDPROC\n",
                "MISSING FUNC RETURN LINE 1: MISSING\n",
            ),
            "bare": (
                "BYTE FUNC Broken()\nRETURN\nPROC MAIN()\nRETURN\nENDPROC\n",
                "FUNC RETURN VALUE REQUIRED LINE 2\n",
            ),
            "proc_value": (
                "PROC MAIN()\nRETURN(1)\nENDPROC\n",
                "PROC RETURN HAS VALUE LINE 2\n",
            ),
        }
        for name, (source, expected_error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    source,
                    encoding="ascii",
                )
                result = self.run_tool(
                    project,
                    "actc",
                    "main",
                    expected_status=1,
                )
                self.assertEqual(result.stderr, expected_error)
                self.assertFalse((project / "OBJ" / "MAIN.OBJ").exists())

    def test_actc_rejects_array_storage_beyond_c64_address_space(self) -> None:
        for declaration in (
            "BYTE ARRAY huge(65536)",
            "REAL ARRAY huge(16384)",
        ):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    f"PROC MAIN()\n{declaration}\nRETURN\nENDPROC\n",
                    encoding="ascii",
                )

                result = self.run_tool(project, "actc", "main", expected_status=1)
                self.assertEqual(result.stderr, "ARRAY SIZE RANGE LINE 2: HUGE\n")
                self.assertFalse((project / "OBJ" / "MAIN.OBJ").exists())

    def test_actc_real_expressions_select_only_referenced_helpers(self) -> None:
        runtime_names = tuple(
            path.name
            for path in (self.root / "src" / "runtime" / "modules").glob("rt_*f*.obj")
            if path.name
            in {
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
                "rt_f_pow.obj",
                "rt_f_sin.obj",
                "rt_f_cos.obj",
                "rt_f_tan.obj",
                "rt_f_atan.obj",
                "rt_f_atan2.obj",
                "rt_f_asin.obj",
                "rt_f_acos.obj",
                "rt_f_sec.obj",
                "rt_f_csc.obj",
                "rt_f_cot.obj",
                "rt_f_asec.obj",
                "rt_f_acsc.obj",
                "rt_f_wrap_pi.obj",
                "rt_f_exp.obj",
                "rt_f_ln.obj",
                "rt_f_log2.obj",
                "rt_f_log10.obj",
                "rt_f_min.obj",
                "rt_f_max.obj",
                "rt_f_addsub_core.obj",
                "rt_f_special.obj",
                "rt_f_mul.obj",
                "rt_f_sign.obj",
                "rt_f_sqrt.obj",
                "rt_f_sub.obj",
                "rt_f_trunc.obj",
                "rt_f_to_i.obj",
                "rt_i_to_f.obj",
                "rt_print_f.obj",
                "rt_s_to_f.obj",
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in runtime_names:
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD n",
                        "REAL a=[1.5],b=[2.0],sum,difference,product,quotient,root,absolute,truncated,floored,ceiled,rounded,fractional,modulus,hypotenuse,power,sine,cosine,tangent,arctangent,arctangent2,arcsine,arccosine,secant,cosecant,cotangent,arcsecant,arccosecant,exponential,logarithm,logarithm2,logarithm10,minimum,maximum,fromint",
                        "n = 3",
                        "sum = a + b",
                        "difference = a - b",
                        "product = a * b",
                        "quotient = a / b",
                        "root = FSqrt(b)",
                        "absolute = FAbs(difference)",
                        "truncated = FTrunc(difference)",
                        "floored = FFloor(difference)",
                        "ceiled = FCeil(difference)",
                        "rounded = FRound(difference)",
                        "fractional = FFrac(difference)",
                        "modulus = FMod(a,b)",
                        "hypotenuse = FHypot(a,b)",
                        "power = FPow(a,b)",
                        "sine = FSin(a)",
                        "cosine = FCos(a)",
                        "tangent = FTan(a)",
                        "arctangent = FATan(a)",
                        "arctangent2 = FATan2(a,b)",
                        "arcsine = FASin(a)",
                        "arccosine = FACos(a)",
                        "secant = FSec(a)",
                        "cosecant = FCsc(a)",
                        "cotangent = FCot(a)",
                        "arcsecant = FASec(b)",
                        "arccosecant = FACsc(b)",
                        "exponential = FExp(a)",
                        "logarithm = FLn(a)",
                        "logarithm2 = FLog2(a)",
                        "logarithm10 = FLog10(a)",
                        "minimum = FMin(a,b)",
                        "maximum = FMax(a,b)",
                        "fromint = REAL(n)",
                        "IF sum > a THEN",
                        "PrintRE(sum)",
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "RT_F_ADD",
                "RT_F_SUB",
                "RT_F_MUL",
                "RT_F_DIV",
                "RT_F_SQRT",
                "RT_F_ABS",
                "RT_F_TRUNC",
                "RT_F_FLOOR",
                "RT_F_CEIL",
                "RT_F_ROUND",
                "RT_F_FRAC",
                "RT_F_MOD",
                "RT_F_HYPOT",
                "RT_F_POW",
                "RT_F_SIN",
                "RT_F_COS",
                "RT_F_TAN",
                "RT_F_ATAN",
                "RT_F_ATAN2",
                "RT_F_ASIN",
                "RT_F_ACOS",
                "RT_F_SEC",
                "RT_F_CSC",
                "RT_F_COT",
                "RT_F_ASEC",
                "RT_F_ACSC",
                "RT_F_EXP",
                "RT_F_LN",
                "RT_F_LOG2",
                "RT_F_LOG10",
                "RT_F_MIN",
                "RT_F_MAX",
                "RT_I_TO_F",
                "RT_F_CMP",
                "RT_PRINT_F",
            ):
                self.assertIn(f"\nu {symbol}\n", obj_text)
            self.assertNotIn("\nu RT_F_TO_I\n", obj_text)
            self.assertIn("x MAIN_A_B0", obj_text)
            self.assertIn("x MAIN___REAL_TEMP_", obj_text)
            self.run_tool(project, "alink", "main")

            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for symbol in (
                "RT_F_ADD",
                "RT_F_SUB",
                "RT_F_MUL",
                "RT_F_DIV",
                "RT_F_SQRT",
                "RT_F_ABS",
                "RT_F_TRUNC",
                "RT_F_FLOOR",
                "RT_F_CEIL",
                "RT_F_ROUND",
                "RT_F_FRAC",
                "RT_F_MOD",
                "RT_F_HYPOT",
                "RT_F_POW",
                "RT_F_SIN",
                "RT_F_COS",
                "RT_F_TAN",
                "RT_F_ATAN",
                "RT_F_ATAN2",
                "RT_F_ASIN",
                "RT_F_ACOS",
                "RT_F_SEC",
                "RT_F_CSC",
                "RT_F_COT",
                "RT_F_ASEC",
                "RT_F_ACSC",
                "RT_F_MIN",
                "RT_F_MAX",
                "RT_I_TO_F",
                "RT_F_CMP",
                "RT_PRINT_F",
            ):
                self.assertIn(symbol, debug)
            self.assertNotIn("RT_S_TO_F", debug)

    def test_actc_angle_intrinsics_fold_and_select_only_the_dynamic_sibling(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in (
                "rt_f_deg_to_rad.obj",
                "rt_f_rad_to_deg.obj",
                "rt_f_mul.obj",
                "rt_f_special.obj",
            ):
                (shared_lib / name.upper()).write_text(
                    (
                        self.root / "src" / "runtime" / "modules" / name
                    ).read_text(encoding="ascii"),
                    encoding="ascii",
                )

            self.run_tool(root, "actnew", "folded")
            folded_project = root / "FOLDED"
            (folded_project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n"
                "REAL radians=[DegToRad(180.0)]\n"
                "REAL degrees=[RadToDeg(3.14159265358979323846)]\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )
            self.run_tool(folded_project, "actc", "main")
            folded_object = (
                folded_project / "OBJ" / "MAIN.OBJ"
            ).read_text(encoding="ascii")
            self.assertNotIn("\nu RT_F_DEG_TO_RAD\n", folded_object)
            self.assertNotIn("\nu RT_F_RAD_TO_DEG\n", folded_object)
            self.assertIn("DB0F4940", folded_object)
            self.assertIn("00003443", folded_object)

            for project_name, call, expected, absent in (
                (
                    "dynamicdeg",
                    "DegToRad",
                    "RT_F_DEG_TO_RAD",
                    "RT_F_RAD_TO_DEG",
                ),
                (
                    "dynamicrad",
                    "RadToDeg",
                    "RT_F_RAD_TO_DEG",
                    "RT_F_DEG_TO_RAD",
                ),
            ):
                with self.subTest(call=call):
                    self.run_tool(root, "actnew", project_name)
                    project = root / project_name.upper()
                    (project / "SRC" / "MAIN.ACT").write_text(
                        "PROC MAIN()\n"
                        "REAL source=[180.0],result\n"
                        f"result={call}(source)\n"
                        "RETURN\n"
                        "ENDPROC\n",
                        encoding="ascii",
                    )
                    self.run_tool(project, "actc", "main")
                    object_text = (
                        project / "OBJ" / "MAIN.OBJ"
                    ).read_text(encoding="ascii")
                    self.assertIn(f"\nu {expected}\n", object_text)
                    self.assertNotIn(f"\nu {absent}\n", object_text)
                    self.run_tool(project, "alink", "main")
                    debug = (
                        project / "BIN" / "MAIN.DBG"
                    ).read_text(encoding="ascii")
                    self.assertIn(expected, debug)
                    self.assertNotIn(absent, debug)
                    self.assertIn("RT_F_MUL", debug)
                    self.assertIn("RT_F_SPECIAL", debug)

    def test_actc_constant_real_expression_and_condition_fold_without_math_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "RT_PRINT_F.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_f.obj").read_text(
                    encoding="ascii"
                ),
                encoding="ascii",
            )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "REAL x=[(1.5 + 2.25) * 2]",
                        "REAL rounded=[(16777216.0 + 1.0) - 16777216.0]",
                        "REAL overflow=[3.4028234663852886E38 * 2.0]",
                        "REAL invalid=[0.0 / 0.0]",
                        "REAL literalinf=[INF]",
                        "REAL literalnan=[NAN]",
                        "REAL truncated=[FTrunc(-1.75)]",
                        "REAL floored=[FFloor(-1.25)]",
                        "REAL ceiled=[FCeil(1.25)]",
                        "REAL callrounded=[FRound(2.5)]",
                        "REAL callfraction=[FFrac(-1.75)]",
                        "REAL callmod=[FMod(7.5,2.0)]",
                        "REAL callmodinf=[FMod(-1.75,INF)]",
                        "REAL callhypot=[FHypot(3.0,4.0)]",
                        "REAL callhypotsub=[FHypot(1.401298464324817E-45,0.0)]",
                        "REAL callhypotlarge=[FHypot(3.0E38,3.0E38)]",
                        "REAL callhypottiny=[FHypot(1.401298464324817E-45,1.401298464324817E-45)]",
                        "REAL callhypotinfnan=[FHypot(INF,NAN)]",
                        "REAL callhypotnaninf=[FHypot(NAN,INF)]",
                        "REAL callhypotnanfinite=[FHypot(NAN,3.0)]",
                        "REAL callhypotfinitenan=[FHypot(3.0,NAN)]",
                        "REAL callhypotnegzero=[FHypot(-0.0,0.0)]",
                        "REAL callminleftzero=[FMin(0.0,-0.0)]",
                        "REAL callminleftnegzero=[FMin(-0.0,0.0)]",
                        "REAL callmaxleftzero=[FMax(0.0,-0.0)]",
                        "REAL callmaxleftnegzero=[FMax(-0.0,0.0)]",
                        "REAL callminleftnan=[FMin(NAN,-2.0)]",
                        "REAL callmaxrightnan=[FMax(2.0,NAN)]",
                        "IF 1.0 < 2.0 THEN",
                        "PrintRE(x)",
                        "FI",
                        "IF NAN = NAN THEN",
                        'PrintE("BAD")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_PRINT_F\n", obj_text)
            for symbol in (
                "RT_F_ADD",
                "RT_F_MUL",
                "RT_F_CMP",
                "RT_F_TRUNC",
                "RT_F_FLOOR",
                "RT_F_CEIL",
                "RT_F_ROUND",
                "RT_F_FRAC",
                "RT_F_MOD",
                "RT_F_HYPOT",
                "RT_F_MIN",
                "RT_F_MAX",
            ):
                self.assertNotIn(f"\nu {symbol}\n", obj_text)
            lines = obj_text.splitlines()
            image = bytes.fromhex(
                "".join(line[2:].replace(" ", "") for line in lines if line.startswith("m "))
            )
            exports = {
                fields[1]: int(fields[2])
                for line in lines
                if line.startswith("x ") and len(fields := line.split()) >= 4
            }
            expected = {
                "MAIN_X_B0": bytes.fromhex("0000F040"),
                "MAIN_ROUNDED_B0": bytes.fromhex("00000000"),
                "MAIN_OVERFLOW_B0": bytes.fromhex("0000807F"),
                "MAIN_INVALID_B0": bytes.fromhex("0000C07F"),
                "MAIN_LITERALINF_B0": bytes.fromhex("0000807F"),
                "MAIN_LITERALNAN_B0": bytes.fromhex("0000C07F"),
                "MAIN_TRUNCATED_B0": bytes.fromhex("000080BF"),
                "MAIN_FLOORED_B0": bytes.fromhex("000000C0"),
                "MAIN_CEILED_B0": bytes.fromhex("00000040"),
                "MAIN_CALLROUNDED_B0": bytes.fromhex("00004040"),
                "MAIN_CALLFRACTION_B0": bytes.fromhex("000040BF"),
                "MAIN_CALLMOD_B0": bytes.fromhex("0000C03F"),
                "MAIN_CALLMODINF_B0": bytes.fromhex("0000E0BF"),
                "MAIN_CALLHYPOT_B0": bytes.fromhex("0000A040"),
                "MAIN_CALLHYPOTSUB_B0": bytes.fromhex("01000000"),
                "MAIN_CALLHYPOTLARGE_B0": bytes.fromhex("0000807F"),
                "MAIN_CALLHYPOTTINY_B0": bytes.fromhex("01000000"),
                "MAIN_CALLHYPOTINFNAN_B0": bytes.fromhex("0000807F"),
                "MAIN_CALLHYPOTNANINF_B0": bytes.fromhex("0000807F"),
                "MAIN_CALLHYPOTNANFINITE_B0": bytes.fromhex("B6C38740"),
                "MAIN_CALLHYPOTFINITENAN_B0": bytes.fromhex("B6C38740"),
                "MAIN_CALLHYPOTNEGZERO_B0": bytes.fromhex("00000000"),
                "MAIN_CALLMINLEFTZERO_B0": bytes.fromhex("00000000"),
                "MAIN_CALLMINLEFTNEGZERO_B0": bytes.fromhex("00000080"),
                "MAIN_CALLMAXLEFTZERO_B0": bytes.fromhex("00000000"),
                "MAIN_CALLMAXLEFTNEGZERO_B0": bytes.fromhex("00000080"),
                "MAIN_CALLMINLEFTNAN_B0": bytes.fromhex("000000C0"),
                "MAIN_CALLMAXRIGHTNAN_B0": bytes.fromhex("00000040"),
            }
            for symbol, value in expected.items():
                offset = exports[symbol]
                self.assertEqual(image[offset : offset + 4], value, msg=symbol)
            self.run_tool(project, "alink", "main")

    def test_actc_int_signed_comparison_and_real_bridges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in ("rt_s_to_f.obj", "rt_f_to_i.obj"):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "INT signed=[-7],converted",
                        "REAL source=[3.75],fromsigned",
                        "fromsigned = REAL(signed)",
                        "converted = INT(source)",
                        "IF signed < 0 THEN",
                        'PrintE("NEG")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_S_TO_F\n", obj_text)
            self.assertIn("\nu RT_F_TO_I\n", obj_text)
            self.assertIn("49808502", obj_text)
            self.assertIn("F9FF", obj_text)
            self.run_tool(project, "alink", "main")

            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("RT_S_TO_F", debug)
            self.assertIn("RT_F_TO_I", debug)

    def test_actc_rejects_unknown_external_call_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nUnknownHelper(5,2,65)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            result = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertEqual(result.stderr, "UNSUPPORTED CALL ARGS LINE 2: UNKNOWNHELPER\n")
            self.assertFalse((project / "OBJ" / "MAIN.OBJ").exists())

    def test_gfx_cell_calls_lower_arguments_and_link_standalone_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in ("rt_gfx_screen_cell.obj", "rt_gfx_color_cell.obj"):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC ScreenCell(BYTE x,y,ch)\n"
                "PROC ColorCell(BYTE x,y,color)\n"
                "PROC MAIN()\n"
                "ScreenCell(0,0,'A)\n"
                "ColorCell(0,0,1)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_GFX_SCREEN_CELL\n", obj_text)
            self.assertIn("\nu RT_GFX_COLOR_CELL\n", obj_text)
            self.assertIn("MAIN_EXPR_", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes.fromhex("85048405A9008502A9048503"), prg)
            self.assertIn(bytes.fromhex("850498290F8505A9008502A9D8"), prg)
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("RT_GFX_SCREEN_CELL", debug)
            self.assertIn("RT_GFX_COLOR_CELL", debug)

    def test_complete_gfx1_procedure_family_is_link_selectable(self) -> None:
        runtime_names = (
            "rt_gfx_vic_bank.obj",
            "rt_gfx_bgcolor.obj",
            "rt_gfx_bordercolor.obj",
            "rt_gfx_screen_base.obj",
            "rt_gfx_bitmap_base.obj",
            "rt_gfx_screen_cell.obj",
            "rt_gfx_color_cell.obj",
            "rt_gfx_screen_copy.obj",
            "rt_gfx_color_copy.obj",
            "rt_gfx_bitmap_fill.obj",
            "rt_gfx_bitmap_copy.obj",
            "rt_gfx_bitmap_on.obj",
            "rt_gfx_bitmap_off.obj",
            "rt_gfx_mbitmap_on.obj",
            "rt_gfx_mbitmap_off.obj",
        )
        source_lines = (
            "VicBank(1)",
            "BgColor(6)",
            "BorderColor(14)",
            "ScreenBase($0400)",
            "BitmapBase($2000)",
            "ScreenCell(5,2,65)",
            "ColorCell(5,2,10)",
            "ScreenCopy($3000)",
            "ColorCopy($3400)",
            "BitmapFill(0)",
            "BitmapCopy($4000)",
            "BitmapOn()",
            "BitmapOff()",
            "MBitmapOn()",
            "MBitmapOff()",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in runtime_names:
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n" + "\n".join(source_lines) + "\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for name in runtime_names:
                symbol = name.removesuffix(".obj").upper()
                self.assertIn(f"\nu {symbol}\n", obj_text)
            self.run_tool(project, "alink", "main")

            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for name in runtime_names:
                self.assertIn(name.removesuffix(".obj").upper(), debug)

    def test_input1_demo_lowers_byte_function_results_and_transitive_state(self) -> None:
        runtime_names = (
            "rt_joy.obj",
            "rt_js.obj",
            "rt_jp.obj",
            "rt_jb1.obj",
            "rt_jb2.obj",
            "rt_ms.obj",
            "rt_mp.obj",
            "rt_mseen.obj",
            "rt_mx.obj",
            "rt_my.obj",
            "rt_mb.obj",
            "rt_mb1.obj",
            "rt_mb2.obj",
        )
        direct_helpers = (
            "RT_JOY",
            "RT_JP",
            "RT_JB1",
            "RT_JB2",
            "RT_MP",
            "RT_MSEEN",
            "RT_MX",
            "RT_MY",
            "RT_MB",
            "RT_MB1",
            "RT_MB2",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in runtime_names:
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                (self.root / "examples" / "input1_demo.act").read_text(encoding="ascii"),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for helper in direct_helpers:
                self.assertIn(f"\nu {helper}\n", obj_text)
            self.assertNotIn("\nu RT_JS\n", obj_text)
            self.assertNotIn("\nu RT_MS\n", obj_text)
            self.assertIn("A200", obj_text)
            self.run_tool(project, "alink", "main")

            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for name in runtime_names:
                self.assertIn(name.removesuffix(".obj").upper(), debug)
            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes.fromhex("AD19D4"), prg)
            self.assertIn(bytes.fromhex("AD1AD4"), prg)

    def test_complete_sidspr1_family_uses_register_and_carry_abis(self) -> None:
        runtime_names = tuple(
            sorted(
                path.name
                for pattern in ("rt_sid_*.obj", "rt_sprite_*.obj")
                for path in (self.root / "src" / "runtime" / "modules").glob(pattern)
            )
        )
        source_lines = (
            "BYTE hit,hitbg,osc,env",
            "PROC MAIN()",
            "hit=SpriteHit()",
            "hitbg=SpriteHitBg()",
            "osc=SidOsc3()",
            "env=SidEnv3()",
            "SpriteOn(1)",
            "SpriteOff(1)",
            "SpritePos(1,$0101,50)",
            "SpritePtr(1,128)",
            "SpriteData(1,$2000)",
            "SpriteColor(1,10)",
            "SpriteMC(1,1)",
            "SpriteXExp(1,1)",
            "SpriteYExp(1,1)",
            "SpritePrio(1,SPR_BACK)",
            "SetSpriteMC(5,7)",
            "SidFreq(1,$1234)",
            "SidPulse(1,$0800)",
            "SidWave(1,SID_TRI+SID_SAW)",
            "SidAD(1,$24)",
            "SidSR(1,$A8)",
            "SidOn(1)",
            "SidOff(1)",
            "SidVol(15)",
            "SidCutoff($345)",
            "SidRes(8)",
            "SidMode(SID_LOW+SID_HIGH)",
            "SidRoute(3)",
            "SidRst()",
            "RETURN",
            "ENDPROC",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in runtime_names:
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE MAIN\n" + "\n".join(source_lines) + "\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_SPRITE_POS\n", obj_text)
            self.assertIn("\nu RT_SID_RST\n", obj_text)
            self.assertNotIn("\nu RT_SID_STATE\n", obj_text)
            self.assertIn("4AAD", obj_text)
            self.run_tool(project, "alink", "main")

            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for name in runtime_names:
                self.assertIn(name.removesuffix(".obj").upper(), debug)
            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes.fromhex("AD1ED060"), prg)
            self.assertIn(bytes.fromhex("A900A2189D00D4"), prg)

    def test_shipped_simple_examples_compile_and_link_on_linux(self) -> None:
        for example in ("hello.act", "if.act", "math.act"):
            with self.subTest(example=example), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shared_lib = root / "LIB"
                shared_lib.mkdir()
                (shared_lib / "RT_PRINT_I.OBJ").write_text(
                    (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    (self.root / "examples" / example).read_text(encoding="ascii"),
                    encoding="ascii",
                )

                self.run_tool(project, "actc", "main")
                self.run_tool(project, "alink", "main")
                self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 3)

    def test_shipped_examples_indent_every_routine_body(self) -> None:
        routine_start = re.compile(
            r"^(?:PROC\s+|OVERLAY\s+|(?:BYTE|CARD|INT|REAL)\s+FUNC\s+)",
            re.IGNORECASE,
        )
        routine_end = re.compile(
            r"^(?:ENDPROC|ENDFUNC|ENDOVERLAY)$", re.IGNORECASE
        )
        for source in sorted((self.root / "examples").glob("*.act")):
            inside_routine = False
            for line_number, line in enumerate(
                source.read_text(encoding="ascii").splitlines(), start=1
            ):
                stripped = line.strip()
                if routine_start.match(line):
                    self.assertFalse(
                        line.startswith((" ", "\t")),
                        f"{source.name}:{line_number}: routine declaration is indented",
                    )
                    inside_routine = True
                    continue
                if routine_end.fullmatch(stripped):
                    self.assertFalse(
                        line.startswith((" ", "\t")),
                        f"{source.name}:{line_number}: routine terminator is indented",
                    )
                    inside_routine = False
                    continue
                if inside_routine and stripped and not stripped.startswith(";"):
                    self.assertTrue(
                        line.startswith("    "),
                        f"{source.name}:{line_number}: routine body is not indented",
                    )
            self.assertFalse(
                inside_routine,
                f"{source.name}: final routine has no explicit terminator",
            )

    def test_shipped_real_examples_compile_and_link_on_linux(self) -> None:
        runtime_names = (
            "rt_f_abs.obj",
            "rt_f_add.obj",
            "rt_f_cmp.obj",
            "rt_f_clamp.obj",
            "rt_f_div.obj",
            "rt_f_mul.obj",
            "rt_f_sign.obj",
            "rt_f_sqrt.obj",
            "rt_f_sub.obj",
            "rt_f_trunc.obj",
            "rt_f_to_i.obj",
            "rt_i_to_f.obj",
            "rt_print_f.obj",
            "rt_s_to_f.obj",
        )
        for example in (
            "real_demo.act",
            "real_math.act",
            "real_cmp.act",
            "math1_demo.act",
        ):
            with self.subTest(example=example), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shared_lib = root / "LIB"
                shared_lib.mkdir()
                for name in runtime_names:
                    (shared_lib / name.upper()).write_text(
                        (self.root / "src" / "runtime" / "modules" / name).read_text(
                            encoding="ascii"
                        ),
                        encoding="ascii",
                    )
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    (self.root / "examples" / example).read_text(encoding="ascii"),
                    encoding="ascii",
                )

                self.run_tool(project, "actc", "main")
                self.run_tool(project, "alink", "main")
                self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 3)

    def test_prime_and_reu_dbf_sort_examples_compile_and_link(self) -> None:
        expectations = {
            "prime_real.act": {
                "RT_F_SQRT",
                "RT_I_TO_F",
                "RT_F_TO_I",
                "RT_I_MOD",
                "RT_PRINT_I",
            },
            "reu_dbf_sort.act": {
                "RT_DBF_OPEN",
                "RT_DBF_READBYTE",
                "RT_DBF_WRITEBYTE",
                "RT_DBF_SAVE",
                "RT_REU_ALLOC",
                "RT_REU_PEEK8",
                "RT_REU_POKE8",
            },
        }
        for example, imports in expectations.items():
            with self.subTest(example=example), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    (self.root / "examples" / example).read_text(encoding="ascii"),
                    encoding="ascii",
                )

                self.run_tool(project, "actc", "main")
                obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
                for symbol in imports:
                    self.assertIn(f"\nu {symbol}\n", obj_text)
                self.run_tool(project, "alink", "main")
                self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 3)
                if example == "reu_dbf_sort.act":
                    source = (self.root / "examples" / example).read_text(
                        encoding="ascii"
                    )
                    self.assertIn(
                        "PROC main(CARD argc,CARD ARRAY argv)", source
                    )
                    self.assertIn("IF argc>12 THEN", source)
                    self.assertIn("arguments(keyIndex+2)", source)
                    self.assertIn("BYTE keyCount", source)
                    self.assertNotIn("primaryKey", source)
                    self.assertNotIn("secondaryKey", source)

    def test_shipped_asmblock_example_compiles_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj")
                .read_text(encoding="ascii"),
                encoding="ascii",
            )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                (self.root / "examples" / "asmblock_demo.act").read_text(
                    encoding="ascii"
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("18690160", obj_text)
            self.assertRegex(obj_text, r"(?m)^r \d+ x COUNTCOLOR_AMOUNT_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x DOUBLEVALUE_VALUE_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x DOUBLEVALUE_RESULT_LO$")
            self.assertRegex(
                obj_text, r"(?m)^x MAIN_COUNTCOLOR_ASM_DELAY_\d+ \d+ 1$"
            )
            self.run_tool(project, "alink", "main")

    def test_alink_loads_external_object_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nHELPER()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )
            (project / "OBJ" / "HELPER.OBJ").write_text(
                "OBJ1\nx HELPER 0 1\nb M\nm 60\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertEqual(
                prg,
                bytes([0x00, 0x10, 0x4C, 0x03, 0x10, 0x20, 0x07, 0x10, 0x60, 0x60]),
            )

    def test_alink_accepts_native_compact_byte_relocations_with_addends(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "OBJ1\n"
                "x MAIN 0 5\n"
                "b u0M\n"
                "u HELPER\n"
                "m A900A20060\n"
                "r 1 l u0 1\n"
                "r 3 h u0 -1\n",
                encoding="ascii",
            )
            (project / "OBJ" / "HELPER.OBJ").write_text(
                "OBJ1\nx HELPER 0 1\nb M\nm 60\n",
                encoding="ascii",
            )

            self.run_tool(project, "alink", "main")

            self.assertEqual(
                (project / "BIN" / "MAIN.PRG").read_bytes(),
                bytes([0x00, 0x10, 0xA9, 0x06, 0xA2, 0x10, 0x60, 0x60]),
            )

    def test_alink_discovers_export_in_differently_named_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nHELPER()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )
            (project / "OBJ" / "UTIL.OBJ").write_text(
                "OBJ1\nx HELPER 0 1\nb M\nm 60\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertEqual(
                prg,
                bytes([0x00, 0x10, 0x4C, 0x03, 0x10, 0x20, 0x07, 0x10, 0x60, 0x60]),
            )
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("m 1 UTIL\n", debug)

    def test_alink_rejects_ambiguous_scanned_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "OBJ1\nx MAIN 0 4\nb u0M\nu HELPER\nm 20000060\nr 1 u0\n",
                encoding="ascii",
            )
            for module in ("FIRST", "SECOND"):
                (project / "OBJ" / f"{module}.OBJ").write_text(
                    "OBJ1\nx HELPER 0 1\nb M\nm 60\n",
                    encoding="ascii",
                )

            result = self.run_tool(project, "alink", "main", expected_status=1)
            self.assertEqual(result.stderr, "DUPLICATE EXPORT HELPER\n")
            self.assertFalse((project / "BIN" / "MAIN.PRG").exists())

    def test_alink_strictly_validates_obj1_records(self) -> None:
        cases = {
            "compact_body": (
                "OBJ1\nx MAIN 0 1\nb s0i0r\nm 60\n",
                "UNSUPPORTED OBJECT BODY\n",
            ),
            "bad_body_import": (
                "OBJ1\nx MAIN 0 1\nb u1M\nu HELPER\nm 60\n",
                "BAD OBJECT\n",
            ),
            "bad_relocation": (
                "OBJ1\nx MAIN 0 2\nb M\nm 0000\nr 0 x\n",
                "BAD OBJECT\n",
            ),
            "unknown_record": (
                "OBJ1\nx MAIN 0 1\nb M\nq ignored\nm 60\n",
                "BAD OBJECT\n",
            ),
        }
        for name, (object_text, expected_error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "OBJ" / "MAIN.OBJ").write_text(
                    object_text,
                    encoding="ascii",
                )

                result = self.run_tool(project, "alink", "main", expected_status=1)
                self.assertEqual(result.stderr, expected_error)
                self.assertFalse((project / "BIN" / "MAIN.PRG").exists())

    def test_alink_rejects_legacy_placeholder_runtime_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            name = "rt_print_line.obj"
            (project / "LIB" / name.upper()).write_text(
                (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "OBJ1\nx MAIN 0 4\nb u0M\nu RT.PRINT_LINE\nm 20000060\nr 1 u0\n",
                encoding="ascii",
            )

            result = self.run_tool(project, "alink", "main", expected_status=1)
            self.assertEqual(result.stderr, "PLACEHOLDER OBJECT RT.PRINT_LINE\n")
            self.assertFalse((project / "BIN" / "MAIN.PRG").exists())

    def test_alink_rejects_duplicate_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "OBJ1\nx MAIN 0 4\nb u0M\nu HELPER\nm 20000060\nr 1 u0\n",
                encoding="ascii",
            )
            (project / "OBJ" / "HELPER.OBJ").write_text(
                "OBJ1\nx HELPER 0 1\nx MAIN 0 1\nb M\nm 60\n",
                encoding="ascii",
            )

            result = self.run_tool(project, "alink", "main", expected_status=1)
            self.assertEqual(result.stderr, "DUPLICATE EXPORT MAIN\n")
            self.assertFalse((project / "BIN" / "MAIN.PRG").exists())

    def test_alink_rejects_out_of_range_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "OBJ1\nx MAIN 1 1\nb M\nm 60\n",
                encoding="ascii",
            )

            result = self.run_tool(project, "alink", "main", expected_status=1)
            self.assertEqual(result.stderr, "BAD OBJECT\n")
            self.assertFalse((project / "BIN" / "MAIN.PRG").exists())

    def test_alink_loads_standalone_real_runtime_family_and_closure(self) -> None:
        generated = subprocess.run(
            ["python3", str(self.root / "tools" / "generate_real_runtime.py"), "--check"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(generated.returncode, 0, msg=generated.stdout + generated.stderr)

        runtime_names = (
            "rt_f_abs.obj",
            "rt_f_add.obj",
            "rt_f_cmp.obj",
            "rt_f_clamp.obj",
            "rt_f_div.obj",
            "rt_f_max.obj",
            "rt_f_min.obj",
            "rt_f_mul.obj",
            "rt_f_sign.obj",
            "rt_f_sqrt.obj",
            "rt_f_sub.obj",
            "rt_f_trunc.obj",
            "rt_f_to_i.obj",
            "rt_i_to_f.obj",
            "rt_print_f.obj",
            "rt_s_to_f.obj",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            for name in runtime_names:
                (project / "LIB" / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )

            symbols = [name.removesuffix(".obj").upper() for name in runtime_names]
            code = bytearray()
            relocations = []
            for index in range(len(symbols)):
                code.extend((0x20, 0x00, 0x00))
                relocations.append(f"r {len(code) - 2} u{index}")
            code.append(0x60)
            object_lines = [
                "OBJ1",
                f"x MAIN 0 {len(code)}",
                "b " + "".join(f"u{i}" for i in range(len(symbols))) + "M",
                *(f"u {symbol}" for symbol in symbols),
                "m " + code.hex().upper(),
                *relocations,
                "",
            ]
            (project / "OBJ" / "MAIN.OBJ").write_text(
                "\n".join(object_lines), encoding="ascii"
            )

            self.run_tool(project, "alink", "main")
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for symbol in symbols:
                self.assertIn(symbol, debug)
            self.assertEqual(debug.count("RT_S_TO_F"), 1)
            self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 2000)

    def test_reu_source_calls_link_direct_hardware_runtime_without_udos(self) -> None:
        generated = subprocess.run(
            ["python3", str(self.root / "tools" / "generate_reu_runtime.py"), "--check"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(generated.returncode, 0, msg=generated.stdout + generated.stderr)

        runtime_names = (
            "rt_reu_alloc.obj",
            "rt_reu_state.obj",
            "rt_reu_resolve.obj",
            "rt_reu_transfer.obj",
            "rt_reu_peek8.obj",
            "rt_reu_peek16.obj",
            "rt_reu_poke8.obj",
            "rt_reu_poke16.obj",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            for name in runtime_names:
                (project / "LIB" / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE main\n"
                "REU BYTE ARRAY global(50000)\n"
                "BYTE value\n"
                "PROC main()\n"
                "REU BYTE ARRAY local(32)\n"
                "ReuPoke8(global,0,65)\n"
                "ReuPoke16(local,2,$1234)\n"
                "value=ReuPeek8(global,0)+1\n"
                "IF ReuPeek16(local,2)=$1234 THEN\n"
                'PrintE("reu ok")\n'
                "FI\n"
                "RETURN\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "RT_REU_ALLOC",
                "RT_REU_PEEK8",
                "RT_REU_PEEK16",
                "RT_REU_POKE8",
                "RT_REU_POKE16",
            ):
                self.assertIn(f"\nu {symbol}\n", obj_text)
            self.assertIn("850E", obj_text)

            self.run_tool(project, "alink", "main")
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for module in (
                "RT_REU_STATE",
                "RT_REU_RESOLVE",
                "RT_REU_TRANSFER",
            ):
                self.assertIn(module, debug)
            self.assertNotIn("UDOS", debug)
            self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 1800)

    def test_actc_rejects_invalid_reu_array_sizes(self) -> None:
        cases = (
            ("REU BYTE ARRAY big(0)", "REU SIZE RANGE LINE 2: BIG\n"),
            ("REU BYTE ARRAY big(65536)", "REU SIZE RANGE LINE 2: BIG\n"),
            (
                "BYTE size\nREU BYTE ARRAY big(size)",
                "REU SIZE MUST BE CONSTANT LINE 3\n",
            ),
        )
        for declaration, expected_error in cases:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(
                    "MODULE main\n"
                    + declaration
                    + "\nPROC main()\nRETURN\n",
                    encoding="ascii",
                )
                result = self.run_tool(project, "actc", "main", expected_status=1)
                self.assertEqual(result.stderr, expected_error)

    def test_shipped_overlay_is_linked_as_program_owned_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                (self.root / "examples" / "ovl_demo.act").read_text(encoding="ascii"),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertRegex(obj_text, r"(?m)^x MAIN 0 ")
            self.assertRegex(obj_text, r"(?m)^x MATH [1-9][0-9]* ")
            self.assertNotIn("RT_OVL_", obj_text)

            self.run_tool(project, "alink", "main")
            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertEqual(prg[:2], bytes([0x00, 0x10]))
            self.assertIn(bytes([0xA9, ord("4"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("2"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_rejects_unknown_program_owned_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE main\n"
                "PROC main()\n"
                "OverlayCall(Missing)\n"
                "RETURN\n",
                encoding="ascii",
            )

            result = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertEqual(result.stderr, "UNKNOWN OVERLAY LINE 3: MISSING\n")

    def test_dbf_family_links_reu_and_kernal_adapters_without_udos_calls(self) -> None:
        generated = subprocess.run(
            ["python3", str(self.root / "tools" / "generate_dbf_runtime.py"), "--check"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(generated.returncode, 0, msg=generated.stdout + generated.stderr)

        runtime_dir = self.root / "src" / "runtime" / "modules"
        for path in runtime_dir.glob("rt_dbf_*.obj"):
            text = path.read_text(encoding="ascii").replace(" ", "")
            for address in ("2DCF", "30CF", "33CF", "36CF", "39CF", "3CCF"):
                self.assertNotIn("20" + address, text, msg=path.name)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            for source in runtime_dir.glob("rt_dbf_*.obj"):
                (project / "LIB" / source.name.upper()).write_text(
                    source.read_text(encoding="ascii"),
                    encoding="ascii",
                )
            for name in (
                "rt_reu_alloc.obj",
                "rt_reu_state.obj",
                "rt_reu_resolve.obj",
                "rt_reu_transfer.obj",
                "rt_reu_peek8.obj",
                "rt_reu_poke8.obj",
            ):
                (project / "LIB" / name.upper()).write_text(
                    (runtime_dir / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )
            (project / "SRC" / "MAIN.ACT").write_text(
                "MODULE main\n"
                "CARD filename\n"
                "BYTE handle\n"
                "BYTE result\n"
                "PROC main()\n"
                "filename=$3000\n"
                "handle=DbfCreate(filename)\n"
                "handle=DbfOpen(filename)\n"
                "result=DbfGo(handle,2)\n"
                "result=DbfFieldCount(handle)\n"
                "result=DbfFieldLen(handle,1)\n"
                "result=DbfReadByte(handle,0)\n"
                "result=DbfReadFieldByte(handle,1,0)\n"
                "result=DbfWriteFieldByte(handle,1,0,65)\n"
                "result=DbfWriteByte(handle,0,65)\n"
                "result=DbfAppend(handle)\n"
                "result=DbfPack(handle)\n"
                "result=DbfSave(handle)\n"
                "result=DbfDelete(handle)\n"
                "result=DbfUndelete(handle)\n"
                "result=DbfDeleted(handle)\n"
                "result=DbfHeaderLen(handle)\n"
                "result=DbfRecordLen(handle)\n"
                "result=DbfTotalRecs(handle)\n"
                "result=DbfCurrRecNo(handle)\n"
                "DbfClose(handle)\n"
                "RETURN\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "RT_DBF_CREATE",
                "RT_DBF_OPEN",
                "RT_DBF_WRITEFIELDBYTE",
                "RT_DBF_PACK",
                "RT_DBF_SAVE",
                "RT_DBF_CLOSE",
            ):
                self.assertIn(f"\nu {symbol}\n", obj_text)
            self.assertIn("85E0", obj_text)
            self.assertGreaterEqual(
                obj_text.count("087820000028"),
                20,
                "every DBF call must protect its zero-page scratch",
            )

            self.run_tool(project, "alink", "main")
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            for module in (
                "RT_DBF_STATE",
                "RT_DBF_ADAPTER_STATE",
                "RT_DBF_ENSURE_REU",
                "RT_DBF_FILE_LOAD_REU",
                "RT_DBF_RAW_REU_READ",
                "RT_DBF_RAW_REU_WRITE",
                "RT_DBF_FILE_OPEN_WRITE",
                "RT_DBF_FILE_WRITE_BYTE",
                "RT_DBF_FILE_CLOSE",
                "RT_REU_ALLOC",
                "RT_REU_TRANSFER",
            ):
                self.assertIn(module, debug)
            self.assertNotIn("UDOS", debug)
            self.assertGreater((project / "BIN" / "MAIN.PRG").stat().st_size, 3000)

            (project / "SRC" / "MAIN.ACT").write_text(
                (self.root / "examples" / "dbf1_demo.act").read_text(encoding="ascii"),
                encoding="ascii",
            )
            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")
            shipped_debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("RT_DBF_OPEN", shipped_debug)
            self.assertIn("RT_DBF_FILE_LOAD_REU", shipped_debug)
            self.assertNotIn("UDOS", shipped_debug)

    def test_actc_emits_printe_without_runtime_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'PROC MAIN()\nPrintE("HI")\nRETURN\nENDPROC\n',
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("\nu PRINTE\n", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertEqual(prg[:2], bytes([0x00, 0x10]))
            self.assertIn(bytes([0xA9, ord("H"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("I"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_emits_printie_for_constant_integer_expression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nPrintIE((2 + 3) * 4)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("\nu PRINTIE\n", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0xA9, ord("2"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("0"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_printie_variable_imports_helper_and_emits_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x\nx = 300\nPrintIE(x)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0xA9, 0x2C, 0xA2, 0x01]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_printie_simple_variable_addition_emits_native_adc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x\nx = 300\nPrintIE(x + 5)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.assertNotIn(bytes("305", "ascii").hex().upper(), obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0x18, 0x69, 0x05, 0x48, 0x8A, 0x69, 0x00, 0xAA, 0x68]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_assignment_from_variable_addition_stores_runtime_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x,y\nx = 300\ny = x + 5\nPrintIE(y)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("x MAIN_Y_LO", obj_text)
            self.assertIn("x MAIN_Y_HI", obj_text)
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0x18, 0x69, 0x05, 0x48, 0x8A, 0x69, 0x00, 0xAA, 0x68]), prg)
            self.assertIn(bytes([0x8D]), prg)
            self.assertIn(bytes([0x8E]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_assignment_from_two_variables_emits_native_adc_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x,y,z\nx = 300\ny = 7\nz = x + y\nPrintIE(z)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("x MAIN_Z_LO", obj_text)
            self.assertIn("x MAIN_Z_HI", obj_text)
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0x18, 0x6D]), prg)
            self.assertIn(bytes([0x48, 0x8A, 0x6D]), prg)
            self.assertIn(bytes([0xAA, 0x68, 0x8D]), prg)
            self.assertIn(bytes([0x8E]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_card_plus_byte_zero_extends_rhs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x,z\nBYTE y\nx = 300\ny = 7\nz = x + y\nPrintIE(z)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("x MAIN_Y_LO", obj_text)
            self.assertNotIn("x MAIN_Y_HI", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0x48, 0x8A, 0x69, 0x00, 0xAA, 0x68]), prg)
            self.assertIn(bytes([0xA9, 0x0D, 0x20, 0xD2, 0xFF]), prg)

    def test_actc_dynamic_expression_tree_selects_mul_and_div_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in ("rt_i_mul.obj", "rt_i_div.obj", "rt_print_i.obj"):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(encoding="ascii"),
                    encoding="ascii",
                )

            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD seed,a,b,result",
                        "seed = 6",
                        "a = seed + 0",
                        "b = a + 1",
                        "result = -((b + 3) * 4) / (a - 4)",
                        "PrintI(result)",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_I_MUL\n", obj_text)
            self.assertIn("\nu RT_I_DIV\n", obj_text)
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.assertIn("MAIN_EXPR_", obj_text)
            self.assertFalse((project / "LIB").exists())

            self.run_tool(project, "alink", "main")
            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes.fromhex("85E086E1A000B10285E2"), prg)
            self.assertIn(bytes.fromhex("85E086E1A000B10285E2C8B10285E305E2"), prg)
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("RT_I_MUL", debug)
            self.assertIn("RT_I_DIV", debug)
            self.assertIn("RT_PRINT_I", debug)

    def test_actc_action_integer_operator_family_compiles_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "RT_I_MOD.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_i_mod.obj").read_text(
                    encoding="ascii"
                ),
                encoding="ascii",
            )

            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n"
                "CARD divisor,mask,low,one,modresult,andresult,orresult,xorresult,shiftresult\n"
                "CHAR letter\n"
                "BYTE shorthand\n"
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
                "letter='Z\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_I_MOD\n", obj_text)
            self.assertNotIn("\nu RT_I_MUL\n", obj_text)
            self.assertNotIn("\nu RT_I_DIV\n", obj_text)
            self.run_tool(project, "alink", "main")
            self.assertTrue((project / "BIN" / "MAIN.PRG").is_file())
            self.assertIn(
                "RT_I_MOD",
                (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii"),
            )

    def test_actc_logical_conditions_short_circuit_and_preserve_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE probe\n"
                "BYTE FUNC Touch(BYTE value)\n"
                "probe==+1\n"
                "RETURN(value)\n"
                "PROC MAIN()\n"
                "BYTE a,result\n"
                "a=1\n"
                "result=0\n"
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
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("OR_RIGHT", obj_text)
            self.assertIn("OR_DONE", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_typed_constants_and_multiline_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
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
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for constant in ("OUTPUT_ADDR", "VALUE", "SHIFTED", "NEG", "SCALE"):
                self.assertNotIn(f"MAIN_{constant}_LO", obj_text)
            self.run_tool(project, "alink", "main")

            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE CONST TOO_BIG=256\nPROC MAIN()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )
            bad = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertIn("CONST RANGE LINE 1: TOO_BIG", bad.stderr)

    def test_actc_matches_native_integer_constant_parity_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            source = (self.root / "tests" / "parity" / "const_expr.act").read_text(
                encoding="ascii"
            )
            (project / "SRC" / "MAIN.ACT").write_text(source, encoding="ascii")

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            expected_data = (
                "0E00140010000001C100F6FFFEFF4234120200"
                "FFFFFFFF0080FFFF11"
            )
            self.assertIn(expected_data, obj_text)
            for constant in (
                "PRECEDENCE",
                "GROUPED",
                "DIVMOD",
                "SHIFT",
                "BITS",
                "SIGNED",
                "REMAINDER",
                "CHARACTER",
                "CHEX",
                "MIXED",
                "MASK",
                "WIDE",
                "HIGH",
                "NEGSHIFT",
                "BUTTONS",
            ):
                self.assertNotIn(f"MAIN_{constant}_LO", obj_text)

    def test_actc_matches_native_library_constant_header_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            source = (
                self.root / "tests" / "parity" / "library_const_headers.act"
            ).read_text(encoding="ascii")
            (project / "SRC" / "MAIN.ACT").write_text(source, encoding="ascii")

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("m 4C0000600F\n", obj_text)
            for constant in ("GFX_BLACK", "GFX_LIGHTGRAY", "MATH_PI", "MATH_SQRT2"):
                self.assertNotIn(f"MAIN_{constant}_LO", obj_text)

    def test_actc_define_and_nested_include_preprocess_library_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "BASE.ACT").write_text(
                "MODULE\nCARD CONST TARGET=$C140\n",
                encoding="ascii",
            )
            (shared_lib / "WRAP.ACT").write_text(
                'INCLUDE "base.act"\nDEFINE U8="BYTE",\n DOUBLE="LSH ONE", ONE=1\n',
                encoding="ascii",
            )
            (shared_lib / "INPUT1.ACT").write_text(
                (self.root / "lib" / "input1.act").read_text(encoding="ascii"),
                encoding="ascii",
            )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "wrap.act"\n'
                'INCLUDE "input1.act"\n'
                "SET $49A=1\n"
                "PROC MAIN()\n"
                "U8 seed,result=TARGET,done=$C141\n"
                "seed=3\n"
                "result=seed DOUBLE\n"
                "IF ONE THEN\n"
                "result==+1\n"
                "FI\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("\nx JOY ", obj_text)
            self.assertNotIn("\nx MOUSEBTN2 ", obj_text)
            self.run_tool(project, "alink", "main")

            (shared_lib / "A.ACT").write_text('INCLUDE "b.act"\n', encoding="ascii")
            (shared_lib / "B.ACT").write_text('INCLUDE "a.act"\n', encoding="ascii")
            (project / "SRC" / "MAIN.ACT").write_text(
                'INCLUDE "a.act"\nPROC MAIN()\nRETURN\nENDPROC\n',
                encoding="ascii",
            )
            cycle = self.run_tool(project, "actc", "main", expected_status=1)
            self.assertIn("INCLUDE CYCLE", cycle.stderr)

    def test_actc_directly_includes_every_shipped_library(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            library_names = []
            for source in sorted((self.root / "lib").glob("*.act")):
                destination = shared_lib / source.name.upper()
                destination.write_text(source.read_text(encoding="ascii"), encoding="ascii")
                library_names.append(source.name)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            includes = "".join(f'INCLUDE "{name}"\n' for name in library_names)
            (project / "SRC" / "MAIN.ACT").write_text(
                includes + "PROC MAIN()\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for declaration in (
                "JOY",
                "VICBANK",
                "DBFCREATE",
                "FABS",
                "FTRUNC",
                "FCEIL",
                "FROUND",
                "FFRAC",
                "FMOD",
                "FHYPOT",
                "SIDFREQ",
            ):
                self.assertNotIn(f"\nx {declaration} ", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_records_support_storage_addresses_and_pointer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "TYPE Pair=[BYTE tag\n"
                " CARD value\n"
                " INT delta], Other=[BYTE marker]\n"
                "Pair direct=$C150\n"
                "PROC MAIN()\n"
                "Pair stored\n"
                "Pair POINTER ptr\n"
                "Other extra\n"
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
                "extra.marker=ptr.tag\n"
                "direct.tag=ptr.tag\n"
                "direct.value=ptr.value\n"
                "direct.delta=ptr.delta\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            for symbol in (
                "MAIN_STORED_TAG_LO",
                "MAIN_STORED_VALUE_LO",
                "MAIN_STORED_VALUE_HI",
                "MAIN_STORED_DELTA_LO",
                "MAIN_STORED_DELTA_HI",
                "MAIN_PTR_LO",
                "MAIN_PTR_HI",
            ):
                self.assertIn(symbol, obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_initialized_array_sizes_and_record_parameters_match_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "TYPE Pair=[BYTE tag CARD value]\n"
                "PROC Adjust(BYTE amount, Pair POINTER item)\n"
                "item.tag==+amount\n"
                "item.value==+amount\n"
                "RETURN\n"
                "PROC Mark(Pair item)\n"
                "item.tag==+1\n"
                "RETURN\n"
                "PROC MAIN()\n"
                "BYTE ARRAY short(5)=[4 7 18]\n"
                "BYTE ARRAY bits(0)=[1 2 4 8 16 32 64 128]\n"
                "CARD ARRAY packed(0)=[$FFA2$A686]\n"
                "Pair value\n"
                "value.tag=short(0)\n"
                "value.value=bits(7)\n"
                "Adjust(2,value)\n"
                "Mark(value)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertRegex(obj_text, r"(?m)^x MAIN_SHORT_DATA \d+ 3$")
            self.assertRegex(obj_text, r"(?m)^x MAIN_BITS_DATA \d+ 8$")
            self.assertRegex(obj_text, r"(?m)^x MAIN_PACKED_DATA \d+ 4$")
            self.assertIn("A2FF86A6", obj_text)
            self.assertIn("x ADJUST_ITEM_LO", obj_text)
            self.assertIn("x ADJUST_ITEM_HI", obj_text)
            self.assertIn("x MARK_ITEM_LO", obj_text)
            self.assertIn("x MARK_ITEM_HI", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_relocates_identifier_compiler_constants_in_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "TYPE Pair=[BYTE tag CARD value]\n"
                "BYTE base\n"
                "BYTE alias=base\n"
                "BYTE next=base+1\n"
                "BYTE POINTER ptr=base+1\n"
                "BYTE ARRAY values(3)\n"
                "BYTE ARRAY tail=values+1\n"
                "Pair record\n"
                "Pair mirror=record\n"
                "PROC Worker()\n"
                "RETURN\n"
                "PROC WorkerAlias=Worker()\n"
                "PROC WorkerExpr=Worker+(2*3)()\n"
                "PROC WorkerFirst=(1 LSH 2)+Worker()\n"
                "MODULE\n"
                "CARD ARRAY addresses(0)=[base base+1 values+2 Worker]\n"
                "PROC Constants=*()\n"
                "[base+2 * $60]\n"
                "PROC MAIN()\n"
                "alias=1\n"
                "next=2\n"
                "ptr^=3\n"
                "tail(0)=4\n"
                "mirror.tag=5\n"
                "WorkerAlias()\n"
                "WorkerExpr()\n"
                "WorkerFirst()\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("x MAIN_ALIAS_LO", obj_text)
            self.assertNotIn("x MAIN_NEXT_LO", obj_text)
            self.assertRegex(obj_text, r"(?m)^r \d+ x MAIN_BASE_LO 1$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x MAIN_VALUES_DATA 1$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x MAIN_VALUES_DATA 2$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x MAIN_RECORD_TAG_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER 6$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER 4$")
            self.assertRegex(obj_text, r"(?m)^x MAIN_CONSTANTS_CURRENT_ADDRESS_\d+ \d+ 1$")
            self.run_tool(project, "alink", "main")

    def test_actc_code_blocks_and_fixed_address_routines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE FUNC Seven=*()\n"
                "[$A9 7 $60]\n"
                "PROC Legacy=*()\n"
                "[$FFA2$A686$CA0$AD0$60]\n"
                "CARD FUNC Pair=*(BYTE low,high)\n"
                "[$60]\n"
                "BYTE FUNC Fourth=*(BYTE a,b,c,d)\n"
                "[$A3AD 0 $60]\n"
                "BYTE FUNC KernalGet=($FFE0+4)()\n"
                "PROC KernalOut=($FFD0+2)(BYTE value)\n"
                "PROC MAIN()\n"
                "CARD word\n"
                "CARD result=$C200\n"
                "BYTE done=$C202\n"
                "CARD packed=$C203\n"
                "BYTE fourthout=$C205\n"
                "BYTE key=$C206\n"
                "[$A9 $34 $8D word $A9 $12 $8D word+1]\n"
                "result=word+Seven()\n"
                "packed=Pair($34,$12)\n"
                "fourthout=Fourth(1,2,3,77)\n"
                "key=KernalGet()\n"
                "KernalOut('A)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("A9348D0000A9128D0000", obj_text)
            self.assertIn("A2FF86A6A00CD00A60", obj_text)
            self.assertNotIn("x PAIR_LOW_LO", obj_text)
            self.assertNotIn("x FOURTH_D_LO", obj_text)
            self.assertRegex(obj_text, r"r \d+ x MAIN_WORD_LO 1")
            self.assertIn("20E4FF", obj_text)
            self.assertIn("20D2FF", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_binds_idun_argc_and_argv_to_main_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN(CARD argc,CARD ARRAY argv)\n"
                "BYTE POINTER firstArgument\n"
                "firstArgument=argv(1)\n"
                "IF argc>1 THEN\n"
                "PrintIE(firstArgument^)\n"
                "FI\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("AD040FAE050F", obj_text)
            self.assertIn("AD060FAE070F", obj_text)
            self.assertRegex(obj_text, r"(?m)^x MAIN_ARGC_LO \d+ 1$")
            self.assertRegex(obj_text, r"(?m)^x MAIN_ARGV_LO \d+ 1$")
            self.run_tool(project, "alink", "main")

    def test_actc_rejects_non_idun_main_parameter_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN(BYTE ARRAY filename)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            result = self.run_tool(
                project, "actc", "main", expected_status=1
            )
            self.assertEqual(
                result.stderr,
                "MAIN ABI LINE 1: EXPECTED PROC MAIN() OR "
                "PROC MAIN(CARD argc,CARD ARRAY argv)\n",
            )

    def test_actc_asmblock_assembles_scoped_symbols_registers_and_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "BYTE globalValue\n"
                "PROC Helper()\n"
                "    globalValue=globalValue+1\n"
                "    RETURN\n"
                "ENDPROC\n"
                "PROC Worker(CARD argument)\n"
                "    CARD localValue\n"
                "    ASMBLOCK [\n"
                "        lda #<globalValue\n"
                "        sta $20\n"
                "        lda #>globalValue\n"
                "        sta $21\n"
                "        ldy #0\n"
                "        lda ($20),y\n"
                "        clc\n"
                "        adc argument\n"
                "        sta localValue\n"
                "        lda argument+1\n"
                "        sta localValue+1\n"
                "        ldx #3\n"
                "    again:\n"
                "        dex\n"
                "        bne again\n"
                "        jsr Helper\n"
                "        jmp finished\n"
                "        nop\n"
                "    finished:\n"
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
                "PROC MAIN()\n"
                "    Worker(4)\n"
                "    globalValue=RegisterPlusOne(globalValue)\n"
                "    RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("A9008520A9008521A000B120186D00008D0000", obj_text)
            self.assertIn("A203CAD0FD2000004C0000EA", obj_text)
            self.assertIn("18690160", obj_text)
            self.assertRegex(obj_text, r"(?m)^r \d+ lo x MAIN_GLOBALVALUE_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ hi x MAIN_GLOBALVALUE_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER_ARGUMENT_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER_ARGUMENT_LO 1$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x WORKER_LOCALVALUE_LO$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x HELPER$")
            self.assertRegex(obj_text, r"(?m)^x MAIN_WORKER_ASM_AGAIN_\d+ \d+ 1$")
            self.run_tool(project, "alink", "main")

    def test_actc_asmblock_reports_source_line_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n"
                "    ASMBLOCK [\n"
                "        teleport $D020\n"
                "    ]\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            result = self.run_tool(
                project, "actc", "main", expected_status=1
            )
            self.assertEqual(
                result.stderr,
                "ASM LINE 3: ILLEGAL ADDRESSING MODE FOR TELEPORT\n",
            )

    def test_actc_array_addresses_omitted_arguments_and_signed_division(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            for name in ("rt_i_div.obj", "rt_i_mod.obj"):
                (shared_lib / name.upper()).write_text(
                    (self.root / "src" / "runtime" / "modules" / name).read_text(
                        encoding="ascii"
                    ),
                    encoding="ascii",
                )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "CARD FUNC Add(CARD a,b)\n"
                "RETURN(a+b)\n"
                "PROC MAIN()\n"
                "BYTE ARRAY values(4)\n"
                "BYTE POINTER ptr\n"
                "INT dividend,divisor,quotient,remainder\n"
                "CARD omitted\n"
                "dividend=-13\n"
                "divisor=5\n"
                "quotient=dividend/divisor\n"
                "remainder=dividend MOD divisor\n"
                "values(1)=42\n"
                "ptr=@values(1)\n"
                "values(2)=ptr^\n"
                "omitted=Add(2,3)\n"
                "omitted=Add(4)\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_I_DIV\n", obj_text)
            self.assertIn("\nu RT_I_MOD\n", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_assignable_routines_and_action_quoted_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                'BYTE ARRAY text="A""B"\n'
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
                "BYTE redirected=$C221,quote=$C222,length=$C223,done=$C224\n"
                "saved=First\n"
                "First=routines(1)\n"
                "First()\n"
                "redirected=output\n"
                "First=saved\n"
                "First()\n"
                "quote=text(2)\n"
                "length=text(0)\n"
                "done=1\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertRegex(obj_text, r"r \d+ x FIRST 1")
            self.assertRegex(obj_text, r"r \d+ x FIRST 2")
            self.assertRegex(obj_text, r"(?m)^x MAIN_ROUTINES_DATA \d+ 4$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x FIRST$")
            self.assertRegex(obj_text, r"(?m)^r \d+ x SECOND$")
            self.run_tool(project, "alink", "main")

    def test_actc_folds_constant_product_inside_dynamic_expression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared_lib = root / "LIB"
            shared_lib.mkdir()
            (shared_lib / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(
                    encoding="ascii"
                ),
                encoding="ascii",
            )
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD seed,x,y\nseed = 5\nx = seed + 0\n"
                "y = x + (2 * 3)\nPrintI(y)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertNotIn("RT_I_MUL", obj_text)
            self.assertNotIn("RT_I_DIV", obj_text)
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.assertIn("6906", obj_text)
            self.run_tool(project, "alink", "main")

    def test_actc_expression_storage_grows_past_6502_style_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            expression = "x + (" * 40 + "x" + ")" * 40
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD seed,x,y\nseed = 1\nx = seed + 0\ny = "
                + expression
                + "\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertGreater(len(obj_text), 4096)
            self.assertIn("MAIN_EXPR_30_VALUE_LO", obj_text)

    def test_actc_runtime_if_variable_equals_constant_emits_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 300",
                        "y = x + 5",
                        "IF y = 305 THEN",
                        'PrintE("YES")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn("MAIN_MAIN_IF_NEXT_", obj_text)
            self.assertIn("MAIN_EXPR_", obj_text)
            self.assertIn(bytes([0xCD]), prg)
            self.assertIn(bytes([0xD0]), prg)
            self.assertIn(bytes([0xA9, ord("Y"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_variable_not_equals_constant_emits_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 300",
                        "y = x + 5",
                        "IF y # 0 THEN",
                        'PrintE("NE")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn("MAIN_MAIN_IF_NEXT_", obj_text)
            self.assertIn("MAIN_EXPR_", obj_text)
            self.assertGreaterEqual(prg.count(bytes([0xD0])), 2)
            self.assertIn(bytes([0xA9, ord("N"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_card_less_than_constant_emits_unsigned_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 300",
                        "y = x + 5",
                        "IF y < 400 THEN",
                        'PrintE("LT")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn("MAIN_EXPR_", obj_text)
            self.assertIn(bytes([0x90]), prg)
            self.assertIn(bytes([0xD0]), prg)
            self.assertIn(bytes([0xA9, ord("L"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_byte_greater_equal_constant_emits_unsigned_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x",
                        "BYTE b",
                        "x = 2",
                        "b = x + 5",
                        "IF b >= 7 THEN",
                        'PrintE("GE")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn("MAIN_EXPR_", obj_text)
            self.assertIn(bytes([0x90]), prg)
            self.assertIn(bytes([0xB0]), prg)
            self.assertIn(bytes([0xA9, ord("G"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_card_less_than_out_of_range_constant_runs_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 300",
                        "y = x + 5",
                        "IF y < 70000 THEN",
                        'PrintE("OK")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertNotIn("MAIN_EXPR_", obj_text)
            self.assertIn(bytes([0xA9, ord("O"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_card_equals_out_of_range_constant_skips_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 0",
                        "y = x + 0",
                        "IF y = 65536 THEN",
                        'PrintE("BAD")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertNotIn("MAIN_EXPR_", obj_text)
            self.assertIn("MAIN_MAIN_IF_NEXT_", obj_text)
            self.assertIn(bytes([0x4C]), prg)
            self.assertIn(bytes([0xA9, ord("B"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_byte_equals_out_of_range_constant_skips_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x",
                        "BYTE b",
                        "x = 2",
                        "b = x + 5",
                        "IF b = 263 THEN",
                        'PrintE("BAD")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertNotIn("MAIN_EXPR_", obj_text)
            self.assertIn("MAIN_MAIN_IF_NEXT_", obj_text)
            self.assertIn(bytes([0x4C]), prg)
            self.assertIn(bytes([0xA9, ord("B"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_runtime_if_byte_not_equals_out_of_range_constant_runs_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "BYTE b",
                        "b = 7",
                        "IF b <> 263 THEN",
                        'PrintE("OK")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertNotIn("MAIN_EXPR_", obj_text)
            self.assertIn(bytes([0xA9, ord("O"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_if_else_body_has_no_relative_branch_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            long_text = "T" * 80
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "BYTE x",
                        "x = 1",
                        "IF x = 1 THEN",
                        f'PrintE("{long_text}")',
                        "ELSE",
                        'PrintE("FALSE")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("MAIN_MAIN_IF_NEXT_", obj_text)
            self.assertIn("MAIN_MAIN_IF_END_", obj_text)
            self.assertIn("r ", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertGreater(len(prg), 400)
            self.assertIn(bytes([0x4C]), prg)

    def test_actc_elseif_compares_arbitrary_word_expressions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD x,y",
                        "x = 2",
                        "y = x + 1",
                        "IF x + 1 < y THEN",
                        'PrintE("LESS")',
                        "ELSEIF x + 1 = y THEN",
                        'PrintE("EQUAL")',
                        "ELSE",
                        'PrintE("GREATER")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertGreaterEqual(obj_text.count("_IF_NEXT_"), 2)
            self.assertGreaterEqual(obj_text.count("_VALUE_LO"), 4)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            for initial in ("L", "E", "G"):
                self.assertIn(bytes([0xA9, ord(initial), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_do_until_while_and_exit_use_absolute_control_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "BYTE x",
                        "x = 0",
                        "DO",
                        "x = x + 1",
                        "UNTIL x = 3",
                        "OD",
                        "WHILE x < 10",
                        "DO",
                        "x = x + 1",
                        "IF x = 5 THEN",
                        "EXIT",
                        "FI",
                        "OD",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertGreaterEqual(obj_text.count("_LOOP_START_"), 2)
            self.assertGreaterEqual(obj_text.count("_LOOP_END_"), 2)
            self.assertIn("x MAIN_MAIN_IF_END_", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertGreaterEqual(prg.count(bytes([0x4C])), 4)

    def test_actc_accepts_inline_while_do_from_native_action_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\n"
                "CARD I\n"
                "I=0\n"
                "WHILE I<1 DO\n"
                "I=I+1\n"
                "OD\n"
                "RETURN\n"
                "ENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            object_text = (project / "OBJ" / "MAIN.OBJ").read_text(
                encoding="ascii"
            )
            self.assertIn("MAIN_MAIN_LOOP_START_", object_text)
            self.assertIn("MAIN_MAIN_LOOP_END_", object_text)
            self.run_tool(project, "alink", "main")

    def test_actc_for_loops_stage_bounds_and_support_dynamic_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "CARD first,last,i,j",
                        "INT step",
                        "first = 1",
                        "last = first + 4",
                        "step = 2",
                        "FOR i=first TO last STEP step",
                        "DO",
                        "j = i + 0",
                        "OD",
                        "step = -2",
                        "FOR j=5 TO 1 STEP step",
                        "DO",
                        "i = j + 0",
                        "OD",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertGreaterEqual(obj_text.count("__FOR_"), 8)
            self.assertGreaterEqual(obj_text.count("_LOOP_START_"), 2)
            self.assertIn("_STEP", obj_text)
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertGreaterEqual(prg.count(bytes([0x4C])), 2)
            self.assertIn(bytes([0x90]), prg)

    def test_actc_rejects_invalid_for_steps(self) -> None:
        cases = {
            "zero": (
                "PROC MAIN()\nBYTE i\nFOR i=0 TO 3 STEP 0\nDO\nOD\nENDPROC\n",
                "ZERO FOR STEP LINE 3\n",
            ),
            "missing_do": (
                "PROC MAIN()\nBYTE i\nFOR i=0 TO 3\nRETURN\nENDPROC\n",
                "FOR REQUIRES DO LINE 3\n",
            ),
        }
        for name, (source, expected_error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(source, encoding="ascii")
                result = self.run_tool(project, "actc", "main", expected_status=1)
                self.assertEqual(result.stderr, expected_error)

    def test_actc_structured_control_stack_is_vector_backed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            depth = 40
            lines = ["PROC MAIN()"] + ["DO"] * depth + ["OD"] * depth + ["RETURN", "ENDPROC", ""]
            (project / "SRC" / "MAIN.ACT").write_text("\n".join(lines), encoding="ascii")

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            export_lines = [line for line in obj_text.splitlines() if line.startswith("x ")]
            self.assertEqual(sum("MAIN_MAIN_LOOP_START_" in line for line in export_lines), depth)
            self.assertEqual(sum("MAIN_MAIN_LOOP_END_" in line for line in export_lines), depth)
            self.run_tool(project, "alink", "main")

    def test_actc_rejects_malformed_structured_control(self) -> None:
        cases = {
            "while": ("PROC MAIN()\nWHILE 1\nRETURN\nENDPROC\n", "WHILE REQUIRES DO LINE 2\n"),
            "exit": ("PROC MAIN()\nEXIT\nRETURN\nENDPROC\n", "EXIT OUTSIDE LOOP LINE 2\n"),
            "od": ("PROC MAIN()\nOD\nRETURN\nENDPROC\n", "BAD OD LINE 2\n"),
        }
        for name, (source, expected_error) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.run_tool(root, "actnew", "demo")
                project = root / "DEMO"
                (project / "SRC" / "MAIN.ACT").write_text(source, encoding="ascii")
                result = self.run_tool(project, "actc", "main", expected_status=1)
                self.assertEqual(result.stderr, expected_error)

    def test_actc_printi_imports_link_selected_runtime_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "LIB").mkdir()
            (project / "LIB" / "RT_PRINT_I.OBJ").write_text(
                (self.root / "src" / "runtime" / "modules" / "rt_print_i.obj").read_text(encoding="ascii"),
                encoding="ascii",
            )
            (project / "SRC" / "MAIN.ACT").write_text(
                "PROC MAIN()\nCARD x\nx = 300\nPrintI(x)\nPrintI(-1)\nRETURN\nENDPROC\n",
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            obj_text = (project / "OBJ" / "MAIN.OBJ").read_text(encoding="ascii")
            self.assertIn("\nu RT_PRINT_I\n", obj_text)
            self.assertIn("x MAIN_X_LO", obj_text)
            self.assertIn("x MAIN_X_HI", obj_text)

            self.run_tool(project, "alink", "main")
            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0xA9, 0x2C, 0xA2, 0x01]), prg)
            self.assertIn(bytes([0xA9, 0xFF, 0xA2, 0xFF]), prg)
            self.assertIn(bytes([0x20, 0xD2, 0xFF]), prg)
            debug = (project / "BIN" / "MAIN.DBG").read_text(encoding="ascii")
            self.assertIn("m 1 RT_PRINT_I\n", debug)
            runtime = (project / "LIB" / "RT_PRINT_I.OBJ").read_text(encoding="ascii")
            self.assertIn("x RT_PRINT_I 0 126\n", runtime)
            self.assertIn("r 38 x RT_PRINT_I_EMIT_DIGIT\n", runtime)

    def test_actc_compile_time_if_condition_controls_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "IF 1 = 1 THEN",
                        'PrintE("YES")',
                        "FI",
                        "IF 1 = 0 THEN",
                        'PrintE("NO")',
                        "FI",
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0xA9, ord("Y"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("E"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("S"), 0x20, 0xD2, 0xFF]), prg)
            self.assertNotIn(bytes([0xA9, ord("N"), 0x20, 0xD2, 0xFF]), prg)
            self.assertNotIn(bytes([0xA9, ord("O"), 0x20, 0xD2, 0xFF]), prg)

    def test_actc_compile_time_if_skips_inactive_unknown_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_tool(root, "actnew", "demo")
            project = root / "DEMO"
            (project / "SRC" / "MAIN.ACT").write_text(
                "\n".join(
                    [
                        "PROC MAIN()",
                        "IF 0 THEN",
                        "IF missing = 1 THEN",
                        'PrintE("BAD")',
                        "FI",
                        "FI",
                        'PrintE("OK")',
                        "RETURN",
                        "ENDPROC",
                        "",
                    ]
                ),
                encoding="ascii",
            )

            self.run_tool(project, "actc", "main")
            self.run_tool(project, "alink", "main")

            prg = (project / "BIN" / "MAIN.PRG").read_bytes()
            self.assertIn(bytes([0xA9, ord("O"), 0x20, 0xD2, 0xFF]), prg)
            self.assertIn(bytes([0xA9, ord("K"), 0x20, 0xD2, 0xFF]), prg)
            self.assertNotIn(bytes([0xA9, ord("B"), 0x20, 0xD2, 0xFF]), prg)


if __name__ == "__main__":
    unittest.main()
