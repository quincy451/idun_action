#include "reu_backend.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define MAX_HANDLES 4
#define REU_TOTAL_BYTES (16UL * 1024UL * 1024UL)

#define C64_PORT (*(volatile uint8_t*)0x0001)

#define REU_STATUS (*(volatile uint8_t*)0xDF00)
#define REU_COMMAND (*(volatile uint8_t*)0xDF01)
#define REU_C64ADDR_LO (*(volatile uint8_t*)0xDF02)
#define REU_C64ADDR_HI (*(volatile uint8_t*)0xDF03)
#define REU_REUADDR_LO (*(volatile uint8_t*)0xDF04)
#define REU_REUADDR_HI (*(volatile uint8_t*)0xDF05)
#define REU_REUADDR_BANK (*(volatile uint8_t*)0xDF06)
#define REU_COUNT_LO (*(volatile uint8_t*)0xDF07)
#define REU_COUNT_HI (*(volatile uint8_t*)0xDF08)
#define REU_IRQMASK (*(volatile uint8_t*)0xDF09)
#define REU_CONTROL (*(volatile uint8_t*)0xDF0A)
#define REU_TRIGGER (*(volatile uint8_t*)0xFF00)

#define C64_PORT_IO_ON 0x05
#define C64_PORT_ALL_RAM 0x00

#define REU_CMD_COPY_C64_TO_REU 0xEC
#define REU_CMD_COPY_REU_TO_C64 0xED

typedef struct {
    bool in_use;
    uint32_t base;
    uint32_t size;
} HwHandle;

static HwHandle handles[MAX_HANDLES];
static uint32_t next_free_offset;
static bool probed;
static bool present;

static bool handle_valid(ReuHandle handle)
{
    return (handle < MAX_HANDLES) && handles[handle].in_use;
}

static bool ensure_reu_present(void)
{
    if (probed)
        return present;

    uint8_t saved_port = C64_PORT;
    probed = true;
    C64_PORT = (saved_port & 0xF8u) | C64_PORT_IO_ON;

    REU_REUADDR_LO = 0x55;
    if (REU_REUADDR_LO != 0x55)
    {
        C64_PORT = saved_port;
        present = false;
        return false;
    }

    REU_REUADDR_LO = 0xAA;
    present = (REU_REUADDR_LO == 0xAA);
    C64_PORT = saved_port;
    return present;
}

static bool bounds_ok(ReuHandle handle, uint32_t offset, uint32_t count)
{
    if (!handle_valid(handle))
        return false;
    if (count == 0)
        return true;
    if (offset >= handles[handle].size)
        return false;
    return count <= (handles[handle].size - offset);
}

static void reu_transfer(uint8_t command, uint32_t reu_addr, void* cpu_addr, uint16_t count)
{
    uint8_t saved_port = C64_PORT;
    uintptr_t host_addr = (uintptr_t)cpu_addr;

    C64_PORT = (saved_port & 0xF8u) | C64_PORT_IO_ON;

    REU_C64ADDR_LO = (uint8_t)(host_addr & 0xFFu);
    REU_C64ADDR_HI = (uint8_t)((host_addr >> 8) & 0xFFu);
    REU_REUADDR_LO = (uint8_t)(reu_addr & 0xFFu);
    REU_REUADDR_HI = (uint8_t)((reu_addr >> 8) & 0xFFu);
    REU_REUADDR_BANK = (uint8_t)((reu_addr >> 16) & 0xFFu);
    REU_COUNT_LO = (uint8_t)(count & 0xFFu);
    REU_COUNT_HI = (uint8_t)((count >> 8) & 0xFFu);
    REU_IRQMASK = 0;
    REU_CONTROL = 0;
    REU_COMMAND = command;

    C64_PORT = saved_port & 0xF8u;
    REU_TRIGGER = REU_TRIGGER;
    C64_PORT = saved_port;

    (void)REU_STATUS;
}

void reu_backend_reset(void)
{
    memset(handles, 0, sizeof(handles));
    next_free_offset = 0;
}

const char* reu_backend_name(void)
{
    return "hw";
}

bool reu_alloc(uint32_t size, ReuHandle* handle_out)
{
    if (!handle_out || (size == 0) || !ensure_reu_present())
        return false;
    if (size > REU_TOTAL_BYTES || next_free_offset > (REU_TOTAL_BYTES - size))
        return false;

    for (ReuHandle handle = 0; handle < MAX_HANDLES; handle++)
    {
        if (!handles[handle].in_use)
        {
            handles[handle].in_use = true;
            handles[handle].base = next_free_offset;
            handles[handle].size = size;
            next_free_offset += size;
            *handle_out = handle;
            return true;
        }
    }

    return false;
}

bool reu_free(ReuHandle handle)
{
    if (!handle_valid(handle))
        return false;

    if ((handles[handle].base + handles[handle].size) == next_free_offset)
        next_free_offset = handles[handle].base;

    handles[handle].in_use = false;
    handles[handle].base = 0;
    handles[handle].size = 0;
    return true;
}

bool reu_copy(ReuHandle dest_handle, uint32_t dest_offset, ReuHandle src_handle, uint32_t src_offset, uint32_t length)
{
    uint8_t byte;

    if (!ensure_reu_present() || !bounds_ok(dest_handle, dest_offset, length) || !bounds_ok(src_handle, src_offset, length))
        return false;

    while (length)
    {
        if (!reu_peek8(src_handle, src_offset, &byte))
            return false;
        if (!reu_poke8(dest_handle, dest_offset, byte))
            return false;
        src_offset++;
        dest_offset++;
        length--;
    }

    return true;
}

bool reu_peek8(ReuHandle handle, uint32_t offset, uint8_t* out)
{
    if (!out || !ensure_reu_present() || !bounds_ok(handle, offset, 1))
        return false;

    reu_transfer(REU_CMD_COPY_REU_TO_C64, handles[handle].base + offset, out, 1);
    return true;
}

bool reu_peek16(ReuHandle handle, uint32_t offset, uint16_t* out)
{
    uint8_t bytes[2];

    if (!out || !ensure_reu_present() || !bounds_ok(handle, offset, 2))
        return false;

    reu_transfer(REU_CMD_COPY_REU_TO_C64, handles[handle].base + offset, bytes, 2);
    *out = (uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8);
    return true;
}

bool reu_poke8(ReuHandle handle, uint32_t offset, uint8_t value)
{
    if (!ensure_reu_present() || !bounds_ok(handle, offset, 1))
        return false;

    reu_transfer(REU_CMD_COPY_C64_TO_REU, handles[handle].base + offset, &value, 1);
    return true;
}

bool reu_poke16(ReuHandle handle, uint32_t offset, uint16_t value)
{
    uint8_t bytes[2];

    if (!ensure_reu_present() || !bounds_ok(handle, offset, 2))
        return false;

    bytes[0] = (uint8_t)(value & 0xFFu);
    bytes[1] = (uint8_t)((value >> 8) & 0xFFu);
    reu_transfer(REU_CMD_COPY_C64_TO_REU, handles[handle].base + offset, bytes, 2);
    return true;
}
