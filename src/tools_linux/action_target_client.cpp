#include "action_target_client.hpp"

#include "action_help_editor.hpp"

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <poll.h>
#include <string_view>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

namespace fs = std::filesystem;

namespace action_linux::target {
namespace {

bool executable_exists(std::string_view name) {
    const char* path = std::getenv("PATH");
    if (path == nullptr) return false;
    std::string_view paths(path);
    std::size_t begin = 0;
    while (begin <= paths.size()) {
        const std::size_t end = paths.find(':', begin);
        const fs::path candidate =
            fs::path(std::string(paths.substr(
                begin, end == std::string_view::npos ? paths.size() - begin : end - begin))) /
            std::string(name);
        if (::access(candidate.c_str(), X_OK) == 0) return true;
        if (end == std::string_view::npos) break;
        begin = end + 1;
    }
    return false;
}

fs::path executable_directory() {
    std::error_code error;
    const fs::path executable = fs::read_symlink("/proc/self/exe", error);
    return error ? fs::current_path() : executable.parent_path();
}

fs::path runtime_directory() {
    const char* configured = std::getenv("XDG_RUNTIME_DIR");
    if (configured != nullptr && *configured != '\0') {
        return configured;
    }
    return fs::path("/run/user") / std::to_string(::getuid());
}

bool path_is_within(const fs::path& parent, const fs::path& child) {
    auto parent_part = parent.begin();
    auto child_part = child.begin();
    for (; parent_part != parent.end(); ++parent_part, ++child_part) {
        if (child_part == child.end() || *parent_part != *child_part) return false;
    }
    return true;
}

std::string idun_path_for(const fs::path& path) {
    const char* home_value = std::getenv("HOME");
    if (home_value == nullptr || *home_value == '\0') {
        throw ToolError("IDUN TARGET NEEDS HOME");
    }
    const fs::path home = fs::weakly_canonical(home_value);
    const fs::path absolute = fs::weakly_canonical(path);
    if (!path_is_within(home, absolute)) {
        throw ToolError("IDUN TARGET PATH MUST BE UNDER HOME: " + absolute.string());
    }
    const std::string relative = fs::relative(absolute, home).generic_string();
    if (relative.find(' ') != std::string::npos) {
        throw ToolError("IDUN TARGET PATH CANNOT CONTAIN SPACES");
    }
    return "c:" + relative;
}

fs::path target_service_path() {
    const char* configured = std::getenv("ACTION_TARGET_SERVICE");
    if (configured != nullptr && *configured != '\0') {
        return fs::weakly_canonical(configured);
    }
    return executable_directory() / "actsvc";
}

void require_ok(const Packet& packet) {
    if (packet.payload.empty()) {
        throw ToolError("EMPTY TARGET RESPONSE");
    }
    const Status status = static_cast<Status>(packet.payload.front());
    if (status != Status::Ok) {
        throw ToolError(
            "TARGET " + message_type_name(packet.type) + ": " + status_name(status));
    }
}

std::uint16_t payload_word(const std::vector<std::uint8_t>& payload, std::size_t offset) {
    if (offset + 1 >= payload.size()) {
        throw ToolError("SHORT TARGET RESPONSE");
    }
    return static_cast<std::uint16_t>(
        payload[offset] | (static_cast<std::uint16_t>(payload[offset + 1]) << 8));
}

}  // namespace

bool idun_target_runtime_available() {
    return executable_exists("idunsh") && fs::is_regular_file(target_service_path());
}

IdunTargetSession::IdunTargetSession(
    const fs::path& project_root,
    const std::string& module) {
    launch_and_accept(project_root, module);
}

IdunTargetSession::~IdunTargetSession() {
    if (connection_ >= 0) {
        try {
            // Restore patched instructions and stop a running target before
            // tearing down the socket. Cleanup must still proceed if the C64
            // disappeared, so detach is deliberately best-effort.
            request(MessageType::ResetSession, {}, 1000);
        } catch (...) {
        }
    }
    cleanup();
}

void IdunTargetSession::launch_and_accept(
    const fs::path& project_root,
    const std::string& module) {
    if (!executable_exists("idunsh")) {
        throw ToolError("IDUN TARGET UNAVAILABLE: idunsh not found");
    }
    const fs::path service = target_service_path();
    if (!fs::is_regular_file(service)) {
        throw ToolError("IDUN TARGET SERVICE NOT FOUND: " + service.string());
    }
    const fs::path prg = project_root / "BIN" / (module + ".PRG");
    if (!fs::is_regular_file(prg)) {
        throw ToolError("NO PRG");
    }
    const fs::path runtime = runtime_directory();
    if (!fs::is_directory(runtime)) {
        throw ToolError("IDUN RUNTIME DIRECTORY NOT FOUND: " + runtime.string());
    }

    socket_path_ = runtime / std::to_string(::getpid());
    if (socket_path_.string().size() >= sizeof(sockaddr_un::sun_path)) {
        throw ToolError("IDUN TARGET SOCKET PATH TOO LONG");
    }
    std::error_code error;
    fs::remove(socket_path_, error);
    listener_ = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listener_ < 0) {
        throw ToolError("IDUN TARGET SOCKET: " + std::string(std::strerror(errno)));
    }
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::strncpy(address.sun_path, socket_path_.c_str(), sizeof(address.sun_path) - 1);
    if (::bind(listener_, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0 ||
        ::chmod(socket_path_.c_str(), 0600) != 0 || ::listen(listener_, 1) != 0) {
        const std::string message = std::strerror(errno);
        cleanup();
        throw ToolError("IDUN TARGET LISTEN: " + message);
    }

    const std::string service_argument = idun_path_for(service);
    const std::string prg_argument = idun_path_for(prg);
    const std::string pid_argument = std::to_string(::getpid());
    launcher_pid_ = ::fork();
    if (launcher_pid_ < 0) {
        const std::string message = std::strerror(errno);
        cleanup();
        throw ToolError("IDUN TARGET LAUNCH: " + message);
    }
    if (launcher_pid_ == 0) {
        if (std::getenv("XDG_RUNTIME_DIR") == nullptr) {
            ::setenv("XDG_RUNTIME_DIR", runtime.c_str(), 1);
        }
        ::execlp(
            "idunsh",
            "idunsh",
            "exec",
            service_argument.c_str(),
            pid_argument.c_str(),
            prg_argument.c_str(),
            static_cast<char*>(nullptr));
        _exit(127);
    }

    pollfd descriptor{listener_, POLLIN, 0};
    const auto connect_deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(15);
    bool ready = false;
    while (!ready) {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
            connect_deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0) break;
        descriptor.revents = 0;
        const int status = ::poll(
            &descriptor,
            1,
            static_cast<int>(std::min<std::int64_t>(remaining, 15000)));
        if (status < 0 && errno == EINTR) continue;
        if (status < 0) {
            const std::string message = std::strerror(errno);
            cleanup();
            throw ToolError("IDUN TARGET POLL: " + message);
        }
        if (status == 0) break;
        if ((descriptor.revents & POLLIN) != 0) {
            ready = true;
            break;
        }
        if ((descriptor.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) break;
    }
    if (!ready) {
        int child_status = 0;
        const pid_t child = ::waitpid(launcher_pid_, &child_status, WNOHANG);
        cleanup();
        if (child == launcher_pid_) {
            throw ToolError("IDUN TARGET SERVICE EXITED BEFORE CONNECTING");
        }
        throw ToolError("IDUN TARGET SERVICE CONNECT TIMEOUT");
    }
    do {
        connection_ = ::accept4(listener_, nullptr, nullptr, SOCK_CLOEXEC);
    } while (connection_ < 0 && errno == EINTR);
    if (connection_ < 0) {
        const std::string message = std::strerror(errno);
        cleanup();
        throw ToolError("IDUN TARGET ACCEPT: " + message);
    }
    try {
        upload_program(prg);
        set_program_arguments(module, {});
    } catch (...) {
        cleanup();
        throw;
    }
}

void IdunTargetSession::upload_program(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw ToolError("LOAD FAIL");
    const std::vector<std::uint8_t> prg{
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>(),
    };
    if (prg.size() < 3) throw ToolError("BAD PRG");
    const std::uint16_t load_address = static_cast<std::uint16_t>(
        prg[0] | (static_cast<std::uint16_t>(prg[1]) << 8));
    const std::size_t image_size = prg.size() - 2;
    const std::uint32_t image_end =
        static_cast<std::uint32_t>(load_address) + image_size;
    if (image_end > 0x10000) throw ToolError("TARGET PRG WRAPS MEMORY");
    if (load_address < 0x0200) {
        throw ToolError("TARGET PRG LOAD ADDRESS BELOW $0200");
    }
    if (image_end > 0xd000) {
        throw ToolError("TARGET PRG ENTERS C64 I/O/ROM AREA");
    }

    const HelloInfo target = hello();
    if ((target.capabilities & (Memory | RegisterAccess)) !=
        (Memory | RegisterAccess)) {
        throw ToolError("TARGET CANNOT LOAD PROGRAM");
    }
    const std::uint32_t service_end =
        static_cast<std::uint32_t>(target.service_end) + 1;
    if (load_address < service_end && image_end > target.service_begin) {
        throw ToolError("TARGET PRG OVERLAPS DEBUG SERVICE");
    }

    std::size_t offset = 0;
    while (offset < image_size) {
        const std::size_t count = std::min<std::size_t>(
            kMaximumPayload - 3, image_size - offset);
        write_memory(
            static_cast<std::uint16_t>(load_address + offset),
            std::vector<std::uint8_t>(
                prg.begin() + static_cast<std::ptrdiff_t>(offset + 2),
                prg.begin() + static_cast<std::ptrdiff_t>(offset + 2 + count)));
        offset += count;
    }
    Registers registers = read_registers();
    registers.pc = load_address;
    write_registers(registers);
}

void IdunTargetSession::send_packet(const Packet& packet) {
    const std::vector<std::uint8_t> encoded = encode_packet(packet);
    std::size_t offset = 0;
    while (offset < encoded.size()) {
        const ssize_t written = ::send(
            connection_,
            encoded.data() + offset,
            encoded.size() - offset,
            MSG_NOSIGNAL);
        if (written > 0) {
            offset += static_cast<std::size_t>(written);
        } else if (written < 0 && errno == EINTR) {
            continue;
        } else {
            throw ToolError("IDUN TARGET WRITE: " + std::string(std::strerror(errno)));
        }
    }
}

Packet IdunTargetSession::receive_packet(int timeout_ms) {
    if (!pending_packets_.empty()) {
        Packet packet = std::move(pending_packets_.front());
        pending_packets_.erase(pending_packets_.begin());
        return packet;
    }
    const auto deadline = std::chrono::steady_clock::now() +
        std::chrono::milliseconds(timeout_ms);
    while (true) {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
            deadline - std::chrono::steady_clock::now()).count();
        if (remaining <= 0) {
            throw ToolError("IDUN TARGET RESPONSE TIMEOUT");
        }
        pollfd descriptor{connection_, POLLIN, 0};
        const int status = ::poll(
            &descriptor,
            1,
            static_cast<int>(std::min<std::int64_t>(remaining, 1000)));
        if (status < 0 && errno == EINTR) continue;
        if (status < 0) {
            throw ToolError("IDUN TARGET POLL: " + std::string(std::strerror(errno)));
        }
        if (status == 0) continue;
        if ((descriptor.revents & (POLLERR | POLLNVAL)) != 0) {
            throw ToolError("IDUN TARGET DISCONNECTED");
        }
        if ((descriptor.revents & POLLIN) == 0) {
            if ((descriptor.revents & POLLHUP) != 0) {
                throw ToolError("IDUN TARGET DISCONNECTED");
            }
            continue;
        }
        std::uint8_t buffer[512];
        const ssize_t count = ::read(connection_, buffer, sizeof(buffer));
        if (count == 0) throw ToolError("IDUN TARGET DISCONNECTED");
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) {
            throw ToolError("IDUN TARGET READ: " + std::string(std::strerror(errno)));
        }
        std::vector<Packet> decoded = decoder_.feed(
            buffer, static_cast<std::size_t>(count));
        pending_packets_.insert(
            pending_packets_.end(),
            std::make_move_iterator(decoded.begin()),
            std::make_move_iterator(decoded.end()));
        if (!pending_packets_.empty()) {
            Packet packet = std::move(pending_packets_.front());
            pending_packets_.erase(pending_packets_.begin());
            return packet;
        }
    }
}

Packet IdunTargetSession::request(
    MessageType type,
    std::vector<std::uint8_t> payload,
    int timeout_ms,
    std::vector<Packet>* observed_events) {
    const std::uint16_t sequence = next_sequence_++;
    send_packet(Packet{type, 0, sequence, std::move(payload)});
    std::vector<Packet> events;
    while (true) {
        Packet packet = receive_packet(timeout_ms);
        if ((packet.flags & Event) != 0) {
            events.push_back(std::move(packet));
            continue;
        }
        if ((packet.flags & Response) == 0 || packet.sequence != sequence ||
            packet.type != type) {
            throw ToolError("IDUN TARGET OUT-OF-ORDER RESPONSE");
        }
        if (observed_events != nullptr) {
            observed_events->insert(
                observed_events->end(),
                std::make_move_iterator(events.begin()),
                std::make_move_iterator(events.end()));
        } else {
            pending_packets_.insert(
                pending_packets_.begin(),
                std::make_move_iterator(events.begin()),
                std::make_move_iterator(events.end()));
        }
        require_ok(packet);
        return packet;
    }
}

std::optional<Packet> IdunTargetSession::receive_event(int timeout_ms) {
    try {
        Packet packet = receive_packet(timeout_ms);
        if ((packet.flags & Event) == 0) {
            pending_packets_.insert(pending_packets_.begin(), std::move(packet));
            return std::nullopt;
        }
        return packet;
    } catch (const ToolError& error) {
        if (std::string(error.what()) == "IDUN TARGET RESPONSE TIMEOUT") {
            return std::nullopt;
        }
        throw;
    }
}

HelloInfo IdunTargetSession::hello() {
    const Packet packet = request(MessageType::Hello);
    if (packet.payload.size() < 9) throw ToolError("SHORT TARGET HELLO");
    return HelloInfo{
        payload_word(packet.payload, 1),
        payload_word(packet.payload, 3),
        payload_word(packet.payload, 5),
        payload_word(packet.payload, 7),
    };
}

void IdunTargetSession::halt() {
    request(MessageType::Halt, {}, 10000);
}

void IdunTargetSession::run() {
    request(MessageType::Run);
}

void IdunTargetSession::step() {
    // A previous HALT request may have observed its asynchronous STOPPED event
    // before the response and left it queued. Keep those records distinct from
    // the post-response event that proves this instruction actually finished.
    std::vector<Packet> earlier_events;
    request(MessageType::Step, {}, 5000, &earlier_events);
    const std::optional<Packet> event = receive_event(10000);
    if (!event) {
        throw ToolError("TARGET STEP EVENT TIMEOUT");
    }
    if (event->type == MessageType::TargetFault) {
        throw ToolError("TARGET STEP FAULT");
    }
    if (event->type != MessageType::Stopped &&
        event->type != MessageType::BreakpointHit &&
        event->type != MessageType::TargetExit) {
        throw ToolError("TARGET STEP BAD EVENT");
    }
}

Registers IdunTargetSession::read_registers() {
    const Packet packet = request(MessageType::ReadRegisters);
    if (packet.payload.size() < 9) throw ToolError("SHORT TARGET REGISTERS");
    return Registers{
        packet.payload[1], packet.payload[2], packet.payload[3],
        packet.payload[4], packet.payload[5], payload_word(packet.payload, 6),
    };
}

void IdunTargetSession::write_registers(const Registers& registers) {
    request(MessageType::WriteRegisters, {
        registers.a,
        registers.x,
        registers.y,
        registers.sp,
        registers.status,
        static_cast<std::uint8_t>(registers.pc & 0xff),
        static_cast<std::uint8_t>(registers.pc >> 8),
    });
}

std::vector<std::uint8_t> IdunTargetSession::read_memory(
    std::uint16_t address,
    std::uint8_t size) {
    const Packet packet = request(MessageType::ReadMemory, {
        static_cast<std::uint8_t>(address & 0xff),
        static_cast<std::uint8_t>(address >> 8),
        size,
    });
    return std::vector<std::uint8_t>(packet.payload.begin() + 1, packet.payload.end());
}

void IdunTargetSession::write_memory(
    std::uint16_t address,
    const std::vector<std::uint8_t>& bytes) {
    if (bytes.empty() || bytes.size() > kMaximumPayload - 3) {
        throw ToolError("BAD TARGET WRITE SIZE");
    }
    std::vector<std::uint8_t> payload{
        static_cast<std::uint8_t>(address & 0xff),
        static_cast<std::uint8_t>(address >> 8),
        static_cast<std::uint8_t>(bytes.size()),
    };
    payload.insert(payload.end(), bytes.begin(), bytes.end());
    request(MessageType::WriteMemory, std::move(payload));
}

void IdunTargetSession::set_program_arguments(
    const std::string& program_name,
    const std::vector<std::string>& arguments) {
    constexpr std::uint16_t argument_base = 0x0800;
    constexpr std::uint16_t argument_limit = 0x0F00;
    constexpr std::uint16_t ace_argc = 0x0F04;

    std::vector<std::string> values;
    values.reserve(arguments.size() + 1);
    values.push_back(program_name);
    values.insert(values.end(), arguments.begin(), arguments.end());
    if (values.size() > 0xFFFF) {
        throw ToolError("TOO MANY PROGRAM ARGUMENTS");
    }
    std::size_t string_bytes = 0;
    for (const std::string& value : values) {
        for (unsigned char ch : value) {
            if (ch == 0 || ch > 0x7F) {
                throw ToolError("PROGRAM ARGUMENTS MUST BE ASCII");
            }
        }
        string_bytes += value.size() + 1;
    }
    const std::size_t table_bytes = (values.size() + 1) * 2;
    const std::size_t image_size = table_bytes + string_bytes;
    if (image_size > argument_limit - argument_base) {
        throw ToolError("PROGRAM ARGUMENTS TOO LARGE");
    }

    std::vector<std::uint8_t> image(image_size, 0);
    std::size_t string_offset = table_bytes;
    for (std::size_t index = 0; index < values.size(); ++index) {
        const std::uint16_t address = static_cast<std::uint16_t>(
            argument_base + string_offset);
        image[index * 2] = static_cast<std::uint8_t>(address & 0xFF);
        image[index * 2 + 1] = static_cast<std::uint8_t>(address >> 8);
        std::copy(
            values[index].begin(),
            values[index].end(),
            image.begin() + static_cast<std::ptrdiff_t>(string_offset));
        string_offset += values[index].size() + 1;
    }

    std::size_t offset = 0;
    while (offset < image.size()) {
        const std::size_t count = std::min<std::size_t>(
            kMaximumPayload - 3, image.size() - offset);
        write_memory(
            static_cast<std::uint16_t>(argument_base + offset),
            std::vector<std::uint8_t>(
                image.begin() + static_cast<std::ptrdiff_t>(offset),
                image.begin() + static_cast<std::ptrdiff_t>(offset + count)));
        offset += count;
    }

    const std::uint16_t count = static_cast<std::uint16_t>(values.size());
    write_memory(ace_argc, {
        static_cast<std::uint8_t>(count & 0xFF),
        static_cast<std::uint8_t>(count >> 8),
        static_cast<std::uint8_t>(argument_base & 0xFF),
        static_cast<std::uint8_t>(argument_base >> 8),
    });
}

std::uint8_t IdunTargetSession::set_breakpoint(std::uint16_t address) {
    const Packet packet = request(MessageType::BreakSet, {
        static_cast<std::uint8_t>(address & 0xff),
        static_cast<std::uint8_t>(address >> 8),
    });
    if (packet.payload.size() < 2) throw ToolError("SHORT TARGET BREAKPOINT");
    return packet.payload[1];
}

void IdunTargetSession::clear_breakpoint(std::uint8_t id) {
    request(MessageType::BreakClear, {id});
}

void IdunTargetSession::configure_sampling(bool enabled) {
    request(MessageType::SampleConfig, {static_cast<std::uint8_t>(enabled ? 1 : 0)});
}

std::vector<std::uint16_t> IdunTargetSession::read_samples(std::uint32_t* interval_us) {
    const Packet packet = request(MessageType::SampleRead);
    if (packet.payload.size() < 6) throw ToolError("SHORT TARGET SAMPLES");
    const std::size_t count = packet.payload[1];
    if (packet.payload.size() != 6 + count * 2) {
        throw ToolError("BAD TARGET SAMPLE COUNT");
    }
    if (interval_us != nullptr) {
        *interval_us = static_cast<std::uint32_t>(packet.payload[2]) |
            (static_cast<std::uint32_t>(packet.payload[3]) << 8) |
            (static_cast<std::uint32_t>(packet.payload[4]) << 16) |
            (static_cast<std::uint32_t>(packet.payload[5]) << 24);
    }
    std::vector<std::uint16_t> samples;
    samples.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        samples.push_back(payload_word(packet.payload, 6 + index * 2));
    }
    return samples;
}

void IdunTargetSession::cleanup() noexcept {
    if (connection_ >= 0) {
        ::close(connection_);
        connection_ = -1;
    }
    if (listener_ >= 0) {
        ::close(listener_);
        listener_ = -1;
    }
    if (!socket_path_.empty()) {
        std::error_code error;
        fs::remove(socket_path_, error);
    }
    if (launcher_pid_ > 0) {
        int status = 0;
        if (::waitpid(launcher_pid_, &status, WNOHANG) == 0) {
            ::kill(launcher_pid_, SIGTERM);
            for (int attempt = 0; attempt < 20; ++attempt) {
                if (::waitpid(launcher_pid_, &status, WNOHANG) == launcher_pid_) break;
                ::usleep(10000);
            }
            if (::waitpid(launcher_pid_, &status, WNOHANG) == 0) {
                ::kill(launcher_pid_, SIGKILL);
                ::waitpid(launcher_pid_, &status, 0);
            }
        }
        launcher_pid_ = -1;
    }
}

}  // namespace action_linux::target
