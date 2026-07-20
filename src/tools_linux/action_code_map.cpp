#include "action_code_map.hpp"

#include "action_help_editor.hpp"

#include <algorithm>
#include <cctype>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <string_view>
#include <system_error>
#include <unistd.h>

#include <sqlite3.h>

namespace fs = std::filesystem;

namespace action_linux {
namespace {

constexpr int kCodeMapSchemaVersion = 1;

std::string upper_ascii(std::string_view input) {
    std::string output;
    output.reserve(input.size());
    for (const unsigned char ch : input) {
        output.push_back(static_cast<char>(std::toupper(ch)));
    }
    return output;
}

std::string trim(std::string_view input) {
    std::size_t begin = 0;
    while (begin < input.size() &&
           std::isspace(static_cast<unsigned char>(input[begin])) != 0) {
        ++begin;
    }
    std::size_t end = input.size();
    while (end > begin &&
           std::isspace(static_cast<unsigned char>(input[end - 1])) != 0) {
        --end;
    }
    return std::string(input.substr(begin, end - begin));
}

std::vector<std::string> split_lines(const std::string& text) {
    std::vector<std::string> lines;
    std::string current;
    for (std::size_t index = 0; index < text.size(); ++index) {
        const char ch = text[index];
        if (ch == '\r' || ch == '\n') {
            lines.push_back(current);
            current.clear();
            if (ch == '\r' && index + 1 < text.size() && text[index + 1] == '\n') {
                ++index;
            }
        } else {
            current.push_back(ch);
        }
    }
    if (!current.empty() || text.empty()) {
        lines.push_back(current);
    }
    return lines;
}

std::string read_text_file(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ToolError("CODE MAP SOURCE READ: " + path.generic_string());
    }
    return std::string(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

std::string source_code_prefix(std::string_view line) {
    bool in_string = false;
    bool escaped = false;
    for (std::size_t index = 0; index < line.size(); ++index) {
        const char ch = line[index];
        if (in_string) {
            if (escaped) {
                escaped = false;
            } else if (ch == '\\') {
                escaped = true;
            } else if (ch == '"') {
                in_string = false;
            }
        } else if (ch == '"') {
            in_string = true;
        } else if (ch == ';') {
            return std::string(line.substr(0, index));
        }
    }
    return std::string(line);
}

bool is_identifier_start(char ch) {
    return std::isalpha(static_cast<unsigned char>(ch)) != 0 || ch == '_';
}

bool is_identifier_char(char ch) {
    return std::isalnum(static_cast<unsigned char>(ch)) != 0 || ch == '_';
}

bool path_is_within(const fs::path& parent, const fs::path& child) {
    auto parent_part = parent.begin();
    auto child_part = child.begin();
    for (; parent_part != parent.end(); ++parent_part, ++child_part) {
        if (child_part == child.end() || *parent_part != *child_part) {
            return false;
        }
    }
    return true;
}

class Database {
public:
    Database(const fs::path& path, int flags) {
        const int status = sqlite3_open_v2(path.c_str(), &database_, flags, nullptr);
        if (status != SQLITE_OK) {
            const std::string message = database_ == nullptr
                ? "open failed"
                : sqlite3_errmsg(database_);
            if (database_ != nullptr) {
                sqlite3_close(database_);
                database_ = nullptr;
            }
            throw ToolError("CODE MAP OPEN: " + message);
        }
        sqlite3_busy_timeout(database_, 2000);
    }

    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;

    ~Database() {
        if (database_ != nullptr) {
            sqlite3_close(database_);
        }
    }

    sqlite3* get() const { return database_; }

    void exec(const std::string& sql) {
        char* error = nullptr;
        if (sqlite3_exec(database_, sql.c_str(), nullptr, nullptr, &error) != SQLITE_OK) {
            const std::string message = error == nullptr ? sqlite3_errmsg(database_) : error;
            sqlite3_free(error);
            throw ToolError("CODE MAP SQL: " + message);
        }
    }

private:
    sqlite3* database_ = nullptr;
};

class Statement {
public:
    Statement(Database& database, const std::string& sql)
        : database_(database.get()) {
        if (sqlite3_prepare_v2(database_, sql.c_str(), -1, &statement_, nullptr) != SQLITE_OK) {
            throw ToolError("CODE MAP QUERY: " + std::string(sqlite3_errmsg(database_)));
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
                statement_, index, value.data(),
                static_cast<sqlite3_uint64>(value.size()), SQLITE_TRANSIENT,
                SQLITE_UTF8) != SQLITE_OK) {
            fail("bind");
        }
    }

    void bind_integer(int index, std::int64_t value) {
        if (sqlite3_bind_int64(statement_, index, value) != SQLITE_OK) {
            fail("bind");
        }
    }

    void bind_optional_integer(int index, const std::optional<std::uint16_t>& value) {
        const int status = value
            ? sqlite3_bind_int64(statement_, index, *value)
            : sqlite3_bind_null(statement_, index);
        if (status != SQLITE_OK) {
            fail("bind");
        }
    }

    void bind_null(int index) {
        if (sqlite3_bind_null(statement_, index) != SQLITE_OK) {
            fail("bind");
        }
    }

    bool step() {
        const int status = sqlite3_step(statement_);
        if (status == SQLITE_ROW) return true;
        if (status == SQLITE_DONE) return false;
        fail("step");
        return false;
    }

    void reset() {
        if (sqlite3_reset(statement_) != SQLITE_OK ||
            sqlite3_clear_bindings(statement_) != SQLITE_OK) {
            fail("reset");
        }
    }

    std::string text(int column) const {
        const unsigned char* value = sqlite3_column_text(statement_, column);
        return value == nullptr
            ? std::string{}
            : std::string(reinterpret_cast<const char*>(value));
    }

    std::int64_t integer(int column) const {
        return sqlite3_column_int64(statement_, column);
    }

    bool is_null(int column) const {
        return sqlite3_column_type(statement_, column) == SQLITE_NULL;
    }

private:
    [[noreturn]] void fail(std::string_view operation) const {
        throw ToolError(
            "CODE MAP " + upper_ascii(operation) + ": " + sqlite3_errmsg(database_));
    }

    sqlite3* database_ = nullptr;
    sqlite3_stmt* statement_ = nullptr;
};

struct ParsedDefinition {
    CodeMapLocation location;
    std::size_t name_begin = 0;
};

struct SourceDocument {
    const CodeMapModule* module = nullptr;
    fs::path absolute_path;
    std::vector<std::string> lines;
    std::vector<ParsedDefinition> definitions;
    std::map<std::size_t, std::uint16_t> line_addresses;
};

std::optional<std::uint16_t> address_for_line(
    const SourceDocument& document,
    std::size_t line) {
    const auto exact = document.line_addresses.find(line);
    if (exact != document.line_addresses.end()) {
        return exact->second;
    }
    auto after = document.line_addresses.upper_bound(line);
    if (after == document.line_addresses.begin()) {
        return std::nullopt;
    }
    --after;
    return after->second;
}

std::optional<CodeMapSymbol> linked_symbol(
    const CodeMapModule& module,
    std::string_view name) {
    const std::string wanted = upper_ascii(name);
    const auto found = std::find_if(
        module.symbols.begin(), module.symbols.end(),
        [&](const CodeMapSymbol& symbol) {
            return upper_ascii(symbol.name) == wanted;
        });
    if (found == module.symbols.end()) {
        return std::nullopt;
    }
    return *found;
}

std::vector<ParsedDefinition> parse_definitions(
    const CodeMapModule& module,
    const std::vector<std::string>& lines) {
    static const std::regex routine(
        R"(^\s*(?:(BYTE|CARD|INT|REAL)\s+FUNC\s+|(PROC|OVERLAY)\s+)([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$)",
        std::regex_constants::icase);
    static const std::regex module_declaration(
        R"(^\s*MODULE\s+([A-Za-z_][A-Za-z0-9_]*)\s*$)",
        std::regex_constants::icase);
    static const std::regex data_declaration(
        R"(^\s*(?:REU\s+)?(BYTE|CARD|INT|REAL)\s+(?:(ARRAY|POINTER)\s+)?([A-Za-z_][A-Za-z0-9_]*)\b.*$)",
        std::regex_constants::icase);

    std::vector<ParsedDefinition> definitions;
    std::string current_routine;
    for (std::size_t index = 0; index < lines.size(); ++index) {
        const std::string code = source_code_prefix(lines[index]);
        const std::string clean = trim(code);
        const std::string upper = upper_ascii(clean);
        std::smatch match;
        ParsedDefinition definition;
        bool found = false;
        if (std::regex_match(code, match, routine)) {
            const bool function = match[1].matched;
            definition.location.name = upper_ascii(match[3].str());
            definition.location.kind = function
                ? "FUNC"
                : upper_ascii(match[2].str());
            definition.location.signature = clean;
            definition.name_begin = static_cast<std::size_t>(match.position(3));
            current_routine = definition.location.name;
            found = true;
        } else if (std::regex_match(code, match, module_declaration)) {
            definition.location.name = upper_ascii(match[1].str());
            definition.location.kind = "MODULE";
            definition.location.signature = clean;
            definition.name_begin = static_cast<std::size_t>(match.position(1));
            found = true;
        } else if (std::regex_match(code, match, data_declaration) &&
                   upper.find(" FUNC ") == std::string::npos) {
            definition.location.name = upper_ascii(match[3].str());
            definition.location.kind = match[2].matched
                ? upper_ascii(match[2].str())
                : upper_ascii(match[1].str());
            definition.location.signature = clean;
            definition.location.caller = current_routine;
            definition.name_begin = static_cast<std::size_t>(match.position(3));
            found = true;
        }
        if (found) {
            definition.location.module = module.module;
            definition.location.path = module.source_path;
            definition.location.line = index + 1;
            definition.location.column = definition.name_begin + 1;
            if (const auto symbol = linked_symbol(module, definition.location.name)) {
                definition.location.address = symbol->address;
                definition.location.size = symbol->size;
            }
            definitions.push_back(std::move(definition));
        }
        if (upper == "ENDPROC" || upper == "ENDFUNC" || upper == "ENDOVERLAY") {
            current_routine.clear();
        }
    }
    return definitions;
}

std::string fingerprint_for(
    const std::string& entry_module,
    const std::vector<std::uint8_t>& prg,
    const std::vector<CodeMapModule>& modules) {
    std::uint64_t hash = 1469598103934665603ULL;
    const auto add_byte = [&](std::uint8_t byte) {
        hash ^= byte;
        hash *= 1099511628211ULL;
    };
    for (const unsigned char ch : entry_module) add_byte(ch);
    for (const std::uint8_t byte : prg) add_byte(byte);
    for (const CodeMapModule& module : modules) {
        for (const unsigned char ch : module.module) add_byte(ch);
        for (const unsigned char ch : module.source_path) add_byte(ch);
    }
    std::ostringstream output;
    output << std::hex << std::setfill('0') << std::setw(16) << hash;
    return output.str();
}

void validate_schema(Database& database) {
    Statement version(database, "PRAGMA user_version");
    if (!version.step() || version.integer(0) != kCodeMapSchemaVersion) {
        throw ToolError("CODE MAP NEEDS ALINK REBUILD");
    }
}

CodeMapLocation location_from_statement(const Statement& statement) {
    CodeMapLocation location;
    location.name = statement.text(0);
    location.kind = statement.text(1);
    location.caller = statement.text(2);
    location.module = statement.text(3);
    location.path = statement.text(4);
    location.line = static_cast<std::size_t>(statement.integer(5));
    location.column = static_cast<std::size_t>(statement.integer(6));
    if (!statement.is_null(7)) {
        location.address = static_cast<std::uint16_t>(statement.integer(7));
    }
    location.size = static_cast<std::uint16_t>(statement.integer(8));
    location.signature = statement.text(9);
    return location;
}

Database open_code_map(const fs::path& root) {
    const fs::path path = code_map_path(root);
    if (!fs::is_regular_file(path)) {
        throw ToolError("NO CODE MAP; RUN ALINK");
    }
    return Database(path, SQLITE_OPEN_READONLY);
}

}  // namespace

fs::path code_map_path(const fs::path& project_root) {
    return project_root / ".action" / "code-map.sqlite3";
}

void build_code_map(
    const fs::path& project_root,
    const std::string& entry_module,
    const std::vector<std::uint8_t>& prg,
    const std::vector<CodeMapModule>& modules) {
    const fs::path root = fs::weakly_canonical(fs::absolute(project_root));
    const fs::path output = code_map_path(root);
    fs::create_directories(output.parent_path());
    const fs::path temporary = output.parent_path() /
        (".code-map.sqlite3-" + std::to_string(::getpid()));
    std::error_code error;
    fs::remove(temporary, error);

    std::vector<SourceDocument> documents;
    for (const CodeMapModule& module : modules) {
        if (module.source_path.empty()) {
            continue;
        }
        const fs::path source = fs::weakly_canonical(root / module.source_path, error);
        if (error || !path_is_within(root, source) || !fs::is_regular_file(source)) {
            error.clear();
            continue;
        }
        SourceDocument document;
        document.module = &module;
        document.absolute_path = source;
        document.lines = split_lines(read_text_file(source));
        for (const CodeMapLine& line : module.lines) {
            document.line_addresses.emplace(line.line, line.address);
        }
        document.definitions = parse_definitions(module, document.lines);
        documents.push_back(std::move(document));
    }

    std::map<std::string, const ParsedDefinition*> definitions_by_name;
    for (const SourceDocument& document : documents) {
        for (const ParsedDefinition& definition : document.definitions) {
            definitions_by_name.emplace(definition.location.name, &definition);
        }
    }

    try {
        Database database(
            temporary,
            SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_EXCLUSIVE);
        database.exec("PRAGMA journal_mode=DELETE");
        database.exec("PRAGMA synchronous=FULL");
        database.exec("PRAGMA user_version=" + std::to_string(kCodeMapSchemaVersion));
        database.exec(
            "CREATE TABLE build("
            "id INTEGER PRIMARY KEY CHECK(id=1),entry_module TEXT NOT NULL,"
            "fingerprint TEXT NOT NULL,load_address INTEGER NOT NULL,"
            "image_size INTEGER NOT NULL,built_unix INTEGER NOT NULL)");
        database.exec(
            "CREATE TABLE definitions("
            "id INTEGER PRIMARY KEY,name TEXT NOT NULL COLLATE NOCASE,"
            "kind TEXT NOT NULL,caller TEXT NOT NULL,module TEXT NOT NULL,"
            "path TEXT NOT NULL,line INTEGER NOT NULL,column_no INTEGER NOT NULL,"
            "address INTEGER,size INTEGER NOT NULL,signature TEXT NOT NULL)");
        database.exec(
            "CREATE INDEX definitions_name ON definitions(name COLLATE NOCASE)");
        database.exec(
            "CREATE TABLE references_map("
            "id INTEGER PRIMARY KEY,name TEXT NOT NULL COLLATE NOCASE,"
            "kind TEXT NOT NULL,caller TEXT NOT NULL,module TEXT NOT NULL,"
            "path TEXT NOT NULL,line INTEGER NOT NULL,column_no INTEGER NOT NULL,"
            "address INTEGER,definition_id INTEGER REFERENCES definitions(id))");
        database.exec(
            "CREATE INDEX references_name ON references_map(name COLLATE NOCASE)");
        database.exec(
            "CREATE TABLE linked_modules("
            "module TEXT PRIMARY KEY,path TEXT NOT NULL,base_address INTEGER NOT NULL,"
            "size INTEGER NOT NULL)");
        database.exec(
            "CREATE TABLE linked_lines("
            "module TEXT NOT NULL,path TEXT NOT NULL,line INTEGER NOT NULL,"
            "address INTEGER NOT NULL,caller TEXT NOT NULL,text TEXT NOT NULL,"
            "PRIMARY KEY(module,line,address))");
        database.exec("CREATE INDEX linked_lines_address ON linked_lines(address)");
        database.exec("BEGIN IMMEDIATE");

        Statement insert_build(
            database,
            "INSERT INTO build VALUES(1,?,?,?,?,?)");
        insert_build.bind_text(1, upper_ascii(entry_module));
        insert_build.bind_text(2, fingerprint_for(entry_module, prg, modules));
        const std::uint16_t load_address = prg.size() >= 2
            ? static_cast<std::uint16_t>(prg[0] | (prg[1] << 8))
            : 0;
        insert_build.bind_integer(3, load_address);
        insert_build.bind_integer(4, prg.size() >= 2 ? prg.size() - 2 : 0);
        insert_build.bind_integer(
            5,
            std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        insert_build.step();

        Statement insert_module(
            database,
            "INSERT INTO linked_modules(module,path,base_address,size) VALUES(?,?,?,?)");
        for (const CodeMapModule& module : modules) {
            insert_module.bind_text(1, module.module);
            insert_module.bind_text(2, module.source_path);
            insert_module.bind_integer(3, module.base_address);
            insert_module.bind_integer(4, module.size);
            insert_module.step();
            insert_module.reset();
        }

        Statement insert_linked_line(
            database,
            "INSERT OR IGNORE INTO linked_lines(module,path,line,address,caller,text) "
            "VALUES(?,?,?,?,?,?)");
        for (const SourceDocument& document : documents) {
            std::string caller;
            std::map<std::size_t, std::string> routine_at_line;
            for (const ParsedDefinition& definition : document.definitions) {
                if (definition.location.kind == "PROC" ||
                    definition.location.kind == "FUNC" ||
                    definition.location.kind == "OVERLAY") {
                    routine_at_line.emplace(
                        definition.location.line, definition.location.name);
                }
            }
            std::map<std::size_t, std::string> callers;
            for (std::size_t index = 0; index < document.lines.size(); ++index) {
                const std::size_t line_number = index + 1;
                const auto start = routine_at_line.find(line_number);
                if (start != routine_at_line.end()) {
                    caller = start->second;
                }
                callers.emplace(line_number, caller);
                const std::string upper = upper_ascii(
                    trim(source_code_prefix(document.lines[index])));
                if (upper == "ENDPROC" || upper == "ENDFUNC" ||
                    upper == "ENDOVERLAY") {
                    caller.clear();
                }
            }
            for (const CodeMapLine& line : document.module->lines) {
                const std::string text = line.line >= 1 && line.line <= document.lines.size()
                    ? document.lines[line.line - 1]
                    : std::string{};
                const auto owner = callers.find(line.line);
                insert_linked_line.bind_text(1, document.module->module);
                insert_linked_line.bind_text(2, document.module->source_path);
                insert_linked_line.bind_integer(3, line.line);
                insert_linked_line.bind_integer(4, line.address);
                insert_linked_line.bind_text(
                    5, owner == callers.end() ? std::string{} : owner->second);
                insert_linked_line.bind_text(6, text);
                insert_linked_line.step();
                insert_linked_line.reset();
            }
        }

        Statement insert_definition(
            database,
            "INSERT INTO definitions(name,kind,caller,module,path,line,column_no,"
            "address,size,signature) VALUES(?,?,?,?,?,?,?,?,?,?)");
        std::map<std::string, std::int64_t> definition_ids;
        for (const SourceDocument& document : documents) {
            for (const ParsedDefinition& definition : document.definitions) {
                const CodeMapLocation& location = definition.location;
                insert_definition.bind_text(1, location.name);
                insert_definition.bind_text(2, location.kind);
                insert_definition.bind_text(3, location.caller);
                insert_definition.bind_text(4, location.module);
                insert_definition.bind_text(5, location.path);
                insert_definition.bind_integer(6, location.line);
                insert_definition.bind_integer(7, location.column);
                insert_definition.bind_optional_integer(8, location.address);
                insert_definition.bind_integer(9, location.size);
                insert_definition.bind_text(10, location.signature);
                insert_definition.step();
                definition_ids.emplace(
                    location.name,
                    sqlite3_last_insert_rowid(database.get()));
                insert_definition.reset();
            }
        }

        static const std::set<std::string> ignored = {
            "MODULE", "PROC", "ENDPROC", "FUNC", "ENDFUNC", "OVERLAY",
            "ENDOVERLAY", "BYTE", "CARD", "INT", "REAL", "ARRAY", "POINTER",
            "REU", "IF", "THEN", "ELSEIF", "ELSE", "FI", "FOR", "TO",
            "STEP", "WHILE", "DO", "UNTIL", "OD", "EXIT", "RETURN",
        };
        Statement insert_reference(
            database,
            "INSERT INTO references_map(name,kind,caller,module,path,line,column_no,"
            "address,definition_id) VALUES(?,?,?,?,?,?,?,?,?)");
        for (const SourceDocument& document : documents) {
            std::string caller;
            std::map<std::size_t, const ParsedDefinition*> definitions_on_line;
            for (const ParsedDefinition& definition : document.definitions) {
                definitions_on_line.emplace(definition.location.line, &definition);
            }
            for (std::size_t line_index = 0; line_index < document.lines.size(); ++line_index) {
                const std::size_t line_number = line_index + 1;
                const auto line_definition = definitions_on_line.find(line_number);
                if (line_definition != definitions_on_line.end() &&
                    (line_definition->second->location.kind == "PROC" ||
                     line_definition->second->location.kind == "FUNC" ||
                     line_definition->second->location.kind == "OVERLAY")) {
                    caller = line_definition->second->location.name;
                }
                const std::string code = source_code_prefix(document.lines[line_index]);
                bool in_string = false;
                bool escaped = false;
                for (std::size_t cursor = 0; cursor < code.size();) {
                    const char ch = code[cursor];
                    if (in_string) {
                        if (escaped) escaped = false;
                        else if (ch == '\\') escaped = true;
                        else if (ch == '"') in_string = false;
                        ++cursor;
                        continue;
                    }
                    if (ch == '"') {
                        in_string = true;
                        ++cursor;
                        continue;
                    }
                    if (!is_identifier_start(ch)) {
                        ++cursor;
                        continue;
                    }
                    const std::size_t begin = cursor++;
                    while (cursor < code.size() && is_identifier_char(code[cursor])) {
                        ++cursor;
                    }
                    const std::string name = upper_ascii(
                        std::string_view(code).substr(begin, cursor - begin));
                    if (ignored.count(name) != 0) {
                        continue;
                    }
                    if (line_definition != definitions_on_line.end() &&
                        begin == line_definition->second->name_begin) {
                        continue;
                    }
                    std::size_t suffix = cursor;
                    while (suffix < code.size() &&
                           std::isspace(static_cast<unsigned char>(code[suffix])) != 0) {
                        ++suffix;
                    }
                    const bool call = suffix < code.size() && code[suffix] == '(';
                    const auto definition_id = definition_ids.find(name);
                    if (!call && definition_id == definition_ids.end()) {
                        continue;
                    }
                    insert_reference.bind_text(1, name);
                    insert_reference.bind_text(2, call ? "CALL" : "REFERENCE");
                    insert_reference.bind_text(3, caller);
                    insert_reference.bind_text(4, document.module->module);
                    insert_reference.bind_text(5, document.module->source_path);
                    insert_reference.bind_integer(6, line_number);
                    insert_reference.bind_integer(7, begin + 1);
                    insert_reference.bind_optional_integer(
                        8, address_for_line(document, line_number));
                    if (definition_id == definition_ids.end()) {
                        insert_reference.bind_null(9);
                    } else {
                        insert_reference.bind_integer(9, definition_id->second);
                    }
                    insert_reference.step();
                    insert_reference.reset();
                }
                const std::string upper_line = upper_ascii(trim(code));
                if (upper_line == "ENDPROC" || upper_line == "ENDFUNC" ||
                    upper_line == "ENDOVERLAY") {
                    caller.clear();
                }
            }
        }
        database.exec("COMMIT");
        database.exec("PRAGMA optimize");
    } catch (...) {
        fs::remove(temporary, error);
        throw;
    }

    fs::rename(temporary, output, error);
    if (error) {
        fs::remove(output, error);
        error.clear();
        fs::rename(temporary, output, error);
    }
    if (error) {
        const std::string message = error.message();
        fs::remove(temporary, error);
        throw ToolError("CODE MAP INSTALL: " + message);
    }
}

std::optional<CodeMapLocation> code_map_definition(
    const fs::path& project_root,
    const std::string& symbol) {
    Database database = open_code_map(project_root);
    validate_schema(database);
    Statement query(
        database,
        "SELECT name,kind,caller,module,path,line,column_no,address,size,signature "
        "FROM definitions WHERE name=? COLLATE NOCASE "
        "ORDER BY CASE kind WHEN 'PROC' THEN 0 WHEN 'FUNC' THEN 1 "
        "WHEN 'OVERLAY' THEN 2 ELSE 3 END,line LIMIT 1");
    query.bind_text(1, symbol);
    if (!query.step()) {
        return std::nullopt;
    }
    return location_from_statement(query);
}

std::vector<CodeMapLocation> code_map_references(
    const fs::path& project_root,
    const std::string& symbol) {
    Database database = open_code_map(project_root);
    validate_schema(database);
    Statement query(
        database,
        "SELECT r.name,r.kind,r.caller,r.module,r.path,r.line,r.column_no,"
        "r.address,0,'' FROM references_map r WHERE r.name=? COLLATE NOCASE "
        "ORDER BY r.path,r.line,r.column_no");
    query.bind_text(1, symbol);
    std::vector<CodeMapLocation> locations;
    while (query.step()) {
        locations.push_back(location_from_statement(query));
    }
    return locations;
}

std::optional<CodeMapLocation> code_map_address(
    const fs::path& project_root,
    std::uint16_t address) {
    Database database = open_code_map(project_root);
    validate_schema(database);
    Statement query(
        database,
        "SELECT l.caller,'LINE',l.caller,l.module,l.path,l.line,1,l.address,0,l.text "
        "FROM linked_lines l JOIN linked_modules m ON m.module=l.module "
        "WHERE ?1>=m.base_address AND ?1<m.base_address+m.size AND l.address<=?1 "
        "ORDER BY l.address DESC,l.line DESC LIMIT 1");
    query.bind_integer(1, address);
    if (!query.step()) {
        return std::nullopt;
    }
    return location_from_statement(query);
}

CodeMapSummary code_map_summary(const fs::path& project_root) {
    Database database = open_code_map(project_root);
    validate_schema(database);
    Statement query(
        database,
        "SELECT entry_module,fingerprint,"
        "(SELECT count(*) FROM linked_modules),"
        "(SELECT count(*) FROM definitions),"
        "(SELECT count(*) FROM references_map) FROM build WHERE id=1");
    if (!query.step()) {
        throw ToolError("EMPTY CODE MAP; RUN ALINK");
    }
    return CodeMapSummary{
        query.text(0),
        query.text(1),
        static_cast<std::size_t>(query.integer(2)),
        static_cast<std::size_t>(query.integer(3)),
        static_cast<std::size_t>(query.integer(4)),
    };
}

}  // namespace action_linux
