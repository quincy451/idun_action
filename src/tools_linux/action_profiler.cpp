#include "action_profiler.hpp"

#include "action_code_map.hpp"
#include "action_help_editor.hpp"
#include "action_target_client.hpp"
#include "action_target_protocol.hpp"

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <string_view>
#include <tuple>

#include <sqlite3.h>

namespace fs = std::filesystem;

namespace action_linux {
namespace {

constexpr int kProfileSchemaVersion = 1;

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

std::uint64_t parse_unsigned(std::string_view input, std::uint64_t maximum) {
    std::string text = trim(input);
    int base = 10;
    if (!text.empty() && text.front() == '$') {
        text.erase(text.begin());
        base = 16;
    } else if (text.size() > 2 && text[0] == '0' &&
               (text[1] == 'x' || text[1] == 'X')) {
        text.erase(0, 2);
        base = 16;
    }
    try {
        std::size_t consumed = 0;
        const unsigned long long value = std::stoull(text, &consumed, base);
        if (consumed != text.size() || value > maximum) {
            throw ToolError("BAD PROFILE NUMBER " + std::string(input));
        }
        return value;
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD PROFILE NUMBER " + std::string(input));
    }
}

class Database {
public:
    explicit Database(const fs::path& path) {
        fs::create_directories(path.parent_path());
        if (sqlite3_open(path.c_str(), &database_) != SQLITE_OK) {
            const std::string message = database_ == nullptr
                ? "open failed"
                : sqlite3_errmsg(database_);
            if (database_ != nullptr) sqlite3_close(database_);
            database_ = nullptr;
            throw ToolError("PROFILE DATABASE OPEN: " + message);
        }
        sqlite3_busy_timeout(database_, 2000);
    }

    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;
    ~Database() { if (database_ != nullptr) sqlite3_close(database_); }
    sqlite3* get() const { return database_; }

    void exec(const std::string& sql) {
        char* error = nullptr;
        if (sqlite3_exec(database_, sql.c_str(), nullptr, nullptr, &error) != SQLITE_OK) {
            const std::string message = error == nullptr ? sqlite3_errmsg(database_) : error;
            sqlite3_free(error);
            throw ToolError("PROFILE DATABASE SQL: " + message);
        }
    }

private:
    sqlite3* database_ = nullptr;
};

class Statement {
public:
    Statement(Database& database, const std::string& sql) : database_(database.get()) {
        if (sqlite3_prepare_v2(database_, sql.c_str(), -1, &statement_, nullptr) != SQLITE_OK) {
            throw ToolError("PROFILE DATABASE QUERY: " + std::string(sqlite3_errmsg(database_)));
        }
    }
    Statement(const Statement&) = delete;
    Statement& operator=(const Statement&) = delete;
    ~Statement() { if (statement_ != nullptr) sqlite3_finalize(statement_); }

    void bind_text(int index, std::string_view value) {
        if (sqlite3_bind_text64(
                statement_, index, value.data(), value.size(), SQLITE_TRANSIENT,
                SQLITE_UTF8) != SQLITE_OK) fail();
    }
    void bind_integer(int index, std::int64_t value) {
        if (sqlite3_bind_int64(statement_, index, value) != SQLITE_OK) fail();
    }
    void bind_null(int index) {
        if (sqlite3_bind_null(statement_, index) != SQLITE_OK) fail();
    }
    bool step() {
        const int status = sqlite3_step(statement_);
        if (status == SQLITE_ROW) return true;
        if (status == SQLITE_DONE) return false;
        fail();
        return false;
    }
    void reset() {
        if (sqlite3_reset(statement_) != SQLITE_OK ||
            sqlite3_clear_bindings(statement_) != SQLITE_OK) fail();
    }
    std::string text(int column) const {
        const unsigned char* value = sqlite3_column_text(statement_, column);
        return value == nullptr ? std::string{} :
            std::string(reinterpret_cast<const char*>(value));
    }
    std::int64_t integer(int column) const {
        return sqlite3_column_int64(statement_, column);
    }

private:
    [[noreturn]] void fail() const {
        throw ToolError("PROFILE DATABASE: " + std::string(sqlite3_errmsg(database_)));
    }
    sqlite3* database_ = nullptr;
    sqlite3_stmt* statement_ = nullptr;
};

fs::path profile_database_path(const fs::path& root) {
    return root / ".action" / "profile.sqlite3";
}

void ensure_schema(Database& database) {
    database.exec(
        "CREATE TABLE IF NOT EXISTS profile_runs("
        "id INTEGER PRIMARY KEY,module TEXT NOT NULL,fingerprint TEXT NOT NULL,"
        "mode TEXT NOT NULL,interval_us INTEGER NOT NULL,started_unix INTEGER NOT NULL,"
        "total_samples INTEGER NOT NULL,unmapped_samples INTEGER NOT NULL)");
    database.exec(
        "CREATE TABLE IF NOT EXISTS profile_samples("
        "run_id INTEGER NOT NULL REFERENCES profile_runs(id) ON DELETE CASCADE,"
        "address INTEGER NOT NULL,count INTEGER NOT NULL,module TEXT,procedure TEXT,"
        "path TEXT,line INTEGER,source_text TEXT,PRIMARY KEY(run_id,address))");
    database.exec("CREATE INDEX IF NOT EXISTS profile_samples_run ON profile_samples(run_id)");
    database.exec("PRAGMA user_version=" + std::to_string(kProfileSchemaVersion));
}

std::map<std::uint16_t, std::uint64_t> load_sample_file(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw ToolError("PROFILE SAMPLE FILE NOT FOUND: " + path.string());
    std::map<std::uint16_t, std::uint64_t> samples;
    std::string line;
    std::size_t line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        const std::size_t comment = line.find('#');
        if (comment != std::string::npos) line.resize(comment);
        std::istringstream words(trim(line));
        std::string address_text;
        std::string count_text;
        if (!(words >> address_text)) continue;
        words >> count_text;
        std::string extra;
        if (words >> extra) {
            throw ToolError("BAD PROFILE SAMPLE LINE " + std::to_string(line_number));
        }
        const auto address = static_cast<std::uint16_t>(
            parse_unsigned(address_text, 0xffff));
        const std::uint64_t count = count_text.empty()
            ? 1
            : parse_unsigned(count_text, 0x7fffffff);
        if (count == 0) {
            throw ToolError("ZERO PROFILE COUNT LINE " + std::to_string(line_number));
        }
        samples[address] += count;
    }
    if (samples.empty()) throw ToolError("NO PROFILE SAMPLES");
    return samples;
}

std::int64_t store_profile(
    const fs::path& root,
    const std::string& module,
    std::string_view mode,
    std::uint32_t interval_us,
    const std::map<std::uint16_t, std::uint64_t>& samples) {
    const CodeMapSummary code_map = code_map_summary(root);
    Database database(profile_database_path(root));
    database.exec("PRAGMA foreign_keys=ON");
    ensure_schema(database);
    database.exec("BEGIN IMMEDIATE");
    try {
        std::uint64_t total = 0;
        std::uint64_t unmapped = 0;
        for (const auto& sample : samples) {
            total += sample.second;
            if (!code_map_address(root, sample.first)) unmapped += sample.second;
        }
        Statement insert_run(
            database,
            "INSERT INTO profile_runs(module,fingerprint,mode,interval_us,started_unix,"
            "total_samples,unmapped_samples) VALUES(?,?,?,?,?,?,?)");
        insert_run.bind_text(1, module);
        insert_run.bind_text(2, code_map.fingerprint);
        insert_run.bind_text(3, mode);
        insert_run.bind_integer(4, interval_us);
        insert_run.bind_integer(
            5,
            std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        insert_run.bind_integer(6, static_cast<std::int64_t>(total));
        insert_run.bind_integer(7, static_cast<std::int64_t>(unmapped));
        insert_run.step();
        const std::int64_t run_id = sqlite3_last_insert_rowid(database.get());

        Statement insert_sample(
            database,
            "INSERT INTO profile_samples(run_id,address,count,module,procedure,path,line,"
            "source_text) VALUES(?,?,?,?,?,?,?,?)");
        for (const auto& sample : samples) {
            const auto location = code_map_address(root, sample.first);
            insert_sample.bind_integer(1, run_id);
            insert_sample.bind_integer(2, sample.first);
            insert_sample.bind_integer(3, static_cast<std::int64_t>(sample.second));
            if (location) {
                insert_sample.bind_text(4, location->module);
                insert_sample.bind_text(5, location->caller);
                insert_sample.bind_text(6, location->path);
                insert_sample.bind_integer(7, location->line);
                insert_sample.bind_text(8, location->signature);
            } else {
                for (int column = 4; column <= 8; ++column) insert_sample.bind_null(column);
            }
            insert_sample.step();
            insert_sample.reset();
        }
        database.exec("COMMIT");
        return run_id;
    } catch (...) {
        try { database.exec("ROLLBACK"); } catch (...) {}
        throw;
    }
}

struct Aggregate {
    std::string label;
    std::uint64_t count = 0;
};

void print_aggregate(
    std::string_view kind,
    const Aggregate& aggregate,
    std::uint64_t total,
    std::uint64_t interval_us) {
    const double percentage = total == 0
        ? 0.0
        : static_cast<double>(aggregate.count) * 100.0 / static_cast<double>(total);
    std::cout << kind << " " << aggregate.label
              << " SAMPLES " << aggregate.count
              << " TIME_US " << aggregate.count * interval_us
              << " PERCENT " << std::fixed << std::setprecision(2) << percentage << "\n";
}

void report_profile(const fs::path& root, const std::string& module, std::optional<std::int64_t> id) {
    Database database(profile_database_path(root));
    ensure_schema(database);
    if (!id) {
        Statement latest(
            database,
            "SELECT id FROM profile_runs WHERE module=? ORDER BY id DESC LIMIT 1");
        latest.bind_text(1, module);
        if (!latest.step()) throw ToolError("NO PROFILE RUN");
        id = latest.integer(0);
    }
    Statement run(
        database,
        "SELECT module,fingerprint,mode,interval_us,total_samples,unmapped_samples "
        "FROM profile_runs WHERE id=? AND module=?");
    run.bind_integer(1, *id);
    run.bind_text(2, module);
    if (!run.step()) throw ToolError("NO PROFILE RUN");
    const std::uint64_t interval = static_cast<std::uint64_t>(run.integer(3));
    const std::uint64_t total = static_cast<std::uint64_t>(run.integer(4));
    const std::uint64_t unmapped = static_cast<std::uint64_t>(run.integer(5));
    std::cout << "ACTPROF RUN " << *id << "\n"
              << "MODULE " << run.text(0) << "\n"
              << "FINGERPRINT " << run.text(1) << "\n"
              << "MODE " << run.text(2) << "\n"
              << "INTERVAL_US " << interval << "\n"
              << "SAMPLES " << total << "\n"
              << "TOTAL_TIME_US " << total * interval << "\n";
    print_aggregate("PROCESS", Aggregate{module, total}, total, interval);

    Statement samples(
        database,
        "SELECT count,coalesce(procedure,''),coalesce(path,''),coalesce(line,0),"
        "coalesce(source_text,''),address FROM profile_samples WHERE run_id=?");
    samples.bind_integer(1, *id);
    std::map<std::string, std::uint64_t> functions;
    std::map<std::tuple<std::string, std::int64_t, std::string>, std::uint64_t> statements;
    while (samples.step()) {
        const std::uint64_t count = static_cast<std::uint64_t>(samples.integer(0));
        const std::string function = samples.text(1);
        const std::string path = samples.text(2);
        if (!function.empty()) functions[function] += count;
        if (!path.empty()) {
            statements[{path, samples.integer(3), samples.text(4)}] += count;
        }
    }
    std::vector<Aggregate> function_rows;
    for (const auto& item : functions) function_rows.push_back({item.first, item.second});
    std::sort(function_rows.begin(), function_rows.end(), [](const auto& lhs, const auto& rhs) {
        return lhs.count != rhs.count ? lhs.count > rhs.count : lhs.label < rhs.label;
    });
    for (const Aggregate& aggregate : function_rows) {
        print_aggregate("FUNCTION", aggregate, total, interval);
    }
    std::vector<Aggregate> statement_rows;
    for (const auto& item : statements) {
        const auto& [path, line, text] = item.first;
        statement_rows.push_back({
            path + ":" + std::to_string(line) + (text.empty() ? "" : " " + trim(text)),
            item.second,
        });
    }
    std::sort(statement_rows.begin(), statement_rows.end(), [](const auto& lhs, const auto& rhs) {
        return lhs.count != rhs.count ? lhs.count > rhs.count : lhs.label < rhs.label;
    });
    for (const Aggregate& aggregate : statement_rows) {
        print_aggregate("STATEMENT", aggregate, total, interval);
    }
    if (unmapped != 0) {
        print_aggregate("UNMAPPED", Aggregate{"addresses", unmapped}, total, interval);
    }
}

std::int64_t collect_live_profile(
    const fs::path& root,
    const std::string& module,
    std::uint64_t seconds) {
    target::IdunTargetSession session(root, module);
    const target::HelloInfo hello = session.hello();
    if ((hello.capabilities & target::PcSampling) == 0) {
        throw ToolError("TARGET DOES NOT SUPPORT PC SAMPLING");
    }
    session.configure_sampling(true);
    session.run();
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(seconds);
    bool running = true;
    bool target_finished = false;
    std::map<std::uint16_t, std::uint64_t> counts;
    std::uint32_t interval_us = 16667;
    const auto drain_samples = [&]() {
        while (true) {
            const std::vector<std::uint16_t> samples =
                session.read_samples(&interval_us);
            for (const std::uint16_t address : samples) ++counts[address];
            if (samples.size() < 100) break;
        }
    };

    // The resident service deliberately has a small fixed sample buffer. Halt
    // and drain once per second so longer profiles cover their full requested
    // duration instead of retaining only the first 100 PCs.
    while (!target_finished && std::chrono::steady_clock::now() < deadline) {
        const auto batch_deadline = std::min(
            deadline,
            std::chrono::steady_clock::now() + std::chrono::seconds(1));
        while (std::chrono::steady_clock::now() < batch_deadline) {
            const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
                batch_deadline - std::chrono::steady_clock::now()).count();
            if (remaining <= 0) break;
            const auto event = session.receive_event(static_cast<int>(
                std::min<std::int64_t>(remaining, 250)));
            if (event &&
                (event->type == target::MessageType::BreakpointHit ||
                 event->type == target::MessageType::TargetExit ||
                 event->type == target::MessageType::TargetFault)) {
                running = false;
                target_finished = true;
                break;
            }
        }
        if (running) {
            session.halt();
            running = false;
        }
        drain_samples();
        const auto profile_remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
            deadline - std::chrono::steady_clock::now()).count();
        if (!target_finished && profile_remaining > 0) {
            session.run();
            running = true;
        }
    }
    if (running) {
        session.halt();
    }
    drain_samples();
    session.configure_sampling(false);
    if (counts.empty()) throw ToolError("TARGET RETURNED NO PROFILE SAMPLES");
    return store_profile(root, module, "LIVE_PC_SAMPLE", interval_us, counts);
}

}  // namespace

int command_actprof(const std::vector<std::string>& args) {
    if (args.empty()) throw ToolError("NO NAME");
    const fs::path root = fs::current_path();
    const std::string module = upper_ascii(fs::path(args.front()).stem().string());
    if (!fs::is_regular_file(root / "BIN" / (module + ".PRG")) ||
        !fs::is_regular_file(code_map_path(root))) {
        throw ToolError("ACTPROF NEEDS ALINK BUILD");
    }
    const std::string mode = args.size() >= 2 ? upper_ascii(args[1]) : "REPORT";
    if (mode == "IMPORT") {
        if (args.size() < 3 || args.size() > 4) throw ToolError("BAD PROFILE COMMAND");
        const std::uint32_t interval = args.size() == 4
            ? static_cast<std::uint32_t>(parse_unsigned(args[3], 0xffffffffULL))
            : 16666;
        if (interval == 0) throw ToolError("BAD PROFILE INTERVAL");
        const std::int64_t id = store_profile(
            root, module, "IMPORTED_PC_SAMPLE", interval, load_sample_file(args[2]));
        std::cout << "ACTPROF IMPORTED " << id << "\n";
        report_profile(root, module, id);
        return 0;
    }
    if (mode == "REPORT") {
        if (args.size() > 3) throw ToolError("BAD PROFILE COMMAND");
        const std::optional<std::int64_t> id = args.size() == 3
            ? std::optional<std::int64_t>(parse_unsigned(args[2], 0x7fffffff))
            : std::nullopt;
        report_profile(root, module, id);
        return 0;
    }
    if (mode == "LIVE") {
        if (args.size() > 3) throw ToolError("BAD PROFILE COMMAND");
        const std::uint64_t seconds = args.size() == 3
            ? parse_unsigned(args[2], 3600)
            : 10;
        if (seconds == 0) throw ToolError("BAD PROFILE DURATION");
        std::cout << "ACTPROF COLLECTING " << seconds << " SECONDS\n";
        const std::int64_t id = collect_live_profile(root, module, seconds);
        report_profile(root, module, id);
        return 0;
    }
    throw ToolError("BAD PROFILE COMMAND");
}

}  // namespace action_linux
