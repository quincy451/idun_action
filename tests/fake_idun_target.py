#!/usr/bin/env python3
"""Deterministic Unix-socket stand-in for the Idun C64 target service.

The Linux tools launch this through a temporary executable named ``idunsh``.
It implements the same IDBG record protocol as ``actsvc`` so ACTDBG and
ACTPROF can be tested end to end on hosts without an attached cartridge.
"""

from __future__ import annotations

import os
import socket
import struct
import sys
import time
from pathlib import Path


MAGIC = b"IDBG"
HEADER = struct.Struct("<4sBBBBHHH")
RESPONSE = 0x01
EVENT = 0x02
ERROR = 0x04

HELLO = 1
TARGET_INFO = 2
READ_MEMORY = 3
WRITE_MEMORY = 4
READ_REGISTERS = 5
WRITE_REGISTERS = 6
HALT = 7
RUN = 8
STEP = 9
BREAK_SET = 10
BREAK_CLEAR = 11
BREAK_LIST = 12
SAMPLE_CONFIG = 13
SAMPLE_READ = 14
PING = 15
RESET_SESSION = 16
STOPPED = 64
BREAKPOINT_HIT = 65

OK = 0
UNSUPPORTED = 2
BAD_ARGUMENT = 3
UNSAFE_ADDRESS = 4
BAD_STATE = 5
NO_BREAKPOINT_SLOT = 6
NOT_FOUND = 7

CAPABILITIES = 0x005F
MAX_PAYLOAD = 240

MESSAGE_NAMES = {
    HELLO: "HELLO",
    TARGET_INFO: "TARGET_INFO",
    READ_MEMORY: "READ_MEMORY",
    WRITE_MEMORY: "WRITE_MEMORY",
    READ_REGISTERS: "READ_REGISTERS",
    WRITE_REGISTERS: "WRITE_REGISTERS",
    HALT: "HALT",
    RUN: "RUN",
    STEP: "STEP",
    BREAK_SET: "BREAK_SET",
    BREAK_CLEAR: "BREAK_CLEAR",
    BREAK_LIST: "BREAK_LIST",
    SAMPLE_CONFIG: "SAMPLE_CONFIG",
    SAMPLE_READ: "SAMPLE_READ",
    PING: "PING",
    RESET_SESSION: "RESET_SESSION",
}


def checksum(header_without_checksum: bytes, payload: bytes) -> int:
    return (sum(header_without_checksum) + sum(payload)) & 0xFFFF


def encode_packet(message: int, flags: int, sequence: int, payload: bytes) -> bytes:
    prefix = struct.pack(
        "<4sBBBBHH", MAGIC, 1, 0, message, flags, sequence, len(payload)
    )
    return prefix + struct.pack("<H", checksum(prefix, payload)) + payload


def receive_exact(connection: socket.socket, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        block = connection.recv(count - len(data))
        if not block:
            raise EOFError
        data.extend(block)
    return bytes(data)


def receive_packet(connection: socket.socket) -> tuple[int, int, int, bytes]:
    header = receive_exact(connection, HEADER.size)
    magic, major, _minor, message, flags, sequence, size, expected = HEADER.unpack(
        header
    )
    if magic != MAGIC or major != 1 or size > MAX_PAYLOAD:
        raise ValueError("bad IDBG header")
    payload = receive_exact(connection, size)
    if checksum(header[:12], payload) != expected:
        raise ValueError("bad IDBG checksum")
    return message, flags, sequence, payload


def parse_samples() -> list[int]:
    values: list[int] = []
    for item in os.environ.get("ACTION_FAKE_TARGET_SAMPLES", "").split(","):
        item = item.strip()
        if item:
            values.append(int(item, 0) & 0xFFFF)
    return values


class FakeTarget:
    def __init__(self, connection: socket.socket) -> None:
        self.connection = connection
        self.memory = bytearray(65536)
        self.a = 0
        self.x = 0
        self.y = 0
        self.sp = 0xFD
        self.status = 0x20
        self.pc = 0x1000
        self.state = 0
        self.sampling = False
        self.sample_seeded = False
        self.sample_template = parse_samples()
        self.samples: list[int] = []
        self.breakpoints: dict[int, tuple[int, int, bool]] = {}
        self.next_breakpoint = 1
        self.mode = os.environ.get("ACTION_FAKE_TARGET_MODE", "debug").lower()
        configured_log = os.environ.get("ACTION_FAKE_TARGET_LOG")
        self.log_path = Path(configured_log) if configured_log else None

    def log(self, text: str) -> None:
        if self.log_path is None:
            return
        with self.log_path.open("a", encoding="ascii") as output:
            output.write(text + "\n")

    def send_response(
        self, message: int, sequence: int, status: int = OK, data: bytes = b""
    ) -> None:
        flags = RESPONSE | (ERROR if status != OK else 0)
        self.connection.sendall(
            encode_packet(message, flags, sequence, bytes((status,)) + data)
        )

    def send_breakpoint_event(self, breakpoint_id: int, address: int) -> None:
        payload = bytes((breakpoint_id, address & 0xFF, address >> 8))
        self.connection.sendall(encode_packet(BREAKPOINT_HIT, EVENT, 0, payload))

    def send_stopped_event(self) -> None:
        self.connection.sendall(
            encode_packet(STOPPED, EVENT, 0, struct.pack("<H", self.pc))
        )

    @staticmethod
    def word(payload: bytes, offset: int = 0) -> int:
        return payload[offset] | (payload[offset + 1] << 8)

    @staticmethod
    def safe_write(address: int, count: int) -> bool:
        end = address + count
        return end <= 0xD000 and not (address < 0xD000 and end > 0xC000)

    def process(self, message: int, sequence: int, payload: bytes) -> bool:
        name = MESSAGE_NAMES.get(message, f"MESSAGE_{message}")
        detail = ""
        if message in (READ_MEMORY, WRITE_MEMORY, BREAK_SET) and len(payload) >= 2:
            detail = f" ${self.word(payload):04X}"
        if message == WRITE_MEMORY and len(payload) >= 3:
            detail += f" {payload[2]}"
        self.log(name + detail)

        if message == HELLO:
            if payload:
                self.send_response(message, sequence, BAD_ARGUMENT)
            else:
                data = struct.pack("<HHHH", MAX_PAYLOAD, CAPABILITIES, 0xC000, 0xCFFF)
                self.send_response(message, sequence, data=data)
        elif message == TARGET_INFO:
            data = bytes((self.state,)) + struct.pack("<HHH", self.pc, 0xC000, 0xCFFF)
            self.send_response(message, sequence, data=data)
        elif message == READ_MEMORY:
            if len(payload) != 3 or payload[2] == 0:
                self.send_response(message, sequence, BAD_ARGUMENT)
            else:
                address = self.word(payload)
                count = payload[2]
                if address + count > 65536:
                    self.send_response(message, sequence, UNSAFE_ADDRESS)
                else:
                    self.send_response(
                        message, sequence, data=bytes(self.memory[address : address + count])
                    )
        elif message == WRITE_MEMORY:
            if len(payload) < 4 or len(payload) != payload[2] + 3:
                self.send_response(message, sequence, BAD_ARGUMENT)
            else:
                address = self.word(payload)
                data = payload[3:]
                if not self.safe_write(address, len(data)):
                    self.send_response(message, sequence, UNSAFE_ADDRESS)
                else:
                    self.memory[address : address + len(data)] = data
                    self.send_response(message, sequence)
        elif message == READ_REGISTERS:
            data = bytes((self.a, self.x, self.y, self.sp, self.status))
            data += struct.pack("<H", self.pc) + bytes((self.state,))
            self.send_response(message, sequence, data=data)
        elif message == WRITE_REGISTERS:
            if len(payload) != 7 or self.state == 1:
                self.send_response(
                    message, sequence, BAD_STATE if self.state == 1 else BAD_ARGUMENT
                )
            else:
                self.a, self.x, self.y, self.sp, self.status = payload[:5]
                self.pc = self.word(payload, 5)
                self.log(f"PROGRAM_PC ${self.pc:04X}")
                self.send_response(message, sequence)
        elif message == HALT:
            self.state = 0
            self.send_response(message, sequence)
        elif message == RUN:
            if self.state == 2:
                self.send_response(message, sequence, BAD_STATE)
            else:
                self.state = 1
                if self.sampling and not self.sample_seeded:
                    self.samples.extend(self.sample_template)
                    self.sample_seeded = True
                pending = next(
                    (
                        (breakpoint_id, original)
                        for breakpoint_id, (address, original, armed) in self.breakpoints.items()
                        if address == self.pc and not armed
                    ),
                    None,
                )
                if pending is not None:
                    breakpoint_id, original = pending
                    address = self.pc
                    self.memory[address] = 0
                    self.breakpoints[breakpoint_id] = (address, original, True)
                self.send_response(message, sequence)
                armed_breakpoint = next(
                    (
                        (breakpoint_id, address, original)
                        for breakpoint_id, (address, original, armed) in sorted(
                            self.breakpoints.items()
                        )
                        if armed
                    ),
                    None,
                )
                if self.mode == "debug" and pending is None and armed_breakpoint:
                    breakpoint_id, address, original = armed_breakpoint
                    self.memory[address] = original
                    self.breakpoints[breakpoint_id] = (address, original, False)
                    self.pc = address
                    self.state = 0
                    self.send_breakpoint_event(breakpoint_id, address)
        elif message == STEP:
            if self.state != 0:
                self.send_response(message, sequence, BAD_STATE)
            else:
                pending = next(
                    (
                        (breakpoint_id, address, original)
                        for breakpoint_id, (address, original, armed) in self.breakpoints.items()
                        if address == self.pc and not armed
                    ),
                    None,
                )
                self.pc = (self.pc + 1) & 0xFFFF
                if pending is not None:
                    breakpoint_id, address, original = pending
                    self.memory[address] = 0
                    self.breakpoints[breakpoint_id] = (address, original, True)
                self.send_response(message, sequence)
                landed = next(
                    (
                        (breakpoint_id, address, original)
                        for breakpoint_id, (address, original, armed) in self.breakpoints.items()
                        if address == self.pc and armed
                    ),
                    None,
                )
                if landed is None:
                    self.send_stopped_event()
                else:
                    breakpoint_id, address, original = landed
                    self.memory[address] = original
                    self.breakpoints[breakpoint_id] = (address, original, False)
                    self.send_breakpoint_event(breakpoint_id, address)
        elif message == BREAK_SET:
            if len(payload) != 2:
                self.send_response(message, sequence, BAD_ARGUMENT)
            else:
                address = self.word(payload)
                duplicate = next(
                    (item for item in self.breakpoints.items() if item[1][0] == address),
                    None,
                )
                if duplicate is not None:
                    self.send_response(message, sequence, data=bytes((duplicate[0],)))
                elif (
                    address < 0x0200
                    or address >= 0xD000
                    or 0xC000 <= address < 0xD000
                ):
                    self.send_response(message, sequence, UNSAFE_ADDRESS)
                elif len(self.breakpoints) >= 8:
                    self.send_response(message, sequence, NO_BREAKPOINT_SLOT)
                else:
                    breakpoint_id = self.next_breakpoint
                    self.next_breakpoint = (self.next_breakpoint + 1) & 0xFF or 1
                    original = self.memory[address]
                    self.breakpoints[breakpoint_id] = (address, original, True)
                    self.memory[address] = 0
                    self.send_response(
                        message, sequence, data=bytes((breakpoint_id,))
                    )
        elif message == BREAK_CLEAR:
            if len(payload) != 1:
                self.send_response(message, sequence, BAD_ARGUMENT)
            elif payload[0] not in self.breakpoints:
                self.send_response(message, sequence, NOT_FOUND)
            else:
                address, original, armed = self.breakpoints.pop(payload[0])
                if armed:
                    self.memory[address] = original
                self.send_response(message, sequence)
        elif message == BREAK_LIST:
            data = bytearray((len(self.breakpoints),))
            for breakpoint_id, (address, original, _armed) in sorted(
                self.breakpoints.items()
            ):
                data.extend((breakpoint_id, address & 0xFF, address >> 8, original))
            self.send_response(message, sequence, data=bytes(data))
        elif message == SAMPLE_CONFIG:
            if len(payload) != 1 or payload[0] > 1:
                self.send_response(message, sequence, BAD_ARGUMENT)
            else:
                self.sampling = payload[0] != 0
                self.sample_seeded = False
                self.samples.clear()
                self.send_response(message, sequence)
        elif message == SAMPLE_READ:
            batch = self.samples[:100]
            del self.samples[: len(batch)]
            interval = int(os.environ.get("ACTION_FAKE_TARGET_INTERVAL_US", "16667"))
            data = bytes((len(batch),)) + struct.pack("<I", interval)
            data += b"".join(struct.pack("<H", address) for address in batch)
            self.send_response(message, sequence, data=data)
        elif message == PING:
            self.send_response(message, sequence, data=payload)
        elif message == RESET_SESSION:
            for address, original, armed in self.breakpoints.values():
                if armed:
                    self.memory[address] = original
            self.breakpoints.clear()
            self.samples.clear()
            self.sampling = False
            self.sample_seeded = False
            self.state = 0
            self.send_response(message, sequence)
            return False
        else:
            self.send_response(message, sequence, UNSUPPORTED)
        return True

    def run(self) -> None:
        while True:
            message, flags, sequence, payload = receive_packet(self.connection)
            if flags != 0:
                raise ValueError("request unexpectedly carried flags")
            if not self.process(message, sequence, payload):
                return


def target_pid(arguments: list[str]) -> str:
    for value in arguments:
        if value.isdecimal():
            return value
    raise ValueError("idunsh invocation has no client PID")


def main() -> int:
    pid = target_pid(sys.argv[1:])
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    socket_path = runtime / pid
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.monotonic() + 5.0
    while True:
        try:
            connection.connect(str(socket_path))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)
    with connection:
        FakeTarget(connection).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
