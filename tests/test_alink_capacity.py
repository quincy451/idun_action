from pathlib import Path
import re
import shutil
import subprocess
import unittest


ALINK_CODE_START = 0x0900
UDOS_PRESERVED_TOOL_ABI_START = 0x9800
ALINK_WORKSPACE_START = 0xA000
ALINK_WORKSPACE_END = 0xC000


class TestAlinkCapacity(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.map_path = self.root / "build" / "udos_tools" / "alink.current.map"

    def test_production_layout_preserves_live_udos_tool_abi(self) -> None:
        for tool in ("ca65", "ld65"):
            if shutil.which(tool) is None:
                self.skipTest(f"{tool} not found")

        result = subprocess.run(
            [str(self.root / "tools" / "build_alink_udos.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        map_text = self.map_path.read_text(encoding="ascii")
        code_start, code_end = self.segment_bounds(map_text, "CODE")
        bss_start, bss_end = self.segment_bounds(map_text, "BSS")

        self.assertEqual(code_start, ALINK_CODE_START, msg=map_text)
        self.assertLess(code_end, UDOS_PRESERVED_TOOL_ABI_START, msg=map_text)
        self.assertGreaterEqual(bss_start, ALINK_WORKSPACE_START, msg=map_text)
        self.assertLess(bss_end, ALINK_WORKSPACE_END, msg=map_text)

    def segment_bounds(self, map_text: str, segment: str) -> tuple[int, int]:
        match = re.search(
            rf"^{segment}\s+([0-9A-Fa-f]{{6}})\s+([0-9A-Fa-f]{{6}})\s+",
            map_text,
            re.MULTILINE,
        )
        self.assertIsNotNone(match, msg=map_text)
        assert match is not None
        return int(match.group(1), 16), int(match.group(2), 16)


if __name__ == "__main__":
    unittest.main()
