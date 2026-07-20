#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time

API_VERSION = 0x02
STX = 0x02

CMD_MEMORY_GET = 0x01
CMD_MEMORY_SET = 0x02
CMD_REGISTERS_GET = 0x31
CMD_REGISTERS_SET = 0x32
CMD_KEYBOARD_FEED = 0x72
CMD_PING = 0x81
CMD_BANKS_AVAILABLE = 0x82
CMD_REGISTERS_AVAILABLE = 0x83
CMD_EXIT = 0xAA
CMD_QUIT = 0xBB

RESP_MEM_GET = 0x01
RESP_REGISTER_INFO = 0x31
RESP_JAM = 0x61
RESP_STOPPED = 0x62
RESP_RESUMED = 0x63
RESP_PING = 0x81
RESP_EXIT = 0xAA
RESP_QUIT = 0xBB


class ViceUnavailable(RuntimeError):
    pass


class ViceProtocolError(RuntimeError):
    pass


_VICE_VERSION_CACHE: dict[str, str] = {}


def vice_version(path: Path) -> str:
    cache_key = str(path)
    cached = _VICE_VERSION_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        result = subprocess.run(
            [str(path), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5.0,
            check=False,
        )
        line = result.stdout.splitlines()[0].strip() if result.stdout else ""
    except Exception:
        line = ""
    _VICE_VERSION_CACHE[cache_key] = line
    return line


def prefer_known_good_linux_vice(candidate: Path) -> Path:
    if os.name == "nt":
        return candidate
    distro_candidate = Path("/usr/bin/x64sc")
    if candidate == distro_candidate or not distro_candidate.is_file():
        return candidate
    if vice_version(candidate).startswith("x64sc (VICE 3.10)") and vice_version(distro_candidate).startswith(
        "x64sc (VICE 3.7.1)"
    ):
        return distro_candidate.resolve()
    return candidate


def locate_x64sc() -> Path:
    windows_candidates = (
        Path(r"C:\c64\vice\GTK3VICE-3.10-win64\bin\x64sc.exe"),
        Path("/mnt/c/c64/vice/GTK3VICE-3.10-win64/bin/x64sc.exe"),
    )
    candidate = shutil.which("x64sc")
    if not candidate:
        for candidate_path in windows_candidates:
            if candidate_path.is_file():
                return candidate_path.resolve()
        raise ViceUnavailable("x64sc not found on PATH")
    return prefer_known_good_linux_vice(Path(candidate).resolve())


def reserve_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def petscii_bytes(text: str) -> bytes:
    return text.replace("\n", "\r").encode("ascii", errors="strict")


def petscii_to_ascii(code: int) -> str:
    if code == 0x0D:
        return "\n"
    if code == 0x0A:
        return "\r"
    if code <= 0x1F:
        return "."
    if code in {0xA0, 0xE0}:
        return " "
    if 0xC1 <= code <= 0xDA:
        return chr(ord("A") + code - 0xC1)
    if 0x41 <= code <= 0x5A:
        return chr(ord("a") + code - 0x41)
    if 0x20 <= code <= 0x7E:
        return chr(code)
    return "."


def screen_code_to_ascii(code: int) -> str:
    code &= 0x7F
    if code <= 0x1F:
        code += 0x40
    elif 0x40 <= code <= 0x5F:
        code += 0x20
    return petscii_to_ascii(code)


def screen_ram_to_text(data: bytes) -> str:
    if len(data) < 1000:
        raise ViceProtocolError(f"expected 1000 screen bytes, got {len(data)}")
    chars = [screen_code_to_ascii(byte) for byte in data[:1000]]
    rows = ["".join(chars[row * 40 : (row + 1) * 40]).rstrip() for row in range(25)]
    return "\n".join(rows).strip()


class BinaryMonitorClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.request_id = 1

    def connect(self, deadline: float) -> None:
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                sock.settimeout(self.timeout)
                self.sock = sock
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        raise ViceUnavailable(f"unable to connect to VICE binary monitor on {self.host}:{self.port}: {last_error}")

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _recv_exact(self, length: int) -> bytes:
        if self.sock is None:
            raise ViceProtocolError("monitor socket is not connected")
        chunks = bytearray()
        while len(chunks) < length:
            part = self.sock.recv(length - len(chunks))
            if not part:
                raise ViceProtocolError("VICE monitor connection closed unexpectedly")
            chunks.extend(part)
        return bytes(chunks)

    def _read_response(self) -> tuple[int, int, int, bytes]:
        header = self._recv_exact(12)
        if header[0] != STX:
            raise ViceProtocolError(f"unexpected response prefix: 0x{header[0]:02x}")
        version = header[1]
        if version != API_VERSION:
            raise ViceProtocolError(f"unexpected VICE monitor API version: {version}")
        body_len = struct.unpack_from("<I", header, 2)[0]
        response_type = header[6]
        error_code = header[7]
        request_id = struct.unpack_from("<I", header, 8)[0]
        body = self._recv_exact(body_len) if body_len else b""
        return response_type, error_code, request_id, body

    def _send_command(self, command_type: int, body: bytes = b"") -> int:
        if self.sock is None:
            raise ViceProtocolError("monitor socket is not connected")
        request_id = self.request_id
        self.request_id += 1
        packet = bytearray()
        packet.append(STX)
        packet.append(API_VERSION)
        packet.extend(struct.pack("<I", len(body)))
        packet.extend(struct.pack("<I", request_id))
        packet.append(command_type)
        packet.extend(body)
        self.sock.sendall(packet)
        return request_id

    def command(
        self,
        command_type: int,
        body: bytes = b"",
        timeout: float | None = None,
        *,
        response_type: int | None = None,
    ) -> bytes:
        request_id = self._send_command(command_type, body)
        expected_response = command_type if response_type is None else response_type
        deadline = time.monotonic() + (timeout if timeout is not None else self.timeout)
        while time.monotonic() < deadline:
            response_type, error_code, response_request_id, payload = self._read_response()
            if response_request_id != request_id:
                continue
            if error_code != 0:
                raise ViceProtocolError(
                    f"VICE monitor command 0x{command_type:02x} failed with error 0x{error_code:02x}"
                )
            if response_type != expected_response:
                raise ViceProtocolError(
                    f"VICE monitor command 0x{command_type:02x} got response "
                    f"0x{response_type:02x}; expected 0x{expected_response:02x}"
                )
            return payload
        raise ViceProtocolError(f"timed out waiting for VICE monitor response 0x{command_type:02x}")

    def ping(self) -> None:
        self.command(CMD_PING)

    def banks_available(self) -> dict[str, int]:
        payload = self.command(CMD_BANKS_AVAILABLE)
        if len(payload) < 2:
            raise ViceProtocolError("banks-available response was too short")
        count = struct.unpack_from("<H", payload, 0)[0]
        offset = 2
        banks: dict[str, int] = {}
        for _ in range(count):
            if offset >= len(payload):
                raise ViceProtocolError("truncated banks-available item")
            item_size = payload[offset]
            item_end = offset + 1 + item_size
            if item_size < 3 or item_end > len(payload):
                raise ViceProtocolError("invalid banks-available item")
            bank_id = struct.unpack_from("<H", payload, offset + 1)[0]
            name_length = payload[offset + 3]
            if offset + 4 + name_length > item_end:
                raise ViceProtocolError("invalid banks-available name")
            name = payload[offset + 4 : offset + 4 + name_length].decode(
                "ascii", errors="strict"
            )
            banks[name.lower()] = bank_id
            offset = item_end
        if offset != len(payload):
            raise ViceProtocolError("trailing banks-available data")
        return banks

    def resume(self) -> None:
        self.command(CMD_EXIT)
        end = time.monotonic() + self.timeout
        while time.monotonic() < end:
            response_type, error_code, _request_id, _payload = self._read_response()
            if error_code != 0:
                raise ViceProtocolError(f"VICE monitor resume failed with error 0x{error_code:02x}")
            if response_type == RESP_RESUMED:
                return
        raise ViceProtocolError("timed out waiting for VICE resumed event")

    def quit_emulator(self) -> None:
        try:
            self.command(CMD_QUIT)
        except Exception:
            pass

    def keyboard_feed(self, text: str) -> None:
        encoded = petscii_bytes(text)
        if len(encoded) > 0xFF:
            raise ViceProtocolError("keyboard feed text is too long for a single packet")
        self.command(CMD_KEYBOARD_FEED, bytes((len(encoded),)) + encoded)
        self.resume()

    def memory_set(
        self,
        start: int,
        data: bytes,
        *,
        memspace: int = 0,
        bank: int = 0,
        side_effects: bool = False,
    ) -> None:
        if not data:
            raise ViceProtocolError("cannot write an empty memory segment")
        end = start + len(data) - 1
        if start < 0 or end > 0xFFFF:
            raise ViceProtocolError("memory write falls outside the 16-bit address space")
        body = bytes((1 if side_effects else 0,))
        body += struct.pack("<HHBH", start, end, memspace, bank)
        self.command(CMD_MEMORY_SET, body + data)

    def register_ids(self, *, memspace: int = 0) -> dict[str, int]:
        response = self.command(CMD_REGISTERS_AVAILABLE, bytes((memspace,)))
        if len(response) < 2:
            raise ViceProtocolError("register-list response was too short")
        count = struct.unpack_from("<H", response, 0)[0]
        offset = 2
        registers: dict[str, int] = {}
        for _ in range(count):
            if offset >= len(response):
                raise ViceProtocolError("truncated register-list item")
            item_size = response[offset]
            item_end = offset + item_size + 1
            if item_size < 3 or item_end > len(response):
                raise ViceProtocolError("malformed register-list item")
            register_id = response[offset + 1]
            name_length = response[offset + 3]
            name_start = offset + 4
            name_end = name_start + name_length
            if name_end > item_end:
                raise ViceProtocolError("malformed register name")
            name = response[name_start:name_end].decode("ascii", errors="strict").upper()
            registers[name] = register_id
            offset = item_end
        if offset != len(response):
            raise ViceProtocolError("unexpected trailing register-list data")
        return registers

    def registers_set(self, values: dict[int, int], *, memspace: int = 0) -> None:
        body = bytearray((memspace,))
        body.extend(struct.pack("<H", len(values)))
        for register_id, value in values.items():
            if not 0 <= register_id <= 0xFF or not 0 <= value <= 0xFFFF:
                raise ViceProtocolError("register ID or value is out of range")
            body.extend((3, register_id))
            body.extend(struct.pack("<H", value))
        self.command(
            CMD_REGISTERS_SET,
            bytes(body),
            response_type=RESP_REGISTER_INFO,
        )

    def registers_get(self, *, memspace: int = 0) -> dict[int, int]:
        response = self.command(
            CMD_REGISTERS_GET,
            bytes((memspace,)),
            response_type=RESP_REGISTER_INFO,
        )
        if len(response) < 2:
            raise ViceProtocolError("register response was too short")
        count = struct.unpack_from("<H", response, 0)[0]
        offset = 2
        values: dict[int, int] = {}
        for _ in range(count):
            if offset >= len(response):
                raise ViceProtocolError("truncated register response item")
            item_size = response[offset]
            item_end = offset + item_size + 1
            if item_size < 3 or item_end > len(response):
                raise ViceProtocolError("malformed register response item")
            register_id = response[offset + 1]
            values[register_id] = struct.unpack_from("<H", response, offset + 2)[0]
            offset = item_end
        if offset != len(response):
            raise ViceProtocolError("unexpected trailing register response data")
        return values

    def memory_get(self, start: int, end: int, *, memspace: int = 0, bank: int = 0, side_effects: bool = False) -> bytes:
        body = bytes((1 if side_effects else 0,))
        body += struct.pack("<HHBH", start, end, memspace, bank)
        response = self.command(CMD_MEMORY_GET, body)
        if len(response) < 2:
            raise ViceProtocolError("memory-get response was too short")
        segment_len = struct.unpack_from("<H", response, 0)[0]
        data = response[2:]
        if segment_len != len(data):
            raise ViceProtocolError(f"memory-get length mismatch: header={segment_len} actual={len(data)}")
        self.resume()
        return data


class ViceHarness:
    def __init__(
        self,
        *,
        x64sc_path: Path | None = None,
        disk_image: Path | None = None,
        true_drive: bool = True,
        port: int | None = None,
        timeout: float = 8.0,
    ):
        self.x64sc_path = x64sc_path or locate_x64sc()
        self.disk_image = disk_image.resolve() if disk_image is not None else None
        self.true_drive = true_drive
        self.port = port or reserve_tcp_port()
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None
        self.monitor = BinaryMonitorClient("127.0.0.1", self.port, timeout=timeout)

    def command(self, *extra: str) -> list[str]:
        command = [
            str(self.x64sc_path),
            "-console",
            "-default",
            "-binarymonitor",
            "-binarymonitoraddress",
            f"ip4://127.0.0.1:{self.port}",
            "-reu",
            "-reusize",
            "16384",
            "-warp",
            "+sound",
            "-sounddev",
            "dummy",
            "-keybuf-delay",
            "4",
        ]
        if self.disk_image is not None:
            command[3:3] = [
                "-8",
                str(self.disk_image),
                "-drive8type",
                "1541",
                "-drive8truedrive"
                if getattr(self, "true_drive", True)
                else "+drive8truedrive",
                "+virtualdev8"
                if getattr(self, "true_drive", True)
                else "-virtualdev8",
            ]
        command.extend(extra)
        return command

    def start(self) -> None:
        env = dict(os.environ)
        self.process = subprocess.Popen(
            self.command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        deadline = time.monotonic() + 20.0
        try:
            self.monitor.connect(deadline)
            self.monitor.ping()
            self.monitor.resume()
        except Exception as exc:
            self.stop()
            raise ViceUnavailable(f"failed to start VICE monitor session: {exc}") from exc

    def stop(self) -> None:
        process = self.process
        if process is None:
            self.monitor.close()
            return
        try:
            if process.poll() is None:
                # Let VICE flush attached disk images before falling back to a
                # host-side termination.  This matters for true-drive writes,
                # whose directory sector can still be dirty when the program's
                # KERNAL CLOSE has returned.
                graceful_quit = getattr(self.monitor, "quit_emulator", None)
                if callable(graceful_quit):
                    graceful_quit()
                else:
                    process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=5)
            else:
                process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
        finally:
            self.monitor.close()
            self.process = None

    def __enter__(self) -> "ViceHarness":
        self.start()
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.stop()

    def read_screen_text(self) -> str:
        return screen_ram_to_text(self.monitor.memory_get(0x0400, 0x07E7))

    def feed_keys(self, text: str) -> None:
        self.monitor.keyboard_feed(text)

    def load_prg(self, path: Path, *, entry: int | None = None) -> int:
        payload = path.read_bytes()
        if len(payload) < 3:
            raise ViceProtocolError(f"PRG is too short: {path}")
        load_address = struct.unpack_from("<H", payload, 0)[0]
        machine_code = payload[2:]
        if load_address + len(machine_code) > 0x10000:
            raise ViceProtocolError(f"PRG crosses the 16-bit address boundary: {path}")
        self.monitor.memory_set(load_address, machine_code)
        registers = self.monitor.register_ids()
        try:
            pc_id = registers["PC"]
            sp_id = registers["SP"]
        except KeyError as exc:
            raise ViceProtocolError(f"VICE did not expose required register {exc.args[0]}") from exc
        start_address = load_address if entry is None else entry
        if not 0 <= start_address <= 0xFFFF:
            raise ViceProtocolError("PRG entry address is out of range")
        self.monitor.registers_set({pc_id: start_address, sp_id: 0xFF})
        return start_address

    def wait_for_screen_contains(self, fragment: str, *, timeout: float, poll_interval: float = 0.5) -> str:
        deadline = time.monotonic() + timeout
        last_screen = ""
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise ViceUnavailable(f"x64sc exited early while waiting for screen text.\nstdout:\n{stdout}\nstderr:\n{stderr}")
            last_screen = self.read_screen_text()
            if fragment in last_screen:
                return last_screen
            time.sleep(poll_interval)
        raise ViceUnavailable(f"timed out waiting for screen text {fragment!r}; last screen was:\n{last_screen}")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or inspect ActionC64U output in headless VICE")
    parser.add_argument("--disk-image", help="optional C64 disk image to attach")
    parser.add_argument("--prg", help="direct PRG to load into C64 memory and start")
    parser.add_argument("--entry", type=lambda value: int(value, 0), help="optional PRG entry address")
    parser.add_argument("--expected", help="screen text to wait for")
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for expected screen text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        harness = ViceHarness(disk_image=Path(args.disk_image) if args.disk_image else None)
    except ViceUnavailable as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        with harness as vice:
            if args.prg:
                vice.load_prg(Path(args.prg), entry=args.entry)
                vice.monitor.resume()
            if args.expected:
                screen = vice.wait_for_screen_contains(args.expected, timeout=args.timeout)
            elif args.prg:
                time.sleep(min(args.timeout, 1.0))
                screen = vice.read_screen_text()
            else:
                parser.error("provide --prg and/or --expected")
    except ViceUnavailable as exc:
        print(exc, file=sys.stderr)
        return 1

    print(screen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
