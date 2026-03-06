from pathlib import Path
import unittest


class TestRepoLayout(unittest.TestCase):
    def test_repo_layout_smoke(self) -> None:
        root = Path(__file__).resolve().parents[1]

        required = [
            "README.md",
            "LICENSE",
            ".gitignore",
            "AGENTS.md",
            "docs/inspiration/action.pdf",
            "docs/setup_wsl.md",
            "docs/roadmap.md",
            "docs/architecture.md",
            "docs/cpmemu.md",
            "docs/cpm65_abi.md",
            "docs/acheron.md",
            "docs/blockers.md",
            "docs/spec.md",
            "src/compiler",
            "src/vm",
            "src/vm/vmhello/vmhello.asm",
            "src/runtime",
            "src/tools_cpm",
            "src/tools_cpm/hello/hello.asm",
            "src/tools_cpm/hello/hello.c",
            "tools/env_check.sh",
            "tools/setup_wsl.sh",
            "tools/path_probe.py",
            "tools/cpmemu_runner.py",
            "tools/build_cpm65_notes.sh",
            "tools/build_hello.sh",
            "tools/build_vmhello.sh",
            "pytest/__main__.py",
            "tools",
            "examples",
            "tests",
            "tests/test_cpmemu_available.py",
            "tests/test_hello_com.py",
            "tests/test_vmhello.py",
        ]

        missing = [path for path in required if not (root / path).exists()]
        self.assertFalse(missing, f"Missing required project paths: {missing}")


if __name__ == "__main__":
    unittest.main()
