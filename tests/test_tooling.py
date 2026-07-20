from pathlib import Path
import re
import subprocess
import sys
import unittest


class TestTooling(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.workspace = Path(__file__).resolve().parents[2]

    def test_path_probe(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.root / "tools" / "path_probe.py")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("All required local paths resolved.", result.stdout)

    def test_udos_service_include_exports_path_dir_begin(self) -> None:
        generator = (self.root / "tools" / "generate_udos_service_inc.py").read_text(encoding="ascii")

        self.assertIn('"svc_dir_begin_sc0": 0xCF3F', generator)
        self.assertIn('"svc_program_chain_sc0": 0xCF42', generator)
        self.assertIn('"udos_tool_abi_version": "ABI_VERSION"', generator)
        self.assertIn('"tool_dir_status_flat": 6', generator)
        self.assertIn('"tool_dir_status_unmounted": 7', generator)
        self.assertIn('"tool_dir_status_bad": 8', generator)

    def test_env_check_non_destructive(self) -> None:
        result = subprocess.run(
            [str(self.root / "tools" / "env_check.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, msg=combined)
        self.assertIn("STATUS", result.stdout)
        self.assertIn("Summary:", result.stdout)
        self.assertRegex(combined, r"PASS|FAIL")

    def test_setup_guidance_does_not_require_cpm_toolchain(self) -> None:
        setup_script = (self.root / "tools" / "setup_wsl.sh").read_text(encoding="utf-8")
        env_check = (self.root / "tools" / "env_check.sh").read_text(encoding="utf-8")
        setup_doc = (self.root / "docs" / "setup_wsl.md").read_text(encoding="utf-8")
        combined = "\n".join((setup_script, env_check, setup_doc))

        for stale_token in ("cpmtools", "mos-cpm65-clang", "local CP/M-65 work"):
            self.assertNotIn(stale_token, combined)

    def test_actc_probe_progress_output_is_verbose_gated(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_actc_probe.py").read_text()

        self.assertIn('parser.add_argument("--verbose"', probe_text)
        self.assertIn("def log_progress(verbose: bool", probe_text)
        self.assertNotIn('print({"phase":', probe_text)
        self.assertNotIn('print({"attempt":', probe_text)

    def test_alink_probe_progress_output_is_verbose_gated(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_alink_probe.py").read_text()

        self.assertIn('parser.add_argument("--verbose"', probe_text)
        self.assertIn("def log_progress(verbose: bool", probe_text)
        self.assertNotIn('print({"attempt":', probe_text)
        self.assertNotIn("def collect_debug(", probe_text)
        self.assertNotIn("ACTION_ALINK_CURRENT_LABELS", probe_text)
        self.assertNotIn("save_debug_stage_byte", probe_text)

    def test_actmon_probe_debug_output_is_verbose_gated(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_actmon_probe.py").read_text()

        self.assertIn('parser.add_argument("--verbose"', probe_text)
        self.assertIn("ACTMON_PROBE_VERBOSE", probe_text)
        self.assertIn('os.environ.get("ACTMON_PROBE_DEBUG")', probe_text)
        self.assertIn("def debug_log(message: str", probe_text)

    def test_seeded_probe_progress_output_is_verbose_gated(self) -> None:
        for probe_name in (
            "run_action_act2save_seeded_probe.py",
            "run_action_alink_seeded_runtime_probe.py",
        ):
            with self.subTest(probe_name=probe_name):
                probe_text = (self.workspace / "udos" / "tools" / probe_name).read_text()

                self.assertIn('parser.add_argument("--verbose"', probe_text)
                self.assertIn("def log_progress(verbose: bool", probe_text)
                self.assertIsNone(re.search(r"print\(\s*json\.dumps\(\s*\{\s*\"attempt\"", probe_text))

    def test_alink_probes_use_shared_filesystem_helpers(self) -> None:
        shared_text = (self.workspace / "udos" / "tools" / "run_action_probe_fs.py").read_text()
        self.assertIn("def add_case_aliases", shared_text)
        self.assertIn("def project_output_path", shared_text)

        for probe_name in (
            "run_action_alink_probe.py",
            "run_action_alink_prg_probe.py",
            "run_action_alink_seeded_runtime_probe.py",
            "run_action_actmon_probe.py",
        ):
            with self.subTest(probe_name=probe_name):
                probe_text = (self.workspace / "udos" / "tools" / probe_name).read_text()
                self.assertIn("import run_action_probe_fs as pfs", probe_text)
                self.assertNotIn("import run_action_actc_probe as rcp", probe_text)
                for helper in (
                    "write_ascii",
                    "ensure_catalog_entries",
                    "case_insensitive_child",
                    "detect_lowercase_workspace",
                    "host_name",
                ):
                    self.assertNotIn(f"rap.{helper}", probe_text, msg=probe_name)

    def test_alink_prg_probe_allows_slow_tree_mounts(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_alink_prg_probe.py").read_text()

        self.assertIn("mount_timeout = min(shell_timeout, 90.0)", probe_text)
        self.assertIn("prompt_timeout = min(shell_timeout, 45.0)", probe_text)

    def test_tool_abi_harness_captures_default_kernal_output(self) -> None:
        harness_text = (self.root / "tools" / "tool_abi_harness.c").read_text()

        self.assertIn("if (h->current_output_lfn == 0)", harness_text)
        self.assertIn("append_console_char(h, (char)cpu->registers->a);", harness_text)

    def test_vice_tree_persist_probe_success_output_is_verbose_gated(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_vice_tree_persist_probe.py").read_text()

        self.assertIn('parser.add_argument("--verbose"', probe_text)
        self.assertIn("if args.verbose:\n                print(final_screen)", probe_text)
        self.assertIsNone(re.search(r"^            print\\(final_screen\\)$", probe_text, re.MULTILINE))

    def test_active_probe_descriptions_do_not_reintroduce_runner_wording(self) -> None:
        stale_runner_phrase = "generic Action VICE " + "runner"
        for probe_name in (
            "run_action_actc_probe.py",
            "run_action_alink_probe.py",
            "run_action_actmon_check_probe.py",
        ):
            with self.subTest(probe_name=probe_name):
                probe_text = (self.workspace / "udos" / "tools" / probe_name).read_text()
                self.assertNotIn(stale_runner_phrase, probe_text)
                self.assertIn("UDOS VICE probe harness", probe_text)

    def test_act2save_probe_uses_shared_filesystem_helpers(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_act2save_seeded_probe.py").read_text()

        self.assertIn("import run_action_probe_fs as pfs", probe_text)
        self.assertNotIn("import run_action_alink_probe as rap", probe_text)
        self.assertNotIn("rap.", probe_text)

    def test_act2save_probe_success_output_is_verbose_gated(self) -> None:
        probe_text = (self.workspace / "udos" / "tools" / "run_action_act2save_seeded_probe.py").read_text()

        self.assertIn("args.verbose or args.verbose_success", probe_text)
        self.assertIsNone(re.search(r"print\(\s*json\.dumps\(\s*\{\s*\"status\":\s*\"ACT2SAVE OK\"", probe_text))
        self.assertIsNone(
            re.search(
                r"if args\.screen_only_success:\s+print\(screen\)\s+print\(json\.dumps\(debug",
                probe_text,
            )
        )
        self.assertIn("if args.verbose_success:\n                    print(json.dumps(debug, indent=2), file=sys.stderr)", probe_text)


if __name__ == "__main__":
    unittest.main()
