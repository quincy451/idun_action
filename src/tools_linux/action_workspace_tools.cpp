#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <cstdlib>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <unistd.h>

#include <sqlite3.h>

#include "action_code_map.hpp"
#include "action_formatter.hpp"
#include "action_graphics_editor.hpp"
#include "action_help_editor.hpp"
#include "action_profiler.hpp"
#include "action_target_client.hpp"
#include "action_target_protocol.hpp"

namespace fs = std::filesystem;

namespace {

const std::string kProjectHeader = "ACTION PROJECT";
fs::path g_invocation_cwd;

using action_linux::ToolError;

class SqliteDatabase {
public:
    explicit SqliteDatabase(const fs::path& path) {
        fs::create_directories(path.parent_path());
        const int status = sqlite3_open(path.c_str(), &database_);
        if (status != SQLITE_OK) {
            const std::string message =
                database_ == nullptr ? "open failed" : sqlite3_errmsg(database_);
            if (database_ != nullptr) {
                sqlite3_close(database_);
                database_ = nullptr;
            }
            throw ToolError("SQLITE OPEN: " + message);
        }
        exec("PRAGMA foreign_keys=ON");
    }

    SqliteDatabase(const SqliteDatabase&) = delete;
    SqliteDatabase& operator=(const SqliteDatabase&) = delete;

    ~SqliteDatabase() {
        if (database_ != nullptr) {
            sqlite3_close(database_);
        }
    }

    sqlite3* get() const {
        return database_;
    }

    void exec(const std::string& sql) {
        char* error = nullptr;
        const int status = sqlite3_exec(database_, sql.c_str(), nullptr, nullptr, &error);
        if (status != SQLITE_OK) {
            const std::string message =
                error == nullptr ? sqlite3_errmsg(database_) : error;
            sqlite3_free(error);
            throw ToolError("SQLITE EXEC: " + message);
        }
    }

private:
    sqlite3* database_ = nullptr;
};

class SqliteStatement {
public:
    SqliteStatement(SqliteDatabase& database, const std::string& sql)
        : database_(database.get()) {
        if (sqlite3_prepare_v2(database_, sql.c_str(), -1, &statement_, nullptr) !=
            SQLITE_OK) {
            throw ToolError("SQLITE PREPARE: " + std::string(sqlite3_errmsg(database_)));
        }
    }

    SqliteStatement(const SqliteStatement&) = delete;
    SqliteStatement& operator=(const SqliteStatement&) = delete;

    ~SqliteStatement() {
        if (statement_ != nullptr) {
            sqlite3_finalize(statement_);
        }
    }

    void bind_text(int index, std::string_view value) {
        if (sqlite3_bind_text64(
                statement_,
                index,
                value.data(),
                static_cast<sqlite3_uint64>(value.size()),
                SQLITE_TRANSIENT,
                SQLITE_UTF8) != SQLITE_OK) {
            throw ToolError("SQLITE BIND: " + std::string(sqlite3_errmsg(database_)));
        }
    }

    void bind_integer(int index, std::int64_t value) {
        if (sqlite3_bind_int64(statement_, index, value) != SQLITE_OK) {
            throw ToolError("SQLITE BIND: " + std::string(sqlite3_errmsg(database_)));
        }
    }

    bool step() {
        const int status = sqlite3_step(statement_);
        if (status == SQLITE_ROW) {
            return true;
        }
        if (status == SQLITE_DONE) {
            return false;
        }
        throw ToolError("SQLITE STEP: " + std::string(sqlite3_errmsg(database_)));
    }

    void reset() {
        if (sqlite3_reset(statement_) != SQLITE_OK ||
            sqlite3_clear_bindings(statement_) != SQLITE_OK) {
            throw ToolError("SQLITE RESET: " + std::string(sqlite3_errmsg(database_)));
        }
    }

    std::int64_t integer(int column) const {
        return sqlite3_column_int64(statement_, column);
    }

    std::string text(int column) const {
        const unsigned char* value = sqlite3_column_text(statement_, column);
        return value == nullptr
            ? std::string{}
            : std::string(reinterpret_cast<const char*>(value));
    }

private:
    sqlite3* database_ = nullptr;
    sqlite3_stmt* statement_ = nullptr;
};

std::string upper_ascii(std::string_view input) {
    std::string out;
    out.reserve(input.size());
    for (unsigned char ch : input) {
        out.push_back(static_cast<char>(std::toupper(ch)));
    }
    return out;
}

std::string trim(std::string_view input) {
    std::size_t first = 0;
    while (first < input.size() && std::isspace(static_cast<unsigned char>(input[first]))) {
        ++first;
    }
    std::size_t last = input.size();
    while (last > first && std::isspace(static_cast<unsigned char>(input[last - 1]))) {
        --last;
    }
    return std::string(input.substr(first, last - first));
}

std::vector<std::string> split_lines(const std::string& text) {
    std::vector<std::string> lines;
    std::string current;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char ch = text[i];
        if (ch == '\r' || ch == '\n') {
            lines.push_back(current);
            current.clear();
            if (ch == '\r' && i + 1 < text.size() && text[i + 1] == '\n') {
                ++i;
            }
            continue;
        }
        current.push_back(ch);
    }
    if (!current.empty() || text.empty()) {
        lines.push_back(current);
    }
    return lines;
}

std::string strip_source_comment(std::string_view line) {
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char ch = line[i];
        if (in_string && ch == '\\' && !escaped) {
            escaped = true;
            continue;
        }
        if (ch == '"' && !escaped) {
            in_string = !in_string;
        } else if (ch == ';' && !in_string) {
            return std::string(line.substr(0, i));
        }
        escaped = false;
    }
    return std::string(line);
}

std::string join_lines(const std::vector<std::string>& lines) {
    std::string text;
    for (const std::string& line : lines) {
        text += line;
        text += "\n";
    }
    return text;
}

std::string read_text_file(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw ToolError("LOAD FAIL");
    }
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}

void write_text_file(const fs::path& path, std::string_view text) {
    if (!path.parent_path().empty()) {
        fs::create_directories(path.parent_path());
    }
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        throw ToolError("SAVE FAIL");
    }
    out.write(text.data(), static_cast<std::streamsize>(text.size()));
    if (!out) {
        throw ToolError("SAVE FAIL");
    }
}

void write_binary_file(const fs::path& path, const std::vector<std::uint8_t>& bytes) {
    if (!path.parent_path().empty()) {
        fs::create_directories(path.parent_path());
    }
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) {
        throw ToolError("SAVE FAIL");
    }
    out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    if (!out) {
        throw ToolError("SAVE FAIL");
    }
}

std::optional<fs::path> child_case_insensitive(const fs::path& directory, std::string_view wanted) {
    if (!fs::is_directory(directory)) {
        return std::nullopt;
    }
    const std::string wanted_upper = upper_ascii(wanted);
    for (const auto& entry : fs::directory_iterator(directory)) {
        if (upper_ascii(entry.path().filename().string()) == wanted_upper) {
            return entry.path();
        }
    }
    return std::nullopt;
}

fs::path required_child_ci(const fs::path& directory, std::string_view wanted, std::string_view error) {
    auto found = child_case_insensitive(directory, wanted);
    if (!found) {
        throw ToolError(std::string(error));
    }
    return *found;
}

fs::path project_manifest_path(const fs::path& root) {
    return required_child_ci(root, "ACTION.PROJ", "NO PROJECT");
}

std::string module_from_arg(std::string_view arg) {
    std::string value = trim(arg);
    if (value.empty()) {
        throw ToolError("NO NAME");
    }
    for (char& ch : value) {
        if (ch == '\\') {
            ch = '/';
        }
    }
    fs::path p(value);
    std::string name = p.filename().string();
    const std::string suffix = ".ACT";
    if (name.size() >= suffix.size() &&
        upper_ascii(std::string_view(name).substr(name.size() - suffix.size())) == suffix) {
        name.resize(name.size() - suffix.size());
    }
    name = upper_ascii(name);
    if (name.empty()) {
        throw ToolError("BAD NAME");
    }
    const bool ok = std::all_of(name.begin(), name.end(), [](unsigned char ch) {
        return std::isalnum(ch) || ch == '_';
    });
    if (!ok) {
        throw ToolError("BAD NAME");
    }
    return name;
}

std::vector<std::string> load_manifest_entries(const fs::path& root) {
    const std::string text = read_text_file(project_manifest_path(root));
    std::vector<std::string> raw = split_lines(text);
    std::vector<std::string> entries;
    bool saw_header = false;
    for (const std::string& line : raw) {
        std::string cleaned = trim(line);
        if (cleaned.empty()) {
            continue;
        }
        if (!saw_header) {
            if (upper_ascii(cleaned) != kProjectHeader) {
                throw ToolError("NO PROJECT");
            }
            saw_header = true;
            continue;
        }
        entries.push_back(upper_ascii(cleaned));
    }
    if (!saw_header) {
        throw ToolError("NO PROJECT");
    }
    return entries;
}

void save_manifest_entries(const fs::path& root, const std::vector<std::string>& entries) {
    std::string text = kProjectHeader + "\n";
    for (const std::string& entry : entries) {
        text += upper_ascii(entry) + "\n";
    }
    write_text_file(root / "ACTION.PROJ", text);
}

bool manifest_contains_module(const std::vector<std::string>& entries, const std::string& module) {
    const std::string wanted = upper_ascii(module) + ".ACT";
    return std::any_of(entries.begin(), entries.end(), [&](const std::string& entry) {
        return upper_ascii(entry) == wanted;
    });
}

fs::path project_dir(const fs::path& root, std::string_view name) {
    auto found = child_case_insensitive(root, name);
    if (found && fs::is_directory(*found)) {
        return *found;
    }
    return root / std::string(name);
}

std::optional<fs::path> flat_module_file(
    const fs::path& root,
    const std::string& module,
    std::string_view extension) {
    const auto found = child_case_insensitive(root, module + std::string(extension));
    if (found && fs::is_regular_file(*found)) {
        return found;
    }
    return std::nullopt;
}

bool uses_flat_module_layout(const fs::path& root, const std::string& module) {
    return flat_module_file(root, module, ".ACT").has_value() ||
        flat_module_file(root, module, ".OBJ").has_value();
}

fs::path source_path(const fs::path& root, const std::string& module) {
    if (const auto direct = flat_module_file(root, module, ".ACT")) {
        return *direct;
    }
    const fs::path src = project_dir(root, "SRC");
    auto found = child_case_insensitive(src, module + ".ACT");
    return found.value_or(src / (module + ".ACT"));
}

fs::path object_path(const fs::path& root, const std::string& module) {
    if (uses_flat_module_layout(root, module)) {
        const auto direct = flat_module_file(root, module, ".OBJ");
        return direct.value_or(root / (module + ".OBJ"));
    }
    const fs::path obj = project_dir(root, "OBJ");
    auto found = child_case_insensitive(obj, module + ".OBJ");
    return found.value_or(obj / (module + ".OBJ"));
}

fs::path binary_path(const fs::path& root, const std::string& module) {
    if (uses_flat_module_layout(root, module)) {
        return root / (module + ".PRG");
    }
    return project_dir(root, "BIN") / (module + ".PRG");
}

fs::path debug_path(const fs::path& root, const std::string& module) {
    if (uses_flat_module_layout(root, module)) {
        return root / (module + ".DBG");
    }
    return project_dir(root, "BIN") / (module + ".DBG");
}

void require_project_module(const fs::path& root, const std::string& module) {
    if (uses_flat_module_layout(root, module)) {
        return;
    }
    const auto entries = load_manifest_entries(root);
    if (!manifest_contains_module(entries, module)) {
        throw ToolError("NOT IN PROJECT");
    }
}

std::vector<std::string> read_source_lines(const fs::path& path) {
    if (!fs::is_regular_file(path)) {
        throw ToolError("NO FILE");
    }
    std::string text = read_text_file(path);
    std::vector<std::string> lines = split_lines(text);
    if (!lines.empty() && lines.back().empty()) {
        lines.pop_back();
    }
    return lines;
}

std::size_t parse_one_based_line(const std::string& text, std::size_t max_inclusive) {
    std::size_t pos = 0;
    const unsigned long value = std::stoul(text, &pos, 10);
    if (pos != text.size() || value == 0 || value > max_inclusive) {
        throw ToolError("BAD LINE");
    }
    return static_cast<std::size_t>(value - 1);
}

std::string bytes_to_hex(const std::vector<std::uint8_t>& bytes) {
    std::ostringstream out;
    out << std::uppercase << std::hex << std::setfill('0');
    for (std::uint8_t byte : bytes) {
        out << std::setw(2) << static_cast<int>(byte);
    }
    return out.str();
}

std::vector<std::uint8_t> hex_to_bytes(std::string_view hex) {
    std::vector<std::uint8_t> bytes;
    std::string compact;
    compact.reserve(hex.size());
    for (char ch : hex) {
        if (!std::isspace(static_cast<unsigned char>(ch))) {
            compact.push_back(ch);
        }
    }
    if (compact.size() % 2 != 0) {
        throw ToolError("BAD OBJECT");
    }
    bytes.reserve(compact.size() / 2);
    for (std::size_t i = 0; i < compact.size(); i += 2) {
        const std::string pair = compact.substr(i, 2);
        bytes.push_back(static_cast<std::uint8_t>(std::stoul(pair, nullptr, 16)));
    }
    return bytes;
}

std::vector<std::string> split_words(std::string_view line) {
    std::istringstream in{std::string(line)};
    std::vector<std::string> words;
    std::string word;
    while (in >> word) {
        words.push_back(word);
    }
    return words;
}

struct SourceParameter {
    std::string name;
    std::string type;
    bool is_array = false;
    bool is_pointer = false;
};

std::optional<std::size_t> routine_parameter_open_from_line(std::string_view line) {
    std::optional<std::size_t> parameter_open;
    int depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char ch = line[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                in_string = false;
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '(') {
            if (depth == 0) {
                parameter_open = i;
            }
            ++depth;
        } else if (ch == ')') {
            if (depth == 0) {
                return std::nullopt;
            }
            --depth;
        }
    }
    if (depth != 0 || in_string) {
        return std::nullopt;
    }
    return parameter_open;
}

std::optional<std::string> proc_name_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("PROC ", 0) != 0) {
        return std::nullopt;
    }
    std::string rest = trim(cleaned.substr(5));
    if (auto open = routine_parameter_open_from_line(rest)) {
        rest.resize(*open);
    }
    const std::size_t equals = rest.find('=');
    if (equals != std::string::npos) {
        rest.resize(equals);
    }
    rest = trim(rest);
    if (rest.empty()) {
        throw ToolError("BAD PROC");
    }
    return module_from_arg(rest);
}

std::string routine_address_from_line(const std::string& line) {
    const auto open = routine_parameter_open_from_line(line);
    if (!open) {
        return {};
    }
    const std::size_t equals = line.rfind('=', *open);
    if (equals == std::string::npos) {
        return {};
    }
    const std::string address = trim(
        std::string_view(line).substr(equals + 1, *open - equals - 1));
    if (address.empty()) {
        throw ToolError("BAD ROUTINE ADDRESS");
    }
    return address;
}

std::optional<std::string> call_name_from_line(const std::string& line) {
    std::string cleaned = trim(line);
    if (cleaned.empty()) {
        return std::nullopt;
    }
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("RETURN", 0) == 0 || upper == "ENDPROC" ||
        upper == "ENDFUNC" || upper.rfind("PROC ", 0) == 0 ||
        upper.rfind("MODULE ", 0) == 0) {
        return std::nullopt;
    }
    const std::size_t paren = cleaned.find('(');
    if (paren == std::string::npos) {
        return std::nullopt;
    }
    std::string name = trim(cleaned.substr(0, paren));
    if (name.empty()) {
        return std::nullopt;
    }
    if (name.find('=') != std::string::npos || name.find(' ') != std::string::npos) {
        return std::nullopt;
    }
    return module_from_arg(name);
}

std::vector<std::string> split_call_arguments(std::string_view text) {
    std::vector<std::string> arguments;
    std::size_t start = 0;
    int depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char ch = text[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                if (i + 1 < text.size() && text[i + 1] == '"') {
                    ++i;
                } else {
                    in_string = false;
                }
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '(') {
            ++depth;
        } else if (ch == ')') {
            --depth;
            if (depth < 0) {
                throw ToolError("BAD CALL");
            }
        } else if (depth == 0 && ch == ',') {
            std::string argument = trim(text.substr(start, i - start));
            if (argument.empty()) {
                throw ToolError("BAD CALL");
            }
            arguments.push_back(std::move(argument));
            start = i + 1;
        }
    }
    if (depth != 0 || in_string || escaped) {
        throw ToolError("BAD CALL");
    }
    std::string final_argument = trim(text.substr(start));
    if (!final_argument.empty()) {
        arguments.push_back(std::move(final_argument));
    } else if (!arguments.empty()) {
        throw ToolError("BAD CALL");
    }
    return arguments;
}

std::size_t find_call_close(std::string_view text, std::size_t open) {
    if (open >= text.size() || text[open] != '(') {
        throw ToolError("BAD CALL");
    }
    int depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = open + 1; i < text.size(); ++i) {
        const char ch = text[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                if (i + 1 < text.size() && text[i + 1] == '"') {
                    ++i;
                } else {
                    in_string = false;
                }
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '(') {
            ++depth;
        } else if (ch == ')') {
            if (depth == 0) {
                return i;
            }
            --depth;
        }
    }
    throw ToolError("BAD CALL");
}

std::vector<SourceParameter> proc_parameters_from_line(
    const std::string& line,
    const std::set<std::string>& record_type_names) {
    const std::string cleaned = trim(line);
    const auto open = routine_parameter_open_from_line(cleaned);
    const std::size_t close = cleaned.rfind(')');
    if (!open || close == std::string::npos || close < *open ||
        !trim(std::string_view(cleaned).substr(close + 1)).empty()) {
        throw ToolError("BAD PROC");
    }
    const std::string body = trim(
        std::string_view(cleaned).substr(*open + 1, close - *open - 1));
    if (body.empty()) {
        return {};
    }

    std::vector<SourceParameter> parameters;
    std::string current_type;
    bool current_array = false;
    bool current_pointer = false;
    for (std::string item : split_call_arguments(body)) {
        item = trim(item);
        const std::string upper = upper_ascii(item);
        bool supplied_type = false;
        for (const std::string type : {"BYTE", "CHAR", "CARD", "INT", "REAL"}) {
            const std::string array_prefix = type + " ARRAY ";
            const std::string pointer_prefix = type + " POINTER ";
            const std::string scalar_prefix = type + " ";
            if (upper.rfind(array_prefix, 0) == 0) {
                current_type = type == "CHAR" ? "BYTE" : type;
                current_array = true;
                current_pointer = false;
                item = trim(std::string_view(item).substr(array_prefix.size()));
                supplied_type = true;
                break;
            }
            if (upper.rfind(pointer_prefix, 0) == 0) {
                current_type = type == "CHAR" ? "BYTE" : type;
                current_array = false;
                current_pointer = true;
                item = trim(std::string_view(item).substr(pointer_prefix.size()));
                supplied_type = true;
                break;
            }
            if (upper.rfind(scalar_prefix, 0) == 0) {
                current_type = type == "CHAR" ? "BYTE" : type;
                current_array = false;
                current_pointer = false;
                item = trim(std::string_view(item).substr(scalar_prefix.size()));
                supplied_type = true;
                break;
            }
        }
        if (!supplied_type) {
            for (const std::string& record_type : record_type_names) {
                const std::string pointer_prefix = record_type + " POINTER ";
                const std::string scalar_prefix = record_type + " ";
                if (upper.rfind(pointer_prefix, 0) == 0) {
                    current_type = record_type;
                    current_array = false;
                    current_pointer = true;
                    item = trim(std::string_view(item).substr(pointer_prefix.size()));
                    supplied_type = true;
                    break;
                }
                if (upper.rfind(scalar_prefix, 0) == 0) {
                    // Action passes a record name as the address of its first
                    // field; a formal record value is therefore pointer-sized.
                    current_type = record_type;
                    current_array = false;
                    current_pointer = true;
                    item = trim(std::string_view(item).substr(scalar_prefix.size()));
                    supplied_type = true;
                    break;
                }
            }
        }
        if (!supplied_type && current_type.empty()) {
            throw ToolError("BAD PROC PARAM");
        }
        if (item.empty() || item.find_first_not_of(
                                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                                std::string::npos ||
            std::isdigit(static_cast<unsigned char>(item.front()))) {
            throw ToolError("BAD PROC PARAM");
        }
        parameters.push_back(SourceParameter{
            module_from_arg(item),
            current_type,
            current_array,
            current_pointer,
        });
    }
    return parameters;
}

struct ParsedFunctionDeclaration {
    std::string name;
    std::string return_type;
    std::vector<SourceParameter> parameters;
    std::string address_expression;
};

std::optional<ParsedFunctionDeclaration> function_from_line(
    const std::string& line,
    const std::set<std::string>& record_type_names) {
    static const std::regex declaration_prefix(
        R"(^\s*(BYTE|CHAR|CARD|INT|REAL)\s+FUNC\s+([A-Za-z_][A-Za-z0-9_]*))",
        std::regex_constants::icase);
    std::smatch match;
    if (!std::regex_search(line, match, declaration_prefix) || match.position() != 0) {
        return std::nullopt;
    }
    const auto open = routine_parameter_open_from_line(line);
    if (!open || *open < static_cast<std::size_t>(match.length())) {
        throw ToolError("BAD FUNC");
    }
    const std::string binding = trim(std::string_view(line).substr(
        static_cast<std::size_t>(match.length()),
        *open - static_cast<std::size_t>(match.length())));
    if (!binding.empty() && (binding.front() != '=' || trim(binding.substr(1)).empty())) {
        throw ToolError("BAD FUNC");
    }
    return ParsedFunctionDeclaration{
        module_from_arg(match[2].str()),
        upper_ascii(match[1].str()) == "CHAR" ? "BYTE" : upper_ascii(match[1].str()),
        proc_parameters_from_line(line, record_type_names),
        binding.empty() ? std::string{} : trim(binding.substr(1)),
    };
}

struct ParsedCall {
    std::string name;
    std::vector<std::string> arguments;
};

std::optional<ParsedCall> parse_call_expression(std::string_view text) {
    const std::string cleaned = trim(text);
    const std::size_t open = cleaned.find('(');
    const std::size_t close = cleaned.rfind(')');
    if (open == std::string::npos || close == std::string::npos || close != cleaned.size() - 1 ||
        close < open) {
        return std::nullopt;
    }
    int depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = open; i <= close; ++i) {
        const char ch = cleaned[i];
        if (in_string && ch == '\\' && !escaped) {
            escaped = true;
            continue;
        }
        if (ch == '"' && !escaped) {
            in_string = !in_string;
        } else if (!in_string && ch == '(') {
            ++depth;
        } else if (!in_string && ch == ')') {
            --depth;
            if (depth < 0 || (depth == 0 && i != close)) {
                return std::nullopt;
            }
        }
        escaped = false;
    }
    if (depth != 0 || in_string) {
        return std::nullopt;
    }
    const std::string name = trim(std::string_view(cleaned).substr(0, open));
    if (name.empty() || name.find_first_not_of(
                            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                            std::string::npos) {
        return std::nullopt;
    }
    return ParsedCall{
        module_from_arg(name),
        split_call_arguments(std::string_view(cleaned).substr(open + 1, close - open - 1)),
    };
}

std::optional<std::string> print_string_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("PRINTE", 0) != 0) {
        return std::nullopt;
    }
    const std::size_t open = cleaned.find('"');
    const std::size_t close = cleaned.rfind('"');
    if (open == std::string::npos || close == std::string::npos) {
        return std::nullopt;
    }
    if (close <= open) {
        throw ToolError("BAD PRINT");
    }
    std::string out;
    for (std::size_t i = open + 1; i < close; ++i) {
        if (cleaned[i] == '"' && i + 1 < close && cleaned[i + 1] == '"') {
            out.push_back('"');
            ++i;
            continue;
        }
        if (cleaned[i] == '\\' && i + 1 < close) {
            ++i;
            if (cleaned[i] == 'n') {
                out.push_back('\n');
            } else if (cleaned[i] == 'r') {
                out.push_back('\r');
            } else {
                out.push_back(cleaned[i]);
            }
        } else {
            out.push_back(cleaned[i]);
        }
    }
    return out;
}

std::optional<std::string> print_string_expr_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("PRINTE", 0) != 0) {
        return std::nullopt;
    }
    const std::size_t open = cleaned.find('(');
    const std::size_t close = cleaned.rfind(')');
    if (open == std::string::npos || close != cleaned.size() - 1 || close <= open) {
        throw ToolError("BAD PRINT");
    }
    const std::string expression = trim(
        std::string_view(cleaned).substr(open + 1, close - open - 1));
    if (expression.empty()) {
        throw ToolError("BAD PRINT");
    }
    return expression;
}

std::optional<std::string> print_int_expr_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("PRINTIE", 0) != 0) {
        return std::nullopt;
    }
    const std::size_t open = cleaned.find('(');
    const std::size_t close = cleaned.rfind(')');
    if (open == std::string::npos || close == std::string::npos || close <= open) {
        throw ToolError("BAD PRINT");
    }
    return trim(std::string_view(cleaned).substr(open + 1, close - open - 1));
}

std::optional<std::string> print_int_call_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("PRINTI", 0) != 0 || upper.rfind("PRINTIE", 0) == 0) {
        return std::nullopt;
    }
    const std::size_t open = cleaned.find('(');
    const std::size_t close = cleaned.rfind(')');
    if (open == std::string::npos || close == std::string::npos || close <= open) {
        throw ToolError("BAD PRINT");
    }
    return trim(std::string_view(cleaned).substr(open + 1, close - open - 1));
}

std::optional<std::pair<std::string, bool>> print_real_expr_from_line(
    const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    bool newline = false;
    if (upper.rfind("PRINTRE", 0) == 0) {
        newline = true;
    } else if (upper.rfind("PRINTR", 0) != 0) {
        return std::nullopt;
    }
    const std::size_t open = cleaned.find('(');
    const std::size_t close = cleaned.rfind(')');
    if (open == std::string::npos || close != cleaned.size() - 1 || close <= open) {
        throw ToolError("BAD REAL PRINT");
    }
    const std::string expression = trim(
        std::string_view(cleaned).substr(open + 1, close - open - 1));
    if (expression.empty()) {
        throw ToolError("BAD REAL PRINT");
    }
    return std::make_pair(expression, newline);
}

struct ParsedDeclaration {
    std::string name;
    std::string type;
    std::string mode;
    std::string expression;
};

struct ParsedArrayDeclaration {
    std::string name;
    std::string type;
    std::string size_expression;
    std::string mode;
    std::string expression;
};

struct ParsedReuDeclaration {
    std::string name;
    std::string size_expression;
};

std::optional<ParsedReuDeclaration> reu_declaration_from_line(const std::string& line) {
    static const std::regex declaration(
        R"(^\s*REU\s+BYTE\s+ARRAY\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.+)\)\s*$)",
        std::regex_constants::icase);
    std::smatch match;
    if (!std::regex_match(line, match, declaration)) {
        return std::nullopt;
    }
    const std::string size_expression = trim(match[2].str());
    if (size_expression.empty()) {
        throw ToolError("BAD REU DECL");
    }
    return ParsedReuDeclaration{
        module_from_arg(match[1].str()),
        size_expression,
    };
}

std::vector<std::string> split_declarators(std::string_view text) {
    std::vector<std::string> items;
    std::size_t start = 0;
    int paren_depth = 0;
    int bracket_depth = 0;
    bool in_string = false;
    bool escaped = false;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char ch = text[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                if (i + 1 < text.size() && text[i + 1] == '"') {
                    ++i;
                } else {
                    in_string = false;
                }
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '(') {
            ++paren_depth;
        } else if (ch == ')') {
            --paren_depth;
        } else if (ch == '[') {
            ++bracket_depth;
        } else if (ch == ']') {
            --bracket_depth;
        } else if (ch == ',' && paren_depth == 0 && bracket_depth == 0) {
            const std::string item = trim(text.substr(start, i - start));
            if (item.empty()) {
                throw ToolError("BAD DECL");
            }
            items.push_back(item);
            start = i + 1;
        }
        if (paren_depth < 0 || bracket_depth < 0) {
            throw ToolError("BAD DECL");
        }
    }
    if (in_string || paren_depth != 0 || bracket_depth != 0) {
        throw ToolError("BAD DECL");
    }
    const std::string final_item = trim(text.substr(start));
    if (final_item.empty()) {
        throw ToolError("BAD DECL");
    }
    items.push_back(final_item);
    return items;
}

std::vector<std::string> split_array_initializer_values(std::string_view text) {
    bool has_top_level_comma = false;
    bool in_string = false;
    bool escaped = false;
    int paren_depth = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        const char ch = text[i];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                if (i + 1 < text.size() && text[i + 1] == '"') {
                    ++i;
                } else {
                    in_string = false;
                }
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == '(') {
            ++paren_depth;
        } else if (ch == ')') {
            --paren_depth;
        } else if (ch == ',' && paren_depth == 0) {
            has_top_level_comma = true;
        }
    }
    if (in_string || paren_depth != 0) {
        throw ToolError("BAD ARRAY INITIALIZER");
    }
    if (has_top_level_comma) {
        return split_declarators(text);
    }

    std::vector<std::string> values;
    std::size_t pos = 0;
    while (pos < text.size()) {
        while (pos < text.size() &&
               std::isspace(static_cast<unsigned char>(text[pos]))) {
            ++pos;
        }
        if (pos >= text.size()) {
            break;
        }
        const std::size_t start = pos;
        if (text[pos] == '"') {
            ++pos;
            bool string_escaped = false;
            bool closed = false;
            while (pos < text.size()) {
                const char ch = text[pos++];
                if (string_escaped) {
                    string_escaped = false;
                } else if (ch == '\\') {
                    string_escaped = true;
                } else if (ch == '"') {
                    if (pos < text.size() && text[pos] == '"') {
                        ++pos;
                    } else {
                        closed = true;
                        break;
                    }
                }
            }
            if (!closed) {
                throw ToolError("BAD ARRAY INITIALIZER");
            }
        } else if (text[pos] == '\'') {
            ++pos;
            if (pos >= text.size()) {
                throw ToolError("BAD ARRAY INITIALIZER");
            }
            if (text[pos++] == '\\' && pos < text.size()) {
                ++pos;
            }
            if (pos < text.size() && text[pos] == '\'') {
                ++pos;
            }
        } else {
            int depth = 0;
            while (pos < text.size()) {
                const char ch = text[pos];
                if (ch == '(') {
                    ++depth;
                } else if (ch == ')') {
                    --depth;
                } else if (depth == 0 &&
                           std::isspace(static_cast<unsigned char>(ch))) {
                    break;
                }
                ++pos;
            }
        }
        const std::string value = trim(text.substr(start, pos - start));
        if (value.empty()) {
            throw ToolError("BAD ARRAY INITIALIZER");
        }
        values.push_back(value);
    }
    return values;
}

std::vector<std::string> split_code_block_constants(std::string_view text) {
    std::vector<std::string> values;
    std::size_t pos = 0;
    auto skip_separators = [&]() {
        while (pos < text.size() &&
               (std::isspace(static_cast<unsigned char>(text[pos])) ||
                text[pos] == ',')) {
            ++pos;
        }
    };
    auto consume_base = [&]() -> std::string {
        while (pos < text.size() &&
               std::isspace(static_cast<unsigned char>(text[pos]))) {
            ++pos;
        }
        if (pos >= text.size()) {
            throw ToolError("BAD CODE VALUE");
        }
        const std::size_t start = pos;
        if (text[pos] == '-') {
            ++pos;
            if (pos >= text.size()) {
                throw ToolError("BAD CODE VALUE");
            }
        }
        if (text[pos] == '$') {
            ++pos;
            const std::size_t digits = pos;
            while (pos < text.size() &&
                   std::isxdigit(static_cast<unsigned char>(text[pos]))) {
                ++pos;
            }
            if (digits == pos) {
                throw ToolError("BAD CODE VALUE");
            }
        } else if (text[pos] == '\'') {
            ++pos;
            if (pos >= text.size()) {
                throw ToolError("BAD CODE VALUE");
            }
            if (text[pos++] == '\\' && pos < text.size()) {
                ++pos;
            }
            if (pos < text.size() && text[pos] == '\'') {
                ++pos;
            }
        } else if (text[pos] == '*') {
            ++pos;
        } else if (std::isdigit(static_cast<unsigned char>(text[pos]))) {
            while (pos < text.size() &&
                   std::isdigit(static_cast<unsigned char>(text[pos]))) {
                ++pos;
            }
        } else if (std::isalpha(static_cast<unsigned char>(text[pos])) ||
                   text[pos] == '_') {
            while (pos < text.size() &&
                   (std::isalnum(static_cast<unsigned char>(text[pos])) ||
                    text[pos] == '_')) {
                ++pos;
            }
            if (pos < text.size() && text[pos] == '^') {
                ++pos;
            }
        } else {
            throw ToolError("BAD CODE VALUE");
        }
        return std::string(text.substr(start, pos - start));
    };

    skip_separators();
    while (pos < text.size()) {
        std::string value = consume_base();
        while (true) {
            std::size_t lookahead = pos;
            while (lookahead < text.size() &&
                   std::isspace(static_cast<unsigned char>(text[lookahead]))) {
                ++lookahead;
            }
            if (lookahead >= text.size() || text[lookahead] != '+') {
                break;
            }
            pos = lookahead + 1;
            value += "+" + consume_base();
        }
        values.push_back(std::move(value));
        skip_separators();
    }
    return values;
}

std::vector<ParsedArrayDeclaration> array_declarations_from_line(
    const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    std::string type;
    std::string rest;
    for (const std::string candidate : {"BYTE", "CHAR", "CARD", "INT", "REAL"}) {
        const std::string prefix = candidate + " ARRAY ";
        if (upper.rfind(prefix, 0) == 0) {
            type = candidate == "CHAR" ? "BYTE" : candidate;
            rest = trim(std::string_view(cleaned).substr(prefix.size()));
            break;
        }
    }
    if (type.empty()) {
        return {};
    }

    std::vector<ParsedArrayDeclaration> declarations;
    for (const std::string& declarator : split_declarators(rest)) {
        std::size_t pos = 0;
        while (pos < declarator.size() &&
               (std::isalnum(static_cast<unsigned char>(declarator[pos])) ||
                declarator[pos] == '_')) {
            ++pos;
        }
        const std::string name = declarator.substr(0, pos);
        if (name.empty() || std::isdigit(static_cast<unsigned char>(name.front()))) {
            throw ToolError("BAD ARRAY DECL");
        }
        while (pos < declarator.size() &&
               std::isspace(static_cast<unsigned char>(declarator[pos]))) {
            ++pos;
        }

        std::string size_expression;
        if (pos < declarator.size() && declarator[pos] == '(') {
            const std::size_t close = declarator.find(')', pos + 1);
            if (close == std::string::npos) {
                throw ToolError("BAD ARRAY DECL");
            }
            size_expression = trim(std::string_view(declarator).substr(
                pos + 1, close - pos - 1));
            if (size_expression.empty()) {
                throw ToolError("BAD ARRAY DECL");
            }
            pos = close + 1;
            while (pos < declarator.size() &&
                   std::isspace(static_cast<unsigned char>(declarator[pos]))) {
                ++pos;
            }
        }

        std::string mode = size_expression.empty() ? "POINTER" : "STORAGE";
        std::string expression;
        if (pos < declarator.size()) {
            if (declarator[pos] != '=') {
                throw ToolError("BAD ARRAY DECL");
            }
            expression = trim(std::string_view(declarator).substr(pos + 1));
            if (expression.empty()) {
                throw ToolError("BAD ARRAY DECL");
            }
            if (expression.front() == '"' && expression.back() == '"') {
                mode = "STRING";
            } else if (expression.front() == '[' && expression.back() == ']') {
                mode = "VALUES";
                expression = trim(std::string_view(expression).substr(
                    1, expression.size() - 2));
            } else {
                mode = "ADDRESS";
            }
        }
        declarations.push_back(ParsedArrayDeclaration{
            module_from_arg(name),
            type,
            size_expression,
            mode,
            expression,
        });
    }
    return declarations;
}

struct ParsedGraphicsResourceDeclaration {
    std::string name;
    std::string type;
    std::string path;
};

std::optional<ParsedGraphicsResourceDeclaration>
graphics_resource_declaration_from_line(const std::string& line) {
    static const std::regex declaration(
        R"(^\s*(SPRITE|SPITE|MSPRITE|BITMAP|MBITMAP)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*RESOURCE\s+\"([^\"]+)\"\s*$)",
        std::regex_constants::icase);
    std::smatch match;
    if (!std::regex_match(line, match, declaration)) {
        return std::nullopt;
    }
    std::string type = upper_ascii(match[1].str());
    if (type == "SPITE") {
        type = "SPRITE";
    }
    return ParsedGraphicsResourceDeclaration{
        module_from_arg(match[2].str()),
        type,
        match[3].str(),
    };
}

std::vector<ParsedDeclaration> declarations_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    std::string type;
    std::string rest;
    if (upper.rfind("BYTE ", 0) == 0) {
        type = "BYTE";
        rest = trim(cleaned.substr(5));
    } else if (upper.rfind("CHAR ", 0) == 0) {
        type = "BYTE";
        rest = trim(cleaned.substr(5));
    } else if (upper.rfind("CARD ", 0) == 0) {
        type = "CARD";
        rest = trim(cleaned.substr(5));
    } else if (upper.rfind("REAL ", 0) == 0) {
        type = "REAL";
        rest = trim(cleaned.substr(5));
    } else if (upper.rfind("INT ", 0) == 0) {
        type = "INT";
        rest = trim(cleaned.substr(4));
    } else {
        return {};
    }
    const std::string upper_rest = upper_ascii(rest);
    if (upper_rest.rfind("ARRAY ", 0) == 0) {
        return {};
    }
    const bool pointer = upper_rest.rfind("POINTER ", 0) == 0;
    if (pointer) {
        type += "_POINTER";
        rest = trim(std::string_view(rest).substr(8));
    }

    std::vector<ParsedDeclaration> declarations;
    for (const std::string& declarator : split_declarators(rest)) {
        const std::size_t equals = declarator.find('=');
        std::string name = trim(std::string_view(declarator).substr(0, equals));
        std::string mode = "STORAGE";
        std::string expression;
        if (equals != std::string::npos) {
            expression = trim(std::string_view(declarator).substr(equals + 1));
            if (!pointer && expression.size() >= 2 && expression.front() == '[' && expression.back() == ']') {
                mode = "INITIAL";
                expression = trim(
                    std::string_view(expression).substr(1, expression.size() - 2));
            } else {
                mode = pointer ? "INITIAL" : "ADDRESS";
            }
        }
        if (name.empty() || (mode != "STORAGE" && expression.empty())) {
            throw ToolError("BAD DECL");
        }
        declarations.push_back(ParsedDeclaration{
            module_from_arg(name),
            type,
            mode,
            expression,
        });
    }
    if (declarations.empty()) {
        throw ToolError("BAD DECL");
    }
    return declarations;
}

struct ParsedConstantDeclaration {
    std::string name;
    std::string type;
    std::string expression;
};

std::vector<ParsedConstantDeclaration> constant_declarations_from_line(
    const std::string& line) {
    static const std::regex declaration(
        R"(^\s*(BYTE|CHAR|CARD|INT|REAL)\s+CONST\s+(.+)$)",
        std::regex_constants::icase);
    std::smatch match;
    if (!std::regex_match(line, match, declaration)) {
        return {};
    }
    const std::string type =
        upper_ascii(match[1].str()) == "CHAR" ? "BYTE" : upper_ascii(match[1].str());
    std::vector<ParsedConstantDeclaration> constants;
    for (const std::string& declarator : split_declarators(match[2].str())) {
        const std::size_t equals = declarator.find('=');
        if (equals == std::string::npos) {
            throw ToolError("BAD CONST DECL");
        }
        const std::string name = trim(std::string_view(declarator).substr(0, equals));
        const std::string expression = trim(std::string_view(declarator).substr(equals + 1));
        if (name.empty() || expression.empty() ||
            name.find_first_not_of(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                std::string::npos ||
            std::isdigit(static_cast<unsigned char>(name.front()))) {
            throw ToolError("BAD CONST DECL");
        }
        constants.push_back(ParsedConstantDeclaration{
            module_from_arg(name),
            type,
            expression,
        });
    }
    return constants;
}

struct ParsedRecordField {
    std::string name;
    std::string type;
    std::uint16_t offset = 0;
};

struct ParsedRecordTypeDeclaration {
    std::string name;
    std::vector<ParsedRecordField> fields;
    std::uint16_t size = 0;
};

ParsedRecordTypeDeclaration parse_record_type_body(
    std::string_view name,
    std::string_view body) {
    ParsedRecordTypeDeclaration record;
    record.name = module_from_arg(name);
    std::string current_type;
    std::set<std::string> field_names;
    std::size_t pos = 0;
    while (pos < body.size()) {
        while (pos < body.size() &&
               (std::isspace(static_cast<unsigned char>(body[pos])) || body[pos] == ',')) {
            ++pos;
        }
        if (pos >= body.size()) {
            break;
        }
        if (!std::isalpha(static_cast<unsigned char>(body[pos])) && body[pos] != '_') {
            throw ToolError("BAD TYPE DECL");
        }
        const std::size_t start = pos++;
        while (pos < body.size() &&
               (std::isalnum(static_cast<unsigned char>(body[pos])) || body[pos] == '_')) {
            ++pos;
        }
        const std::string token = upper_ascii(
            std::string_view(body).substr(start, pos - start));
        if (token == "BYTE" || token == "CHAR" || token == "CARD" ||
            token == "INT") {
            current_type = token == "CHAR" ? "BYTE" : token;
            continue;
        }
        if (current_type.empty()) {
            throw ToolError("BAD TYPE DECL");
        }
        if (!field_names.insert(token).second) {
            throw ToolError("DUPLICATE TYPE FIELD " + token);
        }
        const std::uint16_t width = current_type == "BYTE" ? 1 : 2;
        if (record.size > static_cast<std::uint16_t>(0xFFFF - width)) {
            throw ToolError("TYPE SIZE RANGE");
        }
        record.fields.push_back(ParsedRecordField{token, current_type, record.size});
        record.size = static_cast<std::uint16_t>(record.size + width);
    }
    if (record.fields.empty()) {
        throw ToolError("EMPTY TYPE DECL");
    }
    return record;
}

std::vector<ParsedRecordTypeDeclaration> record_types_from_line(
    const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("TYPE ", 0) != 0) {
        return {};
    }

    std::vector<ParsedRecordTypeDeclaration> records;
    std::size_t pos = 5;
    while (pos < cleaned.size()) {
        while (pos < cleaned.size() &&
               (std::isspace(static_cast<unsigned char>(cleaned[pos])) ||
                cleaned[pos] == ',')) {
            ++pos;
        }
        if (pos >= cleaned.size() ||
            (!std::isalpha(static_cast<unsigned char>(cleaned[pos])) &&
             cleaned[pos] != '_')) {
            throw ToolError("BAD TYPE DECL");
        }
        const std::size_t name_start = pos++;
        while (pos < cleaned.size() &&
               (std::isalnum(static_cast<unsigned char>(cleaned[pos])) ||
                cleaned[pos] == '_')) {
            ++pos;
        }
        const std::string name = cleaned.substr(name_start, pos - name_start);
        while (pos < cleaned.size() &&
               std::isspace(static_cast<unsigned char>(cleaned[pos]))) {
            ++pos;
        }
        if (pos >= cleaned.size() || cleaned[pos++] != '=') {
            throw ToolError("BAD TYPE DECL");
        }
        while (pos < cleaned.size() &&
               std::isspace(static_cast<unsigned char>(cleaned[pos]))) {
            ++pos;
        }
        if (pos >= cleaned.size() || cleaned[pos++] != '[') {
            throw ToolError("BAD TYPE DECL");
        }
        const std::size_t body_start = pos;
        while (pos < cleaned.size() && cleaned[pos] != ']') {
            ++pos;
        }
        if (pos >= cleaned.size()) {
            throw ToolError("BAD TYPE DECL");
        }
        records.push_back(parse_record_type_body(
            name,
            std::string_view(cleaned).substr(body_start, pos - body_start)));
        ++pos;
        while (pos < cleaned.size() &&
               std::isspace(static_cast<unsigned char>(cleaned[pos]))) {
            ++pos;
        }
        if (pos < cleaned.size() && cleaned[pos] == ',') {
            ++pos;
        }
    }
    if (records.empty()) {
        throw ToolError("BAD TYPE DECL");
    }
    return records;
}

struct ParsedRecordDeclaration {
    std::string name;
    std::string record_type;
    bool pointer = false;
    std::string mode;
    std::string expression;
};

std::vector<ParsedRecordDeclaration> record_declarations_from_line(
    const std::string& line,
    const std::map<std::string, ParsedRecordTypeDeclaration>& record_types) {
    const std::string cleaned = trim(line);
    std::size_t pos = 0;
    while (pos < cleaned.size() &&
           (std::isalnum(static_cast<unsigned char>(cleaned[pos])) || cleaned[pos] == '_')) {
        ++pos;
    }
    if (pos == 0) {
        return {};
    }
    const std::string record_type = upper_ascii(
        std::string_view(cleaned).substr(0, pos));
    if (record_types.count(record_type) == 0 ||
        (pos < cleaned.size() &&
         !std::isspace(static_cast<unsigned char>(cleaned[pos])))) {
        return {};
    }
    std::string rest = trim(std::string_view(cleaned).substr(pos));
    bool pointer = false;
    const std::string upper_rest = upper_ascii(rest);
    if (upper_rest.rfind("POINTER ", 0) == 0) {
        pointer = true;
        rest = trim(std::string_view(rest).substr(8));
    }
    if (rest.empty()) {
        throw ToolError("BAD RECORD DECL");
    }
    std::vector<ParsedRecordDeclaration> declarations;
    for (const std::string& declarator : split_declarators(rest)) {
        const std::size_t equals = declarator.find('=');
        const std::string name = trim(std::string_view(declarator).substr(0, equals));
        const std::string expression = equals == std::string::npos
            ? std::string{}
            : trim(std::string_view(declarator).substr(equals + 1));
        if (name.empty() ||
            name.find_first_not_of(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                std::string::npos ||
            std::isdigit(static_cast<unsigned char>(name.front())) ||
            (equals != std::string::npos && expression.empty())) {
            throw ToolError("BAD RECORD DECL");
        }
        declarations.push_back(ParsedRecordDeclaration{
            module_from_arg(name),
            record_type,
            pointer,
            equals == std::string::npos ? "STORAGE" : (pointer ? "INITIAL" : "ADDRESS"),
            expression,
        });
    }
    return declarations;
}

struct ParsedAssignment {
    std::string name;
    std::string expression;
    std::string mode;
    std::string index_expression;
};

std::optional<ParsedAssignment> assignment_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::size_t equals = cleaned.find('=');
    if (equals == std::string::npos) {
        return std::nullopt;
    }
    std::string name = trim(std::string_view(cleaned).substr(0, equals));
    const bool shorthand = equals + 1 < cleaned.size() && cleaned[equals + 1] == '=';
    std::string expr = trim(std::string_view(cleaned).substr(equals + (shorthand ? 2 : 1)));
    if (name.empty() || expr.empty()) {
        return std::nullopt;
    }
    if (shorthand) {
        std::string op;
        for (const std::string candidate : {"LSH", "RSH", "MOD", "XOR"}) {
            if (upper_ascii(expr).rfind(candidate, 0) == 0 &&
                (expr.size() == candidate.size() ||
                 std::isspace(static_cast<unsigned char>(expr[candidate.size()])))) {
                op = candidate;
                expr = trim(std::string_view(expr).substr(candidate.size()));
                break;
            }
        }
        if (op.empty() && !expr.empty() &&
            std::string("+-*/&%!").find(expr.front()) != std::string::npos) {
            op.assign(1, expr.front());
            expr = trim(std::string_view(expr).substr(1));
        }
        if (op.empty() || expr.empty()) {
            throw ToolError("BAD SHORTHAND ASSIGN");
        }
        expr = name + " " + op + " (" + expr + ")";
    }
    if (name.back() == '^') {
        const std::string pointer_name = trim(
            std::string_view(name).substr(0, name.size() - 1));
        return ParsedAssignment{
            module_from_arg(pointer_name),
            expr,
            "DEREFERENCE",
            {},
        };
    }
    if (auto indexed = parse_call_expression(name)) {
        if (indexed->arguments.size() != 1) {
            throw ToolError("BAD ARRAY ASSIGN");
        }
        return ParsedAssignment{
            indexed->name,
            expr,
            "INDEX",
            indexed->arguments.front(),
        };
    }
    if (name.find(' ') != std::string::npos) {
        return std::nullopt;
    }
    if (name.find('.') != std::string::npos) {
        bool need_identifier = true;
        for (char ch : name) {
            if (ch == '.') {
                if (need_identifier) {
                    throw ToolError("BAD FIELD ASSIGN");
                }
                need_identifier = true;
            } else if ((need_identifier &&
                        (std::isalpha(static_cast<unsigned char>(ch)) || ch == '_')) ||
                       (!need_identifier &&
                        (std::isalnum(static_cast<unsigned char>(ch)) || ch == '_'))) {
                need_identifier = false;
            } else {
                throw ToolError("BAD FIELD ASSIGN");
            }
        }
        if (need_identifier) {
            throw ToolError("BAD FIELD ASSIGN");
        }
        return ParsedAssignment{upper_ascii(name), expr, "VARIABLE", {}};
    }
    return ParsedAssignment{module_from_arg(name), expr, "VARIABLE", {}};
}

std::optional<std::string> conditional_expr_from_line(
    const std::string& line,
    std::string_view keyword,
    bool requires_then) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    const std::string prefix = upper_ascii(keyword) + " ";
    if (upper.rfind(prefix, 0) != 0) {
        return std::nullopt;
    }
    if (!requires_then) {
        const std::string expression = trim(
            std::string_view(cleaned).substr(prefix.size()));
        if (expression.empty()) {
            throw ToolError("BAD CONDITION");
        }
        return expression;
    }
    const std::string marker = " THEN";
    const std::size_t then_pos = upper.rfind(marker);
    if (then_pos == std::string::npos || then_pos < prefix.size()) {
        throw ToolError("BAD IF");
    }
    const std::string expression = trim(
        std::string_view(cleaned).substr(prefix.size(), then_pos - prefix.size()));
    if (expression.empty()) {
        throw ToolError("BAD IF");
    }
    return expression;
}

struct ParsedForClause {
    std::string counter;
    std::string initial;
    std::string final_value;
    std::string step;
};

std::optional<std::size_t> find_top_level_word(
    std::string_view text,
    std::string_view word) {
    const std::string upper = upper_ascii(text);
    const std::string wanted = upper_ascii(word);
    int depth = 0;
    for (std::size_t i = 0; i + wanted.size() <= upper.size(); ++i) {
        if (upper[i] == '(') {
            ++depth;
            continue;
        }
        if (upper[i] == ')') {
            --depth;
            if (depth < 0) {
                throw ToolError("BAD FOR");
            }
            continue;
        }
        if (depth != 0 || upper.compare(i, wanted.size(), wanted) != 0) {
            continue;
        }
        const bool before_ok =
            i == 0 || std::isspace(static_cast<unsigned char>(upper[i - 1]));
        const std::size_t after = i + wanted.size();
        const bool after_ok =
            after == upper.size() || std::isspace(static_cast<unsigned char>(upper[after]));
        if (before_ok && after_ok) {
            return i;
        }
    }
    if (depth != 0) {
        throw ToolError("BAD FOR");
    }
    return std::nullopt;
}

std::optional<ParsedForClause> for_clause_from_line(const std::string& line) {
    const std::string cleaned = trim(line);
    const std::string upper = upper_ascii(cleaned);
    if (upper.rfind("FOR ", 0) != 0) {
        return std::nullopt;
    }
    const std::string clause = trim(std::string_view(cleaned).substr(4));
    const std::size_t equals = clause.find('=');
    if (equals == std::string::npos) {
        throw ToolError("BAD FOR");
    }
    const std::string counter = trim(std::string_view(clause).substr(0, equals));
    const std::string values = trim(std::string_view(clause).substr(equals + 1));
    const auto to_pos = find_top_level_word(values, "TO");
    if (!to_pos || counter.empty() ||
        counter.find_first_not_of(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") != std::string::npos) {
        throw ToolError("BAD FOR");
    }
    const std::string initial = trim(std::string_view(values).substr(0, *to_pos));
    const std::string final_and_step = trim(
        std::string_view(values).substr(*to_pos + 2));
    const auto step_pos = find_top_level_word(final_and_step, "STEP");
    const std::string final_value = trim(std::string_view(final_and_step).substr(
        0, step_pos ? *step_pos : std::string::npos));
    const std::string step = step_pos
        ? trim(std::string_view(final_and_step).substr(*step_pos + 4))
        : "1";
    if (initial.empty() || final_value.empty() || step.empty()) {
        throw ToolError("BAD FOR");
    }
    return ParsedForClause{module_from_arg(counter), initial, final_value, step};
}

enum class AsmAddressMode {
    Implied,
    Accumulator,
    Immediate,
    ZeroPage,
    ZeroPageX,
    ZeroPageY,
    Absolute,
    AbsoluteX,
    AbsoluteY,
    Indirect,
    IndexedIndirect,
    IndirectIndexed,
    Relative,
};

std::size_t asm_instruction_size(AsmAddressMode mode) {
    switch (mode) {
        case AsmAddressMode::Implied:
        case AsmAddressMode::Accumulator:
            return 1;
        case AsmAddressMode::Immediate:
        case AsmAddressMode::ZeroPage:
        case AsmAddressMode::ZeroPageX:
        case AsmAddressMode::ZeroPageY:
        case AsmAddressMode::IndexedIndirect:
        case AsmAddressMode::IndirectIndexed:
        case AsmAddressMode::Relative:
            return 2;
        case AsmAddressMode::Absolute:
        case AsmAddressMode::AbsoluteX:
        case AsmAddressMode::AbsoluteY:
        case AsmAddressMode::Indirect:
            return 3;
    }
    throw ToolError("BAD ASM ADDRESS MODE");
}

std::optional<std::uint8_t> asm_opcode(
    std::string_view mnemonic,
    AsmAddressMode mode) {
    using Key = std::pair<std::string, AsmAddressMode>;
    static const std::map<Key, std::uint8_t> opcodes = {
        {{"ADC", AsmAddressMode::Immediate}, 0x69},
        {{"ADC", AsmAddressMode::ZeroPage}, 0x65},
        {{"ADC", AsmAddressMode::ZeroPageX}, 0x75},
        {{"ADC", AsmAddressMode::Absolute}, 0x6D},
        {{"ADC", AsmAddressMode::AbsoluteX}, 0x7D},
        {{"ADC", AsmAddressMode::AbsoluteY}, 0x79},
        {{"ADC", AsmAddressMode::IndexedIndirect}, 0x61},
        {{"ADC", AsmAddressMode::IndirectIndexed}, 0x71},
        {{"AND", AsmAddressMode::Immediate}, 0x29},
        {{"AND", AsmAddressMode::ZeroPage}, 0x25},
        {{"AND", AsmAddressMode::ZeroPageX}, 0x35},
        {{"AND", AsmAddressMode::Absolute}, 0x2D},
        {{"AND", AsmAddressMode::AbsoluteX}, 0x3D},
        {{"AND", AsmAddressMode::AbsoluteY}, 0x39},
        {{"AND", AsmAddressMode::IndexedIndirect}, 0x21},
        {{"AND", AsmAddressMode::IndirectIndexed}, 0x31},
        {{"ASL", AsmAddressMode::Accumulator}, 0x0A},
        {{"ASL", AsmAddressMode::ZeroPage}, 0x06},
        {{"ASL", AsmAddressMode::ZeroPageX}, 0x16},
        {{"ASL", AsmAddressMode::Absolute}, 0x0E},
        {{"ASL", AsmAddressMode::AbsoluteX}, 0x1E},
        {{"BCC", AsmAddressMode::Relative}, 0x90},
        {{"BCS", AsmAddressMode::Relative}, 0xB0},
        {{"BEQ", AsmAddressMode::Relative}, 0xF0},
        {{"BIT", AsmAddressMode::ZeroPage}, 0x24},
        {{"BIT", AsmAddressMode::Absolute}, 0x2C},
        {{"BMI", AsmAddressMode::Relative}, 0x30},
        {{"BNE", AsmAddressMode::Relative}, 0xD0},
        {{"BPL", AsmAddressMode::Relative}, 0x10},
        {{"BRK", AsmAddressMode::Implied}, 0x00},
        {{"BVC", AsmAddressMode::Relative}, 0x50},
        {{"BVS", AsmAddressMode::Relative}, 0x70},
        {{"CLC", AsmAddressMode::Implied}, 0x18},
        {{"CLD", AsmAddressMode::Implied}, 0xD8},
        {{"CLI", AsmAddressMode::Implied}, 0x58},
        {{"CLV", AsmAddressMode::Implied}, 0xB8},
        {{"CMP", AsmAddressMode::Immediate}, 0xC9},
        {{"CMP", AsmAddressMode::ZeroPage}, 0xC5},
        {{"CMP", AsmAddressMode::ZeroPageX}, 0xD5},
        {{"CMP", AsmAddressMode::Absolute}, 0xCD},
        {{"CMP", AsmAddressMode::AbsoluteX}, 0xDD},
        {{"CMP", AsmAddressMode::AbsoluteY}, 0xD9},
        {{"CMP", AsmAddressMode::IndexedIndirect}, 0xC1},
        {{"CMP", AsmAddressMode::IndirectIndexed}, 0xD1},
        {{"CPX", AsmAddressMode::Immediate}, 0xE0},
        {{"CPX", AsmAddressMode::ZeroPage}, 0xE4},
        {{"CPX", AsmAddressMode::Absolute}, 0xEC},
        {{"CPY", AsmAddressMode::Immediate}, 0xC0},
        {{"CPY", AsmAddressMode::ZeroPage}, 0xC4},
        {{"CPY", AsmAddressMode::Absolute}, 0xCC},
        {{"DEC", AsmAddressMode::ZeroPage}, 0xC6},
        {{"DEC", AsmAddressMode::ZeroPageX}, 0xD6},
        {{"DEC", AsmAddressMode::Absolute}, 0xCE},
        {{"DEC", AsmAddressMode::AbsoluteX}, 0xDE},
        {{"DEX", AsmAddressMode::Implied}, 0xCA},
        {{"DEY", AsmAddressMode::Implied}, 0x88},
        {{"EOR", AsmAddressMode::Immediate}, 0x49},
        {{"EOR", AsmAddressMode::ZeroPage}, 0x45},
        {{"EOR", AsmAddressMode::ZeroPageX}, 0x55},
        {{"EOR", AsmAddressMode::Absolute}, 0x4D},
        {{"EOR", AsmAddressMode::AbsoluteX}, 0x5D},
        {{"EOR", AsmAddressMode::AbsoluteY}, 0x59},
        {{"EOR", AsmAddressMode::IndexedIndirect}, 0x41},
        {{"EOR", AsmAddressMode::IndirectIndexed}, 0x51},
        {{"INC", AsmAddressMode::ZeroPage}, 0xE6},
        {{"INC", AsmAddressMode::ZeroPageX}, 0xF6},
        {{"INC", AsmAddressMode::Absolute}, 0xEE},
        {{"INC", AsmAddressMode::AbsoluteX}, 0xFE},
        {{"INX", AsmAddressMode::Implied}, 0xE8},
        {{"INY", AsmAddressMode::Implied}, 0xC8},
        {{"JMP", AsmAddressMode::Absolute}, 0x4C},
        {{"JMP", AsmAddressMode::Indirect}, 0x6C},
        {{"JSR", AsmAddressMode::Absolute}, 0x20},
        {{"LDA", AsmAddressMode::Immediate}, 0xA9},
        {{"LDA", AsmAddressMode::ZeroPage}, 0xA5},
        {{"LDA", AsmAddressMode::ZeroPageX}, 0xB5},
        {{"LDA", AsmAddressMode::Absolute}, 0xAD},
        {{"LDA", AsmAddressMode::AbsoluteX}, 0xBD},
        {{"LDA", AsmAddressMode::AbsoluteY}, 0xB9},
        {{"LDA", AsmAddressMode::IndexedIndirect}, 0xA1},
        {{"LDA", AsmAddressMode::IndirectIndexed}, 0xB1},
        {{"LDX", AsmAddressMode::Immediate}, 0xA2},
        {{"LDX", AsmAddressMode::ZeroPage}, 0xA6},
        {{"LDX", AsmAddressMode::ZeroPageY}, 0xB6},
        {{"LDX", AsmAddressMode::Absolute}, 0xAE},
        {{"LDX", AsmAddressMode::AbsoluteY}, 0xBE},
        {{"LDY", AsmAddressMode::Immediate}, 0xA0},
        {{"LDY", AsmAddressMode::ZeroPage}, 0xA4},
        {{"LDY", AsmAddressMode::ZeroPageX}, 0xB4},
        {{"LDY", AsmAddressMode::Absolute}, 0xAC},
        {{"LDY", AsmAddressMode::AbsoluteX}, 0xBC},
        {{"LSR", AsmAddressMode::Accumulator}, 0x4A},
        {{"LSR", AsmAddressMode::ZeroPage}, 0x46},
        {{"LSR", AsmAddressMode::ZeroPageX}, 0x56},
        {{"LSR", AsmAddressMode::Absolute}, 0x4E},
        {{"LSR", AsmAddressMode::AbsoluteX}, 0x5E},
        {{"NOP", AsmAddressMode::Implied}, 0xEA},
        {{"ORA", AsmAddressMode::Immediate}, 0x09},
        {{"ORA", AsmAddressMode::ZeroPage}, 0x05},
        {{"ORA", AsmAddressMode::ZeroPageX}, 0x15},
        {{"ORA", AsmAddressMode::Absolute}, 0x0D},
        {{"ORA", AsmAddressMode::AbsoluteX}, 0x1D},
        {{"ORA", AsmAddressMode::AbsoluteY}, 0x19},
        {{"ORA", AsmAddressMode::IndexedIndirect}, 0x01},
        {{"ORA", AsmAddressMode::IndirectIndexed}, 0x11},
        {{"PHA", AsmAddressMode::Implied}, 0x48},
        {{"PHP", AsmAddressMode::Implied}, 0x08},
        {{"PLA", AsmAddressMode::Implied}, 0x68},
        {{"PLP", AsmAddressMode::Implied}, 0x28},
        {{"ROL", AsmAddressMode::Accumulator}, 0x2A},
        {{"ROL", AsmAddressMode::ZeroPage}, 0x26},
        {{"ROL", AsmAddressMode::ZeroPageX}, 0x36},
        {{"ROL", AsmAddressMode::Absolute}, 0x2E},
        {{"ROL", AsmAddressMode::AbsoluteX}, 0x3E},
        {{"ROR", AsmAddressMode::Accumulator}, 0x6A},
        {{"ROR", AsmAddressMode::ZeroPage}, 0x66},
        {{"ROR", AsmAddressMode::ZeroPageX}, 0x76},
        {{"ROR", AsmAddressMode::Absolute}, 0x6E},
        {{"ROR", AsmAddressMode::AbsoluteX}, 0x7E},
        {{"RTI", AsmAddressMode::Implied}, 0x40},
        {{"RTS", AsmAddressMode::Implied}, 0x60},
        {{"SBC", AsmAddressMode::Immediate}, 0xE9},
        {{"SBC", AsmAddressMode::ZeroPage}, 0xE5},
        {{"SBC", AsmAddressMode::ZeroPageX}, 0xF5},
        {{"SBC", AsmAddressMode::Absolute}, 0xED},
        {{"SBC", AsmAddressMode::AbsoluteX}, 0xFD},
        {{"SBC", AsmAddressMode::AbsoluteY}, 0xF9},
        {{"SBC", AsmAddressMode::IndexedIndirect}, 0xE1},
        {{"SBC", AsmAddressMode::IndirectIndexed}, 0xF1},
        {{"SEC", AsmAddressMode::Implied}, 0x38},
        {{"SED", AsmAddressMode::Implied}, 0xF8},
        {{"SEI", AsmAddressMode::Implied}, 0x78},
        {{"STA", AsmAddressMode::ZeroPage}, 0x85},
        {{"STA", AsmAddressMode::ZeroPageX}, 0x95},
        {{"STA", AsmAddressMode::Absolute}, 0x8D},
        {{"STA", AsmAddressMode::AbsoluteX}, 0x9D},
        {{"STA", AsmAddressMode::AbsoluteY}, 0x99},
        {{"STA", AsmAddressMode::IndexedIndirect}, 0x81},
        {{"STA", AsmAddressMode::IndirectIndexed}, 0x91},
        {{"STX", AsmAddressMode::ZeroPage}, 0x86},
        {{"STX", AsmAddressMode::ZeroPageY}, 0x96},
        {{"STX", AsmAddressMode::Absolute}, 0x8E},
        {{"STY", AsmAddressMode::ZeroPage}, 0x84},
        {{"STY", AsmAddressMode::ZeroPageX}, 0x94},
        {{"STY", AsmAddressMode::Absolute}, 0x8C},
        {{"TAX", AsmAddressMode::Implied}, 0xAA},
        {{"TAY", AsmAddressMode::Implied}, 0xA8},
        {{"TSX", AsmAddressMode::Implied}, 0xBA},
        {{"TXA", AsmAddressMode::Implied}, 0x8A},
        {{"TXS", AsmAddressMode::Implied}, 0x9A},
        {{"TYA", AsmAddressMode::Implied}, 0x98},
    };
    const auto found = opcodes.find(Key{upper_ascii(mnemonic), mode});
    if (found == opcodes.end()) {
        return std::nullopt;
    }
    return found->second;
}

struct SourceOp {
    enum class Kind {
        Call,
        Return,
        Print,
        PrintString,
        PrintInt,
        PrintIntCall,
        PrintReal,
        Assign,
        Declare,
        RecordDeclare,
        ArrayDeclare,
        ReuDeclare,
        Code,
        AsmBlock,
        If,
        ElseIf,
        Else,
        Fi,
        For,
        While,
        Do,
        Until,
        Od,
        Exit,
    };
    Kind kind = Kind::Call;
    std::string value;
    std::string aux;
    std::size_t line = 0;
    std::string mode;
    std::string expression;
    std::string size_expression;

    SourceOp() = default;
    SourceOp(
        Kind source_kind,
        std::string source_value,
        std::string source_aux,
        std::size_t source_line,
        std::string source_mode = {},
        std::string source_expression = {},
        std::string source_size_expression = {})
        : kind(source_kind),
          value(std::move(source_value)),
          aux(std::move(source_aux)),
          line(source_line),
          mode(std::move(source_mode)),
          expression(std::move(source_expression)),
          size_expression(std::move(source_size_expression)) {}
};

struct SourceProc {
    std::string name;
    std::vector<SourceParameter> parameters;
    std::vector<SourceOp> ops;
    std::size_t line = 0;
    bool is_overlay = false;
    std::string return_type;
    bool declaration_only = false;
    std::string address_expression;
};

struct SourceGlobal {
    std::string name;
    std::string type;
    std::size_t line = 0;
    std::string mode;
    std::string expression;
    std::string size_expression;
};

struct SourceConstant {
    std::string name;
    std::string type;
    std::string expression;
    std::size_t line = 0;
};

struct SourceRecordType {
    std::string name;
    std::vector<ParsedRecordField> fields;
    std::uint16_t size = 0;
    std::size_t line = 0;
};

struct ParsedSource {
    std::vector<SourceConstant> constants;
    std::vector<SourceRecordType> record_types;
    std::vector<SourceGlobal> globals;
    std::vector<SourceProc> procs;
};

ParsedSource parse_source(const std::string& text) {
    ParsedSource source;
    std::optional<std::size_t> current;
    auto lines = split_lines(text);
    auto square_bracket_depth = [](std::string_view line) {
        int depth = 0;
        bool in_string = false;
        bool escaped = false;
        bool character_byte = false;
        for (char ch : line) {
            if (!in_string && character_byte) {
                character_byte = ch == '\\';
                continue;
            }
            if (in_string) {
                if (escaped) {
                    escaped = false;
                } else if (ch == '\\') {
                    escaped = true;
                } else if (ch == '"') {
                    in_string = false;
                }
                continue;
            }
            if (ch == '"') {
                in_string = true;
            } else if (ch == '\'') {
                character_byte = true;
            } else if (ch == '[') {
                ++depth;
            } else if (ch == ']') {
                --depth;
                if (depth < 0) {
                    throw ToolError("BAD BRACKET");
                }
            }
        }
        return depth;
    };
    auto parenthesis_depth = [](std::string_view line) {
        int depth = 0;
        bool in_string = false;
        bool escaped = false;
        bool character_byte = false;
        for (char ch : line) {
            if (!in_string && character_byte) {
                character_byte = ch == '\\';
                continue;
            }
            if (in_string) {
                if (escaped) {
                    escaped = false;
                } else if (ch == '\\') {
                    escaped = true;
                } else if (ch == '"') {
                    in_string = false;
                }
                continue;
            }
            if (ch == '"') {
                in_string = true;
            } else if (ch == '\'') {
                character_byte = true;
            } else if (ch == '(') {
                ++depth;
            } else if (ch == ')') {
                --depth;
                if (depth < 0) {
                    throw ToolError("BAD PARENTHESIS");
                }
            }
        }
        return depth;
    };
    for (std::size_t i = 0; i < lines.size(); ++i) {
        std::string combined = strip_source_comment(lines[i]);
        const std::string combined_upper = upper_ascii(trim(combined));
        const bool preserve_block_lines =
            combined_upper.rfind("ASMBLOCK ", 0) == 0;
        while (!trim(combined).empty() &&
               (trim(combined).back() == ',' || square_bracket_depth(combined) > 0 ||
                parenthesis_depth(combined) > 0)) {
            std::size_t next = i + 1;
            while (next < lines.size() &&
                   trim(strip_source_comment(lines[next])).empty()) {
                lines[next].clear();
                ++next;
            }
            if (next >= lines.size()) {
                throw ToolError("BAD CONTINUATION LINE " + std::to_string(i + 1));
            }
            combined += preserve_block_lines ? "\n" : " ";
            combined += trim(strip_source_comment(lines[next]));
            lines[next].clear();
        }
        lines[i] = std::move(combined);
    }
    auto mark_empty_routine_declaration = [&]() {
        if (!current) {
            return;
        }
        SourceProc& proc = source.procs[*current];
        if (proc.ops.empty() && upper_ascii(proc.name) != "MAIN") {
            proc.declaration_only = true;
        }
    };
    std::map<std::string, ParsedRecordTypeDeclaration> known_record_types;
    std::set<std::string> known_record_type_names;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        const std::string line = strip_source_comment(lines[i]);
        const std::string cleaned = trim(line);
        const std::string upper = upper_ascii(cleaned);
        if (cleaned.empty()) {
            continue;
        }
        if (upper == "MODULE" || upper.rfind("MODULE ", 0) == 0) {
            mark_empty_routine_declaration();
            current = std::nullopt;
            continue;
        }
        if (auto records = record_types_from_line(line); !records.empty()) {
            for (const ParsedRecordTypeDeclaration& record : records) {
                if (!known_record_types.emplace(record.name, record).second) {
                    throw ToolError(
                        "DUPLICATE TYPE LINE " + std::to_string(i + 1) + ": " +
                        record.name);
                }
                known_record_type_names.insert(record.name);
                source.record_types.push_back(SourceRecordType{
                    record.name,
                    record.fields,
                    record.size,
                    i + 1,
                });
            }
            continue;
        }
        if (upper.rfind("OVERLAY ", 0) == 0) {
            if (current) {
                mark_empty_routine_declaration();
                if (!source.procs[*current].declaration_only) {
                    throw ToolError(
                        "NESTED OVERLAY LINE " + std::to_string(i + 1));
                }
            }
            const std::string name = trim(std::string_view(cleaned).substr(8));
            if (name.empty() ||
                name.find_first_not_of(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                    std::string::npos) {
                throw ToolError("BAD OVERLAY LINE " + std::to_string(i + 1));
            }
            source.procs.push_back(SourceProc{
                module_from_arg(name),
                {},
                {},
                i + 1,
                true,
                {},
                false,
                {},
            });
            current = source.procs.size() - 1;
            continue;
        }
        if (auto proc = proc_name_from_line(line)) {
            mark_empty_routine_declaration();
            source.procs.push_back(SourceProc{
                *proc,
                proc_parameters_from_line(line, known_record_type_names),
                {},
                i + 1,
                false,
                {},
                false,
                {},
            });
            source.procs.back().address_expression = routine_address_from_line(line);
            current = source.procs.size() - 1;
            continue;
        }
        if (auto function = function_from_line(line, known_record_type_names)) {
            mark_empty_routine_declaration();
            source.procs.push_back(SourceProc{
                function->name,
                std::move(function->parameters),
                {},
                i + 1,
                false,
                function->return_type,
                false,
                {},
            });
            source.procs.back().address_expression = function->address_expression;
            current = source.procs.size() - 1;
            continue;
        }
        if (upper == "ENDPROC" || upper == "ENDFUNC" || upper == "ENDOVERLAY") {
            current = std::nullopt;
            continue;
        }
        if (current) {
            if (graphics_resource_declaration_from_line(line)) {
                throw ToolError(
                    "RESOURCE MUST BE GLOBAL LINE " + std::to_string(i + 1));
            }
            if (!constant_declarations_from_line(line).empty()) {
                throw ToolError("CONST MUST BE GLOBAL LINE " + std::to_string(i + 1));
            }
            if (upper == "RETURN") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Return, {}, {}, i + 1});
                continue;
            }
            if (upper.rfind("RETURN", 0) == 0 && upper.size() > 6 &&
                (cleaned[6] == '(' ||
                 std::isspace(static_cast<unsigned char>(cleaned[6])))) {
                const std::string result = trim(std::string_view(cleaned).substr(6));
                if (result.size() < 3 || result.front() != '(' ||
                    result.back() != ')' ||
                    trim(std::string_view(result).substr(1, result.size() - 2)).empty()) {
                    throw ToolError(
                        "BAD RETURN LINE " + std::to_string(i + 1));
                }
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::Return,
                    trim(std::string_view(result).substr(1, result.size() - 2)),
                    {},
                    i + 1,
                });
            } else if (auto expr = conditional_expr_from_line(line, "IF", true)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::If, *expr, {}, i + 1});
            } else if (auto expr = conditional_expr_from_line(line, "ELSEIF", true)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::ElseIf, *expr, {}, i + 1});
            } else if (upper == "ELSE") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Else, {}, {}, i + 1});
            } else if (upper == "FI") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Fi, {}, {}, i + 1});
            } else if (auto clause = for_clause_from_line(line)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::For, cleaned, {}, i + 1});
            } else if (auto expr = conditional_expr_from_line(line, "WHILE", false)) {
                std::string condition = *expr;
                const std::string upper_condition = upper_ascii(condition);
                const bool inline_do =
                    upper_condition.size() > 3 &&
                    upper_condition.rfind(" DO") == upper_condition.size() - 3;
                if (inline_do) {
                    condition = trim(std::string_view(condition).substr(
                        0, condition.size() - 3));
                    if (condition.empty()) {
                        throw ToolError("BAD CONDITION");
                    }
                }
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::While, condition, {}, i + 1});
                if (inline_do) {
                    source.procs[*current].ops.push_back(
                        SourceOp{SourceOp::Kind::Do, {}, {}, i + 1});
                }
            } else if (upper == "DO") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Do, {}, {}, i + 1});
            } else if (auto expr = conditional_expr_from_line(line, "UNTIL", false)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Until, *expr, {}, i + 1});
            } else if (upper == "OD") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Od, {}, {}, i + 1});
            } else if (upper == "EXIT") {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Exit, {}, {}, i + 1});
            } else if (upper.rfind("ASMBLOCK ", 0) == 0) {
                const std::string block = trim(
                    std::string_view(cleaned).substr(8));
                if (block.size() < 2 || block.front() != '[' ||
                    block.back() != ']') {
                    throw ToolError(
                        "BAD ASMBLOCK LINE " + std::to_string(i + 1));
                }
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::AsmBlock,
                    std::string(std::string_view(block).substr(
                        1, block.size() - 2)),
                    {},
                    i + 1,
                });
            } else if (cleaned.size() >= 2 && cleaned.front() == '[' &&
                       cleaned.back() == ']') {
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::Code,
                    trim(std::string_view(cleaned).substr(1, cleaned.size() - 2)),
                    {},
                    i + 1,
                });
            } else if (auto print_text = print_string_from_line(line)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Print, *print_text, {}, i + 1});
            } else if (auto expr = print_string_expr_from_line(line)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::PrintString, *expr, {}, i + 1});
            } else if (auto expr = print_int_expr_from_line(line)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::PrintInt, *expr, {}, i + 1});
            } else if (auto expr = print_int_call_from_line(line)) {
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::PrintIntCall, *expr, {}, i + 1});
            } else if (auto real_print = print_real_expr_from_line(line)) {
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::PrintReal,
                    real_print->first,
                    real_print->second ? "NEWLINE" : "",
                    i + 1,
                });
            } else if (auto declaration = reu_declaration_from_line(line)) {
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::ReuDeclare,
                    declaration->name,
                    declaration->size_expression,
                    i + 1,
                });
            } else if (auto declarations = array_declarations_from_line(line);
                       !declarations.empty()) {
                for (const auto& declaration : declarations) {
                    source.procs[*current].ops.push_back(SourceOp{
                        SourceOp::Kind::ArrayDeclare,
                        declaration.name,
                        declaration.type,
                        i + 1,
                        declaration.mode,
                        declaration.expression,
                        declaration.size_expression,
                    });
                }
            } else if (auto declarations =
                           record_declarations_from_line(line, known_record_types);
                       !declarations.empty()) {
                for (const auto& declaration : declarations) {
                    source.procs[*current].ops.push_back(SourceOp{
                        SourceOp::Kind::RecordDeclare,
                        declaration.name,
                        declaration.record_type,
                        i + 1,
                        declaration.mode,
                        declaration.expression,
                        declaration.pointer ? "POINTER" : "STORAGE",
                    });
                }
            } else if (auto declarations = declarations_from_line(line); !declarations.empty()) {
                for (const auto& declaration : declarations) {
                    source.procs[*current].ops.push_back(SourceOp{
                        SourceOp::Kind::Declare,
                        declaration.name,
                        declaration.type,
                        i + 1,
                        declaration.mode,
                        declaration.expression,
                    });
                }
            } else if (auto assignment = assignment_from_line(line)) {
                source.procs[*current].ops.push_back(SourceOp{
                    SourceOp::Kind::Assign,
                    assignment->name,
                    assignment->expression,
                    i + 1,
                    assignment->mode,
                    assignment->index_expression,
                });
            } else if (auto call = call_name_from_line(line)) {
                const std::size_t open = cleaned.find('(');
                const std::size_t close = cleaned.rfind(')');
                const std::string call_args =
                    open == std::string::npos || close == std::string::npos || close <= open
                        ? std::string{}
                        : trim(std::string_view(cleaned).substr(open + 1, close - open - 1));
                source.procs[*current].ops.push_back(
                    SourceOp{SourceOp::Kind::Call, *call, call_args, i + 1});
            } else {
                throw ToolError(
                    "UNSUPPORTED LINE " + std::to_string(i + 1) + ": " + cleaned);
            }
            continue;
        }

        if (auto constants = constant_declarations_from_line(line); !constants.empty()) {
            for (const auto& constant : constants) {
                source.constants.push_back(SourceConstant{
                    constant.name,
                    constant.type,
                    constant.expression,
                    i + 1,
                });
            }
            continue;
        }
        if (auto declaration = reu_declaration_from_line(line)) {
            source.globals.push_back(SourceGlobal{
                declaration->name,
                "REU_BYTE_ARRAY",
                i + 1,
                "STORAGE",
                declaration->size_expression,
                {},
            });
            continue;
        }
        if (auto resource = graphics_resource_declaration_from_line(line)) {
            source.globals.push_back(SourceGlobal{
                resource->name,
                resource->type + "_RESOURCE",
                i + 1,
                "RESOURCE",
                resource->path,
                {},
            });
            continue;
        }
        if (auto declarations = array_declarations_from_line(line); !declarations.empty()) {
            for (const auto& declaration : declarations) {
                source.globals.push_back(SourceGlobal{
                    declaration.name,
                    declaration.type + "_ARRAY",
                    i + 1,
                    declaration.mode,
                    declaration.expression,
                    declaration.size_expression,
                });
            }
            continue;
        }
        if (auto declarations = record_declarations_from_line(line, known_record_types);
            !declarations.empty()) {
            for (const auto& declaration : declarations) {
                source.globals.push_back(SourceGlobal{
                    declaration.name,
                    std::string(declaration.pointer ? "RECORD_POINTER:" : "RECORD:") +
                        declaration.record_type,
                    i + 1,
                    declaration.mode,
                    declaration.expression,
                    {},
                });
            }
            continue;
        }
        if (auto declarations = declarations_from_line(line); !declarations.empty()) {
            for (const auto& declaration : declarations) {
                source.globals.push_back(SourceGlobal{
                    declaration.name,
                    declaration.type,
                    i + 1,
                    declaration.mode,
                    declaration.expression,
                    {},
                });
            }
            continue;
        }
        throw ToolError("UNSUPPORTED LINE " + std::to_string(i + 1) + ": " + cleaned);
    }
    mark_empty_routine_declaration();
    if (source.procs.empty()) {
        throw ToolError("NO PROC");
    }
    return source;
}

struct ObjExport {
    std::string name;
    std::uint16_t offset = 0;
    std::uint16_t size = 0;
};

enum class ObjRelocPart {
    Word,
    LowByte,
    HighByte,
};

struct ObjReloc {
    std::uint16_t offset = 0;
    bool import = false;
    int import_index = -1;
    std::string symbol;
    std::int32_t addend = 0;
    ObjRelocPart part = ObjRelocPart::Word;
};

struct ObjLineRecord {
    std::uint16_t offset = 0;
    std::size_t line = 0;
};

struct ObjectFile {
    std::string module;
    std::string source_file;
    std::vector<ObjExport> exports;
    std::vector<std::string> imports;
    std::vector<ObjReloc> relocs;
    std::vector<ObjLineRecord> lines;
    std::vector<std::uint8_t> code;
};

std::uint16_t parse_object_word(std::string_view text, int base = 0) {
    try {
        std::size_t consumed = 0;
        const unsigned long value = std::stoul(std::string(text), &consumed, base);
        if (consumed != text.size() || value > std::numeric_limits<std::uint16_t>::max()) {
            throw ToolError("BAD OBJECT");
        }
        return static_cast<std::uint16_t>(value);
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD OBJECT");
    }
}

int parse_import_index(std::string_view text) {
    try {
        std::size_t consumed = 0;
        const unsigned long value = std::stoul(std::string(text), &consumed, 10);
        if (consumed != text.size() || value > static_cast<unsigned long>(std::numeric_limits<int>::max())) {
            throw ToolError("BAD OBJECT");
        }
        return static_cast<int>(value);
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD OBJECT");
    }
}

std::int32_t parse_relocation_addend(std::string_view text) {
    try {
        std::size_t consumed = 0;
        const long long value = std::stoll(std::string(text), &consumed, 10);
        if (consumed != text.size() ||
            value < std::numeric_limits<std::int32_t>::min() ||
            value > std::numeric_limits<std::int32_t>::max()) {
            throw ToolError("BAD OBJECT");
        }
        return static_cast<std::int32_t>(value);
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD OBJECT");
    }
}

std::vector<int> parse_machine_body_marker(std::string_view text) {
    const std::string marker = upper_ascii(trim(text));
    if (marker.empty() || marker.back() != 'M') {
        throw ToolError("UNSUPPORTED OBJECT BODY");
    }

    std::vector<int> imports;
    std::size_t pos = 0;
    while (pos + 1 < marker.size()) {
        if (marker[pos] != 'U') {
            throw ToolError("UNSUPPORTED OBJECT BODY");
        }
        const std::size_t digits = ++pos;
        while (pos + 1 < marker.size() &&
               std::isdigit(static_cast<unsigned char>(marker[pos]))) {
            ++pos;
        }
        if (digits == pos) {
            throw ToolError("BAD OBJECT");
        }
        imports.push_back(parse_import_index(
            std::string_view(marker).substr(digits, pos - digits)));
    }
    if (pos + 1 != marker.size()) {
        throw ToolError("BAD OBJECT");
    }
    return imports;
}

std::size_t parse_object_size(std::string_view text) {
    try {
        std::size_t consumed = 0;
        const unsigned long long value =
            std::stoull(std::string(text), &consumed, 10);
        if (consumed != text.size() ||
            value > std::numeric_limits<std::size_t>::max()) {
            throw ToolError("BAD OBJECT");
        }
        return static_cast<std::size_t>(value);
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD OBJECT");
    }
}

bool is_legacy_placeholder_object(const ObjectFile& object) {
    if (object.code.size() < 2 || object.code.back() != 0) {
        return false;
    }
    const std::string payload(
        object.code.begin(),
        object.code.end() - 1);
    return upper_ascii(payload) == object.module;
}

void validate_object(const ObjectFile& object) {
    if (object.module.empty() || object.exports.empty() || object.code.empty() ||
        object.code.size() > std::numeric_limits<std::uint16_t>::max()) {
        throw ToolError("BAD OBJECT");
    }
    if (is_legacy_placeholder_object(object)) {
        throw ToolError("PLACEHOLDER OBJECT " + object.module);
    }

    std::set<std::string> export_names;
    for (const ObjExport& export_record : object.exports) {
        const std::size_t start = export_record.offset;
        const std::size_t size = export_record.size;
        if (export_record.name.empty() || size == 0 || start >= object.code.size() ||
            size > object.code.size() - start || !export_names.insert(export_record.name).second) {
            throw ToolError("BAD OBJECT");
        }
    }
    for (const ObjReloc& reloc : object.relocs) {
        const std::size_t relocation_width =
            reloc.part == ObjRelocPart::Word ? 2 : 1;
        if (reloc.offset >= object.code.size() ||
            relocation_width > object.code.size() - reloc.offset) {
            throw ToolError("BAD RELOC");
        }
        if (reloc.import) {
            if (reloc.import_index < 0 ||
                static_cast<std::size_t>(reloc.import_index) >= object.imports.size()) {
                throw ToolError("BAD OBJECT");
            }
        } else if (reloc.symbol.empty()) {
            throw ToolError("BAD OBJECT");
        }
    }
    for (const ObjLineRecord& line : object.lines) {
        if (line.line == 0 || line.offset >= object.code.size()) {
            throw ToolError("BAD OBJECT LINE");
        }
    }
}

using ExprValue = std::int64_t;

enum class ActionWordType {
    Byte,
    Int,
    Card,
};

ActionWordType action_literal_type(ExprValue value) {
    if (value < 0) return ActionWordType::Int;
    return value <= 0xFF ? ActionWordType::Byte : ActionWordType::Card;
}

ActionWordType action_mixed_type(ActionWordType lhs, ActionWordType rhs) {
    if (lhs == ActionWordType::Card || rhs == ActionWordType::Card) {
        return ActionWordType::Card;
    }
    if (lhs == ActionWordType::Int || rhs == ActionWordType::Int) {
        return ActionWordType::Int;
    }
    return ActionWordType::Byte;
}

ExprValue normalize_action_word(ExprValue value, ActionWordType type) {
    if (type == ActionWordType::Byte) {
        return static_cast<std::uint8_t>(value);
    }
    const std::uint16_t bits = static_cast<std::uint16_t>(value);
    if (type == ActionWordType::Int) {
        return static_cast<std::int16_t>(bits);
    }
    return bits;
}

std::uint16_t action_word_bits(ExprValue value) {
    return static_cast<std::uint16_t>(value);
}

struct VarSlot {
    std::string name;
    std::string lo_symbol;
    std::string hi_symbol;
    bool is_card = false;
    bool is_signed = false;
    std::uint16_t initial_value = 0;
    std::optional<std::uint16_t> absolute_address;
    // ADDRESS declarations can alias linked storage whose final C64 address is
    // not known until ALINK places the object.  INITIAL declarations for
    // pointer-sized values can likewise contain a linked address.
    std::string bound_address_symbol;
    std::int32_t bound_address_addend = 0;
    std::string initial_address_symbol;
    std::int32_t initial_address_addend = 0;

    VarSlot() = default;
    VarSlot(
        std::string variable_name,
        std::string low_symbol,
        std::string high_symbol,
        bool card,
        bool signed_value = false,
        std::uint16_t initial = 0,
        std::optional<std::uint16_t> address = std::nullopt)
        : name(std::move(variable_name)),
          lo_symbol(std::move(low_symbol)),
          hi_symbol(std::move(high_symbol)),
          is_card(card),
          is_signed(signed_value),
          initial_value(initial),
          absolute_address(address) {}

    bool is_address_bound() const {
        return absolute_address.has_value() || !bound_address_symbol.empty();
    }
};

enum class IndexedElementType {
    Byte,
    Card,
    Int,
    Real,
};

struct IndexedSlot {
    VarSlot pointer;
    IndexedElementType element_type = IndexedElementType::Byte;
    std::uint16_t byte_offset = 0;

    std::size_t element_width() const {
        if (element_type == IndexedElementType::Real) {
            return 4;
        }
        return element_type == IndexedElementType::Byte ? 1 : 2;
    }

    bool element_is_signed() const {
        return element_type == IndexedElementType::Int;
    }

    bool element_is_real() const {
        return element_type == IndexedElementType::Real;
    }
};

IndexedElementType indexed_element_type(std::string_view type_text) {
    const std::string type = upper_ascii(type_text);
    if (type == "BYTE" || type == "CHAR") return IndexedElementType::Byte;
    if (type == "CARD") return IndexedElementType::Card;
    if (type == "INT") return IndexedElementType::Int;
    if (type == "REAL") return IndexedElementType::Real;
    throw ToolError("BAD INDEXED TYPE " + type);
}

ActionWordType indexed_action_word_type(const IndexedSlot& slot) {
    if (slot.element_type == IndexedElementType::Byte) {
        return ActionWordType::Byte;
    }
    if (slot.element_type == IndexedElementType::Int) {
        return ActionWordType::Int;
    }
    if (slot.element_type == IndexedElementType::Card) {
        return ActionWordType::Card;
    }
    throw ToolError("REAL VALUE IN WORD EXPR");
}

struct ArraySlot {
    struct InitialRelocation {
        std::size_t offset = 0;
        std::string symbol;
        std::int32_t addend = 0;
    };

    IndexedSlot indexed;
    std::string data_symbol;
    std::vector<std::uint8_t> initial_data;
    std::vector<InitialRelocation> initial_relocations;
    std::vector<std::string> frame_byte_symbols;
    std::optional<std::uint16_t> absolute_data_address;
    std::string linked_data_address_symbol;
    std::int32_t linked_data_address_addend = 0;
    std::size_t alignment = 1;
};

struct AddressConstantSlot {
    std::string lo_symbol;
    std::string hi_symbol;
    std::string target_symbol;
    std::int32_t addend = 0;
};

struct RelocatableCompilerConstant {
    std::optional<ExprValue> absolute;
    std::string symbol;
    std::int32_t addend = 0;

    bool is_symbolic() const { return !symbol.empty(); }
};

struct RealSlot {
    std::string name;
    std::vector<std::string> byte_symbols;
    std::string pointer_lo_symbol;
    std::string pointer_hi_symbol;
    std::vector<std::uint8_t> initial_value = std::vector<std::uint8_t>(4, 0);
    std::optional<std::uint16_t> absolute_address;
};

struct ExprTempSlot {
    std::string value_lo_symbol;
    std::string value_hi_symbol;
    std::string pointer_lo_symbol;
    std::string pointer_hi_symbol;
};

enum class CallRegister {
    A,
    X,
    Y,
    XY,
    ZeroPage0E,
    ZeroPageE0,
};

struct BuiltinCall {
    std::string helper;
    std::vector<CallRegister> arguments;
    int return_width = 0;
    int carry_low_bit_argument = -1;
};

const std::map<std::string, ExprValue>& builtin_integer_constants() {
    static const std::map<std::string, ExprValue> constants = {
        {"JOY_UP", 0x01},
        {"JOY_DOWN", 0x02},
        {"JOY_LEFT", 0x04},
        {"JOY_RIGHT", 0x08},
        {"JOY_BUTTON1", 0x10},
        {"JOY_BUTTON2", 0x20},
        {"MOUSE_BUTTON1", 0x01},
        {"MOUSE_BUTTON2", 0x02},
        {"SID_TRI", 0x10},
        {"SID_SAW", 0x20},
        {"SID_PULSE", 0x40},
        {"SID_NOISE", 0x80},
        {"SID_LOW", 0x10},
        {"SID_BAND", 0x20},
        {"SID_HIGH", 0x40},
        {"SPR_FRONT", 0},
        {"SPR_BACK", 1},
    };
    return constants;
}

std::optional<BuiltinCall> builtin_call(std::string_view name) {
    static const std::map<std::string, BuiltinCall> calls = {
        {"VICBANK", BuiltinCall{"RT_GFX_VIC_BANK", {CallRegister::A}, 0}},
        {"BGCOLOR", BuiltinCall{"RT_GFX_BGCOLOR", {CallRegister::A}, 0}},
        {"BORDERCOLOR", BuiltinCall{"RT_GFX_BORDERCOLOR", {CallRegister::A}, 0}},
        {"SCREENBASE", BuiltinCall{"RT_GFX_SCREEN_BASE", {CallRegister::XY}, 0}},
        {"BITMAPBASE", BuiltinCall{"RT_GFX_BITMAP_BASE", {CallRegister::XY}, 0}},
        {"SCREENCELL", BuiltinCall{"RT_GFX_SCREEN_CELL", {CallRegister::A, CallRegister::X, CallRegister::Y}, 0}},
        {"COLORCELL", BuiltinCall{"RT_GFX_COLOR_CELL", {CallRegister::A, CallRegister::X, CallRegister::Y}, 0}},
        {"SCREENCOPY", BuiltinCall{"RT_GFX_SCREEN_COPY", {CallRegister::XY}, 0}},
        {"COLORCOPY", BuiltinCall{"RT_GFX_COLOR_COPY", {CallRegister::XY}, 0}},
        {"BITMAPFILL", BuiltinCall{"RT_GFX_BITMAP_FILL", {CallRegister::A}, 0}},
        {"BITMAPCOPY", BuiltinCall{"RT_GFX_BITMAP_COPY", {CallRegister::XY}, 0}},
        {"BITMAPON", BuiltinCall{"RT_GFX_BITMAP_ON", {}, 0}},
        {"BITMAPOFF", BuiltinCall{"RT_GFX_BITMAP_OFF", {}, 0}},
        {"MBITMAPON", BuiltinCall{"RT_GFX_MBITMAP_ON", {}, 0}},
        {"MBITMAPOFF", BuiltinCall{"RT_GFX_MBITMAP_OFF", {}, 0}},
        {"JOY", BuiltinCall{"RT_JOY", {CallRegister::A}, 1}},
        {"JOYSEEN", BuiltinCall{"RT_JP", {CallRegister::A}, 1}},
        {"JOYBTN1", BuiltinCall{"RT_JB1", {CallRegister::A}, 1}},
        {"JOYBTN2", BuiltinCall{"RT_JB2", {CallRegister::A}, 1}},
        {"MOUSEPOLL", BuiltinCall{"RT_MP", {CallRegister::A}, 1}},
        {"MOUSESEEN", BuiltinCall{"RT_MSEEN", {}, 1}},
        {"MOUSEX", BuiltinCall{"RT_MX", {}, 1}},
        {"MOUSEY", BuiltinCall{"RT_MY", {}, 1}},
        {"MOUSEBTN", BuiltinCall{"RT_MB", {}, 1}},
        {"MOUSEBTN1", BuiltinCall{"RT_MB1", {}, 1}},
        {"MOUSEBTN2", BuiltinCall{"RT_MB2", {}, 1}},
        {"SPRITEHIT", BuiltinCall{"RT_SPRITE_HIT", {}, 1}},
        {"SPRITEHITBG", BuiltinCall{"RT_SPRITE_HIT_BG", {}, 1}},
        {"SIDOSC3", BuiltinCall{"RT_SID_OSC3", {}, 1}},
        {"SIDENV3", BuiltinCall{"RT_SID_ENV3", {}, 1}},
        {"SPRITEON", BuiltinCall{"RT_SPRITE_ON", {CallRegister::A}, 0}},
        {"SPRITEOFF", BuiltinCall{"RT_SPRITE_OFF", {CallRegister::A}, 0}},
        {"SPRITEPOS", BuiltinCall{"RT_SPRITE_POS", {CallRegister::A, CallRegister::X, CallRegister::Y}, 0, 1}},
        {"SPRITEPTR", BuiltinCall{"RT_SPRITE_PTR", {CallRegister::X, CallRegister::A}, 0}},
        {"SPRITEDATA", BuiltinCall{"RT_SPRITE_DATA", {CallRegister::A, CallRegister::XY}, 0}},
        {"SPRITECOLOR", BuiltinCall{"RT_SPRITE_COLOR", {CallRegister::X, CallRegister::A}, 0}},
        {"SPRITEMC", BuiltinCall{"RT_SPRITE_MC", {CallRegister::A, CallRegister::Y}, 0}},
        {"SPRITEXEXP", BuiltinCall{"RT_SPRITE_XEXP", {CallRegister::A, CallRegister::Y}, 0}},
        {"SPRITEYEXP", BuiltinCall{"RT_SPRITE_YEXP", {CallRegister::A, CallRegister::Y}, 0}},
        {"SPRITEPRIO", BuiltinCall{"RT_SPRITE_PRIO", {CallRegister::A, CallRegister::Y}, 0}},
        {"SETSPRITEMC", BuiltinCall{"RT_SPRITE_SET_MC", {CallRegister::A, CallRegister::X}, 0}},
        {"SIDFREQ", BuiltinCall{"RT_SID_FREQ", {CallRegister::A, CallRegister::XY}, 0}},
        {"SIDPULSE", BuiltinCall{"RT_SID_PULSE", {CallRegister::A, CallRegister::XY}, 0}},
        {"SIDWAVE", BuiltinCall{"RT_SID_WAVE", {CallRegister::A, CallRegister::Y}, 0}},
        {"SIDAD", BuiltinCall{"RT_SID_AD", {CallRegister::A, CallRegister::Y}, 0}},
        {"SIDSR", BuiltinCall{"RT_SID_SR", {CallRegister::A, CallRegister::Y}, 0}},
        {"SIDON", BuiltinCall{"RT_SID_ON", {CallRegister::A}, 0}},
        {"SIDOFF", BuiltinCall{"RT_SID_OFF", {CallRegister::A}, 0}},
        {"SIDVOL", BuiltinCall{"RT_SID_VOL", {CallRegister::A}, 0}},
        {"SIDCUTOFF", BuiltinCall{"RT_SID_CUTOFF", {CallRegister::XY}, 0}},
        {"SIDRES", BuiltinCall{"RT_SID_RES", {CallRegister::A}, 0}},
        {"SIDMODE", BuiltinCall{"RT_SID_MODE", {CallRegister::A}, 0}},
        {"SIDROUTE", BuiltinCall{"RT_SID_ROUTE", {CallRegister::A}, 0}},
        {"SIDRST", BuiltinCall{"RT_SID_RST", {}, 0}},
        {"REUPEEK8", BuiltinCall{"RT_REU_PEEK8", {CallRegister::A, CallRegister::XY}, 1}},
        {"REUPEEK16", BuiltinCall{"RT_REU_PEEK16", {CallRegister::A, CallRegister::XY}, 2}},
        {"REUPOKE8", BuiltinCall{
            "RT_REU_POKE8",
            {CallRegister::A, CallRegister::XY, CallRegister::ZeroPage0E},
            0,
        }},
        {"REUPOKE16", BuiltinCall{
            "RT_REU_POKE16",
            {CallRegister::A, CallRegister::XY, CallRegister::ZeroPage0E},
            0,
        }},
        {"DBFCREATE", BuiltinCall{"RT_DBF_CREATE", {CallRegister::XY}, 1}},
        {"DBFOPEN", BuiltinCall{"RT_DBF_OPEN", {CallRegister::XY}, 1}},
        {"DBFCLOSE", BuiltinCall{"RT_DBF_CLOSE", {CallRegister::A}, 0}},
        {"DBFGO", BuiltinCall{"RT_DBF_GO", {CallRegister::A, CallRegister::Y}, 1}},
        {"DBFFIELDCOUNT", BuiltinCall{"RT_DBF_FIELDCOUNT", {CallRegister::A}, 1}},
        {"DBFFIELDLEN", BuiltinCall{
            "RT_DBF_FIELDLEN",
            {CallRegister::A, CallRegister::Y},
            1,
        }},
        {"DBFREADBYTE", BuiltinCall{
            "RT_DBF_READBYTE",
            {CallRegister::A, CallRegister::Y},
            1,
        }},
        {"DBFREADFIELDBYTE", BuiltinCall{
            "RT_DBF_READFIELDBYTE",
            {CallRegister::A, CallRegister::X, CallRegister::Y},
            1,
        }},
        {"DBFWRITEFIELDBYTE", BuiltinCall{
            "RT_DBF_WRITEFIELDBYTE",
            {
                CallRegister::A,
                CallRegister::X,
                CallRegister::Y,
                CallRegister::ZeroPageE0,
            },
            1,
        }},
        {"DBFWRITEBYTE", BuiltinCall{
            "RT_DBF_WRITEBYTE",
            {CallRegister::A, CallRegister::X, CallRegister::Y},
            1,
        }},
        {"DBFAPPEND", BuiltinCall{"RT_DBF_APPEND", {CallRegister::A}, 1}},
        {"DBFPACK", BuiltinCall{"RT_DBF_PACK", {CallRegister::A}, 1}},
        {"DBFSAVE", BuiltinCall{"RT_DBF_SAVE", {CallRegister::A}, 1}},
        {"DBFDELETE", BuiltinCall{"RT_DBF_DELETE", {CallRegister::A}, 1}},
        {"DBFUNDELETE", BuiltinCall{"RT_DBF_UNDELETE", {CallRegister::A}, 1}},
        {"DBFDELETED", BuiltinCall{"RT_DBF_DELETED", {CallRegister::A}, 1}},
        {"DBFHEADERLEN", BuiltinCall{"RT_DBF_HEADERLEN", {CallRegister::A}, 1}},
        {"DBFRECORDLEN", BuiltinCall{"RT_DBF_RECORDLEN", {CallRegister::A}, 1}},
        {"DBFTOTALRECS", BuiltinCall{"RT_DBF_TOTALRECS", {CallRegister::A}, 1}},
        {"DBFCURRRECNO", BuiltinCall{"RT_DBF_CURRRECNO", {CallRegister::A}, 1}},
    };
    auto found = calls.find(upper_ascii(name));
    if (found == calls.end()) {
        return std::nullopt;
    }
    return found->second;
}

struct ExprNode {
    enum class Kind {
        Constant,
        StringLiteral,
        Variable,
        Call,
        AddressOf,
        Dereference,
        Negate,
        Add,
        Subtract,
        Multiply,
        Divide,
        Modulo,
        BitAnd,
        BitOr,
        BitXor,
        ShiftLeft,
        ShiftRight,
    };

    Kind kind = Kind::Constant;
    ExprValue value = 0;
    std::string name;
    std::vector<std::string> arguments;
    std::size_t left = 0;
    std::size_t right = 0;
};

struct ParsedExpr {
    std::vector<ExprNode> nodes;
    std::size_t root = 0;
};

class WordExprParser {
public:
    explicit WordExprParser(std::string_view text) : text_(text) {}

    ParsedExpr parse() {
        const std::size_t root = parse_expr();
        skip_ws();
        if (pos_ != text_.size()) {
            throw ToolError("BAD EXPR");
        }
        return ParsedExpr{std::move(nodes_), root};
    }

private:
    void skip_ws() {
        while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
    }

    std::size_t add_node(ExprNode node) {
        nodes_.push_back(std::move(node));
        return nodes_.size() - 1;
    }

    std::size_t add_binary(ExprNode::Kind kind, std::size_t left, std::size_t right) {
        ExprNode node;
        node.kind = kind;
        node.left = left;
        node.right = right;
        return add_node(std::move(node));
    }

    std::size_t parse_expr() {
        return parse_bit_xor();
    }

    bool match_word(std::string_view word) {
        skip_ws();
        if (pos_ + word.size() > text_.size()) return false;
        for (std::size_t i = 0; i < word.size(); ++i) {
            if (std::toupper(static_cast<unsigned char>(text_[pos_ + i])) !=
                std::toupper(static_cast<unsigned char>(word[i]))) {
                return false;
            }
        }
        const std::size_t end = pos_ + word.size();
        if ((pos_ > 0 &&
             (std::isalnum(static_cast<unsigned char>(text_[pos_ - 1])) ||
              text_[pos_ - 1] == '_')) ||
            (end < text_.size() &&
             (std::isalnum(static_cast<unsigned char>(text_[end])) ||
              text_[end] == '_'))) {
            return false;
        }
        pos_ = end;
        return true;
    }

    std::size_t parse_bit_xor() {
        std::size_t value = parse_bit_or();
        while (true) {
            skip_ws();
            if (pos_ < text_.size() && text_[pos_] == '!' &&
                (pos_ + 1 >= text_.size() || text_[pos_ + 1] != '=')) {
                ++pos_;
            } else if (!match_word("XOR")) {
                return value;
            }
            value = add_binary(ExprNode::Kind::BitXor, value, parse_bit_or());
        }
    }

    std::size_t parse_bit_or() {
        std::size_t value = parse_bit_and();
        while (true) {
            skip_ws();
            if (pos_ >= text_.size() || text_[pos_] != '%') return value;
            ++pos_;
            value = add_binary(ExprNode::Kind::BitOr, value, parse_bit_and());
        }
    }

    std::size_t parse_bit_and() {
        std::size_t value = parse_additive();
        while (true) {
            skip_ws();
            if (pos_ >= text_.size() || text_[pos_] != '&') return value;
            ++pos_;
            value = add_binary(ExprNode::Kind::BitAnd, value, parse_additive());
        }
    }

    std::size_t parse_additive() {
        std::size_t value = parse_term();
        while (true) {
            skip_ws();
            if (pos_ >= text_.size() || (text_[pos_] != '+' && text_[pos_] != '-')) {
                return value;
            }
            const char op = text_[pos_++];
            const std::size_t rhs = parse_term();
            value = add_binary(op == '+' ? ExprNode::Kind::Add : ExprNode::Kind::Subtract, value, rhs);
        }
    }

    std::size_t parse_term() {
        std::size_t value = parse_factor();
        while (true) {
            skip_ws();
            if (pos_ < text_.size() && (text_[pos_] == '*' || text_[pos_] == '/')) {
                const char op = text_[pos_++];
                const std::size_t rhs = parse_factor();
                value = add_binary(
                    op == '*' ? ExprNode::Kind::Multiply : ExprNode::Kind::Divide,
                    value,
                    rhs);
                continue;
            }
            ExprNode::Kind kind;
            if (match_word("MOD")) {
                kind = ExprNode::Kind::Modulo;
            } else if (match_word("LSH")) {
                kind = ExprNode::Kind::ShiftLeft;
            } else if (match_word("RSH")) {
                kind = ExprNode::Kind::ShiftRight;
            } else {
                return value;
            }
            value = add_binary(kind, value, parse_factor());
        }
    }

    std::size_t parse_factor() {
        skip_ws();
        if (pos_ >= text_.size()) {
            throw ToolError("BAD EXPR");
        }
        if (text_[pos_] == '(') {
            ++pos_;
            const std::size_t value = parse_expr();
            skip_ws();
            if (pos_ >= text_.size() || text_[pos_] != ')') {
                throw ToolError("BAD EXPR");
            }
            ++pos_;
            return value;
        }
        if (text_[pos_] == '+') {
            ++pos_;
            return parse_factor();
        }
        if (text_[pos_] == '-') {
            ++pos_;
            ExprNode node;
            node.kind = ExprNode::Kind::Negate;
            node.left = parse_factor();
            return add_node(std::move(node));
        }
        if (text_[pos_] == '@') {
            ++pos_;
            ExprNode node;
            node.kind = ExprNode::Kind::AddressOf;
            node.left = parse_factor();
            return add_node(std::move(node));
        }
        if (text_[pos_] == '"') {
            ++pos_;
            ExprNode node;
            node.kind = ExprNode::Kind::StringLiteral;
            bool escaped = false;
            while (pos_ < text_.size()) {
                const char ch = text_[pos_++];
                if (escaped) {
                    if (ch == 'n') {
                        node.name.push_back('\n');
                    } else if (ch == 'r') {
                        node.name.push_back('\r');
                    } else {
                        node.name.push_back(ch);
                    }
                    escaped = false;
                } else if (ch == '\\') {
                    escaped = true;
                } else if (ch == '"') {
                    if (pos_ < text_.size() && text_[pos_] == '"') {
                        node.name.push_back('"');
                        ++pos_;
                    } else {
                        return add_node(std::move(node));
                    }
                } else {
                    node.name.push_back(ch);
                }
            }
            throw ToolError("BAD STRING");
        }
        if (text_[pos_] == '\'') {
            ++pos_;
            if (pos_ >= text_.size()) {
                throw ToolError("BAD CHAR");
            }
            unsigned char value = static_cast<unsigned char>(text_[pos_++]);
            if (value == '\\' && pos_ < text_.size()) {
                const char escaped = text_[pos_++];
                value = static_cast<unsigned char>(
                    escaped == 'n' ? '\n' : escaped == 'r' ? '\r' : escaped);
            }
            if (pos_ < text_.size() && text_[pos_] == '\'') {
                ++pos_;
            }
            ExprNode node;
            node.kind = ExprNode::Kind::Constant;
            node.value = value;
            return add_node(std::move(node));
        }

        int base = 10;
        bool explicit_base = false;
        if (text_[pos_] == '$') {
            base = 16;
            explicit_base = true;
            ++pos_;
        } else if (text_[pos_] == '%') {
            base = 2;
            explicit_base = true;
            ++pos_;
        } else if (pos_ + 1 < text_.size() && text_[pos_] == '0' &&
                   (text_[pos_ + 1] == 'x' || text_[pos_ + 1] == 'X')) {
            base = 16;
            explicit_base = true;
            pos_ += 2;
        }
        const std::size_t number_start = pos_;
        ExprValue number = 0;
        while (pos_ < text_.size()) {
            const unsigned char ch = static_cast<unsigned char>(text_[pos_]);
            int digit = -1;
            if (std::isdigit(ch)) {
                digit = ch - '0';
            } else if (std::isalpha(ch)) {
                digit = std::toupper(ch) - 'A' + 10;
            }
            if (digit < 0 || digit >= base) {
                break;
            }
            if (number > (std::numeric_limits<ExprValue>::max() - digit) / base) {
                throw ToolError("EXPR RANGE");
            }
            number = number * base + digit;
            ++pos_;
        }
        if (pos_ != number_start) {
            ExprNode node;
            node.kind = ExprNode::Kind::Constant;
            node.value = number;
            return add_node(std::move(node));
        }
        if (explicit_base || pos_ >= text_.size()) {
            throw ToolError("BAD EXPR");
        }
        if (std::isalpha(static_cast<unsigned char>(text_[pos_])) || text_[pos_] == '_') {
            std::string name;
            while (pos_ < text_.size() &&
                   (std::isalnum(static_cast<unsigned char>(text_[pos_])) || text_[pos_] == '_')) {
                name.push_back(text_[pos_++]);
            }
            while (pos_ < text_.size() && text_[pos_] == '.') {
                name.push_back(text_[pos_++]);
                if (pos_ >= text_.size() ||
                    (!std::isalpha(static_cast<unsigned char>(text_[pos_])) &&
                     text_[pos_] != '_')) {
                    throw ToolError("BAD FIELD EXPR");
                }
                while (pos_ < text_.size() &&
                       (std::isalnum(static_cast<unsigned char>(text_[pos_])) ||
                        text_[pos_] == '_')) {
                    name.push_back(text_[pos_++]);
                }
            }
            ExprNode node;
            node.name = upper_ascii(name);
            skip_ws();
            if (pos_ < text_.size() && text_[pos_] == '(') {
                node.kind = ExprNode::Kind::Call;
                const std::size_t close = find_call_close(text_, pos_);
                node.arguments = split_call_arguments(
                    text_.substr(pos_ + 1, close - pos_ - 1));
                pos_ = close + 1;
                return add_node(std::move(node));
            }
            if (pos_ < text_.size() && text_[pos_] == '^') {
                ++pos_;
                node.kind = ExprNode::Kind::Dereference;
                return add_node(std::move(node));
            }
            node.kind = ExprNode::Kind::Variable;
            return add_node(std::move(node));
        }
        throw ToolError("BAD EXPR");
    }

    std::string_view text_;
    std::vector<ExprNode> nodes_;
    std::size_t pos_ = 0;
};

std::optional<ExprValue> evaluate_expr_node(
    const ParsedExpr& expr,
    std::size_t index,
    const std::map<std::string, ExprValue>& vars) {
    const ExprNode& node = expr.nodes.at(index);
    if (node.kind == ExprNode::Kind::Constant) {
        return node.value;
    }
    if (node.kind == ExprNode::Kind::Variable) {
        auto found = vars.find(node.name);
        if (found == vars.end()) {
            return std::nullopt;
        }
        return found->second;
    }
    if (node.kind == ExprNode::Kind::Call ||
        node.kind == ExprNode::Kind::StringLiteral ||
        node.kind == ExprNode::Kind::AddressOf ||
        node.kind == ExprNode::Kind::Dereference) {
        return std::nullopt;
    }

    const auto lhs = evaluate_expr_node(expr, node.left, vars);
    if (node.kind == ExprNode::Kind::Negate) {
        if (!lhs) {
            return std::nullopt;
        }
        if (*lhs == std::numeric_limits<ExprValue>::min()) {
            throw ToolError("EXPR RANGE");
        }
        return -*lhs;
    }
    const auto rhs = evaluate_expr_node(expr, node.right, vars);
    if (!lhs || !rhs) {
        return std::nullopt;
    }

    if (node.kind == ExprNode::Kind::Add) {
        if ((*rhs > 0 && *lhs > std::numeric_limits<ExprValue>::max() - *rhs) ||
            (*rhs < 0 && *lhs < std::numeric_limits<ExprValue>::min() - *rhs)) {
            throw ToolError("EXPR RANGE");
        }
        return *lhs + *rhs;
    }
    if (node.kind == ExprNode::Kind::Subtract) {
        if ((*rhs < 0 && *lhs > std::numeric_limits<ExprValue>::max() + *rhs) ||
            (*rhs > 0 && *lhs < std::numeric_limits<ExprValue>::min() + *rhs)) {
            throw ToolError("EXPR RANGE");
        }
        return *lhs - *rhs;
    }
    if (node.kind == ExprNode::Kind::Multiply) {
        const __int128 product = static_cast<__int128>(*lhs) * static_cast<__int128>(*rhs);
        if (product > std::numeric_limits<ExprValue>::max() ||
            product < std::numeric_limits<ExprValue>::min()) {
            throw ToolError("EXPR RANGE");
        }
        return static_cast<ExprValue>(product);
    }
    if (node.kind == ExprNode::Kind::BitAnd) return *lhs & *rhs;
    if (node.kind == ExprNode::Kind::BitOr) return *lhs | *rhs;
    if (node.kind == ExprNode::Kind::BitXor) return *lhs ^ *rhs;
    if (node.kind == ExprNode::Kind::ShiftLeft ||
        node.kind == ExprNode::Kind::ShiftRight) {
        if (*rhs < 0 || *rhs >= 63) throw ToolError("SHIFT RANGE");
        const auto unsigned_lhs = static_cast<std::uint64_t>(*lhs);
        return static_cast<ExprValue>(
            node.kind == ExprNode::Kind::ShiftLeft
                ? unsigned_lhs << static_cast<unsigned>(*rhs)
                : unsigned_lhs >> static_cast<unsigned>(*rhs));
    }
    if (*rhs == 0) {
        throw ToolError("DIV ZERO");
    }
    if (*lhs == std::numeric_limits<ExprValue>::min() && *rhs == -1) {
        throw ToolError("EXPR RANGE");
    }
    return node.kind == ExprNode::Kind::Modulo ? *lhs % *rhs : *lhs / *rhs;
}

ExprValue eval_const_expr(std::string_view text, const std::map<std::string, ExprValue>& vars) {
    const ParsedExpr expr = WordExprParser(text).parse();
    auto value = evaluate_expr_node(expr, expr.root, vars);
    if (!value) {
        throw ToolError("UNKNOWN VAR");
    }
    return *value;
}

std::optional<ExprValue> try_eval_const_expr(
    std::string_view expr,
    const std::map<std::string, ExprValue>& vars) {
    try {
        return eval_const_expr(expr, vars);
    } catch (const ToolError&) {
        return std::nullopt;
    }
}

struct RealExprNode {
    enum class Kind {
        Constant,
        Variable,
        Call,
        Dereference,
        Negate,
        Add,
        Subtract,
        Multiply,
        Divide,
        Cast,
        Absolute,
        SquareRoot,
        Truncate,
        Floor,
        Ceiling,
        Round,
        Fraction,
        DegreesToRadians,
        RadiansToDegrees,
        Modulus,
        Hypotenuse,
        Minimum,
        Maximum,
    };

    Kind kind = Kind::Constant;
    double value = 0.0;
    std::string name;
    std::vector<std::string> arguments;
    std::size_t left = 0;
    std::size_t right = 0;
};

struct ParsedRealExpr {
    std::vector<RealExprNode> nodes;
    std::size_t root = 0;
};

class RealExprParser {
public:
    explicit RealExprParser(std::string_view text) : text_(text) {}

    ParsedRealExpr parse() {
        const std::size_t root = parse_expr();
        skip_ws();
        if (pos_ != text_.size()) {
            throw ToolError("BAD REAL EXPR");
        }
        return ParsedRealExpr{std::move(nodes_), root};
    }

private:
    void skip_ws() {
        while (pos_ < text_.size() &&
               std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
    }

    std::size_t add_node(RealExprNode node) {
        nodes_.push_back(std::move(node));
        return nodes_.size() - 1;
    }

    std::size_t add_binary(
        RealExprNode::Kind kind,
        std::size_t left,
        std::size_t right) {
        RealExprNode node;
        node.kind = kind;
        node.left = left;
        node.right = right;
        return add_node(std::move(node));
    }

    std::size_t parse_expr() {
        std::size_t value = parse_term();
        while (true) {
            skip_ws();
            if (pos_ >= text_.size() || (text_[pos_] != '+' && text_[pos_] != '-')) {
                return value;
            }
            const char op = text_[pos_++];
            const std::size_t rhs = parse_term();
            value = add_binary(
                op == '+' ? RealExprNode::Kind::Add : RealExprNode::Kind::Subtract,
                value,
                rhs);
        }
    }

    std::size_t parse_term() {
        std::size_t value = parse_factor();
        while (true) {
            skip_ws();
            if (pos_ >= text_.size() || (text_[pos_] != '*' && text_[pos_] != '/')) {
                return value;
            }
            const char op = text_[pos_++];
            const std::size_t rhs = parse_factor();
            value = add_binary(
                op == '*' ? RealExprNode::Kind::Multiply : RealExprNode::Kind::Divide,
                value,
                rhs);
        }
    }

    std::size_t parse_factor() {
        skip_ws();
        if (pos_ >= text_.size()) {
            throw ToolError("BAD REAL EXPR");
        }
        if (text_[pos_] == '(') {
            ++pos_;
            const std::size_t value = parse_expr();
            skip_ws();
            if (pos_ >= text_.size() || text_[pos_] != ')') {
                throw ToolError("BAD REAL EXPR");
            }
            ++pos_;
            return value;
        }
        if (text_[pos_] == '+') {
            ++pos_;
            return parse_factor();
        }
        if (text_[pos_] == '-') {
            ++pos_;
            RealExprNode node;
            node.kind = RealExprNode::Kind::Negate;
            node.left = parse_factor();
            return add_node(std::move(node));
        }
        if (std::isdigit(static_cast<unsigned char>(text_[pos_])) || text_[pos_] == '.' ||
            text_[pos_] == '$' || text_[pos_] == '%') {
            return parse_number();
        }
        if (std::isalpha(static_cast<unsigned char>(text_[pos_])) || text_[pos_] == '_') {
            return parse_name_or_call();
        }
        throw ToolError("BAD REAL EXPR");
    }

    std::size_t parse_number() {
        const std::size_t start = pos_;
        int base = 10;
        if (text_[pos_] == '$') {
            base = 16;
            ++pos_;
        } else if (text_[pos_] == '%') {
            base = 2;
            ++pos_;
        } else if (pos_ + 1 < text_.size() && text_[pos_] == '0' &&
                   (text_[pos_ + 1] == 'x' || text_[pos_ + 1] == 'X')) {
            base = 16;
            pos_ += 2;
        }
        if (base != 10) {
            const std::size_t digits_start = pos_;
            std::uint64_t value = 0;
            while (pos_ < text_.size()) {
                const unsigned char ch = static_cast<unsigned char>(text_[pos_]);
                int digit = -1;
                if (std::isdigit(ch)) {
                    digit = ch - '0';
                } else if (std::isalpha(ch)) {
                    digit = std::toupper(ch) - 'A' + 10;
                }
                if (digit < 0 || digit >= base) {
                    break;
                }
                if (value > (std::numeric_limits<std::uint64_t>::max() -
                             static_cast<std::uint64_t>(digit)) /
                                static_cast<std::uint64_t>(base)) {
                    throw ToolError("REAL EXPR RANGE");
                }
                value = value * static_cast<std::uint64_t>(base) +
                        static_cast<std::uint64_t>(digit);
                ++pos_;
            }
            if (pos_ == digits_start) {
                throw ToolError("BAD REAL EXPR");
            }
            RealExprNode node;
            node.kind = RealExprNode::Kind::Constant;
            node.value = static_cast<double>(value);
            return add_node(std::move(node));
        }

        const std::string remaining(text_.substr(start));
        char* end = nullptr;
        const double value = std::strtod(remaining.c_str(), &end);
        const std::size_t consumed = static_cast<std::size_t>(end - remaining.c_str());
        if (consumed == 0) {
            throw ToolError("BAD REAL EXPR");
        }
        pos_ = start + consumed;
        RealExprNode node;
        node.kind = RealExprNode::Kind::Constant;
        node.value = value;
        return add_node(std::move(node));
    }

    std::size_t parse_name_or_call() {
        std::string name;
        while (pos_ < text_.size() &&
               (std::isalnum(static_cast<unsigned char>(text_[pos_])) || text_[pos_] == '_')) {
            name.push_back(text_[pos_++]);
        }
        while (pos_ < text_.size() && text_[pos_] == '.') {
            name.push_back(text_[pos_++]);
            if (pos_ >= text_.size() ||
                (!std::isalpha(static_cast<unsigned char>(text_[pos_])) &&
                 text_[pos_] != '_')) {
                throw ToolError("BAD REAL FIELD EXPR");
            }
            while (pos_ < text_.size() &&
                   (std::isalnum(static_cast<unsigned char>(text_[pos_])) ||
                    text_[pos_] == '_')) {
                name.push_back(text_[pos_++]);
            }
        }
        name = upper_ascii(name);
        skip_ws();
        if ((pos_ >= text_.size() || text_[pos_] != '(') &&
            (name == "NAN" || name == "INF" || name == "INFINITY")) {
            RealExprNode node;
            node.kind = RealExprNode::Kind::Constant;
            node.value = name == "NAN"
                ? std::numeric_limits<double>::quiet_NaN()
                : std::numeric_limits<double>::infinity();
            return add_node(std::move(node));
        }
        if (pos_ >= text_.size() || text_[pos_] != '(') {
            RealExprNode node;
            if (pos_ < text_.size() && text_[pos_] == '^') {
                ++pos_;
                node.kind = RealExprNode::Kind::Dereference;
            } else {
                node.kind = RealExprNode::Kind::Variable;
            }
            node.name = std::move(name);
            return add_node(std::move(node));
        }

        if (name != "REAL" && name != "FABS" && name != "FSQRT" &&
            name != "FTRUNC" && name != "FFLOOR" && name != "FCEIL" &&
            name != "FROUND" && name != "FFRAC" && name != "FMOD" &&
            name != "FHYPOT" && name != "FMIN" && name != "FMAX" &&
            name != "DEGTORAD" && name != "RADTODEG") {
            RealExprNode node;
            node.kind = RealExprNode::Kind::Call;
            node.name = std::move(name);
            const std::size_t close = find_call_close(text_, pos_);
            node.arguments = split_call_arguments(
                text_.substr(pos_ + 1, close - pos_ - 1));
            pos_ = close + 1;
            return add_node(std::move(node));
        }

        ++pos_;
        const std::size_t argument = parse_expr();
        skip_ws();
        std::optional<std::size_t> second_argument;
        if (name == "FMOD" || name == "FHYPOT" || name == "FMIN" ||
            name == "FMAX") {
            if (pos_ >= text_.size() || text_[pos_] != ',') {
                throw ToolError("BAD REAL CALL");
            }
            ++pos_;
            second_argument = parse_expr();
            skip_ws();
        }
        if (pos_ >= text_.size() || text_[pos_] != ')') {
            throw ToolError("BAD REAL CALL");
        }
        ++pos_;
        RealExprNode node;
        if (name == "REAL") {
            node.kind = RealExprNode::Kind::Cast;
        } else if (name == "FABS") {
            node.kind = RealExprNode::Kind::Absolute;
        } else if (name == "FSQRT") {
            node.kind = RealExprNode::Kind::SquareRoot;
        } else if (name == "FTRUNC") {
            node.kind = RealExprNode::Kind::Truncate;
        } else if (name == "FFLOOR") {
            node.kind = RealExprNode::Kind::Floor;
        } else if (name == "FCEIL") {
            node.kind = RealExprNode::Kind::Ceiling;
        } else if (name == "FROUND") {
            node.kind = RealExprNode::Kind::Round;
        } else if (name == "FFRAC") {
            node.kind = RealExprNode::Kind::Fraction;
        } else if (name == "DEGTORAD") {
            node.kind = RealExprNode::Kind::DegreesToRadians;
        } else if (name == "RADTODEG") {
            node.kind = RealExprNode::Kind::RadiansToDegrees;
        } else if (name == "FMOD") {
            node.kind = RealExprNode::Kind::Modulus;
        } else if (name == "FHYPOT") {
            node.kind = RealExprNode::Kind::Hypotenuse;
        } else if (name == "FMIN") {
            node.kind = RealExprNode::Kind::Minimum;
        } else if (name == "FMAX") {
            node.kind = RealExprNode::Kind::Maximum;
        }
        node.left = argument;
        if (second_argument) {
            node.right = *second_argument;
        }
        return add_node(std::move(node));
    }

    std::string_view text_;
    std::size_t pos_ = 0;
    std::vector<RealExprNode> nodes_;
};

std::optional<double> evaluate_real_expr_node(
    const ParsedRealExpr& expr,
    std::size_t index,
    const std::map<std::string, double>& constants) {
    const RealExprNode& node = expr.nodes.at(index);
    if (node.kind == RealExprNode::Kind::Constant) {
        return static_cast<double>(static_cast<float>(node.value));
    }
    if (node.kind == RealExprNode::Kind::Variable) {
        auto found = constants.find(node.name);
        if (found == constants.end()) {
            return std::nullopt;
        }
        return static_cast<double>(static_cast<float>(found->second));
    }
    if (node.kind == RealExprNode::Kind::Call ||
        node.kind == RealExprNode::Kind::Dereference) {
        return std::nullopt;
    }
    auto lhs = evaluate_real_expr_node(expr, node.left, constants);
    if (!lhs) {
        return std::nullopt;
    }
    if (node.kind == RealExprNode::Kind::Negate) {
        return static_cast<double>(-static_cast<float>(*lhs));
    }
    if (node.kind == RealExprNode::Kind::Cast) {
        return static_cast<double>(static_cast<float>(*lhs));
    }
    if (node.kind == RealExprNode::Kind::Absolute) {
        return static_cast<double>(std::fabs(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::SquareRoot) {
        return static_cast<double>(std::sqrt(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::Truncate) {
        return static_cast<double>(std::trunc(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::Floor) {
        return static_cast<double>(std::floor(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::Ceiling) {
        return static_cast<double>(std::ceil(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::Round) {
        return static_cast<double>(std::round(static_cast<float>(*lhs)));
    }
    if (node.kind == RealExprNode::Kind::Fraction) {
        const float value = static_cast<float>(*lhs);
        return static_cast<double>(static_cast<float>(value - std::trunc(value)));
    }
    if (node.kind == RealExprNode::Kind::DegreesToRadians) {
        constexpr float factor = 0x1.1df46ap-6F;
        return static_cast<double>(static_cast<float>(*lhs) * factor);
    }
    if (node.kind == RealExprNode::Kind::RadiansToDegrees) {
        constexpr float factor = 0x1.ca5dcp+5F;
        return static_cast<double>(static_cast<float>(*lhs) * factor);
    }
    auto rhs = evaluate_real_expr_node(expr, node.right, constants);
    if (!rhs) {
        return std::nullopt;
    }
    const float left = static_cast<float>(*lhs);
    const float right = static_cast<float>(*rhs);
    if (node.kind == RealExprNode::Kind::Add) {
        return static_cast<double>(left + right);
    }
    if (node.kind == RealExprNode::Kind::Subtract) {
        return static_cast<double>(left - right);
    }
    if (node.kind == RealExprNode::Kind::Multiply) {
        return static_cast<double>(left * right);
    }
    if (node.kind == RealExprNode::Kind::Modulus) {
        if (std::isinf(right) && std::isfinite(left)) {
            return static_cast<double>(left);
        }
        const float quotient = left / right;
        const float truncated = std::trunc(quotient);
        const float product = truncated * right;
        return static_cast<double>(left - product);
    }
    if (node.kind == RealExprNode::Kind::Hypotenuse) {
        const float left_abs = std::fabs(left);
        const float right_abs = std::fabs(right);
        const float largest = std::isnan(left_abs)
            ? right_abs
            : ((std::isnan(right_abs) || left_abs >= right_abs) ? left_abs : right_abs);
        const float smallest = std::isnan(left_abs)
            ? right_abs
            : ((std::isnan(right_abs) || left_abs <= right_abs) ? left_abs : right_abs);
        if (std::isinf(largest) || largest == 0.0F) {
            return static_cast<double>(largest);
        }
        const float ratio = smallest / largest;
        const float square = ratio * ratio;
        const float total = 1.0F + square;
        const float root = std::sqrt(total);
        return static_cast<double>(largest * root);
    }
    // Match the selected-operand semantics of the shared 6502 helpers.
    if (node.kind == RealExprNode::Kind::Minimum) {
        if (std::isnan(left)) {
            return static_cast<double>(right);
        }
        if (std::isnan(right) || left <= right) {
            return static_cast<double>(left);
        }
        return static_cast<double>(right);
    }
    if (node.kind == RealExprNode::Kind::Maximum) {
        if (std::isnan(left)) {
            return static_cast<double>(right);
        }
        if (std::isnan(right) || left >= right) {
            return static_cast<double>(left);
        }
        return static_cast<double>(right);
    }
    return static_cast<double>(left / right);
}

std::optional<double> try_eval_const_real_expr(
    std::string_view text,
    const std::map<std::string, double>& constants) {
    try {
        const ParsedRealExpr expr = RealExprParser(text).parse();
        return evaluate_real_expr_node(expr, expr.root, constants);
    } catch (const ToolError&) {
        return std::nullopt;
    }
}

std::vector<std::uint8_t> real32_bytes(double source_value) {
    static_assert(sizeof(float) == sizeof(std::uint32_t));
    static_assert(std::numeric_limits<float>::is_iec559);
    const float value = static_cast<float>(source_value);
    std::uint32_t bits = 0;
    if (std::isnan(value)) {
        bits = 0x7FC00000U;
    } else {
        std::memcpy(&bits, &value, sizeof(bits));
    }
    return {
        static_cast<std::uint8_t>(bits & 0xFF),
        static_cast<std::uint8_t>((bits >> 8) & 0xFF),
        static_cast<std::uint8_t>((bits >> 16) & 0xFF),
        static_cast<std::uint8_t>((bits >> 24) & 0xFF),
    };
}

struct ParsedComparison {
    std::string lhs;
    std::string op;
    std::string rhs;
};

std::string strip_outer_condition_parentheses(std::string text) {
    text = trim(text);
    while (text.size() >= 2 && text.front() == '(' && text.back() == ')') {
        int depth = 0;
        bool encloses_all = true;
        for (std::size_t i = 0; i < text.size(); ++i) {
            if (text[i] == '(') {
                ++depth;
            } else if (text[i] == ')') {
                --depth;
                if (depth < 0) {
                    throw ToolError("BAD CONDITION");
                }
                if (depth == 0 && i + 1 != text.size()) {
                    encloses_all = false;
                    break;
                }
            }
        }
        if (depth != 0) {
            throw ToolError("BAD CONDITION");
        }
        if (!encloses_all) {
            break;
        }
        text = trim(std::string_view(text).substr(1, text.size() - 2));
    }
    return text;
}

std::optional<std::pair<std::string, std::string>> split_top_level_condition(
    std::string_view condition,
    std::string_view keyword) {
    const std::string text = strip_outer_condition_parentheses(std::string(condition));
    const std::string upper = upper_ascii(text);
    const std::string upper_keyword = upper_ascii(keyword);
    int depth = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '(') {
            ++depth;
            continue;
        }
        if (text[i] == ')') {
            --depth;
            if (depth < 0) {
                throw ToolError("BAD CONDITION");
            }
            continue;
        }
        if (depth != 0 || i + upper_keyword.size() > upper.size() ||
            upper.compare(i, upper_keyword.size(), upper_keyword) != 0) {
            continue;
        }
        const bool before_ok =
            i == 0 ||
            (!std::isalnum(static_cast<unsigned char>(upper[i - 1])) && upper[i - 1] != '_');
        const std::size_t after = i + upper_keyword.size();
        const bool after_ok =
            after == upper.size() ||
            (!std::isalnum(static_cast<unsigned char>(upper[after])) && upper[after] != '_');
        if (!before_ok || !after_ok) {
            continue;
        }
        const std::string lhs = trim(std::string_view(text).substr(0, i));
        const std::string rhs = trim(std::string_view(text).substr(after));
        if (lhs.empty() || rhs.empty()) {
            throw ToolError("BAD CONDITION");
        }
        return std::make_pair(lhs, rhs);
    }
    if (depth != 0) {
        throw ToolError("BAD CONDITION");
    }
    return std::nullopt;
}

std::optional<ParsedComparison> parse_comparison(std::string_view condition) {
    const std::string text = strip_outer_condition_parentheses(std::string(condition));
    int depth = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '(') {
            ++depth;
            continue;
        }
        if (text[i] == ')') {
            --depth;
            if (depth < 0) {
                throw ToolError("BAD CONDITION");
            }
            continue;
        }
        if (depth != 0) {
            continue;
        }

        std::string op;
        if (i + 1 < text.size()) {
            const std::string two = text.substr(i, 2);
            if (two == "<=" || two == ">=" || two == "<>" || two == "!=") {
                op = two == "!=" ? "<>" : two;
            }
        }
        if (op.empty() && (text[i] == '=' || text[i] == '<' || text[i] == '>' || text[i] == '#')) {
            op = text[i] == '#' ? "<>" : std::string(1, text[i]);
        }
        if (op.empty()) {
            continue;
        }

        const std::string lhs = trim(std::string_view(text).substr(0, i));
        const std::size_t source_op_size =
            i + 1 < text.size() && (text.substr(i, 2) == "!=" || text.substr(i, 2) == "<=" ||
                                     text.substr(i, 2) == ">=" || text.substr(i, 2) == "<>")
                ? 2
                : 1;
        const std::string rhs = trim(std::string_view(text).substr(i + source_op_size));
        if (lhs.empty() || rhs.empty()) {
            throw ToolError("BAD CONDITION");
        }
        return ParsedComparison{lhs, op, rhs};
    }
    if (depth != 0) {
        throw ToolError("BAD CONDITION");
    }
    return std::nullopt;
}

std::string json_string_field(const std::string& text, std::string_view field) {
    const std::string needle = "\"" + std::string(field) + "\"";
    const std::size_t field_pos = text.find(needle);
    if (field_pos == std::string::npos) {
        return {};
    }
    const std::size_t colon = text.find(':', field_pos + needle.size());
    const std::size_t open = text.find('"', colon == std::string::npos ? field_pos : colon);
    if (colon == std::string::npos || open == std::string::npos) {
        return {};
    }
    std::string value;
    for (std::size_t i = open + 1; i < text.size(); ++i) {
        if (text[i] == '"') {
            return value;
        }
        value.push_back(text[i]);
    }
    return {};
}

std::string json_array_body(const std::string& text, std::string_view field) {
    const std::string needle = "\"" + std::string(field) + "\"";
    const std::size_t field_pos = text.find(needle);
    if (field_pos == std::string::npos) {
        return {};
    }
    const std::size_t open = text.find('[', field_pos + needle.size());
    if (open == std::string::npos) {
        return {};
    }
    int depth = 0;
    for (std::size_t i = open; i < text.size(); ++i) {
        if (text[i] == '[') {
            ++depth;
        } else if (text[i] == ']') {
            --depth;
            if (depth == 0) {
                return text.substr(open + 1, i - open - 1);
            }
        }
    }
    return {};
}

std::vector<std::string> json_string_array_field(const std::string& text, std::string_view field) {
    std::vector<std::string> values;
    const std::string body = json_array_body(text, field);
    std::string current;
    bool in_string = false;
    for (char ch : body) {
        if (ch == '"') {
            if (in_string) {
                values.push_back(current);
                current.clear();
            }
            in_string = !in_string;
        } else if (in_string) {
            current.push_back(ch);
        }
    }
    return values;
}

ObjectFile parse_json_object_record(const fs::path& path, const std::string& text) {
    ObjectFile object;
    object.module = upper_ascii(json_string_field(text, "module"));
    if (object.module.empty()) {
        object.module = upper_ascii(path.stem().string());
    }
    const std::string payload_hex = json_string_field(text, "payload_hex");
    if (payload_hex.empty()) {
        throw ToolError("BAD OBJECT");
    }
    object.code = hex_to_bytes(payload_hex);
    if (object.code.size() > std::numeric_limits<std::uint16_t>::max()) {
        throw ToolError("BAD OBJECT");
    }
    for (const std::string& import : json_string_array_field(text, "imports")) {
        object.imports.push_back(upper_ascii(import));
    }

    const std::string exports_body = json_array_body(text, "exports");
    const std::regex export_record("\\[\\s*\"([^\"]+)\"\\s*,\\s*([0-9]+)\\s*\\]");
    for (auto it = std::sregex_iterator(exports_body.begin(), exports_body.end(), export_record);
         it != std::sregex_iterator(); ++it) {
        const std::uint16_t offset = parse_object_word((*it)[2].str(), 10);
        if (offset >= object.code.size()) {
            throw ToolError("BAD OBJECT");
        }
        object.exports.push_back(ObjExport{
            upper_ascii((*it)[1].str()),
            offset,
            static_cast<std::uint16_t>(object.code.size() - offset),
        });
    }
    validate_object(object);
    return object;
}

ObjectFile parse_object_file(const fs::path& path) {
    ObjectFile object;
    object.module = upper_ascii(path.stem().string());
    const auto lines = split_lines(read_text_file(path));
    bool saw_header = false;
    bool saw_body = false;
    bool saw_source_file = false;
    std::vector<int> body_imports;
    for (const std::string& raw : lines) {
        const std::string line = trim(raw);
        if (line.empty()) {
            continue;
        }
        if (!saw_header) {
            if (upper_ascii(line) != "OBJ1") {
                throw ToolError("BAD OBJECT");
            }
            saw_header = true;
            continue;
        }
        if (!line.empty() && line.front() == '{') {
            return parse_json_object_record(path, line);
        }
        const auto words = split_words(line);
        if (words.empty()) {
            continue;
        }
        const std::string record = upper_ascii(words[0]);
        if (record == "X" && words.size() == 4) {
            object.exports.push_back(ObjExport{
                upper_ascii(words[1]),
                parse_object_word(words[2], 10),
                parse_object_word(words[3], 10),
            });
        } else if (record == "B" && words.size() == 2) {
            if (saw_body) {
                throw ToolError("BAD OBJECT");
            }
            saw_body = true;
            body_imports = parse_machine_body_marker(words[1]);
        } else if (record == "U" && words.size() == 2) {
            object.imports.push_back(upper_ascii(words[1]));
        } else if (record == "M" && words.size() >= 2) {
            std::string encoded;
            for (std::size_t i = 1; i < words.size(); ++i) {
                encoded += words[i];
            }
            std::vector<std::uint8_t> chunk = hex_to_bytes(encoded);
            object.code.insert(object.code.end(), chunk.begin(), chunk.end());
        } else if (record == "R" &&
                   (words.size() >= 3 && words.size() <= 6)) {
            ObjReloc reloc;
            reloc.offset = parse_object_word(words[1], 10);
            std::size_t target_index = 2;
            const std::string encoded_part = upper_ascii(words[target_index]);
            if (encoded_part == "L" || encoded_part == "LO" ||
                encoded_part == "H" || encoded_part == "HI") {
                reloc.part = encoded_part == "L" || encoded_part == "LO"
                    ? ObjRelocPart::LowByte
                    : ObjRelocPart::HighByte;
                ++target_index;
                if (target_index >= words.size()) {
                    throw ToolError("BAD OBJECT");
                }
            }
            const std::string target = upper_ascii(words[target_index]);
            const std::size_t remaining = words.size() - target_index;
            if ((remaining == 1 || remaining == 2) &&
                target.size() > 1 && target[0] == 'U') {
                reloc.import = true;
                reloc.import_index = parse_import_index(
                    std::string_view(target).substr(1));
                if (remaining == 2) {
                    reloc.addend = parse_relocation_addend(
                        words[target_index + 1]);
                }
            } else if ((remaining == 2 || remaining == 3) && target == "X") {
                reloc.symbol = upper_ascii(words[target_index + 1]);
                if (remaining == 3) {
                    reloc.addend = parse_relocation_addend(
                        words[target_index + 2]);
                }
            } else {
                throw ToolError("BAD OBJECT");
            }
            object.relocs.push_back(reloc);
        } else if (record == "F" && words.size() >= 2) {
            if (saw_source_file) {
                throw ToolError("BAD OBJECT");
            }
            saw_source_file = true;
            object.source_file = trim(std::string_view(line).substr(1));
        } else if (record == "L" && words.size() == 3) {
            object.lines.push_back(ObjLineRecord{
                parse_object_word(words[1], 10),
                parse_object_size(words[2]),
            });
        } else if (record == "N" && words.size() == 2) {
            // Optional historical display name; exports remain authoritative.
        } else {
            throw ToolError("BAD OBJECT");
        }
    }
    if (!saw_header || !saw_body) {
        throw ToolError("BAD OBJECT");
    }
    std::set<int> body_import_set;
    for (const int index : body_imports) {
        if (index < 0 || static_cast<std::size_t>(index) >= object.imports.size() ||
            !body_import_set.insert(index).second) {
            throw ToolError("BAD OBJECT");
        }
    }
    validate_object(object);
    return object;
}

int cmd_actnew(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const fs::path root = fs::current_path() / upper_ascii(args.front());
    if (fs::exists(root)) {
        throw ToolError("EXISTS");
    }
    fs::create_directories(root / "SRC");
    fs::create_directories(root / "BIN");
    fs::create_directories(root / "OBJ");
    write_text_file(root / "ACTION.PROJ", "ACTION PROJECT\nMAIN.ACT\n");
    write_text_file(
        root / "README.TXT",
        "UPDATES\nACTION PROJECT READY\n\n"
        "SRC contains Action source.\n"
        "BIN contains build outputs.\n"
        "OBJ contains intermediate artifacts.\n");
    write_text_file(root / "SRC" / "MAIN.ACT", "PROC MAIN()\nENDPROC\n");
    std::cout << "ACTNEW OK\n";
    return 0;
}

int cmd_actadd(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const std::string module = module_from_arg(args.front());
    std::vector<std::string> entries = load_manifest_entries(fs::current_path());
    if (manifest_contains_module(entries, module)) {
        throw ToolError("EXISTS");
    }
    const fs::path path = source_path(fs::current_path(), module);
    if (fs::exists(path)) {
        throw ToolError("EXISTS");
    }
    write_text_file(path, "PROC " + module + "()\nENDPROC\n");
    entries.push_back(module + ".ACT");
    save_manifest_entries(fs::current_path(), entries);
    std::cout << "ACTADD OK\n";
    return 0;
}

struct WorkSummary {
    bool project = false;
    bool src = false;
    bool bin = false;
    bool obj = false;
    std::size_t modules = 0;
};

WorkSummary collect_work_summary(const fs::path& root) {
    WorkSummary summary;
    summary.project = child_case_insensitive(root, "ACTION.PROJ").has_value();
    summary.src = child_case_insensitive(root, "SRC").has_value();
    summary.bin = child_case_insensitive(root, "BIN").has_value();
    summary.obj = child_case_insensitive(root, "OBJ").has_value();
    if (summary.project) {
        summary.modules = load_manifest_entries(root).size();
    }
    return summary;
}

void print_work_summary(const WorkSummary& summary) {
    std::cout << "PROJECT " << (summary.project ? "YES" : "NO") << "\n";
    std::cout << "SRC " << (summary.src ? "YES" : "NO") << "\n";
    std::cout << "BIN " << (summary.bin ? "YES" : "NO") << "\n";
    std::cout << "OBJ " << (summary.obj ? "YES" : "NO") << "\n";
    std::cout << "MODULES " << summary.modules << "\n";
}

int cmd_actwork(const std::vector<std::string>&) {
    print_work_summary(collect_work_summary(fs::current_path()));
    return 0;
}

int cmd_actsrc(const std::vector<std::string>&) {
    const auto entries = load_manifest_entries(fs::current_path());
    if (entries.empty()) {
        std::cout << "EMPTY\n";
        return 0;
    }
    for (const std::string& entry : entries) {
        std::cout << entry << "\n";
    }
    return 0;
}

int cmd_actfile(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const std::string module = module_from_arg(args.front());
    require_project_module(fs::current_path(), module);
    const fs::path path = source_path(fs::current_path(), module);
    if (!fs::is_regular_file(path)) {
        throw ToolError("NO FILE");
    }
    std::cout << read_text_file(path);
    return 0;
}

int cmd_actchk(const std::vector<std::string>&) {
    const auto entries = load_manifest_entries(fs::current_path());
    WorkSummary summary = collect_work_summary(fs::current_path());
    print_work_summary(summary);

    std::vector<std::string> missing;
    for (const std::string& entry : entries) {
        std::string module = entry;
        const std::string suffix = ".ACT";
        if (module.size() >= suffix.size() &&
            upper_ascii(std::string_view(module).substr(module.size() - suffix.size())) == suffix) {
            module.resize(module.size() - suffix.size());
        }
        if (!fs::is_regular_file(source_path(fs::current_path(), module))) {
            missing.push_back(entry);
        }
    }
    std::cout << "MISSING " << missing.size() << "\n";
    for (const std::string& entry : missing) {
        std::cout << "MISSING " << entry << "\n";
    }
    if (!summary.src || !summary.bin || !summary.obj || !missing.empty()) {
        std::cout << "ACTCHK BROKEN\n";
        return 1;
    }
    std::cout << "ACTCHK OK\n";
    return 0;
}

int cmd_actdir(const std::vector<std::string>& args) {
    const fs::path dir = args.empty() ? fs::current_path() : fs::path(args.front());
    if (!fs::is_directory(dir)) {
        throw ToolError("NO DIR");
    }
    std::vector<std::string> entries;
    for (const auto& entry : fs::directory_iterator(dir)) {
        const std::string prefix = entry.is_directory() ? "D " : "F ";
        entries.push_back(prefix + entry.path().filename().string());
    }
    std::sort(entries.begin(), entries.end(), [](const std::string& a, const std::string& b) {
        return upper_ascii(a) < upper_ascii(b);
    });
    for (const std::string& entry : entries) {
        std::cout << entry << "\n";
    }
    return 0;
}

int cmd_actcopy(const std::vector<std::string>& args) {
    if (args.size() < 2) {
        throw ToolError("BAD COPY");
    }
    const fs::path src = args[0];
    const fs::path dst = args[1];
    if (!fs::is_regular_file(src)) {
        throw ToolError("NO SUCH FILE");
    }
    fs::create_directories(dst.parent_path().empty() ? fs::path(".") : dst.parent_path());
    fs::copy_file(src, dst, fs::copy_options::overwrite_existing);
    std::cout << "ACTCOPY OK\n";
    return 0;
}

int cmd_actdel(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const fs::path target = args.front();
    if (!fs::is_regular_file(target)) {
        throw ToolError("NO SUCH FILE");
    }
    fs::remove(target);
    std::cout << "ACTDEL OK\n";
    return 0;
}

int cmd_actmkdir(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    fs::create_directories(args.front());
    std::cout << "ACTMKDIR OK\n";
    return 0;
}

int cmd_actrmdir(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const fs::path target = args.front();
    if (!fs::is_directory(target)) {
        throw ToolError("NO DIR");
    }
    if (!fs::remove(target)) {
        throw ToolError("RMDIR FAIL");
    }
    std::cout << "ACTRMDIR OK\n";
    return 0;
}

int cmd_actmove(const std::vector<std::string>& args) {
    if (args.size() < 2) {
        throw ToolError("BAD MOVE");
    }
    const fs::path src = args[0];
    const fs::path dst = args[1];
    if (!fs::exists(src)) {
        throw ToolError("NO SUCH FILE");
    }
    fs::create_directories(dst.parent_path().empty() ? fs::path(".") : dst.parent_path());
    fs::rename(src, dst);
    std::cout << "ACTMOVE OK\n";
    return 0;
}

int cmd_actwrite(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    std::string text;
    for (std::size_t i = 1; i < args.size(); ++i) {
        if (i > 1) {
            text += " ";
        }
        text += args[i];
    }
    if (!text.empty()) {
        text += "\n";
    }
    write_text_file(args.front(), text);
    std::cout << "ACTWRITE OK\n";
    return 0;
}

int cmd_actinfo(const std::vector<std::string>&) {
    std::cout << "ACTIONC64U IDUN LINUX TOOLS\n";
    std::cout << "TOOLS C++17\n";
    std::cout << "OUTPUT C64 PRG\n";
    return 0;
}

fs::path normalized_absolute_path(const fs::path& path) {
    return fs::weakly_canonical(fs::absolute(path));
}

std::optional<fs::path> find_project_root_from(fs::path start) {
    std::error_code error;
    const fs::path absolute = fs::absolute(std::move(start)).lexically_normal();
    const fs::path canonical = fs::weakly_canonical(absolute, error);
    start = error ? absolute : canonical;
    error.clear();
    if (!fs::is_directory(start, error)) {
        error.clear();
        start = start.parent_path();
    }
    while (!start.empty()) {
        const auto manifest = child_case_insensitive(start, "ACTION.PROJ");
        if (manifest && fs::is_regular_file(*manifest, error) && !error) {
            return start;
        }
        error.clear();
        const fs::path parent = start.parent_path();
        if (parent.empty() || parent == start) {
            break;
        }
        start = parent;
    }
    return std::nullopt;
}

std::optional<fs::path> selected_project_root() {
    const char* configured = std::getenv("ACTION_PROJECT");
    if (configured != nullptr && *configured != '\0') {
        fs::path requested(configured);
        if (requested.is_relative()) {
            requested = g_invocation_cwd / requested;
        }
        const auto root = find_project_root_from(requested);
        if (!root) {
            throw ToolError("ACTION_PROJECT HAS NO ACTION.PROJ");
        }
        return root;
    }
    return find_project_root_from(g_invocation_cwd);
}

bool command_uses_project_context(std::string_view command) {
    const std::string name = upper_ascii(command);
    static const std::set<std::string> commands = {
        "ACTADD", "ACTWORK", "ACTSRC", "ACTFILE", "ACTCHK", "ACTMON",
        "ACTDBG", "ACTPROF", "ACTEDIT", "ACT2SAVE", "ACTSAVE", "ACTC",
        "ALINK",
    };
    return commands.count(name) != 0;
}

bool invocation_has_local_module(
    std::string_view command,
    const std::vector<std::string>& args) {
    const std::string name = upper_ascii(command);
    if (args.empty() && name != "ACT2SAVE" && name != "ACTSAVE") {
        return false;
    }
    const std::string argument = args.empty() ? "MAIN" : args.front();
    std::string module;
    try {
        module = module_from_arg(argument);
    } catch (const ToolError&) {
        return false;
    }
    const auto local = [&](std::string_view extension) {
        return flat_module_file(g_invocation_cwd, module, extension).has_value();
    };
    if (name == "ACTC" || name == "ACTEDIT") {
        return local(".ACT");
    }
    if (name == "ALINK" || name == "ACT2SAVE" || name == "ACTSAVE") {
        return local(".ACT") || local(".OBJ");
    }
    if (name == "ACTDBG" || name == "ACTPROF") {
        return local(".ACT") || local(".OBJ") ||
            local(".PRG") || local(".DBG");
    }
    return false;
}

bool path_is_same_or_descendant(
    const fs::path& parent,
    const fs::path& candidate) {
    auto parent_it = parent.begin();
    auto candidate_it = candidate.begin();
    for (; parent_it != parent.end(); ++parent_it, ++candidate_it) {
        if (candidate_it == candidate.end() || *parent_it != *candidate_it) {
            return false;
        }
    }
    return true;
}

fs::path action_state_path(const fs::path& root, std::string_view filename) {
    return root / ".action" / std::string(filename);
}

void rebuild_source_index(const fs::path& root) {
    SqliteDatabase database(action_state_path(root, "workspace.sqlite3"));
    database.exec(
        "CREATE TABLE IF NOT EXISTS source_lines("
        "module TEXT NOT NULL,path TEXT NOT NULL,line INTEGER NOT NULL,"
        "text TEXT NOT NULL,PRIMARY KEY(module,line))");
    database.exec(
        "CREATE TABLE IF NOT EXISTS source_symbols("
        "name TEXT NOT NULL,kind TEXT NOT NULL,module TEXT NOT NULL,"
        "path TEXT NOT NULL,line INTEGER NOT NULL)");
    database.exec(
        "CREATE INDEX IF NOT EXISTS source_symbols_name "
        "ON source_symbols(name COLLATE NOCASE)");
    database.exec("BEGIN IMMEDIATE");
    try {
        database.exec("DELETE FROM source_lines");
        database.exec("DELETE FROM source_symbols");
        SqliteStatement insert_line(
            database,
            "INSERT INTO source_lines(module,path,line,text) VALUES(?,?,?,?)");
        SqliteStatement insert_symbol(
            database,
            "INSERT INTO source_symbols(name,kind,module,path,line) "
            "VALUES(?,?,?,?,?)");
        const std::regex structural_symbol(
            R"(^\s*(MODULE|PROC|OVERLAY|BYTE\s+FUNC|CARD\s+FUNC|INT\s+FUNC|REAL\s+FUNC)\s+([A-Za-z_][A-Za-z0-9_]*))",
            std::regex_constants::icase);
        const std::regex data_symbol(
            R"(^\s*(BYTE|CARD|INT|REAL)\s+(?:ARRAY\s+|POINTER\s+)?([A-Za-z_][A-Za-z0-9_]*))",
            std::regex_constants::icase);

        for (const std::string& entry : load_manifest_entries(root)) {
            const std::string module = module_from_arg(entry);
            const fs::path source = source_path(root, module);
            if (!fs::is_regular_file(source)) {
                continue;
            }
            const std::string relative = fs::relative(source, root).generic_string();
            const std::vector<std::string> lines =
                split_lines(read_text_file(source));
            for (std::size_t i = 0; i < lines.size(); ++i) {
                insert_line.bind_text(1, module);
                insert_line.bind_text(2, relative);
                insert_line.bind_integer(3, static_cast<std::int64_t>(i + 1));
                insert_line.bind_text(4, lines[i]);
                insert_line.step();
                insert_line.reset();

                const std::string code = strip_source_comment(lines[i]);
                std::smatch match;
                std::string kind;
                std::string name;
                if (std::regex_search(code, match, structural_symbol)) {
                    kind = upper_ascii(match[1].str());
                    name = upper_ascii(match[2].str());
                } else if (std::regex_search(code, match, data_symbol)) {
                    kind = upper_ascii(match[1].str());
                    name = upper_ascii(match[2].str());
                }
                if (!name.empty()) {
                    insert_symbol.bind_text(1, name);
                    insert_symbol.bind_text(2, kind);
                    insert_symbol.bind_text(3, module);
                    insert_symbol.bind_text(4, relative);
                    insert_symbol.bind_integer(
                        5, static_cast<std::int64_t>(i + 1));
                    insert_symbol.step();
                    insert_symbol.reset();
                }
            }
        }
        database.exec("COMMIT");
    } catch (...) {
        try {
            database.exec("ROLLBACK");
        } catch (...) {
        }
        throw;
    }
}

void print_source_matches(const fs::path& root, std::string_view query) {
    rebuild_source_index(root);
    SqliteDatabase database(action_state_path(root, "workspace.sqlite3"));
    SqliteStatement select(
        database,
        "SELECT path,line,text FROM source_lines "
        "WHERE instr(lower(text),lower(?))>0 ORDER BY path,line");
    select.bind_text(1, query);
    while (select.step()) {
        std::cout << select.text(0) << ":" << select.integer(1) << ":"
                  << select.text(2) << "\n";
    }
}

void print_source_symbols(const fs::path& root, std::string_view module) {
    rebuild_source_index(root);
    SqliteDatabase database(action_state_path(root, "workspace.sqlite3"));
    SqliteStatement select(
        database,
        "SELECT kind,name,path,line FROM source_symbols "
        "WHERE module=? ORDER BY line,name");
    select.bind_text(1, upper_ascii(module));
    while (select.step()) {
        std::cout << select.text(0) << " " << select.text(1) << " "
                  << select.text(2) << ":" << select.integer(3) << "\n";
    }
}

void print_code_map_location(
    std::string_view label,
    const action_linux::CodeMapLocation& location) {
    std::cout << label << " " << location.kind << " " << location.name << " "
              << location.path << ":" << location.line << ":" << location.column;
    if (location.address) {
        std::cout << " ADDRESS " << *location.address;
    }
    if (!location.caller.empty()) {
        std::cout << " CALLER " << location.caller;
    }
    std::cout << "\n";
    if (!location.signature.empty()) {
        std::cout << "SIGNATURE " << location.signature << "\n";
    }
}

void print_code_map_definition(const fs::path& root, std::string_view symbol) {
    const auto definition =
        action_linux::code_map_definition(root, std::string(symbol));
    if (!definition) {
        throw ToolError("NO DEFINITION " + std::string(symbol));
    }
    print_code_map_location("DEFINITION", *definition);
}

void print_code_map_references(const fs::path& root, std::string_view symbol) {
    const std::vector<action_linux::CodeMapLocation> references =
        action_linux::code_map_references(root, std::string(symbol));
    for (const auto& reference : references) {
        print_code_map_location("REFERENCE", reference);
    }
    std::cout << "REFERENCES " << references.size() << "\n";
}

void print_code_map_summary(const fs::path& root) {
    const action_linux::CodeMapSummary summary =
        action_linux::code_map_summary(root);
    std::cout << "CODE MAP " << summary.entry_module << "\n"
              << "FINGERPRINT " << summary.fingerprint << "\n"
              << "MODULES " << summary.modules << "\n"
              << "DEFINITIONS " << summary.definitions << "\n"
              << "REFERENCES " << summary.references << "\n";
}

int cmd_actedit(const std::vector<std::string>& args);
int cmd_actc(const std::vector<std::string>& args);
int cmd_alink(const std::vector<std::string>& args);
int cmd_actdbg(const std::vector<std::string>& args);

int compile_and_link_module(const std::string& module) {
    const int compile_status = cmd_actc({module});
    if (compile_status != 0) {
        return compile_status;
    }
    return cmd_alink({module});
}

int cmd_actmon(const std::vector<std::string>& args) {
    if (!args.empty()) {
        const std::string mode = upper_ascii(args.front());
        if (mode == "STATUS") {
            if (args.size() != 1) {
                throw ToolError("BAD MONITOR COMMAND");
            }
        } else if (mode == "SOURCES") {
            if (args.size() != 1) {
                throw ToolError("BAD MONITOR COMMAND");
            }
            return cmd_actsrc({});
        } else if (mode == "CHECK") {
            if (args.size() != 1) {
                throw ToolError("BAD MONITOR COMMAND");
            }
            return cmd_actchk({});
        } else {
            if (args.size() != 2) {
                throw ToolError("BAD MONITOR COMMAND");
            }
            const std::string module = module_from_arg(args[1]);
            if (mode == "EDIT") {
                return cmd_actedit({module});
            }
            if (mode == "COMPILE") {
                return cmd_actc({module});
            }
            if (mode == "BUILD") {
                return compile_and_link_module(module);
            }
            if (mode == "DEBUG") {
                const int status = compile_and_link_module(module);
                return status == 0 ? cmd_actdbg({module}) : status;
            }
            throw ToolError("BAD MONITOR COMMAND");
        }
    }

    const fs::path root = fs::current_path();
    std::cout << "ACTIONC64U MONITOR\n";
    print_work_summary(collect_work_summary(root));
    if (child_case_insensitive(root, "ACTION.PROJ").has_value()) {
        const auto entries = load_manifest_entries(root);
        std::cout << "SOURCES\n";
        for (const std::string& entry : entries) {
            std::cout << "  " << entry << "\n";
        }
    }
    std::cout << "COMMANDS actnew actadd actedit actc alink actdbg actchk\n";
    std::cout << "WORKFLOW actmon edit|compile|build|debug <module>\n";
    return 0;
}

struct DebugLineInfo {
    std::uint16_t address = 0;
    int module_id = 0;
    std::size_t line = 0;
};

struct DebugSymbolInfo {
    std::uint16_t address = 0;
    std::uint16_t size = 0;
    std::string name;
};

struct DebugSidecar {
    std::map<int, std::string> modules;
    std::map<int, std::string> source_files;
    std::vector<DebugLineInfo> lines;
    std::vector<DebugSymbolInfo> symbols;
};

DebugSidecar parse_debug_sidecar(const fs::path& path) {
    DebugSidecar sidecar;
    for (const std::string& raw : split_lines(read_text_file(path))) {
        const std::string line = trim(raw);
        const std::vector<std::string> words = split_words(line);
        if (words.empty()) {
            continue;
        }
        if (words[0] == "m" && words.size() >= 3) {
            sidecar.modules[static_cast<int>(parse_object_size(words[1]))] =
                words[2];
        } else if (words[0] == "f" && words.size() >= 3) {
            const int module_id =
                static_cast<int>(parse_object_size(words[1]));
            const std::size_t path_pos = line.find(words[2]);
            sidecar.source_files[module_id] =
                path_pos == std::string::npos ? words[2] : line.substr(path_pos);
        } else if (words[0] == "l" && words.size() >= 4) {
            sidecar.lines.push_back(DebugLineInfo{
                parse_object_word(words[1]),
                static_cast<int>(parse_object_size(words[2])),
                parse_object_size(words[3]),
            });
        } else if (words[0] == "y" && words.size() >= 4) {
            sidecar.symbols.push_back(DebugSymbolInfo{
                parse_object_word(words[1]),
                parse_object_word(words[2]),
                upper_ascii(words[3]),
            });
        }
    }
    return sidecar;
}

std::uint16_t parse_debug_address(std::string_view text) {
    std::string value = trim(text);
    int base = 10;
    if (!value.empty() && value.front() == '$') {
        value.erase(value.begin());
        base = 16;
    } else if (value.size() > 2 && value[0] == '0' &&
               (value[1] == 'x' || value[1] == 'X')) {
        value.erase(0, 2);
        base = 16;
    }
    return parse_object_word(value, base);
}

std::optional<DebugLineInfo> debug_line_for_source(
    const DebugSidecar& sidecar,
    int module_id,
    std::size_t line) {
    std::optional<DebugLineInfo> best;
    for (const DebugLineInfo& candidate : sidecar.lines) {
        if (candidate.module_id == module_id && candidate.line == line &&
            (!best || candidate.address < best->address)) {
            best = candidate;
        }
    }
    return best;
}

std::optional<DebugLineInfo> debug_line_for_address(
    const DebugSidecar& sidecar,
    std::uint16_t address) {
    std::optional<DebugLineInfo> best;
    for (const DebugLineInfo& candidate : sidecar.lines) {
        if (candidate.address <= address &&
            (!best || candidate.address > best->address)) {
            best = candidate;
        }
    }
    return best;
}

std::string debug_source_name(const DebugSidecar& sidecar, int module_id) {
    auto source = sidecar.source_files.find(module_id);
    if (source != sidecar.source_files.end()) {
        return source->second;
    }
    auto module = sidecar.modules.find(module_id);
    return module == sidecar.modules.end()
        ? std::string{"UNKNOWN"}
        : "SRC/" + module->second + ".ACT";
}

void ensure_breakpoint_schema(SqliteDatabase& database) {
    database.exec(
        "CREATE TABLE IF NOT EXISTS breakpoints("
        "id INTEGER PRIMARY KEY,module TEXT NOT NULL,source TEXT NOT NULL,"
        "line INTEGER NOT NULL,address INTEGER NOT NULL,enabled INTEGER NOT NULL "
        "DEFAULT 1,UNIQUE(module,source,line))");
}

void store_breakpoint(
    const fs::path& root,
    std::string_view module,
    const std::string& source,
    const DebugLineInfo& location) {
    SqliteDatabase database(action_state_path(root, "debug.sqlite3"));
    ensure_breakpoint_schema(database);
    SqliteStatement upsert(
        database,
        "INSERT INTO breakpoints(module,source,line,address,enabled) "
        "VALUES(?,?,?,?,1) ON CONFLICT(module,source,line) DO UPDATE SET "
        "address=excluded.address,enabled=1");
    upsert.bind_text(1, upper_ascii(module));
    upsert.bind_text(2, source);
    upsert.bind_integer(3, static_cast<std::int64_t>(location.line));
    upsert.bind_integer(4, location.address);
    upsert.step();

    SqliteStatement select(
        database,
        "SELECT id FROM breakpoints WHERE module=? AND source=? AND line=?");
    select.bind_text(1, upper_ascii(module));
    select.bind_text(2, source);
    select.bind_integer(3, static_cast<std::int64_t>(location.line));
    if (!select.step()) {
        throw ToolError("BREAKPOINT STORE FAIL");
    }
    std::cout << "BREAKPOINT " << select.integer(0) << " "
              << location.address << " " << source << ":" << location.line
              << "\n";
}

void list_breakpoints(const fs::path& root, std::string_view module) {
    SqliteDatabase database(action_state_path(root, "debug.sqlite3"));
    ensure_breakpoint_schema(database);
    SqliteStatement select(
        database,
        "SELECT id,address,source,line,enabled FROM breakpoints "
        "WHERE module=? ORDER BY source,line");
    select.bind_text(1, upper_ascii(module));
    while (select.step()) {
        std::cout << "BREAKPOINT " << select.integer(0) << " "
                  << select.integer(1) << " " << select.text(2) << ":"
                  << select.integer(3) << " "
                  << (select.integer(4) != 0 ? "ENABLED" : "DISABLED")
                  << "\n";
    }
}

void clear_breakpoint(
    const fs::path& root,
    std::string_view module,
    std::size_t id) {
    SqliteDatabase database(action_state_path(root, "debug.sqlite3"));
    ensure_breakpoint_schema(database);
    SqliteStatement remove(
        database,
        "DELETE FROM breakpoints WHERE module=? AND id=?");
    remove.bind_text(1, upper_ascii(module));
    remove.bind_integer(2, static_cast<std::int64_t>(id));
    remove.step();
    if (sqlite3_changes(database.get()) == 0) {
        throw ToolError("NO BREAKPOINT");
    }
    std::cout << "BREAKPOINT CLEARED " << id << "\n";
}

struct PreparedBreakpoint {
    std::size_t id = 0;
    std::uint16_t address = 0;
    std::string source;
    std::size_t line = 0;
};

std::vector<PreparedBreakpoint> load_prepared_breakpoints(
    const fs::path& root,
    std::string_view module) {
    const fs::path path = action_state_path(root, "debug.sqlite3");
    if (!fs::is_regular_file(path)) {
        return {};
    }
    SqliteDatabase database(path);
    ensure_breakpoint_schema(database);
    SqliteStatement select(
        database,
        "SELECT id,address,source,line FROM breakpoints "
        "WHERE module=? AND enabled<>0 ORDER BY id");
    select.bind_text(1, upper_ascii(module));
    std::vector<PreparedBreakpoint> breakpoints;
    while (select.step()) {
        breakpoints.push_back(PreparedBreakpoint{
            static_cast<std::size_t>(select.integer(0)),
            static_cast<std::uint16_t>(select.integer(1)),
            select.text(2),
            static_cast<std::size_t>(select.integer(3)),
        });
    }
    return breakpoints;
}

std::string debug_hex_word(std::uint16_t value) {
    std::ostringstream output;
    output << "$" << std::uppercase << std::hex << std::setfill('0')
           << std::setw(4) << value;
    return output.str();
}

void print_live_source(const DebugSidecar& sidecar, std::uint16_t address) {
    const auto location = debug_line_for_address(sidecar, address);
    if (!location) {
        std::cout << "SOURCE " << debug_hex_word(address) << " UNKNOWN\n";
        return;
    }
    std::cout << "SOURCE " << debug_hex_word(address) << " "
              << debug_source_name(sidecar, location->module_id)
              << ":" << location->line << "\n";
}

void print_live_registers(
    const DebugSidecar& sidecar,
    const action_linux::target::Registers& registers) {
    std::cout << "REGISTERS"
              << " A=" << static_cast<unsigned int>(registers.a)
              << " X=" << static_cast<unsigned int>(registers.x)
              << " Y=" << static_cast<unsigned int>(registers.y)
              << " SP=" << static_cast<unsigned int>(registers.sp)
              << " P=" << static_cast<unsigned int>(registers.status)
              << " PC=" << debug_hex_word(registers.pc) << "\n";
    print_live_source(sidecar, registers.pc);
}

void print_target_event(
    const DebugSidecar& sidecar,
    const action_linux::target::Packet& event) {
    using action_linux::target::MessageType;
    std::cout << "EVENT " << action_linux::target::message_type_name(event.type);
    std::optional<std::uint16_t> address;
    if (event.type == MessageType::BreakpointHit && event.payload.size() >= 3) {
        std::cout << " BREAKPOINT=" << static_cast<unsigned int>(event.payload[0]);
        address = static_cast<std::uint16_t>(
            event.payload[1] | (static_cast<std::uint16_t>(event.payload[2]) << 8));
    } else if (event.payload.size() >= 2) {
        address = static_cast<std::uint16_t>(
            event.payload[0] | (static_cast<std::uint16_t>(event.payload[1]) << 8));
    }
    if (address) {
        std::cout << " PC=" << debug_hex_word(*address);
    }
    std::cout << "\n";
    if (address) {
        print_live_source(sidecar, *address);
    }
}

void print_live_debug_help() {
    std::cout
        << "LIVE COMMANDS\n"
        << "  info | regs | where\n"
        << "  memory <address> [count]\n"
        << "  args [program-argument ...]\n"
        << "  break <line> | break address <address>\n"
        << "  clear <target-breakpoint-id>\n"
        << "  run | halt | step | wait [milliseconds]\n"
        << "  sampling on|off | samples\n"
        << "  help | quit\n";
}

int run_live_debugger(
    const fs::path& root,
    const std::string& module,
    const DebugSidecar& sidecar,
    const std::vector<std::string>& initial_command,
    const std::vector<std::string>& program_arguments) {
    using namespace action_linux::target;
    IdunTargetSession session(root, module);
    if (!program_arguments.empty()) {
        session.set_program_arguments(module, program_arguments);
    }
    const HelloInfo hello = session.hello();
    std::cout << "ACTDBG LIVE\n"
              << "PROTOCOL " << static_cast<unsigned int>(kProtocolMajor)
              << "." << static_cast<unsigned int>(kProtocolMinor) << "\n"
              << "MAX_PAYLOAD " << hello.maximum_payload << "\n"
              << "CAPABILITIES 0x" << std::uppercase << std::hex
              << std::setfill('0') << std::setw(4) << hello.capabilities
              << std::dec << "\n"
              << "SERVICE " << debug_hex_word(hello.service_begin)
              << "-" << debug_hex_word(hello.service_end) << "\n";

    if ((hello.capabilities & SoftwareBreakpoints) != 0) {
        for (const PreparedBreakpoint& breakpoint :
             load_prepared_breakpoints(root, module)) {
            const std::uint8_t target_id = session.set_breakpoint(breakpoint.address);
            std::cout << "BREAKPOINT SYNC " << breakpoint.id
                      << " TARGET=" << static_cast<unsigned int>(target_id)
                      << " " << breakpoint.source << ":" << breakpoint.line
                      << " " << debug_hex_word(breakpoint.address) << "\n";
        }
    }

    bool running = false;
    const auto execute = [&](const std::vector<std::string>& words) -> bool {
        if (words.empty()) return true;
        const std::string command = upper_ascii(words[0]);
        if (command == "QUIT" || command == "EXIT") return false;
        if (command == "HELP" || command == "?") {
            print_live_debug_help();
            return true;
        }
        if (command == "INFO") {
            std::cout << "TARGET " << (running ? "RUNNING" : "HALTED") << "\n";
            if ((hello.capabilities & RegisterAccess) != 0 && !running) {
                print_live_registers(sidecar, session.read_registers());
            }
            return true;
        }
        if (command == "REGS" || command == "REGISTERS" || command == "WHERE") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            print_live_registers(sidecar, session.read_registers());
            return true;
        }
        if (command == "MEMORY" || command == "MEM") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            if (words.size() < 2 || words.size() > 3) {
                throw ToolError("BAD LIVE MEMORY COMMAND");
            }
            const std::uint16_t address = parse_debug_address(words[1]);
            const std::size_t count = words.size() == 3
                ? parse_object_size(words[2])
                : 16;
            if (count == 0 || count > kMaximumPayload - 1) {
                throw ToolError("BAD LIVE MEMORY SIZE");
            }
            const std::vector<std::uint8_t> bytes = session.read_memory(
                address, static_cast<std::uint8_t>(count));
            std::cout << "MEMORY " << debug_hex_word(address) << " "
                      << bytes_to_hex(bytes) << "\n";
            return true;
        }
        if (command == "ARGS" || command == "ARGUMENTS") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            session.set_program_arguments(
                module,
                std::vector<std::string>(words.begin() + 1, words.end()));
            std::cout << "PROGRAM ARGUMENTS " << words.size() - 1
                      << " ARGC " << words.size() << "\n";
            return true;
        }
        if (command == "BREAK") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            if (words.size() < 2 || words.size() > 3) {
                throw ToolError("BAD LIVE BREAK COMMAND");
            }
            std::uint16_t address = 0;
            std::string label;
            if (words.size() == 3 && upper_ascii(words[1]) == "ADDRESS") {
                address = parse_debug_address(words[2]);
                label = debug_hex_word(address);
            } else if (words.size() == 2) {
                const std::size_t line = parse_object_size(words[1]);
                const auto location = debug_line_for_source(sidecar, 0, line);
                if (!location) throw ToolError("NO SOURCE LINE");
                address = location->address;
                label = debug_source_name(sidecar, location->module_id) +
                    ":" + std::to_string(location->line);
            } else {
                throw ToolError("BAD LIVE BREAK COMMAND");
            }
            const std::uint8_t id = session.set_breakpoint(address);
            std::cout << "TARGET BREAKPOINT " << static_cast<unsigned int>(id)
                      << " " << debug_hex_word(address) << " " << label << "\n";
            return true;
        }
        if (command == "CLEAR") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            if (words.size() != 2) throw ToolError("BAD LIVE CLEAR COMMAND");
            const std::size_t id = parse_object_size(words[1]);
            if (id == 0 || id > 255) throw ToolError("BAD TARGET BREAKPOINT ID");
            session.clear_breakpoint(static_cast<std::uint8_t>(id));
            std::cout << "TARGET BREAKPOINT CLEARED " << id << "\n";
            return true;
        }
        if (command == "RUN" || command == "CONTINUE" || command == "GO") {
            if (running) throw ToolError("TARGET IS ALREADY RUNNING");
            session.run();
            running = true;
            std::cout << "TARGET RUNNING\n";
            return true;
        }
        if (command == "HALT" || command == "STOP") {
            session.halt();
            running = false;
            std::cout << "TARGET HALTED\n";
            print_live_registers(sidecar, session.read_registers());
            return true;
        }
        if (command == "STEP") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            session.step();
            print_live_registers(sidecar, session.read_registers());
            return true;
        }
        if (command == "WAIT") {
            if (words.size() > 2) throw ToolError("BAD LIVE WAIT COMMAND");
            const std::size_t timeout = words.size() == 2
                ? parse_object_size(words[1])
                : 1000;
            const auto event = session.receive_event(static_cast<int>(timeout));
            if (!event) {
                std::cout << "NO EVENT\n";
            } else {
                print_target_event(sidecar, *event);
                if (event->type == MessageType::Stopped ||
                    event->type == MessageType::BreakpointHit ||
                    event->type == MessageType::TargetExit ||
                    event->type == MessageType::TargetFault) {
                    running = false;
                }
            }
            return true;
        }
        if (command == "SAMPLING") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            if (words.size() != 2) throw ToolError("BAD LIVE SAMPLING COMMAND");
            const std::string state = upper_ascii(words[1]);
            if (state != "ON" && state != "OFF") {
                throw ToolError("BAD LIVE SAMPLING STATE");
            }
            session.configure_sampling(state == "ON");
            std::cout << "SAMPLING " << state << "\n";
            return true;
        }
        if (command == "SAMPLES") {
            if (running) throw ToolError("TARGET IS RUNNING; HALT FIRST");
            std::uint32_t interval = 0;
            const std::vector<std::uint16_t> samples = session.read_samples(&interval);
            std::cout << "SAMPLES " << samples.size()
                      << " INTERVAL_US " << interval << "\n";
            for (const std::uint16_t address : samples) {
                print_live_source(sidecar, address);
            }
            return true;
        }
        throw ToolError("BAD LIVE DEBUG COMMAND");
    };

    if (!initial_command.empty()) {
        execute(initial_command);
        if (running) {
            session.halt();
            running = false;
            std::cout << "TARGET HALTED ON CLIENT EXIT\n";
        }
        return 0;
    }

    print_live_debug_help();
    std::string line;
    while (true) {
        if (::isatty(STDIN_FILENO) != 0) {
            std::cout << "actdbg> " << std::flush;
        }
        if (!std::getline(std::cin, line)) break;
        try {
            if (!execute(split_words(line))) break;
        } catch (const ToolError& error) {
            std::cerr << error.what() << "\n";
        }
    }
    if (running) {
        try {
            session.halt();
        } catch (const ToolError&) {
        }
    }
    return 0;
}

int cmd_actdbg(const std::vector<std::string>& args) {
    if (args.size() == 1 && upper_ascii(args.front()) == "--PROTOCOL-SELFTEST") {
        using namespace action_linux::target;
        TargetSimulator simulator;
        const Packet hello{MessageType::Hello, 0, 7, {}};
        const Packet decoded = decode_packet(encode_packet(hello));
        if (decoded.type != MessageType::Hello || decoded.sequence != 7) {
            throw ToolError("TARGET PROTOCOL SELFTEST FAILED");
        }
        const std::vector<std::uint8_t> encoded_hello = encode_packet(hello);
        StreamDecoder stream;
        if (!stream.feed(encoded_hello.data(), 5).empty()) {
            throw ToolError("TARGET STREAM SELFTEST FAILED");
        }
        const std::vector<Packet> streamed = stream.feed(
            encoded_hello.data() + 5, encoded_hello.size() - 5);
        if (streamed.size() != 1 || streamed.front().sequence != 7) {
            throw ToolError("TARGET STREAM SELFTEST FAILED");
        }
        std::vector<std::uint8_t> corrupt = encoded_hello;
        corrupt.back() ^= 0x01;
        bool rejected = false;
        try {
            decode_packet(corrupt);
        } catch (const ToolError&) {
            rejected = true;
        }
        if (!rejected) {
            throw ToolError("TARGET CHECKSUM SELFTEST FAILED");
        }
        const Packet fuzz_source{
            MessageType::Ping,
            static_cast<std::uint8_t>(Response | Event),
            0xbeef,
            {0x00, 0x7f, 0x80, 0xff, 'I', 'D', 'B', 'G'},
        };
        const std::vector<std::uint8_t> fuzz_encoded = encode_packet(fuzz_source);
        for (std::size_t size = 0; size < fuzz_encoded.size(); ++size) {
            bool truncated_rejected = false;
            try {
                decode_packet(std::vector<std::uint8_t>(
                    fuzz_encoded.begin(),
                    fuzz_encoded.begin() + static_cast<std::ptrdiff_t>(size)));
            } catch (const ToolError&) {
                truncated_rejected = true;
            }
            if (!truncated_rejected) {
                throw ToolError("TARGET TRUNCATION SELFTEST FAILED");
            }
        }
        for (std::size_t index = 0; index < fuzz_encoded.size(); ++index) {
            std::vector<std::uint8_t> mutated = fuzz_encoded;
            mutated[index] ^= 0x5a;
            bool mutation_rejected = false;
            try {
                decode_packet(mutated);
            } catch (const ToolError&) {
                mutation_rejected = true;
            }
            if (!mutation_rejected) {
                throw ToolError("TARGET MUTATION SELFTEST FAILED");
            }
        }
        bool oversized_rejected = false;
        try {
            encode_packet(Packet{
                MessageType::Ping,
                0,
                1,
                std::vector<std::uint8_t>(kMaximumPayload + 1, 0xa5),
            });
        } catch (const ToolError&) {
            oversized_rejected = true;
        }
        if (!oversized_rejected) {
            throw ToolError("TARGET OVERSIZE SELFTEST FAILED");
        }
        StreamDecoder noisy_stream;
        const std::vector<std::uint8_t> noise = {
            0x00, 0xff, 'I', 'D', 0x00, 'I', 'D', 'B',
        };
        if (!noisy_stream.feed(noise).empty()) {
            throw ToolError("TARGET NOISE SELFTEST FAILED");
        }
        std::vector<Packet> recovered;
        for (const std::uint8_t value : fuzz_encoded) {
            std::vector<Packet> next = noisy_stream.feed(&value, 1);
            recovered.insert(recovered.end(), next.begin(), next.end());
        }
        if (recovered.size() != 1 || recovered.front().sequence != 0xbeef ||
            recovered.front().payload != fuzz_source.payload) {
            throw ToolError("TARGET STREAM RECOVERY SELFTEST FAILED");
        }
        // Exercise every message byte and short payload shape. This is a
        // deterministic protocol-parser fuzz pass and is run under ASan/UBSan.
        for (unsigned raw_type = 0; raw_type <= 0xff; ++raw_type) {
            TargetSimulator parser_simulator;
            for (std::size_t size = 0; size <= 32; ++size) {
                std::vector<std::uint8_t> payload(size);
                for (std::size_t index = 0; index < size; ++index) {
                    payload[index] = static_cast<std::uint8_t>(
                        raw_type * 17U + index * 29U);
                }
                parser_simulator.process(Packet{
                    static_cast<MessageType>(raw_type),
                    static_cast<std::uint8_t>(raw_type ^ size),
                    static_cast<std::uint16_t>((raw_type << 8) | size),
                    std::move(payload),
                });
            }
        }
        const Packet hello_response = simulator.process(decoded);
        if (hello_response.payload.empty() ||
            hello_response.payload.front() != static_cast<std::uint8_t>(Status::Ok)) {
            throw ToolError("TARGET SIMULATOR SELFTEST FAILED");
        }
        const Packet write_response = simulator.process(Packet{
            MessageType::WriteMemory,
            0,
            8,
            {0x00, 0x20, 0x03, 0xaa, 0xbb, 0xcc},
        });
        const Packet read_response = simulator.process(Packet{
            MessageType::ReadMemory,
            0,
            9,
            {0x00, 0x20, 0x03},
        });
        if (write_response.payload.empty() || read_response.payload !=
                std::vector<std::uint8_t>({0, 0xaa, 0xbb, 0xcc})) {
            throw ToolError("TARGET MEMORY SELFTEST FAILED");
        }
        const auto has_status = [](const Packet& packet, Status status) {
            return !packet.payload.empty() &&
                packet.payload.front() == static_cast<std::uint8_t>(status);
        };
        const Packet unsafe_write = simulator.process(Packet{
            MessageType::WriteMemory,
            0,
            10,
            {0xff, 0xcf, 0x02, 0x11, 0x22},
        });
        const Packet unsafe_low_break = simulator.process(Packet{
            MessageType::BreakSet, 0, 11, {0xff, 0x01},
        });
        const Packet unsafe_service_break = simulator.process(Packet{
            MessageType::BreakSet, 0, 12, {0x00, 0xc0},
        });
        const Packet unsafe_basic_break = simulator.process(Packet{
            MessageType::BreakSet, 0, 13, {0x00, 0xa0},
        });
        const Packet unsafe_io_break = simulator.process(Packet{
            MessageType::BreakSet, 0, 14, {0x00, 0xd0},
        });
        if (!has_status(unsafe_write, Status::UnsafeAddress) ||
            !has_status(unsafe_low_break, Status::UnsafeAddress) ||
            !has_status(unsafe_service_break, Status::UnsafeAddress) ||
            !has_status(unsafe_basic_break, Status::UnsafeAddress) ||
            !has_status(unsafe_io_break, Status::UnsafeAddress)) {
            throw ToolError("TARGET ADDRESS SAFETY SELFTEST FAILED");
        }
        simulator.process(Packet{MessageType::SampleConfig, 0, 10, {1}});
        simulator.record_sample(0x2000);
        simulator.record_sample(0x2001);
        const Packet sample_response = simulator.process(
            Packet{MessageType::SampleRead, 0, 11, {}});
        if (sample_response.payload.size() != 10 || sample_response.payload[1] != 2) {
            throw ToolError("TARGET SAMPLE SELFTEST FAILED");
        }
        std::cout << "TARGET PROTOCOL OK\n";
        return 0;
    }
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const std::string module = module_from_arg(args.front());
    const fs::path prg = binary_path(fs::current_path(), module);
    const fs::path dbg = debug_path(fs::current_path(), module);
    if (!fs::is_regular_file(prg)) {
        throw ToolError("NO PRG");
    }
    if (!fs::is_regular_file(dbg)) {
        throw ToolError("NO DBG");
    }
    std::ifstream in(prg, std::ios::binary | std::ios::ate);
    if (!in) {
        throw ToolError("LOAD FAIL");
    }
    const std::streamoff size = in.tellg();
    if (size < 3) {
        throw ToolError("BAD PRG");
    }
    in.seekg(0);
    const int lo = in.get();
    const int hi = in.get();
    const std::uint16_t load_address = static_cast<std::uint16_t>(lo | (hi << 8));
    const DebugSidecar sidecar = parse_debug_sidecar(dbg);

    if (args.size() >= 2) {
        const std::string mode = upper_ascii(args[1]);
        if (mode == "--LIVE" || mode == "LIVE") {
            std::vector<std::string> initial_command(
                args.begin() + 2, args.end());
            std::vector<std::string> program_arguments;
            if (!initial_command.empty() && initial_command.front() == "--") {
                program_arguments.assign(
                    initial_command.begin() + 1, initial_command.end());
                initial_command.clear();
            }
            return run_live_debugger(
                fs::current_path(),
                module,
                sidecar,
                initial_command,
                program_arguments);
        }
        if (mode == "--SYMBOLS" || mode == "SYMBOLS") {
            const std::string filter =
                args.size() >= 3 ? upper_ascii(args[2]) : std::string{};
            for (const DebugSymbolInfo& symbol : sidecar.symbols) {
                if (filter.empty() || symbol.name.find(filter) != std::string::npos) {
                    std::cout << "SYMBOL " << symbol.address << " "
                              << symbol.size << " " << symbol.name << "\n";
                }
            }
            return 0;
        }
        if ((mode == "--SOURCE" || mode == "SOURCE") && args.size() >= 3) {
            const std::uint16_t address = parse_debug_address(args[2]);
            auto location = debug_line_for_address(sidecar, address);
            if (!location) {
                throw ToolError("NO SOURCE LOCATION");
            }
            std::cout << "SOURCE " << location->address << " "
                      << debug_source_name(sidecar, location->module_id)
                      << ":" << location->line << "\n";
            return 0;
        }
        if ((mode == "--LINE" || mode == "LINE") && args.size() >= 3) {
            const std::size_t line = parse_object_size(args[2]);
            auto location = debug_line_for_source(sidecar, 0, line);
            if (!location) {
                throw ToolError("NO SOURCE LINE");
            }
            std::cout << "ADDRESS " << location->address << " "
                      << debug_source_name(sidecar, location->module_id)
                      << ":" << location->line << "\n";
            return 0;
        }
        if ((mode == "--BREAK" || mode == "BREAK") && args.size() >= 3) {
            const std::size_t line = parse_object_size(args[2]);
            auto location = debug_line_for_source(sidecar, 0, line);
            if (!location) {
                throw ToolError("NO SOURCE LINE");
            }
            store_breakpoint(
                fs::current_path(),
                module,
                debug_source_name(sidecar, location->module_id),
                *location);
            return 0;
        }
        if (mode == "--BREAKS" || mode == "BREAKS") {
            list_breakpoints(fs::current_path(), module);
            return 0;
        }
        if ((mode == "--CLEAR" || mode == "CLEAR") && args.size() >= 3) {
            clear_breakpoint(
                fs::current_path(),
                module,
                parse_object_size(args[2]));
            return 0;
        }
        throw ToolError("BAD DEBUG COMMAND");
    }

    std::cout << "ACTDBG INFO\n";
    std::cout << "MODULE " << module << "\n";
    std::cout << "PRG " << prg.generic_string() << "\n";
    std::cout << "LOAD " << load_address << "\n";
    std::cout << "SIZE " << (size - 2) << "\n";

    const auto lines = split_lines(read_text_file(dbg));
    for (const std::string& raw : lines) {
        const std::string line = trim(raw);
        if (line.empty() || upper_ascii(line) == "DBG1") {
            continue;
        }
        std::cout << line << "\n";
    }
    return 0;
}

void collect_tree_entries(const fs::path& root, const fs::path& current, std::vector<std::string>& entries) {
    std::vector<fs::directory_entry> children;
    for (const auto& entry : fs::directory_iterator(current)) {
        children.push_back(entry);
    }
    std::sort(children.begin(), children.end(), [](const auto& a, const auto& b) {
        return upper_ascii(a.path().filename().string()) < upper_ascii(b.path().filename().string());
    });
    for (const auto& entry : children) {
        const fs::path relative = fs::relative(entry.path(), root);
        entries.push_back(std::string(entry.is_directory() ? "D " : "F ") + relative.generic_string());
        if (entry.is_directory()) {
            collect_tree_entries(root, entry.path(), entries);
        }
    }
}

int cmd_acttree(const std::vector<std::string>& args) {
    const fs::path root = args.empty() ? fs::current_path() : fs::path(args.front());
    if (!fs::is_directory(root)) {
        throw ToolError("NO DIR");
    }
    std::vector<std::string> entries;
    collect_tree_entries(root, root, entries);
    for (const std::string& entry : entries) {
        std::cout << entry << "\n";
    }
    return 0;
}

int cmd_xcopy(const std::vector<std::string>& args) {
    if (args.size() < 2) {
        throw ToolError("BAD COPY");
    }
    if (!fs::exists(args[0])) {
        throw ToolError("NO SUCH FILE");
    }
    const fs::path source = normalized_absolute_path(args[0]);
    const fs::path destination = normalized_absolute_path(args[1]);
    if (fs::is_directory(source) &&
        path_is_same_or_descendant(source, destination)) {
        throw ToolError("COPY INTO SELF");
    }
    fs::copy(args[0], args[1], fs::copy_options::recursive | fs::copy_options::overwrite_existing);
    std::cout << "XCOPY OK\n";
    return 0;
}

int cmd_deltree(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    if (!fs::exists(args.front())) {
        throw ToolError("NO SUCH FILE");
    }
    const fs::path target = normalized_absolute_path(args.front());
    if (!fs::is_symlink(fs::symlink_status(args.front()))) {
        const fs::path cwd = normalized_absolute_path(fs::current_path());
        if (target == target.root_path() ||
            path_is_same_or_descendant(target, cwd)) {
            throw ToolError("REFUSE DANGEROUS DELETE");
        }
    }
    fs::remove_all(args.front());
    std::cout << "DELTREE OK\n";
    return 0;
}

std::optional<fs::path> existing_file_case_insensitive(fs::path candidate) {
    const auto find_one = [](const fs::path& path) -> std::optional<fs::path> {
        if (fs::is_regular_file(path)) {
            return normalized_absolute_path(path);
        }
        const fs::path parent = path.parent_path();
        const auto found =
            child_case_insensitive(parent, path.filename().string());
        if (found && fs::is_regular_file(*found)) {
            return normalized_absolute_path(*found);
        }
        return std::nullopt;
    };
    if (candidate.is_absolute()) {
        return find_one(candidate);
    }
    if (const auto invoked = find_one(g_invocation_cwd / candidate)) {
        return invoked;
    }
    if (fs::current_path() != g_invocation_cwd) {
        return find_one(fs::current_path() / candidate);
    }
    return std::nullopt;
}

std::optional<fs::path> direct_actedit_source(std::string_view argument) {
    std::string text = trim(argument);
    for (char& ch : text) {
        if (ch == '\\') {
            ch = '/';
        }
    }
    fs::path candidate(text);
    if (const auto exact = existing_file_case_insensitive(candidate)) {
        return exact;
    }
    if (candidate.extension().empty()) {
        candidate += ".ACT";
        return existing_file_case_insensitive(candidate);
    }
    return std::nullopt;
}

struct ActeditTarget {
    fs::path path;
    fs::path project_root;
    std::string module;
    bool project_source = false;
};

ActeditTarget resolve_actedit_target(std::string_view argument) {
    const std::string module = module_from_arg(argument);
    if (const auto direct = direct_actedit_source(argument)) {
        const auto discovered_root = find_project_root_from(direct->parent_path());
        const fs::path root = discovered_root.value_or(direct->parent_path());
        bool project_source = false;
        if (discovered_root) {
            try {
                project_source =
                    manifest_contains_module(load_manifest_entries(root), module) &&
                    normalized_absolute_path(source_path(root, module)) == *direct;
            } catch (const ToolError&) {
                project_source = false;
            }
        }
        return ActeditTarget{*direct, root, module, project_source};
    }

    const fs::path root = fs::current_path();
    require_project_module(root, module);
    return ActeditTarget{source_path(root, module), root, module, true};
}

void require_actedit_project_source(const ActeditTarget& target) {
    if (!target.project_source) {
        throw ToolError("NOT PROJECT SOURCE");
    }
}

int cmd_actedit(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const ActeditTarget target = resolve_actedit_target(args.front());
    const std::string& module = target.module;
    const fs::path& path = target.path;
    const fs::path& root = target.project_root;
    if (target.project_source) {
        fs::current_path(root);
    }
    std::vector<std::string> lines = read_source_lines(path);

    if (args.size() == 1) {
        if (action_linux::editor_terminal_available()) {
            const int status = action_linux::run_terminal_editor(
                path, module, root, false);
            if (status == 0) {
                std::cout << "ACTEDIT OK\n";
            }
            return status;
        }
        std::cout << read_text_file(path);
        return 0;
    }

    const std::string mode = upper_ascii(args[1]);
    if (mode == "--TUI" || mode == "TUI") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        const int status = action_linux::run_terminal_editor(
            path, module, root, true);
        if (status == 0) {
            std::cout << "ACTEDIT OK\n";
        }
        return status;
    }
    if (mode == "--HIGHLIGHT" || mode == "HIGHLIGHT") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        action_linux::print_highlighted_source(read_text_file(path), std::cout);
        return 0;
    }
    if (mode == "--INDEX" || mode == "INDEX") {
        require_actedit_project_source(target);
        rebuild_source_index(root);
        std::cout << "ACTEDIT INDEXED\n";
        return 0;
    }
    if ((mode == "--FIND" || mode == "FIND") && args.size() >= 3) {
        std::string query;
        for (std::size_t i = 2; i < args.size(); ++i) {
            if (!query.empty()) {
                query.push_back(' ');
            }
            query += args[i];
        }
        require_actedit_project_source(target);
        print_source_matches(root, query);
        return 0;
    }
    if (mode == "--SYMBOLS" || mode == "SYMBOLS") {
        require_actedit_project_source(target);
        print_source_symbols(root, module);
        return 0;
    }
    if (mode == "--MAP" || mode == "MAP") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        print_code_map_summary(root);
        return 0;
    }
    if ((mode == "--DEFINITION" || mode == "DEFINITION" ||
         mode == "--GOTO" || mode == "GOTO") && args.size() == 3) {
        print_code_map_definition(root, args[2]);
        return 0;
    }
    if ((mode == "--REFERENCES" || mode == "REFERENCES") &&
        args.size() == 3) {
        print_code_map_references(root, args[2]);
        return 0;
    }
    if (mode == "--PRINT" || mode == "PRINT") {
        std::cout << read_text_file(path);
        return 0;
    }
    if (mode == "--COMPILE" || mode == "COMPILE") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        return cmd_actc({module});
    }
    if (mode == "--BUILD" || mode == "BUILD") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        return compile_and_link_module(module);
    }
    if (mode == "--DEBUG" || mode == "DEBUG") {
        if (args.size() != 2) {
            throw ToolError("BAD EDIT");
        }
        const int status = compile_and_link_module(module);
        return status == 0 ? cmd_actdbg({module}) : status;
    }
    if ((mode == "--APPEND" || mode == "APPEND") && args.size() >= 3) {
        lines.push_back(args[2]);
        write_text_file(path, join_lines(lines));
        std::cout << "ACTEDIT OK\n";
        return 0;
    }
    if ((mode == "--INSERT" || mode == "INSERT") && args.size() >= 4) {
        const std::size_t index = parse_one_based_line(args[2], lines.size() + 1);
        lines.insert(lines.begin() + static_cast<std::ptrdiff_t>(index), args[3]);
        write_text_file(path, join_lines(lines));
        std::cout << "ACTEDIT OK\n";
        return 0;
    }
    if ((mode == "--REPLACE" || mode == "REPLACE") && args.size() >= 4) {
        const std::size_t index = parse_one_based_line(args[2], lines.size());
        lines[index] = args[3];
        write_text_file(path, join_lines(lines));
        std::cout << "ACTEDIT OK\n";
        return 0;
    }
    if ((mode == "--DELETE" || mode == "DELETE") && args.size() >= 3) {
        const std::size_t index = parse_one_based_line(args[2], lines.size());
        lines.erase(lines.begin() + static_cast<std::ptrdiff_t>(index));
        write_text_file(path, join_lines(lines));
        std::cout << "ACTEDIT OK\n";
        return 0;
    }
    throw ToolError("BAD EDIT");
}

int cmd_act2save(const std::vector<std::string>& args) {
    const std::vector<std::string> link_args = args.empty() ? std::vector<std::string>{"MAIN"} : args;
    int status = cmd_alink(link_args);
    if (status == 0) {
        std::cout << "ACT2SAVE OK\n";
    }
    return status;
}

void append_unique_directory(
    std::vector<fs::path>& directories,
    const fs::path& candidate) {
    std::error_code error;
    if (!fs::is_directory(candidate, error) || error) {
        return;
    }
    const fs::path canonical = fs::weakly_canonical(candidate, error);
    const fs::path normalized = error ? candidate.lexically_normal() : canonical;
    if (std::find(directories.begin(), directories.end(), normalized) ==
        directories.end()) {
        directories.push_back(normalized);
    }
}

std::vector<fs::path> library_search_directories(const fs::path& root) {
    std::vector<fs::path> directories;
    append_unique_directory(directories, project_dir(root, "LIB"));
    if (const auto project = find_project_root_from(root);
        project && *project != root) {
        append_unique_directory(directories, project_dir(*project, "LIB"));
    }
    const fs::path parent = root.parent_path();
    if (!parent.empty() && parent != root) {
        append_unique_directory(directories, project_dir(parent, "LIB"));
    }

    const char* configured = std::getenv("ACTION_LIB");
    if (configured != nullptr && *configured != '\0') {
        std::string paths(configured);
        std::size_t begin = 0;
        while (begin <= paths.size()) {
            const std::size_t end = paths.find(':', begin);
            fs::path candidate(paths.substr(
                begin,
                end == std::string::npos ? std::string::npos : end - begin));
            if (candidate.is_relative()) {
                candidate = g_invocation_cwd / candidate;
            }
            append_unique_directory(directories, candidate);
            if (end == std::string::npos) {
                break;
            }
            begin = end + 1;
        }
    }

    const fs::path executable = action_linux::program_path();
    if (!executable.empty()) {
        const fs::path tools_dir = executable.parent_path();
        const fs::path workspace = tools_dir.parent_path();
        append_unique_directory(directories, project_dir(workspace, "LIB"));
        const fs::path source_root = workspace.parent_path();
        if (!source_root.empty()) {
            append_unique_directory(directories, project_dir(source_root, "LIB"));
            append_unique_directory(
                directories,
                source_root / "src" / "runtime" / "modules");
        }
    }
    return directories;
}

class ActionSourcePreprocessor {
public:
    explicit ActionSourcePreprocessor(fs::path project_root)
        : project_root_(fs::weakly_canonical(std::move(project_root))) {
        for (const fs::path& directory :
             library_search_directories(project_root_)) {
            library_directories_.push_back(fs::weakly_canonical(directory));
        }
    }

    std::string process(const fs::path& source) {
        return process_file(fs::weakly_canonical(source));
    }

    const std::set<std::string>& project_routine_names() const {
        return project_routine_names_;
    }

private:
    static bool starts_with_word(std::string_view text, std::string_view word) {
        const std::string cleaned = trim(text);
        const std::string upper = upper_ascii(cleaned);
        const std::string wanted = upper_ascii(word);
        return upper == wanted ||
               (upper.size() > wanted.size() &&
                upper.compare(0, wanted.size(), wanted) == 0 &&
                std::isspace(static_cast<unsigned char>(upper[wanted.size()])));
    }

    static std::optional<fs::path> find_relative_case_insensitive(
        const fs::path& root,
        const fs::path& relative) {
        fs::path current = root;
        for (const fs::path& component : relative) {
            const std::string name = component.string();
            if (name.empty() || name == ".") {
                continue;
            }
            auto child = child_case_insensitive(current, name);
            if (!child) {
                return std::nullopt;
            }
            current = *child;
        }
        return current;
    }

    fs::path resolve_include(const fs::path& including_file, std::string spec) const {
        for (char& ch : spec) {
            if (ch == '\\') {
                ch = '/';
            }
        }
        const std::size_t device = spec.find(':');
        if (device != std::string::npos) {
            spec = spec.substr(device + 1);
        }
        const fs::path relative = fs::path(trim(spec)).lexically_normal();
        if (relative.empty() || relative.is_absolute()) {
            throw ToolError("BAD INCLUDE PATH");
        }
        for (const fs::path& component : relative) {
            if (component == "..") {
                throw ToolError("BAD INCLUDE PATH");
            }
        }

        std::vector<fs::path> names{relative};
        if (!relative.has_extension()) {
            fs::path with_extension = relative;
            with_extension += ".ACT";
            names.push_back(std::move(with_extension));
        }
        std::vector<fs::path> roots;
        append_unique_directory(roots, including_file.parent_path());
        append_unique_directory(roots, project_root_);
        append_unique_directory(roots, project_dir(project_root_, "SRC"));
        for (const fs::path& directory :
             library_search_directories(project_root_)) {
            append_unique_directory(roots, directory);
        }
        for (const fs::path& root : roots) {
            for (const fs::path& name : names) {
                auto found = find_relative_case_insensitive(root, name);
                if (found && fs::is_regular_file(*found)) {
                    return fs::weakly_canonical(*found);
                }
            }
        }
        throw ToolError("INCLUDE NOT FOUND: " + relative.generic_string());
    }

    void parse_define(std::string_view source_line) {
        const std::string line = trim(strip_source_comment(source_line));
        if (!starts_with_word(line, "DEFINE")) {
            throw ToolError("BAD DEFINE");
        }
        const std::string body = trim(std::string_view(line).substr(6));
        if (body.empty()) {
            throw ToolError("BAD DEFINE");
        }
        for (const std::string& item : split_declarators(body)) {
            const std::size_t equals = item.find('=');
            if (equals == std::string::npos) {
                throw ToolError("BAD DEFINE");
            }
            const std::string name = trim(std::string_view(item).substr(0, equals));
            const std::string encoded = trim(std::string_view(item).substr(equals + 1));
            if (name.empty() ||
                name.find_first_not_of(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                    std::string::npos ||
                std::isdigit(static_cast<unsigned char>(name.front())) ||
                encoded.empty()) {
                throw ToolError("BAD DEFINE");
            }
            std::string value;
            if (encoded.size() >= 2 && encoded.front() == '"' &&
                encoded.back() == '"') {
                for (std::size_t i = 1; i + 1 < encoded.size(); ++i) {
                    if (encoded[i] == '\\' && i + 2 < encoded.size() &&
                        (encoded[i + 1] == '\\' || encoded[i + 1] == '"')) {
                        value.push_back(encoded[++i]);
                    } else {
                        value.push_back(encoded[i]);
                    }
                }
            } else if (encoded.find('"') != std::string::npos) {
                throw ToolError("BAD DEFINE");
            } else {
                value = encoded;
            }
            defines_[upper_ascii(name)] = std::move(value);
        }
    }

    std::string substitute_defines(std::string line) const {
        for (int pass = 0; pass < 64; ++pass) {
            std::string expanded;
            bool changed = false;
            for (std::size_t i = 0; i < line.size();) {
                const char ch = line[i];
                if (ch == ';') {
                    expanded.append(line.substr(i));
                    i = line.size();
                    break;
                }
                if (ch == '"') {
                    const std::size_t start = i++;
                    bool escaped = false;
                    while (i < line.size()) {
                        const char string_ch = line[i++];
                        if (string_ch == '"' && !escaped) {
                            break;
                        }
                        escaped = string_ch == '\\' && !escaped;
                        if (string_ch != '\\') {
                            escaped = false;
                        }
                    }
                    expanded.append(line.substr(start, i - start));
                    continue;
                }
                if (ch == '\'') {
                    expanded.push_back(line[i++]);
                    if (i < line.size()) {
                        expanded.push_back(line[i++]);
                        if (expanded.back() == '\\' && i < line.size()) {
                            expanded.push_back(line[i++]);
                        }
                        if (i < line.size() && line[i] == '\'') {
                            expanded.push_back(line[i++]);
                        }
                    }
                    continue;
                }
                if (!std::isalpha(static_cast<unsigned char>(ch)) && ch != '_') {
                    expanded.push_back(ch);
                    ++i;
                    continue;
                }
                const std::size_t start = i++;
                while (i < line.size() &&
                       (std::isalnum(static_cast<unsigned char>(line[i])) || line[i] == '_')) {
                    ++i;
                }
                const std::string token = line.substr(start, i - start);
                auto replacement = defines_.find(upper_ascii(token));
                if (replacement == defines_.end()) {
                    expanded += token;
                } else {
                    expanded += replacement->second;
                    changed = true;
                }
            }
            if (!changed) {
                return expanded;
            }
            if (expanded == line) {
                throw ToolError("DEFINE CYCLE");
            }
            line = std::move(expanded);
        }
        throw ToolError("DEFINE EXPANSION LIMIT");
    }

    bool is_library_source(const fs::path& source) const {
        for (const fs::path& directory : library_directories_) {
            const fs::path relative = source.lexically_relative(directory);
            if (relative.empty() || relative.is_absolute()) {
                continue;
            }
            if (*relative.begin() != "..") {
                return true;
            }
        }
        return false;
    }

    void record_project_routine(
        const fs::path& source,
        const std::string& source_line) {
        if (is_library_source(source)) {
            return;
        }
        static const std::regex procedure_declaration(
            R"(^\s*(?:PROC|OVERLAY)\s+([A-Za-z_][A-Za-z0-9_]*))",
            std::regex_constants::icase);
        static const std::regex function_declaration(
            R"(^\s*(?:BYTE|CHAR|CARD|INT|REAL)\s+FUNC\s+([A-Za-z_][A-Za-z0-9_]*))",
            std::regex_constants::icase);
        const std::string line = strip_source_comment(source_line);
        std::smatch match;
        if ((std::regex_search(line, match, procedure_declaration) ||
             std::regex_search(line, match, function_declaration)) &&
            match.position() == 0) {
            project_routine_names_.insert(module_from_arg(match[1].str()));
        }
    }

    void process_line(
        const fs::path& source,
        const std::string& source_line,
        std::string& output) {
        const std::string cleaned = trim(strip_source_comment(source_line));
        if (cleaned.empty()) {
            output += source_line + "\n";
            return;
        }
        if (starts_with_word(cleaned, "DEFINE")) {
            parse_define(cleaned);
            output.push_back('\n');
            return;
        }
        if (starts_with_word(cleaned, "INCLUDE")) {
            static const std::regex include_line(
                R"ACT(^\s*INCLUDE\s+"([^"]+)"\s*$)ACT",
                std::regex_constants::icase);
            std::smatch match;
            if (!std::regex_match(cleaned, match, include_line)) {
                throw ToolError("BAD INCLUDE");
            }
            output += process_file(resolve_include(source, match[1].str()));
            return;
        }
        if (starts_with_word(cleaned, "SET")) {
            const std::string assignment = trim(std::string_view(cleaned).substr(3));
            const std::size_t equals = assignment.find('=');
            if (equals == std::string::npos ||
                trim(std::string_view(assignment).substr(0, equals)).empty() ||
                trim(std::string_view(assignment).substr(equals + 1)).empty()) {
                throw ToolError("BAD SET");
            }
            output.push_back('\n');
            return;
        }
        output += source_line + "\n";
    }

    std::string process_file(const fs::path& source) {
        if (include_stack_.size() >= 32) {
            throw ToolError("INCLUDE DEPTH");
        }
        if (std::find(include_stack_.begin(), include_stack_.end(), source) !=
            include_stack_.end()) {
            throw ToolError("INCLUDE CYCLE: " + source.filename().string());
        }
        include_stack_.push_back(source);
        const std::vector<std::string> lines = split_lines(read_text_file(source));
        std::string output;
        for (std::size_t i = 0; i < lines.size(); ++i) {
            std::string line = lines[i];
            const std::string cleaned = trim(strip_source_comment(line));
            if (starts_with_word(cleaned, "DEFINE")) {
                while (!trim(strip_source_comment(line)).empty() &&
                       trim(strip_source_comment(line)).back() == ',') {
                    if (++i >= lines.size()) {
                        throw ToolError("BAD DEFINE");
                    }
                    line += " " + trim(strip_source_comment(lines[i]));
                }
                process_line(source, line, output);
                continue;
            }
            const std::string expanded = substitute_defines(line);
            const std::vector<std::string> expanded_lines = split_lines(expanded);
            for (const std::string& expanded_line : expanded_lines) {
                record_project_routine(source, expanded_line);
                process_line(source, expanded_line, output);
            }
        }
        include_stack_.pop_back();
        return output;
    }

    fs::path project_root_;
    std::vector<fs::path> library_directories_;
    std::set<std::string> project_routine_names_;
    std::map<std::string, std::string> defines_;
    std::vector<fs::path> include_stack_;
};

std::vector<std::uint8_t> read_binary_resource(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ToolError("RESOURCE LOAD FAIL: " + path.generic_string());
    }
    return std::vector<std::uint8_t>(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

fs::path resolve_graphics_resource(
    const fs::path& project_root,
    const fs::path& source,
    const std::string& specification) {
    fs::path relative(specification);
    if (relative.empty() || relative.is_absolute()) {
        throw ToolError("BAD RESOURCE PATH: " + specification);
    }
    for (const fs::path& component : relative) {
        if (component == "..") {
            throw ToolError("BAD RESOURCE PATH: " + specification);
        }
    }
    for (const fs::path& root : {
             source.parent_path(),
             project_dir(project_root, "RES"),
             project_root,
         }) {
        fs::path candidate = root;
        bool found_all = true;
        for (const fs::path& component : relative) {
            const std::string name = component.string();
            if (name.empty() || name == ".") {
                continue;
            }
            const auto child = child_case_insensitive(candidate, name);
            if (!child) {
                found_all = false;
                break;
            }
            candidate = *child;
        }
        if (found_all) {
            std::error_code error;
            if (fs::is_regular_file(candidate, error) && !error) {
                return fs::weakly_canonical(candidate);
            }
        }
    }
    throw ToolError("RESOURCE NOT FOUND: " + specification);
}

std::uint16_t resource_word(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    if (offset + 1 >= bytes.size()) {
        throw ToolError("BAD GRAPHICS RESOURCE");
    }
    return static_cast<std::uint16_t>(
        bytes[offset] | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8));
}

std::vector<std::uint8_t> compiled_graphics_resource(
    std::string_view declaration_type,
    const fs::path& path,
    std::size_t line) {
    const std::string type = upper_ascii(declaration_type);
    const std::vector<std::uint8_t> source = read_binary_resource(path);
    const auto bad = [&](std::string_view reason) -> ToolError {
        return ToolError(
            "BAD " + type + " RESOURCE LINE " + std::to_string(line) +
            ": " + std::string(reason));
    };

    if (type == "SPRITE_RESOURCE" || type == "MSPRITE_RESOURCE") {
        const bool multicolor = type == "MSPRITE_RESOURCE";
        std::vector<std::uint8_t> result(64, 0);
        if (source.size() == 71 &&
            std::equal(source.begin(), source.begin() + 4, "ASP1")) {
            if ((source[4] != 0) != multicolor) {
                throw bad("MODE DOES NOT MATCH DECLARATION");
            }
            if (source[5] > 15 || source[6] > 15 || source[7] > 15) {
                throw bad("COLOR RANGE");
            }
            std::copy(source.begin() + 8, source.end(), result.begin());
            result[63] = static_cast<std::uint8_t>(
                (multicolor ? 0x80 : 0x00) | source[5]);
            return result;
        }
        if (source.size() != 63 && source.size() != 64) {
            throw bad("EXPECTED ASP1, 63, OR 64 BYTES");
        }
        std::copy(source.begin(), source.begin() + 63, result.begin());
        const std::uint8_t default_color =
            source.size() == 64 ? source[63] & 0x0F : 1;
        result[63] = static_cast<std::uint8_t>(
            (multicolor ? 0x80 : 0x00) | default_color);
        return result;
    }

    if (type != "BITMAP_RESOURCE" && type != "MBITMAP_RESOURCE") {
        throw bad("UNKNOWN TYPE");
    }
    if (source.size() < 16 ||
        !std::equal(source.begin(), source.begin() + 4, "ABM1")) {
        throw bad("EXPECTED ABM1 HEADER");
    }
    const bool multicolor = type == "MBITMAP_RESOURCE";
    if ((source[4] != 0) != multicolor) {
        throw bad("MODE DOES NOT MATCH DECLARATION");
    }
    if (source[5] > 15 || source[6] > 15) {
        throw bad("COLOR RANGE");
    }
    const std::uint16_t width = resource_word(source, 8);
    const std::uint16_t height = resource_word(source, 10);
    const std::uint16_t stride = resource_word(source, 12);
    const std::uint16_t payload = resource_word(source, 14);
    const std::uint16_t maximum_width = multicolor ? 160 : 320;
    const std::size_t expected_stride =
        (static_cast<std::size_t>(width) * (multicolor ? 2U : 1U) + 7U) / 8U;
    const std::size_t expected_payload = expected_stride * height;
    if (width == 0 || width > maximum_width || height == 0 || height > 200 ||
        stride != expected_stride || payload != expected_payload ||
        source.size() != 16 + expected_payload) {
        throw bad("INVALID DIMENSIONS OR PAYLOAD");
    }
    return source;
}

int cmd_actc(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const std::string module = module_from_arg(args.front());
    require_project_module(fs::current_path(), module);
    const fs::path src = source_path(fs::current_path(), module);
    if (!fs::is_regular_file(src)) {
        throw ToolError("NO FILE");
    }

    ActionSourcePreprocessor preprocessor(fs::current_path());
    ParsedSource source = parse_source(preprocessor.process(src));
    std::vector<SourceProc>& procs = source.procs;
    auto main_it = std::find_if(procs.begin(), procs.end(), [](const SourceProc& proc) {
        return upper_ascii(proc.name) == "MAIN" && !proc.declaration_only;
    });
    if (main_it == procs.end()) {
        throw ToolError("NO MAIN");
    }
    if (!main_it->return_type.empty()) {
        throw ToolError("MAIN MUST BE PROC LINE " + std::to_string(main_it->line));
    }

    std::vector<SourceProc> ordered;
    ordered.push_back(*main_it);
    for (const SourceProc& proc : procs) {
        if (upper_ascii(proc.name) != "MAIN" && !proc.declaration_only) {
            ordered.push_back(proc);
        }
    }

    std::set<std::string> local_names;
    std::set<std::string> overlay_names;
    std::set<std::string> machine_code_names;
    for (const SourceProc& proc : ordered) {
        const std::string name = upper_ascii(proc.name);
        if (!local_names.insert(name).second) {
            throw ToolError(
                "DUPLICATE PROC LINE " + std::to_string(proc.line) + ": " + name);
        }
        if (proc.is_overlay) {
            overlay_names.insert(name);
        }
        if (trim(proc.address_expression) == "*" &&
            std::any_of(proc.ops.begin(), proc.ops.end(), [](const SourceOp& op) {
                return op.kind == SourceOp::Kind::Code ||
                    op.kind == SourceOp::Kind::AsmBlock;
            })) {
            machine_code_names.insert(name);
        }
    }

    auto local_calls_in_text = [&](std::string_view text) {
        std::set<std::string> calls;
        bool in_string = false;
        bool escaped = false;
        for (std::size_t i = 0; i < text.size();) {
            const unsigned char ch = static_cast<unsigned char>(text[i]);
            if (in_string) {
                if (escaped) {
                    escaped = false;
                } else if (ch == '\\') {
                    escaped = true;
                } else if (ch == '"') {
                    in_string = false;
                }
                ++i;
                continue;
            }
            if (ch == '"') {
                in_string = true;
                ++i;
                continue;
            }
            if (!std::isalpha(ch) && ch != '_') {
                ++i;
                continue;
            }
            const std::size_t start = i++;
            while (i < text.size()) {
                const unsigned char tail = static_cast<unsigned char>(text[i]);
                if (!std::isalnum(tail) && tail != '_') {
                    break;
                }
                ++i;
            }
            const std::string name = upper_ascii(text.substr(start, i - start));
            // Routine values and OverlayCall targets are references even when
            // they are not followed by a source-level call parenthesis.
            if (local_names.count(name) != 0) {
                calls.insert(name);
            }
        }
        return calls;
    };

    std::map<std::string, std::set<std::string>> local_call_graph;
    for (const SourceProc& proc : ordered) {
        const std::string caller = upper_ascii(proc.name);
        std::set<std::string>& calls = local_call_graph[caller];
        for (const SourceOp& op : proc.ops) {
            if (op.kind == SourceOp::Kind::Call) {
                const std::string direct = upper_ascii(op.value);
                if (local_names.count(direct) != 0) {
                    calls.insert(direct);
                }
            }
            for (const std::string* text : {
                     &op.value,
                     &op.aux,
                     &op.expression,
                     &op.size_expression,
                 }) {
                const std::set<std::string> nested = local_calls_in_text(*text);
                calls.insert(nested.begin(), nested.end());
            }
        }
    }

    auto graph_reaches = [&](const std::string& start, const std::string& wanted) {
        std::vector<std::string> pending{start};
        std::set<std::string> visited;
        while (!pending.empty()) {
            const std::string current = pending.back();
            pending.pop_back();
            if (current == wanted) {
                return true;
            }
            if (!visited.insert(current).second) {
                continue;
            }
            auto edges = local_call_graph.find(current);
            if (edges != local_call_graph.end()) {
                pending.insert(
                    pending.end(), edges->second.begin(), edges->second.end());
            }
        }
        return false;
    };

    std::set<std::pair<std::string, std::string>> reentrant_call_edges;
    for (const auto& caller : local_call_graph) {
        for (const std::string& target : caller.second) {
            if (graph_reaches(target, caller.first)) {
                reentrant_call_edges.emplace(caller.first, target);
            }
        }
    }

    std::set<std::string> reachable_routines =
        preprocessor.project_routine_names();
    reachable_routines.insert("MAIN");
    auto add_root_references = [&](std::string_view text) {
        const std::set<std::string> references = local_calls_in_text(text);
        reachable_routines.insert(references.begin(), references.end());
    };
    for (const SourceConstant& constant : source.constants) {
        add_root_references(constant.expression);
    }
    for (const SourceGlobal& global : source.globals) {
        add_root_references(global.expression);
        add_root_references(global.size_expression);
    }
    for (const SourceProc& proc : source.procs) {
        if (proc.declaration_only) {
            add_root_references(proc.address_expression);
        }
    }
    std::vector<std::string> pending_reachable(
        reachable_routines.begin(), reachable_routines.end());
    while (!pending_reachable.empty()) {
        const std::string current = pending_reachable.back();
        pending_reachable.pop_back();
        auto edges = local_call_graph.find(current);
        if (edges == local_call_graph.end()) {
            continue;
        }
        for (const std::string& target : edges->second) {
            if (reachable_routines.insert(target).second) {
                pending_reachable.push_back(target);
            }
        }
    }
    ordered.erase(
        std::remove_if(
            ordered.begin(), ordered.end(), [&](const SourceProc& proc) {
                return reachable_routines.count(upper_ascii(proc.name)) == 0;
            }),
        ordered.end());

    std::vector<ObjExport> exports;
    std::vector<std::string> imports;
    std::map<std::string, int> import_index;
    std::vector<ObjReloc> relocs;
    std::vector<ObjLineRecord> source_lines;
    std::vector<std::uint8_t> code;
    std::vector<VarSlot> data_slots;
    std::vector<ExprTempSlot> expr_temp_slots;
    std::vector<RealSlot> real_slots;
    std::vector<ArraySlot> array_slots;
    std::vector<AddressConstantSlot> address_constant_slots;
    std::set<std::string> data_symbols;
    std::size_t next_expr_temp = 0;
    std::size_t next_real_temp = 0;
    std::size_t next_string_literal = 0;
    std::size_t next_address_constant = 0;
    std::size_t next_control_label = 0;

    std::map<std::string, ExprValue> global_constants = builtin_integer_constants();
    std::map<std::string, ActionWordType> global_constant_types;
    std::map<std::string, double> real_constants;
    for (const auto& constant : global_constants) {
        real_constants.emplace(constant.first, static_cast<double>(constant.second));
        global_constant_types.emplace(
            constant.first, action_literal_type(constant.second));
    }
    std::set<std::string> source_constant_names;
    for (const SourceConstant& declaration : source.constants) {
        const std::string name = upper_ascii(declaration.name);
        if (!source_constant_names.insert(name).second) {
            throw ToolError(
                "DUPLICATE CONST LINE " + std::to_string(declaration.line) + ": " + name);
        }
        const std::string type = upper_ascii(declaration.type);
        if (type == "REAL") {
            if (global_constants.count(name) != 0 || real_constants.count(name) != 0) {
                throw ToolError(
                    "CONST REDEFINES BUILTIN LINE " + std::to_string(declaration.line) +
                    ": " + name);
            }
            auto value = try_eval_const_real_expr(declaration.expression, real_constants);
            if (!value) {
                throw ToolError(
                    "BAD REAL CONST LINE " + std::to_string(declaration.line) + ": " + name);
            }
            real_constants.emplace(name, *value);
            continue;
        }
        const ExprValue value = eval_const_expr(declaration.expression, global_constants);
        const ExprValue minimum = type == "INT" ? -32768 : 0;
        const ExprValue maximum = type == "BYTE" ? 0xFF : (type == "INT" ? 32767 : 0xFFFF);
        if ((type != "BYTE" && type != "CARD" && type != "INT") ||
            value < minimum || value > maximum) {
            throw ToolError(
                "CONST RANGE LINE " + std::to_string(declaration.line) + ": " + name);
        }
        auto existing = global_constants.find(name);
        if (existing != global_constants.end() && existing->second != value) {
            throw ToolError(
                "CONST REDEFINES BUILTIN LINE " + std::to_string(declaration.line) +
                ": " + name);
        }
        global_constants[name] = value;
        global_constant_types[name] = type == "BYTE"
            ? ActionWordType::Byte
            : type == "INT" ? ActionWordType::Int : ActionWordType::Card;
        real_constants[name] = static_cast<double>(value);
    }
    std::map<std::string, SourceRecordType> record_types;
    for (const SourceRecordType& record : source.record_types) {
        record_types.emplace(upper_ascii(record.name), record);
    }
    struct ExternalRoutine {
        std::optional<std::uint16_t> absolute_address;
        std::string linked_address_symbol;
        std::int32_t linked_address_addend = 0;
        std::vector<SourceParameter> parameters;
        std::string return_type;
    };
    std::map<std::string, ExternalRoutine> external_routines;
    for (const SourceProc& proc : source.procs) {
        if (proc.address_expression.empty() || trim(proc.address_expression) == "*") {
            continue;
        }
        if (!proc.declaration_only) {
            throw ToolError(
                "FIXED ROUTINE BODY LINE " + std::to_string(proc.line) + ": " +
                upper_ascii(proc.name));
        }
        std::optional<ExprValue> absolute =
            try_eval_const_expr(proc.address_expression, global_constants);
        std::string linked_symbol;
        std::int32_t linked_addend = 0;
        if (!absolute) {
            const std::string expression = trim(proc.address_expression);
            const std::size_t plus = expression.find('+');
            const std::string lhs = trim(std::string_view(expression).substr(0, plus));
            const std::string rhs = plus == std::string::npos
                ? std::string{}
                : trim(std::string_view(expression).substr(plus + 1));
            auto use_linked_routine = [&](std::string_view name,
                                          std::string_view addend_text) {
                const std::string target = upper_ascii(trim(name));
                if (local_names.count(target) == 0) {
                    return false;
                }
                ExprValue addend = 0;
                if (!trim(addend_text).empty()) {
                    auto value = try_eval_const_expr(addend_text, global_constants);
                    if (!value ||
                        *value < std::numeric_limits<std::int32_t>::min() ||
                        *value > std::numeric_limits<std::int32_t>::max()) {
                        return false;
                    }
                    addend = *value;
                }
                linked_symbol = target;
                linked_addend = static_cast<std::int32_t>(addend);
                return true;
            };
            bool resolved = use_linked_routine(lhs, rhs);
            if (!resolved && plus != std::string::npos) {
                resolved = use_linked_routine(rhs, lhs);
            }
            if (!resolved) {
                throw ToolError(
                    "UNKNOWN ROUTINE ADDRESS LINE " + std::to_string(proc.line) +
                    ": " + proc.address_expression);
            }
        }
        if (absolute && (*absolute < 0 || *absolute > 0xFFFF)) {
            throw ToolError(
                "ROUTINE ADDRESS RANGE LINE " + std::to_string(proc.line) + ": " +
                upper_ascii(proc.name));
        }
        if (!external_routines.emplace(
                upper_ascii(proc.name),
                ExternalRoutine{
                    absolute
                        ? std::optional<std::uint16_t>(
                              static_cast<std::uint16_t>(*absolute))
                        : std::nullopt,
                    linked_symbol,
                    linked_addend,
                    proc.parameters,
                    upper_ascii(proc.return_type),
                }).second) {
            throw ToolError(
                "DUPLICATE ROUTINE LINE " + std::to_string(proc.line) + ": " +
                upper_ascii(proc.name));
        }
    }

    std::map<std::string, RelocatableCompilerConstant> global_compiler_addresses;
    auto resolve_compiler_constant = [&](std::string_view expression,
                                         const std::map<
                                             std::string,
                                             RelocatableCompilerConstant>& addresses,
                                         std::optional<std::string> current_symbol = std::nullopt) {
        const std::string text = trim(expression);
        if (text.empty()) {
            throw ToolError("BAD COMPILER CONSTANT");
        }
        if (auto numeric = try_eval_const_expr(text, global_constants)) {
            return RelocatableCompilerConstant{numeric, {}, 0};
        }

        RelocatableCompilerConstant result{ExprValue{0}, {}, 0};
        std::size_t start = 0;
        while (start < text.size()) {
            const std::size_t plus = text.find('+', start);
            const std::string term = trim(std::string_view(text).substr(
                start,
                plus == std::string::npos ? std::string::npos : plus - start));
            if (term.empty()) {
                throw ToolError("BAD COMPILER CONSTANT " + text);
            }

            RelocatableCompilerConstant value;
            if (auto numeric = try_eval_const_expr(term, global_constants)) {
                value.absolute = *numeric;
            } else if (term == "*") {
                if (!current_symbol) {
                    throw ToolError("CURRENT ADDRESS NOT AVAILABLE HERE");
                }
                value.symbol = upper_ascii(*current_symbol);
            } else if (term.back() == '^') {
                // The cartridge compiler interpreted this by reading its own
                // live 64K compile-time memory.  A deterministic host/linker
                // build has no equivalent target-memory value to inspect.
                throw ToolError(
                    "LEGACY COMPILER-MEMORY POINTER CONSTANT " + upper_ascii(term));
            } else {
                const std::string name = upper_ascii(term);
                auto address = addresses.find(name);
                if (address != addresses.end()) {
                    value = address->second;
                } else {
                    auto external = external_routines.find(name);
                    if (external != external_routines.end()) {
                        if (external->second.absolute_address) {
                            value.absolute = *external->second.absolute_address;
                        } else {
                            value.symbol = external->second.linked_address_symbol;
                            value.addend = external->second.linked_address_addend;
                        }
                    } else if (local_names.count(name) != 0) {
                        value.symbol = name;
                    } else {
                        throw ToolError("UNKNOWN COMPILER CONSTANT " + name);
                    }
                }
            }

            if (value.absolute) {
                if (result.absolute) {
                    *result.absolute += *value.absolute;
                } else {
                    const std::int64_t combined =
                        static_cast<std::int64_t>(result.addend) + *value.absolute;
                    if (combined < std::numeric_limits<std::int32_t>::min() ||
                        combined > std::numeric_limits<std::int32_t>::max()) {
                        throw ToolError("COMPILER CONSTANT RANGE " + text);
                    }
                    result.addend = static_cast<std::int32_t>(combined);
                }
            } else {
                if (value.symbol.empty()) {
                    throw ToolError("BAD COMPILER CONSTANT " + text);
                }
                if (!result.symbol.empty()) {
                    throw ToolError(
                        "TWO LINKED ADDRESSES IN COMPILER CONSTANT " + text);
                }
                const std::int64_t combined =
                    (result.absolute
                         ? static_cast<std::int64_t>(*result.absolute)
                         : static_cast<std::int64_t>(result.addend)) +
                    value.addend;
                if (combined < std::numeric_limits<std::int32_t>::min() ||
                    combined > std::numeric_limits<std::int32_t>::max()) {
                    throw ToolError("COMPILER CONSTANT RANGE " + text);
                }
                result.symbol = value.symbol;
                result.addend = static_cast<std::int32_t>(combined);
                result.absolute.reset();
            }

            if (plus == std::string::npos) {
                break;
            }
            start = plus + 1;
        }
        return result;
    };

    auto apply_declaration_binding = [&](
        VarSlot slot,
        std::string_view mode,
        std::string_view expression,
        std::size_t line,
        const std::map<std::string, RelocatableCompilerConstant>& addresses,
        bool compiler_constant_initializer = false) {
        if (mode == "STORAGE") {
            return slot;
        }
        if (mode == "INITIAL") {
            if (compiler_constant_initializer) {
                const RelocatableCompilerConstant address =
                    resolve_compiler_constant(expression, addresses);
                if (address.absolute) {
                    if (*address.absolute < 0 || *address.absolute > 0xFFFF) {
                        throw ToolError(
                            "INITIALIZER RANGE LINE " + std::to_string(line) +
                            ": " + slot.name);
                    }
                    slot.initial_value = static_cast<std::uint16_t>(*address.absolute);
                } else {
                    slot.initial_address_symbol = address.symbol;
                    slot.initial_address_addend = address.addend;
                }
                return slot;
            }
            const ExprValue value = eval_const_expr(expression, global_constants);
            const ExprValue minimum = slot.is_signed ? -32768 : 0;
            const ExprValue maximum = slot.is_signed ? 32767 : (slot.is_card ? 0xFFFF : 0xFF);
            if (value < minimum || value > maximum) {
                throw ToolError(
                    "INITIALIZER RANGE LINE " + std::to_string(line) + ": " + slot.name);
            }
            slot.initial_value = static_cast<std::uint16_t>(value);
            return slot;
        }
        if (mode == "ADDRESS") {
            const RelocatableCompilerConstant address =
                resolve_compiler_constant(expression, addresses);
            if (address.absolute) {
                const ExprValue maximum = slot.is_card ? 0xFFFE : 0xFFFF;
                if (*address.absolute < 0 || *address.absolute > maximum) {
                    throw ToolError(
                        "ADDRESS RANGE LINE " + std::to_string(line) + ": " + slot.name);
                }
                slot.absolute_address = static_cast<std::uint16_t>(*address.absolute);
            } else {
                slot.bound_address_symbol = address.symbol;
                slot.bound_address_addend = address.addend;
            }
            return slot;
        }
        throw ToolError("BAD DECL LINE " + std::to_string(line));
    };

    auto compiler_address_of_variable = [](const VarSlot& slot) {
        if (slot.absolute_address) {
            return RelocatableCompilerConstant{
                static_cast<ExprValue>(*slot.absolute_address), {}, 0};
        }
        if (!slot.bound_address_symbol.empty()) {
            return RelocatableCompilerConstant{
                std::nullopt,
                slot.bound_address_symbol,
                slot.bound_address_addend,
            };
        }
        return RelocatableCompilerConstant{std::nullopt, slot.lo_symbol, 0};
    };

    auto compiler_address_of_array = [](const ArraySlot& slot)
        -> std::optional<RelocatableCompilerConstant> {
        if (slot.absolute_data_address) {
            return RelocatableCompilerConstant{
                static_cast<ExprValue>(*slot.absolute_data_address), {}, 0};
        }
        if (!slot.linked_data_address_symbol.empty()) {
            return RelocatableCompilerConstant{
                std::nullopt,
                slot.linked_data_address_symbol,
                slot.linked_data_address_addend,
            };
        }
        if (!slot.initial_data.empty()) {
            return RelocatableCompilerConstant{
                std::nullopt, slot.data_symbol, 0};
        }
        return std::nullopt;
    };

    auto make_real_slot = [&](
        const std::string& name,
        const std::string& prefix,
        std::string_view mode,
        std::string_view expression,
        std::size_t line) {
        RealSlot slot;
        slot.name = upper_ascii(name);
        for (int i = 0; i < 4; ++i) {
            slot.byte_symbols.push_back(prefix + "_B" + std::to_string(i));
        }
        slot.pointer_lo_symbol = prefix + "_PTR_LO";
        slot.pointer_hi_symbol = prefix + "_PTR_HI";
        if (mode == "INITIAL") {
            auto value = try_eval_const_real_expr(expression, real_constants);
            if (!value) {
                throw ToolError(
                    "BAD REAL INITIALIZER LINE " + std::to_string(line) + ": " + slot.name);
            }
            slot.initial_value = real32_bytes(*value);
        } else if (mode == "ADDRESS") {
            const ExprValue address = eval_const_expr(expression, global_constants);
            if (address < 0 || address > 0xFFFC) {
                throw ToolError(
                    "ADDRESS RANGE LINE " + std::to_string(line) + ": " + slot.name);
            }
            slot.absolute_address = static_cast<std::uint16_t>(address);
        } else if (mode != "STORAGE") {
            throw ToolError("BAD DECL LINE " + std::to_string(line));
        }
        return slot;
    };

    auto make_array_slot = [&](
        const std::string& name,
        const std::string& prefix,
        std::string_view type_text,
        std::string_view size_expression,
        std::string_view mode_text,
        std::string_view initializer,
        std::size_t line,
        const std::map<std::string, RelocatableCompilerConstant>& addresses) {
        const std::string type = upper_ascii(type_text);
        const std::string mode = upper_ascii(mode_text);
        const IndexedElementType element_type = indexed_element_type(type);

        ArraySlot slot;
        slot.indexed.pointer = VarSlot{
            upper_ascii(name),
            prefix + "_PTR_LO",
            prefix + "_PTR_HI",
            true,
        };
        slot.indexed.element_type = element_type;
        slot.data_symbol = prefix + "_DATA";
        const std::size_t element_width = slot.indexed.element_width();

        std::optional<std::size_t> element_count;
        if (!trim(size_expression).empty()) {
            const ExprValue count = eval_const_expr(size_expression, global_constants);
            const bool initializer_sets_size = mode == "STRING" || mode == "VALUES";
            if (count < 0 || (!initializer_sets_size && count < 1) ||
                (count > 0 &&
                 static_cast<unsigned long long>(count) * element_width > 0xFFFFULL)) {
                throw ToolError(
                    "ARRAY SIZE RANGE LINE " + std::to_string(line) + ": " +
                    upper_ascii(name));
            }
            if (!initializer_sets_size) {
                element_count = static_cast<std::size_t>(count);
            }
        }

        std::vector<std::uint8_t> initialized;
        if (mode == "STRING") {
            if (type != "BYTE") {
                throw ToolError(
                    "STRING ARRAY TYPE LINE " + std::to_string(line) + ": " +
                    upper_ascii(name));
            }
            const std::string text = trim(initializer);
            if (text.size() < 2 || text.front() != '"' || text.back() != '"') {
                throw ToolError("BAD STRING ARRAY LINE " + std::to_string(line));
            }
            std::string decoded;
            bool escaped = false;
            for (std::size_t i = 1; i + 1 < text.size(); ++i) {
                const char ch = text[i];
                if (escaped) {
                    if (ch == 'n') decoded.push_back('\n');
                    else if (ch == 'r') decoded.push_back('\r');
                    else decoded.push_back(ch);
                    escaped = false;
                } else if (ch == '"' && i + 2 < text.size() &&
                           text[i + 1] == '"') {
                    decoded.push_back('"');
                    ++i;
                } else if (ch == '\\') {
                    escaped = true;
                } else {
                    decoded.push_back(ch);
                }
            }
            if (escaped || decoded.size() > 255) {
                throw ToolError(
                    "STRING SIZE RANGE LINE " + std::to_string(line) + ": " +
                    upper_ascii(name));
            }
            initialized.push_back(static_cast<std::uint8_t>(decoded.size()));
            initialized.insert(initialized.end(), decoded.begin(), decoded.end());
            // Original Action semantics: an initializer overrides a written
            // dimension, including the idiomatic ARRAY name(0)=[...].
            element_count = initialized.size();
        } else if (mode == "VALUES") {
            std::vector<std::string> value_expressions =
                split_array_initializer_values(initializer);
            if (!slot.indexed.element_is_real()) {
                std::vector<std::string> lexed_values;
                for (const std::string& value : value_expressions) {
                    if (!value.empty() && value.front() == '"') {
                        lexed_values.push_back(value);
                        continue;
                    }
                    std::vector<std::string> adjacent =
                        split_code_block_constants(value);
                    lexed_values.insert(
                        lexed_values.end(), adjacent.begin(), adjacent.end());
                }
                value_expressions = std::move(lexed_values);
            }
            for (const std::string& value_text : value_expressions) {
                if (!value_text.empty() && value_text.front() == '"') {
                    const ParsedExpr parsed_value = WordExprParser(value_text).parse();
                    const ExprNode& root = parsed_value.nodes.at(parsed_value.root);
                    if (root.kind != ExprNode::Kind::StringLiteral) {
                        throw ToolError("BAD STRING ARRAY INITIALIZER");
                    }
                    if (element_width != 2 || slot.indexed.element_is_real()) {
                        throw ToolError(
                            "STRING ADDRESS ARRAY TYPE LINE " +
                            std::to_string(line) + ": " + upper_ascii(name));
                    }
                    if (root.name.size() > 255) {
                        throw ToolError(
                            "STRING SIZE RANGE LINE " + std::to_string(line) + ": " +
                            upper_ascii(name));
                    }
                    const std::string literal_name =
                        "__STRING_" + std::to_string(next_string_literal++);
                    const std::string literal_prefix = module + "_" + literal_name;
                    ArraySlot literal;
                    literal.indexed.pointer = VarSlot{
                        literal_name,
                        literal_prefix + "_PTR_LO",
                        literal_prefix + "_PTR_HI",
                        true,
                    };
                    literal.data_symbol = literal_prefix + "_DATA";
                    literal.initial_data.push_back(
                        static_cast<std::uint8_t>(root.name.size()));
                    literal.initial_data.insert(
                        literal.initial_data.end(), root.name.begin(), root.name.end());
                    const std::size_t relocation_offset = initialized.size();
                    initialized.push_back(0);
                    initialized.push_back(0);
                    slot.initial_relocations.push_back(ArraySlot::InitialRelocation{
                        relocation_offset,
                        literal.data_symbol,
                        0,
                    });
                    array_slots.push_back(std::move(literal));
                    continue;
                }
                if (slot.indexed.element_is_real()) {
                    auto value = try_eval_const_real_expr(value_text, real_constants);
                    if (!value) {
                        throw ToolError(
                            "BAD REAL ARRAY INITIALIZER LINE " +
                            std::to_string(line) + ": " + upper_ascii(name));
                    }
                    const std::vector<std::uint8_t> bytes = real32_bytes(*value);
                    initialized.insert(initialized.end(), bytes.begin(), bytes.end());
                    continue;
                }
                std::optional<ExprValue> constant_value =
                    try_eval_const_expr(value_text, global_constants);
                if (!constant_value && element_width == 2) {
                    const RelocatableCompilerConstant value =
                        resolve_compiler_constant(value_text, addresses);
                    if (value.is_symbolic()) {
                        const std::size_t relocation_offset = initialized.size();
                        initialized.push_back(0);
                        initialized.push_back(0);
                        slot.initial_relocations.push_back(
                            ArraySlot::InitialRelocation{
                                relocation_offset,
                                value.symbol,
                                value.addend,
                            });
                        continue;
                    }
                    constant_value = value.absolute;
                }
                if (!constant_value) {
                    throw ToolError("UNKNOWN VAR");
                }
                const ExprValue value = *constant_value;
                const ExprValue minimum = slot.indexed.element_is_signed() ? -32768 : 0;
                const ExprValue maximum = slot.indexed.element_is_signed()
                    ? 32767
                    : (element_width == 2 ? 0xFFFF : 0xFF);
                if (value < minimum || value > maximum) {
                    throw ToolError(
                        "ARRAY INITIALIZER RANGE LINE " + std::to_string(line) + ": " +
                        upper_ascii(name));
                }
                initialized.push_back(static_cast<std::uint8_t>(value & 0xFF));
                if (element_width == 2) {
                    initialized.push_back(static_cast<std::uint8_t>((value >> 8) & 0xFF));
                }
            }
            if (initialized.empty()) {
                throw ToolError("EMPTY ARRAY INITIALIZER LINE " + std::to_string(line));
            }
            element_count = initialized.size() / element_width;
        } else if (mode == "ADDRESS") {
            const RelocatableCompilerConstant address =
                resolve_compiler_constant(initializer, addresses);
            if (address.absolute) {
                if (*address.absolute < 0 || *address.absolute > 0xFFFF) {
                    throw ToolError(
                        "ADDRESS RANGE LINE " + std::to_string(line) + ": " +
                        upper_ascii(name));
                }
                slot.absolute_data_address =
                    static_cast<std::uint16_t>(*address.absolute);
            } else {
                slot.linked_data_address_symbol = address.symbol;
                slot.linked_data_address_addend = address.addend;
            }
        } else if (mode != "STORAGE" && mode != "POINTER") {
            throw ToolError("BAD ARRAY DECL LINE " + std::to_string(line));
        }

        if (element_count && !slot.absolute_data_address &&
            slot.linked_data_address_symbol.empty()) {
            const std::size_t byte_count = *element_count * element_width;
            if (initialized.size() > byte_count) {
                throw ToolError(
                    "ARRAY INITIALIZER SIZE LINE " + std::to_string(line) + ": " +
                    upper_ascii(name));
            }
            slot.initial_data.assign(byte_count, 0);
            std::copy(initialized.begin(), initialized.end(), slot.initial_data.begin());
        }
        return slot;
    };

    struct RecordAddressSlot {
        std::string target_symbol;
        std::optional<std::uint16_t> absolute_address;
        std::int32_t target_addend = 0;
    };
    std::set<std::string> global_names = source_constant_names;
    std::map<std::string, const SourceProc*> seen_routines;
    for (const SourceProc& source_proc : source.procs) {
        const std::string routine_name = upper_ascii(source_proc.name);
        const auto [seen, first_declaration] =
            seen_routines.emplace(routine_name, &source_proc);
        if (!first_declaration) {
            const SourceProc& previous = *seen->second;
            bool same_parameters =
                previous.parameters.size() == source_proc.parameters.size();
            for (std::size_t i = 0;
                 same_parameters && i < source_proc.parameters.size();
                 ++i) {
                const SourceParameter& left = previous.parameters[i];
                const SourceParameter& right = source_proc.parameters[i];
                same_parameters =
                    upper_ascii(left.type) == upper_ascii(right.type) &&
                    left.is_array == right.is_array &&
                    left.is_pointer == right.is_pointer;
            }
            const bool matching_declarations =
                previous.declaration_only && source_proc.declaration_only &&
                previous.address_expression.empty() &&
                source_proc.address_expression.empty() &&
                upper_ascii(previous.return_type) ==
                    upper_ascii(source_proc.return_type) &&
                same_parameters;
            if (matching_declarations) {
                continue;
            }
            throw ToolError("ROUTINE NAME COLLISION " + routine_name);
        }
        if (!global_names.insert(routine_name).second) {
            throw ToolError("ROUTINE NAME COLLISION " + routine_name);
        }
    }
    std::map<std::string, VarSlot> global_variables;
    std::map<std::string, RealSlot> global_real_variables;
    std::map<std::string, IndexedSlot> global_arrays;
    std::map<std::string, IndexedSlot> global_pointers;
    std::map<std::string, RecordAddressSlot> global_record_addresses;
    struct ReuArrayDeclaration {
        std::string name;
        std::string size_expression;
        std::size_t line = 0;
    };
    std::vector<ReuArrayDeclaration> global_reu_arrays;
    for (const SourceGlobal& declaration : source.globals) {
        const std::string name = upper_ascii(declaration.name);
        if (!global_names.insert(name).second) {
            throw ToolError(
                "DUPLICATE GLOBAL LINE " + std::to_string(declaration.line) + ": " + name);
        }
        const std::string prefix = module + "_" + name;
        const std::string declaration_type = upper_ascii(declaration.type);
        if (declaration_type.rfind("RECORD_POINTER:", 0) == 0 ||
            declaration_type.rfind("RECORD:", 0) == 0) {
            const bool pointer = declaration_type.rfind("RECORD_POINTER:", 0) == 0;
            const std::size_t separator = declaration_type.find(':');
            const std::string record_name = declaration_type.substr(separator + 1);
            auto record = record_types.find(record_name);
            if (record == record_types.end()) {
                throw ToolError(
                    "UNKNOWN TYPE LINE " + std::to_string(declaration.line) + ": " +
                    record_name);
            }
            if (pointer) {
                VarSlot slot = apply_declaration_binding(VarSlot{
                    name,
                    prefix + "_LO",
                    prefix + "_HI",
                    true,
                }, declaration.mode, declaration.expression, declaration.line,
                   global_compiler_addresses, true);
                global_variables.emplace(name, slot);
                if (!slot.is_address_bound()) {
                    data_slots.push_back(slot);
                    data_symbols.insert(slot.lo_symbol);
                }
                global_compiler_addresses[name] = compiler_address_of_variable(slot);
                for (const ParsedRecordField& field : record->second.fields) {
                    global_pointers.emplace(
                        name + "." + field.name,
                        IndexedSlot{
                            slot,
                            indexed_element_type(field.type),
                            field.offset,
                        });
                }
                continue;
            }

            std::optional<RelocatableCompilerConstant> base_address;
            if (upper_ascii(declaration.mode) == "ADDRESS") {
                base_address = resolve_compiler_constant(
                    declaration.expression, global_compiler_addresses);
                if (base_address->absolute &&
                    (*base_address->absolute < 0 ||
                     static_cast<unsigned long long>(*base_address->absolute) +
                             record->second.size >
                         0x10000ULL)) {
                    throw ToolError(
                        "RECORD ADDRESS RANGE LINE " +
                        std::to_string(declaration.line) + ": " + name);
                }
            } else if (upper_ascii(declaration.mode) != "STORAGE") {
                throw ToolError("BAD RECORD DECL LINE " + std::to_string(declaration.line));
            }
            RecordAddressSlot record_address;
            if (base_address) {
                if (base_address->absolute) {
                    record_address.absolute_address =
                        static_cast<std::uint16_t>(*base_address->absolute);
                } else {
                    record_address.target_symbol = base_address->symbol;
                    record_address.target_addend = base_address->addend;
                }
            }
            for (const ParsedRecordField& field : record->second.fields) {
                const std::string field_name = name + "." + field.name;
                const std::string field_prefix = prefix + "_" + field.name;
                VarSlot slot{
                    field_name,
                    field_prefix + "_LO",
                    field_prefix + "_HI",
                    field.type == "CARD" || field.type == "INT",
                    field.type == "INT",
                    0,
                    base_address && base_address->absolute
                        ? std::optional<std::uint16_t>(static_cast<std::uint16_t>(
                              *base_address->absolute + field.offset))
                        : std::nullopt,
                };
                if (base_address && base_address->is_symbolic()) {
                    slot.bound_address_symbol = base_address->symbol;
                    slot.bound_address_addend = static_cast<std::int32_t>(
                        static_cast<std::int64_t>(base_address->addend) + field.offset);
                }
                global_variables.emplace(field_name, slot);
                if (!slot.is_address_bound()) {
                    data_slots.push_back(slot);
                    data_symbols.insert(slot.lo_symbol);
                }
                if (field.offset == 0 && !base_address) {
                    record_address.target_symbol = slot.lo_symbol;
                }
            }
            if (base_address) {
                global_compiler_addresses[name] = *base_address;
            } else {
                global_compiler_addresses[name] = RelocatableCompilerConstant{
                    std::nullopt, record_address.target_symbol, 0};
            }
            global_record_addresses.emplace(name, std::move(record_address));
            continue;
        }
        if (upper_ascii(declaration.type) == "REU_BYTE_ARRAY") {
            VarSlot slot{
                name,
                prefix + "_LO",
                prefix + "_HI",
                false,
                false,
                0xFF,
            };
            global_variables.emplace(name, slot);
            data_slots.push_back(slot);
            data_symbols.insert(slot.lo_symbol);
            global_compiler_addresses[name] = compiler_address_of_variable(slot);
            global_reu_arrays.push_back(ReuArrayDeclaration{
                name,
                declaration.expression,
                declaration.line,
            });
            continue;
        }
        if (declaration_type == "SPRITE_RESOURCE" ||
            declaration_type == "MSPRITE_RESOURCE" ||
            declaration_type == "BITMAP_RESOURCE" ||
            declaration_type == "MBITMAP_RESOURCE") {
            const fs::path resource_path = resolve_graphics_resource(
                fs::current_path(), src, declaration.expression);
            std::vector<std::uint8_t> contents = compiled_graphics_resource(
                declaration_type, resource_path, declaration.line);
            ArraySlot slot = make_array_slot(
                name,
                prefix,
                "BYTE",
                std::to_string(contents.size()),
                "STORAGE",
                {},
                declaration.line,
                global_compiler_addresses);
            slot.initial_data = std::move(contents);
            slot.alignment =
                (declaration_type == "SPRITE_RESOURCE" ||
                 declaration_type == "MSPRITE_RESOURCE")
                ? 64
                : 1;
            global_variables.emplace(name, slot.indexed.pointer);
            global_arrays.emplace(name, slot.indexed);
            if (auto address = compiler_address_of_array(slot)) {
                global_compiler_addresses[name] = *address;
            }
            array_slots.push_back(std::move(slot));
            continue;
        }
        if (declaration_type.size() > 6 &&
            declaration_type.substr(declaration_type.size() - 6) == "_ARRAY") {
            const std::string element_type =
                declaration_type.substr(0, declaration_type.size() - 6);
            ArraySlot slot = make_array_slot(
                name,
                prefix,
                element_type,
                declaration.size_expression,
                declaration.mode,
                declaration.expression,
                declaration.line,
                global_compiler_addresses);
            global_variables.emplace(name, slot.indexed.pointer);
            global_arrays.emplace(name, slot.indexed);
            if (auto address = compiler_address_of_array(slot)) {
                global_compiler_addresses[name] = *address;
            }
            array_slots.push_back(std::move(slot));
            continue;
        }
        if (declaration_type.size() > 8 &&
            declaration_type.substr(declaration_type.size() - 8) == "_POINTER") {
            const std::string element_type =
                declaration_type.substr(0, declaration_type.size() - 8);
            VarSlot slot = apply_declaration_binding(VarSlot{
                name,
                prefix + "_LO",
                prefix + "_HI",
                true,
            }, declaration.mode, declaration.expression, declaration.line,
               global_compiler_addresses, true);
            global_variables.emplace(name, slot);
            global_pointers.emplace(name, IndexedSlot{
                slot,
                indexed_element_type(element_type),
            });
            data_slots.push_back(slot);
            data_symbols.insert(slot.lo_symbol);
            global_compiler_addresses[name] = compiler_address_of_variable(slot);
            continue;
        }
        if (upper_ascii(declaration.type) == "REAL") {
            RealSlot slot = make_real_slot(
                name,
                prefix,
                declaration.mode,
                declaration.expression,
                declaration.line);
            global_real_variables.emplace(name, slot);
            if (slot.absolute_address) {
                global_compiler_addresses[name] = RelocatableCompilerConstant{
                    static_cast<ExprValue>(*slot.absolute_address), {}, 0};
            } else {
                global_compiler_addresses[name] = RelocatableCompilerConstant{
                    std::nullopt, slot.byte_symbols.front(), 0};
            }
            real_slots.push_back(std::move(slot));
            continue;
        }
        VarSlot slot = apply_declaration_binding(VarSlot{
            name,
            prefix + "_LO",
            prefix + "_HI",
            declaration_type == "CARD" || declaration_type == "INT",
            declaration_type == "INT",
        }, declaration.mode, declaration.expression, declaration.line,
           global_compiler_addresses, false);
        global_variables.emplace(name, slot);
        if (!slot.is_address_bound()) {
            data_slots.push_back(slot);
            data_symbols.insert(slot.lo_symbol);
        }
        global_compiler_addresses[name] = compiler_address_of_variable(slot);
    }

    struct ProcedureParameterSlot {
        SourceParameter source;
        std::optional<VarSlot> word;
        std::optional<RealSlot> real;
    };
    struct FunctionReturnSlot {
        std::string type;
        std::optional<RealSlot> real;
    };
    std::map<std::string, std::vector<ProcedureParameterSlot>> procedure_parameters;
    std::map<std::string, FunctionReturnSlot> function_returns;
    for (const SourceProc& proc : ordered) {
        const std::string proc_name = upper_ascii(proc.name);
        if (proc_name == "MAIN" && !proc.parameters.empty()) {
            const bool valid_idun_abi =
                proc.parameters.size() == 2 &&
                upper_ascii(proc.parameters[0].type) == "CARD" &&
                !proc.parameters[0].is_array &&
                !proc.parameters[0].is_pointer &&
                upper_ascii(proc.parameters[1].type) == "CARD" &&
                proc.parameters[1].is_array &&
                !proc.parameters[1].is_pointer;
            if (!valid_idun_abi) {
                throw ToolError(
                    "MAIN ABI LINE " + std::to_string(proc.line) +
                    ": EXPECTED PROC MAIN() OR PROC MAIN(CARD argc,CARD ARRAY argv)");
            }
        }
        std::set<std::string> parameter_names;
        std::vector<ProcedureParameterSlot> slots;
        slots.reserve(proc.parameters.size());
        for (const SourceParameter& parameter : proc.parameters) {
            const std::string name = upper_ascii(parameter.name);
            if (!parameter_names.insert(name).second) {
                throw ToolError(
                    "DUPLICATE PARAM LINE " + std::to_string(proc.line) + ": " + name);
            }
            const std::string type = upper_ascii(parameter.type);
            const std::string prefix = proc_name + "_" + name;
            ProcedureParameterSlot slot;
            slot.source = parameter;
            if (machine_code_names.count(proc_name) != 0) {
                if (type == "REAL") {
                    throw ToolError("UNSUPPORTED MACHINE REAL ABI " + proc_name);
                }
            } else if (type == "REAL" && !parameter.is_array && !parameter.is_pointer) {
                slot.real = make_real_slot(name, prefix, "STORAGE", "", proc.line);
                real_slots.push_back(*slot.real);
            } else {
                const bool record_parameter = record_types.count(type) != 0;
                const bool word_value =
                    parameter.is_array || parameter.is_pointer ||
                    type == "CARD" || type == "INT" || record_parameter;
                slot.word = VarSlot{
                    name,
                    prefix + "_LO",
                    prefix + "_HI",
                    word_value,
                    type == "INT" && !parameter.is_array && !parameter.is_pointer,
                };
                data_slots.push_back(*slot.word);
                data_symbols.insert(slot.word->lo_symbol);
            }
            slots.push_back(std::move(slot));
        }
        procedure_parameters.emplace(proc_name, std::move(slots));
        if (!proc.return_type.empty()) {
            FunctionReturnSlot result;
            result.type = upper_ascii(proc.return_type);
            if (result.type == "REAL") {
                if (machine_code_names.count(proc_name) != 0) {
                    throw ToolError("UNSUPPORTED MACHINE REAL ABI " + proc_name);
                }
                result.real = make_real_slot(
                    "__RETURN",
                    proc_name + "_RETURN",
                    "STORAGE",
                    "",
                    proc.line);
                real_slots.push_back(*result.real);
            } else if (result.type != "BYTE" && result.type != "CARD" &&
                       result.type != "INT") {
                throw ToolError(
                    "BAD FUNC TYPE LINE " + std::to_string(proc.line));
            }
            function_returns.emplace(proc_name, std::move(result));
        }
    }

    auto add_import = [&](const std::string& symbol) {
        const std::string upper = upper_ascii(symbol);
        auto found = import_index.find(upper);
        if (found == import_index.end()) {
            const int index = static_cast<int>(imports.size());
            found = import_index.emplace(upper, index).first;
            imports.push_back(upper);
        }
        return found->second;
    };

    auto add_reloc = [&](
        std::uint16_t offset,
        const std::string& symbol,
        std::int32_t addend = 0,
        ObjRelocPart part = ObjRelocPart::Word) {
        ObjReloc reloc;
        reloc.offset = offset;
        reloc.symbol = upper_ascii(symbol);
        reloc.addend = addend;
        reloc.part = part;
        relocs.push_back(reloc);
    };

    auto add_import_reloc = [&](std::uint16_t offset, const std::string& symbol) {
        ObjReloc reloc;
        reloc.offset = offset;
        reloc.import = true;
        reloc.import_index = add_import(symbol);
        relocs.push_back(reloc);
    };

    auto emit_text = [&](std::string text) {
        text.push_back('\r');
        for (unsigned char ch : text) {
            code.push_back(0xA9);  // LDA #imm
            code.push_back(ch);
            code.push_back(0x20);  // JSR $FFD2 / CHROUT
            code.push_back(0xD2);
            code.push_back(0xFF);
        }
    };

    auto emit_jsr_import = [&](const std::string& symbol) {
        code.push_back(0x20);  // JSR absolute
        const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
        code.push_back(0x00);
        code.push_back(0x00);
        add_import_reloc(operand_offset, symbol);
    };

    auto emit_cr = [&]() {
        code.push_back(0xA9);  // LDA #CR
        code.push_back(0x0D);
        code.push_back(0x20);  // JSR $FFD2 / CHROUT
        code.push_back(0xD2);
        code.push_back(0xFF);
    };

    for (const SourceProc& proc : ordered) {
        const std::string current_proc_name = upper_ascii(proc.name);
        std::map<std::string, ExprValue> constants = global_constants;
        std::map<std::string, VarSlot> variables = global_variables;
        std::map<std::string, RealSlot> real_variables = global_real_variables;
        std::map<std::string, IndexedSlot> arrays = global_arrays;
        std::map<std::string, IndexedSlot> pointers = global_pointers;
        std::map<std::string, RecordAddressSlot> record_addresses =
            global_record_addresses;
        std::map<std::string, RelocatableCompilerConstant> compiler_addresses =
            global_compiler_addresses;
        std::vector<std::string> persistent_frame_bytes;
        std::vector<std::string> operation_frame_bytes;
        std::set<std::string> persistent_frame_symbols;
        std::set<std::string> operation_frame_symbols;
        auto add_frame_byte = [&](const std::string& symbol, bool persistent) {
            const std::string upper = upper_ascii(symbol);
            std::set<std::string>& symbols = persistent
                ? persistent_frame_symbols
                : operation_frame_symbols;
            if (!symbols.insert(upper).second) {
                return;
            }
            (persistent ? persistent_frame_bytes : operation_frame_bytes)
                .push_back(upper);
        };
        auto add_frame_variable = [&](const VarSlot& slot, bool persistent) {
            if (slot.is_address_bound()) {
                return;
            }
            add_frame_byte(slot.lo_symbol, persistent);
            if (slot.is_card) {
                add_frame_byte(slot.hi_symbol, persistent);
            }
        };
        auto add_frame_real = [&](const RealSlot& slot, bool persistent) {
            if (slot.absolute_address) {
                return;
            }
            if (slot.byte_symbols.size() != 4) {
                throw ToolError("BAD REAL SLOT");
            }
            for (const std::string& symbol : slot.byte_symbols) {
                add_frame_byte(symbol, persistent);
            }
        };
        struct IfFrame {
            bool runtime = false;
            bool active = true;
            bool branch_taken = false;
            bool parent_active = true;
            bool saw_else = false;
            std::string next_label;
            std::string end_label;
        };
        struct ForLoopState {
            VarSlot counter;
            VarSlot final_value;
            VarSlot step;
            bool descending = false;
            bool dynamic_step = false;
        };
        struct LoopFrame {
            bool active = true;
            bool saw_until = false;
            bool has_precondition = false;
            std::size_t if_depth = 0;
            std::string start_label;
            std::string end_label;
            std::optional<ForLoopState> for_loop;
        };
        struct PendingForState {
            bool active = true;
            ParsedForClause clause;
            VarSlot counter;
            VarSlot final_value;
            VarSlot step;
            bool descending = false;
            bool dynamic_step = false;
            std::size_t line = 0;
        };
        std::vector<IfFrame> if_stack;
        std::vector<LoopFrame> loop_stack;
        std::optional<std::pair<std::string, std::size_t>> pending_while;
        std::optional<PendingForState> pending_for;
        bool has_value_return = false;
        bool terminal_top_level_return = false;
        const bool machine_code_routine =
            trim(proc.address_expression) == "*" &&
            std::any_of(proc.ops.begin(), proc.ops.end(), [](const SourceOp& op) {
                return op.kind == SourceOp::Kind::Code ||
                    op.kind == SourceOp::Kind::AsmBlock;
            });
        for (const SourceOp& op : proc.ops) {
            if (op.kind != SourceOp::Kind::Return) {
                continue;
            }
            if (proc.return_type.empty()) {
                if (!op.value.empty()) {
                    throw ToolError(
                        "PROC RETURN HAS VALUE LINE " + std::to_string(op.line));
                }
            } else {
                if (op.value.empty()) {
                    throw ToolError(
                        "FUNC RETURN VALUE REQUIRED LINE " +
                        std::to_string(op.line));
                }
                has_value_return = true;
            }
        }
        if (!proc.return_type.empty() && !has_value_return && !machine_code_routine) {
            throw ToolError(
                "MISSING FUNC RETURN LINE " + std::to_string(proc.line) +
                ": " + upper_ascii(proc.name));
        }
        const std::uint16_t proc_offset = static_cast<std::uint16_t>(code.size());
        source_lines.push_back(ObjLineRecord{proc_offset, proc.line});
        auto new_control_label = [&](std::string_view purpose) {
            return module + "_" + upper_ascii(proc.name) + "_" + upper_ascii(purpose) + "_" +
                   std::to_string(next_control_label++);
        };
        auto define_control_label = [&](const std::string& label) {
            exports.push_back(ObjExport{
                upper_ascii(label),
                static_cast<std::uint16_t>(code.size()),
                1,
            });
        };
        auto emit_jump = [&](const std::string& label) {
            code.push_back(0x4C);  // JMP absolute
            const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, label);
        };
        const std::string proc_body_label = new_control_label("BODY");
        emit_jump(proc_body_label);
        define_control_label(proc_body_label);
        auto variable_symbol = [&](const std::string& variable, std::string_view suffix) {
            return upper_ascii(proc.name) + "_" + upper_ascii(variable) + "_" + std::string(suffix);
        };
        std::set<std::string> local_declarations;
        for (const ProcedureParameterSlot& parameter :
             procedure_parameters.at(upper_ascii(proc.name))) {
            const std::string name = upper_ascii(parameter.source.name);
            if (!local_declarations.insert(name).second) {
                throw ToolError(
                    "DUPLICATE PARAM LINE " + std::to_string(proc.line) +
                    ": " + name);
            }
            if (machine_code_names.count(current_proc_name) != 0) {
                continue;
            }
            if (parameter.real) {
                real_variables[name] = *parameter.real;
                compiler_addresses[name] = RelocatableCompilerConstant{
                    std::nullopt, parameter.real->byte_symbols.front(), 0};
                add_frame_real(*parameter.real, true);
                continue;
            }
            if (!parameter.word) {
                throw ToolError("BAD PROC PARAM ABI");
            }
            variables[name] = *parameter.word;
            compiler_addresses[name] =
                compiler_address_of_variable(*parameter.word);
            add_frame_variable(*parameter.word, true);
            const std::string type = upper_ascii(parameter.source.type);
            auto record = record_types.find(type);
            if (record != record_types.end()) {
                for (const ParsedRecordField& field : record->second.fields) {
                    pointers[name + "." + field.name] = IndexedSlot{
                        *parameter.word,
                        indexed_element_type(field.type),
                        field.offset,
                    };
                }
                continue;
            }
            const IndexedSlot indexed{
                *parameter.word,
                indexed_element_type(type),
            };
            if (parameter.source.is_array) {
                arrays[name] = indexed;
            } else if (parameter.source.is_pointer) {
                pointers[name] = indexed;
            }
        }
        auto add_variable = [&](
            const std::string& variable,
            bool is_card,
            std::string_view mode = "STORAGE",
            std::string_view expression = "",
            std::size_t line = 0,
            bool is_signed = false,
            bool compiler_constant_initializer = false) {
            const std::string name = upper_ascii(variable);
            if (!local_declarations.insert(name).second) {
                throw ToolError(
                    "DUPLICATE VAR LINE " + std::to_string(line) + ": " + name);
            }
            VarSlot slot = apply_declaration_binding(
                VarSlot{
                    name,
                    variable_symbol(name, "LO"),
                    variable_symbol(name, "HI"),
                    is_card,
                    is_signed,
                },
                mode,
                expression,
                line,
                compiler_addresses,
                compiler_constant_initializer);
            variables[name] = slot;
            if (!slot.is_address_bound() &&
                data_symbols.insert(slot.lo_symbol).second) {
                data_slots.push_back(slot);
            }
            compiler_addresses[name] = compiler_address_of_variable(slot);
            add_frame_variable(slot, true);
        };
        auto add_real_variable = [&](
            const std::string& variable,
            std::string_view mode,
            std::string_view expression,
            std::size_t line) {
            const std::string name = upper_ascii(variable);
            if (!local_declarations.insert(name).second) {
                throw ToolError(
                    "DUPLICATE VAR LINE " + std::to_string(line) + ": " + name);
            }
            const std::string prefix = upper_ascii(proc.name) + "_" + name;
            RealSlot slot = make_real_slot(name, prefix, mode, expression, line);
            real_variables[name] = slot;
            if (slot.absolute_address) {
                compiler_addresses[name] = RelocatableCompilerConstant{
                    static_cast<ExprValue>(*slot.absolute_address), {}, 0};
            } else {
                compiler_addresses[name] = RelocatableCompilerConstant{
                    std::nullopt, slot.byte_symbols.front(), 0};
            }
            real_slots.push_back(std::move(slot));
            add_frame_real(real_variables.at(name), true);
        };
        auto add_pointer_variable = [&](
            const std::string& variable,
            std::string_view element_type,
            std::string_view mode,
            std::string_view expression,
            std::size_t line) {
            add_variable(variable, true, mode, expression, line, false, true);
            const std::string name = upper_ascii(variable);
            const std::string type = upper_ascii(element_type);
            pointers[name] = IndexedSlot{
                variables.at(name),
                indexed_element_type(type),
            };
        };
        auto add_record_variable = [&](
            const std::string& variable,
            std::string_view record_type,
            bool pointer,
            std::string_view mode,
            std::string_view expression,
            std::size_t line) {
            const std::string name = upper_ascii(variable);
            if (pointer) {
                add_variable(name, true, mode, expression, line, false, true);
                auto record = record_types.find(upper_ascii(record_type));
                if (record == record_types.end()) {
                    throw ToolError(
                        "UNKNOWN TYPE LINE " + std::to_string(line) + ": " +
                        upper_ascii(record_type));
                }
                for (const ParsedRecordField& field : record->second.fields) {
                    pointers[name + "." + field.name] = IndexedSlot{
                        variables.at(name),
                        indexed_element_type(field.type),
                        field.offset,
                    };
                }
                return;
            }
            if (!local_declarations.insert(name).second) {
                throw ToolError(
                    "DUPLICATE VAR LINE " + std::to_string(line) + ": " + name);
            }
            auto record = record_types.find(upper_ascii(record_type));
            if (record == record_types.end()) {
                throw ToolError(
                    "UNKNOWN TYPE LINE " + std::to_string(line) + ": " +
                    upper_ascii(record_type));
            }
            std::optional<RelocatableCompilerConstant> base_address;
            if (upper_ascii(mode) == "ADDRESS") {
                base_address =
                    resolve_compiler_constant(expression, compiler_addresses);
                if (base_address->absolute &&
                    (*base_address->absolute < 0 ||
                     static_cast<unsigned long long>(*base_address->absolute) +
                             record->second.size >
                         0x10000ULL)) {
                    throw ToolError(
                        "RECORD ADDRESS RANGE LINE " + std::to_string(line) + ": " + name);
                }
            } else if (upper_ascii(mode) != "STORAGE") {
                throw ToolError("BAD RECORD DECL LINE " + std::to_string(line));
            }
            RecordAddressSlot record_address;
            if (base_address) {
                if (base_address->absolute) {
                    record_address.absolute_address =
                        static_cast<std::uint16_t>(*base_address->absolute);
                } else {
                    record_address.target_symbol = base_address->symbol;
                    record_address.target_addend = base_address->addend;
                }
            }
            for (const ParsedRecordField& field : record->second.fields) {
                const std::string field_name = name + "." + field.name;
                const std::string field_prefix =
                    upper_ascii(proc.name) + "_" + name + "_" + field.name;
                VarSlot slot{
                    field_name,
                    field_prefix + "_LO",
                    field_prefix + "_HI",
                    field.type == "CARD" || field.type == "INT",
                    field.type == "INT",
                    0,
                    base_address && base_address->absolute
                        ? std::optional<std::uint16_t>(static_cast<std::uint16_t>(
                              *base_address->absolute + field.offset))
                        : std::nullopt,
                };
                if (base_address && base_address->is_symbolic()) {
                    slot.bound_address_symbol = base_address->symbol;
                    slot.bound_address_addend = static_cast<std::int32_t>(
                        static_cast<std::int64_t>(base_address->addend) + field.offset);
                }
                variables[field_name] = slot;
                if (!slot.is_address_bound() &&
                    data_symbols.insert(slot.lo_symbol).second) {
                    data_slots.push_back(slot);
                }
                add_frame_variable(slot, true);
                if (field.offset == 0 && !base_address) {
                    record_address.target_symbol = slot.lo_symbol;
                }
            }
            if (base_address) {
                compiler_addresses[name] = *base_address;
            } else {
                compiler_addresses[name] = RelocatableCompilerConstant{
                    std::nullopt, record_address.target_symbol, 0};
            }
            record_addresses[name] = std::move(record_address);
        };
        auto add_array_variable = [&](
            const std::string& variable,
            std::string_view element_type,
            std::string_view size_expression,
            std::string_view mode,
            std::string_view expression,
            std::size_t line) {
            const std::string name = upper_ascii(variable);
            if (!local_declarations.insert(name).second) {
                throw ToolError(
                    "DUPLICATE VAR LINE " + std::to_string(line) + ": " + name);
            }
            ArraySlot slot = make_array_slot(
                name,
                upper_ascii(proc.name) + "_" + name,
                element_type,
                size_expression,
                mode,
                expression,
                line,
                compiler_addresses);
            variables[name] = slot.indexed.pointer;
            arrays[name] = slot.indexed;
            if (auto address = compiler_address_of_array(slot)) {
                compiler_addresses[name] = *address;
            }
            add_frame_variable(slot.indexed.pointer, true);
            slot.frame_byte_symbols.reserve(slot.initial_data.size());
            for (std::size_t i = 0; i < slot.initial_data.size(); ++i) {
                const std::string symbol =
                    slot.data_symbol + "_FRAME_" + std::to_string(i);
                slot.frame_byte_symbols.push_back(symbol);
                add_frame_byte(symbol, true);
            }
            array_slots.push_back(std::move(slot));
        };
        auto expression_uses_variable = [&](std::string_view expr) {
            const std::string upper = upper_ascii(expr);
            auto contains_name = [&](const std::string& name) {
                std::size_t pos = upper.find(name);
                while (pos != std::string::npos) {
                    const bool before_ok =
                        pos == 0 ||
                        (!std::isalnum(static_cast<unsigned char>(upper[pos - 1])) && upper[pos - 1] != '_');
                    const std::size_t after = pos + name.size();
                    const bool after_ok =
                        after >= upper.size() ||
                        (!std::isalnum(static_cast<unsigned char>(upper[after])) && upper[after] != '_');
                    if (before_ok && after_ok) {
                        return true;
                    }
                    pos = upper.find(name, pos + 1);
                }
                return false;
            };
            for (const auto& item : variables) {
                if (contains_name(item.first)) {
                    return true;
                }
            }
            for (const auto& item : pointers) {
                if (item.first.find('.') != std::string::npos &&
                    contains_name(item.first)) {
                    return true;
                }
            }
            for (const std::string& routine : local_names) {
                if (contains_name(routine)) {
                    return true;
                }
            }
            return false;
        };
        auto expression_uses_real_variable = [&](std::string_view expr) {
            const std::string upper = upper_ascii(expr);
            for (const auto& item : real_variables) {
                std::size_t pos = upper.find(item.first);
                while (pos != std::string::npos) {
                    const bool before_ok =
                        pos == 0 ||
                        (!std::isalnum(static_cast<unsigned char>(upper[pos - 1])) &&
                         upper[pos - 1] != '_');
                    const std::size_t after = pos + item.first.size();
                    const bool after_ok =
                        after >= upper.size() ||
                        (!std::isalnum(static_cast<unsigned char>(upper[after])) &&
                         upper[after] != '_');
                    if (before_ok && after_ok) {
                        return true;
                    }
                    pos = upper.find(item.first, pos + 1);
                }
            }
            return false;
        };
        auto expression_uses_any_variable = [&](std::string_view expr) {
            return expression_uses_variable(expr) || expression_uses_real_variable(expr);
        };
        auto expression_uses_real_indirect = [&](std::string_view expr) {
            const std::string upper = upper_ascii(expr);
            auto uses = [&](const auto& slots, char suffix) {
                for (const auto& item : slots) {
                    if (!item.second.element_is_real()) {
                        continue;
                    }
                    std::size_t pos = upper.find(item.first);
                    while (pos != std::string::npos) {
                        const bool before_ok =
                            pos == 0 ||
                            (!std::isalnum(static_cast<unsigned char>(upper[pos - 1])) &&
                             upper[pos - 1] != '_');
                        std::size_t after = pos + item.first.size();
                        while (after < upper.size() &&
                               std::isspace(static_cast<unsigned char>(upper[after]))) {
                            ++after;
                        }
                        if (before_ok && after < upper.size() && upper[after] == suffix) {
                            return true;
                        }
                        pos = upper.find(item.first, pos + 1);
                    }
                }
                return false;
            };
            return uses(arrays, '(') || uses(pointers, '^');
        };
        auto expression_looks_real = [&](std::string_view expr) {
            if (expression_uses_real_variable(expr) ||
                expression_uses_real_indirect(expr)) {
                return true;
            }
            const std::string upper = upper_ascii(expr);
            for (const auto& function : function_returns) {
                if (function.second.type != "REAL") {
                    continue;
                }
                std::size_t pos = upper.find(function.first);
                while (pos != std::string::npos) {
                    const bool before_ok =
                        pos == 0 ||
                        (!std::isalnum(static_cast<unsigned char>(upper[pos - 1])) &&
                         upper[pos - 1] != '_');
                    std::size_t after = pos + function.first.size();
                    while (after < upper.size() &&
                           std::isspace(static_cast<unsigned char>(upper[after]))) {
                        ++after;
                    }
                    if (before_ok && after < upper.size() && upper[after] == '(') {
                        return true;
                    }
                    pos = upper.find(function.first, pos + 1);
                }
            }
            if (upper.find("REAL(") != std::string::npos ||
                upper.find("FABS(") != std::string::npos ||
                upper.find("FSQRT(") != std::string::npos ||
                upper.find("FTRUNC(") != std::string::npos ||
                upper.find("FFLOOR(") != std::string::npos ||
                upper.find("FCEIL(") != std::string::npos ||
                upper.find("FROUND(") != std::string::npos ||
                upper.find("FFRAC(") != std::string::npos ||
                upper.find("FMOD(") != std::string::npos ||
                upper.find("FHYPOT(") != std::string::npos ||
                upper.find("FMIN(") != std::string::npos ||
                upper.find("FMAX(") != std::string::npos ||
                upper.find("DEGTORAD(") != std::string::npos ||
                upper.find("RADTODEG(") != std::string::npos ||
                upper.find('.') != std::string::npos) {
                return true;
            }
            if (std::regex_search(
                    upper,
                    std::regex("(^|[^A-Z0-9_])(NAN|INF|INFINITY)([^A-Z0-9_]|$)"))) {
                return true;
            }
            return std::regex_search(upper, std::regex("[0-9]E[+-]?[0-9]"));
        };
        auto add_slot_reloc = [&](std::uint16_t operand_offset,
                                  const VarSlot& slot,
                                  std::uint16_t byte_offset = 0) {
            if (!slot.bound_address_symbol.empty()) {
                const std::int64_t addend =
                    static_cast<std::int64_t>(slot.bound_address_addend) + byte_offset;
                if (addend < std::numeric_limits<std::int32_t>::min() ||
                    addend > std::numeric_limits<std::int32_t>::max()) {
                    throw ToolError("ADDRESS ADDEND RANGE " + slot.name);
                }
                add_reloc(
                    operand_offset,
                    slot.bound_address_symbol,
                    static_cast<std::int32_t>(addend));
                return;
            }
            add_reloc(
                operand_offset,
                byte_offset == 0 ? slot.lo_symbol : slot.hi_symbol);
        };
        auto emit_load_variable = [&](const VarSlot& slot) {
            code.push_back(0xAD);  // LDA absolute
            std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            if (slot.absolute_address) {
                code.push_back(static_cast<std::uint8_t>(*slot.absolute_address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(*slot.absolute_address >> 8));
            } else {
                code.push_back(0x00);
                code.push_back(0x00);
                add_slot_reloc(operand_offset, slot, 0);
            }
            if (slot.is_card) {
                code.push_back(0xAE);  // LDX absolute
                operand_offset = static_cast<std::uint16_t>(code.size());
                if (slot.absolute_address) {
                    const std::uint16_t high_address =
                        static_cast<std::uint16_t>(*slot.absolute_address + 1);
                    code.push_back(static_cast<std::uint8_t>(high_address & 0xFF));
                    code.push_back(static_cast<std::uint8_t>(high_address >> 8));
                } else {
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_slot_reloc(operand_offset, slot, 1);
                }
            } else {
                code.push_back(0xA2);  // LDX #0
                code.push_back(0x00);
            }
        };
        auto emit_store_variable = [&](const VarSlot& slot) {
            code.push_back(0x8D);  // STA absolute
            std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            if (slot.absolute_address) {
                code.push_back(static_cast<std::uint8_t>(*slot.absolute_address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(*slot.absolute_address >> 8));
            } else {
                code.push_back(0x00);
                code.push_back(0x00);
                add_slot_reloc(operand_offset, slot, 0);
            }
            if (slot.is_card) {
                code.push_back(0x8E);  // STX absolute
                operand_offset = static_cast<std::uint16_t>(code.size());
                if (slot.absolute_address) {
                    const std::uint16_t high_address =
                        static_cast<std::uint16_t>(*slot.absolute_address + 1);
                    code.push_back(static_cast<std::uint8_t>(high_address & 0xFF));
                    code.push_back(static_cast<std::uint8_t>(high_address >> 8));
                } else {
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_slot_reloc(operand_offset, slot, 1);
                }
            }
        };
        auto emit_load_immediate = [&](ExprValue value) {
            code.push_back(0xA9);  // LDA #lo
            code.push_back(static_cast<std::uint8_t>(value & 0xFF));
            code.push_back(0xA2);  // LDX #hi
            code.push_back(static_cast<std::uint8_t>((value >> 8) & 0xFF));
        };
        auto emit_normalize_word_result = [&](ActionWordType type) {
            if (type == ActionWordType::Byte) {
                code.push_back(0xA2);  // LDX #0: BYTE expressions wrap at eight bits
                code.push_back(0x00);
            }
        };
        auto allocate_expr_temp = [&]() {
            const std::string prefix =
                upper_ascii(proc.name) + "_EXPR_" + std::to_string(next_expr_temp++);
            ExprTempSlot slot{
                prefix + "_VALUE_LO",
                prefix + "_VALUE_HI",
                prefix + "_POINTER_LO",
                prefix + "_POINTER_HI",
            };
            expr_temp_slots.push_back(slot);
            add_frame_byte(slot.value_lo_symbol, false);
            add_frame_byte(slot.value_hi_symbol, false);
            return slot;
        };
        auto emit_store_word = [&](const ExprTempSlot& slot) {
            code.push_back(0x8D);  // STA absolute
            std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, slot.value_lo_symbol);
            code.push_back(0x8E);  // STX absolute
            operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, slot.value_hi_symbol);
        };
        auto emit_load_absolute = [&](const std::string& symbol) {
            code.push_back(0xAD);  // LDA absolute
            const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, symbol);
        };
        std::function<void(std::string_view)> emit_load_word;
        std::function<std::optional<int>(const ParsedCall&)> emit_builtin;
        std::function<std::optional<int>(const ParsedCall&)> emit_external_routine_call;
        struct LocalCallResult {
            std::string return_type;
            std::optional<RealSlot> real;
        };
        std::function<std::optional<LocalCallResult>(const ParsedCall&)>
            emit_local_routine_call;
        std::function<RealSlot(std::string_view)> emit_real_expr;
        std::function<void(
            const ParsedExpr&,
            std::size_t,
            const std::map<std::string, ExprValue>&)> emit_expr_node;
        std::function<ActionWordType(const ParsedExpr&, std::size_t)> infer_word_type;
        infer_word_type = [&](const ParsedExpr& expr, std::size_t index) {
            const ExprNode& node = expr.nodes.at(index);
            if (node.kind == ExprNode::Kind::Constant) {
                return action_literal_type(node.value);
            }
            if (node.kind == ExprNode::Kind::StringLiteral ||
                node.kind == ExprNode::Kind::AddressOf) {
                return ActionWordType::Card;
            }
            if (node.kind == ExprNode::Kind::Variable) {
                auto variable = variables.find(node.name);
                if (variable != variables.end()) {
                    return variable->second.is_signed
                        ? ActionWordType::Int
                        : variable->second.is_card
                            ? ActionWordType::Card
                            : ActionWordType::Byte;
                }
                auto indirect = pointers.find(node.name);
                if (indirect != pointers.end() &&
                    node.name.find('.') != std::string::npos) {
                    return indexed_action_word_type(indirect->second);
                }
                auto constant_type = global_constant_types.find(node.name);
                if (constant_type != global_constant_types.end()) {
                    return constant_type->second;
                }
                if (local_names.count(node.name) != 0 ||
                    external_routines.count(node.name) != 0) {
                    return ActionWordType::Card;
                }
                if (record_addresses.count(node.name) != 0) {
                    return ActionWordType::Card;
                }
                auto value = constants.find(node.name);
                if (value != constants.end()) {
                    return action_literal_type(value->second);
                }
                throw ToolError("UNKNOWN VAR " + node.name);
            }
            if (node.kind == ExprNode::Kind::Dereference) {
                auto pointer = pointers.find(node.name);
                if (pointer == pointers.end()) {
                    throw ToolError("UNKNOWN POINTER " + node.name);
                }
                return indexed_action_word_type(pointer->second);
            }
            if (node.kind == ExprNode::Kind::Call) {
                auto array = arrays.find(node.name);
                if (array != arrays.end()) {
                    return indexed_action_word_type(array->second);
                }
                if (node.name == "INT") {
                    return ActionWordType::Int;
                }
                auto function = function_returns.find(node.name);
                if (function != function_returns.end()) {
                    if (function->second.type == "BYTE") return ActionWordType::Byte;
                    if (function->second.type == "INT") return ActionWordType::Int;
                    if (function->second.type == "CARD") return ActionWordType::Card;
                    throw ToolError("REAL VALUE IN WORD EXPR");
                }
                if (auto builtin = builtin_call(node.name)) {
                    if (builtin->return_width == 1) return ActionWordType::Byte;
                    if (builtin->return_width == 2) return ActionWordType::Card;
                }
                auto external = external_routines.find(node.name);
                if (external != external_routines.end()) {
                    if (external->second.return_type == "BYTE") return ActionWordType::Byte;
                    if (external->second.return_type == "INT") return ActionWordType::Int;
                    if (external->second.return_type == "CARD") return ActionWordType::Card;
                }
                throw ToolError("PROC USED AS VALUE " + node.name);
            }
            if (node.kind == ExprNode::Kind::Negate ||
                node.kind == ExprNode::Kind::Multiply ||
                node.kind == ExprNode::Kind::Divide ||
                node.kind == ExprNode::Kind::Modulo) {
                return ActionWordType::Int;
            }
            if (node.kind == ExprNode::Kind::ShiftLeft ||
                node.kind == ExprNode::Kind::ShiftRight) {
                return infer_word_type(expr, node.left);
            }
            return action_mixed_type(
                infer_word_type(expr, node.left),
                infer_word_type(expr, node.right));
        };
        std::function<std::optional<ExprValue>(
            const ParsedExpr&,
            std::size_t,
            const std::map<std::string, ExprValue>&)> evaluate_action_word;
        evaluate_action_word = [&](const ParsedExpr& expr,
                                   std::size_t index,
                                   const std::map<std::string, ExprValue>& values)
            -> std::optional<ExprValue> {
            const ExprNode& node = expr.nodes.at(index);
            const ActionWordType result_type = infer_word_type(expr, index);
            if (node.kind == ExprNode::Kind::Constant) {
                return normalize_action_word(node.value, result_type);
            }
            if (node.kind == ExprNode::Kind::Variable) {
                auto value = values.find(node.name);
                if (value == values.end()) {
                    return std::nullopt;
                }
                return normalize_action_word(value->second, result_type);
            }
            if (node.kind == ExprNode::Kind::Call ||
                node.kind == ExprNode::Kind::StringLiteral ||
                node.kind == ExprNode::Kind::AddressOf ||
                node.kind == ExprNode::Kind::Dereference) {
                return std::nullopt;
            }
            auto lhs = evaluate_action_word(expr, node.left, values);
            if (!lhs) {
                return std::nullopt;
            }
            if (node.kind == ExprNode::Kind::Negate) {
                return normalize_action_word(-*lhs, ActionWordType::Int);
            }
            auto rhs = evaluate_action_word(expr, node.right, values);
            if (!rhs) {
                return std::nullopt;
            }
            if (node.kind == ExprNode::Kind::Add) {
                return normalize_action_word(*lhs + *rhs, result_type);
            }
            if (node.kind == ExprNode::Kind::Subtract) {
                return normalize_action_word(*lhs - *rhs, result_type);
            }
            if (node.kind == ExprNode::Kind::Multiply) {
                const std::int32_t product =
                    static_cast<std::int16_t>(action_word_bits(*lhs)) *
                    static_cast<std::int16_t>(action_word_bits(*rhs));
                return normalize_action_word(product, ActionWordType::Int);
            }
            if (node.kind == ExprNode::Kind::Divide ||
                node.kind == ExprNode::Kind::Modulo) {
                const std::int32_t dividend =
                    static_cast<std::int16_t>(action_word_bits(*lhs));
                const std::int32_t divisor =
                    static_cast<std::int16_t>(action_word_bits(*rhs));
                if (divisor == 0) {
                    throw ToolError("DIV ZERO");
                }
                const std::int32_t value = node.kind == ExprNode::Kind::Modulo
                    ? dividend % divisor
                    : dividend / divisor;
                return normalize_action_word(value, ActionWordType::Int);
            }
            if (node.kind == ExprNode::Kind::BitAnd) {
                return normalize_action_word(
                    action_word_bits(*lhs) & action_word_bits(*rhs), result_type);
            }
            if (node.kind == ExprNode::Kind::BitOr) {
                return normalize_action_word(
                    action_word_bits(*lhs) | action_word_bits(*rhs), result_type);
            }
            if (node.kind == ExprNode::Kind::BitXor) {
                return normalize_action_word(
                    action_word_bits(*lhs) ^ action_word_bits(*rhs), result_type);
            }
            if (*rhs < 0) {
                throw ToolError("SHIFT RANGE");
            }
            const unsigned width = infer_word_type(expr, node.left) ==
                    ActionWordType::Byte
                ? 8U
                : 16U;
            const std::uint32_t value = *rhs >= width
                ? 0U
                : node.kind == ExprNode::Kind::ShiftLeft
                    ? static_cast<std::uint32_t>(action_word_bits(*lhs)) <<
                        static_cast<unsigned>(*rhs)
                    : static_cast<std::uint32_t>(action_word_bits(*lhs)) >>
                        static_cast<unsigned>(*rhs);
            return normalize_action_word(value, result_type);
        };
        auto try_evaluate_action_word = [&](std::string_view text,
                                            const std::map<std::string, ExprValue>& values)
            -> std::optional<ExprValue> {
            try {
                const ParsedExpr expr = WordExprParser(text).parse();
                return evaluate_action_word(expr, expr.root, values);
            } catch (const ToolError&) {
                return std::nullopt;
            }
        };
        auto infer_word_text_type = [&](std::string_view text) {
            const ParsedExpr expr = WordExprParser(text).parse();
            return infer_word_type(expr, expr.root);
        };
        auto emit_load_linked_address = [&](const std::string& target_symbol,
                                            std::int32_t addend = 0) {
            const std::string prefix =
                upper_ascii(proc.name) + "_ADDRESS_" +
                std::to_string(next_address_constant++);
            AddressConstantSlot address{
                prefix + "_LO",
                prefix + "_HI",
                target_symbol,
                addend,
            };
            address_constant_slots.push_back(address);
            emit_load_absolute(address.lo_symbol);
            code.push_back(0xAE);  // LDX absolute
            const std::uint16_t operand_offset =
                static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, address.hi_symbol);
        };
        auto emit_load_address_of = [&](const VarSlot& slot) {
            if (slot.absolute_address) {
                emit_load_immediate(*slot.absolute_address);
                return;
            }
            emit_load_linked_address(
                slot.bound_address_symbol.empty()
                    ? slot.lo_symbol
                    : slot.bound_address_symbol,
                slot.bound_address_symbol.empty() ? 0 : slot.bound_address_addend);
        };
        auto emit_load_real_address_of = [&](const RealSlot& slot) {
            if (slot.absolute_address) {
                emit_load_immediate(*slot.absolute_address);
                return;
            }
            emit_load_absolute(slot.pointer_lo_symbol);
            code.push_back(0xAE);  // LDX absolute
            const std::uint16_t operand_offset =
                static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, slot.pointer_hi_symbol);
        };
        auto emit_load_record_address = [&](const RecordAddressSlot& record) {
            if (record.absolute_address) {
                emit_load_immediate(*record.absolute_address);
                return;
            }
            emit_load_linked_address(record.target_symbol, record.target_addend);
        };
        auto emit_prepare_pointer = [&](const IndexedSlot& indexed) {
            emit_load_variable(indexed.pointer);
            if (indexed.byte_offset != 0) {
                code.push_back(0x18);  // CLC
                code.push_back(0x69);  // ADC #field offset low
                code.push_back(static_cast<std::uint8_t>(indexed.byte_offset & 0xFF));
                code.push_back(0x48);  // PHA
                code.push_back(0x8A);  // TXA
                code.push_back(0x69);  // ADC #field offset high
                code.push_back(static_cast<std::uint8_t>(indexed.byte_offset >> 8));
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA
            }
            code.push_back(0x85);  // STA $0A
            code.push_back(0x0A);
            code.push_back(0x86);  // STX $0B
            code.push_back(0x0B);
        };
        auto emit_add_pointer_byte = [&](
            std::uint8_t opcode,
            const VarSlot& pointer,
            bool high) {
            code.push_back(opcode);
            const std::uint16_t operand_offset =
                static_cast<std::uint16_t>(code.size());
            if (pointer.absolute_address) {
                const std::uint16_t address = static_cast<std::uint16_t>(
                    *pointer.absolute_address + (high ? 1 : 0));
                code.push_back(static_cast<std::uint8_t>(address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(address >> 8));
            } else {
                code.push_back(0x00);
                code.push_back(0x00);
                add_slot_reloc(operand_offset, pointer, high ? 1 : 0);
            }
        };
        auto emit_prepare_indexed = [&](
            const IndexedSlot& indexed,
            std::string_view index_expression) {
            emit_load_word(index_expression);
            for (std::size_t width = indexed.element_width(); width > 1; width >>= 1) {
                code.push_back(0x0A);  // ASL A
                code.push_back(0x48);  // PHA
                code.push_back(0x8A);  // TXA
                code.push_back(0x2A);  // ROL A
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA
            }
            code.push_back(0x18);  // CLC
            emit_add_pointer_byte(0x6D, indexed.pointer, false);  // ADC pointer low
            code.push_back(0x85);  // STA $0A
            code.push_back(0x0A);
            code.push_back(0x8A);  // TXA
            emit_add_pointer_byte(0x6D, indexed.pointer, true);  // ADC pointer high
            code.push_back(0x85);  // STA $0B
            code.push_back(0x0B);
        };
        auto emit_load_indirect = [&](const IndexedSlot& indexed) {
            if (indexed.element_is_real()) {
                throw ToolError("REAL INDIRECT IN WORD EXPR");
            }
            code.push_back(0xA0);  // LDY #0
            code.push_back(0x00);
            code.push_back(0xB1);  // LDA ($0A),Y
            code.push_back(0x0A);
            if (indexed.element_width() == 2) {
                code.push_back(0x48);  // PHA low
                code.push_back(0xC8);  // INY
                code.push_back(0xB1);  // LDA ($0A),Y
                code.push_back(0x0A);
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA low
            } else {
                code.push_back(0xA2);  // LDX #0
                code.push_back(0x00);
            }
        };
        auto emit_store_indirect = [&](
            const IndexedSlot& indexed,
            const ExprTempSlot& value) {
            if (indexed.element_is_real()) {
                throw ToolError("REAL INDIRECT WORD STORE");
            }
            emit_load_absolute(value.value_lo_symbol);
            code.push_back(0xA0);  // LDY #0
            code.push_back(0x00);
            code.push_back(0x91);  // STA ($0A),Y
            code.push_back(0x0A);
            if (indexed.element_width() == 2) {
                code.push_back(0xC8);  // INY
                emit_load_absolute(value.value_hi_symbol);
                code.push_back(0x91);  // STA ($0A),Y
                code.push_back(0x0A);
            }
        };
        auto allocate_string_literal = [&](const std::string& value) {
            if (value.size() > 255) {
                throw ToolError("STRING SIZE RANGE");
            }
            const std::string name =
                "__STRING_" + std::to_string(next_string_literal++);
            const std::string prefix = upper_ascii(proc.name) + "_" + name;
            ArraySlot slot;
            slot.indexed.pointer = VarSlot{
                name,
                prefix + "_PTR_LO",
                prefix + "_PTR_HI",
                true,
            };
            slot.data_symbol = prefix + "_DATA";
            slot.initial_data.push_back(static_cast<std::uint8_t>(value.size()));
            slot.initial_data.insert(
                slot.initial_data.end(), value.begin(), value.end());
            const VarSlot pointer = slot.indexed.pointer;
            array_slots.push_back(std::move(slot));
            return pointer;
        };
        emit_expr_node = [&](const ParsedExpr& expr,
                             std::size_t index,
                             const std::map<std::string, ExprValue>& fold_constants) {
            if (auto value = evaluate_action_word(expr, index, fold_constants)) {
                emit_load_immediate(*value);
                return;
            }

            const ExprNode& node = expr.nodes.at(index);
            if (node.kind == ExprNode::Kind::StringLiteral) {
                emit_load_variable(allocate_string_literal(node.name));
                return;
            }
            if (node.kind == ExprNode::Kind::Variable) {
                auto variable = variables.find(node.name);
                if (variable != variables.end()) {
                    emit_load_variable(variable->second);
                    return;
                }
                auto indirect_field = pointers.find(node.name);
                if (indirect_field != pointers.end() &&
                    node.name.find('.') != std::string::npos) {
                    emit_prepare_pointer(indirect_field->second);
                    emit_load_indirect(indirect_field->second);
                    return;
                }
                auto record = record_addresses.find(node.name);
                if (record != record_addresses.end()) {
                    emit_load_record_address(record->second);
                    return;
                }
                auto external_routine = external_routines.find(node.name);
                if (external_routine != external_routines.end()) {
                    if (external_routine->second.absolute_address) {
                        emit_load_immediate(
                            *external_routine->second.absolute_address);
                    } else {
                        emit_load_linked_address(
                            external_routine->second.linked_address_symbol,
                            external_routine->second.linked_address_addend);
                    }
                    return;
                }
                if (local_names.count(node.name) != 0) {
                    code.push_back(0xAD);  // LDA routine JMP target low
                    std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, node.name, 1);
                    code.push_back(0xAE);  // LDX routine JMP target high
                    operand_offset = static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, node.name, 2);
                    return;
                }
                throw ToolError("UNKNOWN VAR");
            }
            if (node.kind == ExprNode::Kind::AddressOf) {
                const ExprNode& target = expr.nodes.at(node.left);
                if (target.kind == ExprNode::Kind::Call) {
                    auto array = arrays.find(target.name);
                    if (array == arrays.end() || target.arguments.size() != 1) {
                        throw ToolError("BAD ADDRESS EXPR");
                    }
                    emit_prepare_indexed(array->second, target.arguments.front());
                    code.push_back(0xA5);  // LDA $0A
                    code.push_back(0x0A);
                    code.push_back(0xA6);  // LDX $0B
                    code.push_back(0x0B);
                    return;
                }
                if (target.kind == ExprNode::Kind::Dereference) {
                    auto pointer = pointers.find(target.name);
                    if (pointer == pointers.end()) {
                        throw ToolError("BAD ADDRESS EXPR");
                    }
                    emit_load_variable(pointer->second.pointer);
                    return;
                }
                if (target.kind != ExprNode::Kind::Variable) {
                    throw ToolError("BAD ADDRESS EXPR");
                }
                auto variable = variables.find(target.name);
                if (variable != variables.end()) {
                    emit_load_address_of(variable->second);
                    return;
                }
                auto real_variable = real_variables.find(target.name);
                if (real_variable != real_variables.end()) {
                    emit_load_real_address_of(real_variable->second);
                    return;
                }
                auto record = record_addresses.find(target.name);
                if (record != record_addresses.end()) {
                    emit_load_record_address(record->second);
                    return;
                }
                auto indirect_field = pointers.find(target.name);
                if (indirect_field != pointers.end() &&
                    target.name.find('.') != std::string::npos) {
                    emit_prepare_pointer(indirect_field->second);
                    code.push_back(0xA5);  // LDA $0A
                    code.push_back(0x0A);
                    code.push_back(0xA6);  // LDX $0B
                    code.push_back(0x0B);
                    return;
                }
                throw ToolError("UNKNOWN VAR");
            }
            if (node.kind == ExprNode::Kind::Dereference) {
                auto pointer = pointers.find(node.name);
                if (pointer == pointers.end()) {
                    throw ToolError("UNKNOWN POINTER " + node.name);
                }
                emit_prepare_pointer(pointer->second);
                emit_load_indirect(pointer->second);
                return;
            }
            if (node.kind == ExprNode::Kind::Call) {
                auto array = arrays.find(node.name);
                if (array != arrays.end()) {
                    if (node.arguments.size() != 1) {
                        throw ToolError("BAD ARRAY INDEX " + node.name);
                    }
                    emit_prepare_indexed(array->second, node.arguments.front());
                    emit_load_indirect(array->second);
                    return;
                }
                auto return_width = emit_builtin(ParsedCall{node.name, node.arguments});
                if (return_width) {
                    if (*return_width == 0) {
                        throw ToolError("PROC HAS NO VALUE " + node.name);
                    }
                    return;
                }
                return_width = emit_external_routine_call(
                    ParsedCall{node.name, node.arguments});
                if (return_width) {
                    if (*return_width == 0) {
                        throw ToolError("PROC HAS NO VALUE " + node.name);
                    }
                    return;
                }
                auto local_result = emit_local_routine_call(
                    ParsedCall{node.name, node.arguments});
                if (!local_result) {
                    throw ToolError("UNSUPPORTED CALL " + node.name);
                }
                if (local_result->return_type.empty()) {
                    throw ToolError("PROC HAS NO VALUE " + node.name);
                }
                if (local_result->return_type == "REAL") {
                    throw ToolError("REAL FUNC IN WORD EXPR " + node.name);
                }
                return;
            }
            if (node.kind == ExprNode::Kind::Negate) {
                emit_expr_node(expr, node.left, fold_constants);
                code.push_back(0x49);  // EOR #$FF
                code.push_back(0xFF);
                code.push_back(0x18);  // CLC
                code.push_back(0x69);  // ADC #1
                code.push_back(0x01);
                code.push_back(0x48);  // PHA
                code.push_back(0x8A);  // TXA
                code.push_back(0x49);  // EOR #$FF
                code.push_back(0xFF);
                code.push_back(0x69);  // ADC #0 with carry from low byte
                code.push_back(0x00);
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA
                return;
            }
            if (node.kind == ExprNode::Kind::Constant) {
                emit_load_immediate(node.value);
                return;
            }

            if (node.kind == ExprNode::Kind::Add || node.kind == ExprNode::Kind::Subtract) {
                const bool subtract = node.kind == ExprNode::Kind::Subtract;
                auto emit_add_sub_high = [&](bool absolute, const std::string& symbol, ExprValue value) {
                    code.push_back(subtract ? (absolute ? 0xED : 0xE9)
                                            : (absolute ? 0x6D : 0x69));
                    if (absolute) {
                        const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                        code.push_back(0x00);
                        code.push_back(0x00);
                        add_reloc(operand_offset, symbol);
                    } else {
                        code.push_back(static_cast<std::uint8_t>((value >> 8) & 0xFF));
                    }
                };
                if (auto rhs_value = evaluate_action_word(
                        expr, node.right, fold_constants)) {
                    emit_expr_node(expr, node.left, fold_constants);
                    code.push_back(subtract ? 0x38 : 0x18);  // SEC/CLC
                    code.push_back(subtract ? 0xE9 : 0x69);  // SBC/ADC immediate low
                    code.push_back(static_cast<std::uint8_t>(*rhs_value & 0xFF));
                    code.push_back(0x48);  // PHA
                    code.push_back(0x8A);  // TXA
                    emit_add_sub_high(false, {}, *rhs_value);
                    code.push_back(0xAA);  // TAX
                    code.push_back(0x68);  // PLA
                    emit_normalize_word_result(infer_word_type(expr, index));
                    return;
                }
                const ExprNode& rhs_node = expr.nodes.at(node.right);
                if (rhs_node.kind == ExprNode::Kind::Variable) {
                    auto rhs_variable = variables.find(rhs_node.name);
                    if (rhs_variable != variables.end()) {
                        emit_expr_node(expr, node.left, fold_constants);
                        code.push_back(subtract ? 0x38 : 0x18);  // SEC/CLC
                        code.push_back(subtract ? 0xED : 0x6D);  // SBC/ADC absolute low
                        std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                        if (rhs_variable->second.absolute_address) {
                            code.push_back(static_cast<std::uint8_t>(
                                *rhs_variable->second.absolute_address & 0xFF));
                            code.push_back(static_cast<std::uint8_t>(
                                *rhs_variable->second.absolute_address >> 8));
                        } else {
                            code.push_back(0x00);
                            code.push_back(0x00);
                            add_slot_reloc(
                                operand_offset, rhs_variable->second, 0);
                        }
                        code.push_back(0x48);  // PHA
                        code.push_back(0x8A);  // TXA
                        if (rhs_variable->second.is_card) {
                            code.push_back(subtract ? 0xED : 0x6D);  // SBC/ADC absolute high
                            operand_offset = static_cast<std::uint16_t>(code.size());
                            if (rhs_variable->second.absolute_address) {
                                const std::uint16_t high_address = static_cast<std::uint16_t>(
                                    *rhs_variable->second.absolute_address + 1);
                                code.push_back(static_cast<std::uint8_t>(high_address & 0xFF));
                                code.push_back(static_cast<std::uint8_t>(high_address >> 8));
                            } else {
                                code.push_back(0x00);
                                code.push_back(0x00);
                                add_slot_reloc(
                                    operand_offset, rhs_variable->second, 1);
                            }
                        } else {
                            emit_add_sub_high(false, {}, 0);
                        }
                        code.push_back(0xAA);  // TAX
                        code.push_back(0x68);  // PLA
                        emit_normalize_word_result(infer_word_type(expr, index));
                        return;
                    }
                }
            }

            const ExprTempSlot temp = allocate_expr_temp();
            emit_expr_node(expr, node.right, fold_constants);
            emit_store_word(temp);
            emit_expr_node(expr, node.left, fold_constants);

            if (node.kind == ExprNode::Kind::Add || node.kind == ExprNode::Kind::Subtract) {
                const bool subtract = node.kind == ExprNode::Kind::Subtract;
                code.push_back(subtract ? 0x38 : 0x18);  // SEC/CLC
                code.push_back(subtract ? 0xED : 0x6D);  // SBC/ADC absolute low
                std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, temp.value_lo_symbol);
                code.push_back(0x48);  // PHA
                code.push_back(0x8A);  // TXA
                code.push_back(subtract ? 0xED : 0x6D);  // SBC/ADC absolute high
                operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, temp.value_hi_symbol);
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA
                emit_normalize_word_result(infer_word_type(expr, index));
                return;
            }

            if (node.kind == ExprNode::Kind::BitAnd ||
                node.kind == ExprNode::Kind::BitOr ||
                node.kind == ExprNode::Kind::BitXor) {
                const std::uint8_t opcode = node.kind == ExprNode::Kind::BitAnd
                    ? 0x2D  // AND absolute
                    : node.kind == ExprNode::Kind::BitOr
                        ? 0x0D  // ORA absolute
                        : 0x4D; // EOR absolute
                code.push_back(opcode);
                std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, temp.value_lo_symbol);
                code.push_back(0x48);  // PHA low result
                code.push_back(0x8A);  // TXA high lhs
                code.push_back(opcode);
                operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, temp.value_hi_symbol);
                code.push_back(0xAA);  // TAX high result
                code.push_back(0x68);  // PLA low result
                emit_normalize_word_result(infer_word_type(expr, index));
                return;
            }

            if (node.kind == ExprNode::Kind::ShiftLeft ||
                node.kind == ExprNode::Kind::ShiftRight) {
                const std::uint8_t width =
                    infer_word_type(expr, node.left) == ActionWordType::Byte ? 8 : 16;
                code.push_back(0x48);  // PHA: preserve lhs while checking count
                code.push_back(0x8A);  // TXA
                code.push_back(0x48);  // PHA
                emit_load_absolute(temp.value_hi_symbol);
                code.push_back(0xD0);  // BNE zero result
                const std::size_t high_nonzero_operand = code.size();
                code.push_back(0x00);
                code.push_back(0xAC);  // LDY absolute shift count low byte
                std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, temp.value_lo_symbol);
                code.push_back(0xC0);  // CPY #word width
                code.push_back(width);
                code.push_back(0xB0);  // BCS zero result
                const std::size_t too_large_operand = code.size();
                code.push_back(0x00);
                code.push_back(0x68);  // PLA high lhs
                code.push_back(0xAA);  // TAX
                code.push_back(0x68);  // PLA low lhs
                code.push_back(0xF0);  // BEQ done
                const std::size_t zero_count_operand = code.size();
                code.push_back(0x00);
                const std::size_t loop_offset = code.size();
                if (node.kind == ExprNode::Kind::ShiftLeft) {
                    code.push_back(0x0A);  // ASL low
                    code.push_back(0x48);  // PHA
                    code.push_back(0x8A);  // TXA
                    code.push_back(0x2A);  // ROL high
                    code.push_back(0xAA);  // TAX
                    code.push_back(0x68);  // PLA
                } else {
                    code.push_back(0x48);  // PHA low
                    code.push_back(0x8A);  // TXA high
                    code.push_back(0x4A);  // LSR high
                    code.push_back(0xAA);  // TAX
                    code.push_back(0x68);  // PLA low
                    code.push_back(0x6A);  // ROR low
                }
                code.push_back(0x88);  // DEY
                code.push_back(0xD0);  // BNE loop
                const std::size_t loop_operand = code.size();
                code.push_back(0x00);
                const std::string shift_done_label =
                    new_control_label("SHIFT_DONE");
                code.push_back(0x4C);  // JMP done past zero-result cleanup
                const std::uint16_t loop_done_operand =
                    static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(loop_done_operand, shift_done_label);
                const std::size_t zero_offset = code.size();
                code.push_back(0x68);  // discard saved high lhs
                code.push_back(0x68);  // discard saved low lhs
                code.push_back(0xA9);  // LDA #0
                code.push_back(0x00);
                code.push_back(0xA2);  // LDX #0
                code.push_back(0x00);
                const std::size_t done_offset = code.size();
                const auto loop_delta = static_cast<std::ptrdiff_t>(loop_offset) -
                    static_cast<std::ptrdiff_t>(loop_operand + 1);
                const auto high_nonzero_delta =
                    static_cast<std::ptrdiff_t>(zero_offset) -
                    static_cast<std::ptrdiff_t>(high_nonzero_operand + 1);
                const auto too_large_delta =
                    static_cast<std::ptrdiff_t>(zero_offset) -
                    static_cast<std::ptrdiff_t>(too_large_operand + 1);
                const auto zero_count_delta =
                    static_cast<std::ptrdiff_t>(done_offset) -
                    static_cast<std::ptrdiff_t>(zero_count_operand + 1);
                if (loop_delta < -128 || loop_delta > 127 ||
                    high_nonzero_delta < -128 || high_nonzero_delta > 127 ||
                    too_large_delta < -128 || too_large_delta > 127 ||
                    zero_count_delta < -128 || zero_count_delta > 127) {
                    throw ToolError("SHIFT EMISSION RANGE");
                }
                code[loop_operand] = static_cast<std::uint8_t>(loop_delta & 0xFF);
                code[high_nonzero_operand] =
                    static_cast<std::uint8_t>(high_nonzero_delta & 0xFF);
                code[too_large_operand] =
                    static_cast<std::uint8_t>(too_large_delta & 0xFF);
                code[zero_count_operand] =
                    static_cast<std::uint8_t>(zero_count_delta & 0xFF);
                define_control_label(shift_done_label);
                emit_normalize_word_result(infer_word_type(expr, index));
                return;
            }

            if (node.kind == ExprNode::Kind::Divide ||
                node.kind == ExprNode::Kind::Modulo) {
                const ExprTempSlot lhs = allocate_expr_temp();
                const ExprTempSlot sign = allocate_expr_temp();
                emit_store_word(lhs);
                auto emit_store_accumulator = [&](const std::string& symbol) {
                    code.push_back(0x8D);  // STA absolute
                    const std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, symbol);
                };
                auto emit_negate_slot = [&](const ExprTempSlot& slot) {
                    emit_load_absolute(slot.value_lo_symbol);
                    code.push_back(0x49);  // EOR #$FF
                    code.push_back(0xFF);
                    code.push_back(0x18);  // CLC
                    code.push_back(0x69);  // ADC #1
                    code.push_back(0x01);
                    emit_store_accumulator(slot.value_lo_symbol);
                    emit_load_absolute(slot.value_hi_symbol);
                    code.push_back(0x49);  // EOR #$FF
                    code.push_back(0xFF);
                    code.push_back(0x69);  // ADC #0 plus low-byte carry
                    code.push_back(0x00);
                    emit_store_accumulator(slot.value_hi_symbol);
                };
                auto emit_absolute_slot = [&](const ExprTempSlot& slot) {
                    emit_load_absolute(slot.value_hi_symbol);
                    code.push_back(0x10);  // BPL already positive
                    const std::size_t branch_operand = code.size();
                    code.push_back(0x00);
                    emit_negate_slot(slot);
                    const std::ptrdiff_t delta =
                        static_cast<std::ptrdiff_t>(code.size()) -
                        static_cast<std::ptrdiff_t>(branch_operand + 1);
                    if (delta > 127) {
                        throw ToolError("SIGNED DIV EMISSION RANGE");
                    }
                    code[branch_operand] = static_cast<std::uint8_t>(delta);
                };

                emit_load_absolute(lhs.value_hi_symbol);
                if (node.kind == ExprNode::Kind::Divide) {
                    code.push_back(0x4D);  // EOR rhs high for quotient sign
                    const std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, temp.value_hi_symbol);
                }
                code.push_back(0x29);  // AND #$80
                code.push_back(0x80);
                emit_store_accumulator(sign.value_lo_symbol);
                emit_absolute_slot(lhs);
                emit_absolute_slot(temp);

                emit_load_absolute(temp.pointer_lo_symbol);
                code.push_back(0x85);  // STA $02
                code.push_back(0x02);
                emit_load_absolute(temp.pointer_hi_symbol);
                code.push_back(0x85);  // STA $03
                code.push_back(0x03);
                emit_load_absolute(lhs.value_lo_symbol);
                code.push_back(0xAE);  // LDX lhs high
                std::uint16_t operand_offset =
                    static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, lhs.value_hi_symbol);
                emit_jsr_import(
                    node.kind == ExprNode::Kind::Modulo ? "RT_I_MOD" : "RT_I_DIV");
                emit_store_word(lhs);
                emit_load_absolute(sign.value_lo_symbol);
                code.push_back(0x10);  // BPL result already has correct sign
                const std::size_t result_branch_operand = code.size();
                code.push_back(0x00);
                emit_negate_slot(lhs);
                const std::ptrdiff_t result_delta =
                    static_cast<std::ptrdiff_t>(code.size()) -
                    static_cast<std::ptrdiff_t>(result_branch_operand + 1);
                if (result_delta > 127) {
                    throw ToolError("SIGNED DIV EMISSION RANGE");
                }
                code[result_branch_operand] =
                    static_cast<std::uint8_t>(result_delta);
                emit_load_absolute(lhs.value_lo_symbol);
                code.push_back(0xAE);  // LDX result high
                operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, lhs.value_hi_symbol);
                return;
            }

            // Integer product/division helpers take the left word in A/X and a pointer to
            // the right word in zero-page $02/$03, returning the result in A/X.
            code.push_back(0x48);  // PHA low
            code.push_back(0x8A);  // TXA
            code.push_back(0x48);  // PHA high
            emit_load_absolute(temp.pointer_lo_symbol);
            code.push_back(0x85);  // STA $02
            code.push_back(0x02);
            emit_load_absolute(temp.pointer_hi_symbol);
            code.push_back(0x85);  // STA $03
            code.push_back(0x03);
            code.push_back(0x68);  // PLA high
            code.push_back(0xAA);  // TAX
            code.push_back(0x68);  // PLA low
            emit_jsr_import(
                node.kind == ExprNode::Kind::Multiply
                    ? "RT_I_MUL"
                    : node.kind == ExprNode::Kind::Modulo
                        ? "RT_I_MOD"
                        : "RT_I_DIV");
        };
        emit_load_word = [&](std::string_view text) {
            const ParsedExpr expr = WordExprParser(text).parse();
            std::map<std::string, ExprValue> fold_constants = constants;
            for (const auto& variable : variables) {
                fold_constants.erase(variable.first);
            }
            emit_expr_node(expr, expr.root, fold_constants);
        };
        auto emit_real_byte_access = [&](
            std::uint8_t opcode,
            const RealSlot& slot,
            std::size_t index) {
            if (index >= 4 || slot.byte_symbols.size() != 4) {
                throw ToolError("BAD REAL SLOT");
            }
            code.push_back(opcode);
            const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            if (slot.absolute_address) {
                const std::uint16_t address = static_cast<std::uint16_t>(
                    *slot.absolute_address + static_cast<std::uint16_t>(index));
                code.push_back(static_cast<std::uint8_t>(address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(address >> 8));
            } else {
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, slot.byte_symbols[index]);
            }
        };
        auto emit_load_real_indirect = [&](const RealSlot& destination) {
            for (std::size_t i = 0; i < 4; ++i) {
                code.push_back(0xA0);  // LDY #element byte
                code.push_back(static_cast<std::uint8_t>(i));
                code.push_back(0xB1);  // LDA ($0A),Y
                code.push_back(0x0A);
                emit_real_byte_access(0x8D, destination, i);  // STA absolute
            }
        };
        auto emit_store_real_indirect = [&](const RealSlot& source) {
            for (std::size_t i = 0; i < 4; ++i) {
                emit_real_byte_access(0xAD, source, i);  // LDA absolute
                code.push_back(0xA0);  // LDY #element byte
                code.push_back(static_cast<std::uint8_t>(i));
                code.push_back(0x91);  // STA ($0A),Y
                code.push_back(0x0A);
            }
        };
        auto emit_real_copy = [&](const RealSlot& source, const RealSlot& destination) {
            if (source.pointer_lo_symbol == destination.pointer_lo_symbol) {
                return;
            }
            for (std::size_t i = 0; i < 4; ++i) {
                emit_real_byte_access(0xAD, source, i);  // LDA absolute
                emit_real_byte_access(0x8D, destination, i);  // STA absolute
            }
        };
        auto emit_set_real_pointer = [&](const RealSlot& slot, std::uint8_t zero_page) {
            emit_load_absolute(slot.pointer_lo_symbol);
            code.push_back(0x85);  // STA zero page
            code.push_back(zero_page);
            emit_load_absolute(slot.pointer_hi_symbol);
            code.push_back(0x85);  // STA zero page
            code.push_back(static_cast<std::uint8_t>(zero_page + 1));
        };
        auto allocate_real_temp = [&](std::optional<double> initial = std::nullopt) {
            const std::string name =
                "__REAL_TEMP_" + std::to_string(next_real_temp++);
            RealSlot slot = make_real_slot(
                name,
                upper_ascii(proc.name) + "_" + name,
                "STORAGE",
                "",
                0);
            if (initial) {
                slot.initial_value = real32_bytes(*initial);
            }
            real_slots.push_back(slot);
            add_frame_real(slot, false);
            return slot;
        };
        auto emit_prepared_indirect_as_real = [&](const IndexedSlot& indexed) {
            RealSlot destination = allocate_real_temp();
            if (indexed.element_is_real()) {
                emit_load_real_indirect(destination);
                return destination;
            }
            emit_load_indirect(indexed);
            emit_set_real_pointer(destination, 0x02);
            emit_jsr_import(
                indexed.element_is_signed() ? "RT_S_TO_F" : "RT_I_TO_F");
            return destination;
        };
        std::function<RealSlot(const ParsedRealExpr&, std::size_t)> emit_real_expr_node;
        emit_real_expr_node = [&](const ParsedRealExpr& expr, std::size_t index) -> RealSlot {
            if (auto value = evaluate_real_expr_node(expr, index, real_constants)) {
                return allocate_real_temp(*value);
            }

            const RealExprNode& node = expr.nodes.at(index);
            if (node.kind == RealExprNode::Kind::Variable) {
                auto real_variable = real_variables.find(node.name);
                if (real_variable != real_variables.end()) {
                    return real_variable->second;
                }
                auto integer_variable = variables.find(node.name);
                if (integer_variable == variables.end()) {
                    throw ToolError("UNKNOWN REAL VAR " + node.name);
                }
                RealSlot destination = allocate_real_temp();
                emit_set_real_pointer(destination, 0x02);
                emit_load_variable(integer_variable->second);
                emit_jsr_import(
                    integer_variable->second.is_signed ? "RT_S_TO_F" : "RT_I_TO_F");
                return destination;
            }
            if (node.kind == RealExprNode::Kind::Dereference) {
                auto pointer = pointers.find(node.name);
                if (pointer == pointers.end()) {
                    throw ToolError("UNKNOWN POINTER " + node.name);
                }
                emit_prepare_pointer(pointer->second);
                return emit_prepared_indirect_as_real(pointer->second);
            }
            if (node.kind == RealExprNode::Kind::Call) {
                const ParsedCall call{node.name, node.arguments};
                auto array = arrays.find(node.name);
                if (array != arrays.end()) {
                    if (node.arguments.size() != 1) {
                        throw ToolError("BAD ARRAY INDEX " + node.name);
                    }
                    emit_prepare_indexed(array->second, node.arguments.front());
                    return emit_prepared_indirect_as_real(array->second);
                }
                if (auto return_width = emit_builtin(call)) {
                    if (*return_width == 0) {
                        throw ToolError("PROC HAS NO VALUE " + node.name);
                    }
                    RealSlot destination = allocate_real_temp();
                    emit_set_real_pointer(destination, 0x02);
                    emit_jsr_import("RT_I_TO_F");
                    return destination;
                }
                if (auto return_width = emit_external_routine_call(call)) {
                    if (*return_width == 0) {
                        throw ToolError("PROC HAS NO VALUE " + node.name);
                    }
                    RealSlot destination = allocate_real_temp();
                    emit_set_real_pointer(destination, 0x02);
                    emit_jsr_import("RT_I_TO_F");
                    return destination;
                }
                auto local_result = emit_local_routine_call(call);
                if (!local_result) {
                    throw ToolError("UNSUPPORTED REAL CALL " + node.name);
                }
                if (local_result->return_type.empty()) {
                    throw ToolError("PROC HAS NO VALUE " + node.name);
                }
                RealSlot destination = allocate_real_temp();
                if (local_result->return_type == "REAL") {
                    if (!local_result->real) {
                        throw ToolError("BAD FUNC ABI " + node.name);
                    }
                    emit_real_copy(*local_result->real, destination);
                } else {
                    emit_set_real_pointer(destination, 0x02);
                    emit_jsr_import(
                        local_result->return_type == "INT"
                            ? "RT_S_TO_F"
                            : "RT_I_TO_F");
                }
                return destination;
            }

            const RealSlot lhs = emit_real_expr_node(expr, node.left);
            if (node.kind == RealExprNode::Kind::Cast) {
                return lhs;
            }
            RealSlot destination = allocate_real_temp();
            if (node.kind == RealExprNode::Kind::Negate) {
                emit_real_copy(lhs, destination);
                emit_real_byte_access(0xAD, destination, 3);  // LDA absolute
                code.push_back(0x49);  // EOR #$80
                code.push_back(0x80);
                emit_real_byte_access(0x8D, destination, 3);  // STA absolute
                return destination;
            }
            if (node.kind == RealExprNode::Kind::Absolute ||
                node.kind == RealExprNode::Kind::SquareRoot ||
                node.kind == RealExprNode::Kind::Truncate ||
                node.kind == RealExprNode::Kind::Floor ||
                node.kind == RealExprNode::Kind::Ceiling ||
                node.kind == RealExprNode::Kind::Round ||
                node.kind == RealExprNode::Kind::Fraction ||
                node.kind == RealExprNode::Kind::DegreesToRadians ||
                node.kind == RealExprNode::Kind::RadiansToDegrees) {
                emit_set_real_pointer(lhs, 0x02);
                emit_set_real_pointer(destination, 0x06);
                const char* helper = "RT_F_TRUNC";
                if (node.kind == RealExprNode::Kind::Absolute) {
                    helper = "RT_F_ABS";
                } else if (node.kind == RealExprNode::Kind::SquareRoot) {
                    helper = "RT_F_SQRT";
                } else if (node.kind == RealExprNode::Kind::Floor) {
                    helper = "RT_F_FLOOR";
                } else if (node.kind == RealExprNode::Kind::Ceiling) {
                    helper = "RT_F_CEIL";
                } else if (node.kind == RealExprNode::Kind::Round) {
                    helper = "RT_F_ROUND";
                } else if (node.kind == RealExprNode::Kind::Fraction) {
                    helper = "RT_F_FRAC";
                } else if (node.kind == RealExprNode::Kind::DegreesToRadians) {
                    helper = "RT_F_DEG_TO_RAD";
                } else if (node.kind == RealExprNode::Kind::RadiansToDegrees) {
                    helper = "RT_F_RAD_TO_DEG";
                }
                emit_jsr_import(helper);
                return destination;
            }

            const RealSlot rhs = emit_real_expr_node(expr, node.right);
            emit_set_real_pointer(lhs, 0x02);
            emit_set_real_pointer(rhs, 0x04);
            emit_set_real_pointer(destination, 0x06);
            std::string helper;
            if (node.kind == RealExprNode::Kind::Add) {
                helper = "RT_F_ADD";
            } else if (node.kind == RealExprNode::Kind::Subtract) {
                helper = "RT_F_SUB";
            } else if (node.kind == RealExprNode::Kind::Multiply) {
                helper = "RT_F_MUL";
            } else if (node.kind == RealExprNode::Kind::Divide) {
                helper = "RT_F_DIV";
            } else if (node.kind == RealExprNode::Kind::Modulus) {
                helper = "RT_F_MOD";
            } else if (node.kind == RealExprNode::Kind::Hypotenuse) {
                helper = "RT_F_HYPOT";
            } else if (node.kind == RealExprNode::Kind::Minimum) {
                helper = "RT_F_MIN";
            } else if (node.kind == RealExprNode::Kind::Maximum) {
                helper = "RT_F_MAX";
            } else {
                throw ToolError("BAD REAL EXPR");
            }
            emit_jsr_import(helper);
            return destination;
        };
        emit_real_expr = [&](std::string_view text) {
            const ParsedRealExpr expr = RealExprParser(text).parse();
            return emit_real_expr_node(expr, expr.root);
        };
        auto emit_load_index_absolute = [&](std::uint8_t opcode, const std::string& symbol) {
            code.push_back(opcode);
            const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, symbol);
        };
        emit_builtin = [&](const ParsedCall& call) -> std::optional<int> {
            auto spec = builtin_call(call.name);
            if (!spec) {
                return std::nullopt;
            }
            if (call.arguments.size() != spec->arguments.size()) {
                throw ToolError("BAD CALL " + call.name);
            }

            std::vector<ExprTempSlot> argument_slots;
            argument_slots.reserve(call.arguments.size());
            for (const std::string& argument : call.arguments) {
                ExprTempSlot slot = allocate_expr_temp();
                emit_load_word(argument);
                emit_store_word(slot);
                argument_slots.push_back(std::move(slot));
            }

            for (std::size_t i = 0; i < argument_slots.size(); ++i) {
                std::optional<std::uint8_t> zero_page;
                if (spec->arguments[i] == CallRegister::ZeroPage0E) {
                    zero_page = 0x0E;
                } else if (spec->arguments[i] == CallRegister::ZeroPageE0) {
                    zero_page = 0xE0;
                }
                if (!zero_page) {
                    continue;
                }
                emit_load_absolute(argument_slots[i].value_lo_symbol);
                code.push_back(0x85);  // STA zero page
                code.push_back(*zero_page);
                emit_load_absolute(argument_slots[i].value_hi_symbol);
                code.push_back(0x85);  // STA zero page
                code.push_back(static_cast<std::uint8_t>(*zero_page + 1));
            }

            // Load index registers first so the final A load cannot be clobbered.
            for (std::size_t i = 0; i < argument_slots.size(); ++i) {
                const ExprTempSlot& slot = argument_slots[i];
                if (spec->arguments[i] == CallRegister::X ||
                    spec->arguments[i] == CallRegister::XY) {
                    emit_load_index_absolute(0xAE, slot.value_lo_symbol);  // LDX absolute
                }
                if (spec->arguments[i] == CallRegister::Y) {
                    emit_load_index_absolute(0xAC, slot.value_lo_symbol);  // LDY absolute
                } else if (spec->arguments[i] == CallRegister::XY) {
                    emit_load_index_absolute(0xAC, slot.value_hi_symbol);  // LDY absolute
                }
            }
            if (spec->carry_low_bit_argument >= 0) {
                const std::size_t carry_index =
                    static_cast<std::size_t>(spec->carry_low_bit_argument);
                if (carry_index >= argument_slots.size()) {
                    throw ToolError("BAD CALL ABI " + call.name);
                }
                emit_load_absolute(argument_slots[carry_index].value_hi_symbol);
                code.push_back(0x4A);  // LSR A: bit 0 becomes carry
            }
            for (std::size_t i = 0; i < argument_slots.size(); ++i) {
                if (spec->arguments[i] == CallRegister::A) {
                    emit_load_absolute(argument_slots[i].value_lo_symbol);
                }
            }
            const bool guard_interrupt_scratch =
                spec->helper.rfind("RT_DBF_", 0) == 0;
            if (guard_interrupt_scratch) {
                code.push_back(0x08);  // PHP: protect DBF zero-page scratch.
                code.push_back(0x78);  // SEI
            }
            emit_jsr_import(spec->helper);
            if (guard_interrupt_scratch) {
                code.push_back(0x28);  // PLP
            }
            if (spec->return_width == 1) {
                code.push_back(0xA2);  // LDX #0 for a BYTE result
                code.push_back(0x00);
            }
            return spec->return_width;
        };
        emit_external_routine_call = [&](const ParsedCall& call) -> std::optional<int> {
            auto routine = external_routines.find(upper_ascii(call.name));
            if (routine == external_routines.end()) {
                return std::nullopt;
            }
            if (call.arguments.size() > routine->second.parameters.size()) {
                throw ToolError("BAD CALL " + upper_ascii(call.name));
            }
            std::vector<ExprTempSlot> argument_slots;
            argument_slots.reserve(call.arguments.size());
            for (const std::string& argument : call.arguments) {
                ExprTempSlot slot = allocate_expr_temp();
                emit_load_word(argument);
                emit_store_word(slot);
                argument_slots.push_back(std::move(slot));
            }
            struct ParameterByte {
                std::string symbol;
            };
            std::vector<ParameterByte> bytes;
            for (std::size_t i = 0; i < argument_slots.size(); ++i) {
                const SourceParameter& parameter = routine->second.parameters[i];
                const std::string type = upper_ascii(parameter.type);
                if (type == "REAL") {
                    throw ToolError("UNSUPPORTED EXTERNAL REAL ABI " + upper_ascii(call.name));
                }
                bytes.push_back(ParameterByte{argument_slots[i].value_lo_symbol});
                if (parameter.is_array || parameter.is_pointer ||
                    type == "CARD" || type == "INT") {
                    bytes.push_back(ParameterByte{argument_slots[i].value_hi_symbol});
                }
            }
            if (bytes.size() > 16) {
                throw ToolError("EXTERNAL PARAMETER ABI " + upper_ascii(call.name));
            }
            for (std::size_t i = 3; i < bytes.size(); ++i) {
                emit_load_absolute(bytes[i].symbol);
                const std::uint16_t address =
                    static_cast<std::uint16_t>(0x00A3 + (i - 3));
                code.push_back(0x8D);  // STA absolute parameter cell
                code.push_back(static_cast<std::uint8_t>(address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(address >> 8));
            }
            if (bytes.size() >= 3) {
                emit_load_index_absolute(0xAC, bytes[2].symbol);  // LDY absolute
            }
            if (bytes.size() >= 2) {
                emit_load_index_absolute(0xAE, bytes[1].symbol);  // LDX absolute
            }
            if (!bytes.empty()) {
                emit_load_absolute(bytes[0].symbol);
            }
            code.push_back(0x20);  // JSR fixed machine-language routine
            if (routine->second.absolute_address) {
                code.push_back(static_cast<std::uint8_t>(
                    *routine->second.absolute_address & 0xFF));
                code.push_back(static_cast<std::uint8_t>(
                    *routine->second.absolute_address >> 8));
            } else {
                const std::uint16_t operand_offset =
                    static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(
                    operand_offset,
                    routine->second.linked_address_symbol,
                    routine->second.linked_address_addend);
            }

            int return_width = 0;
            if (!routine->second.return_type.empty()) {
                if (routine->second.return_type == "REAL") {
                    throw ToolError("UNSUPPORTED EXTERNAL REAL ABI " + upper_ascii(call.name));
                }
                return_width = routine->second.return_type == "BYTE" ? 1 : 2;
            }
            if (return_width == 1) {
                code.push_back(0xA2);  // LDX #0 for a BYTE result
                code.push_back(0x00);
            }
            return return_width;
        };
        emit_local_routine_call = [&](const ParsedCall& call)
            -> std::optional<LocalCallResult> {
            const std::string target = upper_ascii(call.name);
            auto abi = procedure_parameters.find(target);
            if (abi == procedure_parameters.end()) {
                return std::nullopt;
            }
            if (call.arguments.size() > abi->second.size()) {
                throw ToolError("BAD CALL " + target);
            }

            LocalCallResult result;
            auto function = function_returns.find(target);
            if (function != function_returns.end()) {
                result.return_type = function->second.type;
                result.real = function->second.real;
            }

            if (machine_code_names.count(target) != 0) {
                if (result.return_type == "REAL") {
                    throw ToolError("UNSUPPORTED MACHINE REAL ABI " + target);
                }
                std::vector<std::string> parameter_bytes;
                for (std::size_t i = 0; i < call.arguments.size(); ++i) {
                    const ProcedureParameterSlot& parameter = abi->second[i];
                    if (parameter.real || upper_ascii(parameter.source.type) == "REAL") {
                        throw ToolError("UNSUPPORTED MACHINE REAL ABI " + target);
                    }
                    ExprTempSlot staged = allocate_expr_temp();
                    emit_load_word(call.arguments[i]);
                    emit_store_word(staged);
                    parameter_bytes.push_back(staged.value_lo_symbol);
                    const std::string type = upper_ascii(parameter.source.type);
                    if (parameter.source.is_array || parameter.source.is_pointer ||
                        type == "CARD" || type == "INT") {
                        parameter_bytes.push_back(staged.value_hi_symbol);
                    }
                }
                if (parameter_bytes.size() > 16) {
                    throw ToolError("MACHINE PARAMETER ABI " + target);
                }
                for (std::size_t i = 3; i < parameter_bytes.size(); ++i) {
                    emit_load_absolute(parameter_bytes[i]);
                    const std::uint16_t address =
                        static_cast<std::uint16_t>(0x00A3 + (i - 3));
                    code.push_back(0x8D);  // STA fixed-routine parameter cell
                    code.push_back(static_cast<std::uint8_t>(address & 0xFF));
                    code.push_back(static_cast<std::uint8_t>(address >> 8));
                }
                if (parameter_bytes.size() >= 3) {
                    emit_load_index_absolute(
                        0xAC, parameter_bytes[2]);  // LDY third parameter byte
                }
                if (parameter_bytes.size() >= 2) {
                    emit_load_index_absolute(
                        0xAE, parameter_bytes[1]);  // LDX second parameter byte
                }
                if (!parameter_bytes.empty()) {
                    emit_load_absolute(parameter_bytes[0]);  // LDA first byte
                }
                code.push_back(0x20);  // JSR local machine-code routine
                const std::uint16_t operand_offset =
                    static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(operand_offset, target);
                if (result.return_type == "BYTE") {
                    code.push_back(0xA2);  // BYTE machine function zero-extends X
                    code.push_back(0x00);
                }
                return result;
            }

            std::vector<std::string> caller_frame;
            if (reentrant_call_edges.count({current_proc_name, target}) != 0) {
                caller_frame = persistent_frame_bytes;
                caller_frame.insert(
                    caller_frame.end(),
                    operation_frame_bytes.begin(),
                    operation_frame_bytes.end());
                if (caller_frame.size() > 224) {
                    throw ToolError(
                        "REENTRANT FRAME TOO LARGE " + current_proc_name);
                }
            }
            for (const std::string& symbol : caller_frame) {
                emit_load_absolute(symbol);
                code.push_back(0x48);  // PHA: preserve the caller's static cell.
            }

            struct StagedParameter {
                std::optional<ExprTempSlot> word;
                std::optional<RealSlot> real;
            };
            std::vector<StagedParameter> staged;
            staged.reserve(call.arguments.size());
            for (std::size_t i = 0; i < call.arguments.size(); ++i) {
                StagedParameter value;
                if (abi->second[i].real) {
                    value.real = emit_real_expr(call.arguments[i]);
                } else {
                    ExprTempSlot temp = allocate_expr_temp();
                    emit_load_word(call.arguments[i]);
                    emit_store_word(temp);
                    value.word = std::move(temp);
                }
                staged.push_back(std::move(value));
            }

            for (std::size_t i = 0; i < staged.size(); ++i) {
                const ProcedureParameterSlot& parameter = abi->second[i];
                if (parameter.real) {
                    if (!staged[i].real) {
                        throw ToolError("BAD CALL ABI " + target);
                    }
                    emit_real_copy(*staged[i].real, *parameter.real);
                    continue;
                }
                if (!parameter.word || !staged[i].word) {
                    throw ToolError("BAD CALL ABI " + target);
                }
                emit_load_absolute(staged[i].word->value_lo_symbol);
                if (parameter.word->is_card) {
                    emit_load_index_absolute(
                        0xAE, staged[i].word->value_hi_symbol);  // LDX absolute
                } else {
                    code.push_back(0xA2);  // LDX #0
                    code.push_back(0x00);
                }
                emit_store_variable(*parameter.word);
            }

            code.push_back(0x20);  // JSR local procedure
            const std::uint16_t operand_offset =
                static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, target);

            if (!caller_frame.empty()) {
                if (result.return_type == "REAL") {
                    if (!result.real) {
                        throw ToolError("BAD FUNC ABI " + target);
                    }
                    for (std::size_t i = 0; i < 4; ++i) {
                        emit_real_byte_access(0xAD, *result.real, i);  // LDA absolute
                        code.push_back(0x85);  // STA result scratch
                        code.push_back(static_cast<std::uint8_t>(0x0C + i));
                    }
                } else if (!result.return_type.empty()) {
                    code.push_back(0x85);  // STA $0C
                    code.push_back(0x0C);
                    code.push_back(0x86);  // STX $0D
                    code.push_back(0x0D);
                }

                for (auto symbol = caller_frame.rbegin();
                     symbol != caller_frame.rend();
                     ++symbol) {
                    code.push_back(0x68);  // PLA
                    code.push_back(0x8D);  // STA absolute
                    const std::uint16_t restore_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(restore_offset, *symbol);
                }

                if (!result.return_type.empty() && result.return_type != "REAL") {
                    code.push_back(0xA5);  // LDA $0C
                    code.push_back(0x0C);
                    code.push_back(0xA6);  // LDX $0D
                    code.push_back(0x0D);
                }
            }

            if (result.return_type == "REAL") {
                if (!result.real) {
                    throw ToolError("BAD FUNC ABI " + target);
                }
                const RealSlot static_result = *result.real;
                RealSlot call_result = allocate_real_temp();
                if (caller_frame.empty()) {
                    emit_real_copy(static_result, call_result);
                } else {
                    for (std::size_t i = 0; i < 4; ++i) {
                        code.push_back(0xA5);  // LDA result scratch
                        code.push_back(static_cast<std::uint8_t>(0x0C + i));
                        emit_real_byte_access(0x8D, call_result, i);  // STA absolute
                    }
                }
                result.real = std::move(call_result);
            }
            return result;
        };
        auto emit_reu_allocation = [&](
            const VarSlot& handle,
            std::string_view size_expression,
            std::size_t line) {
            auto size = try_eval_const_expr(size_expression, constants);
            if (!size) {
                throw ToolError(
                    "REU SIZE MUST BE CONSTANT LINE " + std::to_string(line));
            }
            if (*size < 1 || *size > 0xFFFF) {
                throw ToolError(
                    "REU SIZE RANGE LINE " + std::to_string(line) + ": " + handle.name);
            }
            emit_load_immediate(*size);
            emit_jsr_import("RT_REU_ALLOC");
            code.push_back(0xA2);  // BYTE handle result
            code.push_back(0x00);
            emit_store_variable(handle);
            constants.erase(handle.name);
        };
        if (upper_ascii(proc.name) == "MAIN") {
            const auto& main_parameters =
                procedure_parameters.at(upper_ascii(proc.name));
            if (!main_parameters.empty()) {
                if (main_parameters.size() != 2 ||
                    !main_parameters[0].word || !main_parameters[1].word) {
                    throw ToolError("BAD MAIN ABI");
                }
                // Idun/ACE publishes a 16-bit argc and a RAM0 pointer to its
                // null-terminated argv pointer table in the process status
                // block. Bind those values to ordinary Action parameter cells
                // before any user statement or global REU allocation runs.
                code.push_back(0xAD);  // LDA $0F04: aceArgc low
                code.push_back(0x04);
                code.push_back(0x0F);
                code.push_back(0xAE);  // LDX $0F05: aceArgc high
                code.push_back(0x05);
                code.push_back(0x0F);
                emit_store_variable(*main_parameters[0].word);

                code.push_back(0xAD);  // LDA $0F06: aceArgv low
                code.push_back(0x06);
                code.push_back(0x0F);
                code.push_back(0xAE);  // LDX $0F07: aceArgv high
                code.push_back(0x07);
                code.push_back(0x0F);
                emit_store_variable(*main_parameters[1].word);
            }
            for (const ReuArrayDeclaration& declaration : global_reu_arrays) {
                emit_reu_allocation(
                    variables.at(declaration.name),
                    declaration.size_expression,
                    declaration.line);
            }
        }
        auto emit_branch = [&](std::uint8_t opcode) {
            code.push_back(opcode);
            const std::size_t operand = code.size();
            code.push_back(0x00);
            return operand;
        };
        auto patch_branch_to_current = [&](std::size_t operand) {
            const std::ptrdiff_t delta = static_cast<std::ptrdiff_t>(code.size()) -
                                         static_cast<std::ptrdiff_t>(operand + 1);
            if (delta < -128 || delta > 127) {
                throw ToolError("INTERNAL BRANCH RANGE");
            }
            code[operand] = static_cast<std::uint8_t>(static_cast<int>(delta) & 0xFF);
        };
        auto patch_branch_to_offset = [&](std::size_t operand, std::size_t target) {
            const std::ptrdiff_t delta = static_cast<std::ptrdiff_t>(target) -
                                         static_cast<std::ptrdiff_t>(operand + 1);
            if (delta < -128 || delta > 127) {
                throw ToolError("INTERNAL BRANCH RANGE");
            }
            code[operand] = static_cast<std::uint8_t>(static_cast<int>(delta) & 0xFF);
        };
        auto emit_action_string = [&](std::string_view expression) {
            emit_load_word(expression);
            code.push_back(0x85);  // STA $0A
            code.push_back(0x0A);
            code.push_back(0x86);  // STX $0B
            code.push_back(0x0B);
            code.push_back(0xA0);  // LDY #0
            code.push_back(0x00);
            code.push_back(0xB1);  // LDA ($0A),Y: Action string length
            code.push_back(0x0A);
            code.push_back(0xAA);  // TAX
            const std::size_t empty = emit_branch(0xF0);  // BEQ done
            const std::size_t loop = code.size();
            code.push_back(0xC8);  // INY
            code.push_back(0xB1);  // LDA ($0A),Y
            code.push_back(0x0A);
            code.push_back(0x20);  // JSR CHROUT
            code.push_back(0xD2);
            code.push_back(0xFF);
            code.push_back(0xCA);  // DEX
            const std::size_t again = emit_branch(0xD0);  // BNE loop
            patch_branch_to_offset(again, loop);
            patch_branch_to_current(empty);
            emit_cr();
        };
        auto emit_compare_absolute = [&](const std::string& symbol) {
            code.push_back(0xCD);  // CMP absolute
            const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(operand_offset, symbol);
        };
        auto compare_known_out_of_range = [](
            std::string_view op,
            bool is_card,
            bool is_signed,
            ExprValue rhs_value) -> std::optional<bool> {
            const ExprValue min_value = is_signed ? -32768 : 0;
            const ExprValue max_value = is_signed ? 32767 : (is_card ? 0xFFFF : 0xFF);
            if (rhs_value >= min_value && rhs_value <= max_value) {
                return std::nullopt;
            }
            const bool below = rhs_value < min_value;
            if (op == "=") return false;
            if (op == "<>") return true;
            if (op == "<") return !below;
            if (op == "<=") return !below;
            if (op == ">") return below;
            if (op == ">=") return below;
            return std::nullopt;
        };
        std::function<std::optional<bool>(std::string_view)>
            try_eval_action_condition;
        try_eval_action_condition = [&](std::string_view condition)
            -> std::optional<bool> {
            try {
                const std::string text =
                    strip_outer_condition_parentheses(std::string(condition));
                if (auto logical_or = split_top_level_condition(text, "OR")) {
                    auto lhs = try_eval_action_condition(logical_or->first);
                    if (!lhs) return std::nullopt;
                    if (*lhs) return true;
                    return try_eval_action_condition(logical_or->second);
                }
                if (auto logical_and = split_top_level_condition(text, "AND")) {
                    auto lhs = try_eval_action_condition(logical_and->first);
                    if (!lhs) return std::nullopt;
                    if (!*lhs) return false;
                    return try_eval_action_condition(logical_and->second);
                }
                if (auto comparison = parse_comparison(text)) {
                    const ParsedExpr lhs_expr =
                        WordExprParser(comparison->lhs).parse();
                    const ParsedExpr rhs_expr =
                        WordExprParser(comparison->rhs).parse();
                    auto lhs = evaluate_action_word(
                        lhs_expr, lhs_expr.root, constants);
                    auto rhs = evaluate_action_word(
                        rhs_expr, rhs_expr.root, constants);
                    if (!lhs || !rhs) return std::nullopt;
                    const ActionWordType comparison_type = action_mixed_type(
                        infer_word_type(lhs_expr, lhs_expr.root),
                        infer_word_type(rhs_expr, rhs_expr.root));
                    *lhs = normalize_action_word(*lhs, comparison_type);
                    *rhs = normalize_action_word(*rhs, comparison_type);
                    if (comparison->op == "=") return *lhs == *rhs;
                    if (comparison->op == "<>") return *lhs != *rhs;
                    if (comparison->op == "<") return *lhs < *rhs;
                    if (comparison->op == "<=") return *lhs <= *rhs;
                    if (comparison->op == ">") return *lhs > *rhs;
                    if (comparison->op == ">=") return *lhs >= *rhs;
                    throw ToolError("BAD CONDITION");
                }
                const ParsedExpr expr = WordExprParser(text).parse();
                auto value = evaluate_action_word(expr, expr.root, constants);
                return value ? std::optional<bool>(*value != 0) : std::nullopt;
            } catch (const ToolError&) {
                return std::nullopt;
            }
        };
        std::function<std::optional<bool>(std::string_view)> try_eval_real_condition;
        try_eval_real_condition = [&](std::string_view condition) -> std::optional<bool> {
            try {
                const std::string text =
                    strip_outer_condition_parentheses(std::string(condition));
                if (auto logical_or = split_top_level_condition(text, "OR")) {
                    auto lhs = try_eval_real_condition(logical_or->first);
                    if (!lhs) {
                        return std::nullopt;
                    }
                    if (*lhs) {
                        return true;
                    }
                    return try_eval_real_condition(logical_or->second);
                }
                if (auto logical_and = split_top_level_condition(text, "AND")) {
                    auto lhs = try_eval_real_condition(logical_and->first);
                    if (!lhs) {
                        return std::nullopt;
                    }
                    if (!*lhs) {
                        return false;
                    }
                    return try_eval_real_condition(logical_and->second);
                }
                if (auto comparison = parse_comparison(text)) {
                    auto lhs = try_eval_const_real_expr(comparison->lhs, real_constants);
                    auto rhs = try_eval_const_real_expr(comparison->rhs, real_constants);
                    if (!lhs || !rhs) {
                        return std::nullopt;
                    }
                    if (comparison->op == "=") return *lhs == *rhs;
                    if (comparison->op == "<>") return *lhs != *rhs;
                    if (comparison->op == "<") return *lhs < *rhs;
                    if (comparison->op == "<=") return *lhs <= *rhs;
                    if (comparison->op == ">") return *lhs > *rhs;
                    if (comparison->op == ">=") return *lhs >= *rhs;
                    return std::nullopt;
                }
                auto value = try_eval_const_real_expr(text, real_constants);
                return value ? std::optional<bool>(*value != 0.0) : std::nullopt;
            } catch (const ToolError&) {
                return std::nullopt;
            }
        };
        auto emit_real_condition_false_jump = [&](
            std::string_view condition,
            const std::string& false_label) {
            ParsedComparison comparison;
            if (auto parsed = parse_comparison(condition)) {
                comparison = std::move(*parsed);
            } else {
                comparison = ParsedComparison{
                    strip_outer_condition_parentheses(std::string(condition)),
                    "<>",
                    "0.0",
                };
            }
            const RealSlot lhs = emit_real_expr(comparison.lhs);
            const RealSlot rhs = emit_real_expr(comparison.rhs);
            emit_set_real_pointer(lhs, 0x02);
            emit_set_real_pointer(rhs, 0x04);
            emit_jsr_import("RT_F_CMP");

            // RT_F_CMP returns A=2 for an unordered comparison (either
            // operand is NaN).  All ordered predicates, including equality,
            // must be false in that case; inequality remains true.
            if (comparison.op != "<>") {
                code.push_back(0xC9);  // CMP #unordered
                code.push_back(0x02);
                const std::size_t ordered_operand = emit_branch(0xD0);  // BNE
                emit_jump(false_label);
                patch_branch_to_current(ordered_operand);
            }

            std::uint8_t compare_value = 0;
            std::uint8_t true_branch = 0;
            if (comparison.op == "=") {
                compare_value = 0x00;
                true_branch = 0xF0;  // BEQ
            } else if (comparison.op == "<>") {
                compare_value = 0x00;
                true_branch = 0xD0;  // BNE
            } else if (comparison.op == "<") {
                compare_value = 0xFF;
                true_branch = 0xF0;  // BEQ
            } else if (comparison.op == "<=") {
                compare_value = 0x01;
                true_branch = 0xD0;  // BNE
            } else if (comparison.op == ">") {
                compare_value = 0x01;
                true_branch = 0xF0;  // BEQ
            } else if (comparison.op == ">=") {
                compare_value = 0xFF;
                true_branch = 0xD0;  // BNE
            } else {
                throw ToolError("BAD REAL CONDITION");
            }
            code.push_back(0xC9);  // CMP immediate
            code.push_back(compare_value);
            const std::size_t true_operand = emit_branch(true_branch);
            emit_jump(false_label);
            patch_branch_to_current(true_operand);
        };
        auto emit_simple_condition_false_jump = [&](
            std::string_view condition,
            const std::string& false_label) {
            if (expression_looks_real(condition)) {
                if (!expression_uses_any_variable(condition)) {
                    auto value = try_eval_real_condition(condition);
                    if (value) {
                        if (!*value) {
                            emit_jump(false_label);
                        }
                        return;
                    }
                }
                emit_real_condition_false_jump(condition, false_label);
                return;
            }
            if (!expression_uses_variable(condition)) {
                auto value = try_eval_action_condition(condition);
                if (value) {
                    if (!*value) {
                        emit_jump(false_label);
                    }
                    return;
                }
            }

            ParsedComparison comparison;
            if (auto parsed = parse_comparison(condition)) {
                comparison = std::move(*parsed);
            } else {
                comparison = ParsedComparison{
                    strip_outer_condition_parentheses(std::string(condition)),
                    "<>",
                    "0",
                };
            }
            const ActionWordType comparison_word_type = action_mixed_type(
                infer_word_text_type(comparison.lhs),
                infer_word_text_type(comparison.rhs));

            auto simple_lhs = variables.find(upper_ascii(comparison.lhs));
            if (simple_lhs != variables.end() && !expression_uses_variable(comparison.rhs)) {
                if (auto rhs_value = try_eval_const_expr(comparison.rhs, constants)) {
                    if (auto known = compare_known_out_of_range(
                            comparison.op,
                            simple_lhs->second.is_card &&
                                !(simple_lhs->second.is_signed &&
                                  comparison_word_type == ActionWordType::Int),
                            simple_lhs->second.is_signed &&
                                comparison_word_type == ActionWordType::Int,
                            *rhs_value)) {
                        if (!*known) {
                            emit_jump(false_label);
                        }
                        return;
                    }
                }
            }

            const ExprTempSlot lhs_slot = allocate_expr_temp();
            const ExprTempSlot rhs_slot = allocate_expr_temp();
            emit_load_word(comparison.lhs);
            emit_store_word(lhs_slot);
            emit_load_word(comparison.rhs);
            emit_store_word(rhs_slot);

            std::vector<std::size_t> true_branches;
            std::vector<std::size_t> false_branches;
            const bool signed_comparison =
                comparison_word_type == ActionWordType::Int;
            if (signed_comparison) {
                emit_load_absolute(rhs_slot.value_hi_symbol);
                code.push_back(0x49);  // EOR #$80 normalizes signed order
                code.push_back(0x80);
                code.push_back(0x85);  // STA $02
                code.push_back(0x02);
                emit_load_absolute(lhs_slot.value_hi_symbol);
                code.push_back(0x49);  // EOR #$80
                code.push_back(0x80);
                code.push_back(0xC5);  // CMP $02
                code.push_back(0x02);
            } else {
                emit_load_absolute(lhs_slot.value_hi_symbol);
                emit_compare_absolute(rhs_slot.value_hi_symbol);
            }

            if (comparison.op == "=") {
                false_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                true_branches.push_back(emit_branch(0xF0));  // BEQ
            } else if (comparison.op == "<>") {
                true_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                true_branches.push_back(emit_branch(0xD0));  // BNE
            } else if (comparison.op == "<") {
                true_branches.push_back(emit_branch(0x90));  // BCC
                false_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                true_branches.push_back(emit_branch(0x90));  // BCC
            } else if (comparison.op == "<=") {
                true_branches.push_back(emit_branch(0x90));  // BCC
                false_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                true_branches.push_back(emit_branch(0x90));  // BCC
                true_branches.push_back(emit_branch(0xF0));  // BEQ
            } else if (comparison.op == ">") {
                false_branches.push_back(emit_branch(0x90));  // BCC
                true_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                false_branches.push_back(emit_branch(0x90));  // BCC
                true_branches.push_back(emit_branch(0xD0));  // BNE
            } else if (comparison.op == ">=") {
                false_branches.push_back(emit_branch(0x90));  // BCC
                true_branches.push_back(emit_branch(0xD0));  // BNE
                emit_load_absolute(lhs_slot.value_lo_symbol);
                emit_compare_absolute(rhs_slot.value_lo_symbol);
                false_branches.push_back(emit_branch(0x90));  // BCC
                true_branches.push_back(emit_branch(0xB0));  // BCS
            } else {
                throw ToolError("BAD CONDITION");
            }

            for (std::size_t operand : false_branches) {
                patch_branch_to_current(operand);
            }
            emit_jump(false_label);
            for (std::size_t operand : true_branches) {
                patch_branch_to_current(operand);
            }
        };
        std::function<void(std::string_view, const std::string&)> emit_condition_false_jump;
        emit_condition_false_jump = [&emit_condition_false_jump,
                                     &emit_simple_condition_false_jump,
                                     &new_control_label,
                                     &define_control_label,
                                     &emit_jump](
                                        std::string_view condition,
                                        const std::string& false_label) {
            const std::string text =
                strip_outer_condition_parentheses(std::string(condition));
            if (auto logical_or = split_top_level_condition(text, "OR")) {
                const std::string left_false = new_control_label("OR_RIGHT");
                const std::string success = new_control_label("OR_DONE");
                emit_condition_false_jump(logical_or->first, left_false);
                emit_jump(success);
                define_control_label(left_false);
                emit_condition_false_jump(logical_or->second, false_label);
                define_control_label(success);
                return;
            }
            if (auto logical_and = split_top_level_condition(text, "AND")) {
                emit_condition_false_jump(logical_and->first, false_label);
                emit_condition_false_jump(logical_and->second, false_label);
                return;
            }
            emit_simple_condition_false_jump(text, false_label);
        };
        struct CodeBlockSymbol {
            std::string symbol;
            std::optional<std::uint16_t> absolute_address;
            std::int32_t addend = 0;
        };
        auto resolve_code_block_symbol = [&](std::string_view source_name)
            -> std::optional<CodeBlockSymbol> {
            const std::string name = upper_ascii(trim(source_name));
            if (name == "*") {
                const std::string label = new_control_label("CURRENT_ADDRESS");
                define_control_label(label);
                return CodeBlockSymbol{label, std::nullopt, 0};
            }
            auto declared_address = compiler_addresses.find(name);
            if (declared_address != compiler_addresses.end()) {
                if (declared_address->second.absolute) {
                    return CodeBlockSymbol{
                        {},
                        static_cast<std::uint16_t>(
                            *declared_address->second.absolute),
                        declared_address->second.addend,
                    };
                }
                return CodeBlockSymbol{
                    declared_address->second.symbol,
                    std::nullopt,
                    declared_address->second.addend,
                };
            }
            auto variable = variables.find(name);
            if (variable != variables.end()) {
                if (!variable->second.bound_address_symbol.empty()) {
                    return CodeBlockSymbol{
                        variable->second.bound_address_symbol,
                        std::nullopt,
                        variable->second.bound_address_addend,
                    };
                }
                return CodeBlockSymbol{
                    variable->second.lo_symbol,
                    variable->second.absolute_address,
                    0,
                };
            }
            auto real_variable = real_variables.find(name);
            if (real_variable != real_variables.end()) {
                return CodeBlockSymbol{
                    real_variable->second.byte_symbols.front(),
                    real_variable->second.absolute_address,
                    0,
                };
            }
            auto record = record_addresses.find(name);
            if (record != record_addresses.end()) {
                return CodeBlockSymbol{
                    record->second.target_symbol,
                    record->second.absolute_address,
                    record->second.target_addend,
                };
            }
            auto external = external_routines.find(name);
            if (external != external_routines.end()) {
                return CodeBlockSymbol{
                    external->second.linked_address_symbol,
                    external->second.absolute_address,
                    external->second.linked_address_addend,
                };
            }
            if (local_names.count(name) != 0) {
                return CodeBlockSymbol{name, std::nullopt, 0};
            }
            return std::nullopt;
        };
        auto emit_code_block = [&](std::string body) {
            for (const std::string& token : split_code_block_constants(body)) {
                if (auto value = try_eval_const_expr(token, global_constants)) {
                    if (*value < -32768 || *value > 0xFFFF) {
                        throw ToolError("CODE VALUE RANGE");
                    }
                    const std::uint16_t word = static_cast<std::uint16_t>(*value);
                    code.push_back(static_cast<std::uint8_t>(word & 0xFF));
                    if (*value < 0 || *value > 0xFF) {
                        code.push_back(static_cast<std::uint8_t>(word >> 8));
                    }
                    continue;
                }

                std::optional<CodeBlockSymbol> symbol =
                    resolve_code_block_symbol(token);
                ExprValue addend = 0;
                if (!symbol) {
                    const std::size_t plus = token.find('+');
                    if (plus != std::string::npos &&
                        token.find('+', plus + 1) == std::string::npos) {
                        const std::string lhs = trim(
                            std::string_view(token).substr(0, plus));
                        const std::string rhs = trim(
                            std::string_view(token).substr(plus + 1));
                        symbol = resolve_code_block_symbol(lhs);
                        auto constant = try_eval_const_expr(rhs, global_constants);
                        if (!symbol || !constant) {
                            symbol = resolve_code_block_symbol(rhs);
                            constant = try_eval_const_expr(lhs, global_constants);
                        }
                        if (symbol && constant) {
                            addend = *constant;
                        } else {
                            symbol.reset();
                        }
                    }
                }
                if (!symbol) {
                    throw ToolError("BAD CODE VALUE " + token);
                }
                if (symbol->absolute_address) {
                    const ExprValue value =
                        static_cast<ExprValue>(*symbol->absolute_address) +
                        symbol->addend + addend;
                    if (value < 0 || value > 0xFFFF) {
                        throw ToolError("CODE VALUE RANGE");
                    }
                    code.push_back(static_cast<std::uint8_t>(value & 0xFF));
                    code.push_back(static_cast<std::uint8_t>((value >> 8) & 0xFF));
                    continue;
                }
                const std::int64_t relocation_addend =
                    static_cast<std::int64_t>(symbol->addend) + addend;
                if (relocation_addend < std::numeric_limits<std::int32_t>::min() ||
                    relocation_addend > std::numeric_limits<std::int32_t>::max()) {
                    throw ToolError("CODE VALUE RANGE");
                }
                const std::uint16_t offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                add_reloc(
                    offset,
                    symbol->symbol,
                    static_cast<std::int32_t>(relocation_addend));
            }
        };
        auto emit_asm_block = [&](const SourceOp& source_op) {
            struct AsmLocalLabel {
                std::size_t offset = 0;
                std::string link_symbol;
            };
            struct AsmStatement {
                std::vector<std::string> labels;
                std::string mnemonic;
                std::string expression;
                AsmAddressMode mode = AsmAddressMode::Implied;
                ObjRelocPart immediate_part = ObjRelocPart::Word;
                std::size_t offset = 0;
                std::size_t line = 0;
            };
            struct AsmValue {
                std::optional<ExprValue> absolute;
                std::string symbol;
                std::int32_t addend = 0;
            };

            auto fail = [](std::size_t line, const std::string& message) -> void {
                throw ToolError(
                    "ASM LINE " + std::to_string(line) + ": " + message);
            };
            auto valid_label = [](std::string_view value) {
                if (value.empty() ||
                    (!std::isalpha(static_cast<unsigned char>(value.front())) &&
                     value.front() != '_')) {
                    return false;
                }
                return std::all_of(
                    value.begin(), value.end(), [](unsigned char ch) {
                        return std::isalnum(ch) != 0 || ch == '_';
                    });
            };
            auto compact_operand = [](std::string_view operand) {
                std::string compact;
                compact.reserve(operand.size());
                for (unsigned char ch : operand) {
                    if (!std::isspace(ch)) {
                        compact.push_back(static_cast<char>(ch));
                    }
                }
                return compact;
            };
            auto ends_with = [](std::string_view value, std::string_view suffix) {
                return value.size() >= suffix.size() &&
                    upper_ascii(value.substr(value.size() - suffix.size())) == suffix;
            };

            std::map<std::string, AsmLocalLabel> local_labels;
            std::vector<AsmStatement> statements;
            std::size_t assembled_size = 0;
            const std::vector<std::string> lines = split_lines(source_op.value);
            for (std::size_t line_index = 0; line_index < lines.size(); ++line_index) {
                const std::size_t source_line = source_op.line + line_index;
                std::string line = trim(strip_source_comment(lines[line_index]));
                AsmStatement statement;
                statement.offset = assembled_size;
                statement.line = source_line;

                while (!line.empty()) {
                    const std::size_t colon = line.find(':');
                    const std::size_t whitespace = line.find_first_of(" \t");
                    if (colon == std::string::npos ||
                        (whitespace != std::string::npos && whitespace < colon)) {
                        break;
                    }
                    const std::string label = upper_ascii(trim(
                        std::string_view(line).substr(0, colon)));
                    if (!valid_label(label)) {
                        fail(source_line, "BAD LABEL");
                    }
                    AsmLocalLabel local{
                        assembled_size,
                        new_control_label("ASM_" + label),
                    };
                    if (!local_labels.emplace(label, local).second) {
                        fail(source_line, "DUPLICATE LABEL " + label);
                    }
                    statement.labels.push_back(label);
                    line = trim(std::string_view(line).substr(colon + 1));
                }

                if (line.empty()) {
                    if (!statement.labels.empty()) {
                        statements.push_back(std::move(statement));
                    }
                    continue;
                }

                const std::size_t mnemonic_end = line.find_first_of(" \t");
                statement.mnemonic = upper_ascii(line.substr(0, mnemonic_end));
                const std::string operand = mnemonic_end == std::string::npos
                    ? std::string{}
                    : trim(std::string_view(line).substr(mnemonic_end));
                const std::string compact = compact_operand(operand);
                const std::string compact_upper = upper_ascii(compact);

                if (asm_opcode(statement.mnemonic, AsmAddressMode::Relative)) {
                    if (compact.empty()) {
                        fail(source_line, "MISSING BRANCH LABEL");
                    }
                    statement.mode = AsmAddressMode::Relative;
                    statement.expression = compact;
                } else if (compact.empty()) {
                    if (asm_opcode(statement.mnemonic, AsmAddressMode::Implied)) {
                        statement.mode = AsmAddressMode::Implied;
                    } else if (asm_opcode(
                                   statement.mnemonic,
                                   AsmAddressMode::Accumulator)) {
                        statement.mode = AsmAddressMode::Accumulator;
                    } else {
                        fail(source_line, "MISSING OPERAND FOR " + statement.mnemonic);
                    }
                } else if (compact_upper == "A" &&
                           asm_opcode(
                               statement.mnemonic,
                               AsmAddressMode::Accumulator)) {
                    statement.mode = AsmAddressMode::Accumulator;
                } else if (compact.front() == '#') {
                    statement.mode = AsmAddressMode::Immediate;
                    statement.expression = compact.substr(1);
                    if (!statement.expression.empty() &&
                        (statement.expression.front() == '<' ||
                         statement.expression.front() == '>')) {
                        statement.immediate_part =
                            statement.expression.front() == '<'
                            ? ObjRelocPart::LowByte
                            : ObjRelocPart::HighByte;
                        statement.expression.erase(statement.expression.begin());
                    }
                    if (statement.expression.empty()) {
                        fail(source_line, "BAD IMMEDIATE OPERAND");
                    }
                } else if (compact.size() >= 5 && compact.front() == '(' &&
                           ends_with(compact, ",X)")) {
                    statement.mode = AsmAddressMode::IndexedIndirect;
                    statement.expression = compact.substr(1, compact.size() - 4);
                } else if (compact.size() >= 5 && compact.front() == '(' &&
                           ends_with(compact, "),Y")) {
                    statement.mode = AsmAddressMode::IndirectIndexed;
                    statement.expression = compact.substr(1, compact.size() - 4);
                } else if (compact.size() >= 3 && compact.front() == '(' &&
                           compact.back() == ')') {
                    statement.mode = AsmAddressMode::Indirect;
                    statement.expression = compact.substr(1, compact.size() - 2);
                } else {
                    AsmAddressMode zero_page_mode = AsmAddressMode::ZeroPage;
                    AsmAddressMode absolute_mode = AsmAddressMode::Absolute;
                    statement.expression = compact;
                    if (ends_with(compact, ",X")) {
                        zero_page_mode = AsmAddressMode::ZeroPageX;
                        absolute_mode = AsmAddressMode::AbsoluteX;
                        statement.expression.resize(statement.expression.size() - 2);
                    } else if (ends_with(compact, ",Y")) {
                        zero_page_mode = AsmAddressMode::ZeroPageY;
                        absolute_mode = AsmAddressMode::AbsoluteY;
                        statement.expression.resize(statement.expression.size() - 2);
                    }
                    if (statement.expression.empty()) {
                        fail(source_line, "BAD OPERAND");
                    }

                    bool fixed_zero_page = false;
                    if (auto value = try_eval_const_expr(
                            statement.expression, global_constants)) {
                        fixed_zero_page = *value >= 0 && *value <= 0xFF;
                    } else if (statement.expression != "*") {
                        if (auto symbol =
                                resolve_code_block_symbol(statement.expression);
                            symbol && symbol->absolute_address) {
                            const ExprValue value =
                                static_cast<ExprValue>(*symbol->absolute_address) +
                                symbol->addend;
                            fixed_zero_page = value >= 0 && value <= 0xFF;
                        }
                    }
                    if (fixed_zero_page &&
                        asm_opcode(statement.mnemonic, zero_page_mode)) {
                        statement.mode = zero_page_mode;
                    } else {
                        statement.mode = absolute_mode;
                    }
                }

                if (!asm_opcode(statement.mnemonic, statement.mode)) {
                    fail(
                        source_line,
                        "ILLEGAL ADDRESSING MODE FOR " + statement.mnemonic);
                }
                assembled_size += asm_instruction_size(statement.mode);
                if (assembled_size > 0xFFFF ||
                    assembled_size > 0xFFFF - code.size()) {
                    fail(source_line, "BLOCK TOO LARGE");
                }
                statements.push_back(std::move(statement));
            }

            auto resolve_value = [&](std::string expression) -> std::optional<AsmValue> {
                expression = trim(expression);
                if (auto value = try_eval_const_expr(expression, global_constants)) {
                    return AsmValue{*value, {}, 0};
                }

                auto resolve_base = [&](std::string_view base)
                    -> std::optional<AsmValue> {
                    const std::string name = upper_ascii(trim(base));
                    auto local = local_labels.find(name);
                    if (local != local_labels.end()) {
                        return AsmValue{
                            std::nullopt,
                            local->second.link_symbol,
                            0,
                        };
                    }
                    auto symbol = resolve_code_block_symbol(name);
                    if (!symbol) {
                        return std::nullopt;
                    }
                    if (symbol->absolute_address) {
                        return AsmValue{
                            static_cast<ExprValue>(*symbol->absolute_address) +
                                symbol->addend,
                            {},
                            0,
                        };
                    }
                    return AsmValue{
                        std::nullopt,
                        symbol->symbol,
                        symbol->addend,
                    };
                };

                if (auto exact = resolve_base(expression)) {
                    return exact;
                }
                for (std::size_t index = 1; index < expression.size(); ++index) {
                    if (expression[index] != '+' && expression[index] != '-') {
                        continue;
                    }
                    const char operation = expression[index];
                    const std::string lhs = expression.substr(0, index);
                    const std::string rhs = expression.substr(index + 1);
                    if (rhs.empty()) {
                        continue;
                    }
                    auto base = resolve_base(lhs);
                    auto addend = try_eval_const_expr(rhs, global_constants);
                    if (base && addend) {
                        const ExprValue signed_addend =
                            operation == '+' ? *addend : -*addend;
                        if (base->absolute) {
                            base->absolute = *base->absolute + signed_addend;
                        } else {
                            const std::int64_t combined =
                                static_cast<std::int64_t>(base->addend) +
                                signed_addend;
                            if (combined < std::numeric_limits<std::int32_t>::min() ||
                                combined > std::numeric_limits<std::int32_t>::max()) {
                                return std::nullopt;
                            }
                            base->addend = static_cast<std::int32_t>(combined);
                        }
                        return base;
                    }
                    if (operation == '+') {
                        base = resolve_base(rhs);
                        addend = try_eval_const_expr(lhs, global_constants);
                        if (base && addend) {
                            if (base->absolute) {
                                base->absolute = *base->absolute + *addend;
                            } else {
                                const std::int64_t combined =
                                    static_cast<std::int64_t>(base->addend) +
                                    *addend;
                                if (combined <
                                        std::numeric_limits<std::int32_t>::min() ||
                                    combined >
                                        std::numeric_limits<std::int32_t>::max()) {
                                    return std::nullopt;
                                }
                                base->addend =
                                    static_cast<std::int32_t>(combined);
                            }
                            return base;
                        }
                    }
                }
                return std::nullopt;
            };

            const std::size_t block_start = code.size();
            for (const AsmStatement& statement : statements) {
                if (code.size() != block_start + statement.offset) {
                    throw ToolError("INTERNAL ASM OFFSET");
                }
                for (const std::string& label : statement.labels) {
                    define_control_label(local_labels.at(label).link_symbol);
                }
                if (statement.mnemonic.empty()) {
                    continue;
                }
                source_lines.push_back(ObjLineRecord{
                    static_cast<std::uint16_t>(code.size()),
                    statement.line,
                });
                code.push_back(*asm_opcode(statement.mnemonic, statement.mode));

                if (statement.mode == AsmAddressMode::Implied ||
                    statement.mode == AsmAddressMode::Accumulator) {
                    continue;
                }
                if (statement.mode == AsmAddressMode::Relative) {
                    const std::string label = upper_ascii(statement.expression);
                    auto target = local_labels.find(label);
                    if (target == local_labels.end()) {
                        fail(statement.line, "BRANCH REQUIRES LOCAL LABEL " + label);
                    }
                    const std::ptrdiff_t displacement =
                        static_cast<std::ptrdiff_t>(target->second.offset) -
                        static_cast<std::ptrdiff_t>(statement.offset + 2);
                    if (displacement < -128 || displacement > 127) {
                        fail(statement.line, "BRANCH OUT OF RANGE " + label);
                    }
                    code.push_back(static_cast<std::uint8_t>(
                        static_cast<int>(displacement) & 0xFF));
                    continue;
                }

                auto value = resolve_value(statement.expression);
                if (!value) {
                    fail(statement.line, "UNKNOWN OPERAND " + statement.expression);
                }
                const std::size_t width = asm_instruction_size(statement.mode) - 1;
                if (width == 1) {
                    if (value->absolute) {
                        ExprValue encoded = *value->absolute;
                        if (statement.immediate_part == ObjRelocPart::LowByte) {
                            if (encoded < 0 || encoded > 0xFFFF) {
                                fail(statement.line, "OPERAND RANGE");
                            }
                            encoded &= 0xFF;
                        } else if (
                            statement.immediate_part == ObjRelocPart::HighByte) {
                            if (encoded < 0 || encoded > 0xFFFF) {
                                fail(statement.line, "OPERAND RANGE");
                            }
                            encoded = (encoded >> 8) & 0xFF;
                        } else if (encoded < -128 || encoded > 0xFF) {
                            fail(statement.line, "BYTE OPERAND RANGE");
                        }
                        code.push_back(static_cast<std::uint8_t>(encoded & 0xFF));
                    } else {
                        if (statement.mode != AsmAddressMode::Immediate) {
                            fail(
                                statement.line,
                                "ZERO PAGE OPERAND REQUIRES FIXED ADDRESS");
                        }
                        if (statement.immediate_part == ObjRelocPart::Word) {
                            fail(
                                statement.line,
                                "IMMEDIATE SYMBOL REQUIRES < OR >");
                        }
                        const std::uint16_t operand_offset =
                            static_cast<std::uint16_t>(code.size());
                        code.push_back(0x00);
                        add_reloc(
                            operand_offset,
                            value->symbol,
                            value->addend,
                            statement.immediate_part);
                    }
                    continue;
                }

                if (value->absolute) {
                    if (*value->absolute < 0 || *value->absolute > 0xFFFF) {
                        fail(statement.line, "WORD OPERAND RANGE");
                    }
                    const std::uint16_t encoded =
                        static_cast<std::uint16_t>(*value->absolute);
                    code.push_back(static_cast<std::uint8_t>(encoded & 0xFF));
                    code.push_back(static_cast<std::uint8_t>(encoded >> 8));
                } else {
                    const std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(
                        operand_offset,
                        value->symbol,
                        value->addend);
                }
            }
            if (code.size() != block_start + assembled_size) {
                throw ToolError("INTERNAL ASM SIZE");
            }
        };
        for (const SourceOp& op : proc.ops) {
            operation_frame_bytes.clear();
            operation_frame_symbols.clear();
            if (code.size() > 0xFFFF) {
                throw ToolError("TARGET OBJECT TOO LARGE");
            }
            source_lines.push_back(ObjLineRecord{
                static_cast<std::uint16_t>(code.size()),
                op.line,
            });
            auto block_active = [&]() {
                return std::all_of(if_stack.begin(), if_stack.end(), [](const IfFrame& frame) {
                    return frame.runtime || frame.active;
                });
            };
            if ((pending_while || pending_for) && op.kind != SourceOp::Kind::Do) {
                if (pending_while) {
                    throw ToolError(
                        "WHILE REQUIRES DO LINE " + std::to_string(pending_while->second));
                }
                throw ToolError(
                    "FOR REQUIRES DO LINE " + std::to_string(pending_for->line));
            }
            if (op.kind == SourceOp::Kind::If) {
                const bool parent_active = block_active();
                IfFrame frame;
                frame.parent_active = parent_active;
                if (!parent_active) {
                    frame.active = false;
                } else if (expression_uses_any_variable(op.value)) {
                    frame.runtime = true;
                    frame.next_label = new_control_label("IF_NEXT");
                    frame.end_label = new_control_label("IF_END");
                    emit_condition_false_jump(op.value, frame.next_label);
                } else {
                    auto value = expression_looks_real(op.value)
                        ? try_eval_real_condition(op.value)
                        : try_eval_action_condition(op.value);
                    if (value) {
                        frame.active = *value;
                        frame.branch_taken = *value;
                    } else {
                        frame.runtime = true;
                        frame.next_label = new_control_label("IF_NEXT");
                        frame.end_label = new_control_label("IF_END");
                        emit_condition_false_jump(op.value, frame.next_label);
                    }
                }
                if_stack.push_back(std::move(frame));
                continue;
            }
            if (op.kind == SourceOp::Kind::ElseIf) {
                if (if_stack.empty() || if_stack.back().saw_else) {
                    throw ToolError("BAD ELSEIF LINE " + std::to_string(op.line));
                }
                IfFrame& frame = if_stack.back();
                if (frame.runtime) {
                    emit_jump(frame.end_label);
                    define_control_label(frame.next_label);
                    frame.next_label = new_control_label("IF_NEXT");
                    emit_condition_false_jump(op.value, frame.next_label);
                    frame.active = true;
                } else if (!frame.parent_active || frame.branch_taken) {
                    frame.active = false;
                } else if (expression_uses_any_variable(op.value)) {
                    frame.runtime = true;
                    frame.active = true;
                    frame.next_label = new_control_label("IF_NEXT");
                    frame.end_label = new_control_label("IF_END");
                    emit_condition_false_jump(op.value, frame.next_label);
                } else {
                    auto value = expression_looks_real(op.value)
                        ? try_eval_real_condition(op.value)
                        : try_eval_action_condition(op.value);
                    if (value) {
                        frame.active = *value;
                        frame.branch_taken = *value;
                    } else {
                        frame.runtime = true;
                        frame.active = true;
                        frame.next_label = new_control_label("IF_NEXT");
                        frame.end_label = new_control_label("IF_END");
                        emit_condition_false_jump(op.value, frame.next_label);
                    }
                }
                continue;
            }
            if (op.kind == SourceOp::Kind::Else) {
                if (if_stack.empty() || if_stack.back().saw_else) {
                    throw ToolError("BAD ELSE LINE " + std::to_string(op.line));
                }
                IfFrame& frame = if_stack.back();
                frame.saw_else = true;
                if (frame.runtime) {
                    emit_jump(frame.end_label);
                    define_control_label(frame.next_label);
                    frame.next_label.clear();
                    frame.active = true;
                } else {
                    frame.active = frame.parent_active && !frame.branch_taken;
                    frame.branch_taken = frame.parent_active;
                }
                continue;
            }
            if (op.kind == SourceOp::Kind::Fi) {
                if (if_stack.empty()) {
                    throw ToolError("BAD FI LINE " + std::to_string(op.line));
                }
                IfFrame frame = std::move(if_stack.back());
                if_stack.pop_back();
                if (frame.runtime) {
                    if (!frame.next_label.empty()) {
                        define_control_label(frame.next_label);
                    }
                    define_control_label(frame.end_label);
                }
                continue;
            }
            if (op.kind == SourceOp::Kind::For) {
                auto clause = for_clause_from_line(op.value);
                if (!clause) {
                    throw ToolError("BAD FOR LINE " + std::to_string(op.line));
                }
                PendingForState state;
                state.active = block_active();
                state.clause = std::move(*clause);
                state.line = op.line;
                if (state.active) {
                    auto counter = variables.find(upper_ascii(state.clause.counter));
                    if (counter == variables.end()) {
                        throw ToolError(
                            "UNKNOWN FOR COUNTER LINE " + std::to_string(op.line) + ": " +
                            state.clause.counter);
                    }
                    const auto step_value = expression_uses_variable(state.clause.step)
                        ? std::optional<ExprValue>{}
                        : try_eval_const_expr(state.clause.step, constants);
                    if (step_value && *step_value == 0) {
                        throw ToolError("ZERO FOR STEP LINE " + std::to_string(op.line));
                    }
                    state.dynamic_step = !step_value.has_value();
                    state.descending = step_value && *step_value < 0;
                    state.counter = counter->second;
                    const std::string hidden =
                        "__FOR_" + std::to_string(next_control_label++);
                    add_variable(
                        hidden + "_FINAL",
                        true,
                        "STORAGE",
                        "",
                        op.line,
                        state.counter.is_signed);
                    add_variable(hidden + "_STEP", true, "STORAGE", "", op.line, true);
                    state.final_value = variables.at(hidden + "_FINAL");
                    state.step = variables.at(hidden + "_STEP");
                }
                pending_for = std::move(state);
                continue;
            }
            if (op.kind == SourceOp::Kind::While) {
                pending_while = std::make_pair(op.value, op.line);
                continue;
            }
            if (op.kind == SourceOp::Kind::Do) {
                LoopFrame frame;
                frame.active = block_active();
                frame.has_precondition = pending_while.has_value() || pending_for.has_value();
                frame.if_depth = if_stack.size();
                if (frame.active) {
                    if (pending_for) {
                        emit_load_word(pending_for->clause.initial);
                        emit_store_variable(pending_for->counter);
                        emit_load_word(pending_for->clause.final_value);
                        emit_store_variable(pending_for->final_value);
                        emit_load_word(pending_for->clause.step);
                        emit_store_variable(pending_for->step);
                        constants.erase(upper_ascii(pending_for->counter.name));
                    }
                    frame.start_label = new_control_label("LOOP_START");
                    frame.end_label = new_control_label("LOOP_END");
                    define_control_label(frame.start_label);
                    if (pending_while) {
                        emit_condition_false_jump(pending_while->first, frame.end_label);
                    } else if (pending_for) {
                        if (pending_for->dynamic_step) {
                            emit_condition_false_jump(
                                "(" + pending_for->step.name + " > 0 AND " +
                                    pending_for->counter.name + " <= " +
                                    pending_for->final_value.name + ") OR (" +
                                    pending_for->step.name + " < 0 AND " +
                                    pending_for->counter.name + " >= " +
                                    pending_for->final_value.name + ")",
                                frame.end_label);
                        } else {
                            emit_condition_false_jump(
                                pending_for->counter.name +
                                    (pending_for->descending ? " >= " : " <= ") +
                                    pending_for->final_value.name,
                                frame.end_label);
                        }
                        frame.for_loop = ForLoopState{
                            pending_for->counter,
                            pending_for->final_value,
                            pending_for->step,
                            pending_for->descending,
                            pending_for->dynamic_step,
                        };
                    }
                }
                pending_while.reset();
                pending_for.reset();
                loop_stack.push_back(std::move(frame));
                continue;
            }
            if (op.kind == SourceOp::Kind::Until) {
                if (loop_stack.empty() || loop_stack.back().saw_until ||
                    loop_stack.back().has_precondition ||
                    loop_stack.back().if_depth != if_stack.size()) {
                    throw ToolError("BAD UNTIL LINE " + std::to_string(op.line));
                }
                LoopFrame& frame = loop_stack.back();
                frame.saw_until = true;
                if (frame.active) {
                    emit_condition_false_jump(op.value, frame.start_label);
                }
                continue;
            }
            if (op.kind == SourceOp::Kind::Od) {
                if (loop_stack.empty() || loop_stack.back().if_depth != if_stack.size()) {
                    throw ToolError("BAD OD LINE " + std::to_string(op.line));
                }
                LoopFrame frame = std::move(loop_stack.back());
                loop_stack.pop_back();
                if (frame.active) {
                    if (!frame.saw_until) {
                        if (frame.for_loop) {
                            if (frame.for_loop->dynamic_step) {
                                emit_condition_false_jump(
                                    "(" + frame.for_loop->step.name + " > 0 AND " +
                                        frame.for_loop->step.name + " <= " +
                                        frame.for_loop->final_value.name +
                                        " - " + frame.for_loop->counter.name + ") OR (" +
                                        frame.for_loop->step.name + " < 0 AND -" +
                                        frame.for_loop->step.name + " <= " +
                                        frame.for_loop->counter.name + " - " +
                                        frame.for_loop->final_value.name +
                                        ")",
                                    frame.end_label);
                            } else if (frame.for_loop->descending) {
                                emit_condition_false_jump(
                                    "-" + frame.for_loop->step.name + " <= " +
                                        frame.for_loop->counter.name + " - " +
                                        frame.for_loop->final_value.name,
                                    frame.end_label);
                            } else {
                                emit_condition_false_jump(
                                    frame.for_loop->step.name + " <= " +
                                        frame.for_loop->final_value.name + " - " +
                                        frame.for_loop->counter.name,
                                    frame.end_label);
                            }
                            emit_load_word(
                                frame.for_loop->counter.name + " + " +
                                frame.for_loop->step.name);
                            emit_store_variable(frame.for_loop->counter);
                        }
                        emit_jump(frame.start_label);
                    }
                    define_control_label(frame.end_label);
                }
                continue;
            }
            if (op.kind == SourceOp::Kind::Exit) {
                if (loop_stack.empty()) {
                    throw ToolError("EXIT OUTSIDE LOOP LINE " + std::to_string(op.line));
                }
                if (block_active() && loop_stack.back().active) {
                    emit_jump(loop_stack.back().end_label);
                }
                continue;
            }
            if (!block_active()) {
                continue;
            }
            if (op.kind == SourceOp::Kind::Code) {
                emit_code_block(op.value);
            } else if (op.kind == SourceOp::Kind::AsmBlock) {
                emit_asm_block(op);
            } else if (op.kind == SourceOp::Kind::Return) {
                terminal_top_level_return =
                    &op == &proc.ops.back() && if_stack.empty() &&
                    loop_stack.empty() && !pending_while && !pending_for;
                if (!proc.return_type.empty()) {
                    const std::string return_type = upper_ascii(proc.return_type);
                    if (return_type == "REAL") {
                        auto function = function_returns.find(upper_ascii(proc.name));
                        if (function == function_returns.end() ||
                            !function->second.real) {
                            throw ToolError(
                                "BAD FUNC ABI " + upper_ascii(proc.name));
                        }
                        const RealSlot result = emit_real_expr(op.value);
                        emit_real_copy(result, *function->second.real);
                        emit_load_absolute(function->second.real->pointer_lo_symbol);
                        emit_load_index_absolute(
                            0xAE,
                            function->second.real->pointer_hi_symbol);
                    } else {
                        emit_load_word(op.value);
                        if (return_type == "BYTE") {
                            code.push_back(0xA2);  // LDX #0 for a BYTE result
                            code.push_back(0x00);
                        }
                    }
                }
                code.push_back(0x60);  // RTS
            } else if (op.kind == SourceOp::Kind::Print) {
                emit_text(op.value);
            } else if (op.kind == SourceOp::Kind::PrintString) {
                emit_action_string(op.value);
            } else if (op.kind == SourceOp::Kind::Declare) {
                const std::string declaration_type = upper_ascii(op.aux);
                if (declaration_type == "REAL") {
                    add_real_variable(
                        op.value,
                        op.mode,
                        op.expression,
                        op.line);
                } else if (declaration_type.size() > 8 &&
                           declaration_type.substr(declaration_type.size() - 8) ==
                               "_POINTER") {
                    const std::string element_type =
                        declaration_type.substr(0, declaration_type.size() - 8);
                    add_pointer_variable(
                        op.value,
                        element_type,
                        op.mode,
                        op.expression,
                        op.line);
                } else {
                    add_variable(
                        op.value,
                        declaration_type == "CARD" || declaration_type == "INT",
                        op.mode,
                        op.expression,
                        op.line,
                        declaration_type == "INT");
                }
            } else if (op.kind == SourceOp::Kind::RecordDeclare) {
                add_record_variable(
                    op.value,
                    op.aux,
                    upper_ascii(op.size_expression) == "POINTER",
                    op.mode,
                    op.expression,
                    op.line);
            } else if (op.kind == SourceOp::Kind::ArrayDeclare) {
                add_array_variable(
                    op.value,
                    op.aux,
                    op.size_expression,
                    op.mode,
                    op.expression,
                    op.line);
            } else if (op.kind == SourceOp::Kind::ReuDeclare) {
                add_variable(op.value, false, "INITIAL", "255", op.line);
                emit_reu_allocation(variables.at(upper_ascii(op.value)), op.aux, op.line);
            } else if (op.kind == SourceOp::Kind::Assign) {
                const std::string target = upper_ascii(op.value);
                if (op.mode == "INDEX" || op.mode == "DEREFERENCE") {
                    const IndexedSlot* indexed = nullptr;
                    if (op.mode == "INDEX") {
                        auto found = arrays.find(target);
                        if (found == arrays.end()) {
                            throw ToolError(
                                "UNKNOWN ARRAY LINE " + std::to_string(op.line) +
                                ": " + target);
                        }
                        indexed = &found->second;
                    } else {
                        auto found = pointers.find(target);
                        if (found == pointers.end()) {
                            throw ToolError(
                                "UNKNOWN POINTER LINE " + std::to_string(op.line) +
                                ": " + target);
                        }
                        indexed = &found->second;
                    }
                    if (indexed->element_is_real()) {
                        const RealSlot value = emit_real_expr(op.aux);
                        if (op.mode == "INDEX") {
                            emit_prepare_indexed(*indexed, op.expression);
                        } else {
                            emit_prepare_pointer(*indexed);
                        }
                        emit_store_real_indirect(value);
                        continue;
                    }
                    ExprTempSlot value = allocate_expr_temp();
                    emit_load_word(op.aux);
                    emit_store_word(value);
                    if (op.mode == "INDEX") {
                        emit_prepare_indexed(*indexed, op.expression);
                    } else {
                        emit_prepare_pointer(*indexed);
                    }
                    emit_store_indirect(*indexed, value);
                    continue;
                }
                if (local_names.count(target) != 0) {
                    emit_load_word(op.aux);
                    code.push_back(0x8D);  // STA routine JMP operand low
                    std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, target, 1);
                    code.push_back(0x8E);  // STX routine JMP operand high
                    operand_offset = static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, target, 2);
                    continue;
                }
                auto real_variable = real_variables.find(target);
                if (real_variable != real_variables.end()) {
                    const RealSlot value = emit_real_expr(op.aux);
                    emit_real_copy(value, real_variable->second);
                } else {
                    auto variable = variables.find(target);
                    if (variable == variables.end()) {
                        auto indirect_field = pointers.find(target);
                        if (indirect_field != pointers.end() &&
                            target.find('.') != std::string::npos) {
                            ExprTempSlot value = allocate_expr_temp();
                            emit_load_word(op.aux);
                            emit_store_word(value);
                            emit_prepare_pointer(indirect_field->second);
                            emit_store_indirect(indirect_field->second, value);
                            constants.erase(target);
                            continue;
                        }
                        throw ToolError(
                            "UNKNOWN VAR LINE " + std::to_string(op.line) + ": " + op.value);
                    }
                    if (auto call = parse_call_expression(op.aux)) {
                        if (call->name == "INT") {
                            if (call->arguments.size() != 1) {
                                throw ToolError("BAD CALL INT");
                            }
                            const RealSlot source_value = emit_real_expr(call->arguments.front());
                            emit_set_real_pointer(source_value, 0x02);
                            emit_jsr_import("RT_F_TO_I");
                        } else {
                            emit_load_word(op.aux);
                        }
                    } else {
                        emit_load_word(op.aux);
                    }
                    emit_store_variable(variable->second);
                    if (expression_uses_variable(op.aux)) {
                        constants.erase(target);
                    } else if (auto value = try_evaluate_action_word(op.aux, constants)) {
                        const ActionWordType target_type = variable->second.is_signed
                            ? ActionWordType::Int
                            : variable->second.is_card
                                ? ActionWordType::Card
                                : ActionWordType::Byte;
                        constants[target] = normalize_action_word(*value, target_type);
                    } else {
                        constants.erase(target);
                    }
                }
            } else if (op.kind == SourceOp::Kind::PrintInt) {
                if (expression_uses_variable(op.value)) {
                    emit_load_word(op.value);
                    emit_jsr_import("RT_PRINT_I");
                    emit_cr();
                } else {
                    auto value = try_evaluate_action_word(op.value, constants);
                    if (!value) {
                        throw ToolError("BAD PRINT EXPR");
                    }
                    emit_text(std::to_string(static_cast<std::int16_t>(
                        action_word_bits(*value))));
                }
            } else if (op.kind == SourceOp::Kind::PrintIntCall) {
                emit_load_word(op.value);
                emit_jsr_import("RT_PRINT_I");
            } else if (op.kind == SourceOp::Kind::PrintReal) {
                const RealSlot value = emit_real_expr(op.value);
                emit_set_real_pointer(value, 0x02);
                emit_jsr_import("RT_PRINT_F");
                if (op.aux == "NEWLINE") {
                    emit_cr();
                }
            } else {
                ParsedCall parsed_call{op.value, split_call_arguments(op.aux)};
                if (upper_ascii(parsed_call.name) == "OVERLAYCALL") {
                    if (parsed_call.arguments.size() != 1) {
                        throw ToolError(
                            "BAD OVERLAY CALL LINE " + std::to_string(op.line));
                    }
                    const std::string target_text = trim(parsed_call.arguments.front());
                    if (target_text.empty() ||
                        target_text.find_first_not_of(
                            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") !=
                            std::string::npos) {
                        throw ToolError(
                            "BAD OVERLAY CALL LINE " + std::to_string(op.line));
                    }
                    const std::string target = module_from_arg(target_text);
                    if (overlay_names.count(target) == 0) {
                        throw ToolError(
                            "UNKNOWN OVERLAY LINE " + std::to_string(op.line) + ": " +
                            target);
                    }
                    code.push_back(0x20);  // Program-owned overlay is a direct JSR.
                    const std::uint16_t operand_offset =
                        static_cast<std::uint16_t>(code.size());
                    code.push_back(0x00);
                    code.push_back(0x00);
                    add_reloc(operand_offset, target);
                    continue;
                }
                if (emit_builtin(parsed_call)) {
                    continue;
                }
                if (emit_external_routine_call(parsed_call)) {
                    continue;
                }
                if (emit_local_routine_call(parsed_call)) {
                    continue;
                }
                if (!parsed_call.arguments.empty()) {
                    throw ToolError(
                        "UNSUPPORTED CALL ARGS LINE " + std::to_string(op.line) + ": " + op.value);
                }
                const std::string call = upper_ascii(op.value);
                code.push_back(0x20);  // JSR absolute
                const std::uint16_t operand_offset = static_cast<std::uint16_t>(code.size());
                code.push_back(0x00);
                code.push_back(0x00);
                ObjReloc reloc;
                reloc.offset = operand_offset;
                if (local_names.count(call) != 0) {
                    reloc.symbol = call;
                } else {
                    reloc.import = true;
                    reloc.import_index = add_import(call);
                }
                relocs.push_back(reloc);
            }
        }
        if (!if_stack.empty()) {
            throw ToolError("BAD IF");
        }
        if (pending_while) {
            throw ToolError(
                "WHILE REQUIRES DO LINE " + std::to_string(pending_while->second));
        }
        if (pending_for) {
            throw ToolError(
                "FOR REQUIRES DO LINE " + std::to_string(pending_for->line));
        }
        if (!loop_stack.empty()) {
            throw ToolError("BAD LOOP");
        }
        if (!terminal_top_level_return) {
            code.push_back(0x60);  // Fall-through RTS
        }
        const std::uint16_t proc_size = static_cast<std::uint16_t>(code.size() - proc_offset);
        exports.push_back(ObjExport{upper_ascii(proc.name), proc_offset, proc_size});
    }

    std::size_t final_data_size = 0;
    for (const VarSlot& slot : data_slots) {
        final_data_size += slot.is_card ? 2 : 1;
    }
    for (const RealSlot& slot : real_slots) {
        final_data_size += slot.absolute_address ? 2 : 6;
    }
    for (const ExprTempSlot& slot : expr_temp_slots) {
        (void)slot;
        final_data_size += 4;
    }
    for (const ArraySlot& slot : array_slots) {
        final_data_size += slot.initial_data.size() + 2;
        if (!slot.initial_data.empty() && slot.alignment > 1) {
            final_data_size += slot.alignment - 1;
        }
    }
    final_data_size += address_constant_slots.size() * 2;
    if (code.size() > 0xFFFF ||
        final_data_size > 0xFFFF - code.size()) {
        throw ToolError("TARGET OBJECT TOO LARGE");
    }

    for (const VarSlot& slot : data_slots) {
        const std::uint16_t lo_offset = static_cast<std::uint16_t>(code.size());
        code.push_back(static_cast<std::uint8_t>(slot.initial_value & 0xFF));
        exports.push_back(ObjExport{slot.lo_symbol, lo_offset, 1});
        if (!slot.initial_address_symbol.empty()) {
            if (!slot.is_card) {
                throw ToolError("BYTE LINKED INITIALIZER " + slot.name);
            }
            code.back() = 0;
            add_reloc(
                lo_offset,
                slot.initial_address_symbol,
                slot.initial_address_addend);
        }
        if (slot.is_card) {
            const std::uint16_t hi_offset = static_cast<std::uint16_t>(code.size());
            code.push_back(static_cast<std::uint8_t>(slot.initial_value >> 8));
            exports.push_back(ObjExport{slot.hi_symbol, hi_offset, 1});
        }
    }

    for (const ArraySlot& slot : array_slots) {
        if (!slot.initial_data.empty()) {
            if (slot.alignment == 0 ||
                (slot.alignment & (slot.alignment - 1)) != 0) {
                throw ToolError("BAD ARRAY ALIGNMENT");
            }
            while (code.size() % slot.alignment != 0) {
                code.push_back(0x00);
            }
            const std::uint16_t data_offset =
                static_cast<std::uint16_t>(code.size());
            code.insert(
                code.end(), slot.initial_data.begin(), slot.initial_data.end());
            for (const ArraySlot::InitialRelocation& relocation :
                 slot.initial_relocations) {
                if (relocation.offset + 1 >= slot.initial_data.size()) {
                    throw ToolError("BAD ARRAY INITIALIZER RELOCATION");
                }
                add_reloc(
                    static_cast<std::uint16_t>(data_offset + relocation.offset),
                    relocation.symbol,
                    relocation.addend);
            }
            exports.push_back(ObjExport{
                slot.data_symbol,
                data_offset,
                static_cast<std::uint16_t>(slot.initial_data.size()),
            });
            if (!slot.frame_byte_symbols.empty() &&
                slot.frame_byte_symbols.size() != slot.initial_data.size()) {
                throw ToolError("BAD ARRAY FRAME");
            }
            for (std::size_t i = 0; i < slot.frame_byte_symbols.size(); ++i) {
                exports.push_back(ObjExport{
                    slot.frame_byte_symbols[i],
                    static_cast<std::uint16_t>(data_offset + i),
                    1,
                });
            }
        }

        const std::uint16_t pointer_offset =
            static_cast<std::uint16_t>(code.size());
        if (slot.absolute_data_address) {
            code.push_back(static_cast<std::uint8_t>(
                *slot.absolute_data_address & 0xFF));
            code.push_back(static_cast<std::uint8_t>(
                *slot.absolute_data_address >> 8));
        } else if (!slot.linked_data_address_symbol.empty()) {
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(
                pointer_offset,
                slot.linked_data_address_symbol,
                slot.linked_data_address_addend);
        } else {
            code.push_back(0x00);
            code.push_back(0x00);
            if (!slot.initial_data.empty()) {
                add_reloc(pointer_offset, slot.data_symbol);
            }
        }
        exports.push_back(ObjExport{
            slot.indexed.pointer.lo_symbol,
            pointer_offset,
            1,
        });
        exports.push_back(ObjExport{
            slot.indexed.pointer.hi_symbol,
            static_cast<std::uint16_t>(pointer_offset + 1),
            1,
        });
    }

    for (const RealSlot& slot : real_slots) {
        if (slot.byte_symbols.size() != 4 || slot.initial_value.size() != 4) {
            throw ToolError("BAD REAL SLOT");
        }
        if (!slot.absolute_address) {
            for (std::size_t i = 0; i < 4; ++i) {
                const std::uint16_t offset = static_cast<std::uint16_t>(code.size());
                code.push_back(slot.initial_value[i]);
                exports.push_back(ObjExport{slot.byte_symbols[i], offset, 1});
            }
        }

        const std::uint16_t pointer_offset = static_cast<std::uint16_t>(code.size());
        if (slot.absolute_address) {
            code.push_back(static_cast<std::uint8_t>(*slot.absolute_address & 0xFF));
            code.push_back(static_cast<std::uint8_t>(*slot.absolute_address >> 8));
        } else {
            code.push_back(0x00);
            code.push_back(0x00);
            add_reloc(pointer_offset, slot.byte_symbols.front());
        }
        exports.push_back(ObjExport{slot.pointer_lo_symbol, pointer_offset, 1});
        exports.push_back(ObjExport{
            slot.pointer_hi_symbol,
            static_cast<std::uint16_t>(pointer_offset + 1),
            1,
        });
    }

    for (const ExprTempSlot& slot : expr_temp_slots) {
        std::uint16_t offset = static_cast<std::uint16_t>(code.size());
        code.push_back(0x00);
        exports.push_back(ObjExport{slot.value_lo_symbol, offset, 1});
        offset = static_cast<std::uint16_t>(code.size());
        code.push_back(0x00);
        exports.push_back(ObjExport{slot.value_hi_symbol, offset, 1});

        offset = static_cast<std::uint16_t>(code.size());
        code.push_back(0x00);
        code.push_back(0x00);
        exports.push_back(ObjExport{slot.pointer_lo_symbol, offset, 1});
        exports.push_back(ObjExport{
            slot.pointer_hi_symbol,
            static_cast<std::uint16_t>(offset + 1),
            1,
        });
        add_reloc(offset, slot.value_lo_symbol);
    }

    for (const AddressConstantSlot& slot : address_constant_slots) {
        const std::uint16_t offset = static_cast<std::uint16_t>(code.size());
        code.push_back(0x00);
        code.push_back(0x00);
        exports.push_back(ObjExport{slot.lo_symbol, offset, 1});
        exports.push_back(ObjExport{
            slot.hi_symbol,
            static_cast<std::uint16_t>(offset + 1),
            1,
        });
        add_reloc(offset, slot.target_symbol, slot.addend);
    }

    std::ostringstream out;
    out << "OBJ1\n";
    out << "f "
        << fs::relative(
               source_path(fs::current_path(), module),
               fs::current_path()).generic_string()
        << "\n";
    for (const ObjExport& export_record : exports) {
        out << "x " << export_record.name << " " << export_record.offset << " "
            << export_record.size << "\n";
    }
    std::string body = "M";
    if (!imports.empty()) {
        body.clear();
        for (std::size_t i = 0; i < imports.size(); ++i) {
            body += "u" + std::to_string(i);
        }
        body += "M";
    }
    out << "b " << body << "\n";
    for (const std::string& symbol : imports) {
        out << "u " << symbol << "\n";
    }
    out << "m " << bytes_to_hex(code) << "\n";
    for (const ObjReloc& reloc : relocs) {
        out << "r " << reloc.offset;
        if (reloc.part == ObjRelocPart::LowByte) {
            out << " lo";
        } else if (reloc.part == ObjRelocPart::HighByte) {
            out << " hi";
        }
        if (reloc.import) {
            out << " u" << reloc.import_index;
        } else {
            out << " x " << reloc.symbol;
        }
        if (reloc.addend != 0) {
            out << " " << reloc.addend;
        }
        out << "\n";
    }
    for (const ObjLineRecord& line : source_lines) {
        out << "l " << line.offset << " " << line.line << "\n";
    }

    write_text_file(object_path(fs::current_path(), module), out.str());
    std::cout << "ACTC OK\n";
    return 0;
}

std::vector<fs::path> object_search_directories(const fs::path& root) {
    std::vector<fs::path> search_dirs;
    append_unique_directory(search_dirs, root);
    append_unique_directory(search_dirs, project_dir(root, "OBJ"));
    for (const fs::path& directory : library_search_directories(root)) {
        append_unique_directory(search_dirs, directory);
    }
    return search_dirs;
}

fs::path find_object_for_symbol(const fs::path& root, const std::string& symbol) {
    const std::string wanted = upper_ascii(symbol);
    std::string filename_stem = wanted;
    std::replace(filename_stem.begin(), filename_stem.end(), '.', '_');
    const std::vector<fs::path> search_dirs = object_search_directories(root);
    for (const fs::path& dir : search_dirs) {
        auto found = child_case_insensitive(dir, wanted + ".OBJ");
        if (!found && filename_stem != wanted) {
            found = child_case_insensitive(dir, filename_stem + ".OBJ");
        }
        if (found && fs::is_regular_file(*found)) {
            return *found;
        }
    }

    std::vector<fs::path> candidates;
    for (const fs::path& dir : search_dirs) {
        if (!fs::is_directory(dir)) {
            continue;
        }
        for (const fs::directory_entry& entry : fs::directory_iterator(dir)) {
            if (entry.is_regular_file() &&
                upper_ascii(entry.path().extension().string()) == ".OBJ") {
                candidates.push_back(entry.path());
            }
        }
    }
    std::sort(candidates.begin(), candidates.end(), [](const fs::path& lhs, const fs::path& rhs) {
        return upper_ascii(lhs.generic_string()) < upper_ascii(rhs.generic_string());
    });

    std::vector<fs::path> matches;
    std::set<std::string> seen_paths;
    for (const fs::path& candidate : candidates) {
        if (!seen_paths.insert(upper_ascii(candidate.lexically_normal().generic_string())).second) {
            continue;
        }
        try {
            const ObjectFile object = parse_object_file(candidate);
            const bool exports_symbol = std::any_of(
                object.exports.begin(),
                object.exports.end(),
                [&](const ObjExport& export_record) {
                    return export_record.name == wanted;
                });
            if (exports_symbol) {
                matches.push_back(candidate);
            }
        } catch (const ToolError&) {
            // Unselected malformed or legacy objects are outside the closure.
        }
    }
    if (matches.size() > 1) {
        throw ToolError("DUPLICATE EXPORT " + wanted);
    }
    if (!matches.empty()) {
        return matches.front();
    }
    throw ToolError("UNRESOLVED " + wanted);
}

int cmd_alink(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("NO NAME");
    }
    const fs::path root = fs::current_path();
    const std::string module = module_from_arg(args.front());
    require_project_module(root, module);

    std::vector<ObjectFile> objects;
    std::map<std::string, std::size_t> loaded_modules;
    std::map<std::string, std::pair<std::size_t, ObjExport>> exports;
    std::size_t cursor = 0;

    auto load_one = [&](const fs::path& path) -> std::size_t {
        ObjectFile object = parse_object_file(path);
        auto found = loaded_modules.find(object.module);
        if (found != loaded_modules.end()) {
            return found->second;
        }
        const std::size_t index = objects.size();
        loaded_modules[object.module] = index;
        for (const ObjExport& export_record : object.exports) {
            const std::string name = upper_ascii(export_record.name);
            if (exports.find(name) != exports.end()) {
                throw ToolError("DUPLICATE EXPORT " + name);
            }
            exports[name] = {index, export_record};
        }
        objects.push_back(std::move(object));
        return index;
    };

    load_one(object_path(root, module));
    while (cursor < objects.size()) {
        const std::vector<std::string> pending_imports = objects[cursor].imports;
        const std::vector<ObjReloc> pending_relocs = objects[cursor].relocs;
        ++cursor;
        for (const std::string& symbol : pending_imports) {
            if (exports.find(symbol) == exports.end()) {
                load_one(find_object_for_symbol(root, symbol));
            }
        }
        for (const ObjReloc& reloc : pending_relocs) {
            if (!reloc.import && !reloc.symbol.empty() && exports.find(reloc.symbol) == exports.end()) {
                load_one(find_object_for_symbol(root, reloc.symbol));
            }
        }
    }

    const auto main_export = exports.find("MAIN");
    if (main_export == exports.end()) {
        throw ToolError("NO MAIN");
    }
    if (main_export->second.first != 0 || main_export->second.second.offset != 0) {
        throw ToolError("MAIN NOT ENTRY");
    }

    const std::uint16_t load_address = 0x1000;
    std::vector<std::uint16_t> object_bases(objects.size(), 0);
    std::uint32_t address_cursor = load_address;
    for (std::size_t i = 0; i < objects.size(); ++i) {
        object_bases[i] = static_cast<std::uint16_t>(address_cursor);
        address_cursor += objects[i].code.size();
        if (address_cursor > 0x10000) {
            throw ToolError("PRG TOO LARGE");
        }
    }

    std::map<std::string, std::uint16_t> symbol_addresses;
    for (const auto& item : exports) {
        const std::size_t object_index = item.second.first;
        const ObjExport& export_record = item.second.second;
        symbol_addresses[item.first] = static_cast<std::uint16_t>(object_bases[object_index] + export_record.offset);
    }

    for (ObjectFile& object : objects) {
        for (const ObjReloc& reloc : object.relocs) {
            std::string target;
            if (reloc.import) {
                if (reloc.import_index < 0 ||
                    static_cast<std::size_t>(reloc.import_index) >= object.imports.size()) {
                    throw ToolError("BAD OBJECT");
                }
                target = object.imports[static_cast<std::size_t>(reloc.import_index)];
            } else {
                target = reloc.symbol;
            }
            auto found = symbol_addresses.find(upper_ascii(target));
            if (found == symbol_addresses.end()) {
                throw ToolError("UNRESOLVED " + target);
            }
            const std::size_t relocation_width =
                reloc.part == ObjRelocPart::Word ? 2 : 1;
            if (reloc.offset >= object.code.size() ||
                relocation_width > object.code.size() - reloc.offset) {
                throw ToolError("BAD RELOC");
            }
            const std::int64_t relocated =
                static_cast<std::int64_t>(found->second) + reloc.addend;
            if (relocated < 0 || relocated > 0xFFFF) {
                throw ToolError("RELOCATION RANGE " + target);
            }
            if (reloc.part == ObjRelocPart::LowByte) {
                object.code[reloc.offset] =
                    static_cast<std::uint8_t>(relocated & 0xFF);
            } else if (reloc.part == ObjRelocPart::HighByte) {
                object.code[reloc.offset] =
                    static_cast<std::uint8_t>((relocated >> 8) & 0xFF);
            } else {
                object.code[reloc.offset] =
                    static_cast<std::uint8_t>(relocated & 0xFF);
                object.code[reloc.offset + 1] =
                    static_cast<std::uint8_t>((relocated >> 8) & 0xFF);
            }
        }
    }

    std::vector<std::uint8_t> prg;
    prg.push_back(static_cast<std::uint8_t>(load_address & 0xFF));
    prg.push_back(static_cast<std::uint8_t>((load_address >> 8) & 0xFF));
    for (const ObjectFile& object : objects) {
        prg.insert(prg.end(), object.code.begin(), object.code.end());
    }
    write_binary_file(binary_path(root, module), prg);

    std::ostringstream dbg;
    dbg << "DBG1\n";
    dbg << "e " << symbol_addresses.at("MAIN") << "\n";
    for (std::size_t module_id = 0; module_id < objects.size(); ++module_id) {
        const ObjectFile& object = objects[module_id];
        dbg << "m " << module_id << " " << object.module << "\n";
        if (!object.source_file.empty()) {
            dbg << "f " << module_id << " " << object.source_file << "\n";
            for (const ObjLineRecord& line : object.lines) {
                dbg << "l "
                    << static_cast<std::uint16_t>(
                           object_bases[module_id] + line.offset)
                    << " " << module_id << " " << line.line << "\n";
            }
            for (const ObjExport& symbol : object.exports) {
                dbg << "y "
                    << static_cast<std::uint16_t>(
                           object_bases[module_id] + symbol.offset)
                    << " " << symbol.size << " " << symbol.name << "\n";
            }
        }
    }
    write_text_file(debug_path(root, module), dbg.str());

    std::vector<action_linux::CodeMapModule> code_map_modules;
    code_map_modules.reserve(objects.size());
    for (std::size_t module_id = 0; module_id < objects.size(); ++module_id) {
        const ObjectFile& object = objects[module_id];
        action_linux::CodeMapModule linked;
        linked.module = object.module;
        linked.source_path = object.source_file;
        linked.base_address = object_bases[module_id];
        linked.size = static_cast<std::uint32_t>(object.code.size());
        for (const ObjLineRecord& line : object.lines) {
            linked.lines.push_back(action_linux::CodeMapLine{
                static_cast<std::uint16_t>(object_bases[module_id] + line.offset),
                line.line,
            });
        }
        for (const ObjExport& symbol : object.exports) {
            linked.symbols.push_back(action_linux::CodeMapSymbol{
                symbol.name,
                static_cast<std::uint16_t>(
                    object_bases[module_id] + symbol.offset),
                symbol.size,
            });
        }
        code_map_modules.push_back(std::move(linked));
    }
    action_linux::build_code_map(root, module, prg, code_map_modules);

    std::cout << "ALINK OK\n";
    return 0;
}

using CommandFn = int (*)(const std::vector<std::string>&);

std::optional<CommandFn> lookup_command(const std::string& command) {
    const std::string name = upper_ascii(command);
    if (name == "ACTNEW") return cmd_actnew;
    if (name == "ACTADD") return cmd_actadd;
    if (name == "ACTWORK") return cmd_actwork;
    if (name == "ACTSRC") return cmd_actsrc;
    if (name == "ACTFILE") return cmd_actfile;
    if (name == "ACTCHK") return cmd_actchk;
    if (name == "ACTDIR") return cmd_actdir;
    if (name == "ACTCOPY") return cmd_actcopy;
    if (name == "ACTDEL") return cmd_actdel;
    if (name == "ACTMKDIR") return cmd_actmkdir;
    if (name == "ACTRMDIR") return cmd_actrmdir;
    if (name == "ACTMOVE" || name == "ACTREN") return cmd_actmove;
    if (name == "ACTWRITE") return cmd_actwrite;
    if (name == "ACTINFO") return cmd_actinfo;
    if (name == "ACTMON") return cmd_actmon;
    if (name == "ACTDBG") return cmd_actdbg;
    if (name == "ACTPROF") return action_linux::command_actprof;
    if (name == "ACTTREE" || name == "TREE") return cmd_acttree;
    if (name == "XCOPY") return cmd_xcopy;
    if (name == "DELTREE") return cmd_deltree;
    if (name == "ACTSPC") return action_linux::command_actspc;
    if (name == "ACTSPRITE") return action_linux::command_actsprite;
    if (name == "ACTBITMAP") return action_linux::command_actbitmap;
    if (name == "ACTEDIT") return cmd_actedit;
    if (name == "ACTHELP") return action_linux::command_acthelp;
    if (name == "ACT2SAVE" || name == "ACTSAVE") return cmd_act2save;
    if (name == "ACTC") return cmd_actc;
    if (name == "ALINK") return cmd_alink;
    return std::nullopt;
}

std::string basename_without_extension(const char* argv0) {
    std::string base = fs::path(argv0).filename().string();
    const std::string suffix = ".exe";
    if (base.size() >= suffix.size() &&
        upper_ascii(std::string_view(base).substr(base.size() - suffix.size())) == upper_ascii(suffix)) {
        base.resize(base.size() - suffix.size());
    }
    return base;
}

void usage() {
    std::cerr
        << "usage: actnew <project>\n"
        << "       actadd <module>\n"
        << "       actwork\n"
        << "       actsrc\n"
        << "       actfile <module>\n"
        << "       actchk\n"
        << "       actdir [dir]\n"
        << "       actcopy <src> <dst>\n"
        << "       actdel <path>\n"
        << "       actmkdir <dir>\n"
        << "       actrmdir <dir>\n"
        << "       actmove <src> <dst>\n"
        << "       actwrite <path> [text...]\n"
        << "       actinfo\n"
        << "       actmon [status|sources|check|edit|compile|build|debug [module]]\n"
        << "       actdbg <module> [symbols|source|line|break|breaks|clear|live [-- program-args...]]\n"
        << "       actprof <module> [report [run-id]|import <samples> [interval-us]|live [seconds]]\n"
        << "       acttree [dir]\n"
        << "       xcopy <src> <dst>\n"
        << "       deltree <path>\n"
        << "       actspc <file-or-filespec> [file-or-filespec ...]\n"
        << "       actsprite <resource.spr> [tui|new [multicolor]|set x y [value]|clear|color n|print|info]\n"
        << "       actbitmap <resource.abm> [tui|new width height [multicolor]|set x y [value]|clear|print|info]\n"
        << "       actedit <module> [tui|highlight|print|append|insert|replace|delete|index|find|symbols|map|definition|references|compile|build|debug ...]\n"
        << "       acthelp [keyword-or-function|search <text>|list [kind]]\n"
        << "       act2save [module]\n"
        << "       actc <module>\n"
        << "       alink <module>\n";
}

}  // namespace

int main(int argc, char** argv) {
    action_linux::set_program_path(argv[0]);
    std::string command = basename_without_extension(argv[0]);
    int first_arg = 1;
    auto fn = lookup_command(command);
    if (!fn && argc > 1) {
        command = argv[1];
        fn = lookup_command(command);
        first_arg = 2;
    }
    if (!fn) {
        usage();
        return 2;
    }

    std::vector<std::string> args;
    args.reserve(static_cast<std::size_t>(std::max(0, argc - first_arg)));
    for (int i = first_arg; i < argc; ++i) {
        args.emplace_back(argv[i]);
    }

    try {
        g_invocation_cwd = fs::current_path();
        if (command_uses_project_context(command) &&
            !invocation_has_local_module(command, args)) {
            if (const auto root = selected_project_root()) {
                fs::current_path(*root);
            }
        }
        return (*fn)(args);
    } catch (const ToolError& err) {
        std::cerr << err.what() << "\n";
        return 1;
    } catch (const fs::filesystem_error& err) {
        std::cerr << err.what() << "\n";
        return 1;
    } catch (const std::exception& err) {
        std::cerr << "ERROR: " << err.what() << "\n";
        return 1;
    }
}
