#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from generate_reu_runtime import ObjectBuilder


# The public ABI keeps the compiler-owned pointers in $02-$07.  REAL helpers
# are synchronous and use $20-$5A as private scratch; no value in this range is
# live across a helper call in generated Action code.
A = 0x20
B = 0x24
R = 0x28
EA = 0x2C
EB = 0x2E
SA = 0x30
SB = 0x31
CA = 0x32
CB = 0x33
COUNT = 0x34
STICKY = 0x35
TMP = 0x36
TMP2 = 0x37
P = 0x38
M = 0x3E
REM = 0x44
TRIAL = 0x48
N = 0x4C
PAIR = 0x53
QBYTE = 0x54
SCALE = 0x55
DIGCOUNT = 0x56
DIGSTART = 0x57
BIGCARRY = 0x58
K = 0x59

ZERO = 0
FINITE = 1
INFINITY = 2
NAN = 3


class Assembler(ObjectBuilder):
    def __init__(self, module: str) -> None:
        super().__init__(module)
        self.serial = 0

    def fresh(self, stem: str) -> str:
        self.serial += 1
        return f"{stem}_{self.serial}"

    def lda_i(self, value: int) -> None:
        self.immediate(0xA9, value)

    def ldx_i(self, value: int) -> None:
        self.immediate(0xA2, value)

    def ldy_i(self, value: int) -> None:
        self.immediate(0xA0, value)

    def lda(self, address: int) -> None:
        self.zero_page(0xA5, address)

    def ldx(self, address: int) -> None:
        self.zero_page(0xA6, address)

    def ldy(self, address: int) -> None:
        self.zero_page(0xA4, address)

    def sta(self, address: int) -> None:
        self.zero_page(0x85, address)

    def stx(self, address: int) -> None:
        self.zero_page(0x86, address)

    def sty(self, address: int) -> None:
        self.zero_page(0x84, address)

    def and_i(self, value: int) -> None:
        self.immediate(0x29, value)

    def and_(self, address: int) -> None:
        self.zero_page(0x25, address)

    def ora_i(self, value: int) -> None:
        self.immediate(0x09, value)

    def ora(self, address: int) -> None:
        self.zero_page(0x05, address)

    def eor_i(self, value: int) -> None:
        self.immediate(0x49, value)

    def eor(self, address: int) -> None:
        self.zero_page(0x45, address)

    def adc_i(self, value: int) -> None:
        self.immediate(0x69, value)

    def adc(self, address: int) -> None:
        self.zero_page(0x65, address)

    def sbc_i(self, value: int) -> None:
        self.immediate(0xE9, value)

    def sbc(self, address: int) -> None:
        self.zero_page(0xE5, address)

    def cmp_i(self, value: int) -> None:
        self.immediate(0xC9, value)

    def cmp(self, address: int) -> None:
        self.zero_page(0xC5, address)

    def cpx_i(self, value: int) -> None:
        self.immediate(0xE0, value)

    def inc(self, address: int) -> None:
        self.zero_page(0xE6, address)

    def dec(self, address: int) -> None:
        self.zero_page(0xC6, address)

    def asl(self, address: int) -> None:
        self.zero_page(0x06, address)

    def rol(self, address: int) -> None:
        self.zero_page(0x26, address)

    def lsr(self, address: int) -> None:
        self.zero_page(0x46, address)

    def ror(self, address: int) -> None:
        self.zero_page(0x66, address)

    def branch_far(self, opcode: int, target: str) -> None:
        inverse = {
            0x10: 0x30,  # BPL/BMI
            0x30: 0x10,
            0x50: 0x70,  # BVC/BVS
            0x70: 0x50,
            0x90: 0xB0,  # BCC/BCS
            0xB0: 0x90,
            0xD0: 0xF0,  # BNE/BEQ
            0xF0: 0xD0,
        }[opcode]
        skip = self.fresh("far_skip")
        self.branch(inverse, skip)
        self.jmp_local(target)
        self.label(skip)

    def jsr_local(self, target: str) -> None:
        self.local_reference(0x20, target)


def emit_copy(a: Assembler, source: int, destination: int, count: int) -> None:
    for index in range(count):
        a.lda(source + index)
        a.sta(destination + index)


def emit_clear(a: Assembler, destination: int, count: int) -> None:
    a.lda_i(0)
    for index in range(count):
        a.sta(destination + index)


def emit_load_pointer(a: Assembler, pointer: int, destination: int) -> None:
    for index in range(4):
        a.ldy_i(index)
        a.emit(0xB1, pointer)  # LDA (pointer),Y
        a.sta(destination + index)


def emit_store_pointer(a: Assembler, pointer: int, source: int) -> None:
    for index in range(4):
        a.lda(source + index)
        a.ldy_i(index)
        a.emit(0x91, pointer)  # STA (pointer),Y


def emit_store_bytes(a: Assembler, values: tuple[int, int, int, int]) -> None:
    for index, value in enumerate(values):
        a.lda_i(value)
        a.ldy_i(index)
        a.emit(0x91, 0x06)


def emit_increment16(a: Assembler, address: int) -> None:
    done = a.fresh("inc16_done")
    a.inc(address)
    a.branch(0xD0, done)
    a.inc(address + 1)
    a.label(done)


def emit_decrement16(a: Assembler, address: int) -> None:
    no_borrow = a.fresh("dec16_no_borrow")
    a.lda(address)
    a.branch(0xD0, no_borrow)
    a.dec(address + 1)
    a.label(no_borrow)
    a.dec(address)


def emit_shift_left(
    a: Assembler,
    base: int,
    count: int,
    width: int = 4,
) -> None:
    for _ in range(count):
        a.emit(0x18)  # CLC
        for index in range(width):
            a.rol(base + index)


def emit_shift_right(a: Assembler, base: int, count: int, width: int) -> None:
    for _ in range(count):
        a.lsr(base + width - 1)
        for index in reversed(range(width - 1)):
            a.ror(base + index)


def emit_add(a: Assembler, left: int, right: int, destination: int, width: int) -> None:
    a.emit(0x18)  # CLC
    for index in range(width):
        a.lda(left + index)
        a.adc(right + index)
        a.sta(destination + index)


def emit_subtract(
    a: Assembler,
    left: int,
    right: int,
    destination: int,
    width: int,
) -> None:
    a.emit(0x38)  # SEC
    for index in range(width):
        a.lda(left + index)
        a.sbc(right + index)
        a.sta(destination + index)


def emit_any_nonzero(
    a: Assembler,
    base: int,
    count: int,
    nonzero: str,
    zero: str,
) -> None:
    a.lda(base)
    for index in range(1, count):
        a.ora(base + index)
    a.branch_far(0xD0, nonzero)
    a.jmp_local(zero)


def emit_compare_unsigned(
    a: Assembler,
    left: int,
    right: int,
    count: int,
    less: str,
    greater: str,
    equal: str,
) -> None:
    for index in reversed(range(count)):
        a.lda(left + index)
        a.cmp(right + index)
        a.branch_far(0x90, less)
        a.branch_far(0xD0, greater)
    a.jmp_local(equal)


def emit_compare_signed16(
    a: Assembler,
    left: int,
    right: int,
    less: str,
    greater: str,
    equal: str,
) -> None:
    a.lda(left + 1)
    a.eor_i(0x80)
    a.sta(TMP)
    a.lda(right + 1)
    a.eor_i(0x80)
    a.sta(TMP2)
    a.lda(TMP)
    a.cmp(TMP2)
    a.branch_far(0x90, less)
    a.branch_far(0xD0, greater)
    a.lda(left)
    a.cmp(right)
    a.branch_far(0x90, less)
    a.branch_far(0xD0, greater)
    a.jmp_local(equal)


def emit_unpack(
    a: Assembler,
    base: int,
    exponent: int,
    sign: int,
    classification: int,
    stem: str,
) -> None:
    normal = a.fresh(f"{stem}_normal")
    subnormal = a.fresh(f"{stem}_subnormal")
    sub_loop = a.fresh(f"{stem}_sub_loop")
    exponent_done = a.fresh(f"{stem}_exponent_done")
    sub_done = a.fresh(f"{stem}_sub_done")
    is_zero = a.fresh(f"{stem}_zero")
    is_special = a.fresh(f"{stem}_special")
    is_inf = a.fresh(f"{stem}_inf")
    done = a.fresh(f"{stem}_done")

    a.lda(base + 3)
    a.and_i(0x80)
    a.sta(sign)
    a.lda(base + 3)
    a.and_i(0x7F)
    a.emit(0x0A)  # ASL A
    a.sta(TMP)
    a.lda(base + 2)
    a.and_i(0x80)
    a.branch(0xF0, exponent_done)
    a.inc(TMP)
    a.label(exponent_done)
    a.lda(TMP)
    a.cmp_i(0xFF)
    a.branch_far(0xF0, is_special)
    a.cmp_i(0)
    a.branch_far(0xF0, subnormal)

    a.label(normal)
    a.lda(TMP)
    a.emit(0x38)  # SEC
    a.sbc_i(127)
    a.sta(exponent)
    a.lda_i(0)
    a.sbc_i(0)
    a.sta(exponent + 1)
    a.lda(base + 2)
    a.and_i(0x7F)
    a.ora_i(0x80)
    a.sta(base + 2)
    a.lda_i(0)
    a.sta(base + 3)
    a.lda_i(FINITE)
    a.sta(classification)
    a.jmp_local(done)

    a.label(subnormal)
    a.lda(base + 2)
    a.and_i(0x7F)
    a.sta(TMP2)
    a.lda(base)
    a.ora(base + 1)
    a.ora(TMP2)
    a.branch_far(0xF0, is_zero)
    a.lda_i(0x82)  # -126
    a.sta(exponent)
    a.lda_i(0xFF)
    a.sta(exponent + 1)
    a.lda(base + 2)
    a.and_i(0x7F)
    a.sta(base + 2)
    a.lda_i(0)
    a.sta(base + 3)
    a.label(sub_loop)
    a.lda(base + 2)
    a.and_i(0x80)
    a.branch(0xD0, sub_done)
    a.emit(0x18)
    a.rol(base)
    a.rol(base + 1)
    a.rol(base + 2)
    emit_decrement16(a, exponent)
    a.jmp_local(sub_loop)
    a.label(sub_done)
    a.lda_i(FINITE)
    a.sta(classification)
    a.jmp_local(done)

    a.label(is_zero)
    emit_clear(a, base, 4)
    a.lda_i(0x82)
    a.sta(exponent)
    a.lda_i(0xFF)
    a.sta(exponent + 1)
    a.lda_i(ZERO)
    a.sta(classification)
    a.jmp_local(done)

    a.label(is_special)
    a.lda(base)
    a.ora(base + 1)
    a.sta(TMP2)
    a.lda(base + 2)
    a.and_i(0x7F)
    a.ora(TMP2)
    a.branch_far(0xF0, is_inf)
    a.lda_i(NAN)
    a.sta(classification)
    a.jmp_local(done)
    a.label(is_inf)
    a.lda_i(INFINITY)
    a.sta(classification)
    a.label(done)


def emit_shift_right_sticky_subroutine(
    a: Assembler,
    base: int,
    width: int,
    label: str,
) -> None:
    loop = a.fresh(f"{label}_loop")
    no_sticky = a.fresh(f"{label}_no_sticky")
    done = a.fresh(f"{label}_done")
    a.label(label)
    a.lda(COUNT)
    a.branch(0xF0, done)
    a.lda_i(0)
    a.sta(STICKY)
    a.label(loop)
    a.lda(base)
    a.and_i(1)
    a.ora(STICKY)
    a.sta(STICKY)
    a.lsr(base + width - 1)
    for index in reversed(range(width - 1)):
        a.ror(base + index)
    a.dec(COUNT)
    a.branch(0xD0, loop)
    a.lda(STICKY)
    a.branch(0xF0, no_sticky)
    a.lda(base)
    a.ora_i(1)
    a.sta(base)
    a.label(no_sticky)
    a.label(done)
    a.emit(0x60)


def emit_pack_subroutine(a: Assembler, label: str, shift_label: str) -> None:
    nonzero = a.fresh("pack_nonzero")
    exp_nonnegative = a.fresh("pack_exp_nonnegative")
    not_tiny = a.fresh("pack_not_tiny")
    maybe_subnormal = a.fresh("pack_maybe_subnormal")
    after_subnormal = a.fresh("pack_after_subnormal")
    round_up = a.fresh("pack_round_up")
    after_round = a.fresh("pack_after_round")
    no_carry1 = a.fresh("pack_no_carry1")
    no_carry2 = a.fresh("pack_no_carry2")
    no_sig_overflow = a.fresh("pack_no_sig_overflow")
    normal_field = a.fresh("pack_normal_field")
    have_field = a.fresh("pack_have_field")
    overflow = a.fresh("pack_overflow")
    signed_zero = a.fresh("pack_signed_zero")

    a.label(label)
    emit_any_nonzero(a, R, 4, nonzero, signed_zero)
    a.label(nonzero)

    # Any nonnegative exponent above 127 overflows to infinity.
    a.lda(EA + 1)
    a.branch(0x10, exp_nonnegative)
    a.jmp_local(not_tiny)
    a.label(exp_nonnegative)
    a.branch_far(0xD0, overflow)
    a.lda(EA)
    a.cmp_i(128)
    a.branch_far(0xB0, overflow)
    a.jmp_local(maybe_subnormal)

    a.label(not_tiny)
    # Values below exponent -150 are strictly below half the minimum
    # subnormal and round to signed zero in nearest-even mode.
    a.lda(EA + 1)
    a.cmp_i(0xFF)
    a.branch_far(0x90, signed_zero)
    a.branch(0xD0, maybe_subnormal)
    a.lda(EA)
    a.cmp_i(0x6A)  # -150
    a.branch_far(0x90, signed_zero)

    a.label(maybe_subnormal)
    a.lda(EA + 1)
    a.cmp_i(0xFF)
    a.branch(0xD0, after_subnormal)
    a.lda(EA)
    a.cmp_i(0x82)  # -126
    a.branch(0xB0, after_subnormal)
    a.lda_i(0x82)
    a.emit(0x38)
    a.sbc(EA)
    a.sta(COUNT)
    a.jsr_local(shift_label)
    a.lda_i(0x82)
    a.sta(EA)
    a.lda_i(0xFF)
    a.sta(EA + 1)

    a.label(after_subnormal)
    a.lda(R)
    a.and_i(7)
    a.sta(TMP)
    a.cmp_i(4)
    a.branch(0x90, after_round)
    a.branch(0xD0, round_up)
    a.lda(R)
    a.and_i(8)
    a.branch(0xF0, after_round)
    a.label(round_up)
    a.lda(R)
    a.emit(0x18)
    a.adc_i(8)
    a.sta(R)
    a.branch(0x90, no_carry1)
    a.inc(R + 1)
    a.branch(0xD0, no_carry1)
    a.inc(R + 2)
    a.branch(0xD0, no_carry2)
    a.inc(R + 3)
    a.label(no_carry2)
    a.label(no_carry1)

    a.label(after_round)
    a.lda(R + 3)
    a.and_i(0x08)
    a.branch(0xF0, no_sig_overflow)
    a.lsr(R + 3)
    a.ror(R + 2)
    a.ror(R + 1)
    a.ror(R)
    emit_increment16(a, EA)
    a.label(no_sig_overflow)

    # Rounding can carry exponent 127 to 128.
    a.lda(EA + 1)
    a.branch(0x30, normal_field)
    a.branch_far(0xD0, overflow)
    a.lda(EA)
    a.cmp_i(128)
    a.branch_far(0xB0, overflow)

    a.label(normal_field)
    for _ in range(3):
        a.lsr(R + 3)
        a.ror(R + 2)
        a.ror(R + 1)
        a.ror(R)

    # At exponent -126 a rounded significand below bit 23 is subnormal.
    a.lda(EA + 1)
    a.cmp_i(0xFF)
    a.branch(0xD0, normal_field + "_biased")
    a.lda(EA)
    a.cmp_i(0x82)
    a.branch(0xD0, normal_field + "_biased")
    a.lda(R + 2)
    a.and_i(0x80)
    a.branch(0xD0, normal_field + "_biased")
    a.lda_i(0)
    a.sta(TMP)
    a.jmp_local(have_field)

    a.label(normal_field + "_biased")
    a.lda(EA)
    a.emit(0x18)
    a.adc_i(127)
    a.sta(TMP)

    a.label(have_field)
    a.lda(R)
    a.ldy_i(0)
    a.emit(0x91, 0x06)
    a.lda(R + 1)
    a.ldy_i(1)
    a.emit(0x91, 0x06)
    a.lda(TMP)
    a.and_i(1)
    a.branch(0xF0, have_field + "_even")
    a.lda(R + 2)
    a.and_i(0x7F)
    a.ora_i(0x80)
    a.jmp_local(have_field + "_store2")
    a.label(have_field + "_even")
    a.lda(R + 2)
    a.and_i(0x7F)
    a.label(have_field + "_store2")
    a.ldy_i(2)
    a.emit(0x91, 0x06)
    a.lda(TMP)
    a.lsr(TMP)
    a.lda(TMP)
    a.ora(SA)
    a.ldy_i(3)
    a.emit(0x91, 0x06)
    a.emit(0x60)

    a.label(overflow)
    emit_store_bytes(a, (0x00, 0x00, 0x80, 0x00))
    a.lda(SA)
    a.ora_i(0x7F)
    a.ldy_i(3)
    a.emit(0x91, 0x06)
    a.emit(0x60)

    a.label(signed_zero)
    emit_store_bytes(a, (0x00, 0x00, 0x00, 0x00))
    a.lda(SA)
    a.ldy_i(3)
    a.emit(0x91, 0x06)
    a.emit(0x60)


def emit_special_returns(a: Assembler, qnan: str, infinity: str, zero: str) -> None:
    a.label(qnan)
    emit_store_bytes(a, (0x00, 0x00, 0xC0, 0x7F))
    a.emit(0x60)
    a.label(infinity)
    emit_store_bytes(a, (0x00, 0x00, 0x80, 0x00))
    a.lda(SA)
    a.ora_i(0x7F)
    a.ldy_i(3)
    a.emit(0x91, 0x06)
    a.emit(0x60)
    a.label(zero)
    emit_store_bytes(a, (0x00, 0x00, 0x00, 0x00))
    a.lda(SA)
    a.ldy_i(3)
    a.emit(0x91, 0x06)
    a.emit(0x60)


def add_sub_module(subtract: bool) -> Assembler:
    name = "RT_F_SUB" if subtract else "RT_F_ADD"
    a = Assembler(name)
    qnan = a.fresh("return_qnan")
    infinity = a.fresh("return_inf")
    zero = a.fresh("return_zero")
    pack = a.fresh("pack")
    shift_r = a.fresh("shift_r")
    shift_b = a.fresh("shift_b")
    a_zero = a.fresh("a_zero")
    b_zero = a.fresh("b_zero")
    both_zero = a.fresh("both_zero")
    finite = a.fresh("finite")
    swap = a.fresh("swap")
    ordered = a.fresh("ordered")
    diff_capped = a.fresh("diff_capped")
    same_sign = a.fresh("same_sign")
    opposite = a.fresh("opposite")
    a_larger = a.fresh("a_larger")
    b_larger = a.fresh("b_larger")
    cancel = a.fresh("cancel")
    normalize = a.fresh("normalize")
    normalized = a.fresh("normalized")
    no_add_overflow = a.fresh("no_add_overflow")

    emit_load_pointer(a, 0x02, A)
    emit_load_pointer(a, 0x04, B)
    emit_unpack(a, A, EA, SA, CA, "a")
    emit_unpack(a, B, EB, SB, CB, "b")
    if subtract:
        a.lda(SB)
        a.eor_i(0x80)
        a.sta(SB)

    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CB)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CA)
    a.cmp_i(INFINITY)
    a.branch(0xD0, finite + "_a")
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch_far(0xD0, infinity)
    a.lda(SA)
    a.cmp(SB)
    a.branch_far(0xD0, qnan)
    a.jmp_local(infinity)
    a.label(finite + "_a")
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch(0xD0, finite)
    a.lda(SB)
    a.sta(SA)
    a.jmp_local(infinity)

    a.label(finite)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, a_zero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, b_zero)
    a.jmp_local(ordered)

    a.label(a_zero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, both_zero)
    emit_copy(a, B, R, 4)
    emit_shift_left(a, R, 3)
    emit_copy(a, EB, EA, 2)
    a.lda(SB)
    a.sta(SA)
    a.jsr_local(pack)
    a.emit(0x60)

    a.label(b_zero)
    emit_copy(a, A, R, 4)
    emit_shift_left(a, R, 3)
    a.jsr_local(pack)
    a.emit(0x60)

    a.label(both_zero)
    a.lda(SA)
    a.and_(SB)
    a.and_i(0x80)
    a.sta(SA)
    a.jmp_local(zero)

    a.label(ordered)
    emit_compare_signed16(a, EA, EB, swap, ordered + "_noswap", ordered + "_noswap")
    a.label(swap)
    for index in range(4):
        a.lda(A + index)
        a.sta(TMP)
        a.lda(B + index)
        a.sta(A + index)
        a.lda(TMP)
        a.sta(B + index)
    for index in range(2):
        a.lda(EA + index)
        a.sta(TMP)
        a.lda(EB + index)
        a.sta(EA + index)
        a.lda(TMP)
        a.sta(EB + index)
    a.lda(SA)
    a.sta(TMP)
    a.lda(SB)
    a.sta(SA)
    a.lda(TMP)
    a.sta(SB)
    a.label(ordered + "_noswap")

    emit_copy(a, A, R, 4)
    emit_shift_left(a, R, 3)
    emit_shift_left(a, B, 3)
    a.lda(EA)
    a.emit(0x38)
    a.sbc(EB)
    a.sta(COUNT)
    a.lda(EA + 1)
    a.sbc(EB + 1)
    a.branch(0xD0, ordered + "_cap")
    a.lda(COUNT)
    a.cmp_i(32)
    a.branch(0x90, diff_capped)
    a.label(ordered + "_cap")
    a.lda_i(31)
    a.sta(COUNT)
    a.label(diff_capped)
    a.jsr_local(shift_b)

    a.lda(SA)
    a.cmp(SB)
    a.branch_far(0xF0, same_sign)
    a.jmp_local(opposite)

    a.label(same_sign)
    a.emit(0x18)
    for index in range(4):
        a.lda(R + index)
        a.adc(B + index)
        a.sta(R + index)
    a.lda(R + 3)
    a.and_i(0x08)
    a.branch(0xF0, no_add_overflow)
    a.lda_i(1)
    a.sta(COUNT)
    a.jsr_local(shift_r)
    emit_increment16(a, EA)
    a.label(no_add_overflow)
    a.jsr_local(pack)
    a.emit(0x60)

    a.label(opposite)
    emit_compare_unsigned(a, R, B, 4, b_larger, a_larger, cancel)
    a.label(cancel)
    a.lda_i(0)
    a.sta(SA)
    a.jmp_local(zero)
    a.label(a_larger)
    a.emit(0x38)
    for index in range(4):
        a.lda(R + index)
        a.sbc(B + index)
        a.sta(R + index)
    a.jmp_local(normalize)
    a.label(b_larger)
    a.emit(0x38)
    for index in range(4):
        a.lda(B + index)
        a.sbc(R + index)
        a.sta(R + index)
    a.lda(SB)
    a.sta(SA)
    a.label(normalize)
    a.lda(R + 3)
    a.and_i(0x04)
    a.branch(0xD0, normalized)
    emit_shift_left(a, R, 1)
    emit_decrement16(a, EA)
    a.jmp_local(normalize)
    a.label(normalized)
    a.jsr_local(pack)
    a.emit(0x60)

    emit_special_returns(a, qnan, infinity, zero)
    emit_shift_right_sticky_subroutine(a, R, 4, shift_r)
    emit_shift_right_sticky_subroutine(a, B, 4, shift_b)
    emit_pack_subroutine(a, pack, shift_r)
    a.export(name)
    return a


def multiply_module() -> Assembler:
    name = "RT_F_MUL"
    a = Assembler(name)
    qnan = a.fresh("return_qnan")
    infinity = a.fresh("return_inf")
    zero = a.fresh("return_zero")
    finite = a.fresh("finite")
    a_not_inf = a.fresh("a_not_inf")
    b_not_inf = a.fresh("b_not_inf")
    multiply_loop = a.fresh("multiply_loop")
    skip_add = a.fresh("skip_add")
    product_normal = a.fresh("product_normal")
    product_shift = a.fresh("product_shift")
    pack = a.fresh("pack")
    shift_p = a.fresh("shift_p")
    shift_r = a.fresh("shift_r")

    emit_load_pointer(a, 0x02, A)
    emit_load_pointer(a, 0x04, B)
    emit_unpack(a, A, EA, SA, CA, "a")
    emit_unpack(a, B, EB, SB, CB, "b")
    a.lda(SA)
    a.eor(SB)
    a.and_i(0x80)
    a.sta(SA)

    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CB)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CA)
    a.cmp_i(INFINITY)
    a.branch(0xD0, a_not_inf)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, qnan)
    a.jmp_local(infinity)
    a.label(a_not_inf)
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch(0xD0, b_not_inf)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, qnan)
    a.jmp_local(infinity)
    a.label(b_not_inf)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, zero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, zero)

    a.label(finite)
    a.emit(0x18)
    a.lda(EA)
    a.adc(EB)
    a.sta(EA)
    a.lda(EA + 1)
    a.adc(EB + 1)
    a.sta(EA + 1)
    emit_clear(a, P, 6)
    emit_clear(a, M, 6)
    emit_copy(a, A, M, 3)
    a.lda_i(24)
    a.sta(COUNT)
    a.label(multiply_loop)
    a.lda(B)
    a.and_i(1)
    a.branch(0xF0, skip_add)
    emit_add(a, P, M, P, 6)
    a.label(skip_add)
    emit_shift_right(a, B, 1, 3)
    emit_shift_left(a, M, 1, 6)
    a.dec(COUNT)
    a.branch(0xD0, multiply_loop)

    a.lda(P + 5)
    a.and_i(0x80)
    a.branch(0xF0, product_normal)
    emit_increment16(a, EA)
    a.lda_i(21)
    a.jmp_local(product_shift)
    a.label(product_normal)
    a.lda_i(20)
    a.label(product_shift)
    a.sta(COUNT)
    a.jsr_local(shift_p)
    emit_copy(a, P, R, 4)
    a.jsr_local(pack)
    a.emit(0x60)

    emit_special_returns(a, qnan, infinity, zero)
    emit_shift_right_sticky_subroutine(a, P, 6, shift_p)
    emit_shift_right_sticky_subroutine(a, R, 4, shift_r)
    emit_pack_subroutine(a, pack, shift_r)
    a.export(name)
    return a


def divide_module() -> Assembler:
    name = "RT_F_DIV"
    a = Assembler(name)
    qnan = a.fresh("return_qnan")
    infinity = a.fresh("return_inf")
    zero = a.fresh("return_zero")
    a_not_inf = a.fresh("a_not_inf")
    b_not_inf = a.fresh("b_not_inf")
    a_not_zero = a.fresh("a_not_zero")
    finite = a.fresh("finite")
    numerator_less = a.fresh("numerator_less")
    divide_start = a.fresh("divide_start")
    divide_loop = a.fresh("divide_loop")
    subtract = a.fresh("subtract")
    next_bit = a.fresh("next_bit")
    remainder_nonzero = a.fresh("remainder_nonzero")
    quotient_ready = a.fresh("quotient_ready")
    pack = a.fresh("pack")
    shift_r = a.fresh("shift_r")

    emit_load_pointer(a, 0x02, A)
    emit_load_pointer(a, 0x04, B)
    emit_unpack(a, A, EA, SA, CA, "a")
    emit_unpack(a, B, EB, SB, CB, "b")
    a.lda(SA)
    a.eor(SB)
    a.and_i(0x80)
    a.sta(SA)

    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CB)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(CA)
    a.cmp_i(INFINITY)
    a.branch(0xD0, a_not_inf)
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch_far(0xF0, qnan)
    a.jmp_local(infinity)
    a.label(a_not_inf)
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch(0xD0, b_not_inf)
    a.jmp_local(zero)
    a.label(b_not_inf)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch(0xD0, a_not_zero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, qnan)
    a.jmp_local(zero)
    a.label(a_not_zero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, infinity)

    a.label(finite)
    a.emit(0x38)
    a.lda(EA)
    a.sbc(EB)
    a.sta(EA)
    a.lda(EA + 1)
    a.sbc(EB + 1)
    a.sta(EA + 1)
    emit_copy(a, A, REM, 4)
    emit_clear(a, R, 4)
    emit_compare_unsigned(
        a,
        REM,
        B,
        4,
        numerator_less,
        divide_start,
        divide_start,
    )
    a.label(numerator_less)
    emit_shift_left(a, REM, 1)
    emit_decrement16(a, EA)
    a.label(divide_start)
    a.lda_i(27)
    a.sta(COUNT)
    a.label(divide_loop)
    emit_shift_left(a, R, 1)
    emit_compare_unsigned(a, REM, B, 4, next_bit, subtract, subtract)
    a.label(subtract)
    emit_subtract(a, REM, B, REM, 4)
    a.lda(R)
    a.ora_i(1)
    a.sta(R)
    a.label(next_bit)
    emit_shift_left(a, REM, 1)
    a.dec(COUNT)
    a.branch_far(0xD0, divide_loop)
    emit_any_nonzero(a, REM, 4, remainder_nonzero, quotient_ready)
    a.label(remainder_nonzero)
    a.lda(R)
    a.ora_i(1)
    a.sta(R)
    a.label(quotient_ready)
    a.jsr_local(pack)
    a.emit(0x60)

    emit_special_returns(a, qnan, infinity, zero)
    emit_shift_right_sticky_subroutine(a, R, 4, shift_r)
    emit_pack_subroutine(a, pack, shift_r)
    a.export(name)
    return a


def compare_module() -> Assembler:
    name = "RT_F_CMP"
    a = Assembler(name)
    unordered = a.fresh("unordered")
    equal = a.fresh("equal")
    less = a.fresh("less")
    greater = a.fresh("greater")
    signs_equal = a.fresh("signs_equal")
    a_nonzero = a.fresh("a_nonzero")
    magnitudes = a.fresh("magnitudes")
    a_not_inf = a.fresh("a_not_inf")
    both_inf = a.fresh("both_inf")
    magnitude_less = a.fresh("magnitude_less")
    magnitude_greater = a.fresh("magnitude_greater")
    magnitude_equal = a.fresh("magnitude_equal")

    emit_load_pointer(a, 0x02, A)
    emit_load_pointer(a, 0x04, B)
    emit_unpack(a, A, EA, SA, CA, "a")
    emit_unpack(a, B, EB, SB, CB, "b")
    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, unordered)
    a.lda(CB)
    a.cmp_i(NAN)
    a.branch_far(0xF0, unordered)

    # IEEE treats both signed zeros as equal before sign ordering.
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch(0xD0, a_nonzero)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, equal)
    a.label(a_nonzero)
    a.lda(SA)
    a.cmp(SB)
    a.branch(0xF0, signs_equal)
    a.lda(SA)
    a.branch_far(0xD0, less)
    a.jmp_local(greater)
    a.label(signs_equal)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, magnitude_less)
    a.lda(CB)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, magnitude_greater)

    a.label(magnitudes)
    a.lda(CA)
    a.cmp_i(INFINITY)
    a.branch(0xD0, a_not_inf)
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch_far(0xF0, both_inf)
    a.jmp_local(magnitude_greater)
    a.label(a_not_inf)
    a.lda(CB)
    a.cmp_i(INFINITY)
    a.branch_far(0xF0, magnitude_less)
    emit_compare_signed16(
        a,
        EA,
        EB,
        magnitude_less,
        magnitude_greater,
        magnitudes + "_same_exp",
    )
    a.label(magnitudes + "_same_exp")
    emit_compare_unsigned(
        a,
        A,
        B,
        3,
        magnitude_less,
        magnitude_greater,
        magnitude_equal,
    )
    a.label(both_inf)
    a.jmp_local(magnitude_equal)

    a.label(magnitude_less)
    a.lda(SA)
    a.branch_far(0xD0, greater)
    a.jmp_local(less)
    a.label(magnitude_greater)
    a.lda(SA)
    a.branch_far(0xD0, less)
    a.jmp_local(greater)
    a.label(magnitude_equal)
    a.jmp_local(equal)

    a.label(unordered)
    a.lda_i(2)
    a.ldx_i(0)
    a.emit(0x60)
    a.label(equal)
    a.lda_i(0)
    a.ldx_i(0)
    a.emit(0x60)
    a.label(less)
    a.lda_i(0xFF)
    a.ldx_i(0xFF)
    a.emit(0x60)
    a.label(greater)
    a.lda_i(1)
    a.ldx_i(0)
    a.emit(0x60)
    a.export(name)
    return a


def absolute_module() -> Assembler:
    name = "RT_F_ABS"
    a = Assembler(name)
    for index in range(4):
        a.ldy_i(index)
        a.emit(0xB1, 0x02)
        if index == 3:
            a.and_i(0x7F)
        a.emit(0x91, 0x06)
    a.emit(0x60)
    a.export(name)
    return a


def integer_to_float_module(signed: bool) -> Assembler:
    name = "RT_S_TO_F" if signed else "RT_I_TO_F"
    a = Assembler(name)
    magnitude_ready = a.fresh("magnitude_ready")
    nonzero = a.fresh("nonzero")
    normalize = a.fresh("normalize")
    normalized = a.fresh("normalized")
    pack = a.fresh("pack")
    shift_r = a.fresh("shift_r")

    a.sta(A)
    a.stx(A + 1)
    emit_clear(a, A + 2, 2)
    emit_clear(a, SA, 1)
    a.lda(0x02)
    a.sta(0x06)
    a.lda(0x03)
    a.sta(0x07)
    if signed:
        a.lda(A + 1)
        a.and_i(0x80)
        a.branch(0xF0, magnitude_ready)
        a.lda_i(0x80)
        a.sta(SA)
        a.lda(A)
        a.eor_i(0xFF)
        a.emit(0x18)
        a.adc_i(1)
        a.sta(A)
        a.lda(A + 1)
        a.eor_i(0xFF)
        a.adc_i(0)
        a.sta(A + 1)
        a.label(magnitude_ready)
    a.lda(A)
    a.ora(A + 1)
    a.branch(0xD0, nonzero)
    emit_store_bytes(a, (0, 0, 0, 0))
    a.emit(0x60)

    a.label(nonzero)
    a.lda_i(23)
    a.sta(EA)
    a.lda_i(0)
    a.sta(EA + 1)
    a.label(normalize)
    a.lda(A + 2)
    a.and_i(0x80)
    a.branch(0xD0, normalized)
    emit_shift_left(a, A, 1, 3)
    emit_decrement16(a, EA)
    a.jmp_local(normalize)
    a.label(normalized)
    emit_copy(a, A, R, 4)
    emit_shift_left(a, R, 3)
    a.jsr_local(pack)
    a.emit(0x60)

    emit_shift_right_sticky_subroutine(a, R, 4, shift_r)
    emit_pack_subroutine(a, pack, shift_r)
    a.export(name)
    return a


def float_to_integer_module() -> Assembler:
    name = "RT_F_TO_I"
    a = Assembler(name)
    invalid = a.fresh("invalid")
    regular = a.fresh("regular")
    shift_loop = a.fresh("shift_loop")
    shifted = a.fresh("shifted")
    positive = a.fresh("positive")
    return_value = a.fresh("return_value")
    minimum = a.fresh("minimum")

    emit_load_pointer(a, 0x02, A)
    emit_unpack(a, A, EA, SA, CA, "source")
    a.lda(CA)
    a.cmp_i(FINITE)
    a.branch_far(0xD0, invalid)
    a.lda(EA + 1)
    a.branch_far(0x30, invalid)
    a.branch_far(0xD0, invalid)
    a.lda(EA)
    a.cmp_i(15)
    a.branch(0x90, regular)
    a.branch_far(0xD0, invalid)
    a.lda(SA)
    a.branch_far(0xF0, invalid)
    # Every negative value from -32768.0 through -32768.996... truncates to
    # -32768.  At exponent 15 that is precisely 0x800000..0x8000FF.
    a.lda(A + 1)
    a.branch_far(0xD0, invalid)
    a.lda(A + 2)
    a.cmp_i(0x80)
    a.branch_far(0xD0, invalid)
    a.jmp_local(minimum)

    a.label(regular)
    a.lda_i(23)
    a.emit(0x38)
    a.sbc(EA)
    a.sta(COUNT)
    a.label(shift_loop)
    a.lda(COUNT)
    a.branch(0xF0, shifted)
    emit_shift_right(a, A, 1, 3)
    a.dec(COUNT)
    a.jmp_local(shift_loop)
    a.label(shifted)
    a.lda(SA)
    a.branch(0xF0, positive)
    a.lda(A)
    a.eor_i(0xFF)
    a.emit(0x18)
    a.adc_i(1)
    a.sta(A)
    a.lda(A + 1)
    a.eor_i(0xFF)
    a.adc_i(0)
    a.sta(A + 1)
    a.label(positive)
    a.lda(A)
    a.ldx(A + 1)
    a.emit(0x60)

    a.label(minimum)
    a.lda_i(0)
    a.ldx_i(0x80)
    a.emit(0x60)
    a.label(invalid)
    a.lda_i(0)
    a.ldx_i(0)
    a.emit(0x60)
    a.export(name)
    return a


def square_root_module() -> Assembler:
    name = "RT_F_SQRT"
    a = Assembler(name)
    qnan = a.fresh("return_qnan")
    infinity = a.fresh("return_inf")
    zero = a.fresh("return_zero")
    nonnegative = a.fresh("nonnegative")
    finite = a.fresh("finite")
    exponent_even = a.fresh("exponent_even")
    root_loop = a.fresh("root_loop")
    root_no_subtract = a.fresh("root_no_subtract")
    root_subtract = a.fresh("root_subtract")
    remainder_nonzero = a.fresh("remainder_nonzero")
    root_ready = a.fresh("root_ready")
    pack = a.fresh("pack")
    shift_r = a.fresh("shift_r")

    emit_load_pointer(a, 0x02, A)
    emit_unpack(a, A, EA, SA, CA, "source")
    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, qnan)
    a.lda(SA)
    a.branch(0xF0, nonnegative)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, zero)
    a.jmp_local(qnan)
    a.label(nonnegative)
    a.lda(CA)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, zero)
    a.cmp_i(INFINITY)
    a.branch_far(0xF0, infinity)

    a.label(finite)
    emit_clear(a, SA, 1)
    a.lda(EA)
    a.and_i(1)
    a.branch(0xF0, exponent_even)
    emit_shift_left(a, A, 1)
    emit_decrement16(a, EA)
    a.label(exponent_even)
    # EA is now even.  This is an arithmetic 16-bit right shift.
    a.lda(EA + 1)
    a.cmp_i(0x80)
    a.ror(EA + 1)
    a.ror(EA)

    emit_clear(a, N, 7)
    emit_copy(a, A, N, 4)
    # The restoring loop consumes the upper 54 bits of a 56-bit register.
    # Shifting by 31 therefore presents A*2^29 to integer square root.
    emit_shift_left(a, N, 31, 7)
    emit_clear(a, REM, 4)
    emit_clear(a, R, 4)
    a.lda_i(27)
    a.sta(COUNT)
    a.label(root_loop)
    a.lda(N + 6)
    for _ in range(6):
        a.emit(0x4A)  # LSR A
    a.and_i(3)
    a.sta(PAIR)
    emit_shift_left(a, N, 2, 7)
    emit_shift_left(a, REM, 2)
    a.lda(REM)
    a.ora(PAIR)
    a.sta(REM)
    emit_shift_left(a, R, 1)
    emit_copy(a, R, TRIAL, 4)
    emit_shift_left(a, TRIAL, 1)
    a.inc(TRIAL)
    emit_compare_unsigned(
        a,
        REM,
        TRIAL,
        4,
        root_no_subtract,
        root_subtract,
        root_subtract,
    )
    a.label(root_subtract)
    emit_subtract(a, REM, TRIAL, REM, 4)
    a.lda(R)
    a.ora_i(1)
    a.sta(R)
    a.label(root_no_subtract)
    a.dec(COUNT)
    a.branch_far(0xD0, root_loop)
    emit_any_nonzero(a, REM, 4, remainder_nonzero, root_ready)
    a.label(remainder_nonzero)
    a.lda(R)
    a.ora_i(1)
    a.sta(R)
    a.label(root_ready)
    a.jsr_local(pack)
    a.emit(0x60)

    emit_special_returns(a, qnan, infinity, zero)
    emit_shift_right_sticky_subroutine(a, R, 4, shift_r)
    emit_pack_subroutine(a, pack, shift_r)
    a.export(name)
    return a


def print_float_module() -> Assembler:
    name = "RT_PRINT_F"
    a = Assembler(name)
    big_bytes = 54
    digit_bytes = 128
    big = a.fresh("big")
    digits = a.fresh("digits")
    state_count = a.fresh("state_count")
    state_start = a.fresh("state_start")
    state_bound = a.fresh("state_bound")
    state_zeros = a.fresh("state_zeros")
    chout = a.fresh("chout")
    print_sign = a.fresh("print_sign")
    print_nan = a.fresh("print_nan")
    print_inf = a.fresh("print_inf")
    print_zero = a.fresh("print_zero")
    finite = a.fresh("finite")
    clear_big = a.fresh("clear_big")
    exponent_negative = a.fresh("exponent_negative")
    scale_ready = a.fresh("scale_ready")
    shift_outer = a.fresh("shift_outer")
    shift_inner = a.fresh("shift_inner")
    multiply_outer = a.fresh("multiply_outer")
    multiply_inner = a.fresh("multiply_inner")
    decimal_outer = a.fresh("decimal_outer")
    decimal_byte = a.fresh("decimal_byte")
    decimal_bit = a.fresh("decimal_bit")
    decimal_no_subtract = a.fresh("decimal_no_subtract")
    trim = a.fresh("trim")
    output_ready = a.fresh("output_ready")
    output_integer = a.fresh("output_integer")
    output_integer_loop = a.fresh("output_integer_loop")
    output_fraction = a.fresh("output_fraction")
    output_fraction_loop = a.fresh("output_fraction_loop")
    output_small = a.fresh("output_small")
    output_zero_loop = a.fresh("output_zero_loop")
    output_all_digits = a.fresh("output_all_digits")
    output_all_loop = a.fresh("output_all_loop")
    done = a.fresh("done")

    def local_abs(opcode: int, label: str) -> None:
        a.local_reference(opcode, label)

    def emit_character(value: int) -> None:
        a.lda_i(value)
        a.jsr_local(chout)

    emit_load_pointer(a, 0x02, A)
    emit_unpack(a, A, EA, SA, CA, "source")
    a.lda(CA)
    a.cmp_i(NAN)
    a.branch_far(0xF0, print_nan)
    a.cmp_i(INFINITY)
    a.branch_far(0xF0, print_inf)
    a.cmp_i(ZERO)
    a.branch_far(0xF0, print_zero)

    a.label(finite)
    a.jsr_local(print_sign)
    a.ldx_i(big_bytes - 1)
    a.lda_i(0)
    a.label(clear_big)
    local_abs(0x9D, big)  # STA big,X
    a.emit(0xCA)  # DEX
    a.branch(0x10, clear_big)  # BPL
    for index in range(3):
        a.ldx_i(index)
        a.lda(A + index)
        local_abs(0x9D, big)

    # value = significand * 2^(EA-23).  For negative powers, multiplying the
    # significand by 5^(-K) gives an integer over the decimal scale 10^(-K).
    a.emit(0x38)
    a.lda(EA)
    a.sbc_i(23)
    a.sta(K)
    a.lda(EA + 1)
    a.sbc_i(0)
    a.sta(K + 1)
    a.lda(K + 1)
    a.branch(0x30, exponent_negative)
    a.lda_i(0)
    a.sta(SCALE)
    a.lda(K)
    a.sta(COUNT)
    a.label(shift_outer)
    a.lda(COUNT)
    a.branch_far(0xF0, scale_ready)
    a.emit(0x18)  # CLC
    a.ldx_i(0)
    a.ldy_i(big_bytes)
    a.label(shift_inner)
    local_abs(0x3E, big)  # ROL big,X
    a.emit(0xE8)  # INX
    a.emit(0x88)  # DEY; unlike CPX, this preserves carry between bytes
    a.branch(0xD0, shift_inner)
    a.dec(COUNT)
    a.jmp_local(shift_outer)

    a.label(exponent_negative)
    a.lda(K)
    a.eor_i(0xFF)
    a.emit(0x18)
    a.adc_i(1)
    a.sta(COUNT)
    a.sta(SCALE)
    a.label(multiply_outer)
    a.lda(COUNT)
    a.branch_far(0xF0, scale_ready)
    a.lda_i(0)
    a.sta(BIGCARRY)
    a.ldx_i(0)
    a.label(multiply_inner)
    local_abs(0xBD, big)  # LDA big,X
    a.sta(QBYTE)
    a.lda_i(0)
    a.sta(TMP2)
    a.lda(QBYTE)
    a.emit(0x0A)  # ASL A
    a.rol(TMP2)
    a.emit(0x0A)
    a.rol(TMP2)
    a.emit(0x18)
    a.adc(QBYTE)
    a.sta(TMP)
    a.lda(TMP2)
    a.adc_i(0)
    a.sta(TMP2)
    a.emit(0x18)
    a.lda(TMP)
    a.adc(BIGCARRY)
    local_abs(0x9D, big)  # STA big,X
    a.lda(TMP2)
    a.adc_i(0)
    a.sta(BIGCARRY)
    a.emit(0xE8)  # INX
    a.cpx_i(big_bytes)
    a.branch(0xD0, multiply_inner)
    a.dec(COUNT)
    a.jmp_local(multiply_outer)

    a.label(scale_ready)
    a.lda_i(0)
    a.sta(DIGCOUNT)
    a.label(decimal_outer)
    a.lda_i(0)
    a.sta(BIGCARRY)  # Decimal division remainder.
    a.sta(STICKY)  # OR of quotient bytes.
    a.ldx_i(big_bytes - 1)
    a.label(decimal_byte)
    local_abs(0xBD, big)  # LDA big,X
    a.sta(QBYTE)
    a.lda_i(0)
    a.sta(TMP)  # Quotient byte.
    a.lda_i(8)
    a.sta(K)
    a.label(decimal_bit)
    a.asl(QBYTE)
    a.rol(BIGCARRY)
    a.asl(TMP)
    a.lda(BIGCARRY)
    a.cmp_i(10)
    a.branch(0x90, decimal_no_subtract)
    a.sbc_i(10)
    a.sta(BIGCARRY)
    a.inc(TMP)
    a.label(decimal_no_subtract)
    a.dec(K)
    a.branch(0xD0, decimal_bit)
    a.lda(TMP)
    local_abs(0x9D, big)  # STA big,X
    a.ora(STICKY)
    a.sta(STICKY)
    a.emit(0xCA)  # DEX
    a.branch(0x10, decimal_byte)
    a.ldx(DIGCOUNT)
    a.lda(BIGCARRY)
    a.emit(0x18)
    a.adc_i(ord("0"))
    local_abs(0x9D, digits)  # STA digits,X
    a.inc(DIGCOUNT)
    a.lda(STICKY)
    a.branch_far(0xD0, decimal_outer)

    # Remove exact trailing decimal zeroes while reducing the decimal scale.
    # This keeps integral values compact and min-subnormal output finite.
    a.lda_i(0)
    a.sta(DIGSTART)
    a.label(trim)
    a.lda(SCALE)
    a.branch(0xF0, output_ready)
    a.ldx(DIGSTART)
    local_abs(0xBD, digits)  # LDA digits,X
    a.cmp_i(ord("0"))
    a.branch(0xD0, output_ready)
    a.inc(DIGSTART)
    a.dec(SCALE)
    a.jmp_local(trim)

    a.label(output_ready)
    a.lda(DIGCOUNT)
    local_abs(0x8D, state_count)
    a.lda(DIGSTART)
    local_abs(0x8D, state_start)
    a.lda(SCALE)
    a.branch_far(0xF0, output_integer)
    # Remaining digit count determines whether any digit precedes the point.
    a.lda(DIGCOUNT)
    a.emit(0x38)
    a.sbc(DIGSTART)
    a.sta(TMP)
    a.cmp(SCALE)
    a.branch_far(0x90, output_small)
    a.branch_far(0xF0, output_small)
    a.lda(DIGSTART)
    a.emit(0x18)
    a.adc(SCALE)
    local_abs(0x8D, state_bound)
    a.ldx(DIGCOUNT)
    a.emit(0xCA)  # DEX
    a.label(output_integer_loop)
    local_abs(0xBD, digits)
    a.jsr_local(chout)
    local_abs(0xEC, state_bound)  # CPX state_bound
    a.branch(0xF0, output_fraction)
    a.emit(0xCA)
    a.jmp_local(output_integer_loop)

    a.label(output_fraction)
    emit_character(ord("."))
    local_abs(0xAE, state_bound)  # LDX state_bound
    a.emit(0xCA)
    a.label(output_fraction_loop)
    local_abs(0xBD, digits)
    a.jsr_local(chout)
    local_abs(0xEC, state_start)
    a.branch_far(0xF0, done)
    a.emit(0xCA)
    a.jmp_local(output_fraction_loop)

    a.label(output_small)
    a.lda(SCALE)
    a.emit(0x38)
    a.sbc(TMP)
    local_abs(0x8D, state_zeros)
    emit_character(ord("0"))
    emit_character(ord("."))
    local_abs(0xAD, state_zeros)
    a.branch(0xF0, output_all_digits)
    a.label(output_zero_loop)
    emit_character(ord("0"))
    local_abs(0xCE, state_zeros)  # DEC state_zeros
    a.branch(0xD0, output_zero_loop)
    a.label(output_all_digits)
    local_abs(0xAE, state_count)  # LDX state_count
    a.emit(0xCA)
    a.label(output_all_loop)
    local_abs(0xBD, digits)
    a.jsr_local(chout)
    local_abs(0xEC, state_start)
    a.branch(0xF0, done)
    a.emit(0xCA)
    a.jmp_local(output_all_loop)

    a.label(output_integer)
    local_abs(0xAE, state_count)  # LDX state_count
    a.emit(0xCA)
    a.label(output_integer + "_loop")
    local_abs(0xBD, digits)
    a.jsr_local(chout)
    local_abs(0xEC, state_start)
    a.branch(0xF0, done)
    a.emit(0xCA)
    a.jmp_local(output_integer + "_loop")

    a.label(print_nan)
    for character in "NAN":
        emit_character(ord(character))
    a.emit(0x60)
    a.label(print_inf)
    a.jsr_local(print_sign)
    for character in "INF":
        emit_character(ord(character))
    a.emit(0x60)
    a.label(print_zero)
    a.jsr_local(print_sign)
    emit_character(ord("0"))
    a.emit(0x60)
    a.label(done)
    a.emit(0x60)

    a.label(print_sign)
    a.lda(SA)
    a.branch(0xF0, print_sign + "_done")
    emit_character(ord("-"))
    a.label(print_sign + "_done")
    a.emit(0x60)

    # CHROUT is allowed to use the C64 zero page.  X is the only live loop
    # register across output, so preserve it on the hardware stack and load
    # the character before entering KERNAL.
    a.label(chout)
    a.sta(QBYTE)
    a.emit(0x8A, 0x48)  # TXA; PHA
    a.lda(QBYTE)
    a.absolute(0x20, 0xFFD2)
    a.emit(0x68, 0xAA, 0x60)  # PLA; TAX; RTS

    a.label(big)
    a.emit(*([0] * big_bytes))
    a.label(digits)
    a.emit(*([0] * digit_bytes))
    for label in (state_count, state_start, state_bound, state_zeros):
        a.label(label)
        a.emit(0)
    a.export(name)
    return a


def modules() -> dict[str, Assembler]:
    return {
        "rt_f_add.obj": add_sub_module(False),
        "rt_f_sub.obj": add_sub_module(True),
        "rt_f_mul.obj": multiply_module(),
        "rt_f_div.obj": divide_module(),
        "rt_f_cmp.obj": compare_module(),
        "rt_f_abs.obj": absolute_module(),
        "rt_i_to_f.obj": integer_to_float_module(False),
        "rt_s_to_f.obj": integer_to_float_module(True),
        "rt_f_to_i.obj": float_to_integer_module(),
        "rt_f_sqrt.obj": square_root_module(),
        "rt_print_f.obj": print_float_module(),
    }


def main() -> int:
    # Keep the original assembler above as design provenance, but never let its
    # older monolithic objects replace the native authoritative runtime set.
    root = Path(__file__).resolve().parents[1]
    arguments = sys.argv[1:]
    has_output = "--output" in arguments
    if not has_output:
        arguments = arguments + ["--output", str(root / "src/runtime/modules")]
    result = subprocess.run(
        [sys.executable, str(root / "tools/generate_math_runtime.py"), *arguments],
        cwd=root,
        check=False,
    )
    if result.returncode != 0 or "--check" not in arguments or has_output:
        return result.returncode
    return subprocess.run(
        [sys.executable, str(root / "tools/shared_6502_sync.py")],
        cwd=root,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
