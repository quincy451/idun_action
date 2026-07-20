#pragma once

#include "action_target_protocol.hpp"

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace action_linux::target {

struct HelloInfo {
    std::uint16_t maximum_payload = 0;
    std::uint16_t capabilities = 0;
    std::uint16_t service_begin = 0;
    std::uint16_t service_end = 0;
};

bool idun_target_runtime_available();

class IdunTargetSession {
public:
    IdunTargetSession(
        const std::filesystem::path& project_root,
        const std::string& module);
    IdunTargetSession(const IdunTargetSession&) = delete;
    IdunTargetSession& operator=(const IdunTargetSession&) = delete;
    ~IdunTargetSession();

    HelloInfo hello();
    Packet request(
        MessageType type,
        std::vector<std::uint8_t> payload = {},
        int timeout_ms = 5000,
        std::vector<Packet>* observed_events = nullptr);
    std::optional<Packet> receive_event(int timeout_ms);

    void halt();
    void run();
    void step();
    Registers read_registers();
    void write_registers(const Registers& registers);
    std::vector<std::uint8_t> read_memory(std::uint16_t address, std::uint8_t size);
    void write_memory(std::uint16_t address, const std::vector<std::uint8_t>& bytes);
    void set_program_arguments(
        const std::string& program_name,
        const std::vector<std::string>& arguments);
    std::uint8_t set_breakpoint(std::uint16_t address);
    void clear_breakpoint(std::uint8_t id);
    void configure_sampling(bool enabled);
    std::vector<std::uint16_t> read_samples(std::uint32_t* interval_us = nullptr);

    const std::filesystem::path& socket_path() const { return socket_path_; }

private:
    void launch_and_accept(
        const std::filesystem::path& project_root,
        const std::string& module);
    void upload_program(const std::filesystem::path& path);
    void send_packet(const Packet& packet);
    Packet receive_packet(int timeout_ms);
    void cleanup() noexcept;

    int listener_ = -1;
    int connection_ = -1;
    int launcher_pid_ = -1;
    std::uint16_t next_sequence_ = 1;
    std::filesystem::path socket_path_;
    StreamDecoder decoder_;
    std::vector<Packet> pending_packets_;
};

}  // namespace action_linux::target
