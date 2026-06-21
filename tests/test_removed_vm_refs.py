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

    def test_active_docs_do_not_reintroduce_monolithic_helper_bins(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        scan_roots = [
            workspace / "actionc64u" / "docs",
            workspace / "actionc64u" / "examples",
            workspace / "actionc64u" / "lib",
            workspace / "actionc64u" / "src" / "runtime" / "udos_modules" / "README.md",
        ]
        skipped_dirs = {".git", "build", "__pycache__", ".pytest_cache", "inspiration"}
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
        rejected = [
            re.compile(r"RT_[A-Z0-9_]+_HELPER\.BIN"),
            re.compile(r"\bHELPER\.BIN\b"),
        ]

        findings: list[str] = []
        for path in self._iter_files(scan_roots, skipped_dirs, skipped_suffixes):
            rel = path.relative_to(workspace).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            text_terms = [pattern.pattern for pattern in rejected if pattern.search(text)]
            if text_terms:
                findings.append(f"{rel}: text contains {', '.join(text_terms)}")

        self.assertFalse(
            findings,
            "Active docs/libs should reference link-selected RT_*.OBJ modules, not monolithic helper bins:\n"
            + "\n".join(findings),
        )

    def test_runtime_spec_names_shipped_helper_families(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        spec = (workspace / "actionc64u" / "docs" / "runtime_programs_spec.txt").read_text(
            encoding="utf-8"
        )

        for family in [
            "REAL math",
            "printing",
            "graphics",
            "SID/sprite",
            "joystick/mouse input",
            "DBF",
        ]:
            self.assertIn(family, spec)

    def test_workspace_readme_documents_active_udos_direct_prg_path(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        readme = (workspace / "README.md").read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", readme)

        for expected in [
            "ACTC.PRG -> OBJ/<MODULE>.OBJ -> ALINK.PRG -> BIN/<MODULE>.PRG",
            "direct linked 6502 `.PRG`",
            "There is no separate runtime runner",
            "link-selected runtime `RT_*.OBJ` modules",
            "make test",
            "vice-action-actc-alink-launch",
        ]:
            self.assertIn(expected, normalized)

        for retired in [
            "primary execution backend",
            "bytecode runner",
            "release C64 CP/M-65 disk image",
            "bin/cpmemu",
            "/mnt/c/test/action",
        ]:
            self.assertNotIn(retired, normalized)

    def test_prompt_chain_docs_are_archive_not_active_workflow(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        docs = {
            "RUN_PROMPTS.md": workspace / "RUN_PROMPTS.md",
            "actionc64u/docs/prompt_chain.md": workspace / "actionc64u" / "docs" / "prompt_chain.md",
        }

        for name, path in docs.items():
            with self.subTest(path=name):
                text = path.read_text(encoding="utf-8")
                normalized = re.sub(r"\s+", " ", text)
                for expected in [
                    "historical",
                    "not the active",
                    "make test",
                    "vice-action-actc-alink-launch",
                    "ACTC.PRG -> OBJ/<MODULE>.OBJ -> ALINK.PRG -> BIN/<MODULE>.PRG",
                ]:
                    self.assertIn(expected, normalized)

                for retired in [
                    "/mnt/c/test/action",
                    "codex exec --sandbox workspace-write",
                    "< prompt-1.txt",
                    "< prompt-13.txt",
                    "The prompts will create",
                    "primary execution backend",
                    "bytecode runner",
                    "release C64 CP/M-65 disk image",
                    "bin/cpmemu",
                ]:
                    self.assertNotIn(retired, normalized)

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
