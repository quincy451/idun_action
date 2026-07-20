from __future__ import annotations

from contextlib import closing
import json
import os
import re
import shlex
import sqlite3
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestProfilerTarget(unittest.TestCase):
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
        env: dict[str, str] | None = None,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.tool_dir / tool), *args],
            cwd=workspace,
            text=True,
            capture_output=True,
            env=env,
            input=input_text,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            expected_status,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def make_linked_project(self, root: Path) -> Path:
        self.run_tool(root, "actnew", "demo")
        project = root / "DEMO"
        (project / "SRC" / "MAIN.ACT").write_text(
            "PROC HELPER()\n"
            "RETURN\n"
            "ENDPROC\n"
            "PROC MAIN()\n"
            "HELPER()\n"
            "RETURN\n"
            "ENDPROC\n",
            encoding="ascii",
        )
        self.run_tool(project, "actc", "main")
        self.run_tool(project, "alink", "main")
        return project

    def fake_target_environment(
        self,
        home: Path,
        mode: str,
        samples: list[int],
        interval_us: int = 16667,
    ) -> tuple[dict[str, str], Path]:
        executable_dir = home / "fake-bin"
        executable_dir.mkdir()
        fake_source = self.root / "tests" / "fake_idun_target.py"
        launcher = executable_dir / "idunsh"
        launcher.write_text(
            "#!/bin/sh\nexec python3 "
            + shlex.quote(str(fake_source))
            + ' "$@"\n',
            encoding="ascii",
        )
        launcher.chmod(0o755)
        service = home / "actsvc"
        service.write_bytes(b"fake target service\n")
        runtime = home / "runtime"
        runtime.mkdir()
        log = home / "target.log"
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "XDG_RUNTIME_DIR": str(runtime),
                "ACTION_TARGET_SERVICE": str(service),
                "ACTION_FAKE_TARGET_MODE": mode,
                "ACTION_FAKE_TARGET_SAMPLES": ",".join(hex(value) for value in samples),
                "ACTION_FAKE_TARGET_INTERVAL_US": str(interval_us),
                "ACTION_FAKE_TARGET_LOG": str(log),
                "PATH": str(executable_dir) + os.pathsep + env.get("PATH", ""),
            }
        )
        return env, log

    def test_binary_target_protocol_selftest(self) -> None:
        result = self.run_tool(self.root, "actdbg", "--protocol-selftest")
        self.assertEqual(result.stdout, "TARGET PROTOCOL OK\n")

    def test_idun_target_service_has_tool_header_and_bounded_resident_image(self) -> None:
        service = self.tool_dir / "actsvc"
        self.assertTrue(service.is_file())
        self.assertEqual(service.read_bytes()[:8], bytes.fromhex("4c086dcb06104000"))
        labels = (self.root / "build" / "target_idun" / "actsvc.labels").read_text(
            encoding="utf-8"
        )
        values = {}
        for line in labels.splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[1] == "=":
                values[fields[0]] = int(fields[2].removeprefix("$"), 16)
        self.assertLessEqual(values["RESIDENT_SIZE"], 0x1000)
        self.assertEqual(values["SERVICE_BASE"], 0xC000)
        self.assertEqual(values["SERVICE_LIMIT"], 0xD000)
        self.assertIn("command_step", values)
        self.assertEqual(
            values["target_a"] - values["step_opcode_lengths"], 256
        )

    def test_resident_step_engine_handles_6510_control_flow_and_rearming(self) -> None:
        harness_build = subprocess.run(
            [str(self.root / "tools" / "build_tool_abi_harness.sh")],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(
            harness_build.returncode,
            0,
            msg=harness_build.stdout + harness_build.stderr,
        )
        harness = self.root / "build" / "udos_tools" / "tool_abi_harness"
        acme_labels = self.root / "build" / "target_idun" / "actsvc.labels"
        values: dict[str, int] = {}
        for line in acme_labels.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[1] == "=" and fields[2].startswith("$"):
                values[fields[0]] = int(fields[2][1:], 16)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = (self.tool_dir / "actsvc").read_bytes()
            resident_offset = values["resident_source"] - values["aceToolAddress"]
            resident = service[
                resident_offset : resident_offset + values["RESIDENT_SIZE"]
            ]
            expected_length_rows = (
                (1, 2, 0, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (3, 2, 0, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (1, 2, 0, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (1, 2, 0, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
                (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 3, 3, 3, 3),
                (2, 2, 0, 2, 2, 2, 2, 2, 1, 3, 1, 3, 3, 3, 3, 3),
            )
            expected_lengths = bytes(
                length for row in expected_length_rows for length in row
            )
            table_offset = values["step_opcode_lengths"] - values["SERVICE_BASE"]
            self.assertEqual(
                resident[table_offset : table_offset + 256], expected_lengths
            )
            resident_prg = root / "resident.prg"
            resident_prg.write_bytes(struct.pack("<H", values["SERVICE_BASE"]) + resident)
            labels = root / "resident.lbl"
            labels.write_text(
                "".join(
                    f"al {address:04x} .{name}\n"
                    for name, address in values.items()
                    if address <= 0xFFFF and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
                ),
                encoding="ascii",
            )
            services = root / "empty-services.inc"
            services.write_text("", encoding="ascii")

            def run_resident(
                entry: str,
                pokes: list[tuple[str, int, bool]],
                dumps: list[str],
            ) -> dict:
                command = [
                    str(harness),
                    "--prg",
                    str(resident_prg),
                    "--workspace",
                    str(root),
                    "--services-inc",
                    str(services),
                    "--labels",
                    str(labels),
                    "--entry-label",
                    entry,
                    "--max-steps",
                    "10000",
                ]
                for target, value, word in pokes:
                    command.extend(
                        ["--poke-word" if word else "--poke-byte", f"{target}={value}"]
                    )
                for dump in dumps:
                    command.extend(["--dump", dump])
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    msg=result.stdout + result.stderr,
                )
                summary = json.loads(result.stdout)
                self.assertTrue(summary["exited"], result.stdout)
                self.assertFalse(summary["hit_limit"], result.stdout)
                return summary

            def step_target(
                pc: int,
                memory: list[tuple[int, int]],
                *,
                status: int = 0x20,
                sp: int = 0xFD,
            ) -> tuple[int, dict]:
                pokes: list[tuple[str, int, bool]] = [
                    ("target_pc", pc, True),
                    ("target_status", status, False),
                    ("target_sp", sp, False),
                ]
                pokes.extend((hex(address), value, False) for address, value in memory)
                summary = run_resident(
                    "compute_step_target", pokes, ["step_target:2"]
                )
                target = int.from_bytes(
                    bytes(summary["dumps"]["step_target"]), "little"
                )
                return target, summary

            self.assertEqual(step_target(0x2000, [(0x2000, 0xEA)])[0], 0x2001)
            self.assertEqual(
                step_target(
                    0x2000, [(0x2000, 0x20), (0x2001, 0x56), (0x2002, 0x34)]
                )[0],
                0x3456,
            )
            self.assertEqual(
                step_target(
                    0x2000,
                    [
                        (0x2000, 0x6C),
                        (0x2001, 0xFF),
                        (0x2002, 0x30),
                        (0x30FF, 0x34),
                        (0x3000, 0x12),
                    ],
                )[0],
                0x1234,
            )
            self.assertEqual(
                step_target(
                    0x20FE, [(0x20FE, 0xD0), (0x20FF, 0x02)], status=0x20
                )[0],
                0x2102,
            )
            self.assertEqual(
                step_target(
                    0x20FE, [(0x20FE, 0xD0), (0x20FF, 0x02)], status=0x22
                )[0],
                0x2100,
            )
            for opcode, taken_status, clear_status in (
                (0x10, 0x20, 0xA0),  # BPL / N clear
                (0x30, 0xA0, 0x20),  # BMI / N set
                (0x50, 0x20, 0x60),  # BVC / V clear
                (0x70, 0x60, 0x20),  # BVS / V set
                (0x90, 0x20, 0x21),  # BCC / C clear
                (0xB0, 0x21, 0x20),  # BCS / C set
                (0xD0, 0x20, 0x22),  # BNE / Z clear
                (0xF0, 0x22, 0x20),  # BEQ / Z set
            ):
                with self.subTest(branch=hex(opcode)):
                    branch = [(0x2100, opcode), (0x2101, 0xFC)]
                    self.assertEqual(
                        step_target(0x2100, branch, status=taken_status)[0],
                        0x20FE,
                    )
                    self.assertEqual(
                        step_target(0x2100, branch, status=clear_status)[0],
                        0x2102,
                    )
            self.assertEqual(
                step_target(
                    0x2000,
                    [(0x2000, 0x60), (0x01FA, 0x55), (0x01FB, 0x34)],
                    sp=0xF9,
                )[0],
                0x3456,
            )
            self.assertEqual(
                step_target(
                    0x2000,
                    [(0x2000, 0x40), (0x01FA, 0x78), (0x01FB, 0x56)],
                    sp=0xF8,
                )[0],
                0x5678,
            )
            _, unsupported = step_target(0x2000, [(0x2000, 0x00)])
            self.assertEqual(unsupported["registers"]["a"], 2)
            self.assertEqual(unsupported["registers"]["p"] & 1, 1)
            _, jammed = step_target(0x2000, [(0x2000, 0x02)])
            self.assertEqual(jammed["registers"]["a"], 2)
            self.assertEqual(jammed["registers"]["p"] & 1, 1)

            basic_visible = run_resident(
                "step_target_is_safe",
                [("step_target", 0xA000, True), ("0x0001", 0x37, False)],
                [],
            )
            self.assertEqual(basic_visible["registers"]["p"] & 1, 1)
            basic_banked_out = run_resident(
                "step_target_is_safe",
                [("step_target", 0xA000, True), ("0x0001", 0x36, False)],
                [],
            )
            self.assertEqual(basic_banked_out["registers"]["p"] & 1, 0)

            prepared = run_resident(
                "prepare_step",
                [
                    ("target_pc", 0x2000, True),
                    ("0x2000", 0xEA, False),
                    ("0x2001", 0x7F, False),
                ],
                [
                    "step_active:1",
                    "step_temp_armed:1",
                    "step_original:1",
                    "step_target:2",
                    "0x2001:1",
                ],
            )
            self.assertEqual(prepared["dumps"]["step_active"], [1])
            self.assertEqual(prepared["dumps"]["step_temp_armed"], [1])
            self.assertEqual(prepared["dumps"]["step_original"], [0x7F])
            self.assertEqual(prepared["dumps"]["0x2001"], [0])

            finished = run_resident(
                "finish_step",
                [
                    ("step_active", 1, False),
                    ("step_temp_armed", 1, False),
                    ("step_target", 0x2001, True),
                    ("step_original", 0x7F, False),
                    ("step_rearm_index", 0, False),
                    ("breakpoint_id", 7, False),
                    ("breakpoint_armed", 0, False),
                    ("breakpoint_lo", 0x00, False),
                    ("breakpoint_hi", 0x20, False),
                    ("0x2000", 0xEA, False),
                    ("0x2001", 0x00, False),
                ],
                [
                    "step_active:1",
                    "step_temp_armed:1",
                    "step_rearm_index:1",
                    "breakpoint_armed:1",
                    "0x2000:2",
                ],
            )
            self.assertEqual(finished["dumps"]["step_active"], [0])
            self.assertEqual(finished["dumps"]["step_temp_armed"], [0])
            self.assertEqual(finished["dumps"]["step_rearm_index"], [0xFF])
            self.assertEqual(finished["dumps"]["breakpoint_armed"], [1])
            self.assertEqual(finished["dumps"]["0x2000"], [0, 0x7F])

    def test_imported_samples_report_process_function_and_statement_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_linked_project(Path(tmp))
            code_map = project / ".action" / "code-map.sqlite3"
            with closing(sqlite3.connect(code_map)) as database:
                rows = database.execute(
                    "SELECT caller,address,line FROM linked_lines "
                    "WHERE caller IN ('HELPER','MAIN') ORDER BY address"
                ).fetchall()
            helper = next(row for row in rows if row[0] == "HELPER")
            main = next(row for row in rows if row[0] == "MAIN")
            samples = project / "samples.txt"
            samples.write_text(
                f"${helper[1]:04x} 3\n"
                f"0x{main[1]:04x} 1\n"
                "$c000 2 # deliberately outside the linked image\n",
                encoding="ascii",
            )

            imported = self.run_tool(
                project, "actprof", "main", "import", str(samples), "1000"
            )
            self.assertIn("ACTPROF IMPORTED 1\n", imported.stdout)
            self.assertIn("MODE IMPORTED_PC_SAMPLE\n", imported.stdout)
            self.assertIn("SAMPLES 6\n", imported.stdout)
            self.assertIn("TOTAL_TIME_US 6000\n", imported.stdout)
            self.assertIn(
                "FUNCTION HELPER SAMPLES 3 TIME_US 3000 PERCENT 50.00\n",
                imported.stdout,
            )
            self.assertIn(
                "FUNCTION MAIN SAMPLES 1 TIME_US 1000 PERCENT 16.67\n",
                imported.stdout,
            )
            self.assertIn("STATEMENT SRC/MAIN.ACT:", imported.stdout)
            self.assertIn(
                "UNMAPPED addresses SAMPLES 2 TIME_US 2000 PERCENT 33.33\n",
                imported.stdout,
            )

            profile = project / ".action" / "profile.sqlite3"
            self.assertTrue(profile.is_file())
            with closing(sqlite3.connect(profile)) as database:
                self.assertEqual(database.execute("PRAGMA user_version").fetchone()[0], 1)
                run = database.execute(
                    "SELECT module,mode,interval_us,total_samples,unmapped_samples "
                    "FROM profile_runs"
                ).fetchone()
                self.assertEqual(run, ("MAIN", "IMPORTED_PC_SAMPLE", 1000, 6, 2))
                mapped = database.execute(
                    "SELECT procedure,sum(count) FROM profile_samples "
                    "WHERE procedure IS NOT NULL GROUP BY procedure ORDER BY procedure"
                ).fetchall()
                self.assertEqual(mapped, [("HELPER", 3), ("MAIN", 1)])

            report = self.run_tool(project, "actprof", "main", "report")
            self.assertIn("ACTPROF RUN 1\n", report.stdout)
            self.assertIn("PROCESS MAIN SAMPLES 6", report.stdout)

    def test_live_actdbg_uses_real_client_against_fake_idun_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = self.make_linked_project(home)
            code_map = project / ".action" / "code-map.sqlite3"
            with closing(sqlite3.connect(code_map)) as database:
                helper_address, helper_line = database.execute(
                    "SELECT address,line FROM linked_lines "
                    "WHERE caller='HELPER' ORDER BY address LIMIT 1"
                ).fetchone()
                main_address = database.execute(
                    "SELECT address FROM linked_lines "
                    "WHERE caller='MAIN' ORDER BY address LIMIT 1"
                ).fetchone()[0]

            prepared = self.run_tool(
                project, "actdbg", "main", "break", str(helper_line)
            )
            self.assertIn("BREAKPOINT", prepared.stdout)
            env, log = self.fake_target_environment(
                home, "debug", [helper_address, helper_address, main_address], 1000
            )
            load_address = int.from_bytes(
                (project / "BIN" / "MAIN.PRG").read_bytes()[:2], "little"
            )
            commands = "\n".join(
                (
                    "info",
                    "args DATA.DBF 10,20,A",
                    "memory $0f04 4",
                    "memory $0800 8",
                    f"memory ${load_address:04x} 4",
                    "run",
                    "wait 500",
                    "step",
                    "sampling on",
                    "run",
                    "wait 500",
                    "halt",
                    "samples",
                    "sampling off",
                    "quit",
                    "",
                )
            )
            live = self.run_tool(
                project,
                "actdbg",
                "main",
                "live",
                env=env,
                input_text=commands,
            )
            self.assertIn("ACTDBG LIVE\n", live.stdout)
            self.assertIn("CAPABILITIES 0x005F\n", live.stdout)
            self.assertIn("BREAKPOINT SYNC 1 TARGET=1", live.stdout)
            self.assertIn("PROGRAM ARGUMENTS 2 ARGC 3\n", live.stdout)
            self.assertIn("MEMORY $0F04 03000008\n", live.stdout)
            self.assertIn("MEMORY $0800 08080D0816080000\n", live.stdout)
            self.assertIn(f"MEMORY ${load_address:04X} ", live.stdout)
            self.assertIn(
                f"EVENT BREAKPOINT_HIT BREAKPOINT=1 PC=${helper_address:04X}\n",
                live.stdout,
            )
            self.assertEqual(live.stdout.count("EVENT BREAKPOINT_HIT BREAKPOINT=1"), 2)
            self.assertIn(f"PC=${(helper_address + 1) & 0xFFFF:04X}\n", live.stdout)
            self.assertIn("SAMPLES 3 INTERVAL_US 1000\n", live.stdout)
            self.assertEqual(live.stderr, "")

            requests = log.read_text(encoding="ascii").splitlines()
            request_names = [line.split()[0] for line in requests]
            for expected in (
                "HELLO",
                "WRITE_MEMORY",
                "WRITE_REGISTERS",
                "BREAK_SET",
                "RUN",
                "STEP",
                "SAMPLE_CONFIG",
                "HALT",
                "SAMPLE_READ",
                "RESET_SESSION",
            ):
                self.assertIn(expected, request_names)
            self.assertGreaterEqual(request_names.count("HELLO"), 2)
            self.assertEqual(request_names[-1], "RESET_SESSION")

            startup_arguments = self.run_tool(
                project,
                "actdbg",
                "main",
                "live",
                "--",
                "DATA.DBF",
                "10,20,A",
                env=env,
                input_text="memory $0f04 4\nmemory $0800 8\nquit\n",
            )
            self.assertIn("MEMORY $0F04 03000008\n", startup_arguments.stdout)
            self.assertIn(
                "MEMORY $0800 08080D0816080000\n",
                startup_arguments.stdout,
            )

    def test_live_actprof_aggregates_fake_target_samples_in_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project = self.make_linked_project(home)
            code_map = project / ".action" / "code-map.sqlite3"
            with closing(sqlite3.connect(code_map)) as database:
                rows = database.execute(
                    "SELECT caller,address FROM linked_lines "
                    "WHERE caller IN ('HELPER','MAIN') ORDER BY address"
                ).fetchall()
            helper_address = next(address for caller, address in rows if caller == "HELPER")
            main_address = next(address for caller, address in rows if caller == "MAIN")
            env, log = self.fake_target_environment(
                home,
                "profile",
                [
                    helper_address,
                    helper_address,
                    helper_address,
                    main_address,
                    0xC000,
                    0xC000,
                ],
                1000,
            )

            result = self.run_tool(
                project, "actprof", "main", "live", "1", env=env
            )
            self.assertIn("ACTPROF COLLECTING 1 SECONDS\n", result.stdout)
            self.assertIn("MODE LIVE_PC_SAMPLE\n", result.stdout)
            self.assertIn("SAMPLES 6\n", result.stdout)
            self.assertIn("TOTAL_TIME_US 6000\n", result.stdout)
            self.assertIn(
                "FUNCTION HELPER SAMPLES 3 TIME_US 3000 PERCENT 50.00\n",
                result.stdout,
            )
            self.assertIn(
                "FUNCTION MAIN SAMPLES 1 TIME_US 1000 PERCENT 16.67\n",
                result.stdout,
            )
            self.assertIn(
                "UNMAPPED addresses SAMPLES 2 TIME_US 2000 PERCENT 33.33\n",
                result.stdout,
            )

            profile = project / ".action" / "profile.sqlite3"
            with closing(sqlite3.connect(profile)) as database:
                run = database.execute(
                    "SELECT mode,interval_us,total_samples,unmapped_samples "
                    "FROM profile_runs"
                ).fetchone()
                self.assertEqual(run, ("LIVE_PC_SAMPLE", 1000, 6, 2))
                functions = database.execute(
                    "SELECT procedure,sum(count) FROM profile_samples "
                    "WHERE procedure IS NOT NULL GROUP BY procedure ORDER BY procedure"
                ).fetchall()
                self.assertEqual(functions, [("HELPER", 3), ("MAIN", 1)])

            requests = log.read_text(encoding="ascii").splitlines()
            request_names = [line.split()[0] for line in requests]
            self.assertIn("RUN", request_names)
            self.assertIn("HALT", request_names)
            self.assertIn("SAMPLE_READ", request_names)
            self.assertEqual(request_names[-1], "RESET_SESSION")


if __name__ == "__main__":
    unittest.main()
