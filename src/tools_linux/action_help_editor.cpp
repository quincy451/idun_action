#include "action_help_editor.hpp"

#include "action_code_map.hpp"
#include "action_formatter.hpp"

#include <algorithm>
#include <cerrno>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <poll.h>
#include <regex>
#include <set>
#include <sstream>
#include <string_view>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <utility>

#include <sqlite3.h>

namespace fs = std::filesystem;

namespace action_linux {
namespace {

constexpr int kHelpSchemaVersion = 1;
fs::path g_program_path;

std::string upper_ascii(std::string_view input) {
    std::string result;
    result.reserve(input.size());
    for (const unsigned char ch : input) {
        result.push_back(static_cast<char>(std::toupper(ch)));
    }
    return result;
}

std::string trim(std::string_view input) {
    std::size_t begin = 0;
    while (begin < input.size() &&
           std::isspace(static_cast<unsigned char>(input[begin]))) {
        ++begin;
    }
    std::size_t end = input.size();
    while (end > begin &&
           std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }
    return std::string(input.substr(begin, end - begin));
}

std::optional<fs::path> find_relative_case_insensitive(
    const fs::path& root,
    const fs::path& relative) {
    fs::path current = root;
    for (const fs::path& component : relative) {
        const std::string wanted = component.string();
        if (wanted.empty() || wanted == ".") {
            continue;
        }
        if (!fs::is_directory(current)) {
            return std::nullopt;
        }
        const std::string wanted_upper = upper_ascii(wanted);
        std::optional<fs::path> matched;
        for (const fs::directory_entry& entry : fs::directory_iterator(current)) {
            if (upper_ascii(entry.path().filename().string()) == wanted_upper) {
                matched = entry.path();
                break;
            }
        }
        if (!matched) {
            return std::nullopt;
        }
        current = *matched;
    }
    return current;
}

std::vector<std::string> split_path_list(std::string_view value) {
    std::vector<std::string> parts;
    std::size_t begin = 0;
    while (begin <= value.size()) {
        const std::size_t end = value.find(':', begin);
        parts.emplace_back(value.substr(
            begin,
            end == std::string_view::npos ? std::string_view::npos : end - begin));
        if (end == std::string_view::npos) {
            break;
        }
        begin = end + 1;
    }
    return parts;
}

fs::path executable_path_from_argv0(const char* argv0) {
    std::error_code error;
    const fs::path proc_path = fs::read_symlink("/proc/self/exe", error);
    if (!error && !proc_path.empty()) {
        return fs::absolute(proc_path);
    }

    fs::path supplied(argv0 == nullptr ? "" : argv0);
    if (supplied.has_parent_path()) {
        return fs::absolute(supplied);
    }
    const char* path_value = std::getenv("PATH");
    if (path_value != nullptr) {
        for (const std::string& directory : split_path_list(path_value)) {
            const fs::path candidate =
                (directory.empty() ? fs::path(".") : fs::path(directory)) / supplied;
            if (fs::is_regular_file(candidate, error) && !error) {
                return fs::absolute(candidate);
            }
            error.clear();
        }
    }
    return fs::absolute(supplied.empty() ? fs::path("action-workspace-tools") : supplied);
}

fs::path locate_help_database() {
    const char* override_path = std::getenv("ACTION_HELP_DB");
    if (override_path != nullptr && *override_path != '\0') {
        const fs::path candidate = fs::absolute(override_path);
        if (!fs::is_regular_file(candidate)) {
            throw ToolError("HELP DATABASE NOT FOUND: " + candidate.string());
        }
        return candidate;
    }

    const fs::path executable =
        g_program_path.empty() ? executable_path_from_argv0(nullptr) : g_program_path;
    const fs::path executable_dir = executable.parent_path();
    const std::vector<fs::path> candidates = {
        executable_dir / "action-help.sqlite3",
        executable_dir.parent_path() / "DOC" / "action-help.sqlite3",
        fs::current_path() / "action-help.sqlite3",
        fs::current_path() / "DOC" / "action-help.sqlite3",
        "/usr/local/share/actionc64u/action-help.sqlite3",
        "/usr/share/actionc64u/action-help.sqlite3",
    };
    std::set<fs::path> checked;
    for (const fs::path& candidate : candidates) {
        const fs::path absolute = fs::absolute(candidate);
        if (checked.insert(absolute).second && fs::is_regular_file(absolute)) {
            return absolute;
        }
    }
    throw ToolError("HELP DATABASE NOT FOUND; set ACTION_HELP_DB");
}

class ReadOnlyDatabase {
public:
    explicit ReadOnlyDatabase(const fs::path& path) {
        const int status = sqlite3_open_v2(
            path.c_str(),
            &database_,
            SQLITE_OPEN_READONLY,
            nullptr);
        if (status != SQLITE_OK) {
            const std::string message = database_ == nullptr
                ? "open failed"
                : sqlite3_errmsg(database_);
            if (database_ != nullptr) {
                sqlite3_close(database_);
                database_ = nullptr;
            }
            throw ToolError("HELP DATABASE OPEN: " + message);
        }
        sqlite3_busy_timeout(database_, 1000);
        sqlite3_stmt* statement = nullptr;
        if (sqlite3_prepare_v2(
                database_, "PRAGMA user_version", -1, &statement, nullptr) != SQLITE_OK) {
            throw ToolError("HELP DATABASE SCHEMA READ FAILED");
        }
        const int step_status = sqlite3_step(statement);
        const int version = step_status == SQLITE_ROW ? sqlite3_column_int(statement, 0) : -1;
        sqlite3_finalize(statement);
        if (step_status != SQLITE_ROW) {
            throw ToolError("HELP DATABASE SCHEMA READ FAILED");
        }
        if (version != kHelpSchemaVersion) {
            throw ToolError(
                "HELP DATABASE SCHEMA " + std::to_string(version) +
                " (expected " + std::to_string(kHelpSchemaVersion) + ")");
        }
    }

    ReadOnlyDatabase(const ReadOnlyDatabase&) = delete;
    ReadOnlyDatabase& operator=(const ReadOnlyDatabase&) = delete;

    ~ReadOnlyDatabase() {
        if (database_ != nullptr) {
            sqlite3_close(database_);
        }
    }

    sqlite3* get() const {
        return database_;
    }

private:
    sqlite3* database_ = nullptr;
};

class Statement {
public:
    Statement(sqlite3* database, const char* sql) : database_(database) {
        if (sqlite3_prepare_v2(database_, sql, -1, &statement_, nullptr) != SQLITE_OK) {
            throw ToolError("HELP DATABASE QUERY: " + std::string(sqlite3_errmsg(database_)));
        }
    }

    Statement(const Statement&) = delete;
    Statement& operator=(const Statement&) = delete;

    ~Statement() {
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
            throw ToolError("HELP DATABASE BIND: " + std::string(sqlite3_errmsg(database_)));
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
        throw ToolError("HELP DATABASE STEP: " + std::string(sqlite3_errmsg(database_)));
    }

    std::string text(int column) const {
        const unsigned char* value = sqlite3_column_text(statement_, column);
        return value == nullptr
            ? std::string{}
            : std::string(reinterpret_cast<const char*>(value));
    }

    int integer(int column) const {
        return sqlite3_column_int(statement_, column);
    }

private:
    sqlite3* database_ = nullptr;
    sqlite3_stmt* statement_ = nullptr;
};

struct HelpTopic {
    std::string token;
    std::string kind;
    std::string signature;
    std::string summary;
    std::string details;
    std::string example;
    std::string library;
    std::string target_notes;
};

struct LibraryReference {
    std::string name;
    std::string details;
    std::string target_notes;
    std::size_t topic_count = 0;
};

HelpTopic topic_from_statement(const Statement& statement) {
    return HelpTopic{
        statement.text(0),
        statement.text(1),
        statement.text(2),
        statement.text(3),
        statement.text(4),
        statement.text(5),
        statement.text(6),
        statement.text(7),
    };
}

class HelpCatalog {
public:
    HelpCatalog() : path_(locate_help_database()), database_(path_) {}

    const fs::path& path() const {
        return path_;
    }

    std::optional<HelpTopic> lookup(std::string_view token) {
        const std::string key = upper_ascii(token);
        const auto cached = cache_.find(key);
        if (cached != cache_.end()) {
            return cached->second;
        }
        Statement query(
            database_.get(),
            "SELECT token,kind,signature,summary,details,example,library,target_notes "
            "FROM topics WHERE token=?1 COLLATE NOCASE "
            "UNION ALL "
            "SELECT t.token,t.kind,t.signature,t.summary,t.details,t.example,t.library,t.target_notes "
            "FROM aliases a JOIN topics t ON t.token=a.token "
            "WHERE a.alias=?2 COLLATE NOCASE LIMIT 1");
        query.bind_text(1, token);
        query.bind_text(2, token);
        std::optional<HelpTopic> result;
        if (query.step()) {
            result = topic_from_statement(query);
        }
        cache_.emplace(key, result);
        return result;
    }

    int count() const {
        Statement query(database_.get(), "SELECT count(*) FROM topics");
        if (!query.step()) {
            throw ToolError("HELP DATABASE COUNT FAILED");
        }
        return query.integer(0);
    }

    std::vector<HelpTopic> list(std::string_view kind) const {
        Statement query(
            database_.get(),
            "SELECT token,kind,signature,summary,details,example,library,target_notes "
            "FROM topics WHERE ?1='' OR kind=?1 COLLATE NOCASE "
            "ORDER BY token COLLATE NOCASE");
        query.bind_text(1, kind);
        std::vector<HelpTopic> topics;
        while (query.step()) {
            topics.push_back(topic_from_statement(query));
        }
        return topics;
    }

    std::vector<HelpTopic> list_core(std::string_view kind) const {
        Statement query(
            database_.get(),
            "SELECT token,kind,signature,summary,details,example,library,target_notes "
            "FROM topics WHERE (library='' OR library='CORE' COLLATE NOCASE) "
            "AND (?1='' OR kind=?1 COLLATE NOCASE) "
            "ORDER BY token COLLATE NOCASE");
        query.bind_text(1, kind);
        std::vector<HelpTopic> topics;
        while (query.step()) {
            topics.push_back(topic_from_statement(query));
        }
        return topics;
    }

    std::vector<LibraryReference> libraries() const {
        Statement query(
            database_.get(),
            "SELECT library,min(details),min(target_notes),count(*) FROM topics "
            "WHERE library<>'' AND library<>'CORE' COLLATE NOCASE "
            "GROUP BY library ORDER BY library COLLATE NOCASE");
        std::vector<LibraryReference> result;
        while (query.step()) {
            result.push_back(LibraryReference{
                query.text(0),
                query.text(1),
                query.text(2),
                static_cast<std::size_t>(query.integer(3)),
            });
        }
        return result;
    }

    std::vector<HelpTopic> list_library(std::string_view library) const {
        Statement query(
            database_.get(),
            "SELECT token,kind,signature,summary,details,example,library,target_notes "
            "FROM topics WHERE library=?1 COLLATE NOCASE "
            "ORDER BY token COLLATE NOCASE");
        query.bind_text(1, library);
        std::vector<HelpTopic> topics;
        while (query.step()) {
            topics.push_back(topic_from_statement(query));
        }
        return topics;
    }

    std::vector<HelpTopic> search(std::string_view text) const {
        Statement query(
            database_.get(),
            "SELECT token,kind,signature,summary,details,example,library,target_notes "
            "FROM topics WHERE token LIKE ?1 COLLATE NOCASE "
            "OR signature LIKE ?1 COLLATE NOCASE "
            "OR summary LIKE ?1 COLLATE NOCASE "
            "OR details LIKE ?1 COLLATE NOCASE "
            "OR library LIKE ?1 COLLATE NOCASE "
            "ORDER BY token COLLATE NOCASE LIMIT 50");
        const std::string pattern = "%" + std::string(text) + "%";
        query.bind_text(1, pattern);
        std::vector<HelpTopic> topics;
        while (query.step()) {
            topics.push_back(topic_from_statement(query));
        }
        return topics;
    }

private:
    fs::path path_;
    ReadOnlyDatabase database_;
    std::map<std::string, std::optional<HelpTopic>> cache_;
};

std::size_t output_width() {
    winsize size{};
    if (::isatty(STDOUT_FILENO) != 0 &&
        ::ioctl(STDOUT_FILENO, TIOCGWINSZ, &size) == 0 && size.ws_col > 0) {
        return std::max<std::size_t>(40, size.ws_col);
    }
    return 80;
}

std::vector<std::string> wrap_text(std::string_view text, std::size_t width) {
    width = std::max<std::size_t>(1, width);
    std::vector<std::string> lines;
    std::istringstream paragraphs{std::string(text)};
    std::string paragraph;
    while (std::getline(paragraphs, paragraph)) {
        if (paragraph.empty()) {
            lines.emplace_back();
            continue;
        }
        std::istringstream words(paragraph);
        std::string word;
        std::string line;
        while (words >> word) {
            if (word.size() > width) {
                if (!line.empty()) {
                    lines.push_back(line);
                    line.clear();
                }
                std::size_t begin = 0;
                while (begin < word.size()) {
                    lines.push_back(word.substr(begin, width));
                    begin += width;
                }
                continue;
            }
            if (line.empty()) {
                line = word;
            } else if (line.size() + 1 + word.size() <= width) {
                line += " " + word;
            } else {
                lines.push_back(line);
                line = word;
            }
        }
        if (!line.empty()) {
            lines.push_back(line);
        }
    }
    if (lines.empty()) {
        lines.emplace_back();
    }
    return lines;
}

void print_wrapped(std::ostream& output, std::string_view text, std::size_t width) {
    for (const std::string& line : wrap_text(text, width)) {
        output << line << "\n";
    }
}

void print_topic(std::ostream& output, const HelpTopic& topic) {
    const std::size_t width = output_width();
    output << topic.token << " [" << topic.kind << "]";
    if (!topic.library.empty()) {
        output << " - " << topic.library;
    }
    output << "\n" << topic.signature << "\n\n";
    print_wrapped(output, topic.summary, width);
    if (!topic.details.empty()) {
        output << "\n";
        print_wrapped(output, topic.details, width);
    }
    if (!topic.example.empty()) {
        output << "\nExample:\n";
        std::istringstream example(topic.example);
        std::string line;
        while (std::getline(example, line)) {
            output << "  " << line << "\n";
        }
    }
    if (!topic.target_notes.empty()) {
        output << "\nTarget notes:\n";
        print_wrapped(output, topic.target_notes, width);
    }
}

bool is_identifier_start(char ch) {
    const unsigned char value = static_cast<unsigned char>(ch);
    return std::isalpha(value) != 0 || ch == '_';
}

bool is_identifier_char(char ch) {
    const unsigned char value = static_cast<unsigned char>(ch);
    return std::isalnum(value) != 0 || ch == '_';
}

enum class HighlightStyle {
    Normal,
    Keyword,
    Builtin,
    Constant,
    String,
    Number,
    Comment,
};

struct HighlightSpan {
    std::size_t begin = 0;
    std::size_t end = 0;
    HighlightStyle style = HighlightStyle::Normal;
};

HighlightStyle style_for_topic(const std::optional<HelpTopic>& topic) {
    if (!topic) {
        return HighlightStyle::Normal;
    }
    if (topic->kind == "keyword" || topic->kind == "type") {
        return HighlightStyle::Keyword;
    }
    if (topic->kind == "constant") {
        return HighlightStyle::Constant;
    }
    if (topic->kind == "builtin") {
        return HighlightStyle::Builtin;
    }
    return HighlightStyle::Normal;
}

bool starts_number(std::string_view line, std::size_t index) {
    if (std::isdigit(static_cast<unsigned char>(line[index])) != 0) {
        return true;
    }
    if ((line[index] == '$' || line[index] == '%') && index + 1 < line.size()) {
        return std::isalnum(static_cast<unsigned char>(line[index + 1])) != 0;
    }
    return false;
}

std::size_t scan_number(std::string_view line, std::size_t index) {
    std::size_t cursor = index;
    if (line[cursor] == '$') {
        ++cursor;
        while (cursor < line.size() &&
               std::isxdigit(static_cast<unsigned char>(line[cursor])) != 0) {
            ++cursor;
        }
        return cursor;
    }
    if (line[cursor] == '%') {
        ++cursor;
        while (cursor < line.size() &&
               (line[cursor] == '0' || line[cursor] == '1')) {
            ++cursor;
        }
        return cursor;
    }
    if (cursor + 1 < line.size() && line[cursor] == '0' &&
        (line[cursor + 1] == 'x' || line[cursor + 1] == 'X')) {
        cursor += 2;
        while (cursor < line.size() &&
               std::isxdigit(static_cast<unsigned char>(line[cursor])) != 0) {
            ++cursor;
        }
        return cursor;
    }
    while (cursor < line.size() &&
           std::isdigit(static_cast<unsigned char>(line[cursor])) != 0) {
        ++cursor;
    }
    if (cursor < line.size() && line[cursor] == '.') {
        ++cursor;
        while (cursor < line.size() &&
               std::isdigit(static_cast<unsigned char>(line[cursor])) != 0) {
            ++cursor;
        }
    }
    if (cursor < line.size() && (line[cursor] == 'e' || line[cursor] == 'E')) {
        std::size_t exponent = cursor + 1;
        if (exponent < line.size() &&
            (line[exponent] == '+' || line[exponent] == '-')) {
            ++exponent;
        }
        const std::size_t digits = exponent;
        while (exponent < line.size() &&
               std::isdigit(static_cast<unsigned char>(line[exponent])) != 0) {
            ++exponent;
        }
        if (exponent > digits) {
            cursor = exponent;
        }
    }
    return cursor;
}

std::vector<HighlightSpan> highlight_spans(
    std::string_view line,
    HelpCatalog& catalog) {
    std::vector<HighlightSpan> spans;
    std::size_t cursor = 0;
    while (cursor < line.size()) {
        const std::size_t begin = cursor;
        HighlightStyle style = HighlightStyle::Normal;
        if (line[cursor] == ';') {
            spans.push_back({cursor, line.size(), HighlightStyle::Comment});
            break;
        }
        if (line[cursor] == '"') {
            ++cursor;
            bool escaped = false;
            while (cursor < line.size()) {
                const char ch = line[cursor++];
                if (escaped) {
                    escaped = false;
                } else if (ch == '\\') {
                    escaped = true;
                } else if (ch == '"') {
                    break;
                }
            }
            style = HighlightStyle::String;
        } else if (is_identifier_start(line[cursor])) {
            ++cursor;
            while (cursor < line.size() && is_identifier_char(line[cursor])) {
                ++cursor;
            }
            style = style_for_topic(catalog.lookup(line.substr(begin, cursor - begin)));
        } else if (starts_number(line, cursor)) {
            cursor = scan_number(line, cursor);
            style = HighlightStyle::Number;
        } else {
            ++cursor;
            while (cursor < line.size() && line[cursor] != ';' &&
                   line[cursor] != '"' && !is_identifier_start(line[cursor]) &&
                   !starts_number(line, cursor)) {
                ++cursor;
            }
        }
        spans.push_back({begin, cursor, style});
    }
    return spans;
}

const char* ansi_for_style(HighlightStyle style) {
    switch (style) {
        case HighlightStyle::Keyword: return "\x1b[1;36m";
        case HighlightStyle::Builtin: return "\x1b[32m";
        case HighlightStyle::Constant: return "\x1b[35m";
        case HighlightStyle::String: return "\x1b[33m";
        case HighlightStyle::Number: return "\x1b[34m";
        case HighlightStyle::Comment: return "\x1b[2;37m";
        case HighlightStyle::Normal: return "";
    }
    return "";
}

std::string sanitize_visible(std::string_view text) {
    std::string result;
    result.reserve(text.size());
    for (const unsigned char ch : text) {
        if (ch == '\t') {
            result.push_back(' ');
        } else if (ch >= 32 && ch != 127) {
            result.push_back(static_cast<char>(ch));
        } else {
            result.push_back(' ');
        }
    }
    return result;
}

std::string highlighted_window(
    std::string_view line,
    std::size_t begin,
    std::size_t width,
    HelpCatalog& catalog) {
    const std::size_t end = std::min(line.size(), begin + width);
    std::string output;
    for (const HighlightSpan& span : highlight_spans(line, catalog)) {
        const std::size_t visible_begin = std::max(begin, span.begin);
        const std::size_t visible_end = std::min(end, span.end);
        if (visible_begin >= visible_end) {
            continue;
        }
        const char* ansi = ansi_for_style(span.style);
        if (*ansi != '\0') {
            output += ansi;
        }
        output += sanitize_visible(line.substr(visible_begin, visible_end - visible_begin));
        if (*ansi != '\0') {
            output += "\x1b[0m";
        }
    }
    return output;
}

std::vector<std::string> editor_lines_from_text(const std::string& text) {
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
        } else {
            current.push_back(ch);
        }
    }
    if (!current.empty() || lines.empty()) {
        lines.push_back(current);
    }
    if (lines.empty()) {
        lines.emplace_back();
    }
    return lines;
}

std::string read_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ToolError("LOAD FAIL");
    }
    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void save_editor_lines(const fs::path& path, const std::vector<std::string>& lines) {
    const fs::path temporary = path.parent_path() /
        ("." + path.filename().string() + ".actedit-" + std::to_string(::getpid()));
    std::error_code error;
    const fs::perms original_permissions = fs::status(path, error).permissions();
    error.clear();
    try {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw ToolError("SAVE FAIL");
        }
        for (const std::string& line : lines) {
            output.write(line.data(), static_cast<std::streamsize>(line.size()));
            output.put('\n');
        }
        output.close();
        if (!output) {
            throw ToolError("SAVE FAIL");
        }
        if (original_permissions != fs::perms::unknown) {
            fs::permissions(temporary, original_permissions, error);
            error.clear();
        }
        fs::rename(temporary, path);
    } catch (...) {
        fs::remove(temporary, error);
        throw;
    }
}

void write_all(int descriptor, std::string_view text) {
    std::size_t offset = 0;
    while (offset < text.size()) {
        const ssize_t written = ::write(
            descriptor,
            text.data() + offset,
            text.size() - offset);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw ToolError("TERMINAL WRITE: " + std::string(std::strerror(errno)));
        }
        offset += static_cast<std::size_t>(written);
    }
}

class TerminalSession {
public:
    TerminalSession() {
        if (::isatty(STDIN_FILENO) == 0 || ::isatty(STDOUT_FILENO) == 0) {
            throw ToolError("ACTEDIT TUI REQUIRES A TERMINAL");
        }
        if (::tcgetattr(STDIN_FILENO, &original_) != 0) {
            throw ToolError("TERMINAL SETUP: " + std::string(std::strerror(errno)));
        }
        resume();
    }

    TerminalSession(const TerminalSession&) = delete;
    TerminalSession& operator=(const TerminalSession&) = delete;

    ~TerminalSession() {
        suspend_noexcept();
    }

    void suspend() {
        if (!active_) {
            return;
        }
        write_all(
            STDOUT_FILENO,
            "\x1b[0m\x1b[?1006l\x1b[?1002l\x1b[0 q\x1b[?25h\x1b[?1049l");
        if (::tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_) != 0) {
            throw ToolError("TERMINAL SUSPEND: " + std::string(std::strerror(errno)));
        }
        active_ = false;
    }

    void resume() {
        if (active_) {
            return;
        }
        termios raw = original_;
        raw.c_iflag &= static_cast<tcflag_t>(~(BRKINT | ICRNL | INPCK | ISTRIP | IXON));
        raw.c_oflag &= static_cast<tcflag_t>(~OPOST);
        raw.c_cflag |= CS8;
        raw.c_lflag &= static_cast<tcflag_t>(~(ECHO | ICANON | IEXTEN | ISIG));
        raw.c_cc[VMIN] = 1;
        raw.c_cc[VTIME] = 0;
        if (::tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) != 0) {
            throw ToolError("TERMINAL SETUP: " + std::string(std::strerror(errno)));
        }
        active_ = true;
        try {
            write_all(
                STDOUT_FILENO,
                "\x1b[?1049h\x1b[1 q\x1b[?25l\x1b[?1002h\x1b[?1006h\x1b[2J\x1b[H");
        } catch (...) {
            (void)::tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_);
            active_ = false;
            throw;
        }
    }

private:
    void suspend_noexcept() noexcept {
        if (!active_) {
            return;
        }
        const char restore[] =
            "\x1b[0m\x1b[?1006l\x1b[?1002l\x1b[0 q\x1b[?25h\x1b[?1049l";
        const ssize_t write_status =
            ::write(STDOUT_FILENO, restore, sizeof(restore) - 1);
        (void)write_status;
        (void)::tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_);
        active_ = false;
    }

    termios original_{};
    bool active_ = false;
};

struct TerminalSize {
    std::size_t rows = 24;
    std::size_t columns = 80;
};

TerminalSize terminal_size() {
    winsize raw{};
    if (::ioctl(STDOUT_FILENO, TIOCGWINSZ, &raw) == 0) {
        return TerminalSize{
            std::max<std::size_t>(8, raw.ws_row),
            std::max<std::size_t>(40, raw.ws_col),
        };
    }
    return {};
}

enum class KeyKind {
    Character,
    Up,
    Down,
    Left,
    Right,
    Home,
    End,
    PageUp,
    PageDown,
    Delete,
    Backspace,
    Enter,
    Tab,
    Save,
    Quit,
    F1,
    F2,
    F3,
    F4,
    F5,
    F6,
    F7,
    F8,
    SelectAll,
    Mark,
    Copy,
    Cut,
    Paste,
    Back,
    Forward,
    Mouse,
    Escape,
    Unknown,
};

struct Key {
    KeyKind kind = KeyKind::Unknown;
    char character = '\0';
    std::size_t mouse_x = 0;
    std::size_t mouse_y = 0;
    int mouse_button = 0;
    bool mouse_release = false;
};

char read_byte() {
    char value = '\0';
    while (true) {
        const ssize_t count = ::read(STDIN_FILENO, &value, 1);
        if (count == 1) {
            return value;
        }
        if (count == 0) {
            return '\x11';
        }
        if (errno != EINTR) {
            throw ToolError("TERMINAL READ: " + std::string(std::strerror(errno)));
        }
    }
}

bool input_ready(int timeout_ms) {
    pollfd descriptor{};
    descriptor.fd = STDIN_FILENO;
    descriptor.events = POLLIN;
    while (true) {
        const int status = ::poll(&descriptor, 1, timeout_ms);
        if (status >= 0) {
            return status > 0 && (descriptor.revents & POLLIN) != 0;
        }
        if (errno != EINTR) {
            throw ToolError("TERMINAL POLL: " + std::string(std::strerror(errno)));
        }
    }
}

Key escape_key(std::string_view sequence) {
    if (sequence == "OP" || sequence == "[11~" || sequence == "[[A") {
        return {KeyKind::F1, '\0'};
    }
    if (sequence == "OQ" || sequence == "[12~" || sequence == "[[B") {
        return {KeyKind::F2, '\0'};
    }
    if (sequence == "OR" || sequence == "[13~" || sequence == "[[C") {
        return {KeyKind::F3, '\0'};
    }
    if (sequence == "OS" || sequence == "[14~" || sequence == "[[D") {
        return {KeyKind::F4, '\0'};
    }
    if (sequence == "[15~" || sequence == "[[E") {
        return {KeyKind::F5, '\0'};
    }
    if (sequence == "[17~") return {KeyKind::F6, '\0'};
    if (sequence == "[18~") return {KeyKind::F7, '\0'};
    if (sequence == "[19~") return {KeyKind::F8, '\0'};
    if (sequence == "[1;3D" || sequence == "[3D") {
        return {KeyKind::Back, '\0'};
    }
    if (sequence == "[1;3C" || sequence == "[3C") {
        return {KeyKind::Forward, '\0'};
    }
    if (sequence.rfind("[<", 0) == 0) {
        int button = 0;
        int x = 0;
        int y = 0;
        char ending = '\0';
        const std::string encoded(sequence);
        if (std::sscanf(encoded.c_str(), "[<%d;%d;%d%c", &button, &x, &y, &ending) == 4 &&
            x > 0 && y > 0 && (ending == 'M' || ending == 'm')) {
            Key key{KeyKind::Mouse, '\0'};
            key.mouse_x = static_cast<std::size_t>(x);
            key.mouse_y = static_cast<std::size_t>(y);
            key.mouse_button = button;
            key.mouse_release = ending == 'm';
            return key;
        }
    }
    if (sequence == "[A" || sequence == "OA") return {KeyKind::Up, '\0'};
    if (sequence == "[B" || sequence == "OB") return {KeyKind::Down, '\0'};
    if (sequence == "[C" || sequence == "OC") return {KeyKind::Right, '\0'};
    if (sequence == "[D" || sequence == "OD") return {KeyKind::Left, '\0'};
    if (sequence == "[H" || sequence == "OH" || sequence == "[1~" ||
        sequence == "[7~") {
        return {KeyKind::Home, '\0'};
    }
    if (sequence == "[F" || sequence == "OF" || sequence == "[4~" ||
        sequence == "[8~") {
        return {KeyKind::End, '\0'};
    }
    if (sequence == "[3~") return {KeyKind::Delete, '\0'};
    if (sequence == "[5~") return {KeyKind::PageUp, '\0'};
    if (sequence == "[6~") return {KeyKind::PageDown, '\0'};
    return {KeyKind::Unknown, '\0'};
}

Key read_key() {
    const unsigned char value = static_cast<unsigned char>(read_byte());
    if (value == 0x1b) {
        if (!input_ready(35)) {
            return {KeyKind::Escape, '\0'};
        }
        std::string sequence;
        while (sequence.size() < 32 && input_ready(sequence.empty() ? 35 : 5)) {
            sequence.push_back(read_byte());
            const char last = sequence.back();
            if (last == '~' || last == 'M' || last == 'm' ||
                (std::isalpha(static_cast<unsigned char>(last)) != 0 &&
                 sequence.size() >= 2)) {
                break;
            }
        }
        return escape_key(sequence);
    }
    if (value == 0x01) return {KeyKind::SelectAll, '\0'};
    if (value == 0x02) return {KeyKind::Mark, '\0'};
    if (value == 0x03) return {KeyKind::Copy, '\0'};
    if (value == 0x13) return {KeyKind::Save, '\0'};
    if (value == 0x11) return {KeyKind::Quit, '\0'};
    if (value == 0x16) return {KeyKind::Paste, '\0'};
    if (value == 0x18) return {KeyKind::Cut, '\0'};
    if (value == 0x7f || value == 0x08) return {KeyKind::Backspace, '\0'};
    if (value == '\r' || value == '\n') return {KeyKind::Enter, '\0'};
    if (value == '\t') return {KeyKind::Tab, '\0'};
    if (value >= 32 && value <= 126) {
        return {KeyKind::Character, static_cast<char>(value)};
    }
    return {KeyKind::Unknown, '\0'};
}

std::string clipped(std::string text, std::size_t width) {
    text = sanitize_visible(text);
    if (text.size() > width) {
        text.resize(width);
    } else if (text.size() < width) {
        text.append(width - text.size(), ' ');
    }
    return text;
}

std::string cursor_position(std::size_t row, std::size_t column) {
    return "\x1b[" + std::to_string(row) + ";" + std::to_string(column) + "H";
}

std::optional<std::string> token_at_cursor(
    std::string_view line,
    std::size_t cursor) {
    if (line.empty()) {
        return std::nullopt;
    }
    std::size_t position = std::min(cursor, line.size());
    if (position == line.size() || !is_identifier_char(line[position])) {
        if (position == 0 || !is_identifier_char(line[position - 1])) {
            return std::nullopt;
        }
        --position;
    }
    std::size_t begin = position;
    while (begin > 0 && is_identifier_char(line[begin - 1])) {
        --begin;
    }
    std::size_t end = position + 1;
    while (end < line.size() && is_identifier_char(line[end])) {
        ++end;
    }
    if (!is_identifier_start(line[begin])) {
        return std::nullopt;
    }
    return std::string(line.substr(begin, end - begin));
}

HelpTopic editor_help_topic(std::string_view token) {
    return HelpTopic{
        std::string(token),
        "editor",
        "F1 contextual help",
        "Move the cursor onto an Action keyword, type, constant, or builtin and press F1.",
        "Arrow keys move; Home/End and Page Up/Page Down navigate; Enter, Backspace, Delete, Tab, and printable keys edit. Ctrl-B marks a block; Ctrl-C, Ctrl-X, and Ctrl-V copy, cut, and paste. Ctrl-S saves. Ctrl-Q quits; press it twice to discard unsaved changes. Escape closes help or clears a selection.",
        {},
        {},
        "Help text is read from the external action-help.sqlite3 catalog.",
    };
}

HelpTopic editor_command_help_topic() {
    return HelpTopic{
        "ACTEDIT KEYS",
        "editor",
        "F2 - editor command help",
        "Keyboard and mouse commands available in ACTEDIT's built-in editor.",
        "Move: Arrow keys move the cursor; Home/End move across a line; Page Up/Page Down move a screen.\n"
        "Edit: Printable keys insert; Enter splits a line; Backspace/Delete remove text; Tab inserts four spaces.\n"
        "Block: Ctrl-B sets or clears the selection anchor; move the cursor to extend it. Ctrl-A selects the entire buffer. Ctrl-C copies, Ctrl-X cuts, and Ctrl-V pastes. Backspace/Delete or typed text replaces a selected block. Escape clears it. The clipboard remains available for the editor session.\n"
        "File: Ctrl-S saves atomically. Ctrl-Q quits; with unsaved changes, press Ctrl-Q twice to discard them.\n"
        "Help: F1 explains the Action keyword or builtin under the cursor. F2 opens this command reference.\n"
        "Reference: F3 browses the complete language catalog. F4 browses libraries and their features.\n"
        "Code: F5 opens a definition. F7 lists references; Enter opens the selected reference.\n"
        "Format: F6 applies ACTSPC indentation and spacing to the current in-memory buffer; Ctrl-S saves the result.\n"
        "Graphics: F8 launches ACTSPRITE or ACTBITMAP for the RESOURCE declaration on the cursor line.\n"
        "History: Alt-Left and Alt-Right move backward and forward through visited definitions.\n"
        "Mouse: Click positions the cursor; left-button drag selects a block. Ctrl-click opens the definition under the pointer.\n"
        "Popups: Up/Down and Page Up/Page Down scroll. Escape closes a popup.",
        {},
        {},
        "Plain mode is uncolored; explicit tui mode enables syntax highlighting.",
    };
}

HelpTopic language_overview_topic() {
    return HelpTopic{
        "ACTION LANGUAGE",
        "reference",
        "F3 - complete language reference",
        "Browse every cataloged Action keyword, type, and core builtin, with signatures, explanations, examples, and target notes.",
        "Programs contain module declarations and PROC or typed FUNC routines. BYTE, CHAR, CARD, INT, and REAL values can be scalars, arrays, pointers, constants, or packed-record fields.\n"
        "Expressions support arithmetic, comparisons, bit operations, shifts, short-circuit conditions, function calls, address-of, and pointer dereference.\n"
        "Control flow includes IF/ELSEIF/ELSE/FI, FOR/TO/STEP, WHILE, DO/UNTIL/OD, EXIT, and RETURN.\n"
        "INCLUDE and DEFINE provide source composition. Inline code, fixed-address routines, resident overlays, REU arrays, strings, recursive routines, and link-selected runtime helpers cover the target-specific surface.\n"
        "Choose a category, then a feature, and press Enter for its detailed page. Escape returns to the previous list.",
        "MODULE demo\nBYTE ARRAY message=\"HELLO\"\nPROC main()\n  CARD i\n  FOR i=1 TO 3\n  DO\n    PrintE(message)\n  OD\n  RETURN\nENDPROC",
        {},
        "The reference describes the active Idun/Linux compiler and direct C64 PRG runtime, including documented target limits.",
    };
}

std::vector<std::string> popup_lines(const HelpTopic& topic, std::size_t width) {
    std::vector<std::string> result;
    result.push_back(topic.token + " [" + topic.kind + "]" +
        (topic.library.empty() ? "" : " - " + topic.library));
    result.push_back(topic.signature);
    result.emplace_back();
    const auto append_wrapped = [&](std::string_view text) {
        const std::vector<std::string> wrapped = wrap_text(text, width);
        result.insert(result.end(), wrapped.begin(), wrapped.end());
    };
    append_wrapped(topic.summary);
    if (!topic.details.empty()) {
        result.emplace_back();
        append_wrapped(topic.details);
    }
    if (!topic.example.empty()) {
        result.emplace_back();
        result.push_back("Example:");
        std::istringstream input(topic.example);
        std::string line;
        while (std::getline(input, line)) {
            result.push_back("  " + line);
        }
    }
    if (!topic.target_notes.empty()) {
        result.emplace_back();
        result.push_back("Target notes:");
        append_wrapped(topic.target_notes);
    }
    return result;
}

enum class ReferenceEntryKind {
    Topic,
    LanguageKind,
    Library,
};

struct ReferenceEntry {
    std::string label;
    std::string summary;
    ReferenceEntryKind kind = ReferenceEntryKind::Topic;
    std::string value;
    std::optional<HelpTopic> topic;
};

struct ReferencePage {
    std::string title;
    std::vector<ReferenceEntry> entries;
    std::size_t selected = 0;
    std::size_t scroll = 0;
};

struct ReferenceBrowser {
    enum class Root {
        Language,
        Libraries,
    };

    Root root = Root::Language;
    std::vector<ReferencePage> pages;
};

class Editor {
public:
    Editor(
        fs::path path,
        std::string module,
        fs::path project_root,
        HelpCatalog& catalog,
        bool syntax_highlighting)
        : path_(std::move(path)),
          project_root_(fs::weakly_canonical(std::move(project_root))),
          module_(std::move(module)),
          catalog_(catalog),
          syntax_highlighting_(syntax_highlighting),
          lines_(editor_lines_from_text(read_file(path_))) {
        path_ = fs::weakly_canonical(path_);
    }

    int run() {
        TerminalSession terminal;
        terminal_ = &terminal;
        bool running = true;
        while (running) {
            render();
            const Key key = read_key();
            if (popup_ || references_popup_) {
                handle_popup_key(key);
                continue;
            }
            if (reference_browser_) {
                handle_reference_key(key);
                continue;
            }
            running = handle_editor_key(key);
        }
        terminal_ = nullptr;
        return 0;
    }

private:
    struct TextPoint {
        std::size_t row = 0;
        std::size_t column = 0;
    };

    static bool point_before(const TextPoint& left, const TextPoint& right) {
        return left.row < right.row ||
            (left.row == right.row && left.column < right.column);
    }

    std::optional<std::pair<TextPoint, TextPoint>> selection_bounds() const {
        if (!selection_anchor_) {
            return std::nullopt;
        }
        const TextPoint cursor{row_, column_};
        if (selection_anchor_->row == cursor.row &&
            selection_anchor_->column == cursor.column) {
            return std::nullopt;
        }
        if (point_before(cursor, *selection_anchor_)) {
            return std::pair<TextPoint, TextPoint>{cursor, *selection_anchor_};
        }
        return std::pair<TextPoint, TextPoint>{*selection_anchor_, cursor};
    }

    std::optional<std::pair<std::size_t, std::size_t>> selection_columns(
        std::size_t row) const {
        const auto bounds = selection_bounds();
        if (!bounds || row < bounds->first.row || row > bounds->second.row) {
            return std::nullopt;
        }
        const std::size_t begin = row == bounds->first.row
            ? bounds->first.column
            : 0;
        const std::size_t end = row == bounds->second.row
            ? bounds->second.column
            : lines_[row].size();
        if (begin >= end) {
            return std::nullopt;
        }
        return std::pair<std::size_t, std::size_t>{begin, end};
    }

    std::string editor_window(
        std::size_t source_row,
        std::size_t left,
        std::size_t width) const {
        const std::string& line = lines_[source_row];
        const auto selected = selection_columns(source_row);
        if (!selected) {
            if (syntax_highlighting_) {
                return highlighted_window(line, left, width, catalog_);
            }
            if (left < line.size()) {
                return sanitize_visible(
                    std::string_view(line).substr(left, width));
            }
            return {};
        }

        const std::size_t visible_end = std::min(line.size(), left + width);
        if (left >= visible_end) {
            return {};
        }
        const std::size_t selected_begin =
            std::clamp(selected->first, left, visible_end);
        const std::size_t selected_end =
            std::clamp(selected->second, left, visible_end);
        std::string output;
        if (selected_begin > left) {
            output += sanitize_visible(
                std::string_view(line).substr(left, selected_begin - left));
        }
        if (selected_end > selected_begin) {
            output += "\x1b[7m";
            output += sanitize_visible(std::string_view(line).substr(
                selected_begin, selected_end - selected_begin));
            output += "\x1b[0m";
        }
        if (visible_end > selected_end) {
            output += sanitize_visible(
                std::string_view(line).substr(selected_end, visible_end - selected_end));
        }
        return output;
    }

    std::size_t gutter_width() const {
        return std::max<std::size_t>(5, std::to_string(lines_.size()).size() + 2);
    }

    void adjust_view(const TerminalSize& size) {
        const std::size_t content_rows = size.rows - 2;
        if (row_ < top_) {
            top_ = row_;
        } else if (row_ >= top_ + content_rows) {
            top_ = row_ - content_rows + 1;
        }
        const std::size_t gutter = gutter_width();
        const std::size_t content_columns =
            size.columns > gutter ? size.columns - gutter : 1;
        if (column_ < left_) {
            left_ = column_;
        } else if (column_ >= left_ + content_columns) {
            left_ = column_ - content_columns + 1;
        }
    }

    void render() {
        const TerminalSize size = terminal_size();
        adjust_view(size);
        const std::size_t gutter = gutter_width();
        const std::size_t content_columns = size.columns - std::min(size.columns, gutter);
        std::string screen = "\x1b[?25l\x1b[H";
        std::string title = " ACTEDIT " +
            std::string(syntax_highlighting_ ? "TUI " : "PLAIN ") + module_ +
            "  " + path_.generic_string();
        if (dirty_) {
            title += " *";
        }
        screen += "\x1b[7m" + clipped(title, size.columns) + "\x1b[0m";

        for (std::size_t viewport_row = 0; viewport_row < size.rows - 2;
             ++viewport_row) {
            screen += "\r\n";
            const std::size_t source_row = top_ + viewport_row;
            if (source_row >= lines_.size()) {
                screen += "\x1b[K";
                continue;
            }
            const std::string number = std::to_string(source_row + 1);
            screen += "\x1b[2m";
            screen.append(gutter - number.size() - 1, ' ');
            screen += number + " \x1b[0m";
            screen += editor_window(source_row, left_, content_columns);
            screen += "\x1b[K";
        }

        std::string status = status_.empty()
            ? " F1 help F2 keys F3 lang F4 libs F5 def F6 fmt F7 refs F8 asset"
            : " " + status_;
        const std::string position =
            "  " + std::to_string(row_ + 1) + ":" + std::to_string(column_ + 1) + " ";
        if (position.size() < size.columns &&
            status.size() + position.size() <= size.columns) {
            status.append(size.columns - status.size() - position.size(), ' ');
            status += position;
        }
        screen += "\r\n\x1b[7m" + clipped(status, size.columns) + "\x1b[0m";

        if (reference_browser_) {
            render_reference_browser(screen, size);
        }
        if (references_popup_) {
            render_references_popup(screen, size);
        } else if (popup_) {
            render_popup(screen, size);
        } else if (!reference_browser_) {
            const std::size_t screen_row = row_ - top_ + 2;
            const std::size_t screen_column = gutter + (column_ - left_) + 1;
            const std::string cursor_cell = column_ < lines_[row_].size()
                ? sanitize_visible(std::string_view(lines_[row_]).substr(column_, 1))
                : " ";
            screen += cursor_position(screen_row, screen_column) +
                "\x1b[1;7m" + cursor_cell + "\x1b[0m" +
                cursor_position(screen_row, screen_column) +
                "\x1b[1 q\x1b[?25h";
        }
        write_all(STDOUT_FILENO, screen);
    }

    void render_reference_browser(std::string& screen, const TerminalSize& size) {
        const std::size_t box_width = std::min<std::size_t>(size.columns - 2, 90);
        const std::size_t box_height = std::min<std::size_t>(size.rows - 2, 22);
        const std::size_t top = (size.rows - box_height) / 2 + 1;
        const std::size_t left = (size.columns - box_width) / 2 + 1;
        const std::size_t inside_width = box_width - 2;
        const std::size_t body_height = box_height - 4;
        ReferencePage& page = reference_browser_->pages.back();
        if (page.selected < page.scroll) {
            page.scroll = page.selected;
        } else if (page.selected >= page.scroll + body_height) {
            page.scroll = page.selected - body_height + 1;
        }

        screen += cursor_position(top, left) + "+" +
            std::string(box_width - 2, '-') + "+";
        screen += cursor_position(top + 1, left) + "|\x1b[7m" +
            clipped(" " + page.title, inside_width) + "\x1b[0m|";
        for (std::size_t row = 0; row < body_height; ++row) {
            const std::size_t item = page.scroll + row;
            std::string line;
            if (item < page.entries.size()) {
                const ReferenceEntry& entry = page.entries[item];
                line = " " + entry.label;
                if (!entry.summary.empty()) {
                    line += " - " + entry.summary;
                }
            }
            screen += cursor_position(top + row + 2, left) + "|";
            if (item == page.selected && item < page.entries.size()) {
                screen += "\x1b[7m" + clipped(line, inside_width) + "\x1b[0m";
            } else {
                screen += clipped(line, inside_width);
            }
            screen += "|";
        }
        const std::string footer = " Enter opens  Esc back/close  Up/Down/Page scroll ";
        screen += cursor_position(top + box_height - 2, left) + "|\x1b[7m" +
            clipped(footer, inside_width) + "\x1b[0m|";
        screen += cursor_position(top + box_height - 1, left) + "+" +
            std::string(box_width - 2, '-') + "+";
    }

    void render_popup(std::string& screen, const TerminalSize& size) {
        const std::size_t box_width = std::min<std::size_t>(size.columns - 2, 76);
        const std::size_t box_height = std::min<std::size_t>(size.rows - 2, 20);
        const std::size_t top = (size.rows - box_height) / 2 + 1;
        const std::size_t left = (size.columns - box_width) / 2 + 1;
        const std::size_t inside_width = box_width - 2;
        const std::size_t body_height = box_height - 3;
        const std::vector<std::string> content = popup_lines(*popup_, inside_width - 2);
        if (popup_scroll_ > content.size()) {
            popup_scroll_ = content.size();
        }

        screen += cursor_position(top, left) + "+" +
            std::string(box_width - 2, '-') + "+";
        for (std::size_t row = 0; row < body_height; ++row) {
            const std::size_t content_row = popup_scroll_ + row;
            const std::string line = content_row < content.size()
                ? " " + content[content_row]
                : "";
            screen += cursor_position(top + row + 1, left) + "|" +
                clipped(line, inside_width) + "|";
        }
        const std::string footer = " Esc/F1/F2 close  Up/Down scroll ";
        screen += cursor_position(top + box_height - 2, left) + "|\x1b[7m" +
            clipped(footer, inside_width) + "\x1b[0m|";
        screen += cursor_position(top + box_height - 1, left) + "+" +
            std::string(box_width - 2, '-') + "+";
    }

    void render_references_popup(std::string& screen, const TerminalSize& size) {
        const std::size_t box_width = std::min<std::size_t>(size.columns - 2, 86);
        const std::size_t box_height = std::min<std::size_t>(size.rows - 2, 20);
        const std::size_t top = (size.rows - box_height) / 2 + 1;
        const std::size_t left = (size.columns - box_width) / 2 + 1;
        const std::size_t inside_width = box_width - 2;
        const std::size_t body_height = box_height - 3;
        auto& popup = *references_popup_;
        if (popup.selected < popup.scroll) {
            popup.scroll = popup.selected;
        } else if (popup.selected >= popup.scroll + body_height) {
            popup.scroll = popup.selected - body_height + 1;
        }

        screen += cursor_position(top, left) + "+" +
            std::string(box_width - 2, '-') + "+";
        for (std::size_t row = 0; row < body_height; ++row) {
            const std::size_t item = popup.scroll + row;
            std::string line;
            if (item < popup.locations.size()) {
                const CodeMapLocation& location = popup.locations[item];
                line = " " + location.path + ":" + std::to_string(location.line) +
                    ":" + std::to_string(location.column);
                if (!location.caller.empty()) {
                    line += "  in " + location.caller;
                }
            }
            screen += cursor_position(top + row + 1, left) + "|";
            if (item == popup.selected && item < popup.locations.size()) {
                screen += "\x1b[7m" + clipped(line, inside_width) + "\x1b[0m";
            } else {
                screen += clipped(line, inside_width);
            }
            screen += "|";
        }
        const std::string footer = " References to " + popup.token + " (" +
            std::to_string(popup.locations.size()) + ")  Enter opens  Esc closes ";
        screen += cursor_position(top + box_height - 2, left) + "|\x1b[7m" +
            clipped(footer, inside_width) + "\x1b[0m|";
        screen += cursor_position(top + box_height - 1, left) + "+" +
            std::string(box_width - 2, '-') + "+";
    }

    void handle_popup_key(const Key& key) {
        if (key.kind == KeyKind::F3) {
            popup_.reset();
            references_popup_.reset();
            show_language_reference();
            return;
        }
        if (key.kind == KeyKind::F4) {
            popup_.reset();
            references_popup_.reset();
            show_library_reference();
            return;
        }
        if (references_popup_) {
            if (key.kind == KeyKind::Escape || key.kind == KeyKind::F5 ||
                key.kind == KeyKind::F7 || key.kind == KeyKind::Quit) {
                references_popup_.reset();
            } else if (key.kind == KeyKind::Up && references_popup_->selected > 0) {
                --references_popup_->selected;
            } else if (key.kind == KeyKind::Down &&
                       references_popup_->selected + 1 <
                           references_popup_->locations.size()) {
                ++references_popup_->selected;
            } else if (key.kind == KeyKind::PageUp) {
                const std::size_t page = std::max<std::size_t>(1, terminal_size().rows - 5);
                references_popup_->selected = references_popup_->selected > page
                    ? references_popup_->selected - page
                    : 0;
            } else if (key.kind == KeyKind::PageDown &&
                       !references_popup_->locations.empty()) {
                const std::size_t page = std::max<std::size_t>(1, terminal_size().rows - 5);
                references_popup_->selected = std::min(
                    references_popup_->locations.size() - 1,
                    references_popup_->selected + page);
            } else if (key.kind == KeyKind::Enter &&
                       !references_popup_->locations.empty()) {
                const CodeMapLocation location =
                    references_popup_->locations[references_popup_->selected];
                references_popup_.reset();
                navigate_to(location, true);
            }
            return;
        }
        const TerminalSize size = terminal_size();
        const std::size_t page = std::max<std::size_t>(1, std::min<std::size_t>(18, size.rows - 5));
        if (key.kind == KeyKind::Escape || key.kind == KeyKind::F1 ||
            key.kind == KeyKind::F2 ||
            key.kind == KeyKind::Enter || key.kind == KeyKind::Quit) {
            popup_.reset();
            popup_scroll_ = 0;
        } else if (key.kind == KeyKind::Up && popup_scroll_ > 0) {
            --popup_scroll_;
        } else if (key.kind == KeyKind::Down) {
            ++popup_scroll_;
        } else if (key.kind == KeyKind::PageUp) {
            popup_scroll_ = popup_scroll_ > page ? popup_scroll_ - page : 0;
        } else if (key.kind == KeyKind::PageDown) {
            popup_scroll_ += page;
        }
    }

    void handle_reference_key(const Key& key) {
        if (key.kind == KeyKind::F3) {
            show_language_reference();
            return;
        }
        if (key.kind == KeyKind::F4) {
            show_library_reference();
            return;
        }
        ReferencePage& page = reference_browser_->pages.back();
        if (key.kind == KeyKind::Escape || key.kind == KeyKind::Backspace ||
            key.kind == KeyKind::Quit) {
            if (reference_browser_->pages.size() > 1) {
                reference_browser_->pages.pop_back();
            } else {
                reference_browser_.reset();
            }
            return;
        }
        if (page.entries.empty()) {
            return;
        }
        if (key.kind == KeyKind::Up && page.selected > 0) {
            --page.selected;
        } else if (key.kind == KeyKind::Down &&
                   page.selected + 1 < page.entries.size()) {
            ++page.selected;
        } else if (key.kind == KeyKind::Home) {
            page.selected = 0;
        } else if (key.kind == KeyKind::End) {
            page.selected = page.entries.size() - 1;
        } else if (key.kind == KeyKind::PageUp) {
            const std::size_t amount =
                std::max<std::size_t>(1, terminal_size().rows - 6);
            page.selected = page.selected > amount ? page.selected - amount : 0;
        } else if (key.kind == KeyKind::PageDown) {
            const std::size_t amount =
                std::max<std::size_t>(1, terminal_size().rows - 6);
            page.selected = std::min(
                page.entries.size() - 1, page.selected + amount);
        } else if (key.kind == KeyKind::Enter) {
            const ReferenceEntry entry = page.entries[page.selected];
            if (entry.kind == ReferenceEntryKind::Topic && entry.topic) {
                popup_ = *entry.topic;
                popup_scroll_ = 0;
            } else if (entry.kind == ReferenceEntryKind::LanguageKind) {
                reference_browser_->pages.push_back(
                    language_kind_page(entry.value));
            } else if (entry.kind == ReferenceEntryKind::Library) {
                reference_browser_->pages.push_back(
                    library_topic_page(entry.value));
            }
        }
    }

    bool handle_editor_key(const Key& key) {
        switch (key.kind) {
            case KeyKind::Up:
                if (row_ > 0) {
                    --row_;
                    column_ = std::min(column_, lines_[row_].size());
                }
                break;
            case KeyKind::Down:
                if (row_ + 1 < lines_.size()) {
                    ++row_;
                    column_ = std::min(column_, lines_[row_].size());
                }
                break;
            case KeyKind::Left:
                if (column_ > 0) {
                    --column_;
                } else if (row_ > 0) {
                    --row_;
                    column_ = lines_[row_].size();
                }
                break;
            case KeyKind::Right:
                if (column_ < lines_[row_].size()) {
                    ++column_;
                } else if (row_ + 1 < lines_.size()) {
                    ++row_;
                    column_ = 0;
                }
                break;
            case KeyKind::Home:
                column_ = 0;
                break;
            case KeyKind::End:
                column_ = lines_[row_].size();
                break;
            case KeyKind::PageUp: {
                const std::size_t page = terminal_size().rows - 2;
                row_ = row_ > page ? row_ - page : 0;
                column_ = std::min(column_, lines_[row_].size());
                break;
            }
            case KeyKind::PageDown: {
                const std::size_t page = terminal_size().rows - 2;
                row_ = std::min(lines_.size() - 1, row_ + page);
                column_ = std::min(column_, lines_[row_].size());
                break;
            }
            case KeyKind::Character:
                delete_selection();
                lines_[row_].insert(lines_[row_].begin() +
                    static_cast<std::ptrdiff_t>(column_), key.character);
                ++column_;
                mark_dirty();
                break;
            case KeyKind::Tab:
                delete_selection();
                lines_[row_].insert(column_, 4, ' ');
                column_ += 4;
                mark_dirty();
                break;
            case KeyKind::Enter: {
                delete_selection();
                std::string remainder = lines_[row_].substr(column_);
                lines_[row_].resize(column_);
                lines_.insert(
                    lines_.begin() + static_cast<std::ptrdiff_t>(row_ + 1),
                    std::move(remainder));
                ++row_;
                column_ = 0;
                mark_dirty();
                break;
            }
            case KeyKind::Backspace:
                if (delete_selection()) {
                    break;
                }
                if (column_ > 0) {
                    lines_[row_].erase(column_ - 1, 1);
                    --column_;
                    mark_dirty();
                } else if (row_ > 0) {
                    const std::size_t previous_size = lines_[row_ - 1].size();
                    lines_[row_ - 1] += lines_[row_];
                    lines_.erase(lines_.begin() + static_cast<std::ptrdiff_t>(row_));
                    --row_;
                    column_ = previous_size;
                    mark_dirty();
                }
                break;
            case KeyKind::Delete:
                if (delete_selection()) {
                    break;
                }
                if (column_ < lines_[row_].size()) {
                    lines_[row_].erase(column_, 1);
                    mark_dirty();
                } else if (row_ + 1 < lines_.size()) {
                    lines_[row_] += lines_[row_ + 1];
                    lines_.erase(lines_.begin() + static_cast<std::ptrdiff_t>(row_ + 1));
                    mark_dirty();
                }
                break;
            case KeyKind::SelectAll:
                select_all();
                break;
            case KeyKind::Mark:
                toggle_mark();
                break;
            case KeyKind::Copy:
                copy_selection();
                break;
            case KeyKind::Cut:
                cut_selection();
                break;
            case KeyKind::Paste:
                paste_clipboard();
                break;
            case KeyKind::Save:
                try {
                    save_editor_lines(path_, lines_);
                    dirty_ = false;
                    quit_armed_ = false;
                    status_ = "Saved " + path_.generic_string();
                } catch (const std::exception& error) {
                    status_ = error.what();
                }
                break;
            case KeyKind::Quit:
                if (!dirty_ || quit_armed_) {
                    return false;
                }
                quit_armed_ = true;
                status_ = "Unsaved changes; press Ctrl-Q again to discard";
                break;
            case KeyKind::F1:
                show_help();
                break;
            case KeyKind::F2:
                show_editor_command_help();
                break;
            case KeyKind::F3:
                show_language_reference();
                break;
            case KeyKind::F4:
                show_library_reference();
                break;
            case KeyKind::F5:
                go_to_definition();
                break;
            case KeyKind::F6:
                format_buffer();
                break;
            case KeyKind::F7:
                show_references();
                break;
            case KeyKind::F8:
                launch_graphics_editor();
                break;
            case KeyKind::Back:
                navigate_back();
                break;
            case KeyKind::Forward:
                navigate_forward();
                break;
            case KeyKind::Mouse:
                handle_mouse(key);
                break;
            case KeyKind::Escape:
                if (selection_anchor_) {
                    selection_anchor_.reset();
                    status_ = "Selection cleared";
                } else {
                    status_.clear();
                }
                quit_armed_ = false;
                break;
            case KeyKind::Unknown:
                break;
        }
        return true;
    }

    void mark_dirty() {
        dirty_ = true;
        quit_armed_ = false;
        status_.clear();
    }

    std::optional<std::string> selected_text() const {
        const auto bounds = selection_bounds();
        if (!bounds) {
            return std::nullopt;
        }
        if (bounds->first.row == bounds->second.row) {
            return lines_[bounds->first.row].substr(
                bounds->first.column,
                bounds->second.column - bounds->first.column);
        }
        std::string text =
            lines_[bounds->first.row].substr(bounds->first.column) + "\n";
        for (std::size_t row = bounds->first.row + 1;
             row < bounds->second.row;
             ++row) {
            text += lines_[row];
            text.push_back('\n');
        }
        text += lines_[bounds->second.row].substr(0, bounds->second.column);
        return text;
    }

    bool delete_selection() {
        const auto bounds = selection_bounds();
        if (!bounds) {
            return false;
        }
        if (bounds->first.row == bounds->second.row) {
            lines_[bounds->first.row].erase(
                bounds->first.column,
                bounds->second.column - bounds->first.column);
        } else {
            lines_[bounds->first.row] =
                lines_[bounds->first.row].substr(0, bounds->first.column) +
                lines_[bounds->second.row].substr(bounds->second.column);
            lines_.erase(
                lines_.begin() +
                    static_cast<std::ptrdiff_t>(bounds->first.row + 1),
                lines_.begin() +
                    static_cast<std::ptrdiff_t>(bounds->second.row + 1));
        }
        row_ = bounds->first.row;
        column_ = bounds->first.column;
        selection_anchor_.reset();
        mouse_selecting_ = false;
        mark_dirty();
        return true;
    }

    void toggle_mark() {
        if (selection_anchor_) {
            selection_anchor_.reset();
            status_ = "Block mark cleared";
            return;
        }
        selection_anchor_ = TextPoint{row_, column_};
        status_ = "Block mark set; move the cursor to extend the selection";
    }

    void select_all() {
        selection_anchor_ = TextPoint{0, 0};
        row_ = lines_.size() - 1;
        column_ = lines_.back().size();
        status_ = "Selected entire buffer";
    }

    void copy_selection() {
        const auto text = selected_text();
        if (!text) {
            status_ = "No block selected; Ctrl-B sets the block mark";
            return;
        }
        clipboard_ = *text;
        status_ = "Copied " + std::to_string(clipboard_.size()) +
            " characters";
    }

    void cut_selection() {
        const auto text = selected_text();
        if (!text) {
            status_ = "No block selected; Ctrl-B sets the block mark";
            return;
        }
        clipboard_ = *text;
        const std::size_t size = clipboard_.size();
        delete_selection();
        status_ = "Cut " + std::to_string(size) + " characters";
    }

    void paste_clipboard() {
        if (clipboard_.empty()) {
            status_ = "Clipboard is empty";
            return;
        }
        delete_selection();
        std::vector<std::string> pasted_lines;
        std::string current;
        for (const char character : clipboard_) {
            if (character == '\n') {
                pasted_lines.push_back(current);
                current.clear();
            } else {
                current.push_back(character);
            }
        }
        pasted_lines.push_back(current);

        const std::string prefix = lines_[row_].substr(0, column_);
        const std::string suffix = lines_[row_].substr(column_);
        if (pasted_lines.size() == 1) {
            lines_[row_] = prefix + pasted_lines.front() + suffix;
            column_ += pasted_lines.front().size();
        } else {
            lines_[row_] = prefix + pasted_lines.front();
            std::vector<std::string> inserted(
                pasted_lines.begin() + 1, pasted_lines.end());
            inserted.back() += suffix;
            lines_.insert(
                lines_.begin() + static_cast<std::ptrdiff_t>(row_ + 1),
                inserted.begin(),
                inserted.end());
            row_ += pasted_lines.size() - 1;
            column_ = pasted_lines.back().size();
        }
        selection_anchor_.reset();
        mark_dirty();
        status_ = "Pasted " + std::to_string(clipboard_.size()) +
            " characters";
    }

    void format_buffer() {
        std::string source;
        for (const std::string& line : lines_) {
            source += line;
            source.push_back('\n');
        }
        try {
            const std::string formatted = format_action_source(source);
            if (formatted == source) {
                status_ = "Source already has canonical spacing";
                return;
            }
            lines_ = editor_lines_from_text(formatted);
            row_ = std::min(row_, lines_.size() - 1);
            column_ = std::min(column_, lines_[row_].size());
            selection_anchor_.reset();
            mouse_selecting_ = false;
            mark_dirty();
            status_ = "Formatted buffer; press Ctrl-S to save";
        } catch (const std::exception& error) {
            status_ = error.what();
        }
    }

    void show_help() {
        const std::optional<std::string> token = token_at_cursor(lines_[row_], column_);
        if (token) {
            popup_ = catalog_.lookup(*token);
            if (!popup_) {
                popup_ = editor_help_topic(*token);
                popup_->summary = "No catalog entry exists for " + *token + ".";
            }
        } else {
            popup_ = editor_help_topic("ACTEDIT");
        }
        popup_scroll_ = 0;
    }

    void show_editor_command_help() {
        popup_ = editor_command_help_topic();
        popup_scroll_ = 0;
    }

    ReferenceEntry topic_entry(const HelpTopic& topic) const {
        return ReferenceEntry{
            topic.token + " [" + topic.kind + "]",
            topic.summary,
            ReferenceEntryKind::Topic,
            {},
            topic,
        };
    }

    ReferencePage language_root_page() const {
        const std::vector<HelpTopic> all_topics = catalog_.list_core("");
        ReferencePage page{
            "ACTION LANGUAGE REFERENCE (" + std::to_string(all_topics.size()) +
                " features)",
            {},
            0,
            0,
        };
        page.entries.push_back(topic_entry(language_overview_topic()));
        const std::vector<std::pair<std::string, std::string>> kinds = {
            {"keyword", "KEYWORDS"},
            {"type", "TYPES"},
            {"builtin", "CORE BUILTINS"},
            {"constant", "CORE CONSTANTS"},
        };
        for (const auto& [kind, label] : kinds) {
            const std::vector<HelpTopic> topics = catalog_.list_core(kind);
            if (topics.empty()) {
                continue;
            }
            page.entries.push_back(ReferenceEntry{
                label + " (" + std::to_string(topics.size()) + ")",
                "Select a feature for its syntax, explanation, and example.",
                ReferenceEntryKind::LanguageKind,
                kind,
                std::nullopt,
            });
        }
        return page;
    }

    ReferencePage language_kind_page(const std::string& kind) const {
        ReferencePage page{
            "LANGUAGE / " + upper_ascii(kind) + "S",
            {},
            0,
            0,
        };
        for (const HelpTopic& topic : catalog_.list_core(kind)) {
            page.entries.push_back(topic_entry(topic));
        }
        return page;
    }

    ReferencePage library_root_page() const {
        ReferencePage page{"ACTION LIBRARIES", {}, 0, 0};
        for (const LibraryReference& library : catalog_.libraries()) {
            page.entries.push_back(ReferenceEntry{
                library.name + " (" + std::to_string(library.topic_count) +
                    " features)",
                library.details,
                ReferenceEntryKind::Library,
                library.name,
                std::nullopt,
            });
        }
        return page;
    }

    ReferencePage library_topic_page(const std::string& name) const {
        ReferencePage page{"LIBRARY " + upper_ascii(name), {}, 0, 0};
        for (const LibraryReference& library : catalog_.libraries()) {
            if (upper_ascii(library.name) != upper_ascii(name)) {
                continue;
            }
            page.entries.push_back(topic_entry(HelpTopic{
                library.name + " OVERVIEW",
                "library",
                library.name + " library (" +
                    std::to_string(library.topic_count) + " features)",
                library.details,
                "Select any feature below and press Enter for its signature, "
                "explanation, example, and target notes.",
                {},
                library.name,
                library.target_notes,
            }));
            break;
        }
        for (const HelpTopic& topic : catalog_.list_library(name)) {
            page.entries.push_back(topic_entry(topic));
        }
        return page;
    }

    void show_language_reference() {
        reference_browser_ = ReferenceBrowser{
            ReferenceBrowser::Root::Language,
            {language_root_page()},
        };
    }

    void show_library_reference() {
        reference_browser_ = ReferenceBrowser{
            ReferenceBrowser::Root::Libraries,
            {library_root_page()},
        };
    }

    struct NavigationPoint {
        fs::path path;
        std::string module;
        std::size_t row = 0;
        std::size_t column = 0;
    };

    struct ReferencesPopup {
        std::string token;
        std::vector<CodeMapLocation> locations;
        std::size_t selected = 0;
        std::size_t scroll = 0;
    };

    NavigationPoint current_point() const {
        return NavigationPoint{path_, module_, row_, column_};
    }

    bool open_point(const NavigationPoint& point) {
        if (dirty_ && point.path != path_) {
            status_ = "Save before navigating to another source file";
            return false;
        }
        if (point.path != path_) {
            if (!fs::is_regular_file(point.path)) {
                status_ = "Definition source is unavailable: " + point.path.generic_string();
                return false;
            }
            lines_ = editor_lines_from_text(read_file(point.path));
            path_ = point.path;
            module_ = point.module;
            top_ = 0;
            left_ = 0;
        }
        row_ = std::min(point.row, lines_.size() - 1);
        column_ = std::min(point.column, lines_[row_].size());
        selection_anchor_.reset();
        mouse_selecting_ = false;
        quit_armed_ = false;
        return true;
    }

    void navigate_to(const CodeMapLocation& location, bool remember) {
        const fs::path destination = fs::weakly_canonical(project_root_ / location.path);
        NavigationPoint point{
            destination,
            upper_ascii(destination.stem().string()),
            location.line == 0 ? 0 : location.line - 1,
            location.column == 0 ? 0 : location.column - 1,
        };
        const NavigationPoint previous = current_point();
        if (!open_point(point)) {
            return;
        }
        if (remember &&
            (previous.path != point.path || previous.row != point.row ||
             previous.column != point.column)) {
            back_stack_.push_back(previous);
            forward_stack_.clear();
        }
        status_ = "Definition " + location.name + " -> " + location.path + ":" +
            std::to_string(location.line);
    }

    void go_to_definition() {
        const std::optional<std::string> token = token_at_cursor(lines_[row_], column_);
        if (!token) {
            status_ = "Place the cursor on a symbol for F5";
            return;
        }
        try {
            const auto definition = code_map_definition(project_root_, *token);
            if (definition) {
                navigate_to(*definition, true);
                return;
            }
            popup_ = catalog_.lookup(*token);
            if (popup_) {
                popup_scroll_ = 0;
                status_ = "Builtin documentation for " + *token;
                return;
            }
            status_ = "No linked definition for " + *token;
        } catch (const std::exception& error) {
            status_ = error.what();
        }
    }

    void launch_graphics_editor() {
        static const std::regex declaration(
            R"(^\s*(SPRITE|SPITE|MSPRITE|BITMAP|MBITMAP)\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*RESOURCE\s+\"([^\"]+)\"\s*(?:;.*)?$)",
            std::regex_constants::icase);
        std::smatch match;
        if (!std::regex_match(lines_[row_], match, declaration)) {
            status_ = "F8 requires a SPRITE, MSPRITE, BITMAP, or MBITMAP RESOURCE line";
            return;
        }
        fs::path relative(match[2].str());
        if (relative.empty() || relative.is_absolute()) {
            status_ = "Invalid graphics resource path";
            return;
        }
        for (const fs::path& component : relative) {
            if (component == "..") {
                status_ = "Graphics resources must stay inside the project";
                return;
            }
        }
        fs::path target;
        for (const fs::path& root : {
                 path_.parent_path(),
                 project_root_ / "RES",
                 project_root_,
             }) {
            const std::optional<fs::path> candidate =
                find_relative_case_insensitive(root, relative);
            std::error_code error;
            if (candidate && fs::is_regular_file(*candidate, error) && !error) {
                target = fs::weakly_canonical(*candidate);
                break;
            }
        }
        if (target.empty()) {
            target = project_root_ / "RES" / relative;
        }
        const std::string type = upper_ascii(match[1].str());
        const std::string command =
            type == "BITMAP" || type == "MBITMAP" ? "actbitmap" : "actsprite";
        const char* graphics_mode =
            type == "MSPRITE" || type == "MBITMAP" ? "multicolor" : "hires";
        const fs::path executable = g_program_path.parent_path() / command;
        if (!fs::is_regular_file(executable)) {
            status_ = "Missing graphics editor: " + executable.generic_string();
            return;
        }
        if (terminal_ == nullptr) {
            status_ = "Graphics editor cannot suspend this terminal";
            return;
        }

        try {
            terminal_->suspend();
            const pid_t child = ::fork();
            if (child < 0) {
                terminal_->resume();
                throw ToolError("ASSET EDITOR LAUNCH: " + std::string(std::strerror(errno)));
            }
            if (child == 0) {
                ::execl(
                    executable.c_str(),
                    command.c_str(),
                    target.c_str(),
                    "tui",
                    graphics_mode,
                    static_cast<char*>(nullptr));
                ::_exit(127);
            }
            int child_status = 0;
            while (::waitpid(child, &child_status, 0) < 0) {
                if (errno != EINTR) {
                    child_status = -1;
                    break;
                }
            }
            terminal_->resume();
            if (child_status != -1 && WIFEXITED(child_status) &&
                WEXITSTATUS(child_status) == 0) {
                status_ = command + " updated " + target.generic_string();
            } else {
                status_ = command + " exited without updating the resource";
            }
        } catch (const std::exception& error) {
            try {
                terminal_->resume();
            } catch (...) {
            }
            status_ = error.what();
        }
    }

    void show_references() {
        const std::optional<std::string> token = token_at_cursor(lines_[row_], column_);
        if (!token) {
            status_ = "Place the cursor on a symbol for F7";
            return;
        }
        try {
            std::vector<CodeMapLocation> locations =
                code_map_references(project_root_, *token);
            if (locations.empty()) {
                status_ = "No linked references to " + *token;
                return;
            }
            references_popup_ = ReferencesPopup{
                *token,
                std::move(locations),
                0,
                0,
            };
        } catch (const std::exception& error) {
            status_ = error.what();
        }
    }

    void navigate_back() {
        if (back_stack_.empty()) {
            status_ = "Navigation history is empty";
            return;
        }
        const NavigationPoint current = current_point();
        const NavigationPoint destination = back_stack_.back();
        if (open_point(destination)) {
            back_stack_.pop_back();
            forward_stack_.push_back(current);
            status_ = "Back -> " + path_.generic_string() + ":" +
                std::to_string(row_ + 1);
        }
    }

    void navigate_forward() {
        if (forward_stack_.empty()) {
            status_ = "Forward navigation history is empty";
            return;
        }
        const NavigationPoint current = current_point();
        const NavigationPoint destination = forward_stack_.back();
        if (open_point(destination)) {
            forward_stack_.pop_back();
            back_stack_.push_back(current);
            status_ = "Forward -> " + path_.generic_string() + ":" +
                std::to_string(row_ + 1);
        }
    }

    void handle_mouse(const Key& key) {
        if (!key.mouse_release && (key.mouse_button & 3) != 0) {
            return;
        }
        if (!key.mouse_release && (key.mouse_button & 32) != 0 &&
            !mouse_selecting_) {
            return;
        }
        const TerminalSize size = terminal_size();
        const std::size_t gutter = gutter_width();
        if (key.mouse_y < 2 || key.mouse_y >= size.rows ||
            key.mouse_x <= gutter) {
            return;
        }
        const std::size_t source_row = top_ + key.mouse_y - 2;
        if (source_row >= lines_.size()) {
            return;
        }
        const TextPoint point{
            source_row,
            std::min(
                lines_[source_row].size(),
                left_ + key.mouse_x - gutter - 1),
        };
        if ((key.mouse_button & 16) != 0 && !key.mouse_release) {
            row_ = point.row;
            column_ = point.column;
            selection_anchor_.reset();
            go_to_definition();
            return;
        }
        if (!key.mouse_release && (key.mouse_button & 32) == 0) {
            selection_anchor_ = point;
            mouse_selecting_ = true;
        }
        row_ = point.row;
        column_ = point.column;
        if (key.mouse_release) {
            mouse_selecting_ = false;
            if (!selection_bounds()) {
                selection_anchor_.reset();
            }
        }
    }

    fs::path path_;
    fs::path project_root_;
    std::string module_;
    HelpCatalog& catalog_;
    bool syntax_highlighting_;
    std::vector<std::string> lines_;
    std::size_t row_ = 0;
    std::size_t column_ = 0;
    std::size_t top_ = 0;
    std::size_t left_ = 0;
    bool dirty_ = false;
    bool quit_armed_ = false;
    std::string status_;
    std::optional<HelpTopic> popup_;
    std::size_t popup_scroll_ = 0;
    std::optional<ReferencesPopup> references_popup_;
    std::optional<ReferenceBrowser> reference_browser_;
    std::vector<NavigationPoint> back_stack_;
    std::vector<NavigationPoint> forward_stack_;
    std::optional<TextPoint> selection_anchor_;
    std::string clipboard_;
    bool mouse_selecting_ = false;
    TerminalSession* terminal_ = nullptr;
};

}  // namespace

void set_program_path(const char* argv0) {
    g_program_path = executable_path_from_argv0(argv0);
}

fs::path program_path() {
    return g_program_path;
}

int command_acthelp(const std::vector<std::string>& args) {
    HelpCatalog catalog;
    if (args.empty()) {
        std::cout
            << "ACTION LANGUAGE HELP\n"
            << "TOPICS " << catalog.count() << "\n"
            << "DATABASE " << catalog.path().generic_string() << "\n\n"
            << "acthelp <keyword-or-function>\n"
            << "acthelp search <text>\n"
            << "acthelp list [keyword|type|builtin|constant]\n";
        return 0;
    }

    const std::string mode = upper_ascii(args.front());
    if (mode == "--DATABASE" || mode == "DATABASE") {
        if (args.size() != 1) {
            throw ToolError("BAD HELP COMMAND");
        }
        std::cout << catalog.path().generic_string() << "\n";
        return 0;
    }
    if (mode == "LIST" || mode == "--LIST") {
        if (args.size() > 2) {
            throw ToolError("BAD HELP COMMAND");
        }
        const std::string kind = args.size() == 2 ? trim(args[1]) : "";
        if (!kind.empty()) {
            const std::string normalized = upper_ascii(kind);
            if (normalized != "KEYWORD" && normalized != "TYPE" &&
                normalized != "BUILTIN" && normalized != "CONSTANT") {
                throw ToolError("BAD HELP KIND");
            }
        }
        for (const HelpTopic& topic : catalog.list(kind)) {
            std::cout << topic.token << " [" << topic.kind << "] - "
                      << topic.summary << "\n";
        }
        return 0;
    }
    if (mode == "SEARCH" || mode == "--SEARCH") {
        if (args.size() < 2) {
            throw ToolError("NO HELP SEARCH");
        }
        std::string query;
        for (std::size_t index = 1; index < args.size(); ++index) {
            if (!query.empty()) {
                query.push_back(' ');
            }
            query += args[index];
        }
        const std::vector<HelpTopic> matches = catalog.search(query);
        for (const HelpTopic& topic : matches) {
            std::cout << topic.token << " [" << topic.kind << "] - "
                      << topic.summary << "\n";
        }
        std::cout << "MATCHES " << matches.size() << "\n";
        return matches.empty() ? 1 : 0;
    }
    if (args.size() != 1) {
        throw ToolError("BAD HELP COMMAND");
    }
    const std::optional<HelpTopic> topic = catalog.lookup(args.front());
    if (!topic) {
        throw ToolError("NO HELP FOR " + args.front());
    }
    print_topic(std::cout, *topic);
    return 0;
}

bool editor_terminal_available() {
    return ::isatty(STDIN_FILENO) != 0 && ::isatty(STDOUT_FILENO) != 0;
}

int run_terminal_editor(
    const fs::path& source_path,
    const std::string& module,
    const fs::path& project_root,
    bool syntax_highlighting) {
    HelpCatalog catalog;
    Editor editor(source_path, module, project_root, catalog, syntax_highlighting);
    return editor.run();
}

void print_highlighted_source(const std::string& source, std::ostream& output) {
    HelpCatalog catalog;
    const std::vector<std::string> lines = editor_lines_from_text(source);
    for (const std::string& line : lines) {
        output << highlighted_window(line, 0, line.size(), catalog) << "\x1b[0m\n";
    }
}

}  // namespace action_linux
