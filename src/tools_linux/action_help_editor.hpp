#pragma once

#include <filesystem>
#include <iosfwd>
#include <stdexcept>
#include <string>
#include <vector>

namespace action_linux {

struct ToolError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

void set_program_path(const char* argv0);

std::filesystem::path program_path();

int command_acthelp(const std::vector<std::string>& args);

bool editor_terminal_available();

int run_terminal_editor(
    const std::filesystem::path& source_path,
    const std::string& module,
    const std::filesystem::path& project_root,
    bool syntax_highlighting);

void print_highlighted_source(const std::string& source, std::ostream& output);

}  // namespace action_linux
