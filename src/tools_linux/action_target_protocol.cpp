#include "action_target_protocol.hpp"

#include "action_help_editor.hpp"

#include <algorithm>
#include <array>

namespace action_linux::target {
namespace {

constexpr std::array<std::uint8_t, 4> kMagic = {'I', 'D', 'B', 'G'};

std::uint16_t read_word(const std::vector<std::uint8_t>& data, std::size_t offset) {
    return static_cast<std::uint16_t>(
        data[offset] | (static_cast<std::uint16_t>(data[offset + 1]) << 8));
}

void append_word(std::vector<std::uint8_t>& output, std::uint16_t value) {
    output.push_back(static_cast<std::uint8_t>(value & 0xff));
    output.push_back(static_cast<std::uint8_t>(value >> 8));
}

}  // namespace

std::uint16_t packet_checksum(
    const std::vector<std::uint8_t>& header_without_checksum,
    const std::vector<std::uint8_t>& payload) {
    std::uint32_t sum = 0;
    for (const std::uint8_t value : header_without_checksum) {
        sum += value;
    }
    for (const std::uint8_t value : payload) {
        sum += value;
    }
    return static_cast<std::uint16_t>(sum & 0xffff);
}

std::vector<std::uint8_t> encode_packet(const Packet& packet) {
    if (packet.payload.size() > kMaximumPayload) {
        throw ToolError("TARGET PACKET TOO LARGE");
    }
    std::vector<std::uint8_t> output;
    output.reserve(kHeaderSize + packet.payload.size());
    output.insert(output.end(), kMagic.begin(), kMagic.end());
    output.push_back(kProtocolMajor);
    output.push_back(kProtocolMinor);
    output.push_back(static_cast<std::uint8_t>(packet.type));
    output.push_back(packet.flags);
    append_word(output, packet.sequence);
    append_word(output, static_cast<std::uint16_t>(packet.payload.size()));
    const std::uint16_t checksum = packet_checksum(output, packet.payload);
    append_word(output, checksum);
    output.insert(output.end(), packet.payload.begin(), packet.payload.end());
    return output;
}

Packet decode_packet(const std::vector<std::uint8_t>& bytes) {
    if (bytes.size() < kHeaderSize ||
        !std::equal(kMagic.begin(), kMagic.end(), bytes.begin())) {
        throw ToolError("BAD TARGET PACKET MAGIC");
    }
    if (bytes[4] != kProtocolMajor) {
        throw ToolError("TARGET PROTOCOL VERSION " + std::to_string(bytes[4]));
    }
    const std::uint16_t payload_size = read_word(bytes, 10);
    if (payload_size > kMaximumPayload || bytes.size() != kHeaderSize + payload_size) {
        throw ToolError("BAD TARGET PACKET LENGTH");
    }
    std::vector<std::uint8_t> header(bytes.begin(), bytes.begin() + 12);
    std::vector<std::uint8_t> payload(bytes.begin() + kHeaderSize, bytes.end());
    if (packet_checksum(header, payload) != read_word(bytes, 12)) {
        throw ToolError("BAD TARGET PACKET CHECKSUM");
    }
    return Packet{
        static_cast<MessageType>(bytes[6]),
        bytes[7],
        read_word(bytes, 8),
        std::move(payload),
    };
}

std::string message_type_name(MessageType type) {
    switch (type) {
        case MessageType::Hello: return "HELLO";
        case MessageType::TargetInfo: return "TARGET_INFO";
        case MessageType::ReadMemory: return "READ_MEMORY";
        case MessageType::WriteMemory: return "WRITE_MEMORY";
        case MessageType::ReadRegisters: return "READ_REGISTERS";
        case MessageType::WriteRegisters: return "WRITE_REGISTERS";
        case MessageType::Halt: return "HALT";
        case MessageType::Run: return "RUN";
        case MessageType::Step: return "STEP";
        case MessageType::BreakSet: return "BREAK_SET";
        case MessageType::BreakClear: return "BREAK_CLEAR";
        case MessageType::BreakList: return "BREAK_LIST";
        case MessageType::SampleConfig: return "SAMPLE_CONFIG";
        case MessageType::SampleRead: return "SAMPLE_READ";
        case MessageType::Ping: return "PING";
        case MessageType::ResetSession: return "RESET_SESSION";
        case MessageType::Stopped: return "STOPPED";
        case MessageType::BreakpointHit: return "BREAKPOINT_HIT";
        case MessageType::TargetExit: return "TARGET_EXIT";
        case MessageType::TargetFault: return "TARGET_FAULT";
    }
    return "UNKNOWN";
}

std::string status_name(Status status) {
    switch (status) {
        case Status::Ok: return "OK";
        case Status::BadPacket: return "BAD_PACKET";
        case Status::Unsupported: return "UNSUPPORTED";
        case Status::BadArgument: return "BAD_ARGUMENT";
        case Status::UnsafeAddress: return "UNSAFE_ADDRESS";
        case Status::BadState: return "BAD_STATE";
        case Status::NoBreakpointSlot: return "NO_BREAKPOINT_SLOT";
        case Status::NotFound: return "NOT_FOUND";
        case Status::InternalError: return "INTERNAL_ERROR";
    }
    return "UNKNOWN_STATUS";
}

std::vector<Packet> StreamDecoder::feed(const std::uint8_t* data, std::size_t size) {
    buffered_.insert(buffered_.end(), data, data + size);
    std::vector<Packet> packets;
    while (buffered_.size() >= kHeaderSize) {
        if (!std::equal(kMagic.begin(), kMagic.end(), buffered_.begin())) {
            const auto next = std::search(
                buffered_.begin() + 1, buffered_.end(), kMagic.begin(), kMagic.end());
            buffered_.erase(buffered_.begin(), next);
            if (buffered_.size() < kHeaderSize) {
                break;
            }
        }
        const std::uint16_t payload_size = read_word(buffered_, 10);
        if (payload_size > kMaximumPayload) {
            buffered_.erase(buffered_.begin());
            continue;
        }
        const std::size_t packet_size = kHeaderSize + payload_size;
        if (buffered_.size() < packet_size) {
            break;
        }
        std::vector<std::uint8_t> encoded(
            buffered_.begin(), buffered_.begin() + static_cast<std::ptrdiff_t>(packet_size));
        packets.push_back(decode_packet(encoded));
        buffered_.erase(
            buffered_.begin(), buffered_.begin() + static_cast<std::ptrdiff_t>(packet_size));
    }
    return packets;
}

void StreamDecoder::reset() {
    buffered_.clear();
}

TargetSimulator::TargetSimulator() : memory_(65536, 0) {}

Packet TargetSimulator::response(
    const Packet& request,
    Status status,
    std::vector<std::uint8_t> payload) const {
    payload.insert(payload.begin(), static_cast<std::uint8_t>(status));
    return Packet{
        request.type,
        static_cast<std::uint8_t>(
            Response | (status == Status::Ok ? 0 : Error)),
        request.sequence,
        std::move(payload),
    };
}

Packet TargetSimulator::process(const Packet& request) {
    const auto word = [&](std::size_t offset) {
        return static_cast<std::uint16_t>(
            request.payload[offset] |
            (static_cast<std::uint16_t>(request.payload[offset + 1]) << 8));
    };
    switch (request.type) {
        case MessageType::Hello:
            if (!request.payload.empty()) return response(request, Status::BadArgument);
            return response(request, Status::Ok, {
                static_cast<std::uint8_t>(kMaximumPayload), 0,
                static_cast<std::uint8_t>(
                    Memory | RegisterAccess | RunHalt | SoftwareBreakpoints |
                    PcSampling | InstructionStep),
                static_cast<std::uint8_t>(
                    (Memory | RegisterAccess | RunHalt | SoftwareBreakpoints |
                     PcSampling | InstructionStep) >> 8),
                0x00, 0xc0, 0xff, 0xcf,
            });
        case MessageType::TargetInfo:
            return response(request, Status::Ok, {
                state_, 0x00, 0x10, 0x00, 0xc0, 0xff, 0xcf,
            });
        case MessageType::ReadMemory: {
            if (request.payload.size() != 3 || request.payload[2] == 0 ||
                request.payload[2] > kMaximumPayload - 1) {
                return response(request, Status::BadArgument);
            }
            const std::uint16_t address = word(0);
            const std::size_t count = request.payload[2];
            if (address > memory_.size() - count) {
                return response(request, Status::UnsafeAddress);
            }
            return response(
                request,
                Status::Ok,
                std::vector<std::uint8_t>(
                    memory_.begin() + address, memory_.begin() + address + count));
        }
        case MessageType::WriteMemory: {
            if (request.payload.size() < 3 ||
                request.payload[2] == 0 ||
                request.payload.size() != static_cast<std::size_t>(3 + request.payload[2])) {
                return response(request, Status::BadArgument);
            }
            const std::uint16_t address = word(0);
            const std::size_t count = request.payload[2];
            if (address > memory_.size() - count ||
                address + count > 0xd000 ||
                (address < 0xd000 && address + count > 0xc000)) {
                return response(request, Status::UnsafeAddress);
            }
            std::copy(
                request.payload.begin() + 3,
                request.payload.end(),
                memory_.begin() + address);
            return response(request, Status::Ok);
        }
        case MessageType::ReadRegisters:
            return response(request, Status::Ok, {
                registers_.a,
                registers_.x,
                registers_.y,
                registers_.sp,
                registers_.status,
                static_cast<std::uint8_t>(registers_.pc & 0xff),
                static_cast<std::uint8_t>(registers_.pc >> 8),
                state_,
            });
        case MessageType::WriteRegisters:
            if (request.payload.size() != 7 || state_ == 1) {
                return response(
                    request,
                    state_ == 1 ? Status::BadState : Status::BadArgument);
            }
            registers_ = Registers{
                request.payload[0], request.payload[1], request.payload[2],
                request.payload[3], request.payload[4], word(5),
            };
            return response(request, Status::Ok);
        case MessageType::Halt:
            state_ = 0;
            return response(request, Status::Ok);
        case MessageType::Run:
            if (state_ == 2) return response(request, Status::BadState);
            state_ = 1;
            return response(request, Status::Ok);
        case MessageType::Step:
            if (!request.payload.empty()) return response(request, Status::BadArgument);
            if (state_ != 0) return response(request, Status::BadState);
            ++registers_.pc;
            return response(request, Status::Ok);
        case MessageType::BreakSet: {
            if (request.payload.size() != 2) {
                return response(request, Status::BadArgument);
            }
            const std::uint16_t address = word(0);
            // The simulator models the default $37 map, where BASIC is
            // visible from $A000 upward; the resident can allow that RAM only
            // after observing BASIC banked out on a real target.
            if (address < 0x0200 || address >= 0xa000) {
                return response(request, Status::UnsafeAddress);
            }
            const auto duplicate = std::find_if(
                breakpoints_.begin(), breakpoints_.end(),
                [&](const Breakpoint& breakpoint) {
                    return breakpoint.address == address;
                });
            if (duplicate != breakpoints_.end()) {
                return response(request, Status::Ok, {duplicate->id});
            }
            if (breakpoints_.size() >= 8) {
                return response(request, Status::NoBreakpointSlot);
            }
            const std::uint8_t id = next_breakpoint_id_++;
            breakpoints_.push_back(Breakpoint{id, address, memory_[address]});
            memory_[address] = 0;
            return response(request, Status::Ok, {id});
        }
        case MessageType::BreakClear: {
            if (request.payload.size() != 1) {
                return response(request, Status::BadArgument);
            }
            const auto found = std::find_if(
                breakpoints_.begin(), breakpoints_.end(),
                [&](const Breakpoint& breakpoint) {
                    return breakpoint.id == request.payload[0];
                });
            if (found == breakpoints_.end()) {
                return response(request, Status::NotFound);
            }
            memory_[found->address] = found->original;
            breakpoints_.erase(found);
            return response(request, Status::Ok);
        }
        case MessageType::BreakList: {
            std::vector<std::uint8_t> payload{static_cast<std::uint8_t>(breakpoints_.size())};
            for (const Breakpoint& breakpoint : breakpoints_) {
                payload.push_back(breakpoint.id);
                payload.push_back(static_cast<std::uint8_t>(breakpoint.address & 0xff));
                payload.push_back(static_cast<std::uint8_t>(breakpoint.address >> 8));
                payload.push_back(breakpoint.original);
            }
            return response(request, Status::Ok, std::move(payload));
        }
        case MessageType::SampleConfig:
            if (request.payload.size() != 1 || request.payload[0] > 1) {
                return response(request, Status::BadArgument);
            }
            sampling_ = request.payload[0] != 0;
            samples_.clear();
            return response(request, Status::Ok);
        case MessageType::SampleRead: {
            const std::size_t count = std::min<std::size_t>(samples_.size(), 100);
            std::vector<std::uint8_t> payload{
                static_cast<std::uint8_t>(count),
                0x1a, 0x41, 0x00, 0x00,  // 16666 microseconds
            };
            for (std::size_t index = 0; index < count; ++index) {
                payload.push_back(static_cast<std::uint8_t>(samples_[index] & 0xff));
                payload.push_back(static_cast<std::uint8_t>(samples_[index] >> 8));
            }
            samples_.erase(samples_.begin(), samples_.begin() + static_cast<std::ptrdiff_t>(count));
            return response(request, Status::Ok, std::move(payload));
        }
        case MessageType::Ping:
            return response(request, Status::Ok, request.payload);
        case MessageType::ResetSession:
            for (const Breakpoint& breakpoint : breakpoints_) {
                memory_[breakpoint.address] = breakpoint.original;
            }
            breakpoints_.clear();
            sampling_ = false;
            samples_.clear();
            state_ = 0;
            return response(request, Status::Ok);
        case MessageType::Stopped:
        case MessageType::BreakpointHit:
        case MessageType::TargetExit:
        case MessageType::TargetFault:
            return response(request, Status::BadArgument);
    }
    return response(request, Status::Unsupported);
}

void TargetSimulator::record_sample(std::uint16_t pc) {
    registers_.pc = pc;
    if (sampling_ && samples_.size() < 100) {
        samples_.push_back(pc);
    }
}

}  // namespace action_linux::target
