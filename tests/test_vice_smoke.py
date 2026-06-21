from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from vice_harness import ViceHarness, default_udos_resident_disk  # noqa: E402


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

    def test_command_defaults_to_udos_resident_disk(self) -> None:
        harness = ViceHarness.__new__(ViceHarness)
        harness.x64sc_path = Path("/usr/bin/x64sc")
        harness.disk_image = Path("/tmp/udos-resident.d64")
        harness.port = 45678

        command = harness.command()

        self.assertIn("-8", command)
        self.assertIn("/tmp/udos-resident.d64", command)
        self.assertIn("-binarymonitor", command)
        self.assertNotIn("CPM", " ".join(command).upper())

    def test_default_disk_path_uses_udos_resident_image(self) -> None:
        disk = default_udos_resident_disk()
        self.assertEqual(disk.name, "udos-resident.d64")
        self.assertIn("udos", disk.parts)


if __name__ == "__main__":
    unittest.main()
