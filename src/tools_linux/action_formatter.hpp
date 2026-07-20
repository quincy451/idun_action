#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace action_linux {

std::string format_action_source(std::string_view source);

int command_actspc(const std::vector<std::string>& args);

}  // namespace action_linux
