#include <stdbool.h>
#include <cpm.h>
#include <stdint.h>
#include <string.h>

#define MAX_SOURCE_BYTES 4096
#define MAX_LINES 256
#define MAX_ACTIONS 128
#define MAX_TEXT_POOL 2048
#define MAX_AVM_BYTES 4096
#define OPCODE_CALLN 0x49
#define OPCODE_SETP16 0x61
#define INTR_PRINT 0xff00
#define INTR_PRINTE 0xff10
#define INTR_EXIT 0xff20
#define AVM_HEADER_SIZE 10

typedef struct {
    uint16_t text_offset;
    bool newline;
} PrintAction;

typedef struct {
    uint16_t line_no;
    char* text;
} SourceLine;

static char source_buffer[MAX_SOURCE_BYTES];
static SourceLine lines[MAX_LINES];
static uint16_t line_count;
static PrintAction actions[MAX_ACTIONS];
static uint16_t action_count;
static char text_pool[MAX_TEXT_POOL];
static uint16_t text_pool_len;
static uint8_t avm_buffer[MAX_AVM_BYTES];

static void print_cstr(const char* s)
{
    while (*s)
        cpm_conout((uint8_t)*s++);
}

static void print_decimal(uint16_t value)
{
    char digits[6];
    uint8_t len = 0;
    if (value == 0)
    {
        cpm_conout('0');
        return;
    }
    while (value && (len < sizeof(digits)))
    {
        digits[len++] = (char)('0' + (value % 10));
        value /= 10;
    }
    while (len)
        cpm_conout((uint8_t)digits[--len]);
}

static void crlf(void)
{
    print_cstr("\r\n");
}

static void fatal_at(uint16_t line_no, const char* message)
{
    print_cstr("actc:");
    if (line_no)
    {
        cpm_conout(' ');
        print_cstr("line ");
        print_decimal(line_no);
        cpm_conout(':');
    }
    cpm_conout(' ');
    print_cstr(message);
    crlf();
    cpm_warmboot();
}

static void fatal(const char* message)
{
    fatal_at(0, message);
}

static char* trim(char* text)
{
    while ((*text == ' ') || (*text == '\t'))
        text++;
    char* end = text + strlen(text);
    while ((end > text) && ((end[-1] == ' ') || (end[-1] == '\t') || (end[-1] == '\r') || (end[-1] == '\n')))
        *--end = 0;
    return text;
}

static void parse_filename(FCB* fcb, const char* name)
{
    memset(fcb, 0, sizeof(*fcb));
    cpm_set_dma(fcb);
    if (!cpm_parse_filename(name))
        fatal("bad filename");
}

static bool fcb_has_filename(const FCB* fcb)
{
    return fcb->f[0] != ' ';
}

static void source_filename_from_primary_fcb(char* out)
{
    if (!fcb_has_filename(&cpm_fcb))
    {
        strcpy(out, "main.act");
        return;
    }

    uint8_t pos = 0;
    for (uint8_t i = 0; i < 8; i++)
    {
        uint8_t ch = cpm_fcb.f[i] & 0x7f;
        if (ch == ' ')
            break;
        if ((ch >= 'A') && (ch <= 'Z'))
            ch = (uint8_t)(ch - 'A' + 'a');
        out[pos++] = (char)ch;
    }
    if (cpm_fcb.f[8] != ' ')
    {
        out[pos++] = '.';
        for (uint8_t i = 8; i < 11; i++)
        {
            uint8_t ch = cpm_fcb.f[i] & 0x7f;
            if (ch == ' ')
                break;
            if ((ch >= 'A') && (ch <= 'Z'))
                ch = (uint8_t)(ch - 'A' + 'a');
            out[pos++] = (char)ch;
        }
    }
    out[pos] = 0;
}

static void output_filename_from_source(const char* source_name, char* out)
{
    uint8_t stem_len = 0;
    while (source_name[stem_len] && (source_name[stem_len] != '.') && (stem_len < 8))
    {
        out[stem_len] = source_name[stem_len];
        stem_len++;
    }
    out[stem_len] = 0;
    strcat(out, ".avm");
}

static void read_source_file(const char* filename)
{
    FCB fcb;
    parse_filename(&fcb, filename);
    fcb.ex = 0;
    fcb.cr = 0;
    if (cpm_open_file(&fcb) != CPME_OK)
        fatal("cannot open source");

    uint16_t pos = 0;
    for (;;)
    {
        cpm_set_dma(cpm_default_dma);
        uint8_t rc = cpm_read_sequential(&fcb);
        if (rc != CPME_OK)
            break;
        for (uint8_t i = 0; i < 128; i++)
        {
            uint8_t ch = cpm_default_dma[i];
            if ((ch == 0) || (ch == 0x1a))
            {
                source_buffer[pos] = 0;
                return;
            }
            if (pos + 1 >= MAX_SOURCE_BYTES)
                fatal("source too large");
            source_buffer[pos++] = (char)ch;
        }
    }
    source_buffer[pos] = 0;
}

static void preprocess_source(void)
{
    char* cursor = source_buffer;
    uint16_t line_no = 1;
    line_count = 0;

    while (*cursor)
    {
        char* line_start = cursor;
        while (*cursor && (*cursor != '\n') && (*cursor != '\r'))
            cursor++;
        if (*cursor == '\r')
            *cursor++ = 0;
        if (*cursor == '\n')
            *cursor++ = 0;

        char* comment = strchr(line_start, ';');
        if (comment)
            *comment = 0;

        char* text = trim(line_start);
        if (*text)
        {
            if (line_count >= MAX_LINES)
                fatal("too many source lines");
            lines[line_count].line_no = line_no;
            lines[line_count].text = text;
            line_count++;
        }
        line_no++;
    }
}

static bool starts_with_keyword(const char* text, const char* keyword)
{
    uint8_t i = 0;
    while (keyword[i])
    {
        char a = text[i];
        char b = keyword[i];
        if ((a >= 'a') && (a <= 'z'))
            a = (char)(a - 'a' + 'A');
        if ((b >= 'a') && (b <= 'z'))
            b = (char)(b - 'a' + 'A');
        if (a != b)
            return false;
        i++;
    }
    return (text[i] == 0) || (text[i] == ' ') || (text[i] == '(');
}

static uint16_t append_text(const char* text)
{
    uint16_t offset = text_pool_len;
    while (*text)
    {
        if ((uint16_t)(text_pool_len + 1u) >= MAX_TEXT_POOL)
            fatal("text pool overflow");
        text_pool[text_pool_len++] = *text++;
    }
    if ((uint16_t)(text_pool_len + 1u) >= MAX_TEXT_POOL)
        fatal("text pool overflow");
    text_pool[text_pool_len++] = 0;
    return offset;
}

static void add_action(const char* text, bool newline)
{
    if (action_count >= MAX_ACTIONS)
        fatal("too many print actions");
    actions[action_count].text_offset = append_text(text);
    actions[action_count].newline = newline;
    action_count++;
}

static bool parse_string_literal(const char* text, char* out, uint16_t out_cap)
{
    if (*text != '"')
        return false;
    text++;
    uint16_t pos = 0;
    while (*text && (*text != '"'))
    {
        if (pos + 1 >= out_cap)
            return false;
        if (*text == '\\')
        {
            text++;
            if (*text == 'n')
                out[pos++] = '\n';
            else if (*text == 'r')
                out[pos++] = '\r';
            else if (*text == 't')
                out[pos++] = '\t';
            else if (*text == '"')
                out[pos++] = '"';
            else if (*text == '\\')
                out[pos++] = '\\';
            else
                return false;
            if (*text)
                text++;
            continue;
        }
        out[pos++] = *text++;
    }
    if (*text != '"')
        return false;
    text++;
    if (*trim((char*)text) != 0)
        return false;
    out[pos] = 0;
    return true;
}

static void emit_payload(uint16_t* out_len)
{
    uint16_t code_len = (uint16_t)(action_count * 6u + 3u);
    uint16_t string_base = code_len;
    uint16_t pos = AVM_HEADER_SIZE;
    uint16_t string_cursor = 0;

    if ((uint16_t)(AVM_HEADER_SIZE + code_len + text_pool_len) > MAX_AVM_BYTES)
        fatal("AVM too large");

    memcpy(avm_buffer, "AVM1", 4);
    avm_buffer[4] = 1;
    avm_buffer[5] = (uint8_t)((code_len + text_pool_len) & 0xff);
    avm_buffer[6] = (uint8_t)((code_len + text_pool_len) >> 8);
    avm_buffer[7] = 0;
    avm_buffer[8] = 0;
    avm_buffer[9] = 0;

    for (uint16_t i = 0; i < action_count; i++)
    {
        uint16_t string_offset = (uint16_t)(string_base + string_cursor);
        avm_buffer[pos++] = OPCODE_SETP16;
        avm_buffer[pos++] = (uint8_t)(string_offset & 0xff);
        avm_buffer[pos++] = (uint8_t)(string_offset >> 8);
        avm_buffer[pos++] = OPCODE_CALLN;
        avm_buffer[pos++] = actions[i].newline ? 0x10 : 0x00;
        avm_buffer[pos++] = 0xff;
        string_cursor = (uint16_t)(actions[i].text_offset + strlen(&text_pool[actions[i].text_offset]) + 1u);
    }

    avm_buffer[pos++] = OPCODE_CALLN;
    avm_buffer[pos++] = 0x20;
    avm_buffer[pos++] = 0xff;

    memcpy(&avm_buffer[AVM_HEADER_SIZE + code_len], text_pool, text_pool_len);
    *out_len = (uint16_t)(AVM_HEADER_SIZE + code_len + text_pool_len);
}

static void write_binary_file(const char* filename, const uint8_t* data, uint16_t len)
{
    FCB fcb;
    parse_filename(&fcb, filename);
    fcb.ex = 0;
    fcb.cr = 0;
    cpm_delete_file(&fcb);
    fcb.ex = 0;
    fcb.cr = 0;
    if (cpm_make_file(&fcb) != CPME_OK)
        fatal("cannot create output");

    uint16_t pos = 0;
    while (pos < len)
    {
        memset(cpm_default_dma, 0, 128);
        uint16_t chunk = (uint16_t)(len - pos);
        if (chunk > 128)
            chunk = 128;
        memcpy(cpm_default_dma, &data[pos], chunk);
        cpm_set_dma(cpm_default_dma);
        if (cpm_write_sequential(&fcb) != CPME_OK)
            fatal("cannot write output");
        pos = (uint16_t)(pos + chunk);
    }

    if (cpm_close_file(&fcb) != CPME_OK)
        fatal("cannot close output");
}

static void compile_program(void)
{
    uint16_t index = 0;
    char literal[256];

    if ((index < line_count) && starts_with_keyword(lines[index].text, "MODULE"))
        index++;
    if ((index >= line_count) || (strcmp(lines[index].text, "PROC main()") != 0))
        fatal_at(index < line_count ? lines[index].line_no : 0, "expected PROC main()");
    index++;

    while (index < line_count)
    {
        SourceLine* line = &lines[index];
        if (strcmp(line->text, "RETURN") == 0)
            return;

        if (starts_with_keyword(line->text, "PRINTE"))
        {
            const char* open = strchr(line->text, '(');
            const char* close = strrchr(line->text, ')');
            if (!open || !close || (close <= open))
                fatal_at(line->line_no, "bad PrintE syntax");
            char inner[256];
            uint16_t len = (uint16_t)(close - open - 1);
            if (len >= sizeof(inner))
                fatal_at(line->line_no, "string literal too long");
            memcpy(inner, open + 1, len);
            inner[len] = 0;
            char* trimmed = trim(inner);
            if (!parse_string_literal(trimmed, literal, sizeof(literal)))
                fatal_at(line->line_no, "PrintE requires a string literal");
            add_action(literal, true);
            index++;
            continue;
        }

        if (starts_with_keyword(line->text, "PRINT"))
        {
            const char* open = strchr(line->text, '(');
            const char* close = strrchr(line->text, ')');
            if (!open || !close || (close <= open))
                fatal_at(line->line_no, "bad Print syntax");
            char inner[256];
            uint16_t len = (uint16_t)(close - open - 1);
            if (len >= sizeof(inner))
                fatal_at(line->line_no, "string literal too long");
            memcpy(inner, open + 1, len);
            inner[len] = 0;
            char* trimmed = trim(inner);
            if (!parse_string_literal(trimmed, literal, sizeof(literal)))
                fatal_at(line->line_no, "Print requires a string literal");
            add_action(literal, false);
            index++;
            continue;
        }

        fatal_at(line->line_no, "unsupported statement");
    }

    fatal("missing RETURN");
}

int main(void)
{
    char source_name[13];
    char output_name[13];
    uint16_t avm_len;

    source_filename_from_primary_fcb(source_name);
    output_filename_from_source(source_name, output_name);
    text_pool_len = 0;
    action_count = 0;

    read_source_file(source_name);
    preprocess_source();
    compile_program();
    emit_payload(&avm_len);
    write_binary_file(output_name, avm_buffer, avm_len);

    print_cstr("wrote ");
    print_cstr(output_name);
    crlf();
    return 0;
}
