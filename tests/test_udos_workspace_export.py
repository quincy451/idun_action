from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestUdosWorkspaceExport(unittest.TestCase):
    def test_export_creates_udos_tree_with_guides_examples_and_libs(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tool = root / "tools" / "export_udos_workspace.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out"
            result = subprocess.run(
                [sys.executable, str(tool), "--output", str(output)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            image_root = output / "IMAGES" / "ACTION.DNP"
            self.assertTrue(image_root.is_dir())

            expected_dirs = ["BIN", "DOC", "LIB", "SRC"]
            for name in expected_dirs:
                self.assertTrue((image_root / name).is_dir(), name)

            self.assertTrue((image_root / "README.TXT").is_file())
            self.assertIn("D BIN", (image_root / "UDOSDIR.TXT").read_text(encoding="ascii"))
            self.assertIn("F README.TXT", (image_root / "UDOSDIR.TXT").read_text(encoding="ascii"))

            docs_dir = image_root / "DOC"
            self.assertTrue((docs_dir / "OPERATOR.TXT").is_file())
            self.assertTrue((docs_dir / "LANGUAGE.TXT").is_file())
            self.assertFalse((docs_dir / "VMABI.TXT").exists())
            self.assertFalse((docs_dir / "UDOSRESM.TXT").exists())
            self.assertIn("ActionC64U UDOS Operator Guide", (docs_dir / "OPERATOR.TXT").read_text(encoding="ascii"))

            src_dir = image_root / "SRC"
            self.assertTrue((src_dir / "HELLO.ACT").is_file())
            self.assertTrue((src_dir / "MATH.ACT").is_file())
            self.assertIn("PROC main()", (src_dir / "HELLO.ACT").read_text(encoding="ascii"))

            old_binary_pattern = "*." + ("A" + "VM")
            self.assertFalse(list(image_root.rglob(old_binary_pattern)))
            self.assertFalse(list(image_root.rglob("*.AVT")))

            lib_dir = image_root / "LIB"
            bundle = (lib_dir / "LIBMODS.DAT").read_text(encoding="ascii")
            self.assertIn("FILE libpstr.mod", bundle)
            self.assertTrue((lib_dir / "LIBPSTR.MOD").is_file())
            self.assertTrue((lib_dir / "RT_PRINT_STR.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_F_ADD.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_F_SUB.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_F_MUL.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_F_DIV.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_I_TO_F.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_SID_FREQ.OBJ").is_file())
            self.assertTrue((lib_dir / "RT_SPRITE_ON.OBJ").is_file())
            self.assertIn(
                "x rt_f_add 0 2",
                (lib_dir / "RT_F_ADD.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "b Ar",
                (lib_dir / "RT_F_ADD.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "n rt_f_add",
                (lib_dir / "RT_F_ADD.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "x rt_f_sub 0 2",
                (lib_dir / "RT_F_SUB.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "b Jr",
                (lib_dir / "RT_F_SUB.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "x rt_f_mul 0 2",
                (lib_dir / "RT_F_MUL.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "b Mr",
                (lib_dir / "RT_F_MUL.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "x rt_f_div 0 2",
                (lib_dir / "RT_F_DIV.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "b Vr",
                (lib_dir / "RT_F_DIV.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "x rt_i_to_f 0 2",
                (lib_dir / "RT_I_TO_F.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "b Wr",
                (lib_dir / "RT_I_TO_F.OBJ").read_text(encoding="ascii"),
            )
            self.assertIn(
                "x rt_s_to_f 0 69",
                (lib_dir / "RT_S_TO_F.OBJ").read_text(encoding="ascii"),
            )
            self.assertTrue((lib_dir / "UDOSDIR.TXT").is_file())

    def test_export_with_udos_tools_builds_actinfo_when_prereqs_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tool = root / "tools" / "export_udos_workspace.py"
        udos_labels = root.parent / "udos" / "build" / "udos-resident.labels"
        if not udos_labels.is_file():
            self.skipTest("UDOS resident labels not built")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out"
            result = subprocess.run(
                [sys.executable, str(tool), "--output", str(output), "--build-udos-tools"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

            image_root = output / "IMAGES" / "ACTION.DNP"
            self.assertTrue((image_root / "ACTDIR.PRG").is_file())
            self.assertTrue((image_root / "ACTADD.PRG").is_file())
            self.assertTrue((image_root / "ACT2SAVE.PRG").is_file())
            self.assertTrue((image_root / "ACTC.PRG").is_file())
            self.assertEqual((image_root / "ACTC_OVL0.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL1.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL2.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL3.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL4.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL5.BIN").read_bytes()[:4], b"ACOV")
            self.assertEqual((image_root / "ACTC_OVL6.BIN").read_bytes()[:4], b"ACOV")
            self.assertTrue((image_root / "ALINK.PRG").is_file())
            self.assertTrue((image_root / "ACTCHK.PRG").is_file())
            self.assertTrue((image_root / "ACTMON.PRG").is_file())
            self.assertTrue((image_root / "ACTFILE.PRG").is_file())
            self.assertTrue((image_root / "ACTWORK.PRG").is_file())
            self.assertTrue((image_root / "ACTFLOW.BAT").is_file())
            self.assertTrue((image_root / "ACTNEW.BAT").is_file())
            self.assertTrue((image_root / "ACTNEW.PRG").is_file())
            self.assertTrue((image_root / "ACTSRC.PRG").is_file())
            self.assertTrue((image_root / "PROJECT.TXT").is_file())
            self.assertTrue((image_root / "MAIN.ACT").is_file())
            actnew_lines = (image_root / "ACTNEW.BAT").read_text(encoding="ascii").splitlines()
            self.assertTrue(actnew_lines)
            self.assertTrue(all(len(line) <= 31 for line in actnew_lines if line))
            self.assertTrue((image_root / "ACTINFO.PRG").is_file())
            self.assertTrue((image_root / "ACTCOPY.PRG").is_file())
            self.assertTrue((image_root / "ACTDEL.PRG").is_file())
            self.assertTrue((image_root / "ACTMKDIR.PRG").is_file())
            self.assertTrue((image_root / "ACTMOVE.PRG").is_file())
            self.assertTrue((image_root / "ACTRMDIR.PRG").is_file())
            self.assertTrue((image_root / "ACTWRITE.PRG").is_file())
            self.assertTrue((image_root / "ACTEDIT.PRG").is_file())
            old_vm_prefix = "A" + "VM"
            old_runner = old_vm_prefix + "RUN"
            for name in [
                old_vm_prefix + "INFO.PRG",
                old_runner + ".PRG",
                old_runner + "C.PRG",
                "ACTDBG.PRG",
                "ACTDBG_OVL1.BIN",
                "ACTDBG_OVL2.BIN",
                "RT_PRINT_STD_HELPER.BIN",
                "RT_PRINT_F_HELPER.BIN",
                "RT_GFX1_HELPER.BIN",
                "RT_SIDSPR1_HELPER.BIN",
                "RT_DBF1_HELPER.BIN",
                "RT_MATH1_HELPER.BIN",
                old_runner + "_OVL1.BIN",
                old_runner + "_OVL2.BIN",
                old_runner + "_OVL3.BIN",
            ]:
                self.assertFalse((image_root / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
