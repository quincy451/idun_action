#include "action_graphics_editor.hpp"

#include "action_help_editor.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>
#include <vector>

namespace action_linux {
namespace {

namespace fs = std::filesystem;

std::string upper_ascii(std::string_view text) {
    std::string result(text);
    std::transform(result.begin(), result.end(), result.begin(), [](unsigned char ch) {
        return static_cast<char>(std::toupper(ch));
    });
    return result;
}

std::size_t parse_size(std::string_view text, std::string_view label) {
    try {
        std::size_t consumed = 0;
        const unsigned long value = std::stoul(std::string(text), &consumed, 0);
        if (consumed != text.size()) {
            throw ToolError("BAD " + std::string(label));
        }
        return static_cast<std::size_t>(value);
    } catch (const ToolError&) {
        throw;
    } catch (const std::exception&) {
        throw ToolError("BAD " + std::string(label));
    }
}

std::vector<std::uint8_t> read_bytes(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw ToolError("GRAPHICS LOAD FAIL: " + path.generic_string());
    }
    return std::vector<std::uint8_t>(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

void atomic_write(const fs::path& path, const std::vector<std::uint8_t>& bytes) {
    if (!path.parent_path().empty()) {
        std::error_code error;
        fs::create_directories(path.parent_path(), error);
        if (error) {
            throw ToolError("GRAPHICS DIRECTORY FAIL: " + path.parent_path().generic_string());
        }
    }
    const fs::path temporary = path.parent_path() /
        ("." + path.filename().string() + ".graphics-" + std::to_string(::getpid()));
    std::error_code error;
    try {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw ToolError("GRAPHICS SAVE FAIL: " + path.generic_string());
        }
        output.write(
            reinterpret_cast<const char*>(bytes.data()),
            static_cast<std::streamsize>(bytes.size()));
        output.close();
        if (!output) {
            throw ToolError("GRAPHICS SAVE FAIL: " + path.generic_string());
        }
        fs::rename(temporary, path);
    } catch (...) {
        fs::remove(temporary, error);
        throw;
    }
}

bool terminal_available() {
    return ::isatty(STDIN_FILENO) != 0 && ::isatty(STDOUT_FILENO) != 0;
}

void write_all(std::string_view text) {
    std::size_t offset = 0;
    while (offset < text.size()) {
        const ssize_t count = ::write(
            STDOUT_FILENO, text.data() + offset, text.size() - offset);
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            throw ToolError("GRAPHICS TERMINAL WRITE: " + std::string(std::strerror(errno)));
        }
        offset += static_cast<std::size_t>(count);
    }
}

class TerminalSession {
public:
    TerminalSession() {
        if (!terminal_available() || ::tcgetattr(STDIN_FILENO, &original_) != 0) {
            throw ToolError("GRAPHICS TUI REQUIRES A TERMINAL");
        }
        termios raw = original_;
        raw.c_iflag &= static_cast<tcflag_t>(~(BRKINT | ICRNL | INPCK | ISTRIP | IXON));
        raw.c_oflag &= static_cast<tcflag_t>(~OPOST);
        raw.c_cflag |= CS8;
        raw.c_lflag &= static_cast<tcflag_t>(~(ECHO | ICANON | IEXTEN | ISIG));
        raw.c_cc[VMIN] = 1;
        raw.c_cc[VTIME] = 0;
        if (::tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) != 0) {
            throw ToolError("GRAPHICS TERMINAL SETUP");
        }
        active_ = true;
        write_all("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H");
    }

    ~TerminalSession() {
        if (active_) {
            const char restore[] = "\x1b[0m\x1b[?25h\x1b[?1049l";
            const ssize_t write_status =
                ::write(STDOUT_FILENO, restore, sizeof(restore) - 1);
            (void)write_status;
            (void)::tcsetattr(STDIN_FILENO, TCSAFLUSH, &original_);
        }
    }

    TerminalSession(const TerminalSession&) = delete;
    TerminalSession& operator=(const TerminalSession&) = delete;

private:
    termios original_{};
    bool active_ = false;
};

struct TerminalSize {
    std::size_t rows = 24;
    std::size_t columns = 80;
};

TerminalSize terminal_size() {
    winsize size{};
    if (::ioctl(STDOUT_FILENO, TIOCGWINSZ, &size) == 0) {
        return {
            std::max<std::size_t>(10, size.ws_row),
            std::max<std::size_t>(40, size.ws_col),
        };
    }
    return {};
}

enum class KeyKind { Character, Up, Down, Left, Right, Save, Quit, Unknown };

struct Key {
    KeyKind kind = KeyKind::Unknown;
    char character = '\0';
};

char read_byte() {
    char value = '\0';
    while (true) {
        const ssize_t count = ::read(STDIN_FILENO, &value, 1);
        if (count == 1) {
            return value;
        }
        if (count == 0) {
            return 0x11;
        }
        if (errno != EINTR) {
            throw ToolError("GRAPHICS TERMINAL READ");
        }
    }
}

Key read_key() {
    const unsigned char ch = static_cast<unsigned char>(read_byte());
    if (ch == 0x13) return {KeyKind::Save, '\0'};
    if (ch == 0x11) return {KeyKind::Quit, '\0'};
    if (ch != 0x1B) return {KeyKind::Character, static_cast<char>(ch)};
    const char first = read_byte();
    if (first != '[' && first != 'O') return {KeyKind::Unknown, '\0'};
    const char second = read_byte();
    if (second == 'A') return {KeyKind::Up, '\0'};
    if (second == 'B') return {KeyKind::Down, '\0'};
    if (second == 'C') return {KeyKind::Right, '\0'};
    if (second == 'D') return {KeyKind::Left, '\0'};
    return {KeyKind::Unknown, '\0'};
}

struct SpriteAsset {
    bool multicolor = false;
    std::uint8_t color = 1;
    std::uint8_t multicolor1 = 7;
    std::uint8_t multicolor2 = 10;
    std::array<std::uint8_t, 63> data{};

    std::size_t width() const { return multicolor ? 12 : 24; }
    std::size_t height() const { return 21; }

    std::uint8_t pixel(std::size_t x, std::size_t y) const {
        const std::size_t offset = y * 3 + (multicolor ? x / 4 : x / 8);
        if (multicolor) {
            const unsigned shift = static_cast<unsigned>(6 - (x % 4) * 2);
            return static_cast<std::uint8_t>((data[offset] >> shift) & 3);
        }
        return static_cast<std::uint8_t>((data[offset] >> (7 - x % 8)) & 1);
    }

    void set_pixel(std::size_t x, std::size_t y, std::uint8_t value) {
        const std::size_t offset = y * 3 + (multicolor ? x / 4 : x / 8);
        if (multicolor) {
            const unsigned shift = static_cast<unsigned>(6 - (x % 4) * 2);
            const std::uint8_t mask = static_cast<std::uint8_t>(3U << shift);
            data[offset] = static_cast<std::uint8_t>(
                (data[offset] & static_cast<std::uint8_t>(~mask)) |
                ((value & 3U) << shift));
        } else {
            const std::uint8_t mask = static_cast<std::uint8_t>(0x80U >> (x % 8));
            if ((value & 1U) != 0) {
                data[offset] |= mask;
            } else {
                data[offset] &= static_cast<std::uint8_t>(~mask);
            }
        }
    }
};

SpriteAsset load_sprite(const fs::path& path, bool missing_multicolor = false) {
    std::error_code error;
    if (!fs::is_regular_file(path, error) || error) {
        SpriteAsset fresh;
        fresh.multicolor = missing_multicolor;
        return fresh;
    }
    const std::vector<std::uint8_t> bytes = read_bytes(path);
    SpriteAsset result;
    if (bytes.size() == 71 &&
        std::equal(bytes.begin(), bytes.begin() + 4, "ASP1")) {
        result.multicolor = bytes[4] != 0;
        result.color = bytes[5] & 15;
        result.multicolor1 = bytes[6] & 15;
        result.multicolor2 = bytes[7] & 15;
        std::copy(bytes.begin() + 8, bytes.end(), result.data.begin());
        return result;
    }
    if (bytes.size() != 63 && bytes.size() != 64) {
        throw ToolError("BAD SPRITE FILE: expected ASP1, 63, or 64 bytes");
    }
    std::copy(bytes.begin(), bytes.begin() + 63, result.data.begin());
    if (bytes.size() == 64) {
        result.multicolor = (bytes[63] & 0x80) != 0;
        result.color = bytes[63] & 15;
    }
    return result;
}

void save_sprite(const fs::path& path, const SpriteAsset& sprite) {
    std::vector<std::uint8_t> bytes{'A', 'S', 'P', '1'};
    bytes.push_back(sprite.multicolor ? 1 : 0);
    bytes.push_back(sprite.color & 15);
    bytes.push_back(sprite.multicolor1 & 15);
    bytes.push_back(sprite.multicolor2 & 15);
    bytes.insert(bytes.end(), sprite.data.begin(), sprite.data.end());
    atomic_write(path, bytes);
}

struct BitmapAsset {
    bool multicolor = false;
    std::uint8_t foreground = 1;
    std::uint8_t background = 0;
    std::uint16_t width = 32;
    std::uint16_t height = 32;
    std::vector<std::uint8_t> data;

    std::size_t stride() const {
        return (static_cast<std::size_t>(width) * (multicolor ? 2U : 1U) + 7U) / 8U;
    }

    void resize_storage() { data.assign(stride() * height, 0); }

    std::uint8_t pixel(std::size_t x, std::size_t y) const {
        const std::size_t bit = x * (multicolor ? 2U : 1U);
        const std::size_t offset = y * stride() + bit / 8;
        if (multicolor) {
            return static_cast<std::uint8_t>((data[offset] >> (6 - bit % 8)) & 3);
        }
        return static_cast<std::uint8_t>((data[offset] >> (7 - bit % 8)) & 1);
    }

    void set_pixel(std::size_t x, std::size_t y, std::uint8_t value) {
        const std::size_t bit = x * (multicolor ? 2U : 1U);
        const std::size_t offset = y * stride() + bit / 8;
        if (multicolor) {
            const unsigned shift = static_cast<unsigned>(6 - bit % 8);
            const std::uint8_t mask = static_cast<std::uint8_t>(3U << shift);
            data[offset] = static_cast<std::uint8_t>(
                (data[offset] & static_cast<std::uint8_t>(~mask)) |
                ((value & 3U) << shift));
        } else {
            const std::uint8_t mask = static_cast<std::uint8_t>(0x80U >> (bit % 8));
            if ((value & 1U) != 0) {
                data[offset] |= mask;
            } else {
                data[offset] &= static_cast<std::uint8_t>(~mask);
            }
        }
    }
};

BitmapAsset new_bitmap(std::size_t width, std::size_t height, bool multicolor) {
    if (width == 0 || width > (multicolor ? 160U : 320U) ||
        height == 0 || height > 200) {
        throw ToolError("BITMAP DIMENSIONS: hires 1..320x200, multicolor 1..160x200");
    }
    BitmapAsset result;
    result.multicolor = multicolor;
    result.width = static_cast<std::uint16_t>(width);
    result.height = static_cast<std::uint16_t>(height);
    result.resize_storage();
    return result;
}

BitmapAsset load_bitmap(const fs::path& path) {
    const std::vector<std::uint8_t> bytes = read_bytes(path);
    if (bytes.size() < 16 ||
        !std::equal(bytes.begin(), bytes.begin() + 4, "ABM1")) {
        throw ToolError("BAD BITMAP FILE: expected ABM1");
    }
    const auto word = [&](std::size_t offset) {
        return static_cast<std::uint16_t>(
            bytes[offset] | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8));
    };
    BitmapAsset result = new_bitmap(word(8), word(10), bytes[4] != 0);
    result.foreground = bytes[5] & 15;
    result.background = bytes[6] & 15;
    const std::size_t stride = word(12);
    const std::size_t payload = word(14);
    if (stride != result.stride() || payload != result.data.size() ||
        bytes.size() != 16 + payload) {
        throw ToolError("BAD BITMAP FILE: dimensions/payload mismatch");
    }
    std::copy(bytes.begin() + 16, bytes.end(), result.data.begin());
    return result;
}

void save_bitmap(const fs::path& path, const BitmapAsset& bitmap) {
    const std::size_t stride = bitmap.stride();
    const std::size_t payload = bitmap.data.size();
    if (stride > 0xFFFF || payload > 0xFFFF) {
        throw ToolError("BITMAP FILE TOO LARGE");
    }
    std::vector<std::uint8_t> bytes{
        'A', 'B', 'M', '1',
        static_cast<std::uint8_t>(bitmap.multicolor ? 1 : 0),
        static_cast<std::uint8_t>(bitmap.foreground & 15),
        static_cast<std::uint8_t>(bitmap.background & 15),
        0,
        static_cast<std::uint8_t>(bitmap.width & 0xFF),
        static_cast<std::uint8_t>(bitmap.width >> 8),
        static_cast<std::uint8_t>(bitmap.height & 0xFF),
        static_cast<std::uint8_t>(bitmap.height >> 8),
        static_cast<std::uint8_t>(stride & 0xFF),
        static_cast<std::uint8_t>(stride >> 8),
        static_cast<std::uint8_t>(payload & 0xFF),
        static_cast<std::uint8_t>(payload >> 8),
    };
    bytes.insert(bytes.end(), bitmap.data.begin(), bitmap.data.end());
    atomic_write(path, bytes);
}

std::size_t asset_width(const SpriteAsset& asset) { return asset.width(); }
std::size_t asset_height(const SpriteAsset& asset) { return asset.height(); }
std::size_t asset_width(const BitmapAsset& asset) { return asset.width; }
std::size_t asset_height(const BitmapAsset& asset) { return asset.height; }

template <typename Asset, typename Save>
int run_pixel_editor(
    const fs::path& path,
    Asset& asset,
    Save save,
    std::string_view title) {
    TerminalSession terminal;
    std::size_t x = 0;
    std::size_t y = 0;
    bool dirty = false;
    bool quit_armed = false;
    std::string status;
    while (true) {
        const TerminalSize screen = terminal_size();
        const std::size_t width = asset_width(asset);
        const std::size_t height = asset_height(asset);
        const std::size_t cell_width = width <= 40 ? 2 : 1;
        const std::size_t visible_columns = std::max<std::size_t>(1, screen.columns / cell_width);
        const std::size_t visible_rows = std::max<std::size_t>(1, screen.rows - 4);
        const std::size_t left = x >= visible_columns ? x - visible_columns + 1 : 0;
        const std::size_t top = y >= visible_rows ? y - visible_rows + 1 : 0;
        std::ostringstream out;
        out << "\x1b[H\x1b[2J" << title << "  " << path.generic_string()
            << "  " << width << "x" << height
            << (asset.multicolor ? " multicolor" : " hires")
            << (dirty ? "  *modified*" : "") << "\r\n";
        out << "Arrows move  Space cycles pixel  0-3 paint  C clears  Ctrl-S saves  Ctrl-Q exits\r\n";
        static const std::array<char, 4> glyph{'.', '#', 'o', '@'};
        for (std::size_t row = 0; row < visible_rows && top + row < height; ++row) {
            for (std::size_t column = 0;
                 column < visible_columns && left + column < width;
                 ++column) {
                const std::size_t px = left + column;
                const std::size_t py = top + row;
                const char mark = glyph[asset.pixel(px, py) & 3];
                if (px == x && py == y) out << "\x1b[7m";
                out << mark;
                if (cell_width == 2) out << mark;
                if (px == x && py == y) out << "\x1b[27m";
            }
            out << "\x1b[K\r\n";
        }
        out << "\x1b[" << screen.rows << ";1H\x1b[Kx=" << x << " y=" << y
            << " value=" << static_cast<unsigned>(asset.pixel(x, y));
        if (!status.empty()) out << "  " << status;
        write_all(out.str());

        const Key key = read_key();
        if (key.kind == KeyKind::Left && x > 0) --x;
        else if (key.kind == KeyKind::Right && x + 1 < width) ++x;
        else if (key.kind == KeyKind::Up && y > 0) --y;
        else if (key.kind == KeyKind::Down && y + 1 < height) ++y;
        else if (key.kind == KeyKind::Save) {
            save(path, asset);
            dirty = false;
            quit_armed = false;
            status = "saved";
        } else if (key.kind == KeyKind::Quit) {
            if (!dirty || quit_armed) return 0;
            quit_armed = true;
            status = "unsaved; Ctrl-Q again discards";
        } else if (key.kind == KeyKind::Character) {
            const unsigned limit = asset.multicolor ? 4U : 2U;
            if (key.character == ' ') {
                asset.set_pixel(x, y, static_cast<std::uint8_t>(
                    (asset.pixel(x, y) + 1) % limit));
                dirty = true;
            } else if (key.character >= '0' &&
                       key.character < static_cast<char>('0' + limit)) {
                asset.set_pixel(x, y, static_cast<std::uint8_t>(key.character - '0'));
                dirty = true;
            } else if (key.character == 'c' || key.character == 'C') {
                std::fill(asset.data.begin(), asset.data.end(), 0);
                dirty = true;
                status = "cleared";
            }
            if (dirty) {
                quit_armed = false;
                if (status != "cleared") status.clear();
            }
        }
    }
}

void print_sprite(const SpriteAsset& sprite) {
    static const std::array<char, 4> glyph{'.', '#', 'o', '@'};
    for (std::size_t y = 0; y < sprite.height(); ++y) {
        for (std::size_t x = 0; x < sprite.width(); ++x) {
            std::cout << glyph[sprite.pixel(x, y) & 3];
        }
        std::cout << '\n';
    }
}

void print_bitmap(const BitmapAsset& bitmap) {
    static const std::array<char, 4> glyph{'.', '#', 'o', '@'};
    for (std::size_t y = 0; y < bitmap.height; ++y) {
        for (std::size_t x = 0; x < bitmap.width; ++x) {
            std::cout << glyph[bitmap.pixel(x, y) & 3];
        }
        std::cout << '\n';
    }
}

}  // namespace

int command_actsprite(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("ACTSPRITE NO FILE");
    }
    const fs::path path = args[0];
    const std::string mode = args.size() > 1 ? upper_ascii(args[1]) : "";
    const bool requested_multicolor =
        path.extension() == ".msp" || path.extension() == ".MSP" ||
        (mode == "TUI" && args.size() > 2 &&
         upper_ascii(args[2]) == "MULTICOLOR");
    SpriteAsset sprite = load_sprite(path, requested_multicolor);
    if (mode == "NEW") {
        sprite = SpriteAsset{};
        sprite.multicolor = args.size() > 2 && upper_ascii(args[2]) == "MULTICOLOR";
        save_sprite(path, sprite);
        std::cout << "ACTSPRITE OK created " << path.generic_string() << "\n";
        return 0;
    }
    if (mode == "SET") {
        if (args.size() < 4 || args.size() > 5) throw ToolError("BAD ACTSPRITE SET");
        const std::size_t x = parse_size(args[2], "SPRITE X");
        const std::size_t y = parse_size(args[3], "SPRITE Y");
        if (x >= sprite.width() || y >= sprite.height()) throw ToolError("SPRITE PIXEL RANGE");
        const std::uint8_t value = static_cast<std::uint8_t>(
            args.size() == 5 ? parse_size(args[4], "SPRITE PIXEL") : 1);
        if (value >= (sprite.multicolor ? 4 : 2)) throw ToolError("SPRITE PIXEL RANGE");
        sprite.set_pixel(x, y, value);
        save_sprite(path, sprite);
        std::cout << "ACTSPRITE OK\n";
        return 0;
    }
    if (mode == "CLEAR") {
        sprite.data.fill(0);
        save_sprite(path, sprite);
        std::cout << "ACTSPRITE OK\n";
        return 0;
    }
    if (mode == "COLOR") {
        if (args.size() != 3) throw ToolError("BAD ACTSPRITE COLOR");
        const std::size_t color = parse_size(args[2], "SPRITE COLOR");
        if (color > 15) throw ToolError("SPRITE COLOR RANGE");
        sprite.color = static_cast<std::uint8_t>(color);
        save_sprite(path, sprite);
        std::cout << "ACTSPRITE OK\n";
        return 0;
    }
    if (mode == "PRINT") {
        print_sprite(sprite);
        return 0;
    }
    if (mode == "INFO" || (!terminal_available() && mode.empty())) {
        std::cout << "ACTSPRITE " << path.generic_string() << " "
                  << sprite.width() << "x" << sprite.height() << " "
                  << (sprite.multicolor ? "multicolor" : "hires")
                  << " color=" << static_cast<unsigned>(sprite.color) << "\n";
        return 0;
    }
    if (!mode.empty() && mode != "TUI") throw ToolError("BAD ACTSPRITE COMMAND");
    return run_pixel_editor(path, sprite, save_sprite, "ACTSPRITE");
}

int command_actbitmap(const std::vector<std::string>& args) {
    if (args.empty()) {
        throw ToolError("ACTBITMAP NO FILE");
    }
    const fs::path path = args[0];
    const std::string mode = args.size() > 1 ? upper_ascii(args[1]) : "";
    const bool requested_multicolor =
        mode == "TUI" && args.size() > 2 &&
        upper_ascii(args[2]) == "MULTICOLOR";
    std::error_code error;
    const bool exists = fs::is_regular_file(path, error) && !error;
    if (mode == "NEW") {
        if (args.size() < 4 || args.size() > 5) throw ToolError("BAD ACTBITMAP NEW");
        BitmapAsset bitmap = new_bitmap(
            parse_size(args[2], "BITMAP WIDTH"),
            parse_size(args[3], "BITMAP HEIGHT"),
            args.size() == 5 && upper_ascii(args[4]) == "MULTICOLOR");
        save_bitmap(path, bitmap);
        std::cout << "ACTBITMAP OK created " << path.generic_string() << "\n";
        return 0;
    }
    if (!exists) {
        if (mode == "TUI" || (mode.empty() && terminal_available())) {
            BitmapAsset bitmap = new_bitmap(32, 32, requested_multicolor);
            return run_pixel_editor(path, bitmap, save_bitmap, "ACTBITMAP");
        }
        throw ToolError("ACTBITMAP NO FILE; use: actbitmap FILE new WIDTH HEIGHT [multicolor]");
    }
    BitmapAsset bitmap = load_bitmap(path);
    if (mode == "SET") {
        if (args.size() < 4 || args.size() > 5) throw ToolError("BAD ACTBITMAP SET");
        const std::size_t x = parse_size(args[2], "BITMAP X");
        const std::size_t y = parse_size(args[3], "BITMAP Y");
        if (x >= bitmap.width || y >= bitmap.height) throw ToolError("BITMAP PIXEL RANGE");
        const std::uint8_t value = static_cast<std::uint8_t>(
            args.size() == 5 ? parse_size(args[4], "BITMAP PIXEL") : 1);
        if (value >= (bitmap.multicolor ? 4 : 2)) throw ToolError("BITMAP PIXEL RANGE");
        bitmap.set_pixel(x, y, value);
        save_bitmap(path, bitmap);
        std::cout << "ACTBITMAP OK\n";
        return 0;
    }
    if (mode == "CLEAR") {
        std::fill(bitmap.data.begin(), bitmap.data.end(), 0);
        save_bitmap(path, bitmap);
        std::cout << "ACTBITMAP OK\n";
        return 0;
    }
    if (mode == "PRINT") {
        print_bitmap(bitmap);
        return 0;
    }
    if (mode == "INFO" || (!terminal_available() && mode.empty())) {
        std::cout << "ACTBITMAP " << path.generic_string() << " "
                  << bitmap.width << "x" << bitmap.height << " "
                  << (bitmap.multicolor ? "multicolor" : "hires")
                  << " bytes=" << bitmap.data.size() << "\n";
        return 0;
    }
    if (!mode.empty() && mode != "TUI") throw ToolError("BAD ACTBITMAP COMMAND");
    return run_pixel_editor(path, bitmap, save_bitmap, "ACTBITMAP");
}

}  // namespace action_linux
