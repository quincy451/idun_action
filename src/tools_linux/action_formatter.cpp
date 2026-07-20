#include "action_formatter.hpp"

#include "action_help_editor.hpp"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include <glob.h>
#include <unistd.h>

namespace fs = std::filesystem;

namespace action_linux {
namespace {

constexpr std::size_t kIndentWidth = 4;

std::string upper_ascii(std::string_view input) {
    std::string output;
    output.reserve(input.size());
    for (const unsigned char character : input) {
        output.push_back(static_cast<char>(std::toupper(character)));
    }
    return output;
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

std::string rtrim(std::string_view input) {
    std::size_t end = input.size();
    while (end > 0 &&
           std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }
    return std::string(input.substr(0, end));
}

std::vector<std::string> split_lines(const std::string& text) {
    std::vector<std::string> lines;
    std::string current;
    for (std::size_t index = 0; index < text.size(); ++index) {
        const char character = text[index];
        if (character == '\r' || character == '\n') {
            lines.push_back(current);
            current.clear();
            if (character == '\r' && index + 1 < text.size() &&
                text[index + 1] == '\n') {
                ++index;
            }
        } else {
            current.push_back(character);
        }
    }
    if (!current.empty() || text.empty()) {
        lines.push_back(current);
    }
    return lines;
}

std::optional<std::size_t> comment_offset(std::string_view line) {
    bool in_string = false;
    bool escaped = false;
    bool character_literal = false;
    for (std::size_t index = 0; index < line.size(); ++index) {
        const char character = line[index];
        if (character_literal) {
            character_literal = false;
            continue;
        }
        if (!in_string && character == '\'') {
            character_literal = true;
            continue;
        }
        if (in_string && character == '\\' && !escaped) {
            escaped = true;
            continue;
        }
        if (character == '"' && !escaped) {
            in_string = !in_string;
        } else if (character == ';' && !in_string) {
            return index;
        }
        escaped = false;
    }
    return std::nullopt;
}

struct SourceParts {
    std::string code;
    std::string comment;
};

SourceParts split_comment(std::string_view line) {
    const auto offset = comment_offset(line);
    if (!offset) {
        return SourceParts{trim(line), {}};
    }
    return SourceParts{
        trim(line.substr(0, *offset)),
        rtrim(line.substr(*offset)),
    };
}

enum class TokenKind {
    Atom,
    String,
    Character,
    Operator,
    OpenParen,
    CloseParen,
    OpenBracket,
    CloseBracket,
    Comma,
    Colon,
    Other,
};

struct Token {
    TokenKind kind = TokenKind::Other;
    std::string text;
    bool whitespace_before = false;
};

bool is_identifier_start(unsigned char character) {
    return std::isalpha(character) || character == '_';
}

bool is_identifier_part(unsigned char character) {
    return std::isalnum(character) || character == '_';
}

std::vector<Token> tokenize_action(std::string_view code) {
    std::vector<Token> tokens;
    bool whitespace = false;
    std::size_t index = 0;
    while (index < code.size()) {
        const unsigned char character = static_cast<unsigned char>(code[index]);
        if (std::isspace(character)) {
            whitespace = true;
            ++index;
            continue;
        }

        const std::size_t begin = index;
        TokenKind kind = TokenKind::Other;
        if (is_identifier_start(character)) {
            kind = TokenKind::Atom;
            ++index;
            while (index < code.size() &&
                   is_identifier_part(static_cast<unsigned char>(code[index]))) {
                ++index;
            }
        } else if (std::isdigit(character)) {
            kind = TokenKind::Atom;
            ++index;
            while (index < code.size() &&
                   std::isdigit(static_cast<unsigned char>(code[index]))) {
                ++index;
            }
            if (index < code.size() && code[index] == '.') {
                ++index;
                while (index < code.size() &&
                       std::isdigit(static_cast<unsigned char>(code[index]))) {
                    ++index;
                }
            }
            if (index < code.size() &&
                (code[index] == 'e' || code[index] == 'E')) {
                ++index;
                if (index < code.size() &&
                    (code[index] == '+' || code[index] == '-')) {
                    ++index;
                }
                while (index < code.size() &&
                       std::isdigit(static_cast<unsigned char>(code[index]))) {
                    ++index;
                }
            }
        } else if (character == '$') {
            kind = TokenKind::Atom;
            ++index;
            while (index < code.size() &&
                   std::isxdigit(static_cast<unsigned char>(code[index]))) {
                ++index;
            }
        } else if (character == '%' && index + 1 < code.size() &&
                   (code[index + 1] == '0' || code[index + 1] == '1')) {
            kind = TokenKind::Atom;
            ++index;
            while (index < code.size() &&
                   (code[index] == '0' || code[index] == '1')) {
                ++index;
            }
        } else if (character == '"') {
            kind = TokenKind::String;
            bool escaped = false;
            ++index;
            while (index < code.size()) {
                const char value = code[index++];
                if (value == '"' && !escaped) {
                    break;
                }
                if (value == '\\' && !escaped) {
                    escaped = true;
                } else {
                    escaped = false;
                }
            }
        } else if (character == '\'') {
            kind = TokenKind::Character;
            ++index;
            if (index < code.size()) {
                ++index;
            }
        } else if (character == '(') {
            kind = TokenKind::OpenParen;
            ++index;
        } else if (character == ')') {
            kind = TokenKind::CloseParen;
            ++index;
        } else if (character == '[') {
            kind = TokenKind::OpenBracket;
            ++index;
        } else if (character == ']') {
            kind = TokenKind::CloseBracket;
            ++index;
        } else if (character == ',') {
            kind = TokenKind::Comma;
            ++index;
        } else if (character == ':') {
            kind = TokenKind::Colon;
            ++index;
        } else if (std::string_view("=+-*/<>#&!%^@").find(character) !=
                   std::string_view::npos) {
            kind = TokenKind::Operator;
            ++index;
            if (index < code.size()) {
                const std::string pair = std::string(code.substr(begin, 2));
                if (pair == "<>" || pair == "!=" || pair == "<=" ||
                    pair == ">=" || pair == "==") {
                    ++index;
                }
            }
        } else {
            ++index;
        }

        tokens.push_back(Token{
            kind,
            std::string(code.substr(begin, index - begin)),
            whitespace,
        });
        whitespace = false;
    }
    return tokens;
}

bool is_atom_like(TokenKind kind) {
    return kind == TokenKind::Atom || kind == TokenKind::String ||
        kind == TokenKind::Character;
}

bool needs_space(const Token& previous, const Token& current) {
    if (current.kind == TokenKind::Comma || current.kind == TokenKind::CloseParen ||
        current.kind == TokenKind::CloseBracket || current.kind == TokenKind::Colon ||
        current.kind == TokenKind::Operator) {
        return false;
    }
    if (previous.kind == TokenKind::Comma || previous.kind == TokenKind::OpenParen ||
        previous.kind == TokenKind::OpenBracket || previous.kind == TokenKind::Colon ||
        previous.kind == TokenKind::Operator) {
        return false;
    }
    if (current.kind == TokenKind::OpenParen) {
        if (previous.kind != TokenKind::Atom) {
            return false;
        }
        static const std::set<std::string> spaced_control_words = {
            "IF", "ELSEIF", "WHILE", "UNTIL", "FOR",
        };
        return spaced_control_words.count(upper_ascii(previous.text)) != 0;
    }
    if (current.kind == TokenKind::OpenBracket) {
        return previous.kind == TokenKind::Atom &&
            (upper_ascii(previous.text) == "ASMBLOCK" ||
             upper_ascii(previous.text) == "CODE");
    }
    if (is_atom_like(previous.kind) && is_atom_like(current.kind)) {
        return current.whitespace_before;
    }
    if ((previous.kind == TokenKind::CloseParen ||
         previous.kind == TokenKind::CloseBracket) &&
        is_atom_like(current.kind)) {
        return true;
    }
    if (is_atom_like(previous.kind) && current.kind == TokenKind::Other) {
        return current.whitespace_before;
    }
    if (previous.kind == TokenKind::Other && is_atom_like(current.kind)) {
        return current.whitespace_before;
    }
    return current.whitespace_before;
}

std::string format_action_code(std::string_view code) {
    const std::vector<Token> tokens = tokenize_action(code);
    std::string output;
    for (std::size_t index = 0; index < tokens.size(); ++index) {
        if (index > 0 && needs_space(tokens[index - 1], tokens[index])) {
            output.push_back(' ');
        }
        output += tokens[index].text;
    }
    return output;
}

std::string compose_line(
    std::size_t indentation,
    const SourceParts& parts,
    bool assembly) {
    std::string code;
    if (assembly) {
        const std::string cleaned = trim(parts.code);
        const std::size_t label = cleaned.find(':');
        if (label != std::string::npos) {
            code = trim(std::string_view(cleaned).substr(0, label));
            code.push_back(':');
            const std::string remainder =
                trim(std::string_view(cleaned).substr(label + 1));
            if (!remainder.empty()) {
                code.push_back(' ');
                code += remainder;
            }
        } else {
            const std::size_t separator = cleaned.find_first_of(" \t");
            if (separator == std::string::npos) {
                code = cleaned;
            } else {
                code = cleaned.substr(0, separator);
                const std::string operand = format_action_code(
                    std::string_view(cleaned).substr(separator + 1));
                if (!operand.empty()) {
                    code.push_back(' ');
                    code += operand;
                }
            }
        }
    } else {
        code = format_action_code(parts.code);
    }

    std::string output(indentation * kIndentWidth, ' ');
    output += code;
    if (!parts.comment.empty()) {
        if (!code.empty()) {
            output += "  ";
        }
        output += parts.comment;
    }
    return rtrim(output);
}

bool starts_with_word(std::string_view code, std::string_view word) {
    const std::string upper = upper_ascii(trim(code));
    const std::string expected = upper_ascii(word);
    if (upper.size() < expected.size() ||
        upper.compare(0, expected.size(), expected) != 0) {
        return false;
    }
    return upper.size() == expected.size() ||
        std::isspace(static_cast<unsigned char>(upper[expected.size()])) ||
        upper[expected.size()] == '(' || upper[expected.size()] == '[';
}

bool is_routine_declaration(std::string_view code) {
    const std::string upper = upper_ascii(trim(code));
    if (starts_with_word(upper, "PROC") || starts_with_word(upper, "OVERLAY")) {
        return true;
    }
    const std::size_t func = upper.find("FUNC");
    if (func == std::string::npos) {
        return false;
    }
    const bool left_boundary = func == 0 ||
        std::isspace(static_cast<unsigned char>(upper[func - 1]));
    const std::size_t after = func + 4;
    const bool right_boundary = after == upper.size() ||
        std::isspace(static_cast<unsigned char>(upper[after]));
    return left_boundary && right_boundary;
}

enum class BlockKind {
    Routine,
    Conditional,
    Loop,
};

void pop_through(std::vector<BlockKind>& blocks, BlockKind wanted) {
    while (!blocks.empty()) {
        const BlockKind kind = blocks.back();
        blocks.pop_back();
        if (kind == wanted) {
            return;
        }
    }
}

void close_previous_routine(std::vector<BlockKind>& blocks) {
    const auto routine = std::find(blocks.rbegin(), blocks.rend(), BlockKind::Routine);
    if (routine != blocks.rend()) {
        blocks.erase(routine.base() - 1, blocks.end());
    }
}

struct DelimiterDelta {
    int parentheses = 0;
    int brackets = 0;
};

DelimiterDelta delimiter_delta(std::string_view code) {
    DelimiterDelta delta;
    bool in_string = false;
    bool escaped = false;
    bool character_literal = false;
    for (const char character : code) {
        if (character_literal) {
            character_literal = false;
            continue;
        }
        if (!in_string && character == '\'') {
            character_literal = true;
            continue;
        }
        if (in_string && character == '\\' && !escaped) {
            escaped = true;
            continue;
        }
        if (character == '"' && !escaped) {
            in_string = !in_string;
        } else if (!in_string) {
            if (character == '(') ++delta.parentheses;
            if (character == ')') --delta.parentheses;
            if (character == '[') ++delta.brackets;
            if (character == ']') --delta.brackets;
        }
        escaped = false;
    }
    return delta;
}

bool is_assembly_label(std::string_view code) {
    const std::string cleaned = trim(code);
    if (cleaned.empty() ||
        !(std::isalpha(static_cast<unsigned char>(cleaned.front())) ||
          cleaned.front() == '_')) {
        return false;
    }
    std::size_t index = 1;
    while (index < cleaned.size() &&
           (std::isalnum(static_cast<unsigned char>(cleaned[index])) ||
            cleaned[index] == '_')) {
        ++index;
    }
    return index < cleaned.size() && cleaned[index] == ':';
}

std::string format_source(const std::string& source) {
    if (source.find('\0') != std::string::npos) {
        throw ToolError("BINARY ACTION SOURCE");
    }

    std::vector<std::string> output;
    std::vector<BlockKind> blocks;
    int parenthesis_depth = 0;
    int bracket_depth = 0;
    bool pending_routine = false;
    bool in_assembly = false;
    std::size_t assembly_indent = 0;

    for (const std::string& raw_line : split_lines(source)) {
        SourceParts parts = split_comment(raw_line);
        if (parts.code.empty() && parts.comment.empty()) {
            if (!output.empty() && !output.back().empty()) {
                output.emplace_back();
            }
            continue;
        }

        if (in_assembly) {
            const bool closes = trim(parts.code) == "]";
            const std::size_t indentation = closes || is_assembly_label(parts.code)
                ? assembly_indent
                : assembly_indent + 1;
            output.push_back(compose_line(indentation, parts, !closes));
            if (closes) {
                in_assembly = false;
                bracket_depth = 0;
            }
            continue;
        }

        const std::string upper = upper_ascii(parts.code);
        const bool routine_end = upper == "ENDPROC" || upper == "ENDFUNC" ||
            upper == "ENDOVERLAY";
        const bool routine_start = is_routine_declaration(parts.code);
        const bool module_boundary = starts_with_word(parts.code, "MODULE");
        const bool conditional_end = upper == "FI";
        const bool conditional_middle = starts_with_word(parts.code, "ELSEIF") ||
            upper == "ELSE";
        const bool loop_end = upper == "OD";

        if (routine_start || module_boundary) {
            close_previous_routine(blocks);
            pending_routine = false;
            parenthesis_depth = 0;
            bracket_depth = 0;
        } else if (routine_end) {
            pop_through(blocks, BlockKind::Routine);
            pending_routine = false;
            parenthesis_depth = 0;
            bracket_depth = 0;
        } else if (conditional_end) {
            pop_through(blocks, BlockKind::Conditional);
        } else if (loop_end) {
            pop_through(blocks, BlockKind::Loop);
        }

        std::size_t indentation = blocks.size();
        if (conditional_middle) {
            const auto conditional =
                std::find(blocks.rbegin(), blocks.rend(), BlockKind::Conditional);
            if (conditional != blocks.rend()) {
                indentation = static_cast<std::size_t>(
                    std::distance(blocks.begin(), conditional.base() - 1));
            }
        }
        const bool closes_continuation =
            (!parts.code.empty() &&
             (parts.code.front() == ')' || parts.code.front() == ']'));
        if ((parenthesis_depth > 0 || bracket_depth > 0) &&
            !closes_continuation) {
            ++indentation;
        } else if ((parenthesis_depth > 0 || bracket_depth > 0) &&
                   pending_routine) {
            ++indentation;
        }

        output.push_back(compose_line(indentation, parts, false));

        const DelimiterDelta delta = delimiter_delta(parts.code);
        parenthesis_depth = std::max(0, parenthesis_depth + delta.parentheses);
        bracket_depth = std::max(0, bracket_depth + delta.brackets);

        if (routine_start) {
            if (parenthesis_depth > 0) {
                pending_routine = true;
            } else {
                blocks.push_back(BlockKind::Routine);
            }
        } else if (pending_routine && parenthesis_depth == 0) {
            blocks.push_back(BlockKind::Routine);
            pending_routine = false;
        }

        if (starts_with_word(parts.code, "ASMBLOCK") && delta.brackets > 0) {
            in_assembly = true;
            assembly_indent = indentation;
            bracket_depth = 0;
        } else if (starts_with_word(parts.code, "IF") &&
                   !starts_with_word(parts.code, "IFDEF")) {
            blocks.push_back(BlockKind::Conditional);
        } else if (upper == "DO") {
            blocks.push_back(BlockKind::Loop);
        }
    }

    while (!output.empty() && output.back().empty()) {
        output.pop_back();
    }
    std::string formatted;
    for (const std::string& line : output) {
        formatted += line;
        formatted.push_back('\n');
    }
    return formatted;
}

std::string read_source(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ToolError("ACTSPC LOAD FAIL: " + path.string());
    }
    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void atomic_write_source(const fs::path& path, std::string_view source) {
    static std::uint64_t sequence = 0;
    const fs::path temporary = path.parent_path() /
        ("." + path.filename().string() + ".actspc-" +
         std::to_string(static_cast<long long>(::getpid())) + "-" +
         std::to_string(++sequence));
    try {
        {
            std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
            if (!output) {
                throw ToolError("ACTSPC SAVE FAIL: " + path.string());
            }
            output.write(source.data(), static_cast<std::streamsize>(source.size()));
            if (!output) {
                throw ToolError("ACTSPC SAVE FAIL: " + path.string());
            }
        }
        std::error_code error;
        const fs::perms permissions = fs::status(path, error).permissions();
        if (error) {
            throw ToolError("ACTSPC STATUS FAIL: " + path.string());
        }
        fs::permissions(temporary, permissions, fs::perm_options::replace, error);
        if (error) {
            throw ToolError("ACTSPC MODE FAIL: " + path.string());
        }
        fs::rename(temporary, path);
    } catch (...) {
        std::error_code ignored;
        fs::remove(temporary, ignored);
        throw;
    }
}

bool has_action_extension(const fs::path& path) {
    return upper_ascii(path.extension().string()) == ".ACT";
}

std::string action_glob_pattern(std::string pattern) {
    const fs::path path(pattern);
    if (path.extension().empty() &&
        pattern.find_first_of("*?[") == std::string::npos) {
        pattern += ".act";
    }
    if (pattern.size() >= 4 &&
        upper_ascii(std::string_view(pattern).substr(pattern.size() - 4)) == ".ACT") {
        pattern.resize(pattern.size() - 4);
        pattern += ".[aA][cC][tT]";
    }
    return pattern;
}

std::vector<fs::path> matches_for_specification(const std::string& specification) {
    glob_t matches{};
    const std::string pattern = action_glob_pattern(specification);
    const int status = ::glob(pattern.c_str(), GLOB_NOSORT, nullptr, &matches);
    std::vector<fs::path> paths;
    if (status == 0) {
        for (std::size_t index = 0; index < matches.gl_pathc; ++index) {
            const fs::path candidate(matches.gl_pathv[index]);
            std::error_code error;
            if (has_action_extension(candidate) &&
                fs::is_regular_file(candidate, error) && !error) {
                paths.push_back(fs::weakly_canonical(candidate));
            }
        }
    }
    ::globfree(&matches);
    if (status != 0 && status != GLOB_NOMATCH) {
        throw ToolError("ACTSPC MATCH FAIL: " + specification);
    }
    if (paths.empty()) {
        throw ToolError("ACTSPC NO MATCH: " + specification);
    }
    return paths;
}

fs::path display_path(const fs::path& path) {
    std::error_code error;
    const fs::path relative = fs::relative(path, fs::current_path(), error);
    if (!error && !relative.empty()) {
        return relative;
    }
    return path;
}

}  // namespace

std::string format_action_source(std::string_view source) {
    return format_source(std::string(source));
}

int command_actspc(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("ACTSPC NO FILESPEC");
    }

    std::set<fs::path> unique_paths;
    for (const std::string& specification : args) {
        for (const fs::path& path : matches_for_specification(specification)) {
            unique_paths.insert(path);
        }
    }

    struct FormattedFile {
        fs::path path;
        std::string source;
        bool changed = false;
    };
    std::vector<FormattedFile> files;
    files.reserve(unique_paths.size());
    for (const fs::path& path : unique_paths) {
        const std::string original = read_source(path);
        std::string formatted = format_action_source(original);
        const bool changed = original != formatted;
        files.push_back(FormattedFile{
            path,
            std::move(formatted),
            changed,
        });
    }

    std::size_t changed = 0;
    for (const FormattedFile& file : files) {
        if (file.changed) {
            atomic_write_source(file.path, file.source);
            ++changed;
            std::cout << "FORMATTED " << display_path(file.path).string() << "\n";
        } else {
            std::cout << "UNCHANGED " << display_path(file.path).string() << "\n";
        }
    }
    std::cout << "ACTSPC OK files=" << files.size()
              << " changed=" << changed
              << " unchanged=" << (files.size() - changed) << "\n";
    return 0;
}

}  // namespace action_linux
