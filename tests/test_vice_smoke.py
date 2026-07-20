from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from vice_harness import (  # noqa: E402
    BinaryMonitorClient,
    CMD_REGISTERS_GET,
    RESP_REGISTER_INFO,
    ViceHarness,
)


class TestViceSmoke(unittest.TestCase):
    def test_stop_drains_process_pipes(self) -> None:
        class FakeMonitor:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        class FakeProcess:
            def __init__(self) -> None:
                self.terminated = False
                self.killed = False
                self.communicate_timeouts: list[float | None] = []

            def poll(self) -> int | None:
                return None

            def terminate(self) -> None:
                self.terminated = True

            def kill(self) -> None:
                self.killed = True

            def communicate(self, timeout: float | None = None) -> tuple[str, str]:
                self.communicate_timeouts.append(timeout)
                return ("", "")

        harness = ViceHarness.__new__(ViceHarness)
        monitor = FakeMonitor()
        process = FakeProcess()
        harness.monitor = monitor
        harness.process = process

        harness.stop()

        self.assertTrue(monitor.closed)
        self.assertTrue(process.terminated)
        self.assertFalse(process.killed)
        self.assertEqual(process.communicate_timeouts, [5])
        self.assertIsNone(harness.process)

    def test_command_defaults_to_headless_direct_prg_environment(self) -> None:
        harness = ViceHarness.__new__(ViceHarness)
        harness.x64sc_path = Path("/usr/bin/x64sc")
        harness.disk_image = None
        harness.port = 45678

        command = harness.command()

        self.assertIn("-console", command)
        self.assertIn("-binarymonitor", command)
        self.assertNotIn("-8", command)
        self.assertNotIn("UDOS", " ".join(command).upper())

    def test_command_attaches_an_explicit_optional_disk(self) -> None:
        harness = ViceHarness.__new__(ViceHarness)
        harness.x64sc_path = Path("/usr/bin/x64sc")
        harness.disk_image = Path("/tmp/c64-workspace.d64")
        harness.port = 45678

        command = harness.command()

        self.assertIn("-8", command)
        self.assertIn("/tmp/c64-workspace.d64", command)

    def test_load_prg_writes_payload_and_sets_named_registers(self) -> None:
        class FakeMonitor:
            def __init__(self) -> None:
                self.memory_writes: list[tuple[int, bytes]] = []
                self.register_writes: list[dict[int, int]] = []

            def memory_set(self, start: int, data: bytes) -> None:
                self.memory_writes.append((start, data))

            def register_ids(self) -> dict[str, int]:
                return {"PC": 9, "SP": 12}

            def registers_set(self, values: dict[int, int]) -> None:
                self.register_writes.append(values)

        harness = ViceHarness.__new__(ViceHarness)
        harness.monitor = FakeMonitor()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "main.prg"
            path.write_bytes(bytes((0x00, 0x20, 0xA9, 0x01, 0x60)))

            entry = harness.load_prg(path)

        self.assertEqual(entry, 0x2000)
        self.assertEqual(harness.monitor.memory_writes, [(0x2000, b"\xA9\x01\x60")])
        self.assertEqual(harness.monitor.register_writes, [{9: 0x2000, 12: 0xFF}])

    def test_registers_get_decodes_binary_monitor_items(self) -> None:
        client = BinaryMonitorClient("127.0.0.1", 1)
        calls: list[tuple[int, bytes, int | None]] = []

        def command(
            command_type: int,
            body: bytes = b"",
            timeout: float | None = None,
            *,
            response_type: int | None = None,
        ) -> bytes:
            del timeout
            calls.append((command_type, body, response_type))
            return bytes((2, 0, 3, 7, 0x34, 0x12, 3, 9, 0xCD, 0xAB))

        client.command = command  # type: ignore[method-assign]

        self.assertEqual(client.registers_get(), {7: 0x1234, 9: 0xABCD})
        self.assertEqual(calls, [(CMD_REGISTERS_GET, b"\x00", RESP_REGISTER_INFO)])


if __name__ == "__main__":
    unittest.main()
