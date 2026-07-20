#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace action_linux {

struct CodeMapLine {
    std::uint16_t address = 0;
    std::size_t line = 0;
};

struct CodeMapSymbol {
    std::string name;
    std::uint16_t address = 0;
    std::uint16_t size = 0;
};

struct CodeMapModule {
    std::string module;
    std::string source_path;
    std::uint16_t base_address = 0;
    std::uint32_t size = 0;
    std::vector<CodeMapLine> lines;
    std::vector<CodeMapSymbol> symbols;
};

struct CodeMapLocation {
    std::string name;
    std::string kind;
    std::string caller;
    std::string module;
    std::string path;
    std::string signature;
    std::size_t line = 0;
    std::size_t column = 0;
    std::optional<std::uint16_t> address;
    std::uint16_t size = 0;
};

struct CodeMapSummary {
    std::string entry_module;
    std::string fingerprint;
    std::size_t modules = 0;
    std::size_t definitions = 0;
    std::size_t references = 0;
};

std::filesystem::path code_map_path(const std::filesystem::path& project_root);

void build_code_map(
    const std::filesystem::path& project_root,
    const std::string& entry_module,
    const std::vector<std::uint8_t>& prg,
    const std::vector<CodeMapModule>& modules);

std::optional<CodeMapLocation> code_map_definition(
    const std::filesystem::path& project_root,
    const std::string& symbol);

std::vector<CodeMapLocation> code_map_references(
    const std::filesystem::path& project_root,
    const std::string& symbol);

std::optional<CodeMapLocation> code_map_address(
    const std::filesystem::path& project_root,
    std::uint16_t address);

CodeMapSummary code_map_summary(const std::filesystem::path& project_root);

}  // namespace action_linux
