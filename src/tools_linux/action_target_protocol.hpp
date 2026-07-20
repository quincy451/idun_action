#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace action_linux::target {

constexpr std::uint8_t kProtocolMajor = 1;
constexpr std::uint8_t kProtocolMinor = 0;
constexpr std::size_t kHeaderSize = 14;
constexpr std::size_t kMaximumPayload = 240;

enum class MessageType : std::uint8_t {
    Hello = 1,
    TargetInfo = 2,
    ReadMemory = 3,
    WriteMemory = 4,
    ReadRegisters = 5,
    WriteRegisters = 6,
    Halt = 7,
    Run = 8,
    Step = 9,
    BreakSet = 10,
    BreakClear = 11,
    BreakList = 12,
    SampleConfig = 13,
    SampleRead = 14,
    Ping = 15,
    ResetSession = 16,
    Stopped = 64,
    BreakpointHit = 65,
    TargetExit = 66,
    TargetFault = 67,
};

enum PacketFlags : std::uint8_t {
    Response = 0x01,
    Event = 0x02,
    Error = 0x04,
};

enum Capability : std::uint16_t {
    Memory = 0x0001,
    RegisterAccess = 0x0002,
    RunHalt = 0x0004,
    SoftwareBreakpoints = 0x0008,
    PcSampling = 0x0010,
    Reu = 0x0020,
    InstructionStep = 0x0040,
};

enum class Status : std::uint8_t {
    Ok = 0,
    BadPacket = 1,
    Unsupported = 2,
    BadArgument = 3,
    UnsafeAddress = 4,
    BadState = 5,
    NoBreakpointSlot = 6,
    NotFound = 7,
    InternalError = 8,
};

struct Packet {
    MessageType type = MessageType::Ping;
    std::uint8_t flags = 0;
    std::uint16_t sequence = 0;
    std::vector<std::uint8_t> payload;
};

std::uint16_t packet_checksum(
    const std::vector<std::uint8_t>& header_without_checksum,
    const std::vector<std::uint8_t>& payload);

std::vector<std::uint8_t> encode_packet(const Packet& packet);

Packet decode_packet(const std::vector<std::uint8_t>& bytes);

std::string message_type_name(MessageType type);
std::string status_name(Status status);

class StreamDecoder {
public:
    std::vector<Packet> feed(const std::uint8_t* data, std::size_t size);
    std::vector<Packet> feed(const std::vector<std::uint8_t>& data) {
        return feed(data.data(), data.size());
    }
    void reset();

private:
    std::vector<std::uint8_t> buffered_;
};

struct Registers {
    std::uint8_t a = 0;
    std::uint8_t x = 0;
    std::uint8_t y = 0;
    std::uint8_t sp = 0xff;
    std::uint8_t status = 0x20;
    std::uint16_t pc = 0x1000;
};

class TargetSimulator {
public:
    TargetSimulator();

    Packet process(const Packet& request);
    void record_sample(std::uint16_t pc);
    const std::vector<std::uint8_t>& memory() const { return memory_; }
    Registers registers() const { return registers_; }

private:
    Packet response(
        const Packet& request,
        Status status,
        std::vector<std::uint8_t> payload = {}) const;

    std::vector<std::uint8_t> memory_;
    Registers registers_;
    std::uint8_t state_ = 0;
    bool sampling_ = false;
    std::vector<std::uint16_t> samples_;
    struct Breakpoint {
        std::uint8_t id = 0;
        std::uint16_t address = 0;
        std::uint8_t original = 0;
    };
    std::vector<Breakpoint> breakpoints_;
    std::uint8_t next_breakpoint_id_ = 1;
};

}  // namespace action_linux::target
