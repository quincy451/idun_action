from __future__ import annotations

import os
from pathlib import Path
import re
import unittest


class TestRemovedVmRefs(unittest.TestCase):
    def test_maintained_trees_do_not_reintroduce_removed_terms(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        scan_roots = [
            workspace / "actionc64u",
            workspace / "udos",
            workspace / "Makefile",
        ]

        skipped_dirs = {".git", "build", "__pycache__", ".pytest_cache"}
        skipped_suffixes = {
            ".7z",
            ".bin",
            ".d64",
            ".dnp",
            ".gif",
            ".jpg",
            ".jpeg",
            ".o",
            ".pdf",
            ".png",
            ".prg",
            ".pyc",
            ".zip",
        }

        vm_word = "a" + "vm"
        obj_word = "a" + "vo"
        runner_word = vm_word + "run"
        rejected = [
            re.compile(re.escape(runner_word), re.IGNORECASE),
            re.compile(r"\b" + re.escape(vm_word) + r"\b", re.IGNORECASE),
            re.compile(r"\b" + re.escape(obj_word) + r"\b", re.IGNORECASE),
            re.compile(re.escape("." + vm_word), re.IGNORECASE),
            re.compile(re.escape("." + obj_word), re.IGNORECASE),
            re.compile(re.escape(vm_word + "1"), re.IGNORECASE),
            re.compile(re.escape(obj_word + "1"), re.IGNORECASE),
        ]

        findings: list[str] = []
        for path in self._iter_files(scan_roots, skipped_dirs, skipped_suffixes):
            rel = path.relative_to(workspace).as_posix()
            path_terms = [pattern.pattern for pattern in rejected if pattern.search(rel)]
            if path_terms:
                findings.append(f"{rel}: path contains {', '.join(path_terms)}")
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            text_terms = [pattern.pattern for pattern in rejected if pattern.search(text)]
            if text_terms:
                findings.append(f"{rel}: text contains {', '.join(text_terms)}")

        self.assertFalse(findings, "Removed VM references found:\n" + "\n".join(findings))

    @staticmethod
    def _iter_files(
        roots: list[Path],
        skipped_dirs: set[str],
        skipped_suffixes: set[str],
    ) -> list[Path]:
        files: list[Path] = []
        for root in roots:
            if root.is_file():
                files.append(root)
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [name for name in dirnames if name not in skipped_dirs]
                current = Path(dirpath)
                for filename in filenames:
                    path = current / filename
                    if path.suffix.lower() in skipped_suffixes:
                        continue
                    files.append(path)
        return files


if __name__ == "__main__":
    unittest.main()
