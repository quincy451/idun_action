#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
UDOS_ROOT = ROOT.parent / "udos"
BUILD_DIR = ROOT / "build" / "udos_tools"
UDOS_RUNTIME_MODULES = ROOT / "src" / "runtime" / "udos_modules"
HARNESS = BUILD_DIR / "tool_abi_harness"
ACTC_PRG = BUILD_DIR / "ACTC_HARNESS.PRG"
ALINK_PRG = BUILD_DIR / "ALINK.PRG"
AVMRUNC_PRG = BUILD_DIR / "AVMRUNC.PRG"
ACTC_LABELS = BUILD_DIR / "actc_harness.current.labels"
ALINK_LABELS = BUILD_DIR / "alink.current.labels"
AVMRUNC_LABELS = BUILD_DIR / "avmrunc.current.labels"
SERVICES_INC = BUILD_DIR / "udos_services.inc"
DEFAULT_BASE_FS = UDOS_ROOT / "build" / "udos-release-fs-manual-pipeline-44"
DIRECT_PRG_ENTRY_ADDR = 0x1000

SCENARIOS = {
    "additive": {
        "out_fs_name": "harness-actc-alink-direct-prg-additive",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("HELLO")\r'
            'W()\r'
            'PrintI(50 + 7 - 3)\r'
            'PrintIE(60 - 3 + 2)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 22\n"
            "b e0u0j0i1r\n"
            "u w\n"
            "s HELLO\n"
            "i 54\n"
            "i 59\n"
            "k 7\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 64, 0, 0, 0, 1, 53, 0, 97, 53, 0, 73,
                16, 255, 69, 40, 0, 17, 50, 0, 17, 7, 0, 20, 17, 3, 0, 21,
                73, 48, 255, 17, 60, 0, 17, 3, 0, 21, 17, 2, 0, 20, 73, 49,
                255, 73, 32, 255, 97, 59, 0, 73, 0, 255, 17, 7, 0, 73, 49,
                255, 72, 72, 69, 76, 76, 79, 0, 84, 79, 79, 76, 0,
            ]
        ),
        "expected_prg": bytes.fromhex(
            "0010a97b8502a9138503a2022003cf2006cf205012a936a2008d77138e7813a9798502a9138503a000a200ad7813c927"
            "901dd007ad7713c910901438ad7713e9108d7713ad7813e9278d7813e8d0dce000d004c000f00e8a1869308d7913a202"
            "2003cfa001a200ad7813c903901dd007ad7713c9e8901438ad7713e9e88d7713ad7813e9038d7813e8d0dce000d004c0"
            "00f00e8a1869308d7913a2022003cfa001a200ad7813c900901dd007ad7713c964901438ad7713e9648d7713ad7813e9"
            "008d7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001a200ad7813c900901dd007ad7713c90a901438"
            "ad7713e90a8d7713ad7813e9008d7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001ad77131869308d"
            "7913a2022003cfa93ba2008d77138e7813a9798502a9138503a000a200ad7813c927901dd007ad7713c910901438ad77"
            "13e9108d7713ad7813e9278d7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001a200ad7813c903901d"
            "d007ad7713c9e8901438ad7713e9e88d7713ad7813e9038d7813e8d0dce000d004c000f00e8a1869308d7913a2022003"
            "cfa001a200ad7813c900901dd007ad7713c964901438ad7713e9648d7713ad7813e9008d7813e8d0dce000d004c000f0"
            "0e8a1869308d7913a2022003cfa001a200ad7813c900901dd007ad7713c90a901438ad7713e90a8d7713ad7813e9008d"
            "7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001ad77131869308d7913a2022003cf2006cf8dd1038e"
            "d203a9a58dd003a90085028503a2024c0fcfa9818502a9138503a2022003cfa907a2008d77138e7813a9798502a91385"
            "03a000a200ad7813c927901dd007ad7713c910901438ad7713e9108d7713ad7813e9278d7813e8d0dce000d004c000f0"
            "0e8a1869308d7913a2022003cfa001a200ad7813c903901dd007ad7713c9e8901438ad7713e9e88d7713ad7813e9038d"
            "7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001a200ad7813c900901dd007ad7713c964901438ad77"
            "13e9648d7713ad7813e9008d7813e8d0dce000d004c000f00e8a1869308d7913a2022003cfa001a200ad7813c900901d"
            "d007ad7713c90a901438ad7713e90a8d7713ad7813e9008d7813e8d0dce000d004c000f00e8a1869308d7913a2022003"
            "cfa001ad77131869308d7913a2022003cf2006cf60000000000000000048454c4c4f00544f4f4c00"
        ),
        "expected_console": "HELLO\nTOOL7\n5459\n",
    },
    "precedence": {
        "out_fs_name": "harness-actc-alink-direct-prg-precedence",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintI(2 + 3 * 4)\r'
            'PrintIE((20 - 5) / 3)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 13\n"
            "b j0i1r\n"
            "i 14\n"
            "i 5\n"
            "k 7\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 19, 0, 0, 0, 1, 19, 0, 17, 2, 0, 17,
                12, 0, 20, 73, 48, 255, 17, 5, 0, 73, 49, 255, 73, 32, 255,
            ]
        ),
        "expected_prg": bytes.fromhex(
            "0010a90ea2008d3d128e3e12a9418502a9128503a000a200ad3e12c927901dd007ad3d12c910901438ad3d12e9108d3d"
            "12ad3e12e9278d3e12e8d0dce000d004c000f00e8a1869308d4112a2022003cfa001a200ad3e12c903901dd007ad3d12"
            "c9e8901438ad3d12e9e88d3d12ad3e12e9038d3e12e8d0dce000d004c000f00e8a1869308d4112a2022003cfa001a200"
            "ad3e12c900901dd007ad3d12c964901438ad3d12e9648d3d12ad3e12e9008d3e12e8d0dce000d004c000f00e8a186930"
            "8d4112a2022003cfa001a200ad3e12c900901dd007ad3d12c90a901438ad3d12e90a8d3d12ad3e12e9008d3e12e8d0dc"
            "e000d004c000f00e8a1869308d4112a2022003cfa001ad3d121869308d4112a2022003cfa905a2008d3d128e3e12a941"
            "8502a9128503a000a200ad3e12c927901dd007ad3d12c910901438ad3d12e9108d3d12ad3e12e9278d3e12e8d0dce000"
            "d004c000f00e8a1869308d4112a2022003cfa001a200ad3e12c903901dd007ad3d12c9e8901438ad3d12e9e88d3d12ad"
            "3e12e9038d3e12e8d0dce000d004c000f00e8a1869308d4112a2022003cfa001a200ad3e12c900901dd007ad3d12c964"
            "901438ad3d12e9648d3d12ad3e12e9008d3e12e8d0dce000d004c000f00e8a1869308d4112a2022003cfa001a200ad3e"
            "12c900901dd007ad3d12c90a901438ad3d12e90a8d3d12ad3e12e9008d3e12e8d0dce000d004c000f00e8a1869308d41"
            "12a2022003cfa001ad3d121869308d4112a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00"
            "0000000000"
        ),
        "expected_console": "145\n",
    },
    "comparisons": {
        "out_fs_name": "harness-actc-alink-direct-prg-comparisons",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintIE(2 + 3 * 4)\r'
            'PrintIE((20 - 5) / 3)\r'
            'PrintIE((2 + 3) * 4 = 20)\r'
            'PrintIE((2 + 3 * 4) > 10)\r'
            'W()\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 28\n"
            "b i0i1i2i3u0r\n"
            "u w\n"
            "i 14\n"
            "i 5\n"
            "i 1\n"
            "i 1\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes.fromhex(
            "41564d310246000000014100110200110c00144931fe1105004931fe110200110300141105004931fe110200110c0014"
            "110e00110a001d4931fe4534004920ff6141004900fe1107004931fe48544f4f4c004156483101021c0441564e480102"
            "0c001c040400011800024800038700044a02a58e48a58f48a58d48a58b48a58c48a5014829f809068501a2e02003cf68"
            "850168858c68858b68858d68858f68858e60a58e48a58f48a58d48a58b48a58c48a5014829f809068501a2e02003cf68"
            "8501a5014829f8090685012006cf68850168858c68858b68858d68858f68858e60b50085f5b50185f6a58e48a58f48a5"
            "8d48a58b48a58c48a90085f7a90085f8a5f6c9279019d006a5f5c910901138a5f5e91085f5a5f6e92785f6e6f8d0e1a5"
            "f7d004a5f8f030a5f818693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf68850168"
            "aa68a8a90185f7a90085f8a5f6c9039019d006a5f5c9e8901138a5f5e9e885f5a5f6e90385f6e6f8d0e1a5f7d004a5f8"
            "f030a5f818693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf68850168aa68a8a901"
            "85f7a90085f8a5f6c9009019d006a5f5c964901138a5f5e96485f5a5f6e90085f6e6f8d0e1a5f7d004a5f8f030a5f818"
            "693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf68850168aa68a8a90185f7a90085"
            "f8a5f6c9009019d006a5f5c90a901138a5f5e90a85f5a5f6e90085f6e6f8d0e1a5f7d004a5f8f030a5f818693085eba9"
            "0085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf68850168aa68a8a90185f7a5f518693085eba9"
            "0085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf68850168aa68a868858c68858b68858d68858f"
            "68858e60b50085f5b50185f6a58e48a58f48a58d48a58b48a58c48a90085f7a90085f8a5f6c9279019d006a5f5c91090"
            "1138a5f5e91085f5a5f6e92785f6e6f8d0e1a5f7d004a5f8f030a5f818693085eba90085ec98488a48a9eb85e0a90085"
            "e1a5014829f809068501a2e02003cf68850168aa68a8a90185f7a90085f8a5f6c9039019d006a5f5c9e8901138a5f5e9"
            "e885f5a5f6e90385f6e6f8d0e1a5f7d004a5f8f030a5f818693085eba90085ec98488a48a9eb85e0a90085e1a5014829"
            "f809068501a2e02003cf68850168aa68a8a90185f7a90085f8a5f6c9009019d006a5f5c964901138a5f5e96485f5a5f6"
            "e90085f6e6f8d0e1a5f7d004a5f8f030a5f818693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501"
            "a2e02003cf68850168aa68a8a90185f7a90085f8a5f6c9009019d006a5f5c90a901138a5f5e90a85f5a5f6e90085f6e6"
            "f8d0e1a5f7d004a5f8f030a5f818693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf"
            "68850168aa68a8a90185f7a5f518693085eba90085ec98488a48a9eb85e0a90085e1a5014829f809068501a2e02003cf"
            "68850168aa68a8a5014829f8090685012006cf68850168858c68858b68858d68858f68858e60"
        ),
        "expected_prg": bytes.fromhex(
            "0010a90ea2008d90158e9115a9948502a9158503a000a200ad9115c927901dd007ad9015c910901438ad9015e9108d90"
            "15ad9115e9278d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c903901dd007ad9015"
            "c9e8901438ad9015e9e88d9015ad9115e9038d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200"
            "ad9115c900901dd007ad9015c964901438ad9015e9648d9015ad9115e9008d9115e8d0dce000d004c000f00e8a186930"
            "8d9415a2022003cfa001a200ad9115c900901dd007ad9015c90a901438ad9015e90a8d9015ad9115e9008d9115e8d0dc"
            "e000d004c000f00e8a1869308d9415a2022003cfa001ad90151869308d9415a2022003cf2006cfa905a2008d90158e91"
            "15a9948502a9158503a000a200ad9115c927901dd007ad9015c910901438ad9015e9108d9015ad9115e9278d9115e8d0"
            "dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c903901dd007ad9015c9e8901438ad9015e9e88d"
            "9015ad9115e9038d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c900901dd007ad90"
            "15c964901438ad9015e9648d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a2"
            "00ad9115c900901dd007ad9015c90a901438ad9015e90a8d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869"
            "308d9415a2022003cfa001ad90151869308d9415a2022003cf2006cfa901a2008d90158e9115a9948502a9158503a000"
            "a200ad9115c927901dd007ad9015c910901438ad9015e9108d9015ad9115e9278d9115e8d0dce000d004c000f00e8a18"
            "69308d9415a2022003cfa001a200ad9115c903901dd007ad9015c9e8901438ad9015e9e88d9015ad9115e9038d9115e8"
            "d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c900901dd007ad9015c964901438ad9015e964"
            "8d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c900901dd007ad"
            "9015c90a901438ad9015e90a8d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001"
            "ad90151869308d9415a2022003cf2006cfa901a2008d90158e9115a9948502a9158503a000a200ad9115c927901dd007"
            "ad9015c910901438ad9015e9108d9015ad9115e9278d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa0"
            "01a200ad9115c903901dd007ad9015c9e8901438ad9015e9e88d9015ad9115e9038d9115e8d0dce000d004c000f00e8a"
            "1869308d9415a2022003cfa001a200ad9115c900901dd007ad9015c964901438ad9015e9648d9015ad9115e9008d9115"
            "e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c900901dd007ad9015c90a901438ad9015e9"
            "0a8d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001ad90151869308d9415a202"
            "2003cf2006cf206d148dd1038ed203a9a58dd003a90085028503a2024c0fcfa9968502a9158503a2022003cfa907a200"
            "8d90158e9115a9948502a9158503a000a200ad9115c927901dd007ad9015c910901438ad9015e9108d9015ad9115e927"
            "8d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c903901dd007ad9015c9e8901438ad"
            "9015e9e88d9015ad9115e9038d9115e8d0dce000d004c000f00e8a1869308d9415a2022003cfa001a200ad9115c90090"
            "1dd007ad9015c964901438ad9015e9648d9015ad9115e9008d9115e8d0dce000d004c000f00e8a1869308d9415a20220"
            "03cfa001a200ad9115c900901dd007ad9015c90a901438ad9015e90a8d9015ad9115e9008d9115e8d0dce000d004c000"
            "f00e8a1869308d9415a2022003cfa001ad90151869308d9415a2022003cf2006cf60000000000000544f4f4c00"
        ),
        "expected_console": "14\n5\n1\n1\nTOOL7\n",
    },
    "int_vars_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-basic",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 23\n"
            "b L0zL0p0aS0L0zr\n"
            "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad6f12ae70128d69128e6a12a96d8502a9128503a000a200ad6a12c927901dd007ad6912c910901438ad6912e9108d6912ad6a12e9278d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c903901dd007ad6912c9e8901438ad6912e9e88d6912ad6a12e9038d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c900901dd007ad6912c964901438ad6912e9648d6912ad6a12e9008d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c900901dd007ad6912c90a901438ad6912e90a8d6912ad6a12e9008d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001ad69121869308d6d12a2022003cf2006cfad6f12ae70128d69128e6a12a901a200186d69128d69128a6d6a12aaad69128d6f128e7012ad6f12ae70128d69128e6a12a96d8502a9128503a000a200ad6a12c927901dd007ad6912c910901438ad6912e9108d6912ad6a12e9278d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c903901dd007ad6912c9e8901438ad6912e9e88d6912ad6a12e9038d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c900901dd007ad6912c964901438ad6912e9648d6912ad6a12e9008d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001a200ad6a12c900901dd007ad6912c90a901438ad6912e90a8d6912ad6a12e9008d6a12e8d0dce000d004c000f00e8a1869308d6d12a2022003cfa001ad69121869308d6d12a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000000"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 27, 0, 0, 0, 1, 25, 0, 19, 25, 0, 73,
                49, 255, 19, 25, 0, 17, 1, 0, 20, 18, 25, 0, 19, 25, 0,
                73, 49, 255, 73, 32, 255, 0, 0,
            ]
        ),
        "expected_console": "0\n1\n",
    },
    "helper_free_word_load_store": {
        "out_fs_name": "harness-actc-alink-direct-prg-word-load-store",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'PROC MAIN()\r'
            'X=7\r'
            'Y=X\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 13\n"
            "b p0S0L0S1r\n"
            "i 7\n"
            "v x 0\n"
            "v y 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a907a2008d2e108e2f10ad2e10ae2f108d30108e3110"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000000000000"
        ),
        "expected_console": "",
    },
    "helper_free_if_eq": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-eq",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'PROC MAIN()\r'
            'X=7\r'
            'IF X=7 THEN\r'
            'Y=1\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 23\n"
            "b p0S0L0p1qhp2S1vr\n"
            "i 7\n"
            "i 7\n"
            "i 1\n"
            "v x 0\n"
            "v y 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a907a2008d49108e4a10ad4910ae4a108d47008e4800"
            "a907a200ec4800d005cd4700f0034c3110a901a2008d"
            "4b108e4c108dd1038ed203a9a58dd003a90085028503"
            "a2024c0fcf000000000000"
        ),
        "expected_console": "",
    },
    "helper_free_nested_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'CARD Z\r'
            'PROC MAIN()\r'
            'X=1\r'
            'Y=2\r'
            'IF X<Y THEN\r'
            'IF Y>2 THEN\r'
            'Z=3\r'
            'ELSE\r'
            'Z=4\r'
            'FI\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 48\n"
            "b p0S0p1S1L0L1lhL1p2ghp3S2wp4S2vvr\n"
            "i 1\n"
            "i 2\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "v x 0\n"
            "v y 0\n"
            "v z 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d9f108ea010a902a2008da1108ea210ad9f10aea0108d9d008e9e00"
            "ada110aea210ec9e00900dd007cd9d009006f004a901d002a900a200c900d003"
            "4c8710ada110aea2108d00008e0100a902a200ec01009007d00dcd00009002f0"
            "04a901d002a900a200c900d0034c7d10a903a2008da3108ea4104c8710a904a2"
            "008da3108ea4108dd1038ed203a9a58dd003a90085028503a2024c0fcf000000"
            "0000000000"
        ),
        "expected_console": "",
    },
    "helper_free_if_local_call_do_until_eq": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-local-call-do-until-eq",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'PROC A()\r'
            'DO\r'
            'Y=2\r'
            'UNTIL Y=2\r'
            'OD\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'X=1\r'
            'Y=0\r'
            'IF X=1 THEN\r'
            'A()\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x a 0 17\n"
            "x main 17 26\n"
            "b dp0S1L1p1qtor\n"
            "b p2S0p3S1L0p4qhc0vr\n"
            "i 2\n"
            "i 2\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "v x 0\n"
            "v y 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d76108e7710a900a2008d78108e7910ad7610ae77108d72108e7310"
            "a901a200ec7310d005cd7210f0034c3410204a108dd1038ed203a9a58dd003a9"
            "0085028503a2024c0fcfa902a2008d78108e7910ad7810ae79108d72108e7310"
            "a902a200ec7310d005cd7210f0034c0010600000000000000000"
        ),
        "expected_console": "",
    },
    "helper_free_if_else_local_call_chain_nested_do_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-else-local-call-chain-nested-do-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'PROC B()\r'
            'DO\r'
            'IF Y=1 THEN\r'
            'Y=3\r'
            'ELSE\r'
            'Y=12\r'
            'FI\r'
            'UNTIL Y=12\r'
            'OD\r'
            'RETURN\r'
            'PROC A()\r'
            'B()\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'X=1\r'
            'Y=0\r'
            'IF X=2 THEN\r'
            'Y=4\r'
            'ELSE\r'
            'A()\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x b 0 36\n"
            "x a 36 4\n"
            "x main 40 35\n"
            "b dL1p0qhp1S1wp2S1vL1p3qtor\n"
            "b c0r\n"
            "b p4S0p5S1L0p6qhp7S1wc1vr\n"
            "i 1\n"
            "i 3\n"
            "i 12\n"
            "i 12\n"
            "i 1\n"
            "i 0\n"
            "i 2\n"
            "i 4\n"
            "v x 0\n"
            "v y 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008db1108eb210a900a2008db3108eb410adb110aeb2108dad108eae10"
            "a902a200ecae10d005cdad10f0034c3e10a904a2008db3108eb4104c411020a9"
            "108dd1038ed203a9a58dd003a90085028503a2024c0fcfadb310aeb4108dad10"
            "8eae10a901a200ecae10d005cdad10f0034c2a10a903a2008db3108eb4104c34"
            "10a90ca2008db3108eb410adb310aeb4108dad108eae10a90ca200ecae10d005"
            "cdad10f0034c001060205710600000000000000000"
        ),
        "expected_console": "",
    },
    "helper_free_nested_else_local_call_chain_nested_do_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-else-local-call-chain-nested-do-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'CARD X\r'
            'CARD Y\r'
            'PROC B()\r'
            'DO\r'
            'IF Y=1 THEN\r'
            'Y=3\r'
            'ELSE\r'
            'Y=13\r'
            'FI\r'
            'UNTIL Y=13\r'
            'OD\r'
            'RETURN\r'
            'PROC A()\r'
            'B()\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'X=1\r'
            'Y=0\r'
            'IF X=1 THEN\r'
            'IF Y=1 THEN\r'
            'Y=4\r'
            'ELSE\r'
            'A()\r'
            'FI\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x b 0 36\n"
            "x a 36 4\n"
            "x main 40 45\n"
            "b dL1p0qhp1S1wp2S1vL1p3qtor\n"
            "b c0r\n"
            "b p4S0p5S1L0p6qhL1p7qhp8S1wc1vvr\n"
            "i 1\n"
            "i 3\n"
            "i 13\n"
            "i 13\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "i 4\n"
            "v x 0\n"
            "v y 0\n"
            "k 0\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008dce108ecf10a900a2008dd0108ed110adce10aecf108dca108ecb10"
            "a901a200eccb10d005cdca10f0034c5e10add010aed1108dca108ecb10a901a2"
            "00eccb10d005cdca10f0034c5b10a904a2008dd0108ed1104c5e1020c6108dd1"
            "038ed203a9a58dd003a90085028503a2024c0fcfadd010aed1108dca108ecb10"
            "a901a200eccb10d005cdca10f0034c2a10a903a2008dd0108ed1104c3410a90d"
            "a2008dd0108ed110add010aed1108dca108ecb10a90da200eccb10d005cdca10"
            "f0034c001060207410600000000000000000"
        ),
        "expected_console": "",
    },
    "printstd_string_direct_prg": {
        "out_fs_name": "harness-actc-alink-direct-prg-printstd-string",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b e0r\n"
            "s HELLO\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a9288502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000048454c4c4f00"
        ),
        "expected_console": "HELLO\n",
    },
    "printstd_integer_direct_prg": {
        "out_fs_name": "harness-actc-alink-direct-prg-printstd-integer",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintIE(7)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b p0zr\n"
            "i 7\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a907a2008d2b118e2c11a92f8502a9118503a000a200ad2c11c927901dd007ad2b11c910901438ad2b11e9108d2b11ad2c11e9278d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cf"
            "a001a200ad2c11c903901dd007ad2b11c9e8901438ad2b11e9e88d2b11ad2c11e9038d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cf"
            "a001a200ad2c11c900901dd007ad2b11c964901438ad2b11e9648d2b11ad2c11e9008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cf"
            "a001a200ad2c11c900901dd007ad2b11c90a901438ad2b11e90a8d2b11ad2c11e9008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cf"
            "a001ad2b111869308d2f11a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000000000000"
        ),
        "expected_console": "7\n",
    },
    "printstd_string_integer_direct_prg": {
        "out_fs_name": "harness-actc-alink-direct-prg-printstd-string-integer",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("HELLO")\r'
            'PrintIE(7)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 13\n"
            "b e0p0zr\n"
            "s HELLO\n"
            "i 7\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a93f8502a9118503a2022003cf2006cf"
            "a907a2008d3b118e3c11a93d8502a9118503a000a200ad3c11c927901dd007ad3b11c910901438ad3b11e9108d3b11ad3c11e9278d3c11e8d0dce000d004c000f00e8a1869308d3d11a2022003cf"
            "a001a200ad3c11c903901dd007ad3b11c9e8901438ad3b11e9e88d3b11ad3c11e9038d3c11e8d0dce000d004c000f00e8a1869308d3d11a2022003cf"
            "a001a200ad3c11c900901dd007ad3b11c964901438ad3b11e9648d3b11ad3c11e9008d3c11e8d0dce000d004c000f00e8a1869308d3d11a2022003cf"
            "a001a200ad3c11c900901dd007ad3b11c90a901438ad3b11e90a8d3b11ad3c11e9008d3c11e8d0dce000d004c000f00e8a1869308d3d11a2022003cf"
            "a001ad3b111869308d3d11a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "0000000048454c4c4f00"
        ),
        "expected_console": "HELLO\n7\n",
    },
    "int_vars_do_until": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-do-until",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'UNTIL X=2\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 33\n"
            "b dL0zL0p0aS0L0p1qtoe0r\n"
            "s DONE\n"
            "i 1\n"
            "i 2\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "ad8311ae84118d7f118e8011a9818502a9118503a000a200ad8011c927901dd007ad7f11c910901438ad7f11e9108d7f11ad8011e9278d8011e8d0dce000d004c000f00e8a1869308d8111a2022003cf"
            "a001a200ad8011c903901dd007ad7f11c9e8901438ad7f11e9e88d7f11ad8011e9038d8011e8d0dce000d004c000f00e8a1869308d8111a2022003cf"
            "a001a200ad8011c900901dd007ad7f11c964901438ad7f11e9648d7f11ad8011e9008d8011e8d0dce000d004c000f00e8a1869308d8111a2022003cf"
            "a001a200ad8011c900901dd007ad7f11c90a901438ad7f11e90a8d7f11ad8011e9008d8011e8d0dce000d004c000f00e8a1869308d8111a2022003cf"
            "a001ad7f111869308d8111a2022003cf2006cf"
            "ad8311ae84118d7f118e8011a901a200186d7f118d7f118a6d8011aaad7f118d83118e8411"
            "ad8311ae84118d7f118e8011a902a200ec8011d005cd7f11f0034c0010"
            "a9858502a9118503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000000000000444f4e4500"
        ),
        "expected_console": "0\n1\nDONE\n",
    },
    "int_vars_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[1]\r'
            'PROC MAIN()\r'
            'IF X=1 THEN\r'
            'PrintE("YES")\r'
            'ELSE\r'
            'PrintE("NO")\r'
            'FI\r'
            'X=X+1\r'
            'IF X=2 THEN\r'
            'PrintE("DONE")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 52\n"
            "b L0p0qhe0we1vL0p1aS0L0p2qhe2vr\n"
            "s YES\n"
            "s NO\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "v x 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "adaa10aeab108da8108ea910a901a200eca910d005cda810f0034c3010"
            "a9ac8502a9108503a2022003cf2006cf"
            "4c4010"
            "a9b08502a9108503a2022003cf2006cf"
            "adaa10aeab108da8108ea910a901a200186da8108da8108a6da910aaada8108daa108eab10"
            "adaa10aeab108da8108ea910a902a200eca910d005cda810f0034c9210"
            "a9b38502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00000100594553004e4f00444f4e4500"
        ),
        "expected_console": "YES\nDONE\n",
    },
    "int_vars_while": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-while",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC MAIN()\r'
            'WHILE X<2 DO\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 36\n"
            "b dL0p0lfL0zL0p1aS0xe0r\n"
            "s DONE\n"
            "i 2\n"
            "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "ad9811ae99118d92118e9311a902a200ec9311900dd007cd92119006f004a901d002"
            "a900a200c900d0034c6c11ad9811ae99118d92118e9311a9968502a9118503a000a2"
            "00ad9311c927901dd007ad9211c910901438ad9211e9108d9211ad9311e9278d9311"
            "e8d0dce000d004c000f00e8a1869308d9611a2022003cfa001a200ad9311c903901d"
            "d007ad9211c9e8901438ad9211e9e88d9211ad9311e9038d9311e8d0dce000d004c00"
            "0f00e8a1869308d9611a2022003cfa001a200ad9311c900901dd007ad9211c9649014"
            "38ad9211e9648d9211ad9311e9008d9311e8d0dce000d004c000f00e8a1869308d9611"
            "a2022003cfa001a200ad9311c900901dd007ad9211c90a901438ad9211e90a8d9211"
            "ad9311e9008d9311e8d0dce000d004c000f00e8a1869308d9611a2022003cfa001ad92"
            "111869308d9611a2022003cf2006cfad9811ae99118d92118e9311a901a200186d9211"
            "8d92118a6d9311aaad92118d98118e99114c0010a99a8502a9118503a2022003cf2006"
            "cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000000444f4e45"
            "00"
        ),
        "expected_console": "0\n1\nDONE\n",
    },
    "int_vars_branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-branch-calls",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'PROC HELLO()\r'
                'PrintE("HELLO")\r'
                'RETURN\r'
                'PROC BYE()\r'
                'PrintE("BYE")\r'
                'RETURN\r'
                'PROC MAIN()\r'
                'IF X=1 THEN\r'
                'HELLO()\r'
                'ELSE\r'
                'BYE()\r'
                'FI\r'
                'X=X+1\r'
                'IF X=2 THEN\r'
                'W()\r'
                'FI\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["MAIN"],
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x main 14 43\n"
            "b e0r\n"
            "b e1r\n"
            "b L0p0qhc0wc1vL0p1aS0L0p2qhu0vr\n"
            "u w\n"
            "s HELLO\n"
            "s BYE\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "v x 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010adcc11aecd118dc6118ec711a901a200ecc711d005cdc611f0034c23102081104c2610209210adcc11aecd118dc6118ec711a901a200186dc6118dc6118a6dc711aaadc6118dcc118ecd11adcc11aecd118dc6118ec711a902a200ecc711d005cdc611f0034c6b1020a3108dd1038ed203a9a58dd003a90085028503a2024c0fcfa9ce8502a9118503a2022003cf2006cf60a9d48502a9118503a2022003cf2006cf60a9d88502a9118503a2022003cfa907a2008dc6118ec711a9ca8502a9118503a000a200adc711c927901dd007adc611c910901438adc611e9108dc611adc711e9278dc711e8d0dce000d004c000f00e8a1869308dca11a2022003cfa001a200adc711c903901dd007adc611c9e8901438adc611e9e88dc611adc711e9038dc711e8d0dce000d004c000f00e8a1869308dca11a2022003cfa001a200adc711c900901dd007adc611c964901438adc611e9648dc611adc711e9008dc711e8d0dce000d004c000f00e8a1869308dca11a2022003cfa001a200adc711c900901dd007adc611c90a901438adc611e90a8dc611adc711e9008dc711e8d0dce000d004c000f00e8a1869308dca11a2022003cfa001adc6111869308dca11a2022003cf2006cf60000000000000010048454c4c4f0042594500544f4f4c00"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 89, 0, 14, 0, 1, 72, 0, 97, 74, 0, 73,
                16, 255, 72, 97, 80, 0, 73, 16, 255, 72, 19, 72, 0, 17,
                1, 0, 22, 24, 30, 0, 69, 0, 0, 25, 33, 0, 69, 7, 0, 19,
                72, 0, 17, 1, 0, 20, 18, 72, 0, 19, 72, 0, 17, 2, 0, 22,
                24, 56, 0, 69, 59, 0, 73, 32, 255, 97, 84, 0, 73, 0, 255,
                17, 7, 0, 73, 49, 255, 72, 1, 0, 72, 69, 76, 76, 79, 0,
                66, 89, 69, 0, 84, 79, 79, 76, 0,
            ]
        ),
        "expected_console": "HELLO\nTOOL7\n",
    },
    "int_vars_while_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-while-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC MAIN()\r'
            'WHILE X<1 DO\r'
            'W()\r'
            'X=X+1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 33\n"
            "b dL0p0lfu0L0p1aS0xe0r\n"
            "u w\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "v x 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ada711aea8118da1118ea211a901a200eca211900dd007cda1119006f004a901d002a900a200c900d0034c5810207e10ada711aea8118da1118ea211a901a200186da1118da1118a6da211aaada1118da7118ea8114c0010a9a98502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9ae8502a9118503a2022003cfa907a2008da1118ea211a9a58502a9118503a000a200ada211c927901dd007ada111c910901438ada111e9108da111ada211e9278da211e8d0dce000d004c000f00e8a1869308da511a2022003cfa001a200ada211c903901dd007ada111c9e8901438ada111e9e88da111ada211e9038da211e8d0dce000d004c000f00e8a1869308da511a2022003cfa001a200ada211c900901dd007ada111c964901438ada111e9648da111ada211e9008da211e8d0dce000d004c000f00e8a1869308da511a2022003cfa001a200ada211c900901dd007ada111c90a901438ada111e90a8da111ada211e9008da211e8d0dce000d004c000f00e8a1869308da511a2022003cfa001ada1111869308da511a2022003cf2006cf600000000000000000444f4e4500544f4f4c00"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 60, 0, 0, 0, 1, 48, 0, 19, 48, 0, 17,
                1, 0, 28, 24, 26, 0, 69, 35, 0, 19, 48, 0, 17, 1, 0, 20,
                18, 48, 0, 25, 0, 0, 97, 50, 0, 73, 16, 255, 73, 32, 255,
                97, 55, 0, 73, 0, 255, 17, 7, 0, 73, 49, 255, 72, 0, 0,
                68, 79, 78, 69, 0, 84, 79, 79, 76, 0,
            ]
        ),
        "expected_console": "TOOL7\nDONE\n",
    },
    "int_vars_multi_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-basic",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'INT Y=[2]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'PrintIE(Y)\r'
            'X=Y+1\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 29\n"
            "b L0zL1zL1p0aS0L0zr\n"
            "i 1\n"
            "v x 0\n"
            "v y 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad8613ae87138d80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfad8813ae89138d80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfad8813ae89138d80138e8113a901a200186d80138d80138a6d8113aaad80138d86138e8713ad8613ae87138d80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000000000000200"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 35, 0, 0, 0, 1, 31, 0, 19, 31, 0, 73,
                49, 255, 19, 33, 0, 73, 49, 255, 19, 33, 0, 17, 1, 0, 20,
                18, 31, 0, 19, 31, 0, 73, 49, 255, 73, 32, 255, 0, 0, 2, 0,
            ]
        ),
        "expected_console": "0\n2\n3\n",
    },
    "byte_card_vars_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-byte-card-vars-basic",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'BYTE X=[0]\r'
            'CARD Y=[2]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'PrintIE(Y)\r'
            'X=Y+1\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 29\n"
            "b L0zL1zL1p0aS0L0zr\n"
            "i 1\n"
            "v x 0\n"
            "v y 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad8613ae87138d80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e910"
            "8d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad"
            "8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001"
            "a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a18"
            "69308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8"
            "d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfad8813ae89138d"
            "80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d"
            "8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad80"
            "13e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901d"
            "d007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003"
            "cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f0"
            "0e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfad8813ae89138d80138e8113a901a200"
            "186d80138d80138a6d8113aaad80138d86138e8713ad8613ae87138d80138e8113a9848502a9138503a000a200ad8113"
            "c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413"
            "a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d0"
            "04c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad81"
            "13e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a90"
            "1438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869"
            "308d8413a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000000000000200"
        ),
        "expected_console": "0\n2\n3\n",
    },
    "real_decl_storage_width": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-decl-storage-width",
        "source": (
            'MODULE MAIN\r'
            'REAL X\r'
            'PROC MAIN()\r'
            'PrintIE(7)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b i0r\n"
            "i 7\n"
            "v x 0 4\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a907a2008d2b118e2c11a92f8502a9118503a000a200ad2c11c927901dd007"
            "ad2b11c910901438ad2b11e9108d2b11ad2c11e9278d2c11e8d0dce000d004c000"
            "f00e8a1869308d2f11a2022003cfa001a200ad2c11c903901dd007ad2b11c9e890"
            "1438ad2b11e9e88d2b11ad2c11e9038d2c11e8d0dce000d004c000f00e8a1869308"
            "d2f11a2022003cfa001a200ad2c11c900901dd007ad2b11c964901438ad2b11e964"
            "8d2b11ad2c11e9008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003c"
            "fa001a200ad2c11c900901dd007ad2b11c90a901438ad2b11e90a8d2b11ad2c11e9"
            "008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cfa001ad2b11186"
            "9308d2f11a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0f"
            "cf00000000000000000000"
        ),
        "expected_console": "7\n",
    },
    "real_zero_initializer": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-zero-initializer",
        "source": (
            'MODULE MAIN\r'
            'REAL X=[0]\r'
            'PROC MAIN()\r'
            'PrintIE(7)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b i0r\n"
            "i 7\n"
            "v x 0 4\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a907a2008d2b118e2c11a92f8502a9118503a000a200ad2c11c927901dd007"
            "ad2b11c910901438ad2b11e9108d2b11ad2c11e9278d2c11e8d0dce000d004c000"
            "f00e8a1869308d2f11a2022003cfa001a200ad2c11c903901dd007ad2b11c9e890"
            "1438ad2b11e9e88d2b11ad2c11e9038d2c11e8d0dce000d004c000f00e8a1869308"
            "d2f11a2022003cfa001a200ad2c11c900901dd007ad2b11c964901438ad2b11e964"
            "8d2b11ad2c11e9008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003c"
            "fa001a200ad2c11c900901dd007ad2b11c90a901438ad2b11e90a8d2b11ad2c11e9"
            "008d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cfa001ad2b11186"
            "9308d2f11a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0f"
            "cf00000000000000000000"
        ),
        "expected_console": "7\n",
    },
    "real_decl_offsets_following_int": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-decl-offsets-following-int",
        "source": (
            'MODULE MAIN\r'
            'REAL R\r'
            'INT X=[5]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b L1zr\n"
            "v r 0 4\n"
            "v x 5\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad3711ae38118d2d118e2e11a9318502a9118503a000a200ad2e11c927901d"
            "d007ad2d11c910901438ad2d11e9108d2d11ad2e11e9278d2e11e8d0dce000d004"
            "c000f00e8a1869308d3111a2022003cfa001a200ad2e11c903901dd007ad2d11c9"
            "e8901438ad2d11e9e88d2d11ad2e11e9038d2e11e8d0dce000d004c000f00e8a186"
            "9308d3111a2022003cfa001a200ad2e11c900901dd007ad2d11c964901438ad2d11"
            "e9648d2d11ad2e11e9008d2e11e8d0dce000d004c000f00e8a1869308d3111a2022"
            "003cfa001a200ad2e11c900901dd007ad2d11c90a901438ad2d11e90a8d2d11ad2e"
            "11e9008d2e11e8d0dce000d004c000f00e8a1869308d3111a2022003cfa001ad2d1"
            "11869308d3111a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a202"
            "4c0fcf000000000000000000000500"
        ),
        "expected_console": "5\n",
    },
    "real_copy_assignment_runtime": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-copy-assignment-runtime",
        "source": (
            'MODULE MAIN\r'
            'REAL A\r'
            'REAL R\r'
            'PROC MAIN()\r'
            'R=A\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 19\n"
            "b L0U0T1S1e0r\n"
            "s DONE\n"
            "v a 0 4\n"
            "v r 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad4e10ae4f108d4a108e4b10ad5010ae51108d54108e5510ad4a10ae4b108d52"
            "108e5310a9568502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085"
            "028503a2024c0fcf000000000000000000000000444f4e4500"
        ),
        "expected_console": "DONE\n",
    },
    "real_zero_assignment_runtime": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-zero-assignment-runtime",
        "source": (
            'MODULE MAIN\r'
            'REAL X\r'
            'PROC MAIN()\r'
            'X=0\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 19\n"
            "b p0p0T0S0e0r\n"
            "s DONE\n"
            "i 0\n"
            "v x 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a900a2008d46108e4710a900a2008d4c108e4d10ad4610ae47108d4a108e4b10"
            "a94e8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf0000000000000000444f4e4500"
        ),
        "expected_console": "DONE\n",
    },
    "real_small_expr_assignment_runtime": {
        "artifact_kind": "prg",
        "out_fs_name": "harness-actc-alink-direct-prg-real-small-expr-assignment-runtime",
        "source": (
            'MODULE MAIN\r'
            'REAL X\r'
            'PROC MAIN()\r'
            'X=(1+2*3)\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 19\n"
            "b p0p1T0S0e0r\n"
            "s DONE\n"
            "i 0\n"
            "i 16608\n"
            "v x 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a900a2008d46108e4710a9e0a2408d4c108e4d10ad4610ae47108d4a108e4b10"
            "a94e8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf0000000000000000444f4e4500"
        ),
        "expected_console": "DONE\n",
    },
    "runtime_library_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-runtime-library-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'RT_F_ADD()\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 16\n"
            "b e0u0e1r\n"
            "u rt_f_add\n"
            "s START\n"
            "s DONE\n"
            "k 2\n"
            "n main\n"
        ),
        "seed_library_objects": {
            "RT_F_ADD": (
                "AVO1\n"
                "x rt_f_add 0 7\n"
                "b e0r\n"
                "s FADD\n"
                "k 2\n"
                "n rt_f_add\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010a94e8502a9108503a2022003cf2006cf203910a9548502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003"
            "a90085028503a2024c0fcfa9598502a9108503a2022003cf2006cf6000000000535441525400444f4e45004641444400"
        ),
        "expected_console": "START\nFADD\nDONE\n",
    },
    "dead_runtime_library_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-dead-runtime-library-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC DEAD()\r'
            'RT_F_ADD()\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x dead 0 4\n"
            "x main 4 7\n"
            "b u0r\n"
            "b e0r\n"
            "u rt_f_add\n"
            "s DONE\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a92a8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000444f4e45"
            "00"
        ),
        "expected_console": "DONE\n",
    },
    "real_add_assignment_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-assignment-runtime",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'REAL A\r'
            'REAL B\r'
            'REAL R\r'
            'PROC MAIN()\r'
            'R=A+B\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 28\n"
            "b L0U0L1U1u0T2S2e0r\n"
            "u rt_f_add\n"
            "s DONE\n"
            "v a 0 4\n"
            "v b 0 4\n"
            "v r 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010ade610aee7108de0108ee110ade810aee9108de2108ee310adea10aeeb108de4108ee510adec10aeed102065108d"
            "f0108ef110ade010aee1108dee108eef10a9f28502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcf8daf3c8eb03ca9f78504a9108505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0"
            "f0a000c038f007b1049106c8d0f5ade0108da93cade1108daa3cade2108dab3cade3108dac3cade4108dad3cade5108d"
            "ae3ca9008dc23ca9018df83c200deaadb13c8de010adb23c8de110adb33caeb43c600000000000000000000000000000"
            "00000000444f4e450041564f560100ea0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860ad"
            "c23cf008adb03c49808db03c20b0ea200aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c"
            "0daa3cd0052026ed1860ada93c8dca3cadaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3cee"
            "c73c4c7beaa98e38edc73c8dbd3ca9008db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0d"
            "ab3c0dac3cd015a9008dbd3c8dbf3c8db53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c"
            "2980f003eebd3cada93c8db53cadaa3c8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd0"
            "15a9008dbe3c8dc03c8db93c8dba3c8dbb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe"
            "3cadad3c8db93cadae3c8dba3cadaf3c297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3c"
            "cdbd3c9012d00dadbf3ccdc03cf00820aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8"
            "e006d0f3adb53c8dcb3cadb63c8dcc3cadb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cac"
            "c13cf010209cf19008add03c09018dd03c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09"
            "018dca3ceebd3cd0034c26ed4c49ec20fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d012"
            "2063f1cebd3cd0034c26edadcd3c2980f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd0"
            "08eece3cd003eecf3cadcf3c0dce3cf0222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed"
            "4ca4ecadbd3cc9ffd0034c26edadcb3c8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8d"
            "b13cadb63c8db23cadb73c297f8db33cadbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db1"
            "3cadaa3c8db23cadab3c8db33cadac3c8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9"
            "008db13c8db23c8db33c8db43c1860adbd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca9006900"
            "8dc93cadc83c38e97f8dc83cadc93ce9008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cad"
            "b73c8dd23ca9188dc73cadb93c2901f00320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd0"
            "03eec93ca9188dc73ca9008dd63cadcc3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63c"
            "d02ca9178dc73ca9008dd63cadcc3c2940f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076"
            "f1cec73cd0f8add63cf024eeca3cd01feecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cad"
            "c93cd02dadc83cf028c9fff0248dbd3cadca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbe"
            "ec4c26edadbd3cf008adbe3cf0034c8bee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e900"
            "8dc93c18adc83c697e8dc83cadc93c69008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc8"
            "3c697f8dc83cadc93c69008dc93ca9178dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb5"
            "3c8dca3cadb63c8dcb3cadb73c8dcc3c2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c20"
            "89f1cec73cd0f8a9188dc73c0ed63c2ed73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd8"
            "3cd0034c24f02034f1905badcf3ccdd53cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd1"
            "3cd00fadca3ccdd03cd007add63c2901f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec8"
            "3cd003eec93cadd83c2980d0250ed63c2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980"
            "f0dbadc93cd026adc83cf021c9fff01d8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26ed"
            "adbd3cd008a90085f585f61860c97fb008a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb"
            "3cadb73c8dcc3ca9008dcd3ca91738edc73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0d"
            "cd3cf0023860adbf3cf01fadcb3cc9809007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cad"
            "ca3c85f5adcb3c85f61860386018adca3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8d"
            "cd3cadce3c6dd43c8dce3cadcf3c6dd53c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc"
            "3cadcd3cedd33c8dcd3cadce3cedd43c8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3c"
            "cdd33cd016adcc3ccdd23cd00eadcb3ccdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604e"
            "cf3c6ece3c6ecd3c6ecc3c6ecb3c6eca3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed2"
            "3c6ed13c6ed03c60adb83ccdbc3cd016adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf"
            "3c688dc03cadbd3c48adbe3c8dbd3c688dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8d"
            "a93c688dad3cadaa3c48adae3c8daa3c688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c"
            "60"
        ),
        "expected_console": "DONE\n",
    },
    "real_add_left_zero_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-left-zero-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 20\n"
                "b p0p0p1p0u0Kzr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 123\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2008dcf118ed011a97ba2008dd1118ed211a900a200205211adcd11aece118dd311"
            "8ed411a9d58502a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411"
            "e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9"
            "e88dd311add411e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007"
            "add311c964901438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa0"
            "01a200add411c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a"
            "1869308dd511a2022003cfa001add3111869308dd511a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "123\n",
    },
    "real_add_two_plus_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-two-plus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16512\n",
    },
    "real_add_one_plus_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-plus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16384\n",
    },
    "real_add_four_plus_four_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-four-plus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16640\n",
    },
    "real_add_one_point_five_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-point-five-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16320\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a9c0a23f8dcf118ed011a900a2008dd1118ed211a9c0a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_add_negative_two_plus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-two-plus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49280\n",
    },
    "real_add_two_plus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-two-plus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16384\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "0\n",
    },
    "real_add_two_plus_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-two-plus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16384\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_add_one_plus_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-plus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16256\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_add_negative_two_plus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-two-plus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49152\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_add_two_plus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-two-plus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16384\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16256\n",
    },
    "real_add_one_plus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-plus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16256\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49024\n",
    },
    "real_add_negative_two_plus_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-two-plus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49152\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49024\n",
    },
    "real_add_negative_one_plus_two_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-one-plus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49024\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2bf8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16256\n",
    },
    "real_add_four_plus_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-four-plus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16512\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16544\n",
    },
    "real_add_one_plus_four_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-plus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16256\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16544\n",
    },
    "real_add_negative_four_plus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-four-plus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49280\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49312\n",
    },
    "real_add_four_plus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-four-plus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16512\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '16448\n',
    },
    "real_add_one_plus_negative_four_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-one-plus-negative-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 16256\n"
                "i 49280\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a980a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '49216\n',
    },
    "real_add_negative_four_plus_one_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-four-plus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49280\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '49216\n',
    },
    "real_add_negative_one_plus_four_runtime": {
        "out_fs_name": "harness-actc-alink-avmrunc-real-add-negative-one-plus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_add\n"
                "i 0\n"
                "i 49024\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2bf8dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '16448\n',
    },
    "real_sub_assignment_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-assignment-runtime",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'REAL A\r'
            'REAL B\r'
            'REAL R\r'
            'PROC MAIN()\r'
            'R=A-B\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 28\n"
            "b L0U0L1U1u0T2S2e0r\n"
            "u rt_f_sub\n"
            "s DONE\n"
            "v a 0 4\n"
            "v b 0 4\n"
            "v r 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010ade610aee7108de0108ee110ade810aee9108de2108ee310adea10aeeb108de4108ee510adec10aeed102065108d"
            "f0108ef110ade010aee1108dee108eef10a9f28502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcf8daf3c8eb03ca9f78504a9108505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0"
            "f0a000c038f007b1049106c8d0f5ade0108da93cade1108daa3cade2108dab3cade3108dac3cade4108dad3cade5108d"
            "ae3ca9018dc23ca9018df83c200deaadb13c8de010adb23c8de110adb33caeb43c600000000000000000000000000000"
            "00000000444f4e450041564f560100ea0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860ad"
            "c23cf008adb03c49808db03c20b0ea200aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c"
            "0daa3cd0052026ed1860ada93c8dca3cadaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3cee"
            "c73c4c7beaa98e38edc73c8dbd3ca9008db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0d"
            "ab3c0dac3cd015a9008dbd3c8dbf3c8db53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c"
            "2980f003eebd3cada93c8db53cadaa3c8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd0"
            "15a9008dbe3c8dc03c8db93c8dba3c8dbb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe"
            "3cadad3c8db93cadae3c8dba3cadaf3c297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3c"
            "cdbd3c9012d00dadbf3ccdc03cf00820aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8"
            "e006d0f3adb53c8dcb3cadb63c8dcc3cadb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cac"
            "c13cf010209cf19008add03c09018dd03c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09"
            "018dca3ceebd3cd0034c26ed4c49ec20fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d012"
            "2063f1cebd3cd0034c26edadcd3c2980f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd0"
            "08eece3cd003eecf3cadcf3c0dce3cf0222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed"
            "4ca4ecadbd3cc9ffd0034c26edadcb3c8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8d"
            "b13cadb63c8db23cadb73c297f8db33cadbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db1"
            "3cadaa3c8db23cadab3c8db33cadac3c8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9"
            "008db13c8db23c8db33c8db43c1860adbd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca9006900"
            "8dc93cadc83c38e97f8dc83cadc93ce9008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cad"
            "b73c8dd23ca9188dc73cadb93c2901f00320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd0"
            "03eec93ca9188dc73ca9008dd63cadcc3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63c"
            "d02ca9178dc73ca9008dd63cadcc3c2940f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076"
            "f1cec73cd0f8add63cf024eeca3cd01feecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cad"
            "c93cd02dadc83cf028c9fff0248dbd3cadca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbe"
            "ec4c26edadbd3cf008adbe3cf0034c8bee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e900"
            "8dc93c18adc83c697e8dc83cadc93c69008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc8"
            "3c697f8dc83cadc93c69008dc93ca9178dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb5"
            "3c8dca3cadb63c8dcb3cadb73c8dcc3c2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c20"
            "89f1cec73cd0f8a9188dc73c0ed63c2ed73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd8"
            "3cd0034c24f02034f1905badcf3ccdd53cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd1"
            "3cd00fadca3ccdd03cd007add63c2901f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec8"
            "3cd003eec93cadd83c2980d0250ed63c2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980"
            "f0dbadc93cd026adc83cf021c9fff01d8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26ed"
            "adbd3cd008a90085f585f61860c97fb008a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb"
            "3cadb73c8dcc3ca9008dcd3ca91738edc73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0d"
            "cd3cf0023860adbf3cf01fadcb3cc9809007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cad"
            "ca3c85f5adcb3c85f61860386018adca3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8d"
            "cd3cadce3c6dd43c8dce3cadcf3c6dd53c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc"
            "3cadcd3cedd33c8dcd3cadce3cedd43c8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3c"
            "cdd33cd016adcc3ccdd23cd00eadcb3ccdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604e"
            "cf3c6ece3c6ecd3c6ecc3c6ecb3c6eca3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed2"
            "3c6ed13c6ed03c60adb83ccdbc3cd016adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf"
            "3c688dc03cadbd3c48adbe3c8dbd3c688dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8d"
            "a93c688dad3cadaa3c48adae3c8daa3c688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c"
            "60"
        ),
        "expected_console": "DONE\n",
    },
    "real_sub_two_minus_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-two-minus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16384\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16256\n",
    },
    "real_sub_two_minus_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-two-minus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "0\n",
    },
    "real_sub_zero_minus_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-zero-minus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p0p0p1u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2008dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49024\n",
    },
    "real_sub_negative_two_minus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-two-minus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "0\n",
    },
    "real_sub_zero_minus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-zero-minus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p0p0p1u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2008dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16256\n",
    },
    "real_sub_four_minus_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-four-minus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16512\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16384\n",
    },
    "real_sub_two_minus_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-two-minus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16384\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49152\n",
    },
    "real_sub_negative_four_minus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-four-minus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49280\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49152\n",
    },
    "real_sub_four_minus_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-four-minus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16512\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_sub_one_minus_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-one-minus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16256\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_sub_negative_four_minus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-four-minus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49280\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_sub_two_minus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-two-minus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16384\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_sub_one_minus_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-one-minus-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16256\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_sub_negative_two_minus_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-two-minus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49152\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_sub_negative_one_minus_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-one-minus-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49024\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2bf8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_sub_four_minus_negative_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-four-minus-negative-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16512\n"
                "i 49024\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a980a2bf2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '16544\n',
    },
    "real_sub_one_minus_negative_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-one-minus-negative-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 16256\n"
                "i 49280\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a980a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '16544\n',
    },
    "real_sub_negative_four_minus_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-four-minus-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49280\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '49312\n',
    },
    "real_sub_negative_one_minus_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-sub-negative-one-minus-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_sub\n"
                "i 0\n"
                "i 49024\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2bf8dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "018dc23ca9018df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": '49312\n',
    },
    "real_mul_assignment_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-assignment-runtime",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'REAL A\r'
            'REAL B\r'
            'REAL R\r'
            'PROC MAIN()\r'
            'R=A*B\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 28\n"
            "b L0U0L1U1u0T2S2e0r\n"
            "u rt_f_mul\n"
            "s DONE\n"
            "v a 0 4\n"
            "v b 0 4\n"
            "v r 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010ade610aee7108de0108ee110ade810aee9108de2108ee310adea10aeeb108de4108ee510adec10aeed102065108d"
            "f0108ef110ade010aee1108dee108eef10a9f28502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcf8daf3c8eb03ca9f78504a9108505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0"
            "f0a000c038f007b1049106c8d0f5ade0108da93cade1108daa3cade2108dab3cade3108dac3cade4108dad3cade5108d"
            "ae3ca9008dc23ca9028df83c200deaadb13c8de010adb23c8de110adb33caeb43c600000000000000000000000000000"
            "00000000444f4e450041564f560100ea0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860ad"
            "c23cf008adb03c49808db03c20b0ea200aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c"
            "0daa3cd0052026ed1860ada93c8dca3cadaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3cee"
            "c73c4c7beaa98e38edc73c8dbd3ca9008db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0d"
            "ab3c0dac3cd015a9008dbd3c8dbf3c8db53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c"
            "2980f003eebd3cada93c8db53cadaa3c8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd0"
            "15a9008dbe3c8dc03c8db93c8dba3c8dbb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe"
            "3cadad3c8db93cadae3c8dba3cadaf3c297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3c"
            "cdbd3c9012d00dadbf3ccdc03cf00820aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8"
            "e006d0f3adb53c8dcb3cadb63c8dcc3cadb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cac"
            "c13cf010209cf19008add03c09018dd03c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09"
            "018dca3ceebd3cd0034c26ed4c49ec20fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d012"
            "2063f1cebd3cd0034c26edadcd3c2980f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd0"
            "08eece3cd003eecf3cadcf3c0dce3cf0222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed"
            "4ca4ecadbd3cc9ffd0034c26edadcb3c8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8d"
            "b13cadb63c8db23cadb73c297f8db33cadbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db1"
            "3cadaa3c8db23cadab3c8db33cadac3c8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9"
            "008db13c8db23c8db33c8db43c1860adbd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca9006900"
            "8dc93cadc83c38e97f8dc83cadc93ce9008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cad"
            "b73c8dd23ca9188dc73cadb93c2901f00320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd0"
            "03eec93ca9188dc73ca9008dd63cadcc3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63c"
            "d02ca9178dc73ca9008dd63cadcc3c2940f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076"
            "f1cec73cd0f8add63cf024eeca3cd01feecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cad"
            "c93cd02dadc83cf028c9fff0248dbd3cadca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbe"
            "ec4c26edadbd3cf008adbe3cf0034c8bee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e900"
            "8dc93c18adc83c697e8dc83cadc93c69008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc8"
            "3c697f8dc83cadc93c69008dc93ca9178dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb5"
            "3c8dca3cadb63c8dcb3cadb73c8dcc3c2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c20"
            "89f1cec73cd0f8a9188dc73c0ed63c2ed73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd8"
            "3cd0034c24f02034f1905badcf3ccdd53cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd1"
            "3cd00fadca3ccdd03cd007add63c2901f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec8"
            "3cd003eec93cadd83c2980d0250ed63c2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980"
            "f0dbadc93cd026adc83cf021c9fff01d8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26ed"
            "adbd3cd008a90085f585f61860c97fb008a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb"
            "3cadb73c8dcc3ca9008dcd3ca91738edc73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0d"
            "cd3cf0023860adbf3cf01fadcb3cc9809007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cad"
            "ca3c85f5adcb3c85f61860386018adca3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8d"
            "cd3cadce3c6dd43c8dce3cadcf3c6dd53c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc"
            "3cadcd3cedd33c8dcd3cadce3cedd43c8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3c"
            "cdd33cd016adcc3ccdd23cd00eadcb3ccdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604e"
            "cf3c6ece3c6ecd3c6ecc3c6ecb3c6eca3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed2"
            "3c6ed13c6ed03c60adb83ccdbc3cd016adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf"
            "3c688dc03cadbd3c48adbe3c8dbd3c688dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8d"
            "a93c688dad3cadaa3c48adae3c8daa3c688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c"
            "60"
        ),
        "expected_console": "DONE\n",
    },
    "real_mul_two_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-two-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16512\n",
    },
    "real_mul_four_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-four-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16512\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16640\n",
    },
    "real_mul_one_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-one-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16256\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a23f8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16384\n",
    },
    "real_mul_zero_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-zero-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p0p0p1u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2008dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "0\n",
    },
    "real_mul_negative_two_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-negative-two-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 49152\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49280\n",
    },
    "real_mul_negative_two_times_negative_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-negative-two-times-negative-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p1u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 49152\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2c08dcf118ed011a900a2008dd1118ed211a900a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16512\n",
    },
    "real_mul_one_point_five_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-one-point-five-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16320\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a9c0a23f8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_mul_two_times_one_point_five_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-two-times-one-point-five-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 16384\n"
                "i 16320\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a9c0a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16448\n",
    },
    "real_mul_negative_one_point_five_times_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-mul-negative-one-point-five-times-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_mul\n"
                "i 0\n"
                "i 49088\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a9c0a2bf8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9028df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49216\n",
    },
    "real_div_assignment_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-assignment-runtime",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'REAL A\r'
            'REAL B\r'
            'REAL R\r'
            'PROC MAIN()\r'
            'R=A/B\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 28\n"
            "b L0U0L1U1u0T2S2e0r\n"
            "u rt_f_div\n"
            "s DONE\n"
            "v a 0 4\n"
            "v b 0 4\n"
            "v r 0 4\n"
            "k 2\n"
            "n main\n"
        ),
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010ade610aee7108de0108ee110ade810aee9108de2108ee310adea10aeeb108de4108ee510adec10aeed102065108d"
            "f0108ef110ade010aee1108dee108eef10a9f28502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcf8daf3c8eb03ca9f78504a9108505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0"
            "f0a000c038f007b1049106c8d0f5ade0108da93cade1108daa3cade2108dab3cade3108dac3cade4108dad3cade5108d"
            "ae3ca9008dc23ca9038df83c200deaadb13c8de010adb23c8de110adb33caeb43c600000000000000000000000000000"
            "00000000444f4e450041564f560100ea0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860ad"
            "c23cf008adb03c49808db03c20b0ea200aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c"
            "0daa3cd0052026ed1860ada93c8dca3cadaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3cee"
            "c73c4c7beaa98e38edc73c8dbd3ca9008db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0d"
            "ab3c0dac3cd015a9008dbd3c8dbf3c8db53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c"
            "2980f003eebd3cada93c8db53cadaa3c8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd0"
            "15a9008dbe3c8dc03c8db93c8dba3c8dbb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe"
            "3cadad3c8db93cadae3c8dba3cadaf3c297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3c"
            "cdbd3c9012d00dadbf3ccdc03cf00820aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8"
            "e006d0f3adb53c8dcb3cadb63c8dcc3cadb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cac"
            "c13cf010209cf19008add03c09018dd03c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09"
            "018dca3ceebd3cd0034c26ed4c49ec20fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d012"
            "2063f1cebd3cd0034c26edadcd3c2980f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd0"
            "08eece3cd003eecf3cadcf3c0dce3cf0222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed"
            "4ca4ecadbd3cc9ffd0034c26edadcb3c8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8d"
            "b13cadb63c8db23cadb73c297f8db33cadbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db1"
            "3cadaa3c8db23cadab3c8db33cadac3c8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9"
            "008db13c8db23c8db33c8db43c1860adbd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca9006900"
            "8dc93cadc83c38e97f8dc83cadc93ce9008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cad"
            "b73c8dd23ca9188dc73cadb93c2901f00320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd0"
            "03eec93ca9188dc73ca9008dd63cadcc3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63c"
            "d02ca9178dc73ca9008dd63cadcc3c2940f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076"
            "f1cec73cd0f8add63cf024eeca3cd01feecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cad"
            "c93cd02dadc83cf028c9fff0248dbd3cadca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbe"
            "ec4c26edadbd3cf008adbe3cf0034c8bee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e900"
            "8dc93c18adc83c697e8dc83cadc93c69008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc8"
            "3c697f8dc83cadc93c69008dc93ca9178dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb5"
            "3c8dca3cadb63c8dcb3cadb73c8dcc3c2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c20"
            "89f1cec73cd0f8a9188dc73c0ed63c2ed73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd8"
            "3cd0034c24f02034f1905badcf3ccdd53cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd1"
            "3cd00fadca3ccdd03cd007add63c2901f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec8"
            "3cd003eec93cadd83c2980d0250ed63c2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980"
            "f0dbadc93cd026adc83cf021c9fff01d8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26ed"
            "adbd3cd008a90085f585f61860c97fb008a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb"
            "3cadb73c8dcc3ca9008dcd3ca91738edc73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0d"
            "cd3cf0023860adbf3cf01fadcb3cc9809007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cad"
            "ca3c85f5adcb3c85f61860386018adca3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8d"
            "cd3cadce3c6dd43c8dce3cadcf3c6dd53c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc"
            "3cadcd3cedd33c8dcd3cadce3cedd43c8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3c"
            "cdd33cd016adcc3ccdd23cd00eadcb3ccdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604e"
            "cf3c6ece3c6ecd3c6ecc3c6ecb3c6eca3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed2"
            "3c6ed13c6ed03c60adb83ccdbc3cd016adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf"
            "3c688dc03cadbd3c48adbe3c8dbd3c688dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8d"
            "a93c688dad3cadaa3c48adae3c8daa3c688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c"
            "60"
        ),
        "expected_console": "DONE\n",
    },
    "real_div_four_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-four-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16512\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16384\n",
    },
    "real_div_eight_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-eight-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16640\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2418dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16512\n",
    },
    "real_div_two_div_one_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-two-div-one-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16384\n"
                "i 16256\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a23f2052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16384\n",
    },
    "real_div_two_div_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-two-div-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16384\n"
                "i 16512\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16128\n",
    },
    "real_div_zero_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-zero-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p0p0p1u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2008dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "0\n",
    },
    "int_vars_multi_while": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-while",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'INT Y=[2]\r'
            'PROC MAIN()\r'
            'WHILE X<Y DO\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'OD\r'
            'PrintIE(Y)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 36\n"
            "b dL0L1lfL0zL0p0aS0xL1zr\n"
            "i 1\n"
            "v x 0\n"
            "v y 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ada112aea2128d9b128e9c12ada312aea412ec9c12900dd007cd9b129006f004a901d002a900a200c900d0034c6e11ada112aea2128d9b128e9c12a99f8502a9128503a000a200ad9c12c927901dd007ad9b12c910901438ad9b12e9108d9b12ad9c12e9278d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c903901dd007ad9b12c9e8901438ad9b12e9e88d9b12ad9c12e9038d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c900901dd007ad9b12c964901438ad9b12e9648d9b12ad9c12e9008d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c900901dd007ad9b12c90a901438ad9b12e90a8d9b12ad9c12e9008d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001ad9b121869308d9f12a2022003cf2006cfada112aea2128d9b128e9c12a901a200186d9b128d9b128a6d9c12aaad9b128da1128ea2124c0010ada312aea4128d9b128e9c12a99f8502a9128503a000a200ad9c12c927901dd007ad9b12c910901438ad9b12e9108d9b12ad9c12e9278d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c903901dd007ad9b12c9e8901438ad9b12e9e88d9b12ad9c12e9038d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c900901dd007ad9b12c964901438ad9b12e9648d9b12ad9c12e9008d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001a200ad9c12c900901dd007ad9b12c90a901438ad9b12e90a8d9b12ad9c12e9008d9c12e8d0dce000d004c000f00e8a1869308d9f12a2022003cfa001ad9b121869308d9f12a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000000000000200"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 42, 0, 0, 0, 1, 38, 0, 19, 38, 0, 19,
                40, 0, 28, 24, 29, 0, 19, 38, 0, 73, 49, 255, 19, 38, 0,
                17, 1, 0, 20, 18, 38, 0, 25, 0, 0, 19, 40, 0, 73, 49, 255,
                73, 32, 255, 0, 0, 2, 0,
            ]
        ),
        "expected_console": "0\n1\n2\n",
    },
    "int_vars_multi_branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-branch-calls",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC HELLO()\r'
                'PrintE("HELLO")\r'
                'RETURN\r'
                'PROC MAIN()\r'
                'IF X<Y THEN\r'
                'HELLO()\r'
                'W()\r'
                'FI\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["MAIN"],
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 17\n"
            "b e0r\n"
            "b L0L1lhc0u0vr\n"
            "u w\n"
            "s HELLO\n"
            "v x 1\n"
            "v y 2\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad8511ae86118d7f118e8011ad8711ae8811ec8011900dd007cd7f119006f004a901d002a900a200c900d0034c3510204b10205c108dd1038ed203a9a58dd003a90085028503a2024c0fcfa9898502a9118503a2022003cf2006cf60a98f8502a9118503a2022003cfa907a2008d7f118e8011a9838502a9118503a000a200ad8011c927901dd007ad7f11c910901438ad7f11e9108d7f11ad8011e9278d8011e8d0dce000d004c000f00e8a1869308d8311a2022003cfa001a200ad8011c903901dd007ad7f11c9e8901438ad7f11e9e88d7f11ad8011e9038d8011e8d0dce000d004c000f00e8a1869308d8311a2022003cfa001a200ad8011c900901dd007ad7f11c964901438ad7f11e9648d7f11ad8011e9008d8011e8d0dce000d004c000f00e8a1869308d8311a2022003cfa001a200ad8011c900901dd007ad7f11c90a901438ad7f11e90a8d7f11ad8011e9008d8011e8d0dce000d004c000f00e8a1869308d8311a2022003cfa001ad7f111869308d8311a2022003cf2006cf600000000000000100020048454c4c4f00544f4f4c00"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 54, 0, 7, 0, 1, 39, 0, 97, 43, 0, 73,
                16, 255, 72, 19, 39, 0, 19, 41, 0, 28, 24, 23, 0, 69, 0,
                0, 69, 26, 0, 73, 32, 255, 97, 49, 0, 73, 0, 255, 17, 7,
                0, 73, 49, 255, 72, 1, 0, 2, 0, 72, 69, 76, 76, 79, 0, 84,
                79, 79, 76, 0,
            ]
        ),
        "expected_console": "HELLO\nTOOL7\n",
    },
    "int_vars_multi_branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-branch-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'IF X<Y THEN\r'
                'W()\r'
                'Q()\r'
                'FI\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Q", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 23\n"
                "b L0L1lhu0u1ve0r\n"
                "u w\n"
                "u q\n"
                "s DONE\n"
                "v x 1\n"
                "v y 2\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010ad9810ae99108d94108e9510ad9a10ae9b10ec9510900dd007cd94109006f004a901d002a900a200c900d0034c3510205b10206f10a99c8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9a18502a9108503a2022003cf2006cf20831060a9a68502a9108503a2022003cf2006cf20831060a9ab8502a9108503a2022003cf2006cf600000000001000200444f4e45004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 75, 0, 0, 0, 1, 52, 0, 19, 52, 0, 19,
                54, 0, 28, 24, 16, 0, 69, 25, 0, 69, 35, 0, 97, 56, 0, 73,
                16, 255, 73, 32, 255, 97, 61, 0, 73, 16, 255, 69, 45, 0,
                72, 97, 66, 0, 73, 16, 255, 69, 45, 0, 72, 97, 71, 0, 73,
                16, 255, 72, 1, 0, 2, 0, 68, 79, 78, 69, 0, 77, 73, 68, 49,
                0, 77, 73, 68, 50, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nDONE\n",
    },
    "int_vars_multi_while_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-while-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[0]\r'
                'INT Y=[1]\r'
                'PROC MAIN()\r'
                'WHILE X<Y DO\r'
                'W()\r'
                'Q()\r'
                'X=X+1\r'
                'OD\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Q", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 36\n"
                "b dL0L1lfu0u1L0p0aS0xe0r\n"
                "u w\n"
                "u q\n"
                "s DONE\n"
                "i 1\n"
                "v x 0\n"
                "v y 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010adc010aec1108dbc108ebd10adc210aec310ecbd10900dd007cdbc109006f004a901d002a900a200c900d0034c5d10208310209710adc010aec1108dbc108ebd10a901a200186dbc108dbc108a6dbd10aaadbc108dc0108ec1104c0010a9c48502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9c98502a9108503a2022003cf2006cf20ab1060a9ce8502a9108503a2022003cf2006cf20ab1060a9d38502a9108503a2022003cf2006cf600000000000000100444f4e45004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 88, 0, 0, 0, 1, 65, 0, 19, 65, 0, 19,
                67, 0, 28, 24, 29, 0, 69, 38, 0, 69, 48, 0, 19, 65, 0, 17,
                1, 0, 20, 18, 65, 0, 25, 0, 0, 97, 69, 0, 73, 16, 255, 73,
                32, 255, 97, 74, 0, 73, 16, 255, 69, 58, 0, 72, 97, 79, 0,
                73, 16, 255, 69, 58, 0, 72, 97, 84, 0, 73, 16, 255, 72, 0,
                0, 1, 0, 68, 79, 78, 69, 0, 77, 73, 68, 49, 0, 77, 73, 68,
                50, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nDONE\n",
    },
    "int_vars_multi_add_rhs_var": {
        "out_fs_name": "harness-actc-alink-direct-prg-int-vars-multi-add-rhs-var",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[1]\r'
            'INT Y=[2]\r'
            'PROC MAIN()\r'
            'X=X+Y\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 17\n"
            "b L0L1aS0L0zr\n"
            "v x 1\n"
            "v y 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad5a11ae5b118d54118e5511ad5c11ae5d11186d54118d54118a6d5511aaad54118d5a118e5b11ad5a11ae5b118d54118e5511a9588502a9118503a000a200ad5511c927901dd007ad5411c910901438ad5411e9108d5411ad5511e9278d5511e8d0dce000d004c000f00e8a1869308d5811a2022003cfa001a200ad5511c903901dd007ad5411c9e8901438ad5411e9e88d5411ad5511e9038d5511e8d0dce000d004c000f00e8a1869308d5811a2022003cfa001a200ad5511c900901dd007ad5411c964901438ad5411e9648d5411ad5511e9008d5511e8d0dce000d004c000f00e8a1869308d5811a2022003cfa001a200ad5511c900901dd007ad5411c90a901438ad5411e90a8d5411ad5511e9008d5511e8d0dce000d004c000f00e8a1869308d5811a2022003cfa001ad54111869308d5811a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000000001000200"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 23, 0, 0, 0, 1, 19, 0, 19, 19, 0, 19,
                21, 0, 20, 18, 19, 0, 19, 19, 0, 73, 49, 255, 73, 32, 255,
                1, 0, 2, 0,
            ]
        ),
        "expected_console": "3\n",
    },
    "return_local_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-local-basic",
        "source": (
            'MODULE MAIN\r'
            'PROC TWO()\r'
            'RETURN 2\r'
            'PROC MAIN()\r'
            'PrintIE(TWO())\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x two 0 4\n"
            "x main 4 7\n"
            "b p0r\n"
            "b c0zr\n"
            "i 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 13, 0, 4, 0, 1, 13, 0, 17, 2, 0, 72,
                69, 0, 0, 73, 49, 255, 73, 32, 255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 42, 17, 141, 47, 17, 142, 48, 17, 169, 51, 133, 2, 169,
                17, 133, 3, 160, 0, 162, 0, 173, 48, 17, 201, 39, 144, 29, 208, 7,
                173, 47, 17, 201, 16, 144, 20, 56, 173, 47, 17, 233, 16, 141, 47, 17,
                173, 48, 17, 233, 39, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 48, 17, 201, 3, 144, 29, 208, 7, 173, 47, 17, 201,
                232, 144, 20, 56, 173, 47, 17, 233, 232, 141, 47, 17, 173, 48, 17, 233,
                3, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                48, 17, 201, 0, 144, 29, 208, 7, 173, 47, 17, 201, 100, 144, 20, 56,
                173, 47, 17, 233, 100, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 48, 17, 201, 0,
                144, 29, 208, 7, 173, 47, 17, 201, 10, 144, 20, 56, 173, 47, 17, 233,
                10, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 160, 1, 173, 47, 17, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208,
                3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 2, 162, 0,
                96, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "2\n",
    },
    "return_local_add": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-local-add",
        "source": (
            'MODULE MAIN\r'
            'PROC TWO()\r'
            'RETURN 2\r'
            'PROC THREE()\r'
            'RETURN 3\r'
            'PROC MAIN()\r'
            'PrintIE(TWO()+THREE())\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x two 0 4\n"
            "x three 4 4\n"
            "x main 8 11\n"
            "b p0r\n"
            "b p1r\n"
            "b c0c1azr\n"
            "i 2\n"
            "i 3\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 21, 0, 8, 0, 1, 21, 0, 17, 2, 0, 72,
                17, 3, 0, 72, 69, 0, 0, 69, 4, 0, 20, 73, 49, 255, 73, 32,
                255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 66, 17, 141, 76, 17, 142, 77, 17, 32, 71, 17, 24, 109,
                76, 17, 141, 76, 17, 138, 109, 77, 17, 170, 173, 76, 17, 141, 76, 17,
                142, 77, 17, 169, 80, 133, 2, 169, 17, 133, 3, 160, 0, 162, 0, 173,
                77, 17, 201, 39, 144, 29, 208, 7, 173, 76, 17, 201, 16, 144, 20, 56,
                173, 76, 17, 233, 16, 141, 76, 17, 173, 77, 17, 233, 39, 141, 77, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                80, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 77, 17, 201, 3,
                144, 29, 208, 7, 173, 76, 17, 201, 232, 144, 20, 56, 173, 76, 17, 233,
                232, 141, 76, 17, 173, 77, 17, 233, 3, 141, 77, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 80, 17, 162, 2,
                32, 3, 207, 160, 1, 162, 0, 173, 77, 17, 201, 0, 144, 29, 208, 7,
                173, 76, 17, 201, 100, 144, 20, 56, 173, 76, 17, 233, 100, 141, 76, 17,
                173, 77, 17, 233, 0, 141, 77, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 80, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 77, 17, 201, 0, 144, 29, 208, 7, 173, 76, 17, 201,
                10, 144, 20, 56, 173, 76, 17, 233, 10, 141, 76, 17, 173, 77, 17, 233,
                0, 141, 77, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 80, 17, 162, 2, 32, 3, 207, 160, 1, 173, 76, 17,
                24, 105, 48, 141, 80, 17, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209,
                3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162,
                2, 76, 15, 207, 169, 2, 162, 0, 96, 169, 3, 162, 0, 96, 0, 0,
                0, 0, 0, 0,
            ]
        ),
        "expected_console": "5\n",
    },
    "return_external_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-external-basic",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintIE(W())\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'RETURN 7\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 7\n"
                "b u0zr\n"
                "u w\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 4\n"
                "b p0r\n"
                "i 7\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 13, 0, 0, 0, 1, 13, 0, 69, 9, 0, 73,
                49, 255, 73, 32, 255, 17, 7, 0, 72,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 42, 17, 141, 47, 17, 142, 48, 17, 169, 51, 133, 2, 169,
                17, 133, 3, 160, 0, 162, 0, 173, 48, 17, 201, 39, 144, 29, 208, 7,
                173, 47, 17, 201, 16, 144, 20, 56, 173, 47, 17, 233, 16, 141, 47, 17,
                173, 48, 17, 233, 39, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 48, 17, 201, 3, 144, 29, 208, 7, 173, 47, 17, 201,
                232, 144, 20, 56, 173, 47, 17, 233, 232, 141, 47, 17, 173, 48, 17, 233,
                3, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                48, 17, 201, 0, 144, 29, 208, 7, 173, 47, 17, 201, 100, 144, 20, 56,
                173, 47, 17, 233, 100, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 48, 17, 201, 0,
                144, 29, 208, 7, 173, 47, 17, 201, 10, 144, 20, 56, 173, 47, 17, 233,
                10, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 160, 1, 173, 47, 17, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208,
                3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 7, 162, 0,
                96, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "7\n",
    },
    "real_div_negative_four_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-negative-four-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 49280\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a980a2c08dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49152\n",
    },
    "real_div_two_div_negative_four_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-two-div-negative-four-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16384\n"
                "i 49280\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a900a2408dcf118ed011a900a2008dd1118ed211a980a2c02052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "48896\n",
    },
    "real_div_three_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-three-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16448\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a940a2408dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16320\n",
    },
    "real_div_one_point_five_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-one-point-five-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 16320\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a9c0a23f8dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "16192\n",
    },
    "real_div_negative_three_div_two_runtime": {
        "out_fs_name": "harness-actc-alink-direct-prg-real-div-negative-three-div-two-runtime",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b p0p1p0p2u0zr\n"
                "u rt_f_div\n"
                "i 0\n"
                "i 49216\n"
                "i 16384\n"
                "k 0\n"
                "n main\n"
            ),
        },
        "use_udos_runtime_modules": True,
        "expected_prg": bytes.fromhex(
            "0010a900a2008dcd118ece11a940a2c08dcf118ed011a900a2008dd1118ed211a900a2402052118dd3118ed411a9d585"
            "02a9118503a000a200add411c927901dd007add311c910901438add311e9108dd311add411e9278dd411e8d0dce000d0"
            "04c000f00e8a1869308dd511a2022003cfa001a200add411c903901dd007add311c9e8901438add311e9e88dd311add4"
            "11e9038dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411c900901dd007add311c96490"
            "1438add311e9648dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511a2022003cfa001a200add411"
            "c900901dd007add311c90a901438add311e90a8dd311add411e9008dd411e8d0dce000d004c000f00e8a1869308dd511"
            "a2022003cfa001add3111869308dd511a2022003cf2006cfadcd11aece118dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcf8daf3c8eb03ca9d78504a9118505a9008506a9ea8507a208f00aa000b1049106c8d0f9e605e607cad0f0a000"
            "c038f007b1049106c8d0f5adcd118da93cadce118daa3cadcf118dab3cadd0118dac3cadd1118dad3cadd2118dae3ca9"
            "008dc23ca9038df83c200deaadb13c8dcd11adb23c8dce11adb33caeb43c600000000000000000000041564f560100ea"
            "0dea38080000adf83cc901f012c902f024c903f029c904f02ec905f0303860adc23cf008adb03c49808db03c20b0ea20"
            "0aeb4c64eb20b0ea200aeb4c36ed20b0ea200aeb4c7bee20b0ea4c27f0ada93c0daa3cd0052026ed1860ada93c8dca3c"
            "adaa3c8dcb3ca9008dcc3c8dcd3c8dbf3c8dc73cadcb3c300c0eca3c2ecb3ceec73c4c7beaa98e38edc73c8dbd3ca900"
            "8db53cadca3c8db63cadcb3c8db73ca9008db83c20beec1860ada93c0daa3c0dab3c0dac3cd015a9008dbd3c8dbf3c8d"
            "b53c8db63c8db73c8db83c60adac3c29808dbf3cadac3c297f0a8dbd3cadab3c2980f003eebd3cada93c8db53cadaa3c"
            "8db63cadab3c297f09808db73ca9008db83c60adad3c0dae3c0daf3c0db03cd015a9008dbe3c8dc03c8db93c8dba3c8d"
            "bb3c8dbc3c60adb03c29808dc03cadb03c297f0a8dbe3cadaf3c2980f003eebe3cadad3c8db93cadae3c8dba3cadaf3c"
            "297f09808dbb3ca9008dbc3c60adbd3cd0034c0cedadbe3cd0034cf2ecadbe3ccdbd3c9012d00dadbf3ccdc03cf00820"
            "aff1b00320cef1adbd3c38edbe3c8dc13cc9289002a200a9009dca3c9dd03ce8e006d0f3adb53c8dcb3cadb63c8dcc3c"
            "adb73c8dcd3cadc13cc928b027adb93c8dd13cadba3c8dd23cadbb3c8dd33cacc13cf010209cf19008add03c09018dd0"
            "3c88d0f0adbf3ccdc03cd02320c4f0adcf3c0dce3cf04b2076f19008adca3c09018dca3ceebd3cd0034c26ed4c49ec20"
            "fcf0adca3c0dcb3c0dcc3c0dcd3c0dce3c0dcf3cd0034c26edadcd3c2980d0122063f1cebd3cd0034c26edadcd3c2980"
            "f0eeadca3cc9809020d007adcb3c2901f017eecb3cd012eecc3cd00deecd3cd008eece3cd003eecf3cadcf3c0dce3cf0"
            "222076f19008adca3c09018dca3ceebd3cd0034c26edadbd3cc9ffd0034c26ed4ca4ecadbd3cc9ffd0034c26edadcb3c"
            "8db53cadcc3c8db63cadcd3c8db73ca9008db83c4cbeecadbd3cf063adb53c8db13cadb63c8db23cadb73c297f8db33c"
            "adbd3c2901f008adb33c09808db33cadbd3c4a0dbf3c8db43c1860ada93c8db13cadaa3c8db23cadab3c8db33cadac3c"
            "8db43c1860adad3c8db13cadae3c8db23cadaf3c8db33cadb03c8db43c1860a9008db13c8db23c8db33c8db43c1860ad"
            "bd3cf0ebadbe3cf0e6adbf3c4dc03c8dbf3cadbd3c186dbe3c8dc83ca90069008dc93cadc83c38e97f8dc83cadc93ce9"
            "008dc93ca200a9009dca3c9dd03ce8e006d0f3adb53c8dd03cadb63c8dd13cadb73c8dd23ca9188dc73cadb93c2901f0"
            "0320c4f04ebb3c6eba3c6eb93c2089f1cec73cd0e5adcf3c2980f036eec83cd003eec93ca9188dc73ca9008dd63cadcc"
            "3c2980f049adca3c0dcb3cd00eadcc3c297fd007adcd3c2901f033a9018dd63cd02ca9178dc73ca9008dd63cadcc3c29"
            "40f01badca3c0dcb3cd00eadcc3c293fd007adcc3c2980f005a9018dd63c2076f1cec73cd0f8add63cf024eeca3cd01f"
            "eecb3cd01aeecc3cd015a9008dca3c8dcb3ca9808dcc3ceec83cd003eec93cadc93cd02dadc83cf028c9fff0248dbd3c"
            "adca3c8db53cadcb3c8db63cadcc3c8db73ca9008db83cadb73c2980f0034cbeec4c26edadbd3cf008adbe3cf0034c8b"
            "ee4c24f0adbf3c4dc03c8dbf3c20aff1b02aadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697e8dc83cadc93c69"
            "008dc93ca9188dc73c4ceaeeadbd3c38edbe3c8dc83ca900e9008dc93c18adc83c697f8dc83cadc93c69008dc93ca917"
            "8dc73ca200a9009dca3c9dd03ce8e006d0f3a200a9009dd63ce8e003d0f6adb53c8dca3cadb63c8dcb3cadb73c8dcc3c"
            "2063f1cec73cd0f8adb93c8dd03cadba3c8dd13cadbb3c8dd23ca9178dc73c2089f1cec73cd0f8a9188dc73c0ed63c2e"
            "d73c2ed83c2034f1900620fcf0eed63c209cf1cec73cd0e4add63c0dd73c0dd83cd0034c24f02034f1905badcf3ccdd5"
            "3cd02fadce3ccdd43cd027adcd3ccdd33cd01fadcc3ccdd23cd017adcb3ccdd13cd00fadca3ccdd03cd007add63c2901"
            "f024eed63cd01feed73cd01aeed83cd015a9008dd63c8dd73ca9808dd83ceec83cd003eec93cadd83c2980d0250ed63c"
            "2ed73c2ed83cadc83cd003cec93ccec83cadc93cd037adc83cf032add83c2980f0dbadc93cd026adc83cf021c9fff01d"
            "8dbd3cadd63c8db53cadd73c8db63cadd83c8db73ca9008db83c4cbeec4c26edadbd3cd008a90085f585f61860c97fb0"
            "08a90085f585f6186038e97fc918900238608dc73cadb53c8dca3cadb63c8dcb3cadb73c8dcc3ca9008dcd3ca91738ed"
            "c73c8dc73cadc73cf0124ecd3c6ecc3c6ecb3c6eca3ccec73c4c6cf0adcc3c0dcd3cf0023860adbf3cf01fadcb3cc980"
            "9007d027adca3cd022a90038edca3c85f5a900edcb3c85f61860adcb3c300cadca3c85f5adcb3c85f61860386018adca"
            "3c6dd03c8dca3cadcb3c6dd13c8dcb3cadcc3c6dd23c8dcc3cadcd3c6dd33c8dcd3cadce3c6dd43c8dce3cadcf3c6dd5"
            "3c8dcf3c6038adca3cedd03c8dca3cadcb3cedd13c8dcb3cadcc3cedd23c8dcc3cadcd3cedd33c8dcd3cadce3cedd43c"
            "8dce3cadcf3cedd53c8dcf3c60adcf3ccdd53cd026adce3ccdd43cd01eadcd3ccdd33cd016adcc3ccdd23cd00eadcb3c"
            "cdd13cd006adca3ccdd03c600eca3c2ecb3c2ecc3c2ecd3c2ece3c2ecf3c604ecf3c6ece3c6ecd3c6ecc3c6ecb3c6eca"
            "3c600ed03c2ed13c2ed23c2ed33c2ed43c2ed53c604ed53c6ed43c6ed33c6ed23c6ed13c6ed03c60adb83ccdbc3cd016"
            "adb73ccdbb3cd00eadb63ccdba3cd006adb53ccdb93c60adbf3c48adc03c8dbf3c688dc03cadbd3c48adbe3c8dbd3c68"
            "8dbe3ca200bdb53c48bdb93c9db53c689db93ce8e004d0edada93c48adad3c8da93c688dad3cadaa3c48adae3c8daa3c"
            "688dae3cadab3c48adaf3c8dab3c688daf3cadac3c48adb03c8dac3c688db03c60"
        ),
        "expected_console": "49088\n",
    },
    "return_assign_local_var_expr": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-assign-local-var-expr",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC NEXT()\r'
            'RETURN X+1\r'
            'PROC MAIN()\r'
            'X=NEXT()\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x next 0 8\n"
            "x main 8 13\n"
            "b L0p0ar\n"
            "b c0S0L0zr\n"
            "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 25, 0, 8, 0, 1, 23, 0, 19, 23, 0, 17,
                1, 0, 20, 72, 69, 0, 0, 18, 23, 0, 19, 23, 0, 73, 49, 255,
                73, 32, 255, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 54, 17, 141, 92, 17, 142, 93, 17, 173, 92, 17, 174, 93,
                17, 141, 86, 17, 142, 87, 17, 169, 90, 133, 2, 169, 17, 133, 3, 160,
                0, 162, 0, 173, 87, 17, 201, 39, 144, 29, 208, 7, 173, 86, 17, 201,
                16, 144, 20, 56, 173, 86, 17, 233, 16, 141, 86, 17, 173, 87, 17, 233,
                39, 141, 87, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 90, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                87, 17, 201, 3, 144, 29, 208, 7, 173, 86, 17, 201, 232, 144, 20, 56,
                173, 86, 17, 233, 232, 141, 86, 17, 173, 87, 17, 233, 3, 141, 87, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                90, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 87, 17, 201, 0,
                144, 29, 208, 7, 173, 86, 17, 201, 100, 144, 20, 56, 173, 86, 17, 233,
                100, 141, 86, 17, 173, 87, 17, 233, 0, 141, 87, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 90, 17, 162, 2,
                32, 3, 207, 160, 1, 162, 0, 173, 87, 17, 201, 0, 144, 29, 208, 7,
                173, 86, 17, 201, 10, 144, 20, 56, 173, 86, 17, 233, 10, 141, 86, 17,
                173, 87, 17, 233, 0, 141, 87, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 90, 17, 162, 2, 32, 3, 207, 160,
                1, 173, 86, 17, 24, 105, 48, 141, 90, 17, 162, 2, 32, 3, 207, 32,
                6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133,
                2, 133, 3, 162, 2, 76, 15, 207, 173, 92, 17, 174, 93, 17, 141, 86,
                17, 142, 87, 17, 169, 1, 162, 0, 24, 109, 86, 17, 141, 86, 17, 138,
                109, 87, 17, 170, 173, 86, 17, 96, 0, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "1\n",
    },
    "return_condition_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-condition-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF W()=7 THEN\r'
                'PrintE("OK")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'RETURN 7\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 17\n"
                "b u0p0qhe0vr\n"
                "u w\n"
                "s OK\n"
                "i 7\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 4\n"
                "b p0r\n"
                "i 7\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 26, 0, 0, 0, 1, 23, 0, 69, 19, 0, 17,
                7, 0, 22, 24, 16, 0, 97, 23, 0, 73, 16, 255, 73, 32, 255,
                17, 7, 0, 72, 79, 75, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 64, 16, 141, 69, 16, 142, 70, 16, 169, 7, 162, 0, 236,
                70, 16, 208, 5, 205, 69, 16, 240, 3, 76, 42, 16, 169, 73, 133, 2,
                169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3, 142,
                210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76,
                15, 207, 169, 7, 162, 0, 96, 0, 0, 0, 0, 79, 75, 0,
            ]
        ),
        "expected_console": "OK\n",
    },
    "return_external_add": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-external-add",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintIE(W()+1)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'RETURN 7\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 11\n"
                "b u0p0azr\n"
                "u w\n"
                "i 1\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 4\n"
                "b p0r\n"
                "i 7\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 17, 0, 0, 0, 1, 17, 0, 69, 13, 0, 17,
                1, 0, 20, 73, 49, 255, 73, 32, 255, 17, 7, 0, 72,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 67, 17, 141, 72, 17, 142, 73, 17, 169, 1, 162, 0, 24,
                109, 72, 17, 141, 72, 17, 138, 109, 73, 17, 170, 173, 72, 17, 141, 72,
                17, 142, 73, 17, 169, 76, 133, 2, 169, 17, 133, 3, 160, 0, 162, 0,
                173, 73, 17, 201, 39, 144, 29, 208, 7, 173, 72, 17, 201, 16, 144, 20,
                56, 173, 72, 17, 233, 16, 141, 72, 17, 173, 73, 17, 233, 39, 141, 73,
                17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 76, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 73, 17, 201,
                3, 144, 29, 208, 7, 173, 72, 17, 201, 232, 144, 20, 56, 173, 72, 17,
                233, 232, 141, 72, 17, 173, 73, 17, 233, 3, 141, 73, 17, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 76, 17, 162,
                2, 32, 3, 207, 160, 1, 162, 0, 173, 73, 17, 201, 0, 144, 29, 208,
                7, 173, 72, 17, 201, 100, 144, 20, 56, 173, 72, 17, 233, 100, 141, 72,
                17, 173, 73, 17, 233, 0, 141, 73, 17, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 76, 17, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 73, 17, 201, 0, 144, 29, 208, 7, 173, 72, 17,
                201, 10, 144, 20, 56, 173, 72, 17, 233, 10, 141, 72, 17, 173, 73, 17,
                233, 0, 141, 73, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 76, 17, 162, 2, 32, 3, 207, 160, 1, 173, 72,
                17, 24, 105, 48, 141, 76, 17, 162, 2, 32, 3, 207, 32, 6, 207, 141,
                209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3,
                162, 2, 76, 15, 207, 169, 7, 162, 0, 96, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "8\n",
    },
    "bool_return_local": {
        "out_fs_name": "harness-actc-alink-avmrunc-bool-return-local",
        "source": (
            'MODULE MAIN\r'
            'PROC FLAG(N)\r'
            'RETURN N<3\r'
            'PROC MAIN()\r'
            'PrintIE(FLAG(2))\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x flag 0 11\n"
            "x main 11 10\n"
            "b S0L0p0lr\n"
            "b p1c0zr\n"
            "i 3\n"
            "i 2\n"
            "v n 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 25, 0, 11, 0, 1, 23, 0, 18, 23, 0, 19,
                23, 0, 17, 3, 0, 28, 72, 17, 2, 0, 69, 0, 0, 73, 49, 255,
                73, 32, 255, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 2, 162, 0, 32, 46, 17, 141, 91, 17, 142, 92, 17,
                169, 95, 133, 2, 169, 17, 133, 3, 160, 0, 162, 0, 173, 92, 17,
                201, 39, 144, 29, 208, 7, 173, 91, 17, 201, 16, 144, 20, 56,
                173, 91, 17, 233, 16, 141, 91, 17, 173, 92, 17, 233, 39, 141,
                92, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 95, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0,
                173, 92, 17, 201, 3, 144, 29, 208, 7, 173, 91, 17, 201, 232,
                144, 20, 56, 173, 91, 17, 233, 232, 141, 91, 17, 173, 92, 17,
                233, 3, 141, 92, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0,
                240, 14, 138, 24, 105, 48, 141, 95, 17, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 92, 17, 201, 0, 144, 29, 208, 7, 173, 91,
                17, 201, 100, 144, 20, 56, 173, 91, 17, 233, 100, 141, 91, 17,
                173, 92, 17, 233, 0, 141, 92, 17, 232, 208, 220, 224, 0, 208,
                4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 95, 17, 162, 2, 32,
                3, 207, 160, 1, 162, 0, 173, 92, 17, 201, 0, 144, 29, 208, 7,
                173, 91, 17, 201, 10, 144, 20, 56, 173, 91, 17, 233, 10, 141,
                91, 17, 173, 92, 17, 233, 0, 141, 92, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 95, 17,
                162, 2, 32, 3, 207, 160, 1, 173, 91, 17, 24, 105, 48, 141, 95,
                17, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3,
                169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15,
                207, 141, 97, 17, 142, 98, 17, 173, 97, 17, 174, 98, 17, 141,
                91, 17, 142, 92, 17, 169, 3, 162, 0, 236, 92, 17, 144, 13, 208,
                7, 205, 91, 17, 144, 6, 240, 4, 169, 1, 208, 2, 169, 0, 162, 0,
                96, 0, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "1\n",
    },
    "local_args_basic": {
        "out_fs_name": "harness-actc-alink-avmrunc-local-args-basic",
        "source": (
            'MODULE MAIN\r'
            'PROC INC(N)\r'
            'RETURN N+1\r'
            'PROC MAIN()\r'
            'PrintIE(INC(2+3))\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x inc 0 11\n"
            "x main 11 14\n"
            "b S0L0p0ar\n"
            "b p1p2ac0zr\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "v n 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 29, 0, 11, 0, 1, 27, 0, 18, 27, 0, 19,
                27, 0, 17, 1, 0, 20, 72, 17, 2, 0, 17, 3, 0, 20, 69, 0, 0,
                73, 49, 255, 73, 32, 255, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 2, 162, 0, 141, 109, 17, 142, 110, 17, 169, 3,
                162, 0, 24, 109, 109, 17, 141, 109, 17, 138, 109, 110, 17, 170,
                173, 109, 17, 32, 71, 17, 141, 109, 17, 142, 110, 17, 169, 113,
                133, 2, 169, 17, 133, 3, 160, 0, 162, 0, 173, 110, 17, 201, 39,
                144, 29, 208, 7, 173, 109, 17, 201, 16, 144, 20, 56, 173, 109,
                17, 233, 16, 141, 109, 17, 173, 110, 17, 233, 39, 141, 110, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105,
                48, 141, 113, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 110,
                17, 201, 3, 144, 29, 208, 7, 173, 109, 17, 201, 232, 144, 20,
                56, 173, 109, 17, 233, 232, 141, 109, 17, 173, 110, 17, 233, 3,
                141, 110, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 113, 17, 162, 2, 32, 3, 207, 160, 1,
                162, 0, 173, 110, 17, 201, 0, 144, 29, 208, 7, 173, 109, 17,
                201, 100, 144, 20, 56, 173, 109, 17, 233, 100, 141, 109, 17,
                173, 110, 17, 233, 0, 141, 110, 17, 232, 208, 220, 224, 0, 208,
                4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 113, 17, 162, 2, 32,
                3, 207, 160, 1, 162, 0, 173, 110, 17, 201, 0, 144, 29, 208, 7,
                173, 109, 17, 201, 10, 144, 20, 56, 173, 109, 17, 233, 10, 141,
                109, 17, 173, 110, 17, 233, 0, 141, 110, 17, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 113,
                17, 162, 2, 32, 3, 207, 160, 1, 173, 109, 17, 24, 105, 48, 141,
                113, 17, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210,
                3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76,
                15, 207, 141, 115, 17, 142, 116, 17, 173, 115, 17, 174, 116, 17,
                141, 109, 17, 142, 110, 17, 169, 1, 162, 0, 24, 109, 109, 17,
                141, 109, 17, 138, 109, 110, 17, 170, 173, 109, 17, 96, 0, 0,
                0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "6\n",
    },
    "local_args_multi": {
        "out_fs_name": "harness-actc-alink-direct-prg-local-args-multi",
        "source": (
            'MODULE MAIN\r'
            'PROC ADD(X,Y)\r'
            'RETURN X+Y\r'
            'PROC MAIN()\r'
            'PrintIE(ADD(2,3))\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x add 0 14\n"
            "x main 14 13\n"
            "b S1S0L0L1ar\n"
            "b p0p1c0zr\n"
            "i 2\n"
            "i 3\n"
            "v x 0\n"
            "v y 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 33, 0, 14, 0, 1, 29, 0, 18, 31, 0, 18,
                29, 0, 19, 29, 0, 19, 31, 0, 20, 72, 17, 2, 0, 17, 3, 0,
                69, 0, 0, 73, 49, 255, 73, 32, 255, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 2, 162, 0, 141, 108, 17, 142, 109, 17, 169, 3, 162, 0,
                32, 56, 17, 141, 108, 17, 142, 109, 17, 169, 112, 133, 2, 169, 17, 133,
                3, 160, 0, 162, 0, 173, 109, 17, 201, 39, 144, 29, 208, 7, 173, 108,
                17, 201, 16, 144, 20, 56, 173, 108, 17, 233, 16, 141, 108, 17, 173, 109,
                17, 233, 39, 141, 109, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240,
                14, 138, 24, 105, 48, 141, 112, 17, 162, 2, 32, 3, 207, 160, 1, 162,
                0, 173, 109, 17, 201, 3, 144, 29, 208, 7, 173, 108, 17, 201, 232, 144,
                20, 56, 173, 108, 17, 233, 232, 141, 108, 17, 173, 109, 17, 233, 3, 141,
                109, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105,
                48, 141, 112, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 109, 17,
                201, 0, 144, 29, 208, 7, 173, 108, 17, 201, 100, 144, 20, 56, 173, 108,
                17, 233, 100, 141, 108, 17, 173, 109, 17, 233, 0, 141, 109, 17, 232, 208,
                220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 112, 17,
                162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 109, 17, 201, 0, 144, 29,
                208, 7, 173, 108, 17, 201, 10, 144, 20, 56, 173, 108, 17, 233, 10, 141,
                108, 17, 173, 109, 17, 233, 0, 141, 109, 17, 232, 208, 220, 224, 0, 208,
                4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 112, 17, 162, 2, 32, 3,
                207, 160, 1, 173, 108, 17, 24, 105, 48, 141, 112, 17, 162, 2, 32, 3,
                207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169,
                0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 141, 116, 17, 142, 117, 17,
                173, 108, 17, 174, 109, 17, 141, 114, 17, 142, 115, 17, 173, 114, 17, 174,
                115, 17, 141, 108, 17, 142, 109, 17, 173, 116, 17, 174, 117, 17, 24, 109,
                108, 17, 141, 108, 17, 138, 109, 109, 17, 170, 173, 108, 17, 96, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "5\n",
    },
    "external_args_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-external-args-basic",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintIE(W(5))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 10\n"
                "b p0u0zr\n"
                "u w\n"
                "i 5\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 25, 0, 0, 0, 1, 23, 0, 17, 5, 0, 69,
                12, 0, 73, 49, 255, 73, 32, 255, 18, 23, 0, 19, 23, 0,
                17, 2, 0, 20, 72, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 5, 162, 0, 32, 46, 17, 141, 84, 17, 142, 85, 17, 169,
                88, 133, 2, 169, 17, 133, 3, 160, 0, 162, 0, 173, 85, 17, 201, 39,
                144, 29, 208, 7, 173, 84, 17, 201, 16, 144, 20, 56, 173, 84, 17, 233,
                16, 141, 84, 17, 173, 85, 17, 233, 39, 141, 85, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 88, 17, 162, 2,
                32, 3, 207, 160, 1, 162, 0, 173, 85, 17, 201, 3, 144, 29, 208, 7,
                173, 84, 17, 201, 232, 144, 20, 56, 173, 84, 17, 233, 232, 141, 84, 17,
                173, 85, 17, 233, 3, 141, 85, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 88, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 85, 17, 201, 0, 144, 29, 208, 7, 173, 84, 17, 201,
                100, 144, 20, 56, 173, 84, 17, 233, 100, 141, 84, 17, 173, 85, 17, 233,
                0, 141, 85, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 88, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                85, 17, 201, 0, 144, 29, 208, 7, 173, 84, 17, 201, 10, 144, 20, 56,
                173, 84, 17, 233, 10, 141, 84, 17, 173, 85, 17, 233, 0, 141, 85, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                88, 17, 162, 2, 32, 3, 207, 160, 1, 173, 84, 17, 24, 105, 48, 141,
                88, 17, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3,
                169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207,
                141, 96, 1, 142, 97, 1, 173, 96, 1, 174, 97, 1, 141, 86, 17, 142,
                87, 17, 169, 2, 162, 0, 24, 109, 86, 17, 141, 86, 17, 138, 109, 87,
                17, 170, 173, 86, 17, 96, 0, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "7\n",
    },
    "external_args_multi": {
        "out_fs_name": "harness-actc-alink-direct-prg-external-args-multi",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintIE(W(2,3))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(X,Y)\r'
                'RETURN X+Y\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 13\n"
                "b p0p1u0zr\n"
                "u w\n"
                "i 2\n"
                "i 3\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 14\n"
                "b S1S0L0L1ar\n"
                "v x 0\n"
                "v y 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a902a2008d7e118e7f11a903a200488a48ad7e118d8011ad7f118d811168aa68204a118d7e118e7f11a9848502a9118503a000a200ad7f11c927901dd007ad7e11c910901438ad7e11e9108d7e11ad7f11e9278d7f11e8d0dce000d004c000f00e8a1869308d8411a2022003cfa001a200ad7f11c903901dd007ad7e11c9e8901438ad7e11e9e88d7e11ad7f11e9038d7f11e8d0dce000d004c000f00e8a1869308d8411a2022003cfa001a200ad7f11c900901dd007ad7e11c964901438ad7e11e9648d7e11ad7f11e9008d7f11e8d0dce000d004c000f00e8a1869308d8411a2022003cfa001a200ad7f11c900901dd007ad7e11c90a901438ad7e11e90a8d7e11ad7f11e9008d7f11e8d0dce000d004c000f00e8a1869308d8411a2022003cfa001ad7e111869308d8411a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8d16038e1703ad8011ae81118d14038e1503ad1403ae15038d80118e8111ad1603ae1703186d80118d80118a6d8111aaad801160000000000000000000000000"
        ),
        "expected_console": "5\n",
    },
    "nested_call_arg": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-call-arg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC INC(N)\r'
                'RETURN N+1\r'
                'PROC MAIN()\r'
                'PrintIE(W(INC(2+3)))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x inc 0 11\n"
                "x main 11 17\n"
                "b S0L0p0ar\n"
                "b p1p2ac0u0zr\n"
                "u w\n"
                "i 1\n"
                "i 2\n"
                "i 3\n"
                "v n 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 45, 0, 11, 0, 1, 41, 0, 18, 41, 0, 19,
                41, 0, 17, 1, 0, 20, 72, 17, 2, 0, 17, 3, 0, 20, 69, 0, 0,
                69, 30, 0, 73, 49, 255, 73, 32, 255, 18, 43, 0, 19, 43, 0,
                17, 2, 0, 20, 72, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 2, 162, 0, 141, 150, 17, 142, 151, 17, 169, 3, 162, 0,
                24, 109, 150, 17, 141, 150, 17, 138, 109, 151, 17, 170, 173, 150, 17, 32,
                74, 17, 32, 112, 17, 141, 150, 17, 142, 151, 17, 169, 154, 133, 2, 169,
                17, 133, 3, 160, 0, 162, 0, 173, 151, 17, 201, 39, 144, 29, 208, 7,
                173, 150, 17, 201, 16, 144, 20, 56, 173, 150, 17, 233, 16, 141, 150, 17,
                173, 151, 17, 233, 39, 141, 151, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 154, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 151, 17, 201, 3, 144, 29, 208, 7, 173, 150, 17, 201,
                232, 144, 20, 56, 173, 150, 17, 233, 232, 141, 150, 17, 173, 151, 17, 233,
                3, 141, 151, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 154, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                151, 17, 201, 0, 144, 29, 208, 7, 173, 150, 17, 201, 100, 144, 20, 56,
                173, 150, 17, 233, 100, 141, 150, 17, 173, 151, 17, 233, 0, 141, 151, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                154, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 151, 17, 201, 0,
                144, 29, 208, 7, 173, 150, 17, 201, 10, 144, 20, 56, 173, 150, 17, 233,
                10, 141, 150, 17, 173, 151, 17, 233, 0, 141, 151, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 154, 17, 162, 2,
                32, 3, 207, 160, 1, 173, 150, 17, 24, 105, 48, 141, 154, 17, 162, 2,
                32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208,
                3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 141, 156, 17, 142,
                157, 17, 173, 156, 17, 174, 157, 17, 141, 150, 17, 142, 151, 17, 169, 1,
                162, 0, 24, 109, 150, 17, 141, 150, 17, 138, 109, 151, 17, 170, 173, 150,
                17, 96, 141, 164, 1, 142, 165, 1, 173, 164, 1, 174, 165, 1, 141, 152,
                17, 142, 153, 17, 169, 2, 162, 0, 24, 109, 152, 17, 141, 152, 17, 138,
                109, 153, 17, 170, 173, 152, 17, 96, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0,
            ]
        ),
        "expected_console": "8\n",
    },
    "if_local_args": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-local-args",
        "source": (
            'MODULE MAIN\r'
            'PROC INC(N)\r'
            'RETURN N+1\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'PrintIE(INC(2+3))\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x inc 0 11\n"
            "x main 11 33\n"
            "b S0L0p0ar\n"
            "b p1p2qhp3p4ac0zwe0vr\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "v n 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 52, 0, 11, 0, 1, 46, 0, 18, 46, 0, 19,
                46, 0, 17, 1, 0, 20, 72, 17, 1, 0, 17, 1, 0, 22, 24, 37,
                0, 17, 2, 0, 17, 3, 0, 20, 69, 0, 0, 73, 49, 255, 25, 43,
                0, 97, 48, 0, 73, 16, 255, 73, 32, 255, 0, 0, 66, 65, 68,
                0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 155, 17, 142, 156, 17, 169, 1, 162, 0,
                236, 156, 17, 208, 5, 205, 155, 17, 240, 3, 76, 79, 17, 169, 2, 162,
                0, 141, 155, 17, 142, 156, 17, 169, 3, 162, 0, 24, 109, 155, 17, 141,
                155, 17, 138, 109, 156, 17, 170, 173, 155, 17, 32, 117, 17, 141, 155, 17,
                142, 156, 17, 169, 159, 133, 2, 169, 17, 133, 3, 160, 0, 162, 0, 173,
                156, 17, 201, 39, 144, 29, 208, 7, 173, 155, 17, 201, 16, 144, 20, 56,
                173, 155, 17, 233, 16, 141, 155, 17, 173, 156, 17, 233, 39, 141, 156, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                159, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 156, 17, 201, 3,
                144, 29, 208, 7, 173, 155, 17, 201, 232, 144, 20, 56, 173, 155, 17, 233,
                232, 141, 155, 17, 173, 156, 17, 233, 3, 141, 156, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 159, 17, 162, 2,
                32, 3, 207, 160, 1, 162, 0, 173, 156, 17, 201, 0, 144, 29, 208, 7,
                173, 155, 17, 201, 100, 144, 20, 56, 173, 155, 17, 233, 100, 141, 155, 17,
                173, 156, 17, 233, 0, 141, 156, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 159, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 156, 17, 201, 0, 144, 29, 208, 7, 173, 155, 17, 201,
                10, 144, 20, 56, 173, 155, 17, 233, 10, 141, 155, 17, 173, 156, 17, 233,
                0, 141, 156, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 159, 17, 162, 2, 32, 3, 207, 160, 1, 173, 155, 17,
                24, 105, 48, 141, 159, 17, 162, 2, 32, 3, 207, 32, 6, 207, 76, 95,
                17, 169, 163, 133, 2, 169, 17, 133, 3, 162, 2, 32, 3, 207, 32, 6,
                207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2,
                133, 3, 162, 2, 76, 15, 207, 141, 161, 17, 142, 162, 17, 173, 161, 17,
                174, 162, 17, 141, 155, 17, 142, 156, 17, 169, 1, 162, 0, 24, 109, 155,
                17, 141, 155, 17, 138, 109, 156, 17, 170, 173, 155, 17, 96, 0, 0, 0,
                0, 0, 0, 0, 0, 66, 65, 68, 0,
            ]
        ),
        "expected_console": "6\n",
    },
    "while_external_args": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-external-args",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[0]\r'
                'PROC MAIN()\r'
                'WHILE X < 2 DO\r'
                'PrintIE(W(X+5))\r'
                'X=X+1\r'
                'OD\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 37\n"
                "b dL0p0lfL0p1au0zL0p2aS0xr\n"
                "u w\n"
                "i 2\n"
                "i 5\n"
                "i 1\n"
                "v x 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 54, 0, 0, 0, 1, 50, 0, 19, 50, 0, 17,
                2, 0, 28, 24, 36, 0, 19, 50, 0, 17, 5, 0, 20, 69, 39, 0,
                73, 49, 255, 19, 50, 0, 17, 1, 0, 20, 18, 50, 0, 25, 0,
                0, 73, 32, 255, 18, 52, 0, 19, 52, 0, 17, 2, 0, 20, 72, 0,
                0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 173, 202, 17, 174, 203, 17, 141, 196, 17, 142, 197, 17, 169, 2,
                162, 0, 236, 197, 17, 144, 13, 208, 7, 205, 196, 17, 144, 6, 240, 4,
                169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 136, 17, 173,
                202, 17, 174, 203, 17, 141, 196, 17, 142, 197, 17, 169, 5, 162, 0, 24,
                109, 196, 17, 141, 196, 17, 138, 109, 197, 17, 170, 173, 196, 17, 32, 158,
                17, 141, 196, 17, 142, 197, 17, 169, 200, 133, 2, 169, 17, 133, 3, 160,
                0, 162, 0, 173, 197, 17, 201, 39, 144, 29, 208, 7, 173, 196, 17, 201,
                16, 144, 20, 56, 173, 196, 17, 233, 16, 141, 196, 17, 173, 197, 17, 233,
                39, 141, 197, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 200, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                197, 17, 201, 3, 144, 29, 208, 7, 173, 196, 17, 201, 232, 144, 20, 56,
                173, 196, 17, 233, 232, 141, 196, 17, 173, 197, 17, 233, 3, 141, 197, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                200, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 197, 17, 201, 0,
                144, 29, 208, 7, 173, 196, 17, 201, 100, 144, 20, 56, 173, 196, 17, 233,
                100, 141, 196, 17, 173, 197, 17, 233, 0, 141, 197, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 200, 17, 162, 2,
                32, 3, 207, 160, 1, 162, 0, 173, 197, 17, 201, 0, 144, 29, 208, 7,
                173, 196, 17, 201, 10, 144, 20, 56, 173, 196, 17, 233, 10, 141, 196, 17,
                173, 197, 17, 233, 0, 141, 197, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 200, 17, 162, 2, 32, 3, 207, 160,
                1, 173, 196, 17, 24, 105, 48, 141, 200, 17, 162, 2, 32, 3, 207, 32,
                6, 207, 173, 202, 17, 174, 203, 17, 141, 196, 17, 142, 197, 17, 169, 1,
                162, 0, 24, 109, 196, 17, 141, 196, 17, 138, 109, 197, 17, 170, 173, 196,
                17, 141, 202, 17, 142, 203, 17, 76, 0, 16, 141, 209, 3, 142, 210, 3,
                169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207,
                141, 210, 1, 142, 211, 1, 173, 210, 1, 174, 211, 1, 141, 198, 17, 142,
                199, 17, 169, 2, 162, 0, 24, 109, 198, 17, 141, 198, 17, 138, 109, 199,
                17, 170, 173, 198, 17, 96, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "7\n8\n",
    },
    "bool_compound": {
        "out_fs_name": "harness-actc-alink-avmrunc-bool-compound",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'IF (X<Y AND W()=7) OR Z()=1 THEN\r'
                'PrintE("OK")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'RETURN 7\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'RETURN 0\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 66\n"
                "b L0L1lp0nu0p1qp2nap3gp4nu1p5qp6nap7ghe0we1vr\n"
                "u w\n"
                "u z\n"
                "s OK\n"
                "s BAD\n"
                "i 0\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 4\n"
                "b p0r\n"
                "i 7\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 4\n"
                "b p0r\n"
                "i 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 87, 0, 0, 0, 1, 76, 0, 19, 76, 0, 19,
                78, 0, 28, 17, 0, 0, 23, 69, 68, 0, 17, 7, 0, 22, 17, 0,
                0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 69, 72, 0, 17, 1,
                0, 22, 17, 0, 0, 23, 20, 17, 0, 0, 29, 24, 59, 0, 97, 80,
                0, 73, 16, 255, 25, 65, 0, 97, 83, 0, 73, 16, 255, 73, 32,
                255, 17, 7, 0, 72, 17, 0, 0, 72, 1, 0, 2, 0, 79, 75, 0,
                66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ad8e11ae8f118d8a118e8b11ad9011ae9111ec8b11900dd007cd8a119006f004a901d002a900"
            "a2008d8a118e8b11a900a200ec8b11d005cd8a11f004a901d002a900a2008d8a118e8b112080118d"
            "8c118e8d11a907a200ec8d11d005cd8c11f004a900f002a901a2008d8c118e8d11a900a200ec8d11"
            "d005cd8c11f004a901d002a900a200186d8a118d8a118a6d8b11aaad8a118d8a118e8b11a901a200"
            "ec8b119007d00dcd8a119002f004a901d002a900a2008d8a118e8b11a900a200ec8b11d005cd8a11"
            "f004a901d002a900a2008d8a118e8b112085118d8c118e8d11a901a200ec8d11d005cd8c11f004a9"
            "00f002a901a2008d8c118e8d11a900a200ec8d11d005cd8c11f004a901d002a900a200186d8a118d"
            "8a118a6d8b11aaad8a118d8a118e8b11a900a200ec8b119007d00dcd8a119002f004a901d002a900"
            "a200c900d0034c5a11a9928502a9118503a2022003cf2006cf4c6a11a9958502a9118503a2022003"
            "cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa907a20060a900a2006000000000"
            "010002004f4b0042414400"
        ),
        "expected_console": "OK\n",
    },
    "bool_compound_args": {
        "out_fs_name": "harness-actc-alink-direct-prg-bool-compound-args",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'IF (X<Y AND W(5)=7) OR Z(1)=1 THEN\r'
                'PrintE("OK")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 72\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9ghe0we1vr\n"
                "u w\n"
                "u z\n"
                "s OK\n"
                "s BAD\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 111, 0, 0, 0, 1, 96, 0, 19, 96, 0, 19,
                98, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 74, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 85, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 24, 65, 0, 97, 104, 0, 73, 16, 255, 25, 71, 0, 97,
                107, 0, 73, 16, 255, 73, 32, 255, 18, 100, 0, 19, 100, 0,
                17, 2, 0, 20, 72, 18, 102, 0, 19, 102, 0, 17, 1, 0, 21,
                72, 1, 0, 2, 0, 0, 0, 0, 0, 79, 75, 0, 66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010addf11aee0118ddb118edc11ade111aee211ecdc11900dd007cddb119006f004a901d002a900"
            "a2008ddb118edc11a900a200ecdc11d005cddb11f004a901d002a900a2008ddb118edc11a905a200"
            "2088118ddd118ede11a907a200ecde11d005cddd11f004a900f002a901a2008ddd118ede11a900a2"
            "00ecde11d005cddd11f004a901d002a900a200186ddb118ddb118a6ddc11aaaddb118ddb118edc11"
            "a901a200ecdc119007d00dcddb119002f004a901d002a900a2008ddb118edc11a900a200ecdc11d0"
            "05cddb11f004a901d002a900a2008ddb118edc11a901a20020ae118ddd118ede11a901a200ecde11"
            "d005cddd11f004a900f002a901a2008ddd118ede11a900a200ecde11d005cddd11f004a901d002a9"
            "00a200186ddb118ddb118a6ddc11aaaddb118ddb118edc11a900a200ecdc119007d00dcddb119002"
            "f004a901d002a900a200c900d0034c6211a9e78502a9118503a2022003cf2006cf4c7211a9ea8502"
            "a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8de7018ee801"
            "ade701aee8018ddd118ede11a902a200186ddd118ddd118a6dde11aaaddd11608de9018eea01ade9"
            "01aeea018ddd118ede11a901a20085028603addd1138e5028ddd11adde11e503aaaddd1160000000"
            "0001000200000000004f4b0042414400"
        ),
        "expected_console": "OK\n",
    },
    "bool_local_external_args": {
        "out_fs_name": "harness-actc-alink-direct-prg-bool-local-external-args",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC INC(N)\r'
                'RETURN N+1\r'
                'PROC MAIN()\r'
                'IF (INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1) THEN\r'
                'PrintE("OK")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x inc 0 11\n"
                "x main 11 87\n"
                "b S2L2p0ar\n"
                "b L0c0p1qp2nL1p3au0p4qp5nap6gp7np8u1p9qpAnpBqpCnapDghe0we1vr\n"
                "u w\n"
                "u z\n"
                "s OK\n"
                "s BAD\n"
                "i 1\n"
                "i 2\n"
                "i 0\n"
                "i 5\n"
                "i 9\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "v n 0\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 139, 0, 11, 0, 1, 122, 0, 18, 126, 0,
                19, 126, 0, 17, 1, 0, 20, 72, 19, 122, 0, 69, 0, 0, 17, 2,
                0, 22, 17, 0, 0, 23, 19, 124, 0, 17, 5, 0, 20, 69, 100, 0,
                17, 9, 0, 22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0,
                23, 17, 1, 0, 69, 111, 0, 17, 1, 0, 22, 17, 0, 0, 23, 17,
                0, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0, 29, 24, 91, 0, 97,
                132, 0, 73, 16, 255, 25, 97, 0, 97, 135, 0, 73, 16, 255,
                73, 32, 255, 18, 128, 0, 19, 128, 0, 17, 2, 0, 20, 72, 18,
                130, 0, 19, 130, 0, 17, 1, 0, 21, 72, 1, 0, 2, 0, 0, 0,
                0, 0, 0, 0, 79, 75, 0, 66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ad5512ae561220d8118d51128e5212a902a200ec5212d005cd5112f004a900f002a901a2008d"
            "51128e5212a900a200ec5212d005cd5112f004a901d002a900a2008d51128e5212ad5712ae58128d"
            "53128e5412a905a200186d53128d53128a6d5412aaad531220fe118d53128e5412a909a200ec5412"
            "d005cd5312f004a900f002a901a2008d53128e5412a900a200ec5412d005cd5312f004a901d002a9"
            "00a200186d51128d51128a6d5212aaad51128d51128e5212a901a200ec52129007d00dcd51129002"
            "f004a901d002a900a2008d51128e5212a900a200ec5212d005cd5112f004a901d002a900a2008d51"
            "128e5212a901a2002024128d53128e5412a901a200ec5412d005cd5312f004a900f002a901a2008d"
            "53128e5412a900a200ec5412d005cd5312f004a901d002a900a2008d53128e5412a900a200ec5412"
            "d005cd5312f004a900f002a901a2008d53128e5412a900a200ec5412d005cd5312f004a901d002a9"
            "00a200186d51128d51128a6d5212aaad51128d51128e5212a900a200ec52129007d00dcd51129002"
            "f004a901d002a900a200c900d0034cb211a95f8502a9128503a2022003cf2006cf4cc211a9628502"
            "a9128503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8d59128e5a12"
            "ad5912ae5a128d51128e5212a901a200186d51128d51128a6d5212aaad5112608d5f028e6002ad5f"
            "02ae60028d53128e5412a902a200186d53128d53128a6d5412aaad5312608d61028e6202ad6102ae"
            "62028d53128e5412a901a20085028603ad531238e5028d5312ad5412e503aaad5312600000000001"
            "0002000000000000004f4b0042414400"
        ),
        "expected_console": "OK\n",
    },
    "bool_assign_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-bool-assign-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[0]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'X=(X<Y AND W(5)=7) OR Z(1)=1\r'
                'PrintIE(X)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 63\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9gS0L0zr\n"
                "u w\n"
                "u z\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 0\n"
                "v y 2\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 95, 0, 0, 0, 1, 87, 0, 19, 87, 0, 19,
                89, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 65, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 76, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 18, 87, 0, 19, 87, 0, 73, 49, 255, 73, 32, 255, 18,
                91, 0, 19, 91, 0, 17, 2, 0, 20, 72, 18, 93, 0, 19, 93, 0,
                17, 1, 0, 21, 72, 0, 0, 2, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010add412aed5128dce128ecf12add612aed712eccf12900dd007cdce129006f004a901d002a900"
            "a2008dce128ecf12a900a200eccf12d005cdce12f004a901d002a900a2008dce128ecf12a905a200"
            "207b128dd0128ed112a907a200ecd112d005cdd012f004a900f002a901a2008dd0128ed112a900a2"
            "00ecd112d005cdd012f004a901d002a900a200186dce128dce128a6dcf12aaadce128dce128ecf12"
            "a901a200eccf129007d00dcdce129002f004a901d002a900a2008dce128ecf12a900a200eccf12d0"
            "05cdce12f004a901d002a900a2008dce128ecf12a901a20020a1128dd0128ed112a901a200ecd112"
            "d005cdd012f004a900f002a901a2008dd0128ed112a900a200ecd112d005cdd012f004a901d002a9"
            "00a200186dce128dce128a6dcf12aaadce128dce128ecf12a900a200eccf129007d00dcdce129002"
            "f004a901d002a900a2008dd4128ed512add412aed5128dce128ecf12a9d28502a9128503a000a200"
            "adcf12c927901dd007adce12c910901438adce12e9108dce12adcf12e9278dcf12e8d0dce000d004"
            "c000f00e8a1869308dd212a2022003cfa001a200adcf12c903901dd007adce12c9e8901438adce12"
            "e9e88dce12adcf12e9038dcf12e8d0dce000d004c000f00e8a1869308dd212a2022003cfa001a200"
            "adcf12c900901dd007adce12c964901438adce12e9648dce12adcf12e9008dcf12e8d0dce000d004"
            "c000f00e8a1869308dd212a2022003cfa001a200adcf12c900901dd007adce12c90a901438adce12"
            "e90a8dce12adcf12e9008dcf12e8d0dce000d004c000f00e8a1869308dd212a2022003cfa001adce"
            "121869308dd212a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8dde02"
            "8edf02adde02aedf028dd0128ed112a902a200186dd0128dd0128a6dd112aaadd012608de0028ee1"
            "02ade002aee1028dd0128ed112a901a20085028603add01238e5028dd012add112e503aaadd01260"
            "0000000000000000020000000000"
        ),
        "expected_console": "1\n",
    },
    "bool_arg_local_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-bool-arg-local-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC INC(N)\r'
                'RETURN N+1\r'
                'PROC MAIN()\r'
                'PrintIE(INC((X<Y AND W(5)=7) OR Z(1)=1))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x inc 0 11\n"
                "x main 11 60\n"
                "b S2L2p0ar\n"
                "b L0L1lp1np2u0p3qp4nap5gp6np7u1p8qp9napAgc0zr\n"
                "u w\n"
                "u z\n"
                "i 1\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "v n 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 105, 0, 11, 0, 1, 95, 0, 18, 99, 0, 19,
                99, 0, 17, 1, 0, 20, 72, 19, 95, 0, 19, 97, 0, 28, 17, 0,
                0, 23, 17, 5, 0, 69, 73, 0, 17, 7, 0, 22, 17, 0, 0, 23,
                20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1, 0, 69, 84, 0, 17,
                1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0, 29, 69, 0, 0, 73,
                49, 255, 73, 32, 255, 18, 101, 0, 19, 101, 0, 17, 2, 0,
                20, 72, 18, 103, 0, 19, 103, 0, 17, 1, 0, 21, 72, 1, 0,
                2, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010adf112aef2128deb128eec12adf312aef412ecec12900dd007cdeb129006f004a901d002a900"
            "a2008deb128eec12a900a200ecec12d005cdeb12f004a901d002a900a2008deb128eec12a905a200"
            "2098128ded128eee12a907a200ecee12d005cded12f004a900f002a901a2008ded128eee12a900a2"
            "00ecee12d005cded12f004a901d002a900a200186deb128deb128a6dec12aaadeb128deb128eec12"
            "a901a200ecec129007d00dcdeb129002f004a901d002a900a2008deb128eec12a900a200ecec12d0"
            "05cdeb12f004a901d002a900a2008deb128eec12a901a20020be128ded128eee12a901a200ecee12"
            "d005cded12f004a900f002a901a2008ded128eee12a900a200ecee12d005cded12f004a901d002a9"
            "00a200186deb128deb128a6dec12aaadeb128deb128eec12a900a200ecec129007d00dcdeb129002"
            "f004a901d002a900a2002072128deb128eec12a9ef8502a9128503a000a200adec12c927901dd007"
            "adeb12c910901438adeb12e9108deb12adec12e9278dec12e8d0dce000d004c000f00e8a1869308d"
            "ef12a2022003cfa001a200adec12c903901dd007adeb12c9e8901438adeb12e9e88deb12adec12e9"
            "038dec12e8d0dce000d004c000f00e8a1869308def12a2022003cfa001a200adec12c900901dd007"
            "adeb12c964901438adeb12e9648deb12adec12e9008dec12e8d0dce000d004c000f00e8a1869308d"
            "ef12a2022003cfa001a200adec12c900901dd007adeb12c90a901438adeb12e90a8deb12adec12e9"
            "008dec12e8d0dce000d004c000f00e8a1869308def12a2022003cfa001adeb121869308def12a202"
            "2003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8df5128ef612adf512aef612"
            "8deb128eec12a901a200186deb128deb128a6dec12aaadeb12608dfd028efe02adfd02aefe028ded"
            "128eee12a902a200186ded128ded128a6dee12aaaded12608dff028e0003adff02ae00038ded128e"
            "ee12a901a20085028603aded1238e5028ded12adee12e503aaaded12600000000000000100020000"
            "0000000000"
        ),
        "expected_console": "2\n",
    },
    "printie_bool_compound": {
        "out_fs_name": "harness-actc-alink-direct-prg-printie-bool-compound",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'PrintIE((X<Y AND W(5)=7) OR Z(1)=1)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 57\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9gzr\n"
                "u w\n"
                "u z\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 89, 0, 0, 0, 1, 81, 0, 19, 81, 0, 19,
                83, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 59, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 70, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 73, 49, 255, 73, 32, 255, 18, 85, 0, 19, 85, 0, 17,
                2, 0, 20, 72, 18, 87, 0, 19, 87, 0, 17, 1, 0, 21, 72, 1,
                0, 2, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010adc812aec9128dc2128ec312adca12aecb12ecc312900dd007cdc2129006f004a901d002a900"
            "a2008dc2128ec312a900a200ecc312d005cdc212f004a901d002a900a2008dc2128ec312a905a200"
            "206f128dc4128ec512a907a200ecc512d005cdc412f004a900f002a901a2008dc4128ec512a900a2"
            "00ecc512d005cdc412f004a901d002a900a200186dc2128dc2128a6dc312aaadc2128dc2128ec312"
            "a901a200ecc3129007d00dcdc2129002f004a901d002a900a2008dc2128ec312a900a200ecc312d0"
            "05cdc212f004a901d002a900a2008dc2128ec312a901a2002095128dc4128ec512a901a200ecc512"
            "d005cdc412f004a900f002a901a2008dc4128ec512a900a200ecc512d005cdc412f004a901d002a9"
            "00a200186dc2128dc2128a6dc312aaadc2128dc2128ec312a900a200ecc3129007d00dcdc2129002"
            "f004a901d002a900a2008dc2128ec312a9c68502a9128503a000a200adc312c927901dd007adc212"
            "c910901438adc212e9108dc212adc312e9278dc312e8d0dce000d004c000f00e8a1869308dc612a2"
            "022003cfa001a200adc312c903901dd007adc212c9e8901438adc212e9e88dc212adc312e9038dc3"
            "12e8d0dce000d004c000f00e8a1869308dc612a2022003cfa001a200adc312c900901dd007adc212"
            "c964901438adc212e9648dc212adc312e9008dc312e8d0dce000d004c000f00e8a1869308dc612a2"
            "022003cfa001a200adc312c900901dd007adc212c90a901438adc212e90a8dc212adc312e9008dc3"
            "12e8d0dce000d004c000f00e8a1869308dc612a2022003cfa001adc2121869308dc612a2022003cf"
            "2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8dd2028ed302add202aed3028dc412"
            "8ec512a902a200186dc4128dc4128a6dc512aaadc412608dd4028ed502add402aed5028dc4128ec5"
            "12a901a20085028603adc41238e5028dc412adc512e503aaadc41260000000000000010002000000"
            "0000"
        ),
        "expected_console": "1\n",
    },
    "printie_bool_local_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-printie-bool-local-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC INC(N)\r'
                'RETURN N+1\r'
                'PROC MAIN()\r'
                'PrintIE((INC(X)=2 AND W(Y+5)=9) OR NOT(Z(1)=1))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x inc 0 11\n"
                "x main 11 72\n"
                "b S2L2p0ar\n"
                "b L0c0p1qp2nL1p3au0p4qp5nap6gp7np8u1p9qpAnpBqpCnapDgzr\n"
                "u w\n"
                "u z\n"
                "i 1\n"
                "i 2\n"
                "i 0\n"
                "i 5\n"
                "i 9\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "v n 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 117, 0, 11, 0, 1, 107, 0, 18, 111, 0,
                19, 111, 0, 17, 1, 0, 20, 72, 19, 107, 0, 69, 0, 0, 17, 2,
                0, 22, 17, 0, 0, 23, 19, 109, 0, 17, 5, 0, 20, 69, 85, 0,
                17, 9, 0, 22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0,
                23, 17, 1, 0, 69, 96, 0, 17, 1, 0, 22, 17, 0, 0, 23, 17,
                0, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0, 29, 73, 49, 255, 73,
                32, 255, 18, 113, 0, 19, 113, 0, 17, 2, 0, 20, 72, 18, 115,
                0, 19, 115, 0, 17, 1, 0, 21, 72, 1, 0, 2, 0, 0, 0, 0, 0,
                0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ad3e13ae3f1320bf128d38138e3913a902a200ec3913d005cd3813f004a900f002a901a2008d"
            "38138e3913a900a200ec3913d005cd3813f004a901d002a900a2008d38138e3913ad4013ae41138d"
            "3a138e3b13a905a200186d3a138d3a138a6d3b13aaad3a1320e5128d3a138e3b13a909a200ec3b13"
            "d005cd3a13f004a900f002a901a2008d3a138e3b13a900a200ec3b13d005cd3a13f004a901d002a9"
            "00a200186d38138d38138a6d3913aaad38138d38138e3913a901a200ec39139007d00dcd38139002"
            "f004a901d002a900a2008d38138e3913a900a200ec3913d005cd3813f004a901d002a900a2008d38"
            "138e3913a901a200200b138d3a138e3b13a901a200ec3b13d005cd3a13f004a900f002a901a2008d"
            "3a138e3b13a900a200ec3b13d005cd3a13f004a901d002a900a2008d3a138e3b13a900a200ec3b13"
            "d005cd3a13f004a900f002a901a2008d3a138e3b13a900a200ec3b13d005cd3a13f004a901d002a9"
            "00a200186d38138d38138a6d3913aaad38138d38138e3913a900a200ec39139007d00dcd38139002"
            "f004a901d002a900a2008d38138e3913a93c8502a9138503a000a200ad3913c927901dd007ad3813"
            "c910901438ad3813e9108d3813ad3913e9278d3913e8d0dce000d004c000f00e8a1869308d3c13a2"
            "022003cfa001a200ad3913c903901dd007ad3813c9e8901438ad3813e9e88d3813ad3913e9038d39"
            "13e8d0dce000d004c000f00e8a1869308d3c13a2022003cfa001a200ad3913c900901dd007ad3813"
            "c964901438ad3813e9648d3813ad3913e9008d3913e8d0dce000d004c000f00e8a1869308d3c13a2"
            "022003cfa001a200ad3913c900901dd007ad3813c90a901438ad3813e90a8d3813ad3913e9008d39"
            "13e8d0dce000d004c000f00e8a1869308d3c13a2022003cfa001ad38131869308d3c13a2022003cf"
            "2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8d42138e4313ad4213ae43138d3813"
            "8e3913a901a200186d38138d38138a6d3913aaad3813608d4a038e4b03ad4a03ae4b038d3a138e3b"
            "13a902a200186d3a138d3a138a6d3b13aaad3a13608d4c038e4d03ad4c03ae4d038d3a138e3b13a9"
            "01a20085028603ad3a1338e5028d3a13ad3b13e503aaad3a13600000000000000100020000000000"
            "0000"
        ),
        "expected_console": "1\n",
    },
    "printi_bool_compound": {
        "out_fs_name": "harness-actc-alink-direct-prg-printi-bool-compound",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'PrintI((X<Y AND W(5)=7) OR Z(1)=1)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 57\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9gyr\n"
                "u w\n"
                "u z\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "v x 1\n"
                "v y 2\n"
                "k 5\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 89, 0, 0, 0, 1, 81, 0, 19, 81, 0, 19,
                83, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 59, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 70, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 73, 48, 255, 73, 32, 255, 18, 85, 0, 19, 85, 0, 17,
                2, 0, 20, 72, 18, 87, 0, 19, 87, 0, 17, 1, 0, 21, 72, 1,
                0, 2, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010adc512aec6128dbf128ec012adc712aec812ecc012900dd007cdbf129006f004a901d002a900"
            "a2008dbf128ec012a900a200ecc012d005cdbf12f004a901d002a900a2008dbf128ec012a905a200"
            "206c128dc1128ec212a907a200ecc212d005cdc112f004a900f002a901a2008dc1128ec212a900a2"
            "00ecc212d005cdc112f004a901d002a900a200186dbf128dbf128a6dc012aaadbf128dbf128ec012"
            "a901a200ecc0129007d00dcdbf129002f004a901d002a900a2008dbf128ec012a900a200ecc012d0"
            "05cdbf12f004a901d002a900a2008dbf128ec012a901a2002092128dc1128ec212a901a200ecc212"
            "d005cdc112f004a900f002a901a2008dc1128ec212a900a200ecc212d005cdc112f004a901d002a9"
            "00a200186dbf128dbf128a6dc012aaadbf128dbf128ec012a900a200ecc0129007d00dcdbf129002"
            "f004a901d002a900a2008dbf128ec012a9c38502a9128503a000a200adc012c927901dd007adbf12"
            "c910901438adbf12e9108dbf12adc012e9278dc012e8d0dce000d004c000f00e8a1869308dc312a2"
            "022003cfa001a200adc012c903901dd007adbf12c9e8901438adbf12e9e88dbf12adc012e9038dc0"
            "12e8d0dce000d004c000f00e8a1869308dc312a2022003cfa001a200adc012c900901dd007adbf12"
            "c964901438adbf12e9648dbf12adc012e9008dc012e8d0dce000d004c000f00e8a1869308dc312a2"
            "022003cfa001a200adc012c900901dd007adbf12c90a901438adbf12e90a8dbf12adc012e9008dc0"
            "12e8d0dce000d004c000f00e8a1869308dc312a2022003cfa001adbf121869308dc312a2022003cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf8dcf028ed002adcf02aed0028dc1128ec212"
            "a902a200186dc1128dc1128a6dc212aaadc112608dd1028ed202add102aed2028dc1128ec212a901"
            "a20085028603adc11238e5028dc112adc212e503aaadc112600000000000000100020000000000"
        ),
        "expected_console": "1",
    },
    "return_bool_plus_one": {
        "out_fs_name": "harness-actc-alink-direct-prg-return-bool-plus-one",
        "source": (
            'MODULE MAIN\r'
            'PROC FLAG(N)\r'
            'RETURN (N<3)+1\r'
            'PROC MAIN()\r'
            'PrintIE(FLAG(2))\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x flag 0 15\n"
            "x main 15 10\n"
            "b S0L0p0lp1ar\n"
            "b p2c0zr\n"
            "i 3\n"
            "i 1\n"
            "i 2\n"
            "v n 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 29, 0, 15, 0, 1, 27, 0, 18, 27, 0, 19,
                27, 0, 17, 3, 0, 28, 17, 1, 0, 20, 72, 17, 2, 0, 69, 0,
                0, 73, 49, 255, 73, 32, 255, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a902a200202e118d74118e7511a9788502a9118503a000a200ad7511c927901dd007ad7411c9"
            "10901438ad7411e9108d7411ad7511e9278d7511e8d0dce000d004c000f00e8a1869308d7811a202"
            "2003cfa001a200ad7511c903901dd007ad7411c9e8901438ad7411e9e88d7411ad7511e9038d7511"
            "e8d0dce000d004c000f00e8a1869308d7811a2022003cfa001a200ad7511c900901dd007ad7411c9"
            "64901438ad7411e9648d7411ad7511e9008d7511e8d0dce000d004c000f00e8a1869308d7811a202"
            "2003cfa001a200ad7511c900901dd007ad7411c90a901438ad7411e90a8d7411ad7511e9008d7511"
            "e8d0dce000d004c000f00e8a1869308d7811a2022003cfa001ad74111869308d7811a2022003cf20"
            "06cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf8d7a118e7b11ad7a11ae7b118d74118e"
            "7511a903a200ec7511900dd007cd74119006f004a901d002a900a2008d74118e7511a901a200186d"
            "74118d74118a6d7511aaad7411600000000000000000"
        ),
        "expected_console": "2\n",
    },
    "assign_bool_plus_one": {
        "out_fs_name": "harness-actc-alink-direct-prg-assign-bool-plus-one",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[0]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'X=((X<Y AND W(5)=7) OR Z(1)=1)+1\r'
                'PrintIE(X)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 67\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9gpAaS0L0zr\n"
                "u w\n"
                "u z\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "i 1\n"
                "v x 0\n"
                "v y 2\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 99, 0, 0, 0, 1, 91, 0, 19, 91, 0, 19,
                93, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 69, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 80, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 17, 1, 0, 20, 18, 91, 0, 19, 91, 0, 73, 49, 255, 73,
                32, 255, 18, 95, 0, 19, 95, 0, 17, 2, 0, 20, 72, 18, 97,
                0, 19, 97, 0, 17, 1, 0, 21, 72, 0, 0, 2, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010aded12aeee128de7128ee812adef12aef012ece812900dd007cde7129006f004a901d002a900"
            "a2008de7128ee812a900a200ece812d005cde712f004a901d002a900a2008de7128ee812a905a200"
            "2094128de9128eea12a907a200ecea12d005cde912f004a900f002a901a2008de9128eea12a900a2"
            "00ecea12d005cde912f004a901d002a900a200186de7128de7128a6de812aaade7128de7128ee812"
            "a901a200ece8129007d00dcde7129002f004a901d002a900a2008de7128ee812a900a200ece812d0"
            "05cde712f004a901d002a900a2008de7128ee812a901a20020ba128de9128eea12a901a200ecea12"
            "d005cde912f004a900f002a901a2008de9128eea12a900a200ecea12d005cde912f004a901d002a9"
            "00a200186de7128de7128a6de812aaade7128de7128ee812a900a200ece8129007d00dcde7129002"
            "f004a901d002a900a2008de7128ee812a901a200186de7128de7128a6de812aaade7128ded128eee"
            "12aded12aeee128de7128ee812a9eb8502a9128503a000a200ade812c927901dd007ade712c91090"
            "1438ade712e9108de712ade812e9278de812e8d0dce000d004c000f00e8a1869308deb12a2022003"
            "cfa001a200ade812c903901dd007ade712c9e8901438ade712e9e88de712ade812e9038de812e8d0"
            "dce000d004c000f00e8a1869308deb12a2022003cfa001a200ade812c900901dd007ade712c96490"
            "1438ade712e9648de712ade812e9008de812e8d0dce000d004c000f00e8a1869308deb12a2022003"
            "cfa001a200ade812c900901dd007ade712c90a901438ade712e90a8de712ade812e9008de812e8d0"
            "dce000d004c000f00e8a1869308deb12a2022003cfa001ade7121869308deb12a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf8df7028ef802adf702aef8028de9128eea12"
            "a902a200186de9128de9128a6dea12aaade912608df9028efa02adf902aefa028de9128eea12a901"
            "a20085028603ade91238e5028de912adea12e503aaade912600000000000000000020000000000"
        ),
        "expected_console": "2\n",
    },
    "arg_bool_plus_one": {
        "out_fs_name": "harness-actc-alink-direct-prg-arg-bool-plus-one",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC INC(N)\r'
                'RETURN N+1\r'
                'PROC MAIN()\r'
                'PrintIE(INC(((X<Y AND W(5)=7) OR Z(1)=1)+1))\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x inc 0 11\n"
                "x main 11 64\n"
                "b S2L2p0ar\n"
                "b L0L1lp1np2u0p3qp4nap5gp6np7u1p8qp9napAgpBac0zr\n"
                "u w\n"
                "u z\n"
                "i 1\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "i 1\n"
                "v x 1\n"
                "v y 2\n"
                "v n 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 109, 0, 11, 0, 1, 99, 0, 18, 103, 0,
                19, 103, 0, 17, 1, 0, 20, 72, 19, 99, 0, 19, 101, 0, 28,
                17, 0, 0, 23, 17, 5, 0, 69, 77, 0, 17, 7, 0, 22, 17, 0,
                0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1, 0, 69, 88,
                0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0, 29, 17, 1,
                0, 20, 69, 0, 0, 73, 49, 255, 73, 32, 255, 18, 105, 0, 19,
                105, 0, 17, 2, 0, 20, 72, 18, 107, 0, 19, 107, 0, 17, 1,
                0, 21, 72, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ad0a13ae0b138d04138e0513ad0c13ae0d13ec0513900dd007cd04139006f004a901d002a900"
            "a2008d04138e0513a900a200ec0513d005cd0413f004a901d002a900a2008d04138e0513a905a200"
            "20b1128d06138e0713a907a200ec0713d005cd0613f004a900f002a901a2008d06138e0713a900a2"
            "00ec0713d005cd0613f004a901d002a900a200186d04138d04138a6d0513aaad04138d04138e0513"
            "a901a200ec05139007d00dcd04139002f004a901d002a900a2008d04138e0513a900a200ec0513d0"
            "05cd0413f004a901d002a900a2008d04138e0513a901a20020d7128d06138e0713a901a200ec0713"
            "d005cd0613f004a900f002a901a2008d06138e0713a900a200ec0713d005cd0613f004a901d002a9"
            "00a200186d04138d04138a6d0513aaad04138d04138e0513a900a200ec05139007d00dcd04139002"
            "f004a901d002a900a2008d04138e0513a901a200186d04138d04138a6d0513aaad0413208b128d04"
            "138e0513a9088502a9138503a000a200ad0513c927901dd007ad0413c910901438ad0413e9108d04"
            "13ad0513e9278d0513e8d0dce000d004c000f00e8a1869308d0813a2022003cfa001a200ad0513c9"
            "03901dd007ad0413c9e8901438ad0413e9e88d0413ad0513e9038d0513e8d0dce000d004c000f00e"
            "8a1869308d0813a2022003cfa001a200ad0513c900901dd007ad0413c964901438ad0413e9648d04"
            "13ad0513e9008d0513e8d0dce000d004c000f00e8a1869308d0813a2022003cfa001a200ad0513c9"
            "00901dd007ad0413c90a901438ad0413e90a8d0413ad0513e9008d0513e8d0dce000d004c000f00e"
            "8a1869308d0813a2022003cfa001ad04131869308d0813a2022003cf2006cf8dd1038ed203a9a58d"
            "d003a90085028503a2024c0fcf8d0e138e0f13ad0e13ae0f138d04138e0513a901a200186d04138d"
            "04138a6d0513aaad0413608d16038e1703ad1603ae17038d06138e0713a902a200186d06138d0613"
            "8a6d0713aaad0613608d18038e1903ad1803ae19038d06138e0713a901a20085028603ad061338e5"
            "028d0613ad0713e503aaad06136000000000000001000200000000000000"
        ),
        "expected_console": "3\n",
    },
    "printie_bool_plus_one": {
        "out_fs_name": "harness-actc-alink-direct-prg-printie-bool-plus-one",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'PrintIE(((X<Y AND W(5)=7) OR Z(1)=1)+1)\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(N)\r'
                'RETURN N+2\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(N)\r'
                'RETURN N-1\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 61\n"
                "b L0L1lp0np1u0p2qp3nap4gp5np6u1p7qp8nap9gpAazr\n"
                "u w\n"
                "u z\n"
                "i 0\n"
                "i 5\n"
                "i 7\n"
                "i 0\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "i 1\n"
                "v x 1\n"
                "v y 2\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 11\n"
                "b S0L0p0ar\n"
                "i 2\n"
                "v n 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 11\n"
                "b S0L0p0mr\n"
                "i 1\n"
                "v n 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 93, 0, 0, 0, 1, 85, 0, 19, 85, 0, 19,
                87, 0, 28, 17, 0, 0, 23, 17, 5, 0, 69, 63, 0, 17, 7, 0,
                22, 17, 0, 0, 23, 20, 17, 1, 0, 29, 17, 0, 0, 23, 17, 1,
                0, 69, 74, 0, 17, 1, 0, 22, 17, 0, 0, 23, 20, 17, 0, 0,
                29, 17, 1, 0, 20, 73, 49, 255, 73, 32, 255, 18, 89, 0, 19,
                89, 0, 17, 2, 0, 20, 72, 18, 91, 0, 19, 91, 0, 17, 1, 0,
                21, 72, 1, 0, 2, 0, 0, 0, 0, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ade112aee2128ddb128edc12ade312aee412ecdc12900dd007cddb129006f004a901d002a900"
            "a2008ddb128edc12a900a200ecdc12d005cddb12f004a901d002a900a2008ddb128edc12a905a200"
            "2088128ddd128ede12a907a200ecde12d005cddd12f004a900f002a901a2008ddd128ede12a900a2"
            "00ecde12d005cddd12f004a901d002a900a200186ddb128ddb128a6ddc12aaaddb128ddb128edc12"
            "a901a200ecdc129007d00dcddb129002f004a901d002a900a2008ddb128edc12a900a200ecdc12d0"
            "05cddb12f004a901d002a900a2008ddb128edc12a901a20020ae128ddd128ede12a901a200ecde12"
            "d005cddd12f004a900f002a901a2008ddd128ede12a900a200ecde12d005cddd12f004a901d002a9"
            "00a200186ddb128ddb128a6ddc12aaaddb128ddb128edc12a900a200ecdc129007d00dcddb129002"
            "f004a901d002a900a2008ddb128edc12a901a200186ddb128ddb128a6ddc12aaaddb128ddb128edc"
            "12a9df8502a9128503a000a200addc12c927901dd007addb12c910901438addb12e9108ddb12addc"
            "12e9278ddc12e8d0dce000d004c000f00e8a1869308ddf12a2022003cfa001a200addc12c903901d"
            "d007addb12c9e8901438addb12e9e88ddb12addc12e9038ddc12e8d0dce000d004c000f00e8a1869"
            "308ddf12a2022003cfa001a200addc12c900901dd007addb12c964901438addb12e9648ddb12addc"
            "12e9008ddc12e8d0dce000d004c000f00e8a1869308ddf12a2022003cfa001a200addc12c900901d"
            "d007addb12c90a901438addb12e90a8ddb12addc12e9008ddc12e8d0dce000d004c000f00e8a1869"
            "308ddf12a2022003cfa001addb121869308ddf12a2022003cf2006cf8dd1038ed203a9a58dd003a9"
            "0085028503a2024c0fcf8deb028eec02adeb02aeec028ddd128ede12a902a200186ddd128ddd128a"
            "6dde12aaaddd12608ded028eee02aded02aeee028ddd128ede12a901a20085028603addd1238e502"
            "8ddd12adde12e503aaaddd12600000000000000100020000000000"
        ),
        "expected_console": "2\n",
    },
    "init_bool_compound": {
        "out_fs_name": "harness-actc-alink-avmrunc-init-bool-compound",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[(1<2 AND 2<3) OR NOT(0=1)]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b L0zr\n"
            "v x 1\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad3311ae34118d2d118e2e11a9318502a9118503a000a200ad2e11c927901dd007ad2d11c910901438ad2d11e9108d2d11ad2e11e9278d2e11e8d0dce000d004c000f00e8a1869308d3111a2022003cfa001a200ad2e11c903901dd007ad2d11c9e8901438ad2d11e9e88d2d11ad2e11e9038d2e11e8d0dce000d004c000f00e8a1869308d3111a2022003cfa001a200ad2e11c900901dd007ad2d11c964901438ad2d11e9648d2d11ad2e11e9008d2e11e8d0dce000d004c000f00e8a1869308d3111a2022003cfa001a200ad2e11c900901dd007ad2d11c90a901438ad2d11e90a8d2d11ad2e11e9008d2e11e8d0dce000d004c000f00e8a1869308d3111a2022003cfa001ad2d111869308d3111a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000100"
        ),
        "expected_console": "1\n",
    },
    "init_bool_plus_one": {
        "out_fs_name": "harness-actc-alink-direct-prg-init-bool-plus-one",
        "source": (
            'MODULE MAIN\r'
            'INT X=[((1<2 AND 2<3) OR NOT(0=1))+1]\r'
            'PROC MAIN()\r'
            'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 7\n"
            "b L0zr\n"
            "v x 2\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 11, 0, 0, 0, 1, 9, 0, 19, 9, 0, 73,
                49, 255, 73, 32, 255, 2, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010ad3311ae34118d2d118e2e11a9318502a9118503a000a200ad2e11c927901dd007ad2d11c910"
            "901438ad2d11e9108d2d11ad2e11e9278d2e11e8d0dce000d004c000f00e8a1869308d3111a20220"
            "03cfa001a200ad2e11c903901dd007ad2d11c9e8901438ad2d11e9e88d2d11ad2e11e9038d2e11e8"
            "d0dce000d004c000f00e8a1869308d3111a2022003cfa001a200ad2e11c900901dd007ad2d11c964"
            "901438ad2d11e9648d2d11ad2e11e9008d2e11e8d0dce000d004c000f00e8a1869308d3111a20220"
            "03cfa001a200ad2e11c900901dd007ad2d11c90a901438ad2d11e90a8d2d11ad2e11e9008d2e11e8"
            "d0dce000d004c000f00e8a1869308d3111a2022003cfa001ad2d111869308d3111a2022003cf2006"
            "cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000200"
        ),
        "expected_console": "2\n",
    },
    "proc_local_reinit": {
        "out_fs_name": "harness-actc-alink-direct-prg-proc-local-reinit",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC TICK()\r'
            'INT X=[0]\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'PrintIE(X)\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'TICK()\r'
            'TICK()\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x tick 0 29\n"
            "x main 29 7\n"
            "b p0S0L0zL0p1aS0L0zr\n"
            "b c0c0r\n"
            "i 0\n"
            "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes(
            [
                0, 16, 32, 28, 16, 32, 28, 16, 141, 209, 3, 142, 210, 3, 169, 165,
                141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 0,
                162, 0, 141, 128, 18, 142, 129, 18, 173, 128, 18, 174, 129, 18, 141, 122,
                18, 142, 123, 18, 169, 126, 133, 2, 169, 18, 133, 3, 160, 0, 162, 0,
                173, 123, 18, 201, 39, 144, 29, 208, 7, 173, 122, 18, 201, 16, 144, 20,
                56, 173, 122, 18, 233, 16, 141, 122, 18, 173, 123, 18, 233, 39, 141, 123,
                18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201,
                3, 144, 29, 208, 7, 173, 122, 18, 201, 232, 144, 20, 56, 173, 122, 18,
                233, 232, 141, 122, 18, 173, 123, 18, 233, 3, 141, 123, 18, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162,
                2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208,
                7, 173, 122, 18, 201, 100, 144, 20, 56, 173, 122, 18, 233, 100, 141, 122,
                18, 173, 123, 18, 233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18,
                201, 10, 144, 20, 56, 173, 122, 18, 233, 10, 141, 122, 18, 173, 123, 18,
                233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 173, 122,
                18, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 32, 6, 207, 173,
                128, 18, 174, 129, 18, 141, 122, 18, 142, 123, 18, 169, 1, 162, 0, 24,
                109, 122, 18, 141, 122, 18, 138, 109, 123, 18, 170, 173, 122, 18, 141, 128,
                18, 142, 129, 18, 173, 128, 18, 174, 129, 18, 141, 122, 18, 142, 123, 18,
                169, 126, 133, 2, 169, 18, 133, 3, 160, 0, 162, 0, 173, 123, 18, 201,
                39, 144, 29, 208, 7, 173, 122, 18, 201, 16, 144, 20, 56, 173, 122, 18,
                233, 16, 141, 122, 18, 173, 123, 18, 233, 39, 141, 123, 18, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162,
                2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201, 3, 144, 29, 208,
                7, 173, 122, 18, 201, 232, 144, 20, 56, 173, 122, 18, 233, 232, 141, 122,
                18, 173, 123, 18, 233, 3, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18,
                201, 100, 144, 20, 56, 173, 122, 18, 233, 100, 141, 122, 18, 173, 123, 18,
                233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 162, 0,
                173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18, 201, 10, 144, 20,
                56, 173, 122, 18, 233, 10, 141, 122, 18, 173, 123, 18, 233, 0, 141, 123,
                18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 173, 122, 18, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0,
                0, 0, 0, 0,
            ]
        ),
        "expected_console": "0\n1\n0\n1\n",
    },
    "byte_proc_local_reinit": {
        "out_fs_name": "harness-actc-alink-direct-prg-byte-proc-local-reinit",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC TICK()\r'
            'BYTE X=[0]\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'PrintIE(X)\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'TICK()\r'
            'TICK()\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x tick 0 29\n"
            "x main 29 7\n"
            "b p0S0L0zL0p1aS0L0zr\n"
            "b c0c0r\n"
            "i 0\n"
            "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes(
            [
                0, 16, 32, 28, 16, 32, 28, 16, 141, 209, 3, 142, 210, 3, 169, 165,
                141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 0,
                162, 0, 141, 128, 18, 142, 129, 18, 173, 128, 18, 174, 129, 18, 141, 122,
                18, 142, 123, 18, 169, 126, 133, 2, 169, 18, 133, 3, 160, 0, 162, 0,
                173, 123, 18, 201, 39, 144, 29, 208, 7, 173, 122, 18, 201, 16, 144, 20,
                56, 173, 122, 18, 233, 16, 141, 122, 18, 173, 123, 18, 233, 39, 141, 123,
                18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201,
                3, 144, 29, 208, 7, 173, 122, 18, 201, 232, 144, 20, 56, 173, 122, 18,
                233, 232, 141, 122, 18, 173, 123, 18, 233, 3, 141, 123, 18, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162,
                2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208,
                7, 173, 122, 18, 201, 100, 144, 20, 56, 173, 122, 18, 233, 100, 141, 122,
                18, 173, 123, 18, 233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18,
                201, 10, 144, 20, 56, 173, 122, 18, 233, 10, 141, 122, 18, 173, 123, 18,
                233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 173, 122,
                18, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 32, 6, 207, 173,
                128, 18, 174, 129, 18, 141, 122, 18, 142, 123, 18, 169, 1, 162, 0, 24,
                109, 122, 18, 141, 122, 18, 138, 109, 123, 18, 170, 173, 122, 18, 141, 128,
                18, 142, 129, 18, 173, 128, 18, 174, 129, 18, 141, 122, 18, 142, 123, 18,
                169, 126, 133, 2, 169, 18, 133, 3, 160, 0, 162, 0, 173, 123, 18, 201,
                39, 144, 29, 208, 7, 173, 122, 18, 201, 16, 144, 20, 56, 173, 122, 18,
                233, 16, 141, 122, 18, 173, 123, 18, 233, 39, 141, 123, 18, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162,
                2, 32, 3, 207, 160, 1, 162, 0, 173, 123, 18, 201, 3, 144, 29, 208,
                7, 173, 122, 18, 201, 232, 144, 20, 56, 173, 122, 18, 233, 232, 141, 122,
                18, 173, 123, 18, 233, 3, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18,
                201, 100, 144, 20, 56, 173, 122, 18, 233, 100, 141, 122, 18, 173, 123, 18,
                233, 0, 141, 123, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 162, 0,
                173, 123, 18, 201, 0, 144, 29, 208, 7, 173, 122, 18, 201, 10, 144, 20,
                56, 173, 122, 18, 233, 10, 141, 122, 18, 173, 123, 18, 233, 0, 141, 123,
                18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 160, 1, 173, 122, 18, 24, 105, 48,
                141, 126, 18, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0,
                0, 0, 0, 0,
            ]
        ),
        "expected_console": "0\n1\n0\n1\n",
    },
    "proc_local_param_loop": {
        "out_fs_name": "harness-actc-alink-direct-prg-proc-local-param-loop",
        "source": (
            'MODULE MAIN\r'
            'PROC COUNT(N)\r'
            'INT X=[N]\r'
            'DO\r'
            'PrintIE(X)\r'
            'X=X+1\r'
            'UNTIL X=2\r'
            'OD\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'COUNT(0)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x count 0 36\n"
            "x main 36 7\n"
            "b S0L0S1dL1zL1p0aS1L1p1qtor\n"
            "b p2c0r\n"
            "i 1\n"
            "i 2\n"
            "i 0\n"
            "v n 0\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a900a200201d108dd1038ed203a9a58dd003a90085028503a2024c0fcf8d8f118e9011ad8f11ae90118d91118e9211ad9111ae92118d89118e8a11a98d8502a9118503a000a200ad8a11c927901dd007ad8911c910901438ad8911e9108d8911ad8a11e9278d8a11e8d0dce000d004c000f00e8a1869308d8d11a2022003cfa001a200ad8a11c903901dd007ad8911c9e8901438ad8911e9e88d8911ad8a11e9038d8a11e8d0dce000d004c000f00e8a1869308d8d11a2022003cfa001a200ad8a11c900901dd007ad8911c964901438ad8911e9648d8911ad8a11e9008d8a11e8d0dce000d004c000f00e8a1869308d8d11a2022003cfa001a200ad8a11c900901dd007ad8911c90a901438ad8911e90a8d8911ad8a11e9008d8a11e8d0dce000d004c000f00e8a1869308d8d11a2022003cfa001ad89111869308d8d11a2022003cf2006cfad9111ae92118d89118e8a11a901a200186d89118d89118a6d8a11aaad89118d91118e9211ad9111ae92118d89118e8a11a902a200ec8a11d005cd8911f0034c2f106000000000000000000000"
        ),
        "expected_console": "0\n1\n",
    },
    "var16_module_slots": {
        "out_fs_name": "harness-actc-alink-direct-prg-var16-module-slots",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT A=[0]\r'
            'INT B=[1]\r'
            'INT C=[2]\r'
            'INT D=[3]\r'
            'INT E=[4]\r'
            'INT F=[5]\r'
            'INT G=[6]\r'
            'INT H=[7]\r'
            'INT I=[8]\r'
            'INT J=[9]\r'
            'INT K=[10]\r'
            'INT L=[11]\r'
            'INT M=[12]\r'
            'INT N=[13]\r'
            'INT O=[14]\r'
            'INT P=[15]\r'
            'PROC MAIN()\r'
            'PrintIE(K)\r'
            'PrintIE(P)\r'
            'P=P+1\r'
            'PrintIE(P)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 29\n"
            "b LAzLFzLFp0aSFLFzr\n"
            "i 1\n"
            "v a 0\n"
            "v b 1\n"
            "v c 2\n"
            "v d 3\n"
            "v e 4\n"
            "v f 5\n"
            "v g 6\n"
            "v h 7\n"
            "v i 8\n"
            "v j 9\n"
            "v k 10\n"
            "v l 11\n"
            "v m 12\n"
            "v n 13\n"
            "v o 14\n"
            "v p 15\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010ad9a13ae9b138d80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e910"
            "8d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad"
            "8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001"
            "a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a18"
            "69308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8"
            "d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfada413aea5138d"
            "80138e8113a9848502a9138503a000a200ad8113c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d"
            "8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad80"
            "13e9e88d8013ad8113e9038d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901d"
            "d007ad8013c964901438ad8013e9648d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003"
            "cfa001a200ad8113c900901dd007ad8013c90a901438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f0"
            "0e8a1869308d8413a2022003cfa001ad80131869308d8413a2022003cf2006cfada413aea5138d80138e8113a901a200"
            "186d80138d80138a6d8113aaad80138da4138ea513ada413aea5138d80138e8113a9848502a9138503a000a200ad8113"
            "c927901dd007ad8013c910901438ad8013e9108d8013ad8113e9278d8113e8d0dce000d004c000f00e8a1869308d8413"
            "a2022003cfa001a200ad8113c903901dd007ad8013c9e8901438ad8013e9e88d8013ad8113e9038d8113e8d0dce000d0"
            "04c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c964901438ad8013e9648d8013ad81"
            "13e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001a200ad8113c900901dd007ad8013c90a90"
            "1438ad8013e90a8d8013ad8113e9008d8113e8d0dce000d004c000f00e8a1869308d8413a2022003cfa001ad80131869"
            "308d8413a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000000010002000300"
            "0400050006000700080009000a000b000c000d000e000f00"
        ),
        "expected_console": "10\n15\n16\n",
    },
    "var16_proc_slots": {
        "out_fs_name": "harness-actc-alink-direct-prg-var16-proc-slots",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC SHOW(Z)\r'
            'INT A\r'
            'INT B\r'
            'INT C\r'
            'INT D\r'
            'INT E\r'
            'INT F\r'
            'INT G\r'
            'INT H\r'
            'INT I\r'
            'INT J\r'
            'INT K\r'
            'INT L\r'
            'INT M\r'
            'INT N\r'
            'INT O\r'
            'O=Z+2\r'
            'PrintIE(O)\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'SHOW(5)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x show 0 20\n"
            "x main 20 7\n"
            "b S0L0p0aSFLFzr\n"
            "b p1c0r\n"
            "i 2\n"
            "i 5\n"
            "v z 0\n"
            "v a 0\n"
            "v b 0\n"
            "v c 0\n"
            "v d 0\n"
            "v e 0\n"
            "v f 0\n"
            "v g 0\n"
            "v h 0\n"
            "v i 0\n"
            "v j 0\n"
            "v k 0\n"
            "v l 0\n"
            "v m 0\n"
            "v n 0\n"
            "v o 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a905a200201d108dd1038ed203a9a58dd003a90085028503a2024c0fcf8d66118e6711ad6611ae67118d60118e61"
            "11a902a200186d60118d60118a6d6111aaad60118d84118e8511ad8411ae85118d60118e6111a9648502a9118503a000"
            "a200ad6111c927901dd007ad6011c910901438ad6011e9108d6011ad6111e9278d6111e8d0dce000d004c000f00e8a18"
            "69308d6411a2022003cfa001a200ad6111c903901dd007ad6011c9e8901438ad6011e9e88d6011ad6111e9038d6111e8"
            "d0dce000d004c000f00e8a1869308d6411a2022003cfa001a200ad6111c900901dd007ad6011c964901438ad6011e964"
            "8d6011ad6111e9008d6111e8d0dce000d004c000f00e8a1869308d6411a2022003cfa001a200ad6111c900901dd007ad"
            "6011c90a901438ad6011e90a8d6011ad6111e9008d6111e8d0dce000d004c000f00e8a1869308d6411a2022003cfa001"
            "ad60111869308d6411a2022003cf2006cf60000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000"
        ),
        "expected_console": "7\n",
    },
    "digit_symbol_names": {
        "out_fs_name": "harness-actc-alink-direct-prg-digit-symbol-names",
        "source": (
            'MODULE MAIN\r'
            'INT V0=[1]\r'
            'PROC ADD1(N1)\r'
            'INT X2=[N1+1]\r'
            'PrintIE(X2)\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'PrintIE(V0)\r'
            'V0=V0+1\r'
            'PrintIE(V0)\r'
            'ADD1(5)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x add1 0 20\n"
            "x main 20 29\n"
            "b S1L1p0aS2L2zr\n"
            "b L0zL0p1aS0L0zp2c0r\n"
            "i 1\n"
            "i 1\n"
            "i 5\n"
            "v v0 1\n"
            "v n1 0\n"
            "v x2 0\n"
            "k 6\n"
            "n main\n"
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010adb913aeba138db3138eb413a9b78502a9138503a000a200adb413c927901dd007adb313c910901438adb313e9108db313adb413e9278db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c903901dd007adb313c9e8901438adb313e9e88db313adb413e9038db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c964901438adb313e9648db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c90a901438adb313e90a8db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001adb3131869308db713a2022003cf2006cfadb913aeba138db3138eb413a901a200186db3138db3138a6db413aaadb3138db9138eba13adb913aeba138db3138eb413a9b78502a9138503a000a200adb413c927901dd007adb313c910901438adb313e9108db313adb413e9278db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c903901dd007adb313c9e8901438adb313e9e88db313adb413e9038db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c964901438adb313e9648db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c90a901438adb313e90a8db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001adb3131869308db713a2022003cf2006cfa905a2002070128dd1038ed203a9a58dd003a90085028503a2024c0fcf8dbb138ebc13adbb13aebc138db3138eb413a901a200186db3138db3138a6db413aaadb3138dbd138ebe13adbd13aebe138db3138eb413a9b78502a9138503a000a200adb413c927901dd007adb313c910901438adb313e9108db313adb413e9278db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c903901dd007adb313c9e8901438adb313e9e88db313adb413e9038db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c964901438adb313e9648db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001a200adb413c900901dd007adb313c90a901438adb313e90a8db313adb413e9008db413e8d0dce000d004c000f00e8a1869308db713a2022003cfa001adb3131869308db713a2022003cf2006cf60000000000000010000000000"
        ),
        "expected_console": "1\n2\n6\n",
    },
    "digit_external_module_names": {
        "out_fs_name": "harness-actc-alink-direct-prg-digit-external-module-names",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintIE(W1())\r'
                'RETURN\r'
            ),
            "W1": (
                'MODULE W1\r'
                'PROC W1()\r'
                'RETURN 7\r'
            ),
        },
        "compile_modules": ["MAIN", "W1"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 7\n"
                "b u0zr\n"
                "u w1\n"
                "k 6\n"
                "n main\n"
            ),
            "W1": (
                "AVO1\n"
                "x w1 0 4\n"
                "b p0r\n"
                "i 7\n"
                "k 0\n"
                "n w1\n"
            ),
        },
        "expected_prg": bytes(
            [
                0, 16, 32, 42, 17, 141, 47, 17, 142, 48, 17, 169, 51, 133, 2, 169,
                17, 133, 3, 160, 0, 162, 0, 173, 48, 17, 201, 39, 144, 29, 208, 7,
                173, 47, 17, 201, 16, 144, 20, 56, 173, 47, 17, 233, 16, 141, 47, 17,
                173, 48, 17, 233, 39, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192,
                0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160,
                1, 162, 0, 173, 48, 17, 201, 3, 144, 29, 208, 7, 173, 47, 17, 201,
                232, 144, 20, 56, 173, 47, 17, 233, 232, 141, 47, 17, 173, 48, 17, 233,
                3, 141, 48, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138,
                24, 105, 48, 141, 51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173,
                48, 17, 201, 0, 144, 29, 208, 7, 173, 47, 17, 201, 100, 144, 20, 56,
                173, 47, 17, 233, 100, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17,
                232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141,
                51, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 48, 17, 201, 0,
                144, 29, 208, 7, 173, 47, 17, 201, 10, 144, 20, 56, 173, 47, 17, 233,
                10, 141, 47, 17, 173, 48, 17, 233, 0, 141, 48, 17, 232, 208, 220, 224,
                0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 160, 1, 173, 47, 17, 24, 105, 48, 141, 51, 17, 162, 2,
                32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208,
                3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 7, 162, 0,
                96, 0, 0, 0, 0, 0, 0,
            ]
        ),
        "expected_console": "7\n",
    },
    "large_object_proc_local_inits": {
        "out_fs_name": "harness-actc-alink-direct-prg-large-object-proc-local-inits",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC SHOW(Z)\r'
            'INT A=[0]\r'
            'INT B=[1]\r'
            'INT C=[2]\r'
            'INT D=[3]\r'
            'INT E=[4]\r'
            'INT F=[5]\r'
            'INT G=[6]\r'
            'INT H=[7]\r'
            'INT I=[8]\r'
            'INT J=[9]\r'
            'INT K=[10]\r'
            'INT L=[11]\r'
            'INT M=[12]\r'
            'INT N=[13]\r'
            'INT O=[14]\r'
            'O=Z+O\r'
            'PrintIE(O)\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'SHOW(2)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x show 0 110\n"
            "x main 110 7\n"
            "b S0p0S1p1S2p2S3p3S4p4S5p5S6p6S7p7S8p8S9p9SApASBpBSCpCSDpDSEpESFL0LFaSFLFzr\n"
            "b pFc0r\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 2\n"
            "v z 0\n"
            "v a 0\n"
            "v b 0\n"
            "v c 0\n"
            "v d 0\n"
            "v e 0\n"
            "v f 0\n"
            "v g 0\n"
            "v h 0\n"
            "v i 0\n"
            "v j 0\n"
            "v k 0\n"
            "v l 0\n"
            "v m 0\n"
            "v n 0\n"
            "v o 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a902a200201d108dd1038ed203a9a58dd003a90085028503a2024c0fcf8dfe118eff11a900a2008d00128e0112a9"
            "01a2008d02128e0312a902a2008d04128e0512a903a2008d06128e0712a904a2008d08128e0912a905a2008d0a128e0b"
            "12a906a2008d0c128e0d12a907a2008d0e128e0f12a908a2008d10128e1112a909a2008d12128e1312a90aa2008d1412"
            "8e1512a90ba2008d16128e1712a90ca2008d18128e1912a90da2008d1a128e1b12a90ea2008d1c128e1d12adfe11aeff"
            "118df8118ef911ad1c12ae1d12186df8118df8118a6df911aaadf8118d1c128e1d12ad1c12ae1d128df8118ef911a9fc"
            "8502a9118503a000a200adf911c927901dd007adf811c910901438adf811e9108df811adf911e9278df911e8d0dce000"
            "d004c000f00e8a1869308dfc11a2022003cfa001a200adf911c903901dd007adf811c9e8901438adf811e9e88df811ad"
            "f911e9038df911e8d0dce000d004c000f00e8a1869308dfc11a2022003cfa001a200adf911c900901dd007adf811c964"
            "901438adf811e9648df811adf911e9008df911e8d0dce000d004c000f00e8a1869308dfc11a2022003cfa001a200adf9"
            "11c900901dd007adf811c90a901438adf811e90a8df811adf911e9008df911e8d0dce000d004c000f00e8a1869308dfc"
            "11a2022003cfa001adf8111869308dfc11a2022003cf2006cf6000000000000000000000000000000000000000000000"
            "00000000000000000000000000000000"
        ),
        "expected_console": "16\n",
    },
    "export16_local_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-export16-local-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'P7()\r'
            'P8()\r'
            'P9()\r'
            'RETURN\r'
            'PROC P0()\r'
            'RETURN\r'
            'PROC P1()\r'
            'RETURN\r'
            'PROC P2()\r'
            'RETURN\r'
            'PROC P3()\r'
            'RETURN\r'
            'PROC P4()\r'
            'RETURN\r'
            'PROC P5()\r'
            'RETURN\r'
            'PROC P6()\r'
            'RETURN\r'
            'PROC P7()\r'
            'PrintE("SEVEN")\r'
            'RETURN\r'
            'PROC P8()\r'
            'PrintE("EIGHT")\r'
            'RETURN\r'
            'PROC P9()\r'
            'PrintE("NINE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 10\n"
            "x p0 10 1\n"
            "x p1 11 1\n"
            "x p2 12 1\n"
            "x p3 13 1\n"
            "x p4 14 1\n"
            "x p5 15 1\n"
            "x p6 16 1\n"
            "x p7 17 7\n"
            "x p8 24 7\n"
            "x p9 31 7\n"
            "b c8c9cAr\n"
            "b r\n"
            "b r\n"
            "b r\n"
            "b r\n"
            "b r\n"
            "b r\n"
            "b r\n"
            "b e0r\n"
            "b e1r\n"
            "b e2r\n"
            "s SEVEN\n"
            "s EIGHT\n"
            "s NINE\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010201f102030102041108dd1038ed203a9a58dd003a90085028503a2024c0fcfa9568502a9108503a2022003cf2006"
            "cf60a95c8502a9108503a2022003cf2006cf60a9628502a9108503a2022003cf2006cf6000000000534556454e004549"
            "474854004e494e4500"
        ),
        "expected_console": "SEVEN\nEIGHT\nNINE\n",
    },
    "external10_child_queue": {
        "out_fs_name": "harness-actc-alink-direct-prg-external10-child-queue",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'W0()\r'
                'W1()\r'
                'W2()\r'
                'W3()\r'
                'W4()\r'
                'W5()\r'
                'W6()\r'
                'W7()\r'
                'W8()\r'
                'W9()\r'
                'RETURN\r'
            ),
            "W0": (
                'MODULE W0\r'
                'PROC W0()\r'
                'PrintE("0")\r'
                'RETURN\r'
            ),
            "W1": (
                'MODULE W1\r'
                'PROC W1()\r'
                'PrintE("1")\r'
                'RETURN\r'
            ),
            "W2": (
                'MODULE W2\r'
                'PROC W2()\r'
                'PrintE("2")\r'
                'RETURN\r'
            ),
            "W3": (
                'MODULE W3\r'
                'PROC W3()\r'
                'PrintE("3")\r'
                'RETURN\r'
            ),
            "W4": (
                'MODULE W4\r'
                'PROC W4()\r'
                'PrintE("4")\r'
                'RETURN\r'
            ),
            "W5": (
                'MODULE W5\r'
                'PROC W5()\r'
                'PrintE("5")\r'
                'RETURN\r'
            ),
            "W6": (
                'MODULE W6\r'
                'PROC W6()\r'
                'PrintE("6")\r'
                'RETURN\r'
            ),
            "W7": (
                'MODULE W7\r'
                'PROC W7()\r'
                'PrintE("7")\r'
                'RETURN\r'
            ),
            "W8": (
                'MODULE W8\r'
                'PROC W8()\r'
                'PrintE("8")\r'
                'RETURN\r'
            ),
            "W9": (
                'MODULE W9\r'
                'PROC W9()\r'
                'PrintE("9")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["MAIN", "W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 31\n"
                "b u0u1u2u3u4u5u6u7u8u9r\n"
                "u w0\n"
                "u w1\n"
                "u w2\n"
                "u w3\n"
                "u w4\n"
                "u w5\n"
                "u w6\n"
                "u w7\n"
                "u w8\n"
                "u w9\n"
                "k 0\n"
                "n main\n"
            ),
            "W0": (
                "AVO1\n"
                "x w0 0 7\n"
                "b e0r\n"
                "s 0\n"
                "k 2\n"
                "n w0\n"
            ),
            "W1": (
                "AVO1\n"
                "x w1 0 7\n"
                "b e0r\n"
                "s 1\n"
                "k 2\n"
                "n w1\n"
            ),
            "W2": (
                "AVO1\n"
                "x w2 0 7\n"
                "b e0r\n"
                "s 2\n"
                "k 2\n"
                "n w2\n"
            ),
            "W3": (
                "AVO1\n"
                "x w3 0 7\n"
                "b e0r\n"
                "s 3\n"
                "k 2\n"
                "n w3\n"
            ),
            "W4": (
                "AVO1\n"
                "x w4 0 7\n"
                "b e0r\n"
                "s 4\n"
                "k 2\n"
                "n w4\n"
            ),
            "W5": (
                "AVO1\n"
                "x w5 0 7\n"
                "b e0r\n"
                "s 5\n"
                "k 2\n"
                "n w5\n"
            ),
            "W6": (
                "AVO1\n"
                "x w6 0 7\n"
                "b e0r\n"
                "s 6\n"
                "k 2\n"
                "n w6\n"
            ),
            "W7": (
                "AVO1\n"
                "x w7 0 7\n"
                "b e0r\n"
                "s 7\n"
                "k 2\n"
                "n w7\n"
            ),
            "W8": (
                "AVO1\n"
                "x w8 0 7\n"
                "b e0r\n"
                "s 8\n"
                "k 2\n"
                "n w8\n"
            ),
            "W9": (
                "AVO1\n"
                "x w9 0 7\n"
                "b e0r\n"
                "s 9\n"
                "k 2\n"
                "n w9\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010203410204510205610206710207810208910209a1020ab1020bc1020cd108dd1038ed203a9a58dd003a900850285"
            "03a2024c0fcfa9e28502a9108503a2022003cf2006cf60a9e48502a9108503a2022003cf2006cf60a9e68502a9108503"
            "a2022003cf2006cf60a9e88502a9108503a2022003cf2006cf60a9ea8502a9108503a2022003cf2006cf60a9ec8502a9"
            "108503a2022003cf2006cf60a9ee8502a9108503a2022003cf2006cf60a9f08502a9108503a2022003cf2006cf60a9f2"
            "8502a9108503a2022003cf2006cf60a9f48502a9108503a2022003cf2006cf6000000000300031003200330034003500"
            "3600370038003900"
        ),
        "expected_console": "0\n1\n2\n3\n4\n5\n6\n7\n8\n9\n",
    },
    "loop9_do_until": {
        "out_fs_name": "harness-actc-alink-direct-prg-loop9-do-until",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'DO\r'
            'PrintE("DEEP")\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'UNTIL 1=1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 97\n"
            "b ddddddddde0p0p1qtop2p3qtop4p5qtop6p7qtop8p9qtopApBqtopCpDqtopEpFqtopGpHqtor\n"
            "s DEEP\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a91d8502a9118503a2022003cf2006cfa901a2008d19118e1a11a901a200ec1a11d005cd1911f0034c0010a901a2"
            "008d19118e1a11a901a200ec1a11d005cd1911f0034c0010a901a2008d19118e1a11a901a200ec1a11d005cd1911f003"
            "4c0010a901a2008d19118e1a11a901a200ec1a11d005cd1911f0034c0010a901a2008d19118e1a11a901a200ec1a11d0"
            "05cd1911f0034c0010a901a2008d19118e1a11a901a200ec1a11d005cd1911f0034c0010a901a2008d19118e1a11a901"
            "a200ec1a11d005cd1911f0034c0010a901a2008d19118e1a11a901a200ec1a11d005cd1911f0034c0010a901a2008d19"
            "118e1a11a901a200ec1a11d005cd1911f0034c00108dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000044"
            "45455000"
        ),
        "expected_console": "DEEP\n",
    },
    "loop9_while": {
        "out_fs_name": "harness-actc-alink-direct-prg-loop9-while",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'WHILE 0=1 DO\r'
            'PrintE("BAD")\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 130\n"
            "b dp0p1qfdp2p3qfdp4p5qfdp6p7qfdp8p9qfdpApBqfdpCpDqfdpEpFqfdpGpHqfe0xxxxxxxxxe1r\n"
            "s BAD\n"
            "s DONE\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a900a2008d44118e4511a901a200ec4511d005cd4411f0034c1e11a900a2008d44118e4511a901a200ec4511d005"
            "cd4411f0034c1b11a900a2008d44118e4511a901a200ec4511d005cd4411f0034c1811a900a2008d44118e4511a901a2"
            "00ec4511d005cd4411f0034c1511a900a2008d44118e4511a901a200ec4511d005cd4411f0034c1211a900a2008d4411"
            "8e4511a901a200ec4511d005cd4411f0034c0f11a900a2008d44118e4511a901a200ec4511d005cd4411f0034c0c11a9"
            "00a2008d44118e4511a901a200ec4511d005cd4411f0034c0911a900a2008d44118e4511a901a200ec4511d005cd4411"
            "f0034c0611a9488502a9118503a2022003cf2006cf4cd8104cbd104ca2104c87104c6c104c51104c36104c1b104c0010"
            "a94c8502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000042414400444f"
            "4e4500"
        ),
        "expected_console": "DONE\n",
    },
    "string36_high_index": {
        "out_fs_name": "harness-actc-alink-direct-prg-string36-high-index",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC F()\r'
            + ''.join(f'PrintE("{value}")\r' for value in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXY")
            + 'RETURN\r'
            'PROC MAIN()\r'
            'PrintE("Z")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x f 0 211\n"
            "x main 211 7\n"
            "b e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFeGeHeIeJeKeLeMeNeOePeQeReSeTeUeVeWeXeYr\n"
            "b eZr\n"
            "s 0\n"
            "s 1\n"
            "s 2\n"
            "s 3\n"
            "s 4\n"
            "s 5\n"
            "s 6\n"
            "s 7\n"
            "s 8\n"
            "s 9\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "s Q\n"
            "s R\n"
            "s S\n"
            "s T\n"
            "s U\n"
            "s V\n"
            "s W\n"
            "s X\n"
            "s Y\n"
            "s Z\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a92a8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf000000005a00"
        ),
        "expected_console": "Z\n",
    },
    "int36_high_index": {
        "out_fs_name": "harness-actc-alink-direct-prg-int36-high-index",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC F()\r'
            + ''.join(f'PrintIE({value})\r' for value in range(31))
            + 'RETURN\r'
            + 'PROC G()\r'
            + ''.join(f'PrintIE({value})\r' for value in range(31, 35))
            + 'RETURN\r'
            'PROC MAIN()\r'
            'PrintIE(35)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x f 0 187\n"
            "x g 187 25\n"
            "x main 212 7\n"
            "b p0zp1zp2zp3zp4zp5zp6zp7zp8zp9zpAzpBzpCzpDzpEzpFzpGzpHzpIzpJzpKzpLzpMzpNzpOzpPzpQzpRzpSzpTzpUzr\n"
            "b pVzpWzpXzpYzr\n"
            "b pZzr\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 15\n"
            "i 16\n"
            "i 17\n"
            "i 18\n"
            "i 19\n"
            "i 20\n"
            "i 21\n"
            "i 22\n"
            "i 23\n"
            "i 24\n"
            "i 25\n"
            "i 26\n"
            "i 27\n"
            "i 28\n"
            "i 29\n"
            "i 30\n"
            "i 31\n"
            "i 32\n"
            "i 33\n"
            "i 34\n"
            "i 35\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a923a2008d2b118e2c11a92f8502a9118503a000a200ad2c11c927901dd007ad2b11c910901438ad2b11e9108d2b"
            "11ad2c11e9278d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cfa001a200ad2c11c903901dd007ad2b11"
            "c9e8901438ad2b11e9e88d2b11ad2c11e9038d2c11e8d0dce000d004c000f00e8a1869308d2f11a2022003cfa001a200"
            "ad2c11c900901dd007ad2b11c964901438ad2b11e9648d2b11ad2c11e9008d2c11e8d0dce000d004c000f00e8a186930"
            "8d2f11a2022003cfa001a200ad2c11c900901dd007ad2b11c90a901438ad2b11e90a8d2b11ad2c11e9008d2c11e8d0dc"
            "e000d004c000f00e8a1869308d2f11a2022003cfa001ad2b111869308d2f11a2022003cf2006cf8dd1038ed203a9a58d"
            "d003a90085028503a2024c0fcf000000000000"
        ),
        "expected_console": "35\n",
    },
    "body152_local_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-body152-local-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC T()\r'
            'X=X+1\r'
            'RETURN\r'
            'PROC MAIN()\r'
            + ('T()\r' * 74)
            + 'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x t 0 11\n"
            "x main 11 229\n"
            "b L0p0aS0r\n"
            + "b " + ("c0" * 74) + "L0zr\n"
            + "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b1220"
            "0b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b1220"
            "0b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b1220"
            "0b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b1220"
            "0b12200b12200b12200b12200b12200b12200b12200b12200b12200b12200b12ad3712ae38128d31128e3212a9358502"
            "a9128503a000a200ad3212c927901dd007ad3112c910901438ad3112e9108d3112ad3212e9278d3212e8d0dce000d004"
            "c000f00e8a1869308d3512a2022003cfa001a200ad3212c903901dd007ad3112c9e8901438ad3112e9e88d3112ad3212"
            "e9038d3212e8d0dce000d004c000f00e8a1869308d3512a2022003cfa001a200ad3212c900901dd007ad3112c9649014"
            "38ad3112e9648d3112ad3212e9008d3212e8d0dce000d004c000f00e8a1869308d3512a2022003cfa001a200ad3212c9"
            "00901dd007ad3112c90a901438ad3112e90a8d3112ad3212e9008d3212e8d0dce000d004c000f00e8a1869308d3512a2"
            "022003cfa001ad31121869308d3512a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfad3712"
            "ae38128d31128e3212a901a200186d31128d31128a6d3212aaad31128d37128e3812600000000000000000"
        ),
        "expected_console": "74\n",
    },
    "payload265_local_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-payload265-local-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC T()\r'
            'X=X+1\r'
            'RETURN\r'
            'PROC MAIN()\r'
            + ('T()\r' * 77)
            + 'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x t 0 11\n"
            "x main 11 238\n"
            "b L0p0aS0r\n"
            + "b " + ("c0" * 77) + "L0zr\n"
            + "i 1\n"
            "v x 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "001020141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "1412201412201412201412201412201412201412201412201412201412201412201412201412201412ad4012ae41128d"
            "3a128e3b12a93e8502a9128503a000a200ad3b12c927901dd007ad3a12c910901438ad3a12e9108d3a12ad3b12e9278d"
            "3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003cfa001a200ad3b12c903901dd007ad3a12c9e8901438ad3a"
            "12e9e88d3a12ad3b12e9038d3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003cfa001a200ad3b12c900901d"
            "d007ad3a12c964901438ad3a12e9648d3a12ad3b12e9008d3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003"
            "cfa001a200ad3b12c900901dd007ad3a12c90a901438ad3a12e90a8d3a12ad3b12e9008d3b12e8d0dce000d004c000f0"
            "0e8a1869308d3e12a2022003cfa001ad3a121869308d3e12a2022003cf2006cf8dd1038ed203a9a58dd003a900850285"
            "03a2024c0fcfad4012ae41128d3a128e3b12a901a200186d3a128d3a128a6d3b12aaad3a128d40128e41126000000000"
            "00000000"
        ),
        "expected_console": "77\n",
    },
    "payload269_local_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-payload269-local-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'INT Y=[0]\r'
            'INT Z=[0]\r'
            'PROC T()\r'
            'X=X+1\r'
            'RETURN\r'
            'PROC MAIN()\r'
            + ('T()\r' * 77)
            + 'PrintIE(X)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x t 0 11\n"
            "x main 11 238\n"
            "b L0p0aS0r\n"
            + "b " + ("c0" * 77) + "L0zr\n"
            + "i 1\n"
            "v x 0\n"
            "v y 0\n"
            "v z 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "001020141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220141220"
            "1412201412201412201412201412201412201412201412201412201412201412201412201412201412ad4012ae41128d"
            "3a128e3b12a93e8502a9128503a000a200ad3b12c927901dd007ad3a12c910901438ad3a12e9108d3a12ad3b12e9278d"
            "3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003cfa001a200ad3b12c903901dd007ad3a12c9e8901438ad3a"
            "12e9e88d3a12ad3b12e9038d3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003cfa001a200ad3b12c900901d"
            "d007ad3a12c964901438ad3a12e9648d3a12ad3b12e9008d3b12e8d0dce000d004c000f00e8a1869308d3e12a2022003"
            "cfa001a200ad3b12c900901dd007ad3a12c90a901438ad3a12e90a8d3a12ad3b12e9008d3b12e8d0dce000d004c000f0"
            "0e8a1869308d3e12a2022003cfa001ad3a121869308d3e12a2022003cf2006cf8dd1038ed203a9a58dd003a900850285"
            "03a2024c0fcfad4012ae41128d3a128e3b12a901a200186d3a128d3a128a6d3b12aaad3a128d40128e41126000000000"
            "0000000000000000"
        ),
        "expected_console": "77\n",
    },
    "code268_dead_local_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-code268-dead-local-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC T()\r'
            'RETURN\r'
            'PROC F()\r'
            + ('T()\r' * 40)
            + 'RETURN\r'
            'PROC G()\r'
            + ('T()\r' * 46)
            + 'RETURN\r'
            'PROC MAIN()\r'
            'PrintE("OK")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x t 0 1\n"
            "x f 1 121\n"
            "x g 122 139\n"
            "x main 261 7\n"
            "b r\n"
            + "b " + ("c0" * 40) + "r\n"
            + "b " + ("c0" * 46) + "r\n"
            + "b e0r\n"
            "s OK\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a92a8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf000000004f4b00"
        ),
        "expected_console": "OK\n",
    },
    "proc259_dead_printi_var": {
        "out_fs_name": "harness-actc-alink-direct-prg-proc259-dead-printi-var",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'INT X=[0]\r'
            'PROC BIG()\r'
            + ('PrintI(X)\r' * 43)
            + 'RETURN\r'
            'PROC MAIN()\r'
            'PrintE("OK")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x big 0 259\n"
            "x main 259 7\n"
            + "b " + ("L0y" * 43) + "r\n"
            + "b e0r\n"
            + "s OK\n"
            + "v x 0\n"
            + "k 7\n"
            + "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a92c8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000004f4b"
            "00"
        ),
        "expected_console": "OK\n",
    },
    "bool_not_external": {
        "out_fs_name": "harness-actc-alink-avmrunc-bool-not-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF NOT(Z()=1) THEN\r'
                'PrintE("OK")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'RETURN 0\r'
            ),
        },
        "compile_modules": ["MAIN", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 34\n"
                "b u0p0qp1np2qhe0we1vr\n"
                "u z\n"
                "s OK\n"
                "s BAD\n"
                "i 1\n"
                "i 0\n"
                "i 0\n"
                "k 2\n"
                "n main\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 4\n"
                "b p0r\n"
                "i 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 47, 0, 0, 0, 1, 40, 0, 69, 36, 0, 17,
                1, 0, 22, 17, 0, 0, 23, 17, 0, 0, 22, 24, 27, 0, 97, 40,
                0, 73, 16, 255, 25, 33, 0, 97, 43, 0, 73, 16, 255, 73, 32,
                255, 17, 0, 0, 72, 79, 75, 0, 66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010208b108d90108e9110a901a200ec9110d005cd9010f004a900f002a901a2008d90108e9110a9"
            "00a200ec9110d005cd9010f004a901d002a900a2008d90108e9110a900a200ec9110d005cd9010f0"
            "034c6510a9948502a9108503a2022003cf2006cf4c7510a9978502a9108503a2022003cf2006cf8d"
            "d1038ed203a9a58dd003a90085028503a2024c0fcfa900a20060000000004f4b0042414400"
        ),
        "expected_console": "OK\n",
    },
    "comparison_ops": {
        "out_fs_name": "harness-actc-alink-direct-prg-comparison-ops",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintIE(2 <> 3)\r'
            'PrintIE(2 < 3)\r'
            'PrintIE(3 <= 3)\r'
            'PrintIE(4 >= 3)\r'
            'PrintIE(4 <= 3)\r'
            'PrintIE(2 >= 3)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 37\n"
            "b i0i1i2i3i4i5r\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 0\n"
            "i 0\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d94168e9516a9988502a9168503a000a200ad9516c927901dd007ad9416c910901438ad9416e9108d94"
            "16ad9516e9278d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c903901dd007ad9416"
            "c9e8901438ad9416e9e88d9416ad9516e9038d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200"
            "ad9516c900901dd007ad9416c964901438ad9416e9648d9416ad9516e9008d9516e8d0dce000d004c000f00e8a186930"
            "8d9816a2022003cfa001a200ad9516c900901dd007ad9416c90a901438ad9416e90a8d9416ad9516e9008d9516e8d0dc"
            "e000d004c000f00e8a1869308d9816a2022003cfa001ad94161869308d9816a2022003cf2006cfa901a2008d94168e95"
            "16a9988502a9168503a000a200ad9516c927901dd007ad9416c910901438ad9416e9108d9416ad9516e9278d9516e8d0"
            "dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c903901dd007ad9416c9e8901438ad9416e9e88d"
            "9416ad9516e9038d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c900901dd007ad94"
            "16c964901438ad9416e9648d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a2"
            "00ad9516c900901dd007ad9416c90a901438ad9416e90a8d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869"
            "308d9816a2022003cfa001ad94161869308d9816a2022003cf2006cfa901a2008d94168e9516a9988502a9168503a000"
            "a200ad9516c927901dd007ad9416c910901438ad9416e9108d9416ad9516e9278d9516e8d0dce000d004c000f00e8a18"
            "69308d9816a2022003cfa001a200ad9516c903901dd007ad9416c9e8901438ad9416e9e88d9416ad9516e9038d9516e8"
            "d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c900901dd007ad9416c964901438ad9416e964"
            "8d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c900901dd007ad"
            "9416c90a901438ad9416e90a8d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001"
            "ad94161869308d9816a2022003cf2006cfa901a2008d94168e9516a9988502a9168503a000a200ad9516c927901dd007"
            "ad9416c910901438ad9416e9108d9416ad9516e9278d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa0"
            "01a200ad9516c903901dd007ad9416c9e8901438ad9416e9e88d9416ad9516e9038d9516e8d0dce000d004c000f00e8a"
            "1869308d9816a2022003cfa001a200ad9516c900901dd007ad9416c964901438ad9416e9648d9416ad9516e9008d9516"
            "e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c900901dd007ad9416c90a901438ad9416e9"
            "0a8d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001ad94161869308d9816a202"
            "2003cf2006cfa900a2008d94168e9516a9988502a9168503a000a200ad9516c927901dd007ad9416c910901438ad9416"
            "e9108d9416ad9516e9278d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c903901dd0"
            "07ad9416c9e8901438ad9416e9e88d9416ad9516e9038d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cf"
            "a001a200ad9516c900901dd007ad9416c964901438ad9416e9648d9416ad9516e9008d9516e8d0dce000d004c000f00e"
            "8a1869308d9816a2022003cfa001a200ad9516c900901dd007ad9416c90a901438ad9416e90a8d9416ad9516e9008d95"
            "16e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001ad94161869308d9816a2022003cf2006cfa900a2008d"
            "94168e9516a9988502a9168503a000a200ad9516c927901dd007ad9416c910901438ad9416e9108d9416ad9516e9278d"
            "9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c903901dd007ad9416c9e8901438ad94"
            "16e9e88d9416ad9516e9038d9516e8d0dce000d004c000f00e8a1869308d9816a2022003cfa001a200ad9516c900901d"
            "d007ad9416c964901438ad9416e9648d9416ad9516e9008d9516e8d0dce000d004c000f00e8a1869308d9816a2022003"
            "cfa001a200ad9516c900901dd007ad9416c90a901438ad9416e90a8d9416ad9516e9008d9516e8d0dce000d004c000f0"
            "0e8a1869308d9816a2022003cfa001ad94161869308d9816a2022003cf2006cf8dd1038ed203a9a58dd003a900850285"
            "03a2024c0fcf000000000000"
        ),
        "expected_console": "1\n1\n1\n1\n0\n0\n",
    },
    "many_string_indices": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-indices",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'PrintE("M")\r'
            'PrintE("N")\r'
            'PrintE("O")\r'
            'PrintE("P")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 97\n"
            "b e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFr\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 131, 0, 0, 0, 1, 99, 0, 97, 99, 0,
                73, 16, 255, 97, 101, 0, 73, 16, 255, 97, 103, 0, 73,
                16, 255, 97, 105, 0, 73, 16, 255, 97, 107, 0, 73, 16,
                255, 97, 109, 0, 73, 16, 255, 97, 111, 0, 73, 16, 255,
                97, 113, 0, 73, 16, 255, 97, 115, 0, 73, 16, 255, 97,
                117, 0, 73, 16, 255, 97, 119, 0, 73, 16, 255, 97, 121,
                0, 73, 16, 255, 97, 123, 0, 73, 16, 255, 97, 125, 0, 73,
                16, 255, 97, 127, 0, 73, 16, 255, 97, 129, 0, 73, 16,
                255, 73, 32, 255, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70,
                0, 71, 0, 72, 0, 73, 0, 74, 0, 75, 0, 76, 0, 77, 0, 78,
                0, 79, 0, 80, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a9188502a9118503a2022003cf2006cfa91a8502a9118503a2022003cf20"
            "06cfa91c8502a9118503a2022003cf2006cfa91e8502a9118503a2022003cf20"
            "06cfa9208502a9118503a2022003cf2006cfa9228502a9118503a2022003cf20"
            "06cfa9248502a9118503a2022003cf2006cfa9268502a9118503a2022003cf20"
            "06cfa9288502a9118503a2022003cf2006cfa92a8502a9118503a2022003cf20"
            "06cfa92c8502a9118503a2022003cf2006cfa92e8502a9118503a2022003cf20"
            "06cfa9308502a9118503a2022003cf2006cfa9328502a9118503a2022003cf20"
            "06cfa9348502a9118503a2022003cf2006cfa9368502a9118503a2022003cf20"
            "06cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000410042004300"
            "4400450046004700480049004a004b004c004d004e004f005000"
        ),
        "expected_console": "A\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "many_string_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 0 THEN\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'ELSE\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'PrintE("M")\r'
            'PrintE("N")\r'
            'PrintE("O")\r'
            'PrintE("P")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 110\n"
            "b p0p1qhe0e1e2e3e4e5e6e7we8e9eAeBeCeDeEeFvr\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 144, 0, 0, 0, 1, 112, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 61, 0, 97, 112, 0, 73, 16, 255, 97,
                114, 0, 73, 16, 255, 97, 116, 0, 73, 16, 255, 97, 118,
                0, 73, 16, 255, 97, 120, 0, 73, 16, 255, 97, 122, 0, 73,
                16, 255, 97, 124, 0, 73, 16, 255, 97, 126, 0, 73, 16,
                255, 25, 109, 0, 97, 128, 0, 73, 16, 255, 97, 130, 0, 73,
                16, 255, 97, 132, 0, 73, 16, 255, 97, 134, 0, 73, 16,
                255, 97, 136, 0, 73, 16, 255, 97, 138, 0, 73, 16, 255,
                97, 140, 0, 73, 16, 255, 97, 142, 0, 73, 16, 255, 73,
                32, 255, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71,
                0, 72, 0, 73, 0, 74, 0, 75, 0, 76, 0, 77, 0, 78, 0, 79,
                0, 80, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008d34118e3511a900a200ec3511d005cd3411f0034c9e10a93685"
            "02a9118503a2022003cf2006cfa9388502a9118503a2022003cf2006cfa93a85"
            "02a9118503a2022003cf2006cfa93c8502a9118503a2022003cf2006cfa93e85"
            "02a9118503a2022003cf2006cfa9408502a9118503a2022003cf2006cfa94285"
            "02a9118503a2022003cf2006cfa9448502a9118503a2022003cf2006cf4c1e11"
            "a9468502a9118503a2022003cf2006cfa9488502a9118503a2022003cf2006cf"
            "a94a8502a9118503a2022003cf2006cfa94c8502a9118503a2022003cf2006cf"
            "a94e8502a9118503a2022003cf2006cfa9508502a9118503a2022003cf2006cf"
            "a9528502a9118503a2022003cf2006cfa9548502a9118503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf00004100420043004400"
            "450046004700480049004a004b004c004d004e004f005000"
        ),
        "expected_console": "I\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "many_string_do_until": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-do-until",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'PrintE("M")\r'
            'PrintE("N")\r'
            'PrintE("O")\r'
            'PrintE("P")\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 107\n"
            "b de0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFp0p1qtor\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 141, 0, 0, 0, 1, 109, 0, 97, 109, 0,
                73, 16, 255, 97, 111, 0, 73, 16, 255, 97, 113, 0, 73,
                16, 255, 97, 115, 0, 73, 16, 255, 97, 117, 0, 73, 16,
                255, 97, 119, 0, 73, 16, 255, 97, 121, 0, 73, 16, 255,
                97, 123, 0, 73, 16, 255, 97, 125, 0, 73, 16, 255, 97,
                127, 0, 73, 16, 255, 97, 129, 0, 73, 16, 255, 97, 131,
                0, 73, 16, 255, 97, 133, 0, 73, 16, 255, 97, 135, 0, 73,
                16, 255, 97, 137, 0, 73, 16, 255, 97, 139, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 73, 32, 255, 65,
                0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73,
                0, 74, 0, 75, 0, 76, 0, 77, 0, 78, 0, 79, 0, 80, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a9338502a9118503a2022003cf2006cfa9358502a9118503a2022003cf20"
            "06cfa9378502a9118503a2022003cf2006cfa9398502a9118503a2022003cf20"
            "06cfa93b8502a9118503a2022003cf2006cfa93d8502a9118503a2022003cf20"
            "06cfa93f8502a9118503a2022003cf2006cfa9418502a9118503a2022003cf20"
            "06cfa9438502a9118503a2022003cf2006cfa9458502a9118503a2022003cf20"
            "06cfa9478502a9118503a2022003cf2006cfa9498502a9118503a2022003cf20"
            "06cfa94b8502a9118503a2022003cf2006cfa94d8502a9118503a2022003cf20"
            "06cfa94f8502a9118503a2022003cf2006cfa9518502a9118503a2022003cf20"
            "06cfa901a2008d31118e3211a901a200ec3211d005cd3111f0034c00108dd103"
            "8ed203a9a58dd003a90085028503a2024c0fcf00004100420043004400450046"
            "004700480049004a004b004c004d004e004f005000"
        ),
        "expected_console": "A\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "many_int_indices": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-int-indices",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintIE(0)\r'
            'PrintIE(1)\r'
            'PrintIE(2)\r'
            'PrintIE(3)\r'
            'PrintIE(4)\r'
            'PrintIE(5)\r'
            'PrintIE(6)\r'
            'PrintIE(7)\r'
            'PrintIE(8)\r'
            'PrintIE(9)\r'
            'PrintIE(10)\r'
            'PrintIE(11)\r'
            'PrintIE(12)\r'
            'PrintIE(13)\r'
            'PrintIE(14)\r'
            'PrintIE(15)\r'
            'PrintIE(16)\r'
            'PrintIE(17)\r'
            'PrintIE(18)\r'
            'PrintIE(19)\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 121\n"
            "b p0zp1zp2zp3zp4zp5zp6zp7zp8zp9zpAzpBzpCzpDzpEzpFzpGzpHzpIzpJzr\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 15\n"
            "i 16\n"
            "i 17\n"
            "i 18\n"
            "i 19\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 123, 0, 0, 0, 1, 123, 0, 17, 0, 0,
                73, 49, 255, 17, 1, 0, 73, 49, 255, 17, 2, 0, 73, 49,
                255, 17, 3, 0, 73, 49, 255, 17, 4, 0, 73, 49, 255, 17,
                5, 0, 73, 49, 255, 17, 6, 0, 73, 49, 255, 17, 7, 0, 73,
                49, 255, 17, 8, 0, 73, 49, 255, 17, 9, 0, 73, 49, 255,
                17, 10, 0, 73, 49, 255, 17, 11, 0, 73, 49, 255, 17, 12,
                0, 73, 49, 255, 17, 13, 0, 73, 49, 255, 17, 14, 0, 73,
                49, 255, 17, 15, 0, 73, 49, 255, 17, 16, 0, 73, 49, 255,
                17, 17, 0, 73, 49, 255, 17, 18, 0, 73, 49, 255, 17, 19,
                0, 73, 49, 255, 73, 32, 255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a900a2008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd0"
            "07adba25c910901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004"
            "c000f00e8a1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25"
            "c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e"
            "8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25c9649014"
            "38adba25e9648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a186930"
            "8dbc25a2022003cfa001a200adbb25c900901dd007adba25c90a901438adba25"
            "e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2"
            "022003cfa001adba251869308dbc25a2022003cf2006cfa901a2008dba258ebb"
            "25a9bc8502a9258503a000a200adbb25c927901dd007adba25c910901438adba"
            "25e9108dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25"
            "a2022003cfa001a200adbb25c903901dd007adba25c9e8901438adba25e9e88d"
            "ba25adbb25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003"
            "cfa001a200adbb25c900901dd007adba25c964901438adba25e9648dba25adbb"
            "25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a2"
            "00adbb25c900901dd007adba25c90a901438adba25e90a8dba25adbb25e9008d"
            "bb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001adba251869"
            "308dbc25a2022003cf2006cfa902a2008dba258ebb25a9bc8502a9258503a000"
            "a200adbb25c927901dd007adba25c910901438adba25e9108dba25adbb25e927"
            "8dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb"
            "25c903901dd007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8"
            "d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c90090"
            "1dd007adba25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000"
            "d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007ad"
            "ba25c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000"
            "f00e8a1869308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006"
            "cfa903a2008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007"
            "adba25c910901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c0"
            "00f00e8a1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9"
            "e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a"
            "1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25c964901438"
            "adba25e9648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308d"
            "bc25a2022003cfa001a200adbb25c900901dd007adba25c90a901438adba25e9"
            "0a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a202"
            "2003cfa001adba251869308dbc25a2022003cf2006cfa904a2008dba258ebb25"
            "a9bc8502a9258503a000a200adbb25c927901dd007adba25c910901438adba25"
            "e9108dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a2"
            "022003cfa001a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba"
            "25adbb25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cf"
            "a001a200adbb25c900901dd007adba25c964901438adba25e9648dba25adbb25"
            "e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200"
            "adbb25c900901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb"
            "25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001adba25186930"
            "8dbc25a2022003cf2006cfa905a2008dba258ebb25a9bc8502a9258503a000a2"
            "00adbb25c927901dd007adba25c910901438adba25e9108dba25adbb25e9278d"
            "bb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25"
            "c903901dd007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0"
            "dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901d"
            "d007adba25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000d0"
            "04c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba"
            "25c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f0"
            "0e8a1869308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006cf"
            "a906a2008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007ad"
            "ba25c910901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c000"
            "f00e8a1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9e8"
            "901438adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a18"
            "69308dbc25a2022003cfa001a200adbb25c900901dd007adba25c964901438ad"
            "ba25e9648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc"
            "25a2022003cfa001a200adbb25c900901dd007adba25c90a901438adba25e90a"
            "8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a20220"
            "03cfa001adba251869308dbc25a2022003cf2006cfa907a2008dba258ebb25a9"
            "bc8502a9258503a000a200adbb25c927901dd007adba25c910901438adba25e9"
            "108dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a202"
            "2003cfa001a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba25"
            "adbb25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa0"
            "01a200adbb25c900901dd007adba25c964901438adba25e9648dba25adbb25e9"
            "008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200ad"
            "bb25c900901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb25"
            "e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001adba251869308d"
            "bc25a2022003cf2006cfa908a2008dba258ebb25a9bc8502a9258503a000a200"
            "adbb25c927901dd007adba25c910901438adba25e9108dba25adbb25e9278dbb"
            "25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c9"
            "03901dd007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dc"
            "e000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd0"
            "07adba25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000d004"
            "c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25"
            "c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e"
            "8a1869308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006cfa9"
            "09a2008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007adba"
            "25c910901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c000f0"
            "0e8a1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9e890"
            "1438adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a1869"
            "308dbc25a2022003cfa001a200adbb25c900901dd007adba25c964901438adba"
            "25e9648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25"
            "a2022003cfa001a200adbb25c900901dd007adba25c90a901438adba25e90a8d"
            "ba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003"
            "cfa001adba251869308dbc25a2022003cf2006cfa90aa2008dba258ebb25a9bc"
            "8502a9258503a000a200adbb25c927901dd007adba25c910901438adba25e910"
            "8dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a20220"
            "03cfa001a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba25ad"
            "bb25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001"
            "a200adbb25c900901dd007adba25c964901438adba25e9648dba25adbb25e900"
            "8dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb"
            "25c900901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb25e8"
            "d0dce000d004c000f00e8a1869308dbc25a2022003cfa001adba251869308dbc"
            "25a2022003cf2006cfa90ba2008dba258ebb25a9bc8502a9258503a000a200ad"
            "bb25c927901dd007adba25c910901438adba25e9108dba25adbb25e9278dbb25"
            "e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c903"
            "901dd007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dce0"
            "00d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007"
            "adba25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000d004c0"
            "00f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25c9"
            "0a901438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a"
            "1869308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006cfa90c"
            "a2008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007adba25"
            "c910901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c000f00e"
            "8a1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9e89014"
            "38adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a186930"
            "8dbc25a2022003cfa001a200adbb25c900901dd007adba25c964901438adba25"
            "e9648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2"
            "022003cfa001a200adbb25c900901dd007adba25c90a901438adba25e90a8dba"
            "25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cf"
            "a001adba251869308dbc25a2022003cf2006cfa90da2008dba258ebb25a9bc85"
            "02a9258503a000a200adbb25c927901dd007adba25c910901438adba25e9108d"
            "ba25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003"
            "cfa001a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba25adbb"
            "25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a2"
            "00adbb25c900901dd007adba25c964901438adba25e9648dba25adbb25e9008d"
            "bb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25"
            "c900901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0"
            "dce000d004c000f00e8a1869308dbc25a2022003cfa001adba251869308dbc25"
            "a2022003cf2006cfa90ea2008dba258ebb25a9bc8502a9258503a000a200adbb"
            "25c927901dd007adba25c910901438adba25e9108dba25adbb25e9278dbb25e8"
            "d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c90390"
            "1dd007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dce000"
            "d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007ad"
            "ba25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000d004c000"
            "f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25c90a"
            "901438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a18"
            "69308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006cfa90fa2"
            "008dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007adba25c9"
            "10901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a"
            "1869308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9e8901438"
            "adba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a1869308d"
            "bc25a2022003cfa001a200adbb25c900901dd007adba25c964901438adba25e9"
            "648dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a202"
            "2003cfa001a200adbb25c900901dd007adba25c90a901438adba25e90a8dba25"
            "adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa0"
            "01adba251869308dbc25a2022003cf2006cfa910a2008dba258ebb25a9bc8502"
            "a9258503a000a200adbb25c927901dd007adba25c910901438adba25e9108dba"
            "25adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cf"
            "a001a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba25adbb25"
            "e9038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200"
            "adbb25c900901dd007adba25c964901438adba25e9648dba25adbb25e9008dbb"
            "25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c9"
            "00901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0dc"
            "e000d004c000f00e8a1869308dbc25a2022003cfa001adba251869308dbc25a2"
            "022003cf2006cfa911a2008dba258ebb25a9bc8502a9258503a000a200adbb25"
            "c927901dd007adba25c910901438adba25e9108dba25adbb25e9278dbb25e8d0"
            "dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c903901d"
            "d007adba25c9e8901438adba25e9e88dba25adbb25e9038dbb25e8d0dce000d0"
            "04c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba"
            "25c964901438adba25e9648dba25adbb25e9008dbb25e8d0dce000d004c000f0"
            "0e8a1869308dbc25a2022003cfa001a200adbb25c900901dd007adba25c90a90"
            "1438adba25e90a8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869"
            "308dbc25a2022003cfa001adba251869308dbc25a2022003cf2006cfa912a200"
            "8dba258ebb25a9bc8502a9258503a000a200adbb25c927901dd007adba25c910"
            "901438adba25e9108dba25adbb25e9278dbb25e8d0dce000d004c000f00e8a18"
            "69308dbc25a2022003cfa001a200adbb25c903901dd007adba25c9e8901438ad"
            "ba25e9e88dba25adbb25e9038dbb25e8d0dce000d004c000f00e8a1869308dbc"
            "25a2022003cfa001a200adbb25c900901dd007adba25c964901438adba25e964"
            "8dba25adbb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a20220"
            "03cfa001a200adbb25c900901dd007adba25c90a901438adba25e90a8dba25ad"
            "bb25e9008dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001"
            "adba251869308dbc25a2022003cf2006cfa913a2008dba258ebb25a9bc8502a9"
            "258503a000a200adbb25c927901dd007adba25c910901438adba25e9108dba25"
            "adbb25e9278dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa0"
            "01a200adbb25c903901dd007adba25c9e8901438adba25e9e88dba25adbb25e9"
            "038dbb25e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200ad"
            "bb25c900901dd007adba25c964901438adba25e9648dba25adbb25e9008dbb25"
            "e8d0dce000d004c000f00e8a1869308dbc25a2022003cfa001a200adbb25c900"
            "901dd007adba25c90a901438adba25e90a8dba25adbb25e9008dbb25e8d0dce0"
            "00d004c000f00e8a1869308dbc25a2022003cfa001adba251869308dbc25a202"
            "2003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf00000000"
        ),
        "expected_console": "0\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n",
    },
    "many_int_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-int-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 0 THEN\r'
            'PrintIE(0)\r'
            'PrintIE(1)\r'
            'PrintIE(2)\r'
            'PrintIE(3)\r'
            'PrintIE(4)\r'
            'PrintIE(5)\r'
            'PrintIE(6)\r'
            'PrintIE(7)\r'
            'ELSE\r'
            'PrintIE(8)\r'
            'PrintIE(9)\r'
            'PrintIE(10)\r'
            'PrintIE(11)\r'
            'PrintIE(12)\r'
            'PrintIE(13)\r'
            'PrintIE(14)\r'
            'PrintIE(15)\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 110\n"
            "b p0p1qhp2zp3zp4zp5zp6zp7zp8zp9zwpAzpBzpCzpDzpEzpFzpGzpHzvr\n"
            "i 1\n"
            "i 0\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 15\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 112, 0, 0, 0, 1, 112, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 61, 0, 17, 0, 0, 73, 49, 255, 17, 1,
                0, 73, 49, 255, 17, 2, 0, 73, 49, 255, 17, 3, 0, 73, 49,
                255, 17, 4, 0, 73, 49, 255, 17, 5, 0, 73, 49, 255, 17,
                6, 0, 73, 49, 255, 17, 7, 0, 73, 49, 255, 25, 109, 0, 17,
                8, 0, 73, 49, 255, 17, 9, 0, 73, 49, 255, 17, 10, 0, 73,
                49, 255, 17, 11, 0, 73, 49, 255, 17, 12, 0, 73, 49, 255,
                17, 13, 0, 73, 49, 255, 17, 14, 0, 73, 49, 255, 17, 15,
                0, 73, 49, 255, 73, 32, 255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008d84218e8521a900a200ec8521d005cd8421f0034cc618a900a2"
            "008d84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c9"
            "10901438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a"
            "1869308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438"
            "ad8421e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d"
            "8621a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e9"
            "648d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a202"
            "2003cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421"
            "ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa0"
            "01ad84211869308d8621a2022003cf2006cfa901a2008d84218e8521a9868502"
            "a9218503a000a200ad8521c927901dd007ad8421c910901438ad8421e9108d84"
            "21ad8521e9278d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cf"
            "a001a200ad8521c903901dd007ad8421c9e8901438ad8421e9e88d8421ad8521"
            "e9038d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200"
            "ad8521c900901dd007ad8421c964901438ad8421e9648d8421ad8521e9008d85"
            "21e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c9"
            "00901dd007ad8421c90a901438ad8421e90a8d8421ad8521e9008d8521e8d0dc"
            "e000d004c000f00e8a1869308d8621a2022003cfa001ad84211869308d8621a2"
            "022003cf2006cfa902a2008d84218e8521a9868502a9218503a000a200ad8521"
            "c927901dd007ad8421c910901438ad8421e9108d8421ad8521e9278d8521e8d0"
            "dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c903901d"
            "d007ad8421c9e8901438ad8421e9e88d8421ad8521e9038d8521e8d0dce000d0"
            "04c000f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad84"
            "21c964901438ad8421e9648d8421ad8521e9008d8521e8d0dce000d004c000f0"
            "0e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421c90a90"
            "1438ad8421e90a8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869"
            "308d8621a2022003cfa001ad84211869308d8621a2022003cf2006cfa903a200"
            "8d84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c910"
            "901438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a18"
            "69308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438ad"
            "8421e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d86"
            "21a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e964"
            "8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a20220"
            "03cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421ad"
            "8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001"
            "ad84211869308d8621a2022003cf2006cfa904a2008d84218e8521a9868502a9"
            "218503a000a200ad8521c927901dd007ad8421c910901438ad8421e9108d8421"
            "ad8521e9278d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa0"
            "01a200ad8521c903901dd007ad8421c9e8901438ad8421e9e88d8421ad8521e9"
            "038d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad"
            "8521c900901dd007ad8421c964901438ad8421e9648d8421ad8521e9008d8521"
            "e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c900"
            "901dd007ad8421c90a901438ad8421e90a8d8421ad8521e9008d8521e8d0dce0"
            "00d004c000f00e8a1869308d8621a2022003cfa001ad84211869308d8621a202"
            "2003cf2006cfa905a2008d84218e8521a9868502a9218503a000a200ad8521c9"
            "27901dd007ad8421c910901438ad8421e9108d8421ad8521e9278d8521e8d0dc"
            "e000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c903901dd0"
            "07ad8421c9e8901438ad8421e9e88d8421ad8521e9038d8521e8d0dce000d004"
            "c000f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421"
            "c964901438ad8421e9648d8421ad8521e9008d8521e8d0dce000d004c000f00e"
            "8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421c90a9014"
            "38ad8421e90a8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a186930"
            "8d8621a2022003cfa001ad84211869308d8621a2022003cf2006cfa906a2008d"
            "84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c91090"
            "1438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a1869"
            "308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438ad84"
            "21e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d8621"
            "a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e9648d"
            "8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003"
            "cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421ad85"
            "21e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001ad"
            "84211869308d8621a2022003cf2006cfa907a2008d84218e8521a9868502a921"
            "8503a000a200ad8521c927901dd007ad8421c910901438ad8421e9108d8421ad"
            "8521e9278d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001"
            "a200ad8521c903901dd007ad8421c9e8901438ad8421e9e88d8421ad8521e903"
            "8d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad85"
            "21c900901dd007ad8421c964901438ad8421e9648d8421ad8521e9008d8521e8"
            "d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c90090"
            "1dd007ad8421c90a901438ad8421e90a8d8421ad8521e9008d8521e8d0dce000"
            "d004c000f00e8a1869308d8621a2022003cfa001ad84211869308d8621a20220"
            "03cf2006cf4c6e21a908a2008d84218e8521a9868502a9218503a000a200ad85"
            "21c927901dd007ad8421c910901438ad8421e9108d8421ad8521e9278d8521e8"
            "d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c90390"
            "1dd007ad8421c9e8901438ad8421e9e88d8421ad8521e9038d8521e8d0dce000"
            "d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad"
            "8421c964901438ad8421e9648d8421ad8521e9008d8521e8d0dce000d004c000"
            "f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421c90a"
            "901438ad8421e90a8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a18"
            "69308d8621a2022003cfa001ad84211869308d8621a2022003cf2006cfa909a2"
            "008d84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c9"
            "10901438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a"
            "1869308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438"
            "ad8421e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d"
            "8621a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e9"
            "648d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a202"
            "2003cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421"
            "ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa0"
            "01ad84211869308d8621a2022003cf2006cfa90aa2008d84218e8521a9868502"
            "a9218503a000a200ad8521c927901dd007ad8421c910901438ad8421e9108d84"
            "21ad8521e9278d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cf"
            "a001a200ad8521c903901dd007ad8421c9e8901438ad8421e9e88d8421ad8521"
            "e9038d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200"
            "ad8521c900901dd007ad8421c964901438ad8421e9648d8421ad8521e9008d85"
            "21e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c9"
            "00901dd007ad8421c90a901438ad8421e90a8d8421ad8521e9008d8521e8d0dc"
            "e000d004c000f00e8a1869308d8621a2022003cfa001ad84211869308d8621a2"
            "022003cf2006cfa90ba2008d84218e8521a9868502a9218503a000a200ad8521"
            "c927901dd007ad8421c910901438ad8421e9108d8421ad8521e9278d8521e8d0"
            "dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c903901d"
            "d007ad8421c9e8901438ad8421e9e88d8421ad8521e9038d8521e8d0dce000d0"
            "04c000f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad84"
            "21c964901438ad8421e9648d8421ad8521e9008d8521e8d0dce000d004c000f0"
            "0e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421c90a90"
            "1438ad8421e90a8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869"
            "308d8621a2022003cfa001ad84211869308d8621a2022003cf2006cfa90ca200"
            "8d84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c910"
            "901438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a18"
            "69308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438ad"
            "8421e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d86"
            "21a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e964"
            "8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a20220"
            "03cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421ad"
            "8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001"
            "ad84211869308d8621a2022003cf2006cfa90da2008d84218e8521a9868502a9"
            "218503a000a200ad8521c927901dd007ad8421c910901438ad8421e9108d8421"
            "ad8521e9278d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa0"
            "01a200ad8521c903901dd007ad8421c9e8901438ad8421e9e88d8421ad8521e9"
            "038d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad"
            "8521c900901dd007ad8421c964901438ad8421e9648d8421ad8521e9008d8521"
            "e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c900"
            "901dd007ad8421c90a901438ad8421e90a8d8421ad8521e9008d8521e8d0dce0"
            "00d004c000f00e8a1869308d8621a2022003cfa001ad84211869308d8621a202"
            "2003cf2006cfa90ea2008d84218e8521a9868502a9218503a000a200ad8521c9"
            "27901dd007ad8421c910901438ad8421e9108d8421ad8521e9278d8521e8d0dc"
            "e000d004c000f00e8a1869308d8621a2022003cfa001a200ad8521c903901dd0"
            "07ad8421c9e8901438ad8421e9e88d8421ad8521e9038d8521e8d0dce000d004"
            "c000f00e8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421"
            "c964901438ad8421e9648d8421ad8521e9008d8521e8d0dce000d004c000f00e"
            "8a1869308d8621a2022003cfa001a200ad8521c900901dd007ad8421c90a9014"
            "38ad8421e90a8d8421ad8521e9008d8521e8d0dce000d004c000f00e8a186930"
            "8d8621a2022003cfa001ad84211869308d8621a2022003cf2006cfa90fa2008d"
            "84218e8521a9868502a9218503a000a200ad8521c927901dd007ad8421c91090"
            "1438ad8421e9108d8421ad8521e9278d8521e8d0dce000d004c000f00e8a1869"
            "308d8621a2022003cfa001a200ad8521c903901dd007ad8421c9e8901438ad84"
            "21e9e88d8421ad8521e9038d8521e8d0dce000d004c000f00e8a1869308d8621"
            "a2022003cfa001a200ad8521c900901dd007ad8421c964901438ad8421e9648d"
            "8421ad8521e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003"
            "cfa001a200ad8521c900901dd007ad8421c90a901438ad8421e90a8d8421ad85"
            "21e9008d8521e8d0dce000d004c000f00e8a1869308d8621a2022003cfa001ad"
            "84211869308d8621a2022003cf2006cf8dd1038ed203a9a58dd003a900850285"
            "03a2024c0fcf00000000"
        ),
        "expected_console": "8\n9\n10\n11\n12\n13\n14\n15\n",
    },
    "comparison_ops_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-comparison-ops-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 2 <> 3 THEN\r'
            'PrintE("NE")\r'
            'FI\r'
            'IF 2 < 3 THEN\r'
            'PrintE("LT")\r'
            'FI\r'
            'IF 3 <= 3 THEN\r'
            'PrintE("LE")\r'
            'FI\r'
            'IF 4 >= 3 THEN\r'
            'PrintE("GE")\r'
            'FI\r'
            'IF 4 <= 3 THEN\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'IF 2 >= 3 THEN\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 113\n"
            "b p0p1nhe0vp2p3lhe1vp4p5gp6qhe2vp7p8lp9qhe3vpApBgpCqhe4vpDpElpFqhe5vr\n"
            "s NE\n"
            "s LT\n"
            "s LE\n"
            "s GE\n"
            "s BAD1\n"
            "s BAD2\n"
            "i 2\n"
            "i 3\n"
            "i 2\n"
            "i 3\n"
            "i 3\n"
            "i 3\n"
            "i 0\n"
            "i 4\n"
            "i 3\n"
            "i 0\n"
            "i 4\n"
            "i 3\n"
            "i 0\n"
            "i 2\n"
            "i 3\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 137, 0, 0, 0, 1, 115, 0, 17, 2, 0,
                17, 3, 0, 23, 24, 16, 0, 97, 115, 0, 73, 16, 255, 17, 2,
                0, 17, 3, 0, 28, 24, 32, 0, 97, 118, 0, 73, 16, 255, 17,
                3, 0, 17, 3, 0, 29, 17, 0, 0, 22, 24, 52, 0, 97, 121, 0,
                73, 16, 255, 17, 4, 0, 17, 3, 0, 28, 17, 0, 0, 22, 24,
                72, 0, 97, 124, 0, 73, 16, 255, 17, 4, 0, 17, 3, 0, 29,
                17, 0, 0, 22, 24, 92, 0, 97, 127, 0, 73, 16, 255, 17, 2,
                0, 17, 3, 0, 28, 17, 0, 0, 22, 24, 112, 0, 97, 132, 0,
                73, 16, 255, 73, 32, 255, 78, 69, 0, 76, 84, 0, 76, 69,
                0, 71, 69, 0, 66, 65, 68, 49, 0, 66, 65, 68, 50, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a902a2008db4118eb511a903a200ecb511d005cdb411f004a901d002a900"
            "a200c900d0034c3710a9b68502a9118503a2022003cf2006cfa902a2008db411"
            "8eb511a903a200ecb511900dd007cdb4119006f004a901d002a900a200c900d0"
            "034c7210a9b98502a9118503a2022003cf2006cfa903a2008db4118eb511a903"
            "a200ecb5119007d00dcdb4119002f004a901d002a900a2008db4118eb511a900"
            "a200ecb511d005cdb411f0034cbd10a9bc8502a9118503a2022003cf2006cfa9"
            "04a2008db4118eb511a903a200ecb511900dd007cdb4119006f004a901d002a9"
            "00a2008db4118eb511a900a200ecb511d005cdb411f0034c0811a9bf8502a911"
            "8503a2022003cf2006cfa904a2008db4118eb511a903a200ecb5119007d00dcd"
            "b4119002f004a901d002a900a2008db4118eb511a900a200ecb511d005cdb411"
            "f0034c5311a9c28502a9118503a2022003cf2006cfa902a2008db4118eb511a9"
            "03a200ecb511900dd007cdb4119006f004a901d002a900a2008db4118eb511a9"
            "00a200ecb511d005cdb411f0034c9e11a9c78502a9118503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf00004e45004c54004c45"
            "0047450042414431004241443200"
        ),
        "expected_console": "NE\nLT\nLE\nGE\n",
    },
    "comparison_ops_loops": {
        "out_fs_name": "harness-actc-alink-avmrunc-comparison-ops-loops",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintE("DO")\r'
            'UNTIL 3 <= 3\r'
            'OD\r'
            'WHILE 2 >= 3 DO\r'
            'PrintE("BAD")\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 50\n"
            "b de0p0p1gp2qtodp3p4lp5qfe1xe2r\n"
            "s DO\n"
            "s BAD\n"
            "s DONE\n"
            "i 3\n"
            "i 3\n"
            "i 0\n"
            "i 2\n"
            "i 3\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 64, 0, 0, 0, 1, 52, 0, 97, 52, 0, 73,
                16, 255, 17, 3, 0, 17, 3, 0, 29, 17, 0, 0, 22, 24, 0, 0,
                17, 2, 0, 17, 3, 0, 28, 17, 0, 0, 22, 24, 43, 0, 97, 55,
                0, 73, 16, 255, 25, 20, 0, 97, 59, 0, 73, 16, 255, 73,
                32, 255, 68, 79, 0, 66, 65, 68, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a9c18502a9108503a2022003cf2006cfa903a2008dbf108ec010a903a200ecc0109007d00dcdbf109002f004a901d002a900a2008dbf108ec010a900a200ecc010d005cdbf10f0034c0010a902a2008dbf108ec010a903a200ecc010900dd007cdbf109006f004a901d002a900a2008dbf108ec010a900a200ecc010d005cdbf10f0034c9910a9c48502a9108503a2022003cf2006cf4c4b10a9c88502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000444f0042414400444f4e4500"
        ),
        "expected_console": "DO\nDONE\n",
    },
    "comparison_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-comparison-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'PrintE("YES")\r'
            'ELSE\r'
            'PrintE("NO")\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 36\n"
            "b p0p1ap2ghe0we1ve2r\n"
            "s YES\n"
            "s NO\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 50, 0, 0, 0, 1, 38, 0, 17, 2, 0, 17,
                12, 0, 20, 17, 10, 0, 29, 24, 23, 0, 97, 38, 0, 73, 16,
                255, 25, 29, 0, 97, 42, 0, 73, 16, 255, 97, 45, 0, 73,
                16, 255, 73, 32, 255, 89, 69, 83, 0, 78, 79, 0, 68, 79,
                78, 69, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a902a2008d8d108e8e10a90ca200186d8d108d8d108a6d8e10aaad8d108d8d108e8e10a90aa200ec8e109007d00dcd8d109002f004a901d002a900a200c900d0034c5710a98f8502a9108503a2022003cf2006cf4c6710a9938502a9108503a2022003cf2006cfa9968502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000594553004e4f00444f4e4500"
        ),
        "expected_console": "YES\nDONE\n",
    },
    "comparison_ops_branch_calls": {
        "out_fs_name": "harness-actc-alink-avmrunc-comparison-ops-branch-calls",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'IF 2 < 3 THEN\r'
            'HELLO()\r'
            'FI\r'
            'IF 2 >= 3 THEN\r'
            'PrintE("BAD")\r'
            'ELSE\r'
            'PrintE("OK")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 43\n"
            "b e0r\n"
            "b p0p1lhc0vp2p3lp4qhe1we2vr\n"
            "s HELLO\n"
            "s BAD\n"
            "s OK\n"
            "i 2\n"
            "i 3\n"
            "i 2\n"
            "i 3\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 65, 0, 7, 0, 1, 52, 0, 97, 52, 0, 73,
                16, 255, 72, 17, 2, 0, 17, 3, 0, 28, 24, 20, 0, 69, 0,
                0, 17, 2, 0, 17, 3, 0, 28, 17, 0, 0, 22, 24, 43, 0, 97,
                58, 0, 73, 16, 255, 25, 49, 0, 97, 62, 0, 73, 16, 255,
                73, 32, 255, 72, 69, 76, 76, 79, 0, 66, 65, 68, 0, 79,
                75, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a902a2008db3108eb410a903a200ecb410900dd007cdb3109006f004a901d002a900a200c900d0034c2e1020a210a902a2008db3108eb410a903a200ecb410900dd007cdb3109006f004a901d002a900a2008db3108eb410a900a200ecb410d005cdb310f0034c7c10a9bb8502a9108503a2022003cf2006cf4c8c10a9bf8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9b58502a9108503a2022003cf2006cf60000048454c4c4f00424144004f4b00"
        ),
        "expected_console": "HELLO\nOK\n",
    },
    "many_string_branch_external": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-branch-external",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'W()\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 95\n"
            "b p0p1qhu0e0e1e2e3e4e5e6e7e8e9eAeBweCvr\n"
            "u w\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 143, 0, 0, 0, 1, 110, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 88, 0, 69, 97, 0, 97, 110, 0, 73, 16,
                255, 97, 112, 0, 73, 16, 255, 97, 114, 0, 73, 16, 255,
                97, 116, 0, 73, 16, 255, 97, 118, 0, 73, 16, 255, 97,
                120, 0, 73, 16, 255, 97, 122, 0, 73, 16, 255, 97, 124,
                0, 73, 16, 255, 97, 126, 0, 73, 16, 255, 97, 128, 0, 73,
                16, 255, 97, 130, 0, 73, 16, 255, 97, 132, 0, 73, 16,
                255, 25, 94, 0, 97, 134, 0, 73, 16, 255, 73, 32, 255,
                97, 138, 0, 73, 0, 255, 17, 7, 0, 73, 49, 255, 72, 65,
                0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73,
                0, 74, 0, 75, 0, 76, 0, 66, 65, 68, 0, 84, 79, 79, 76, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D2A128E2B12A901A200EC2B12D005CD2A12F0034CE110200711A9308502A9128503A2022003CF2006CF"
            "A9328502A9128503A2022003CF2006CFA9348502A9128503A2022003CF2006CFA9368502A9128503A2022003CF2006CF"
            "A9388502A9128503A2022003CF2006CFA93A8502A9128503A2022003CF2006CFA93C8502A9128503A2022003CF2006CF"
            "A93E8502A9128503A2022003CF2006CFA9408502A9128503A2022003CF2006CFA9428502A9128503A2022003CF2006CF"
            "A9448502A9128503A2022003CF2006CFA9468502A9128503A2022003CF2006CF4CF110A9488502A9128503A2022003CF"
            "2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA94C8502A9128503A2022003CFA907A2008D2A128E2B12"
            "A92E8502A9128503A000A200AD2B12C927901DD007AD2A12C910901438AD2A12E9108D2A12AD2B12E9278D2B12E8D0DC"
            "E000D004C000F00E8A1869308D2E12A2022003CFA001A200AD2B12C903901DD007AD2A12C9E8901438AD2A12E9E88D2A"
            "12AD2B12E9038D2B12E8D0DCE000D004C000F00E8A1869308D2E12A2022003CFA001A200AD2B12C900901DD007AD2A12"
            "C964901438AD2A12E9648D2A12AD2B12E9008D2B12E8D0DCE000D004C000F00E8A1869308D2E12A2022003CFA001A200"
            "AD2B12C900901DD007AD2A12C90A901438AD2A12E90A8D2A12AD2B12E9008D2B12E8D0DCE000D004C000F00E8A186930"
            "8D2E12A2022003CFA001AD2A121869308D2E12A2022003CF2006CF600000000000004100420043004400450046004700"
            "480049004A004B004C0042414400544F4F4C00"

        ),
        "expected_console": "TOOL7\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\n",
    },
    "many_string_do_until_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-do-until-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 1 = 0 THEN\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'ELSE\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'PrintE("M")\r'
            'PrintE("N")\r'
            'PrintE("O")\r'
            'PrintE("P")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 120\n"
            "b dp0p1qhe0e1e2e3e4e5e6e7we8e9eAeBeCeDeEeFvp2p3qtor\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 154, 0, 0, 0, 1, 122, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 61, 0, 97, 122, 0, 73, 16, 255, 97,
                124, 0, 73, 16, 255, 97, 126, 0, 73, 16, 255, 97, 128,
                0, 73, 16, 255, 97, 130, 0, 73, 16, 255, 97, 132, 0, 73,
                16, 255, 97, 134, 0, 73, 16, 255, 97, 136, 0, 73, 16,
                255, 25, 109, 0, 97, 138, 0, 73, 16, 255, 97, 140, 0, 73,
                16, 255, 97, 142, 0, 73, 16, 255, 97, 144, 0, 73, 16,
                255, 97, 146, 0, 73, 16, 255, 97, 148, 0, 73, 16, 255,
                97, 150, 0, 73, 16, 255, 97, 152, 0, 73, 16, 255, 17,
                1, 0, 17, 1, 0, 22, 24, 0, 0, 73, 32, 255, 65, 0, 66, 0,
                67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74, 0,
                75, 0, 76, 0, 77, 0, 78, 0, 79, 0, 80, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008d4f118e5011a900a200ec5011d005cd4f11f0034c9e10a95185"
            "02a9118503a2022003cf2006cfa9538502a9118503a2022003cf2006cfa95585"
            "02a9118503a2022003cf2006cfa9578502a9118503a2022003cf2006cfa95985"
            "02a9118503a2022003cf2006cfa95b8502a9118503a2022003cf2006cfa95d85"
            "02a9118503a2022003cf2006cfa95f8502a9118503a2022003cf2006cf4c1e11"
            "a9618502a9118503a2022003cf2006cfa9638502a9118503a2022003cf2006cf"
            "a9658502a9118503a2022003cf2006cfa9678502a9118503a2022003cf2006cf"
            "a9698502a9118503a2022003cf2006cfa96b8502a9118503a2022003cf2006cf"
            "a96d8502a9118503a2022003cf2006cfa96f8502a9118503a2022003cf2006cf"
            "a901a2008d4f118e5011a901a200ec5011d005cd4f11f0034c00108dd1038ed2"
            "03a9a58dd003a90085028503a2024c0fcf000041004200430044004500460047"
            "00480049004a004b004c004d004e004f005000"
        ),
        "expected_console": "I\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "many_int_do_until_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-int-do-until-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 1 = 0 THEN\r'
            'PrintIE(0)\r'
            'PrintIE(1)\r'
            'PrintIE(2)\r'
            'PrintIE(3)\r'
            'PrintIE(4)\r'
            'PrintIE(5)\r'
            'PrintIE(6)\r'
            'PrintIE(7)\r'
            'ELSE\r'
            'PrintIE(8)\r'
            'PrintIE(9)\r'
            'PrintIE(10)\r'
            'PrintIE(11)\r'
            'PrintIE(12)\r'
            'PrintIE(13)\r'
            'PrintIE(14)\r'
            'PrintIE(15)\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 120\n"
            "b dp0p1qhp2zp3zp4zp5zp6zp7zp8zp9zwpAzpBzpCzpDzpEzpFzpGzpHzvpIpJqtor\n"
            "i 1\n"
            "i 0\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 15\n"
            "i 1\n"
            "i 1\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 122, 0, 0, 0, 1, 122, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 61, 0, 17, 0, 0, 73, 49, 255, 17, 1,
                0, 73, 49, 255, 17, 2, 0, 73, 49, 255, 17, 3, 0, 73, 49,
                255, 17, 4, 0, 73, 49, 255, 17, 5, 0, 73, 49, 255, 17,
                6, 0, 73, 49, 255, 17, 7, 0, 73, 49, 255, 25, 109, 0, 17,
                8, 0, 73, 49, 255, 17, 9, 0, 73, 49, 255, 17, 10, 0, 73,
                49, 255, 17, 11, 0, 73, 49, 255, 17, 12, 0, 73, 49, 255,
                17, 13, 0, 73, 49, 255, 17, 14, 0, 73, 49, 255, 17, 15,
                0, 73, 49, 255, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 73, 32,
                255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008d9f218ea021a900a200eca021d005cd9f21f0034cc618a900a2"
            "008d9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c9"
            "10901438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a"
            "1869308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438"
            "ad9f21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308d"
            "a121a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e9"
            "648d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a202"
            "2003cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21"
            "ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa0"
            "01ad9f211869308da121a2022003cf2006cfa901a2008d9f218ea021a9a18502"
            "a9218503a000a200ada021c927901dd007ad9f21c910901438ad9f21e9108d9f"
            "21ada021e9278da021e8d0dce000d004c000f00e8a1869308da121a2022003cf"
            "a001a200ada021c903901dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021"
            "e9038da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200"
            "ada021c900901dd007ad9f21c964901438ad9f21e9648d9f21ada021e9008da0"
            "21e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c9"
            "00901dd007ad9f21c90a901438ad9f21e90a8d9f21ada021e9008da021e8d0dc"
            "e000d004c000f00e8a1869308da121a2022003cfa001ad9f211869308da121a2"
            "022003cf2006cfa902a2008d9f218ea021a9a18502a9218503a000a200ada021"
            "c927901dd007ad9f21c910901438ad9f21e9108d9f21ada021e9278da021e8d0"
            "dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c903901d"
            "d007ad9f21c9e8901438ad9f21e9e88d9f21ada021e9038da021e8d0dce000d0"
            "04c000f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f"
            "21c964901438ad9f21e9648d9f21ada021e9008da021e8d0dce000d004c000f0"
            "0e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21c90a90"
            "1438ad9f21e90a8d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869"
            "308da121a2022003cfa001ad9f211869308da121a2022003cf2006cfa903a200"
            "8d9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c910"
            "901438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a18"
            "69308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438ad"
            "9f21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308da1"
            "21a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e964"
            "8d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a20220"
            "03cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21ad"
            "a021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001"
            "ad9f211869308da121a2022003cf2006cfa904a2008d9f218ea021a9a18502a9"
            "218503a000a200ada021c927901dd007ad9f21c910901438ad9f21e9108d9f21"
            "ada021e9278da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa0"
            "01a200ada021c903901dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021e9"
            "038da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ad"
            "a021c900901dd007ad9f21c964901438ad9f21e9648d9f21ada021e9008da021"
            "e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c900"
            "901dd007ad9f21c90a901438ad9f21e90a8d9f21ada021e9008da021e8d0dce0"
            "00d004c000f00e8a1869308da121a2022003cfa001ad9f211869308da121a202"
            "2003cf2006cfa905a2008d9f218ea021a9a18502a9218503a000a200ada021c9"
            "27901dd007ad9f21c910901438ad9f21e9108d9f21ada021e9278da021e8d0dc"
            "e000d004c000f00e8a1869308da121a2022003cfa001a200ada021c903901dd0"
            "07ad9f21c9e8901438ad9f21e9e88d9f21ada021e9038da021e8d0dce000d004"
            "c000f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21"
            "c964901438ad9f21e9648d9f21ada021e9008da021e8d0dce000d004c000f00e"
            "8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21c90a9014"
            "38ad9f21e90a8d9f21ada021e9008da021e8d0dce000d004c000f00e8a186930"
            "8da121a2022003cfa001ad9f211869308da121a2022003cf2006cfa906a2008d"
            "9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c91090"
            "1438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a1869"
            "308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438ad9f"
            "21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308da121"
            "a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e9648d"
            "9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003"
            "cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21ada0"
            "21e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001ad"
            "9f211869308da121a2022003cf2006cfa907a2008d9f218ea021a9a18502a921"
            "8503a000a200ada021c927901dd007ad9f21c910901438ad9f21e9108d9f21ad"
            "a021e9278da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001"
            "a200ada021c903901dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021e903"
            "8da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada0"
            "21c900901dd007ad9f21c964901438ad9f21e9648d9f21ada021e9008da021e8"
            "d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c90090"
            "1dd007ad9f21c90a901438ad9f21e90a8d9f21ada021e9008da021e8d0dce000"
            "d004c000f00e8a1869308da121a2022003cfa001ad9f211869308da121a20220"
            "03cf2006cf4c6e21a908a2008d9f218ea021a9a18502a9218503a000a200ada0"
            "21c927901dd007ad9f21c910901438ad9f21e9108d9f21ada021e9278da021e8"
            "d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c90390"
            "1dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021e9038da021e8d0dce000"
            "d004c000f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad"
            "9f21c964901438ad9f21e9648d9f21ada021e9008da021e8d0dce000d004c000"
            "f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21c90a"
            "901438ad9f21e90a8d9f21ada021e9008da021e8d0dce000d004c000f00e8a18"
            "69308da121a2022003cfa001ad9f211869308da121a2022003cf2006cfa909a2"
            "008d9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c9"
            "10901438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a"
            "1869308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438"
            "ad9f21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308d"
            "a121a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e9"
            "648d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a202"
            "2003cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21"
            "ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa0"
            "01ad9f211869308da121a2022003cf2006cfa90aa2008d9f218ea021a9a18502"
            "a9218503a000a200ada021c927901dd007ad9f21c910901438ad9f21e9108d9f"
            "21ada021e9278da021e8d0dce000d004c000f00e8a1869308da121a2022003cf"
            "a001a200ada021c903901dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021"
            "e9038da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200"
            "ada021c900901dd007ad9f21c964901438ad9f21e9648d9f21ada021e9008da0"
            "21e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c9"
            "00901dd007ad9f21c90a901438ad9f21e90a8d9f21ada021e9008da021e8d0dc"
            "e000d004c000f00e8a1869308da121a2022003cfa001ad9f211869308da121a2"
            "022003cf2006cfa90ba2008d9f218ea021a9a18502a9218503a000a200ada021"
            "c927901dd007ad9f21c910901438ad9f21e9108d9f21ada021e9278da021e8d0"
            "dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c903901d"
            "d007ad9f21c9e8901438ad9f21e9e88d9f21ada021e9038da021e8d0dce000d0"
            "04c000f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f"
            "21c964901438ad9f21e9648d9f21ada021e9008da021e8d0dce000d004c000f0"
            "0e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21c90a90"
            "1438ad9f21e90a8d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869"
            "308da121a2022003cfa001ad9f211869308da121a2022003cf2006cfa90ca200"
            "8d9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c910"
            "901438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a18"
            "69308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438ad"
            "9f21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308da1"
            "21a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e964"
            "8d9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a20220"
            "03cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21ad"
            "a021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001"
            "ad9f211869308da121a2022003cf2006cfa90da2008d9f218ea021a9a18502a9"
            "218503a000a200ada021c927901dd007ad9f21c910901438ad9f21e9108d9f21"
            "ada021e9278da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa0"
            "01a200ada021c903901dd007ad9f21c9e8901438ad9f21e9e88d9f21ada021e9"
            "038da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ad"
            "a021c900901dd007ad9f21c964901438ad9f21e9648d9f21ada021e9008da021"
            "e8d0dce000d004c000f00e8a1869308da121a2022003cfa001a200ada021c900"
            "901dd007ad9f21c90a901438ad9f21e90a8d9f21ada021e9008da021e8d0dce0"
            "00d004c000f00e8a1869308da121a2022003cfa001ad9f211869308da121a202"
            "2003cf2006cfa90ea2008d9f218ea021a9a18502a9218503a000a200ada021c9"
            "27901dd007ad9f21c910901438ad9f21e9108d9f21ada021e9278da021e8d0dc"
            "e000d004c000f00e8a1869308da121a2022003cfa001a200ada021c903901dd0"
            "07ad9f21c9e8901438ad9f21e9e88d9f21ada021e9038da021e8d0dce000d004"
            "c000f00e8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21"
            "c964901438ad9f21e9648d9f21ada021e9008da021e8d0dce000d004c000f00e"
            "8a1869308da121a2022003cfa001a200ada021c900901dd007ad9f21c90a9014"
            "38ad9f21e90a8d9f21ada021e9008da021e8d0dce000d004c000f00e8a186930"
            "8da121a2022003cfa001ad9f211869308da121a2022003cf2006cfa90fa2008d"
            "9f218ea021a9a18502a9218503a000a200ada021c927901dd007ad9f21c91090"
            "1438ad9f21e9108d9f21ada021e9278da021e8d0dce000d004c000f00e8a1869"
            "308da121a2022003cfa001a200ada021c903901dd007ad9f21c9e8901438ad9f"
            "21e9e88d9f21ada021e9038da021e8d0dce000d004c000f00e8a1869308da121"
            "a2022003cfa001a200ada021c900901dd007ad9f21c964901438ad9f21e9648d"
            "9f21ada021e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003"
            "cfa001a200ada021c900901dd007ad9f21c90a901438ad9f21e90a8d9f21ada0"
            "21e9008da021e8d0dce000d004c000f00e8a1869308da121a2022003cfa001ad"
            "9f211869308da121a2022003cf2006cfa901a2008d9f218ea021a901a200eca0"
            "21d005cd9f21f0034c00108dd1038ed203a9a58dd003a90085028503a2024c0f"
            "cf00000000"
        ),
        "expected_console": "8\n9\n10\n11\n12\n13\n14\n15\n",
    },
    "many_string_branch_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-branch-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 95\n"
                "b p0p1qhu0e0e1e2e3e4e5e6e7e8e9eAeBweCvr\n"
                "u w\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 95\n"
            "b p0p1qhu0e0e1e2e3e4e5e6e7e8e9eAeBweCvr\n"
            "u w\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 150, 0, 0, 0, 1, 114, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 88, 0, 69, 97, 0, 97, 114, 0, 73, 16,
                255, 97, 116, 0, 73, 16, 255, 97, 118, 0, 73, 16, 255,
                97, 120, 0, 73, 16, 255, 97, 122, 0, 73, 16, 255, 97,
                124, 0, 73, 16, 255, 97, 126, 0, 73, 16, 255, 97, 128,
                0, 73, 16, 255, 97, 130, 0, 73, 16, 255, 97, 132, 0, 73,
                16, 255, 97, 134, 0, 73, 16, 255, 97, 136, 0, 73, 16,
                255, 25, 94, 0, 97, 138, 0, 73, 16, 255, 73, 32, 255, 97,
                142, 0, 73, 16, 255, 69, 107, 0, 72, 97, 146, 0, 73, 16,
                255, 72, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0,
                72, 0, 73, 0, 74, 0, 75, 0, 76, 0, 66, 65, 68, 0, 77, 73,
                68, 0, 69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D2C118E2D11A901A200EC2D11D005CD2C11F0034CE110200711A9308502A9118503A2022003CF2006CF"
            "A9328502A9118503A2022003CF2006CFA9348502A9118503A2022003CF2006CFA9368502A9118503A2022003CF2006CF"
            "A9388502A9118503A2022003CF2006CFA93A8502A9118503A2022003CF2006CFA93C8502A9118503A2022003CF2006CF"
            "A93E8502A9118503A2022003CF2006CFA9408502A9118503A2022003CF2006CFA9428502A9118503A2022003CF2006CF"
            "A9448502A9118503A2022003CF2006CFA9468502A9118503A2022003CF2006CF4CF110A9488502A9118503A2022003CF"
            "2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA94C8502A9118503A2022003CF2006CF201B1160A95085"
            "02A9118503A2022003CF2006CF60000000004100420043004400450046004700480049004A004B004C00424144004D49"
            "4400454E4400"

        ),
        "expected_console": "MID\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\n",
    },
    "many_string_nested_loops_external": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-nested-loops-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'DO\r'
                'WHILE 1 = 0 DO\r'
                'PrintE("BAD")\r'
                'OD\r'
                'W()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 93\n"
                "b ddp0p1qfe0xu0e1e2e3e4e5e6e7e8e9eAp2p3qtor\n"
                "u w\n"
                "s BAD\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 93\n"
            "b ddp0p1qfe0xu0e1e2e3e4e5e6e7e8e9eAp2p3qtor\n"
            "u w\n"
            "s BAD\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 132, 0, 0, 0, 1, 102, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 19, 0, 97, 102, 0, 73, 16, 255, 25,
                0, 0, 69, 95, 0, 97, 106, 0, 73, 16, 255, 97, 108, 0,
                73, 16, 255, 97, 110, 0, 73, 16, 255, 97, 112, 0, 73,
                16, 255, 97, 114, 0, 73, 16, 255, 97, 116, 0, 73, 16,
                255, 97, 118, 0, 73, 16, 255, 97, 120, 0, 73, 16, 255,
                97, 122, 0, 73, 16, 255, 97, 124, 0, 73, 16, 255, 17,
                1, 0, 17, 1, 0, 22, 24, 0, 0, 73, 32, 255, 97, 126, 0,
                73, 16, 255, 72, 66, 65, 68, 0, 65, 0, 66, 0, 67, 0, 68,
                0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74, 0, 84, 79, 79,
                76, 55, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D13118E1411A900A200EC1411D005CD1311F0034C2E10A9178502A9118503A2022003CF2006CF4C0010"
            "200211A91B8502A9118503A2022003CF2006CFA91D8502A9118503A2022003CF2006CFA91F8502A9118503A2022003CF"
            "2006CFA9218502A9118503A2022003CF2006CFA9238502A9118503A2022003CF2006CFA9258502A9118503A2022003CF"
            "2006CFA9278502A9118503A2022003CF2006CFA9298502A9118503A2022003CF2006CFA92B8502A9118503A2022003CF"
            "2006CFA92D8502A9118503A2022003CF2006CFA901A2008D13118E1411A901A200EC1411D005CD1311F0034C00108DD1"
            "038ED203A9A58DD003A90085028503A2024C0FCFA92F8502A9118503A2022003CF2006CF600000000042414400410042"
            "0043004400450046004700480049004A00544F4F4C3700"

        ),
        "expected_console": "TOOL7\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\n",
    },
    "many_string_branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-branch-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 98\n"
                "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBweCvr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 98\n"
            "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBweCvr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 169, 0, 0, 0, 1, 127, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 91, 0, 69, 100, 0, 69, 110, 0, 97, 127,
                0, 73, 16, 255, 97, 129, 0, 73, 16, 255, 97, 131, 0, 73,
                16, 255, 97, 133, 0, 73, 16, 255, 97, 135, 0, 73, 16, 255,
                97, 137, 0, 73, 16, 255, 97, 139, 0, 73, 16, 255, 97, 141,
                0, 73, 16, 255, 97, 143, 0, 73, 16, 255, 97, 145, 0, 73,
                16, 255, 97, 147, 0, 73, 16, 255, 97, 149, 0, 73, 16, 255,
                25, 97, 0, 97, 151, 0, 73, 16, 255, 73, 32, 255, 97, 155,
                0, 73, 16, 255, 69, 120, 0, 72, 97, 160, 0, 73, 16, 255,
                69, 120, 0, 72, 97, 165, 0, 73, 16, 255, 72, 65, 0, 66, 0,
                67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74, 0,
                75, 0, 76, 0, 66, 65, 68, 0, 77, 73, 68, 49, 0, 77, 73, 68,
                50, 0, 69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D43118E4411A901A200EC4411D005CD4311F0034CE410200A11201E11A9478502A9118503A2022003CF"
            "2006CFA9498502A9118503A2022003CF2006CFA94B8502A9118503A2022003CF2006CFA94D8502A9118503A2022003CF"
            "2006CFA94F8502A9118503A2022003CF2006CFA9518502A9118503A2022003CF2006CFA9538502A9118503A2022003CF"
            "2006CFA9558502A9118503A2022003CF2006CFA9578502A9118503A2022003CF2006CFA9598502A9118503A2022003CF"
            "2006CFA95B8502A9118503A2022003CF2006CFA95D8502A9118503A2022003CF2006CF4CF410A95F8502A9118503A202"
            "2003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9638502A9118503A2022003CF2006CF20321160"
            "A9688502A9118503A2022003CF2006CF20321160A96D8502A9118503A2022003CF2006CF600000000041004200430044"
            "00450046004700480049004A004B004C00424144004D494431004D49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\n",
    },
    "many_string17_branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string17-branch-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'PrintE("M")\r'
                'PrintE("N")\r'
                'PrintE("O")\r'
                'PrintE("P")\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 122\n"
                "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFweGvr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s M\n"
                "s N\n"
                "s O\n"
                "s P\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 122\n"
            "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFweGvr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 201, 0, 0, 0, 1, 151, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 115, 0, 69, 124, 0, 69, 134, 0, 97,
                151, 0, 73, 16, 255, 97, 153, 0, 73, 16, 255, 97, 155,
                0, 73, 16, 255, 97, 157, 0, 73, 16, 255, 97, 159, 0, 73,
                16, 255, 97, 161, 0, 73, 16, 255, 97, 163, 0, 73, 16,
                255, 97, 165, 0, 73, 16, 255, 97, 167, 0, 73, 16, 255,
                97, 169, 0, 73, 16, 255, 97, 171, 0, 73, 16, 255, 97,
                173, 0, 73, 16, 255, 97, 175, 0, 73, 16, 255, 97, 177,
                0, 73, 16, 255, 97, 179, 0, 73, 16, 255, 97, 181, 0, 73,
                16, 255, 25, 121, 0, 97, 183, 0, 73, 16, 255, 73, 32,
                255, 97, 187, 0, 73, 16, 255, 69, 144, 0, 72, 97, 192,
                0, 73, 16, 255, 69, 144, 0, 72, 97, 197, 0, 73, 16, 255,
                72, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72,
                0, 73, 0, 74, 0, 75, 0, 76, 0, 77, 0, 78, 0, 79, 0, 80,
                0, 66, 65, 68, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0,
                69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D83118E8411A901A200EC8411D005CD8311F0034C2411204A11205E11A9878502A9118503A2022003CF"
            "2006CFA9898502A9118503A2022003CF2006CFA98B8502A9118503A2022003CF2006CFA98D8502A9118503A2022003CF"
            "2006CFA98F8502A9118503A2022003CF2006CFA9918502A9118503A2022003CF2006CFA9938502A9118503A2022003CF"
            "2006CFA9958502A9118503A2022003CF2006CFA9978502A9118503A2022003CF2006CFA9998502A9118503A2022003CF"
            "2006CFA99B8502A9118503A2022003CF2006CFA99D8502A9118503A2022003CF2006CFA99F8502A9118503A2022003CF"
            "2006CFA9A18502A9118503A2022003CF2006CFA9A38502A9118503A2022003CF2006CFA9A58502A9118503A2022003CF"
            "2006CF4C3411A9A78502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9AB8502"
            "A9118503A2022003CF2006CF20721160A9B08502A9118503A2022003CF2006CF20721160A9B58502A9118503A2022003"
            "CF2006CF60000000004100420043004400450046004700480049004A004B004C004D004E004F005000424144004D4944"
            "31004D49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "dense_return_branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-dense-return-branch-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'PrintE("M")\r'
                'PrintE("N")\r'
                'PrintE("O")\r'
                'PrintE("P")\r'
                'RETURN\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'PrintE("TAIL")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 129\n"
                "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrweGveHr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s M\n"
                "s N\n"
                "s O\n"
                "s P\n"
                "s BAD\n"
                "s TAIL\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 129\n"
            "b p0p1qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrweGveHr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "s BAD\n"
            "s TAIL\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 215, 0, 0, 0, 1, 160, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 118, 0, 69, 133, 0, 69, 143, 0, 97,
                160, 0, 73, 16, 255, 97, 162, 0, 73, 16, 255, 97, 164,
                0, 73, 16, 255, 97, 166, 0, 73, 16, 255, 97, 168, 0, 73,
                16, 255, 97, 170, 0, 73, 16, 255, 97, 172, 0, 73, 16,
                255, 97, 174, 0, 73, 16, 255, 97, 176, 0, 73, 16, 255,
                97, 178, 0, 73, 16, 255, 97, 180, 0, 73, 16, 255, 97,
                182, 0, 73, 16, 255, 97, 184, 0, 73, 16, 255, 97, 186,
                0, 73, 16, 255, 97, 188, 0, 73, 16, 255, 97, 190, 0, 73,
                16, 255, 25, 130, 0, 25, 124, 0, 97, 192, 0, 73, 16, 255,
                97, 196, 0, 73, 16, 255, 73, 32, 255, 97, 201, 0, 73, 16,
                255, 69, 153, 0, 72, 97, 206, 0, 73, 16, 255, 69, 153, 0,
                72, 97, 211, 0, 73, 16, 255, 72, 65, 0, 66, 0, 67, 0, 68,
                0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74, 0, 75, 0, 76,
                0, 77, 0, 78, 0, 79, 0, 80, 0, 66, 65, 68, 0, 84, 65, 73,
                76, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69, 78, 68,
                0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D70118E7111A901A200EC7111D005CD7011F0034C3711203711204B11A9748502A9118503A2022003CF"
            "2006CFA9768502A9118503A2022003CF2006CFA9788502A9118503A2022003CF2006CFA97A8502A9118503A2022003CF"
            "2006CFA97C8502A9118503A2022003CF2006CFA97E8502A9118503A2022003CF2006CFA9808502A9118503A2022003CF"
            "2006CFA9828502A9118503A2022003CF2006CFA9848502A9118503A2022003CF2006CFA9868502A9118503A2022003CF"
            "2006CFA9888502A9118503A2022003CF2006CFA98A8502A9118503A2022003CF2006CFA98C8502A9118503A2022003CF"
            "2006CFA98E8502A9118503A2022003CF2006CFA9908502A9118503A2022003CF2006CFA9928502A9118503A2022003CF"
            "2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9948502A9118503A2022003CF2006CF205F1160A99985"
            "02A9118503A2022003CF2006CF205F1160A99E8502A9118503A2022003CF2006CF600000000041004200430044004500"
            "46004700480049004A004B004C004D004E004F0050004D494431004D49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "many_string_do_until_shared_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-do-until-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'DO\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 77\n"
                "b du0u1e0e1e2e3e4e5e6e7e8e9p0p1qtor\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 77\n"
            "b du0u1e0e1e2e3e4e5e6e7e8e9p0p1qtor\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 140, 0, 0, 0, 1, 106, 0, 69, 79, 0,
                69, 89, 0, 97, 106, 0, 73, 16, 255, 97, 108, 0, 73, 16,
                255, 97, 110, 0, 73, 16, 255, 97, 112, 0, 73, 16, 255, 97,
                114, 0, 73, 16, 255, 97, 116, 0, 73, 16, 255, 97, 118, 0,
                73, 16, 255, 97, 120, 0, 73, 16, 255, 97, 122, 0, 73, 16,
                255, 97, 124, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24,
                0, 0, 73, 32, 255, 97, 126, 0, 73, 16, 255, 69, 99, 0, 72,
                97, 131, 0, 73, 16, 255, 69, 99, 0, 72, 97, 136, 0, 73, 16,
                255, 72, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0,
                72, 0, 73, 0, 74, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0,
                69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "001020D71020EB10A9148502A9118503A2022003CF2006CFA9168502A9118503A2022003CF2006CFA9188502A9118503"
            "A2022003CF2006CFA91A8502A9118503A2022003CF2006CFA91C8502A9118503A2022003CF2006CFA91E8502A9118503"
            "A2022003CF2006CFA9208502A9118503A2022003CF2006CFA9228502A9118503A2022003CF2006CFA9248502A9118503"
            "A2022003CF2006CFA9268502A9118503A2022003CF2006CFA901A2008D10118E1111A901A200EC1111D005CD1011F003"
            "4C00108DD1038ED203A9A58DD003A90085028503A2024C0FCFA9288502A9118503A2022003CF2006CF20FF1060A92D85"
            "02A9118503A2022003CF2006CF20FF1060A9328502A9118503A2022003CF2006CF600000000041004200430044004500"
            "46004700480049004A004D494431004D49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\n",
    },
    "many_string_nested_branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-nested-branch-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 1 THEN\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'ELSE\r'
                'PrintE("BAD1")\r'
                'FI\r'
                'ELSE\r'
                'PrintE("BAD2")\r'
                'FI\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 97\n"
                "b p0p1qhp2p3ap4ghu0u1e0e1e2e3e4e5e6e7we8vwe9vr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s BAD1\n"
                "s BAD2\n"
                "i 1\n"
                "i 1\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 97\n"
            "b p0p1qhp2p3ap4ghu0u1e0e1e2e3e4e5e6e7we8vwe9vr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s BAD1\n"
            "s BAD2\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 166, 0, 0, 0, 1, 126, 0, 17, 1, 0, 17,
                1, 0, 22, 24, 90, 0, 17, 2, 0, 17, 12, 0, 20, 17, 10, 0,
                29, 24, 81, 0, 69, 99, 0, 69, 109, 0, 97, 126, 0, 73, 16,
                255, 97, 128, 0, 73, 16, 255, 97, 130, 0, 73, 16, 255, 97,
                132, 0, 73, 16, 255, 97, 134, 0, 73, 16, 255, 97, 136, 0,
                73, 16, 255, 97, 138, 0, 73, 16, 255, 97, 140, 0, 73, 16,
                255, 25, 87, 0, 97, 142, 0, 73, 16, 255, 25, 96, 0, 97,
                147, 0, 73, 16, 255, 73, 32, 255, 97, 152, 0, 73, 16, 255,
                69, 119, 0, 72, 97, 157, 0, 73, 16, 255, 69, 119, 0, 72,
                97, 162, 0, 73, 16, 255, 72, 65, 0, 66, 0, 67, 0, 68, 0,
                69, 0, 70, 0, 71, 0, 72, 0, 66, 65, 68, 49, 0, 66, 65, 68,
                50, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010A901A2008D5A118E5B11A901A200EC5B11D005CD5A11F0034CFB10A902A2008D5A118E5B11A90CA200186D5A118D"
            "5A118A6D5B11AAAD5A118D5A118E5B11A90AA200EC5B119007D00DCD5A119002F004A901D002A900A200C900D0034CE8"
            "10202111203511A95E8502A9118503A2022003CF2006CFA9608502A9118503A2022003CF2006CFA9628502A9118503A2"
            "022003CF2006CFA9648502A9118503A2022003CF2006CFA9668502A9118503A2022003CF2006CFA9688502A9118503A2"
            "022003CF2006CFA96A8502A9118503A2022003CF2006CFA96C8502A9118503A2022003CF2006CF4CF810A96E8502A911"
            "8503A2022003CF2006CF4C0B11A9738502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A202"
            "4C0FCFA9788502A9118503A2022003CF2006CF20491160A97D8502A9118503A2022003CF2006CF20491160A9828502A9"
            "118503A2022003CF2006CF600000000041004200430044004500460047004800424144310042414432004D494431004D"
            "49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\n",
    },
    "many_int_nested_loops_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-int-nested-loops-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'WHILE 1 = 0 DO\r'
            'OD\r'
            'IF 1 = 0 THEN\r'
            'PrintIE(0)\r'
            'PrintIE(1)\r'
            'PrintIE(2)\r'
            'PrintIE(3)\r'
            'PrintIE(4)\r'
            'PrintIE(5)\r'
            'PrintIE(6)\r'
            'PrintIE(7)\r'
            'ELSE\r'
            'PrintIE(8)\r'
            'PrintIE(9)\r'
            'PrintIE(10)\r'
            'PrintIE(11)\r'
            'PrintIE(12)\r'
            'PrintIE(13)\r'
            'PrintIE(14)\r'
            'PrintIE(15)\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 133\n"
            "b ddp0p1qfxp2p3qhp4zp5zp6zp7zp8zp9zpAzpBzwpCzpDzpEzpFzpGzpHzpIzpJzvpKpLqtor\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 0\n"
            "i 1\n"
            "i 2\n"
            "i 3\n"
            "i 4\n"
            "i 5\n"
            "i 6\n"
            "i 7\n"
            "i 8\n"
            "i 9\n"
            "i 10\n"
            "i 11\n"
            "i 12\n"
            "i 13\n"
            "i 14\n"
            "i 15\n"
            "i 1\n"
            "i 1\n"
            "k 6\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 135, 0, 0, 0, 1, 135, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 13, 0, 25, 0, 0, 17, 1, 0, 17, 0, 0, 22, 24,
                74, 0, 17, 0, 0, 73, 49, 255, 17, 1, 0, 73, 49, 255, 17, 2,
                0, 73, 49, 255, 17, 3, 0, 73, 49, 255, 17, 4, 0, 73, 49,
                255, 17, 5, 0, 73, 49, 255, 17, 6, 0, 73, 49, 255, 17, 7,
                0, 73, 49, 255, 25, 122, 0, 17, 8, 0, 73, 49, 255, 17, 9,
                0, 73, 49, 255, 17, 10, 0, 73, 49, 255, 17, 11, 0, 73, 49,
                255, 17, 12, 0, 73, 49, 255, 17, 13, 0, 73, 49, 255, 17,
                14, 0, 73, 49, 255, 17, 15, 0, 73, 49, 255, 17, 1, 0, 17,
                1, 0, 22, 24, 0, 0, 73, 32, 255,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008dbd218ebe21a900a200ecbe21d005cdbd21f0034c1e104c0010"
            "a901a2008dbd218ebe21a900a200ecbe21d005cdbd21f0034ce418a900a2008d"
            "bd218ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c91090"
            "1438adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a1869"
            "308dbf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd"
            "21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21"
            "a2022003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648d"
            "bd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003"
            "cfa001a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe"
            "21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001ad"
            "bd211869308dbf21a2022003cf2006cfa901a2008dbd218ebe21a9bf8502a921"
            "8503a000a200adbe21c927901dd007adbd21c910901438adbd21e9108dbd21ad"
            "be21e9278dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001"
            "a200adbe21c903901dd007adbd21c9e8901438adbd21e9e88dbd21adbe21e903"
            "8dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe"
            "21c900901dd007adbd21c964901438adbd21e9648dbd21adbe21e9008dbe21e8"
            "d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c90090"
            "1dd007adbd21c90a901438adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000"
            "d004c000f00e8a1869308dbf21a2022003cfa001adbd211869308dbf21a20220"
            "03cf2006cfa902a2008dbd218ebe21a9bf8502a9218503a000a200adbe21c927"
            "901dd007adbd21c910901438adbd21e9108dbd21adbe21e9278dbe21e8d0dce0"
            "00d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c903901dd007"
            "adbd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c0"
            "00f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c9"
            "64901438adbd21e9648dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a"
            "1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c90a901438"
            "adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308d"
            "bf21a2022003cfa001adbd211869308dbf21a2022003cf2006cfa903a2008dbd"
            "218ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c9109014"
            "38adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a186930"
            "8dbf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd21"
            "e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21a2"
            "022003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648dbd"
            "21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cf"
            "a001a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe21"
            "e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001adbd"
            "211869308dbf21a2022003cf2006cfa904a2008dbd218ebe21a9bf8502a92185"
            "03a000a200adbe21c927901dd007adbd21c910901438adbd21e9108dbd21adbe"
            "21e9278dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a2"
            "00adbe21c903901dd007adbd21c9e8901438adbd21e9e88dbd21adbe21e9038d"
            "be21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21"
            "c900901dd007adbd21c964901438adbd21e9648dbd21adbe21e9008dbe21e8d0"
            "dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c900901d"
            "d007adbd21c90a901438adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d0"
            "04c000f00e8a1869308dbf21a2022003cfa001adbd211869308dbf21a2022003"
            "cf2006cfa905a2008dbd218ebe21a9bf8502a9218503a000a200adbe21c92790"
            "1dd007adbd21c910901438adbd21e9108dbd21adbe21e9278dbe21e8d0dce000"
            "d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c903901dd007ad"
            "bd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000"
            "f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c964"
            "901438adbd21e9648dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a18"
            "69308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c90a901438ad"
            "bd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf"
            "21a2022003cfa001adbd211869308dbf21a2022003cf2006cfa906a2008dbd21"
            "8ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c910901438"
            "adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a1869308d"
            "bf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd21e9"
            "e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21a202"
            "2003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648dbd21"
            "adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa0"
            "01a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe21e9"
            "008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001adbd21"
            "1869308dbf21a2022003cf2006cfa907a2008dbd218ebe21a9bf8502a9218503"
            "a000a200adbe21c927901dd007adbd21c910901438adbd21e9108dbd21adbe21"
            "e9278dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200"
            "adbe21c903901dd007adbd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe"
            "21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c9"
            "00901dd007adbd21c964901438adbd21e9648dbd21adbe21e9008dbe21e8d0dc"
            "e000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd0"
            "07adbd21c90a901438adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004"
            "c000f00e8a1869308dbf21a2022003cfa001adbd211869308dbf21a2022003cf"
            "2006cf4c8c21a908a2008dbd218ebe21a9bf8502a9218503a000a200adbe21c9"
            "27901dd007adbd21c910901438adbd21e9108dbd21adbe21e9278dbe21e8d0dc"
            "e000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c903901dd0"
            "07adbd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe21e8d0dce000d004"
            "c000f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21"
            "c964901438adbd21e9648dbd21adbe21e9008dbe21e8d0dce000d004c000f00e"
            "8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c90a9014"
            "38adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a186930"
            "8dbf21a2022003cfa001adbd211869308dbf21a2022003cf2006cfa909a2008d"
            "bd218ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c91090"
            "1438adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a1869"
            "308dbf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd"
            "21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21"
            "a2022003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648d"
            "bd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003"
            "cfa001a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe"
            "21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001ad"
            "bd211869308dbf21a2022003cf2006cfa90aa2008dbd218ebe21a9bf8502a921"
            "8503a000a200adbe21c927901dd007adbd21c910901438adbd21e9108dbd21ad"
            "be21e9278dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001"
            "a200adbe21c903901dd007adbd21c9e8901438adbd21e9e88dbd21adbe21e903"
            "8dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe"
            "21c900901dd007adbd21c964901438adbd21e9648dbd21adbe21e9008dbe21e8"
            "d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c90090"
            "1dd007adbd21c90a901438adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000"
            "d004c000f00e8a1869308dbf21a2022003cfa001adbd211869308dbf21a20220"
            "03cf2006cfa90ba2008dbd218ebe21a9bf8502a9218503a000a200adbe21c927"
            "901dd007adbd21c910901438adbd21e9108dbd21adbe21e9278dbe21e8d0dce0"
            "00d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c903901dd007"
            "adbd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c0"
            "00f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c9"
            "64901438adbd21e9648dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a"
            "1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c90a901438"
            "adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308d"
            "bf21a2022003cfa001adbd211869308dbf21a2022003cf2006cfa90ca2008dbd"
            "218ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c9109014"
            "38adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a186930"
            "8dbf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd21"
            "e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21a2"
            "022003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648dbd"
            "21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cf"
            "a001a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe21"
            "e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001adbd"
            "211869308dbf21a2022003cf2006cfa90da2008dbd218ebe21a9bf8502a92185"
            "03a000a200adbe21c927901dd007adbd21c910901438adbd21e9108dbd21adbe"
            "21e9278dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a2"
            "00adbe21c903901dd007adbd21c9e8901438adbd21e9e88dbd21adbe21e9038d"
            "be21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21"
            "c900901dd007adbd21c964901438adbd21e9648dbd21adbe21e9008dbe21e8d0"
            "dce000d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c900901d"
            "d007adbd21c90a901438adbd21e90a8dbd21adbe21e9008dbe21e8d0dce000d0"
            "04c000f00e8a1869308dbf21a2022003cfa001adbd211869308dbf21a2022003"
            "cf2006cfa90ea2008dbd218ebe21a9bf8502a9218503a000a200adbe21c92790"
            "1dd007adbd21c910901438adbd21e9108dbd21adbe21e9278dbe21e8d0dce000"
            "d004c000f00e8a1869308dbf21a2022003cfa001a200adbe21c903901dd007ad"
            "bd21c9e8901438adbd21e9e88dbd21adbe21e9038dbe21e8d0dce000d004c000"
            "f00e8a1869308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c964"
            "901438adbd21e9648dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a18"
            "69308dbf21a2022003cfa001a200adbe21c900901dd007adbd21c90a901438ad"
            "bd21e90a8dbd21adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf"
            "21a2022003cfa001adbd211869308dbf21a2022003cf2006cfa90fa2008dbd21"
            "8ebe21a9bf8502a9218503a000a200adbe21c927901dd007adbd21c910901438"
            "adbd21e9108dbd21adbe21e9278dbe21e8d0dce000d004c000f00e8a1869308d"
            "bf21a2022003cfa001a200adbe21c903901dd007adbd21c9e8901438adbd21e9"
            "e88dbd21adbe21e9038dbe21e8d0dce000d004c000f00e8a1869308dbf21a202"
            "2003cfa001a200adbe21c900901dd007adbd21c964901438adbd21e9648dbd21"
            "adbe21e9008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa0"
            "01a200adbe21c900901dd007adbd21c90a901438adbd21e90a8dbd21adbe21e9"
            "008dbe21e8d0dce000d004c000f00e8a1869308dbf21a2022003cfa001adbd21"
            "1869308dbf21a2022003cf2006cfa901a2008dbd218ebe21a901a200ecbe21d0"
            "05cdbd21f0034c00108dd1038ed203a9a58dd003a90085028503a2024c0fcf00"
            "000000"
        ),
        "expected_console": "8\n9\n10\n11\n12\n13\n14\n15\n",
    },
    "many_string_nested_loops_if_else": {
        "out_fs_name": "harness-actc-alink-avmrunc-many-string-nested-loops-if-else",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'WHILE 1 = 0 DO\r'
            'OD\r'
            'IF 1 = 0 THEN\r'
            'PrintE("A")\r'
            'PrintE("B")\r'
            'PrintE("C")\r'
            'PrintE("D")\r'
            'PrintE("E")\r'
            'PrintE("F")\r'
            'PrintE("G")\r'
            'PrintE("H")\r'
            'ELSE\r'
            'PrintE("I")\r'
            'PrintE("J")\r'
            'PrintE("K")\r'
            'PrintE("L")\r'
            'PrintE("M")\r'
            'PrintE("N")\r'
            'PrintE("O")\r'
            'PrintE("P")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 133\n"
            "b ddp0p1qfxp2p3qhe0e1e2e3e4e5e6e7we8e9eAeBeCeDeEeFvp4p5qtor\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 167, 0, 0, 0, 1, 135, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 13, 0, 25, 0, 0, 17, 1, 0, 17, 0, 0, 22, 24,
                74, 0, 97, 135, 0, 73, 16, 255, 97, 137, 0, 73, 16, 255,
                97, 139, 0, 73, 16, 255, 97, 141, 0, 73, 16, 255, 97, 143,
                0, 73, 16, 255, 97, 145, 0, 73, 16, 255, 97, 147, 0, 73,
                16, 255, 97, 149, 0, 73, 16, 255, 25, 122, 0, 97, 151, 0,
                73, 16, 255, 97, 153, 0, 73, 16, 255, 97, 155, 0, 73, 16,
                255, 97, 157, 0, 73, 16, 255, 97, 159, 0, 73, 16, 255, 97,
                161, 0, 73, 16, 255, 97, 163, 0, 73, 16, 255, 97, 165, 0,
                73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 73, 32, 255,
                65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73,
                0, 74, 0, 75, 0, 76, 0, 77, 0, 78, 0, 79, 0, 80, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes.fromhex(
            "0010a901a2008d6d118e6e11a900a200ec6e11d005cd6d11f0034c1e104c0010"
            "a901a2008d6d118e6e11a900a200ec6e11d005cd6d11f0034cbc10a96f8502a9"
            "118503a2022003cf2006cfa9718502a9118503a2022003cf2006cfa9738502a9"
            "118503a2022003cf2006cfa9758502a9118503a2022003cf2006cfa9778502a9"
            "118503a2022003cf2006cfa9798502a9118503a2022003cf2006cfa97b8502a9"
            "118503a2022003cf2006cfa97d8502a9118503a2022003cf2006cf4c3c11a97f"
            "8502a9118503a2022003cf2006cfa9818502a9118503a2022003cf2006cfa983"
            "8502a9118503a2022003cf2006cfa9858502a9118503a2022003cf2006cfa987"
            "8502a9118503a2022003cf2006cfa9898502a9118503a2022003cf2006cfa98b"
            "8502a9118503a2022003cf2006cfa98d8502a9118503a2022003cf2006cfa901"
            "a2008d6d118e6e11a901a200ec6e11d005cd6d11f0034c00108dd1038ed203a9"
            "a58dd003a90085028503a2024c0fcf0000410042004300440045004600470048"
            "0049004a004b004c004d004e004f005000"
        ),
        "expected_console": "I\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-branch-calls",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC BYE()\r'
            'PrintE("BYE")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'BYE()\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x main 14 26\n"
            "b e0r\n"
            "b e1r\n"
            "b p0p1qhc0wc1ve2r\n"
            "s HELLO\n"
            "s BYE\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 57, 0, 14, 0, 1, 42, 0, 97, 42, 0, 73,
                16, 255, 72, 97, 48, 0, 73, 16, 255, 72, 17, 1, 0, 17, 1,
                0, 22, 24, 30, 0, 69, 0, 0, 25, 33, 0, 69, 7, 0, 97, 52,
                0, 73, 16, 255, 73, 32, 255, 72, 69, 76, 76, 79, 0, 66, 89,
                69, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 108, 16, 142, 109, 16, 169, 1, 162, 0,
                236, 109, 16, 208, 5, 205, 108, 16, 240, 3, 76, 33, 16, 32, 74, 16,
                76, 36, 16, 32, 91, 16, 169, 122, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208,
                3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 112, 133, 2,
                169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 169, 118, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0,
                0, 0, 72, 69, 76, 76, 79, 0, 66, 89, 69, 0, 68, 79, 78, 69,
                0,
            ]
        ),
        "expected_console": "HELLO\nDONE\n",
    },
    "comparison_branch_calls": {
        "out_fs_name": "harness-actc-alink-avmrunc-comparison-branch-calls",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC BYE()\r'
            'PrintE("BYE")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'BYE()\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x main 14 30\n"
            "b e0r\n"
            "b e1r\n"
            "b p0p1ap2ghc0wc1ve2r\n"
            "s HELLO\n"
            "s BYE\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 61, 0, 14, 0, 1, 46, 0, 97, 46, 0, 73,
                16, 255, 72, 97, 52, 0, 73, 16, 255, 72, 17, 2, 0, 17, 12,
                0, 20, 17, 10, 0, 29, 24, 34, 0, 69, 0, 0, 25, 37, 0, 69,
                7, 0, 97, 56, 0, 73, 16, 255, 73, 32, 255, 72, 69, 76, 76,
                79, 0, 66, 89, 69, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 2, 162, 0, 141, 149, 16, 142, 150, 16, 169, 12, 162, 0,
                24, 109, 149, 16, 141, 149, 16, 138, 109, 150, 16, 170, 173, 149, 16, 141,
                149, 16, 142, 150, 16, 169, 10, 162, 0, 236, 150, 16, 144, 7, 208, 13,
                205, 149, 16, 144, 2, 240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201,
                0, 208, 3, 76, 74, 16, 32, 115, 16, 76, 77, 16, 32, 132, 16, 169,
                163, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 141,
                209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3,
                162, 2, 76, 15, 207, 169, 153, 133, 2, 169, 16, 133, 3, 162, 2, 32,
                3, 207, 32, 6, 207, 96, 169, 159, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 72, 69, 76, 76, 79,
                0, 66, 89, 69, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "HELLO\nDONE\n",
    },
    "nested_branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-branch-calls",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC BYE()\r'
            'PrintE("BYE")\r'
            'RETURN\r'
            'PROC OUTER()\r'
            'PrintE("OUTER")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'BYE()\r'
            'FI\r'
            'ELSE\r'
            'OUTER()\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x outer 14 7\n"
            "x main 21 46\n"
            "b e0r\n"
            "b e1r\n"
            "b e2r\n"
            "b p0p1qhp2p3ap4ghc0wc1vwc2ve3r\n"
            "s HELLO\n"
            "s BYE\n"
            "s OUTER\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 90, 0, 21, 0, 1, 69, 0, 97, 69, 0, 73,
                16, 255, 72, 97, 75, 0, 73, 16, 255, 72, 97, 79, 0, 73, 16,
                255, 72, 17, 1, 0, 17, 1, 0, 22, 24, 57, 0, 17, 2, 0, 17,
                12, 0, 20, 17, 10, 0, 29, 24, 51, 0, 69, 0, 0, 25, 54, 0,
                69, 7, 0, 25, 60, 0, 69, 14, 0, 97, 85, 0, 73, 16, 255, 73,
                32, 255, 72, 69, 76, 76, 79, 0, 66, 89, 69, 0, 79, 85, 84,
                69, 82, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 199, 16, 142, 200, 16, 169, 1, 162, 0,
                236, 200, 16, 208, 5, 205, 199, 16, 240, 3, 76, 107, 16, 169, 2, 162,
                0, 141, 199, 16, 142, 200, 16, 169, 12, 162, 0, 24, 109, 199, 16, 141,
                199, 16, 138, 109, 200, 16, 170, 173, 199, 16, 141, 199, 16, 142, 200, 16,
                169, 10, 162, 0, 236, 200, 16, 144, 7, 208, 13, 205, 199, 16, 144, 2,
                240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 101,
                16, 32, 148, 16, 76, 104, 16, 32, 165, 16, 76, 110, 16, 32, 182, 16,
                169, 219, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 169, 203, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 96, 169, 209, 133, 2, 169, 16, 133, 3, 162,
                2, 32, 3, 207, 32, 6, 207, 96, 169, 213, 133, 2, 169, 16, 133, 3,
                162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 72, 69, 76,
                76, 79, 0, 66, 89, 69, 0, 79, 85, 84, 69, 82, 0, 68, 79, 78,
                69, 0,
            ]
        ),
        "expected_console": "HELLO\nDONE\n",
    },
    "branch_external": {
        "out_fs_name": "harness-actc-alink-prg-branch-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 33\n"
            "b p0p1ap2ghu0we0ve1r\n"
            "u w\n"
            "s BAD\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "A902A2008DA3118EA411A90CA200186DA3118DA3118A6DA411AAADA3118DA3118EA411A90AA200"
            "ECA4119007D00DCDA3119002F004A901D002A900A200C900D0034C4A102080104C5A10A9A98502"
            "A9118503A2022003CF2006CFA9AD8502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003"
            "A90085028503A2024C0FCFA9B28502A9118503A2022003CFA907A2008DA3118EA411A9A78502A9"
            "118503A000A200ADA411C927901DD007ADA311C910901438ADA311E9108DA311ADA411E9278DA4"
            "11E8D0DCE000D004C000F00E8A1869308DA711A2022003CFA001A200ADA411C903901DD007ADA3"
            "11C9E8901438ADA311E9E88DA311ADA411E9038DA411E8D0DCE000D004C000F00E8A1869308DA7"
            "11A2022003CFA001A200ADA411C900901DD007ADA311C964901438ADA311E9648DA311ADA411E9"
            "008DA411E8D0DCE000D004C000F00E8A1869308DA711A2022003CFA001A200ADA411C900901DD0"
            "07ADA311C90A901438ADA311E90A8DA311ADA411E9008DA411E8D0DCE000D004C000F00E8A1869"
            "308DA711A2022003CFA001ADA3111869308DA711A2022003CF2006CF6000000000000042414400"
            "444F4E4500544F4F4C00"
        ),
        "expected_console": "TOOL7\nDONE\n",
    },
    "nested_branch_external": {
        "out_fs_name": "harness-actc-alink-prg-nested-branch-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC OUTER()\r'
            'PrintE("OUTER")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'ELSE\r'
            'OUTER()\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x outer 0 7\n"
            "x main 7 49\n"
            "b e0r\n"
            "b p0p1qhp2p3ap4ghu0we1vwc0ve2r\n"
            "u w\n"
            "s OUTER\n"
            "s BAD1\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "A901A2008DD5118ED611A901A200ECD611D005CDD511F0034C7810A902A2008DD5118ED611A90C"
            "A200186DD5118DD5118A6DD611AAADD5118DD5118ED611A90AA200ECD6119007D00DCDD5119002"
            "F004A901D002A900A200C900D0034C651020B2104C7510A9E18502A9118503A2022003CF2006CF"
            "4C7B1020A110A9E68502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503"
            "A2024C0FCFA9DB8502A9118503A2022003CF2006CF60A9EB8502A9118503A2022003CFA907A200"
            "8DD5118ED611A9D98502A9118503A000A200ADD611C927901DD007ADD511C910901438ADD511E9"
            "108DD511ADD611E9278DD611E8D0DCE000D004C000F00E8A1869308DD911A2022003CFA001A200"
            "ADD611C903901DD007ADD511C9E8901438ADD511E9E88DD511ADD611E9038DD611E8D0DCE000D0"
            "04C000F00E8A1869308DD911A2022003CFA001A200ADD611C900901DD007ADD511C964901438AD"
            "D511E9648DD511ADD611E9008DD611E8D0DCE000D004C000F00E8A1869308DD911A2022003CFA0"
            "01A200ADD611C900901DD007ADD511C90A901438ADD511E90A8DD511ADD611E9008DD611E8D0DC"
            "E000D004C000F00E8A1869308DD911A2022003CFA001ADD5111869308DD911A2022003CF2006CF"
            "600000000000004F55544552004241443100444F4E4500544F4F4C00"
        ),
        "expected_console": "TOOL7\nDONE\n",
    },
    "transitive_external": {
        "out_fs_name": "harness-actc-alink-prg-transitive-external",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'W()\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 16\n"
                "b e0u0e1r\n"
                "u w\n"
                "s START\n"
                "s DONE\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A9628502A9108503A2022003CF2006CF203910A9688502A9108503A2022003CF2006CF8DD1038ED203A9A58DD003"
            "A90085028503A2024C0FCFA96D8502A9108503A2022003CF2006CF204D1060A9718502A9108503A2022003CF2006CF60"
            "00000000535441525400444F4E45004D494400454E4400"

        ),
        "expected_console": "START\nMID\nEND\nDONE\n",
    },
    "transitive_branch_external": {
        "out_fs_name": "harness-actc-alink-prg-transitive-branch-external",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'PrintE("START")\r'
                'W()\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 39\n"
                "b p0p1ap2ghe0u0we1ve2r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "s DONE\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010"
            "A902A2008DB5108EB610A90CA200186DB5108DB5108A6DB610AAADB5108DB5108EB610A90AA200"
            "ECB6109007D00DCDB5109002F004A901D002A900A200C900D0034C5A10A9B98502A9108503A202"
            "2003CF2006CF2090104C6A10A9BF8502A9108503A2022003CF2006CFA9C38502A9108503A20220"
            "03CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9C88502A9108503A2022003"
            "CF2006CF20A41060A9CC8502A9108503A2022003CF2006CF600000000053544152540042414400"
            "444F4E45004D494400454E4400"
        ),
        "expected_console": "START\nMID\nEND\nDONE\n",
    },
    "sibling_externals": {
        "out_fs_name": "harness-actc-alink-prg-sibling-externals",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'W()\r'
                'Z()\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("MID2")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b e0u0u1e1r\n"
                "u w\n"
                "u z\n"
                "s START\n"
                "s DONE\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s MID2\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A9628502A9108503A2022003CF2006CF203C10204D10A9688502A9108503A2022003CF2006CF8DD1038ED203A9A5"
            "8DD003A90085028503A2024C0FCFA96D8502A9108503A2022003CF2006CF60A9728502A9108503A2022003CF2006CF60"
            "00000000535441525400444F4E45004D494431004D49443200"

        ),
        "expected_console": "START\nMID1\nMID2\nDONE\n",
    },
    "child_sibling_externals": {
        "out_fs_name": "harness-actc-alink-prg-child-sibling-externals",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'W()\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'Q()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END1")\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("END2")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Z", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 16\n"
                "b e0u0e1r\n"
                "u w\n"
                "s START\n"
                "s DONE\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 13\n"
                "b e0u0u1r\n"
                "u z\n"
                "u q\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END1\n"
                "k 2\n"
                "n z\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 7\n"
                "b e0r\n"
                "s END2\n"
                "k 2\n"
                "n q\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A9768502A9108503A2022003CF2006CF203910A97C8502A9108503A2022003CF2006CF8DD1038ED203A9A58DD003"
            "A90085028503A2024C0FCFA9818502A9108503A2022003CF2006CF20501020611060A9858502A9108503A2022003CF20"
            "06CF60A98A8502A9108503A2022003CF2006CF6000000000535441525400444F4E45004D494400454E443100454E4432"
            "00"

        ),
        "expected_console": "START\nMID\nEND1\nEND2\nDONE\n",
    },
    "branch_transitive_local": {
        "out_fs_name": "harness-actc-alink-prg-branch-transitive-local",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC LOCAL()\r'
                'PrintE("LOCAL")\r'
                'RETURN\r'
                'PROC MAIN()\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'LOCAL()\r'
                'W()\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x local 0 7\n"
                "x main 7 36\n"
                "b e0r\n"
                "b p0p1ap2ghc0u0we1ve2r\n"
                "u w\n"
                "s LOCAL\n"
                "s BAD\n"
                "s DONE\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A902A2008DBF108EC010A90CA200186DBF108DBF108A6DC010AAADBF108DBF108EC010A90AA200ECC0109007D00D"
            "CDBF109002F004A901D002A900A200C900D0034C53102089108DBF108EC010209A104C6310A9C98502A9108503A20220"
            "03CF2006CFA9CD8502A9108503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9C38502A9"
            "108503A2022003CF2006CF60A9D28502A9108503A2022003CF2006CF20AE1060A9D68502A9108503A2022003CF2006CF"
            "60000000004C4F43414C0042414400444F4E45004D494400454E4400"

        ),
        "expected_console": "LOCAL\nMID\nEND\nDONE\n",
    },
    "repeated_root_externals": {
        "out_fs_name": "harness-actc-alink-prg-repeated-root-externals",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'W()\r'
                'Z()\r'
                'W()\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("MID2")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 22\n"
                "b e0u0u1u0e1r\n"
                "u w\n"
                "u z\n"
                "s START\n"
                "s DONE\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s MID2\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A9658502A9108503A2022003CF2006CF203F10205010203F10A96B8502A9108503A2022003CF2006CF8DD1038ED2"
            "03A9A58DD003A90085028503A2024C0FCFA9708502A9108503A2022003CF2006CF60A9758502A9108503A2022003CF20"
            "06CF6000000000535441525400444F4E45004D494431004D49443200"

        ),
        "expected_console": "START\nMID1\nMID2\nMID1\nDONE\n",
    },
    "shared_transitive_external": {
        "out_fs_name": "harness-actc-alink-prg-shared-transitive-external",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'W()\r'
                'Q()\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Q", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 19\n"
                "b e0u0u1e1r\n"
                "u w\n"
                "u q\n"
                "s START\n"
                "s DONE\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A9798502A9108503A2022003CF2006CF203C10205010A97F8502A9108503A2022003CF2006CF8DD1038ED203A9A5"
            "8DD003A90085028503A2024C0FCFA9848502A9108503A2022003CF2006CF20641060A9898502A9108503A2022003CF20"
            "06CF20641060A98E8502A9108503A2022003CF2006CF6000000000535441525400444F4E45004D494431004D49443200"
            "454E4400"

        ),
        "expected_console": "START\nMID1\nEND\nMID2\nEND\nDONE\n",
    },
    "branch_sibling_externals": {
        "out_fs_name": "harness-actc-alink-prg-branch-sibling-externals",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'W()\r'
                'Z()\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("MID2")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 36\n"
                "b p0p1ap2ghu0u1we0ve1r\n"
                "u w\n"
                "u z\n"
                "s BAD\n"
                "s DONE\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s MID2\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A902A2008DA5108EA610A90CA200186DA5108DA5108A6DA610AAADA5108DA5108EA610A90AA200ECA6109007D00D"
            "CDA5109002F004A901D002A900A200C900D0034C4D102083102094104C5D10A9A98502A9108503A2022003CF2006CFA9"
            "AD8502A9108503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9B28502A9108503A20220"
            "03CF2006CF60A9B78502A9108503A2022003CF2006CF600000000042414400444F4E45004D494431004D49443200"

        ),
        "expected_console": "MID1\nMID2\nDONE\n",
    },
    "branch_shared_transitive": {
        "out_fs_name": "harness-actc-alink-prg-branch-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'W()\r'
                'Q()\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "Q", "Z", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 36\n"
                "b p0p1ap2ghu0u1we0ve1r\n"
                "u w\n"
                "u q\n"
                "s BAD\n"
                "s DONE\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010A902A2008DBC108EBD10A90CA200186DBC108DBC108A6DBD10AAADBC108DBC108EBD10A90AA200ECBD109007D00D"
            "CDBC109002F004A901D002A900A200C900D0034C4D102083102097104C5D10A9C08502A9108503A2022003CF2006CFA9"
            "C48502A9108503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9C98502A9108503A20220"
            "03CF2006CF20AB1060A9CE8502A9108503A2022003CF2006CF20AB1060A9D38502A9108503A2022003CF2006CF600000"
            "000042414400444F4E45004D494431004D49443200454E4400"

        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nDONE\n",
    },
    "procedures": {
        "out_fs_name": "harness-actc-alink-direct-prg-procedures",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("ONE")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'HELLO()\r'
            'PrintE("TWO")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 10\n"
            "b e0r\n"
            "b c0e1r\n"
            "s ONE\n"
            "s TWO\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 27, 0, 7, 0, 1, 19, 0, 97, 19, 0, 73,
                16, 255, 72, 69, 0, 0, 97, 23, 0, 73, 16, 255, 73, 32, 255,
                79, 78, 69, 0, 84, 87, 79, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 32, 41, 16, 169, 66, 133, 2, 169, 16, 133, 3, 162, 2, 32,
                3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3,
                169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 62, 133, 2, 169,
                16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0,
                79, 78, 69, 0, 84, 87, 79, 0,
            ]
        ),
        "expected_console": "ONE\nTWO\n",
    },
    "if_blocks": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-blocks",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 0 THEN\r'
            'PrintE("NO")\r'
            'FI\r'
            'IF 1 = 1 THEN\r'
            'PrintE("YES")\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 39\n"
            "b p0p1qhe0vp2p3qhe1ve2r\n"
            "s NO\n"
            "s YES\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d7c108e7d10a900a200ec7d10d005cd7c10f0034c2b10"
            "a97e8502a9108503a2022003cf2006cf"
            "a901a2008d7c108e7d10a901a200ec7d10d005cd7c10f0034c5610"
            "a9818502a9108503a2022003cf2006cf"
            "a9858502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004e4f0059455300444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 53, 0, 0, 0, 1, 41, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 16, 0, 97, 41, 0, 73, 16, 255, 17, 1, 0, 17,
                1, 0, 22, 24, 32, 0, 97, 44, 0, 73, 16, 255, 97, 48, 0, 73,
                16, 255, 73, 32, 255, 78, 79, 0, 89, 69, 83, 0, 68, 79, 78,
                69, 0,
            ]
        ),
        "expected_console": "YES\nDONE\n",
    },
    "else_blocks": {
        "out_fs_name": "harness-actc-alink-direct-prg-else-blocks",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 0 THEN\r'
            'PrintE("BAD")\r'
            'ELSE\r'
            'PrintE("GOOD")\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 32\n"
            "b p0p1qhe0we1ve2r\n"
            "s BAD\n"
            "s GOOD\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d64108e6510a900a200ec6510d005cd6410f0034c2e10"
            "a9668502a9108503a2022003cf2006cf"
            "4c3e10"
            "a96a8502a9108503a2022003cf2006cf"
            "a96f8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000042414400474f4f4400444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 48, 0, 0, 0, 1, 34, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 19, 0, 97, 34, 0, 73, 16, 255, 25, 25, 0, 97,
                38, 0, 73, 16, 255, 97, 43, 0, 73, 16, 255, 73, 32, 255, 66,
                65, 68, 0, 71, 79, 79, 68, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "GOOD\nDONE\n",
    },
    "nested_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'IF 1 = 0 THEN\r'
            'PrintE("BAD1")\r'
            'ELSE\r'
            'PrintE("GOOD1")\r'
            'FI\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 51\n"
            "b p0p1qhp2p3qhe0we1vwe2ve3r\n"
            "s BAD1\n"
            "s GOOD1\n"
            "s BAD2\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d92108e9310a901a200ec9310d005cd9210f0034c5c10"
            "a901a2008d92108e9310a900a200ec9310d005cd9210f0034c4910"
            "a9948502a9108503a2022003cf2006cf"
            "4c5910"
            "a9998502a9108503a2022003cf2006cf"
            "4c6c10"
            "a99f8502a9108503a2022003cf2006cf"
            "a9a48502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004241443100474f4f4431004241443200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 74, 0, 0, 0, 1, 53, 0, 17, 1, 0, 17,
                1, 0, 22, 24, 38, 0, 17, 1, 0, 17, 0, 0, 22, 24, 29, 0,
                97, 53, 0, 73, 16, 255, 25, 35, 0, 97, 58, 0, 73, 16, 255,
                25, 44, 0, 97, 64, 0, 73, 16, 255, 97, 69, 0, 73, 16, 255,
                73, 32, 255, 66, 65, 68, 49, 0, 71, 79, 79, 68, 49, 0, 66,
                65, 68, 50, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "GOOD1\nDONE\n",
    },
    "do_until": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintE("BODY")\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 23\n"
            "b de0p0p1qtoe1r\n"
            "s BODY\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a9538502a9108503a2022003cf2006cf"
            "a901a2008d51108e5210a901a200ec5210d005cd5110f0034c0010"
            "a9588502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "0000424f445900444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 35, 0, 0, 0, 1, 25, 0, 97, 25, 0, 73,
                16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 97, 30, 0, 73,
                16, 255, 73, 32, 255, 66, 79, 68, 89, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "BODY\nDONE\n",
    },
    "do_until_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'HELLO()\r'
            'W()\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 23\n"
            "b e0r\n"
            "b dc0u0p0p1qtoe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010204710205810a901a2008d7b118e7c11a901a200ec7c11d005cd7b11f0034c0010a9878502a9118503a2022003cf"
            "2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9818502a9118503a2022003cf2006cf60a98c8502a911"
            "8503a2022003cfa907a2008d7b118e7c11a97f8502a9118503a000a200ad7c11c927901dd007ad7b11c910901438ad7b"
            "11e9108d7b11ad7c11e9278d7c11e8d0dce000d004c000f00e8a1869308d7f11a2022003cfa001a200ad7c11c903901d"
            "d007ad7b11c9e8901438ad7b11e9e88d7b11ad7c11e9038d7c11e8d0dce000d004c000f00e8a1869308d7f11a2022003"
            "cfa001a200ad7c11c900901dd007ad7b11c964901438ad7b11e9648d7b11ad7c11e9008d7c11e8d0dce000d004c000f0"
            "0e8a1869308d7f11a2022003cfa001a200ad7c11c900901dd007ad7b11c90a901438ad7b11e90a8d7b11ad7c11e9008d"
            "7c11e8d0dce000d004c000f00e8a1869308d7f11a2022003cfa001ad7b111869308d7f11a2022003cf2006cf60000000"
            "00000048454c4c4f00444f4e4500544f4f4c00"
        ),
        "expected_console": "HELLO\nTOOL7\nDONE\n",
    },
    "do_until_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'PrintE("YES")\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 46\n"
            "b dp0p1ap2ghe0we1vp3p4qtoe2r\n"
            "s YES\n"
            "s BAD\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a902a2008da8108ea910a90ca200186da8108da8108a6da910aaada8108da8108ea910"
            "a90aa200eca9109007d00dcda8109002f004a901d002a900a200c900d0034c5710"
            "a9aa8502a9108503a2022003cf2006cf"
            "4c6710"
            "a9ae8502a9108503a2022003cf2006cf"
            "a901a2008da8108ea910a901a200eca910d005cda810f0034c0010"
            "a9b28502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00005945530042414400444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 61, 0, 0, 0, 1, 48, 0, 17, 2, 0, 17, 12,
                0, 20, 17, 10, 0, 29, 24, 23, 0, 97, 48, 0, 73, 16, 255, 25,
                29, 0, 97, 52, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24,
                0, 0, 97, 56, 0, 73, 16, 255, 73, 32, 255, 89, 69, 83, 0,
                66, 65, 68, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "YES\nDONE\n",
    },
    "do_until_branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-branch-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC BYE()\r'
            'PrintE("BYE")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'BYE()\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x main 14 40\n"
            "b e0r\n"
            "b e1r\n"
            "b dp0p1ap2ghc0wc1vp3p4qtoe2r\n"
            "s HELLO\n"
            "s BYE\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a902a2008db0108eb110a90ca200186db0108db0108a6db110aaadb0108db0108eb110a90aa200ecb1109007d00dcdb0109002f004a901d002a900a200c900d0034c4a10208e104c4d10209f10a901a2008db0108eb110a901a200ecb110d005cdb010f0034c0010a9be8502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9b48502a9108503a2022003cf2006cf60a9ba8502a9108503a2022003cf2006cf600000000048454c4c4f0042594500444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 71, 0, 14, 0, 1, 56, 0, 97, 56, 0, 73,
                16, 255, 72, 97, 62, 0, 73, 16, 255, 72, 17, 2, 0, 17, 12,
                0, 20, 17, 10, 0, 29, 24, 34, 0, 69, 0, 0, 25, 37, 0, 69,
                7, 0, 17, 1, 0, 17, 1, 0, 22, 24, 14, 0, 97, 66, 0, 73, 16,
                255, 73, 32, 255, 72, 69, 76, 76, 79, 0, 66, 89, 69, 0, 68,
                79, 78, 69, 0,
            ]
        ),
        "expected_console": "HELLO\nDONE\n",
    },
    "do_until_branch_external": {
        "out_fs_name": "harness-actc-alink-prg-do-until-branch-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 43\n"
            "b dp0p1ap2ghu0we0vp3p4qtoe1r\n"
            "u w\n"
            "s BAD\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "A902A2008DBE118EBF11A90CA200186DBE118DBE118A6DBF11AAADBE118DBE118EBF11A90AA200"
            "ECBF119007D00DCDBE119002F004A901D002A900A200C900D0034C4A10209B104C5A10A9C48502"
            "A9118503A2022003CF2006CFA901A2008DBE118EBF11A901A200ECBF11D005CDBE11F0034C0010"
            "A9C88502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C0FCFA9"
            "CD8502A9118503A2022003CFA907A2008DBE118EBF11A9C28502A9118503A000A200ADBF11C927"
            "901DD007ADBE11C910901438ADBE11E9108DBE11ADBF11E9278DBF11E8D0DCE000D004C000F00E"
            "8A1869308DC211A2022003CFA001A200ADBF11C903901DD007ADBE11C9E8901438ADBE11E9E88D"
            "BE11ADBF11E9038DBF11E8D0DCE000D004C000F00E8A1869308DC211A2022003CFA001A200ADBF"
            "11C900901DD007ADBE11C964901438ADBE11E9648DBE11ADBF11E9008DBF11E8D0DCE000D004C0"
            "00F00E8A1869308DC211A2022003CFA001A200ADBF11C900901DD007ADBE11C90A901438ADBE11"
            "E90A8DBE11ADBF11E9008DBF11E8D0DCE000D004C000F00E8A1869308DC211A2022003CFA001AD"
            "BE111869308DC211A2022003CF2006CF6000000000000042414400444F4E4500544F4F4C00"
        ),
        "expected_console": "TOOL7\nDONE\n",
    },
    "nested_do_until": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-do-until",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintE("OUTER")\r'
            'DO\r'
            'PrintE("INNER")\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 39\n"
            "b de0de1p0p1qtop2p3qtoe2r\n"
            "s OUTER\n"
            "s INNER\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a97e8502a9108503a2022003cf2006cf"
            "a9848502a9108503a2022003cf2006cf"
            "a901a2008d7c108e7d10a901a200ec7d10d005cd7c10f0034c1010"
            "a901a2008d7c108e7d10a901a200ec7d10d005cd7c10f0034c0010"
            "a98a8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004f5554455200494e4e455200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 58, 0, 0, 0, 1, 41, 0, 97, 41, 0, 73,
                16, 255, 97, 47, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22,
                24, 6, 0, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 97, 53, 0, 73,
                16, 255, 73, 32, 255, 79, 85, 84, 69, 82, 0, 73, 78, 78,
                69, 82, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "OUTER\nINNER\nDONE\n",
    },
    "nested_do_until_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-do-until-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'HELLO()\r'
            'DO\r'
            'W()\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 33\n"
            "b e0r\n"
            "b dc0du0p0p1qtop2p3qtoe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010206210207310a901a2008d96118e9711a901a200ec9711d005cd9611f0034c0310a901a2008d96118e9711a901a2"
            "00ec9711d005cd9611f0034c0010a9a28502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2"
            "024c0fcfa99c8502a9118503a2022003cf2006cf60a9a78502a9118503a2022003cfa907a2008d96118e9711a99a8502"
            "a9118503a000a200ad9711c927901dd007ad9611c910901438ad9611e9108d9611ad9711e9278d9711e8d0dce000d004"
            "c000f00e8a1869308d9a11a2022003cfa001a200ad9711c903901dd007ad9611c9e8901438ad9611e9e88d9611ad9711"
            "e9038d9711e8d0dce000d004c000f00e8a1869308d9a11a2022003cfa001a200ad9711c900901dd007ad9611c9649014"
            "38ad9611e9648d9611ad9711e9008d9711e8d0dce000d004c000f00e8a1869308d9a11a2022003cfa001a200ad9711c9"
            "00901dd007ad9611c90a901438ad9611e90a8d9611ad9711e9008d9711e8d0dce000d004c000f00e8a1869308d9a11a2"
            "022003cfa001ad96111869308d9a11a2022003cf2006cf6000000000000048454c4c4f00444f4e4500544f4f4c00"
        ),
        "expected_console": "HELLO\nTOOL7\nDONE\n",
    },
    "nested_do_until_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-do-until-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'PrintE("OUTER")\r'
            'FI\r'
            'DO\r'
            'IF 1 = 1 THEN\r'
            'PrintE("INNER")\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 72\n"
            "b dp0p1ap2ghe0vdp3p4qhe1we2vp5p6qtop7p8qtoe3r\n"
            "s OUTER\n"
            "s INNER\n"
            "s BAD\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a902a2008dee108eef10a90ca200186dee108dee108a6def10aaadee108dee108eef10"
            "a90aa200ecef109007d00dcdee109002f004a901d002a900a200c900d0034c5410"
            "a9f08502a9108503a2022003cf2006cf"
            "a901a2008dee108eef10a901a200ecef10d005cdee10f0034c8210"
            "a9f68502a9108503a2022003cf2006cf"
            "4c9210"
            "a9fc8502a9108503a2022003cf2006cf"
            "a901a2008dee108eef10a901a200ecef10d005cdee10f0034c5410"
            "a901a2008dee108eef10a901a200ecef10d005cdee10f0034c0010"
            "a9008502a9118503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004f5554455200494e4e45520042414400444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 95, 0, 0, 0, 1, 74, 0, 17, 2, 0, 17,
                12, 0, 20, 17, 10, 0, 29, 24, 20, 0, 97, 74, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 39, 0, 97, 80, 0, 73, 16,
                255, 25, 45, 0, 97, 86, 0, 73, 16, 255, 17, 1, 0, 17, 1,
                0, 22, 24, 20, 0, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 97,
                90, 0, 73, 16, 255, 73, 32, 255, 79, 85, 84, 69, 82, 0,
                73, 78, 78, 69, 82, 0, 66, 65, 68, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "OUTER\nINNER\nDONE\n",
    },
    "nested_do_until_branch_mixed": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-do-until-branch-mixed",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'DO\r'
            'IF 1 = 1 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 75\n"
            "b e0r\n"
            "b dp0p1ap2ghu0we1vdp3p4qhc0we2vp5p6qtop7p8qtoe3r\n"
            "u w\n"
            "s HELLO\n"
            "s BAD1\n"
            "s BAD2\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a902a2008d1b128e1c12a90ca200186d1b128d1b128a6d1c12aaad1b128d1b128e1c12a90aa200ec1c129007d00dcd1b129002f004a901d002a900a200c900d0034c4a1020f8104c5a10a9278502a9128503a2022003cf2006cfa901a2008d1b128e1c12a901a200ec1c12d005cd1b12f0034c7b1020e7104c8b10a92c8502a9128503a2022003cf2006cfa901a2008d1b128e1c12a901a200ec1c12d005cd1b12f0034c5a10a901a2008d1b128e1c12a901a200ec1c12d005cd1b12f0034c0010a9318502a9128503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9218502a9128503a2022003cf2006cf60a9368502a9128503a2022003cfa907a2008d1b128e1c12a91f8502a9128503a000a200ad1c12c927901dd007ad1b12c910901438ad1b12e9108d1b12ad1c12e9278d1c12e8d0dce000d004c000f00e8a1869308d1f12a2022003cfa001a200ad1c12c903901dd007ad1b12c9e8901438ad1b12e9e88d1b12ad1c12e9038d1c12e8d0dce000d004c000f00e8a1869308d1f12a2022003cfa001a200ad1c12c900901dd007ad1b12c964901438ad1b12e9648d1b12ad1c12e9008d1c12e8d0dce000d004c000f00e8a1869308d1f12a2022003cfa001a200ad1c12c900901dd007ad1b12c90a901438ad1b12e90a8d1b12ad1c12e9008d1c12e8d0dce000d004c000f00e8a1869308d1f12a2022003cfa001ad1b121869308d1f12a2022003cf2006cf6000000000000048454c4c4f0042414431004241443200444f4e4500544f4f4c00"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 123, 0, 7, 0, 1, 97, 0, 97, 97, 0, 73,
                16, 255, 72, 17, 2, 0, 17, 12, 0, 20, 17, 10, 0, 29, 24,
                27, 0, 69, 84, 0, 25, 33, 0, 97, 103, 0, 73, 16, 255, 17,
                1, 0, 17, 1, 0, 22, 24, 49, 0, 69, 0, 0, 25, 55, 0, 97,
                108, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 33, 0,
                17, 1, 0, 17, 1, 0, 22, 24, 7, 0, 97, 113, 0, 73, 16, 255,
                73, 32, 255, 97, 118, 0, 73, 0, 255, 17, 7, 0, 73, 49,
                255, 72, 72, 69, 76, 76, 79, 0, 66, 65, 68, 49, 0, 66, 65,
                68, 50, 0, 68, 79, 78, 69, 0, 84, 79, 79, 76, 0,
            ]
        ),
        "expected_console": "TOOL7\nHELLO\nDONE\n",
    },
    "while_blocks": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-blocks",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'PrintE("BAD")\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 26\n"
            "b dp0p1qfe0xe1r\n"
            "s BAD\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d54108e5510a900a200ec5510d005cd5410f0034c2e10"
            "a9568502a9108503a2022003cf2006cf"
            "4c0010"
            "a95a8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000042414400444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 37, 0, 0, 0, 1, 28, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 19, 0, 97, 28, 0, 73, 16, 255, 25, 0, 0,
                97, 32, 0, 73, 16, 255, 73, 32, 255, 66, 65, 68, 0, 68,
                79, 78, 69, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "while_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'HELLO()\r'
            'W()\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 26\n"
            "b e0r\n"
            "b dp0p1qfc0u0xe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d7e118e7f11a900a200ec7f11d005cd7e11f0034c2410204a10205b104c0010a98a8502a9118503a202"
            "2003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9848502a9118503a2022003cf2006cf60a98f85"
            "02a9118503a2022003cfa907a2008d7e118e7f11a9828502a9118503a000a200ad7f11c927901dd007ad7e11c9109014"
            "38ad7e11e9108d7e11ad7f11e9278d7f11e8d0dce000d004c000f00e8a1869308d8211a2022003cfa001a200ad7f11c9"
            "03901dd007ad7e11c9e8901438ad7e11e9e88d7e11ad7f11e9038d7f11e8d0dce000d004c000f00e8a1869308d8211a2"
            "022003cfa001a200ad7f11c900901dd007ad7e11c964901438ad7e11e9648d7e11ad7f11e9008d7f11e8d0dce000d004"
            "c000f00e8a1869308d8211a2022003cfa001a200ad7f11c900901dd007ad7e11c90a901438ad7e11e90a8d7e11ad7f11"
            "e9008d7f11e8d0dce000d004c000f00e8a1869308d8211a2022003cfa001ad7e111869308d8211a2022003cf2006cf60"
            "00000000000048454c4c4f00444f4e4500544f4f4c00"
        ),
        "expected_console": "DONE\n",
    },
    "while_if_else": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-if-else",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'PrintE("BAD1")\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 49\n"
            "b dp0p1qfp2p3ap4ghe0we1vxe2r\n"
            "s BAD1\n"
            "s BAD2\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008dab108eac10a900a200ecac10d005cdab10f0034c8510"
            "a902a2008dab108eac10a90ca200186dab108dab108a6dac10aaadab108dab108eac10"
            "a90aa200ecac109007d00dcdab109002f004a901d002a900a200c900d0034c7210"
            "a9ad8502a9108503a2022003cf2006cf"
            "4c8210"
            "a9b28502a9108503a2022003cf2006cf"
            "4c0010"
            "a9b78502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000042414431004241443200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 66, 0, 0, 0, 1, 51, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 42, 0, 17, 2, 0, 17, 12, 0, 20, 17, 10, 0,
                29, 24, 33, 0, 97, 51, 0, 73, 16, 255, 25, 39, 0, 97, 56,
                0, 73, 16, 255, 25, 0, 0, 97, 61, 0, 73, 16, 255, 73, 32,
                255, 66, 65, 68, 49, 0, 66, 65, 68, 50, 0, 68, 79, 78, 69,
                0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "while_branch_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-branch-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC BYE()\r'
            'PrintE("BYE")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'BYE()\r'
            'FI\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x bye 7 7\n"
            "x main 14 43\n"
            "b e0r\n"
            "b e1r\n"
            "b dp0p1qfp2p3ap4ghc0wc1vxe2r\n"
            "s HELLO\n"
            "s BYE\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 179, 16, 142, 180, 16, 169, 0, 162, 0,
                236, 180, 16, 208, 5, 205, 179, 16, 240, 3, 76, 107, 16, 169, 2, 162,
                0, 141, 179, 16, 142, 180, 16, 169, 12, 162, 0, 24, 109, 179, 16, 141,
                179, 16, 138, 109, 180, 16, 170, 173, 179, 16, 141, 179, 16, 142, 180, 16,
                169, 10, 162, 0, 236, 180, 16, 144, 7, 208, 13, 205, 179, 16, 144, 2,
                240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 101,
                16, 32, 145, 16, 76, 104, 16, 32, 162, 16, 76, 0, 16, 169, 193, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3,
                142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2,
                76, 15, 207, 169, 183, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207,
                32, 6, 207, 96, 169, 189, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3,
                207, 32, 6, 207, 96, 0, 0, 0, 0, 72, 69, 76, 76, 79, 0, 66,
                89, 69, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "while_branch_external": {
        "out_fs_name": "harness-actc-alink-prg-while-branch-external",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD")\r'
            'FI\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 46\n"
            "b dp0p1qfp2p3ap4ghu0we0vxe1r\n"
            "u w\n"
            "s BAD\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "A901A2008DC1118EC211A900A200ECC211D005CDC111F0034C7810A902A2008DC1118EC211A90C"
            "A200186DC1118DC1118A6DC211AAADC1118DC1118EC211A90AA200ECC2119007D00DCDC1119002"
            "F004A901D002A900A200C900D0034C6510209E104C7510A9C78502A9118503A2022003CF2006CF"
            "4C0010A9CB8502A9118503A2022003CF2006CF8DD1038ED203A9A58DD003A90085028503A2024C"
            "0FCFA9D08502A9118503A2022003CFA907A2008DC1118EC211A9C58502A9118503A000A200ADC2"
            "11C927901DD007ADC111C910901438ADC111E9108DC111ADC211E9278DC211E8D0DCE000D004C0"
            "00F00E8A1869308DC511A2022003CFA001A200ADC211C903901DD007ADC111C9E8901438ADC111"
            "E9E88DC111ADC211E9038DC211E8D0DCE000D004C000F00E8A1869308DC511A2022003CFA001A2"
            "00ADC211C900901DD007ADC111C964901438ADC111E9648DC111ADC211E9008DC211E8D0DCE000"
            "D004C000F00E8A1869308DC511A2022003CFA001A200ADC211C900901DD007ADC111C90A901438"
            "ADC111E90A8DC111ADC211E9008DC211E8D0DCE000D004C000F00E8A1869308DC511A2022003CF"
            "A001ADC1111869308DC511A2022003CF2006CF6000000000000042414400444F4E4500544F4F4C"
            "00"
        ),
        "expected_console": "DONE\n",
    },
    "nested_while": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-while",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'PrintE("OUTER")\r'
            'WHILE 1 = 0 DO\r'
            'PrintE("INNER")\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 45\n"
            "b dp0p1qfe0dp2p3qfe1xxe2r\n"
            "s OUTER\n"
            "s INNER\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d82108e8310a900a200ec8310d005cd8210f0034c5c10"
            "a9848502a9108503a2022003cf2006cf"
            "a901a2008d82108e8310a900a200ec8310d005cd8210f0034c5910"
            "a98a8502a9108503a2022003cf2006cf"
            "4c2b10"
            "4c0010"
            "a9908502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004f5554455200494e4e455200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 64, 0, 0, 0, 1, 47, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 38, 0, 97, 47, 0, 73, 16, 255, 17, 1, 0,
                17, 0, 0, 22, 24, 35, 0, 97, 53, 0, 73, 16, 255, 25, 16,
                0, 25, 0, 0, 97, 59, 0, 73, 16, 255, 73, 32, 255, 79, 85,
                84, 69, 82, 0, 73, 78, 78, 69, 82, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "nested_while_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-while-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'HELLO()\r'
            'WHILE 1 = 0 DO\r'
            'W()\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 39\n"
            "b e0r\n"
            "b dp0p1qfc0dp2p3qfu0xxe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d9c118e9d11a900a200ec9d11d005cd9c11f0034c4210206810a901a2008d9c118e9d11a900a200ec9d"
            "11d005cd9c11f0034c3f102079104c1e104c0010a9a88502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a9"
            "0085028503a2024c0fcfa9a28502a9118503a2022003cf2006cf60a9ad8502a9118503a2022003cfa907a2008d9c118e"
            "9d11a9a08502a9118503a000a200ad9d11c927901dd007ad9c11c910901438ad9c11e9108d9c11ad9d11e9278d9d11e8"
            "d0dce000d004c000f00e8a1869308da011a2022003cfa001a200ad9d11c903901dd007ad9c11c9e8901438ad9c11e9e8"
            "8d9c11ad9d11e9038d9d11e8d0dce000d004c000f00e8a1869308da011a2022003cfa001a200ad9d11c900901dd007ad"
            "9c11c964901438ad9c11e9648d9c11ad9d11e9008d9d11e8d0dce000d004c000f00e8a1869308da011a2022003cfa001"
            "a200ad9d11c900901dd007ad9c11c90a901438ad9c11e90a8d9c11ad9d11e9008d9d11e8d0dce000d004c000f00e8a18"
            "69308da011a2022003cfa001ad9c111869308da011a2022003cf2006cf6000000000000048454c4c4f00444f4e450054"
            "4f4f4c00"
        ),
        "expected_console": "DONE\n",
    },
    "nested_while_branch_mixed": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-while-branch-mixed",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'WHILE 1 = 0 DO\r'
            'IF 1 = 1 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 81\n"
            "b e0r\n"
            "b dp0p1qfp2p3ap4ghu0we1vdp5p6qfp7p8qhc0we2vxxe3r\n"
            "u w\n"
            "s HELLO\n"
            "s BAD1\n"
            "s BAD2\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d21128e2212a900a200ec2212d005cd2112f0034cc710a902a2008d21128e2212a90ca200186d21128d"
            "21128a6d2212aaad21128d21128e2212a90aa200ec22129007d00dcd21129002f004a901d002a900a200c900d0034c65"
            "1020fe104c7510a92d8502a9128503a2022003cf2006cfa901a2008d21128e2212a900a200ec2212d005cd2112f0034c"
            "c410a901a2008d21128e2212a901a200ec2212d005cd2112f0034cb11020ed104cc110a9328502a9128503a2022003cf"
            "2006cf4c75104c0010a9378502a9128503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9"
            "278502a9128503a2022003cf2006cf60a93c8502a9128503a2022003cfa907a2008d21128e2212a9258502a9128503a0"
            "00a200ad2212c927901dd007ad2112c910901438ad2112e9108d2112ad2212e9278d2212e8d0dce000d004c000f00e8a"
            "1869308d2512a2022003cfa001a200ad2212c903901dd007ad2112c9e8901438ad2112e9e88d2112ad2212e9038d2212"
            "e8d0dce000d004c000f00e8a1869308d2512a2022003cfa001a200ad2212c900901dd007ad2112c964901438ad2112e9"
            "648d2112ad2212e9008d2212e8d0dce000d004c000f00e8a1869308d2512a2022003cfa001a200ad2212c900901dd007"
            "ad2112c90a901438ad2112e90a8d2112ad2212e9008d2212e8d0dce000d004c000f00e8a1869308d2512a2022003cfa0"
            "01ad21121869308d2512a2022003cf2006cf6000000000000048454c4c4f0042414431004241443200444f4e4500544f"
            "4f4c00"
        ),
        "expected_console": "DONE\n",
    },
    "while_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'WHILE 1 = 0 DO\r'
                'W()\r'
                'Q()\r'
                'OD\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 26\n"
                "b dp0p1qfu0u1xe0r\n"
                "u w\n"
                "u q\n"
                "s DONE\n"
                "i 1\n"
                "i 0\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010a901a2008d83108e8410a900a200ec8410d005cd8310f0034c2410204a10205e104c0010a9878502a9108503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa98c8502a9108503a2022003cf2006cf20721060a9918502a9108503a2022003cf2006cf20721060a9968502a9108503a2022003cf2006cf6000000000444f4e45004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 74, 0, 0, 0, 1, 55, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 19, 0, 69, 28, 0, 69, 38, 0, 25, 0, 0, 97,
                55, 0, 73, 16, 255, 73, 32, 255, 97, 60, 0, 73, 16, 255,
                69, 48, 0, 72, 97, 65, 0, 73, 16, 255, 69, 48, 0, 72, 97,
                70, 0, 73, 16, 255, 72, 68, 79, 78, 69, 0, 77, 73, 68, 49,
                0, 77, 73, 68, 50, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "do_until_nested_while": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-nested-while",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'DO\r'
            'PrintE("OUTER")\r'
            'WHILE 1 = 0 DO\r'
            'PrintE("INNER")\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 42\n"
            "b de0dp0p1qfe1xp2p3qtoe2r\n"
            "s OUTER\n"
            "s INNER\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a9818502a9108503a2022003cf2006cf"
            "a901a2008d7f108e8010a900a200ec8010d005cd7f10f0034c3e10"
            "a9878502a9108503a2022003cf2006cf"
            "4c1010"
            "a901a2008d7f108e8010a901a200ec8010d005cd7f10f0034c0010"
            "a98d8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004f5554455200494e4e455200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 61, 0, 0, 0, 1, 44, 0, 97, 44, 0, 73,
                16, 255, 17, 1, 0, 17, 0, 0, 22, 24, 25, 0, 97, 50, 0, 73,
                16, 255, 25, 6, 0, 17, 1, 0, 17, 1, 0, 22, 24, 6, 0, 97,
                56, 0, 73, 16, 255, 73, 32, 255, 79, 85, 84, 69, 82, 0,
                73, 78, 78, 69, 82, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "OUTER\nDONE\n",
    },
    "while_nested_do_until": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-nested-do-until",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'PrintE("OUTER")\r'
            'DO\r'
            'PrintE("INNER")\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 42\n"
            "b dp0p1qfe0de1p2p3qtoxe2r\n"
            "s OUTER\n"
            "s INNER\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d7f108e8010a900a200ec8010d005cd7f10f0034c5910"
            "a9818502a9108503a2022003cf2006cf"
            "a9878502a9108503a2022003cf2006cf"
            "a901a2008d7f108e8010a901a200ec8010d005cd7f10f0034c2b10"
            "4c0010"
            "a98d8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "00004f5554455200494e4e455200444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 61, 0, 0, 0, 1, 44, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 35, 0, 97, 44, 0, 73, 16, 255, 97, 50, 0,
                73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 16, 0, 25, 0, 0,
                97, 56, 0, 73, 16, 255, 73, 32, 255, 79, 85, 84, 69, 82,
                0, 73, 78, 78, 69, 82, 0, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "do_until_nested_while_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-nested-while-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'HELLO()\r'
            'WHILE 1 = 0 DO\r'
            'W()\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 36\n"
            "b e0r\n"
            "b dc0dp0p1qfu0xp2p3qtoe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010206510a901a2008d99118e9a11a900a200ec9a11d005cd9911f0034c24102076104c0310a901a2008d99118e9a11"
            "a901a200ec9a11d005cd9911f0034c0010a9a58502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcfa99f8502a9118503a2022003cf2006cf60a9aa8502a9118503a2022003cfa907a2008d99118e9a11a9"
            "9d8502a9118503a000a200ad9a11c927901dd007ad9911c910901438ad9911e9108d9911ad9a11e9278d9a11e8d0dce0"
            "00d004c000f00e8a1869308d9d11a2022003cfa001a200ad9a11c903901dd007ad9911c9e8901438ad9911e9e88d9911"
            "ad9a11e9038d9a11e8d0dce000d004c000f00e8a1869308d9d11a2022003cfa001a200ad9a11c900901dd007ad9911c9"
            "64901438ad9911e9648d9911ad9a11e9008d9a11e8d0dce000d004c000f00e8a1869308d9d11a2022003cfa001a200ad"
            "9a11c900901dd007ad9911c90a901438ad9911e90a8d9911ad9a11e9008d9a11e8d0dce000d004c000f00e8a1869308d"
            "9d11a2022003cfa001ad99111869308d9d11a2022003cf2006cf6000000000000048454c4c4f00444f4e4500544f4f4c"
            "00"
        ),
        "expected_console": "HELLO\nDONE\n",
    },
    "while_nested_do_until_calls": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-nested-do-until-calls",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'WHILE 1 = 0 DO\r'
            'HELLO()\r'
            'DO\r'
            'W()\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 36\n"
            "b e0r\n"
            "b dp0p1qfc0du0p2p3qtoxe1r\n"
            "u w\n"
            "s HELLO\n"
            "s DONE\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d99118e9a11a900a200ec9a11d005cd9911f0034c3f10206510207610a901a2008d99118e9a11a901a2"
            "00ec9a11d005cd9911f0034c1e104c0010a9a58502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a9008502"
            "8503a2024c0fcfa99f8502a9118503a2022003cf2006cf60a9aa8502a9118503a2022003cfa907a2008d99118e9a11a9"
            "9d8502a9118503a000a200ad9a11c927901dd007ad9911c910901438ad9911e9108d9911ad9a11e9278d9a11e8d0dce0"
            "00d004c000f00e8a1869308d9d11a2022003cfa001a200ad9a11c903901dd007ad9911c9e8901438ad9911e9e88d9911"
            "ad9a11e9038d9a11e8d0dce000d004c000f00e8a1869308d9d11a2022003cfa001a200ad9a11c900901dd007ad9911c9"
            "64901438ad9911e9648d9911ad9a11e9008d9a11e8d0dce000d004c000f00e8a1869308d9d11a2022003cfa001a200ad"
            "9a11c900901dd007ad9911c90a901438ad9911e90a8d9911ad9a11e9008d9a11e8d0dce000d004c000f00e8a1869308d"
            "9d11a2022003cfa001ad99111869308d9d11a2022003cf2006cf6000000000000048454c4c4f00444f4e4500544f4f4c"
            "00"
        ),
        "expected_console": "DONE\n",
    },
    "do_until_nested_while_branch_mixed": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-nested-while-branch-mixed",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'DO\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'W()\r'
            'ELSE\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'WHILE 1 = 0 DO\r'
            'IF 1 = 1 THEN\r'
            'HELLO()\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'OD\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("DONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 78\n"
            "b e0r\n"
            "b dp0p1ap2ghu0we1vdp3p4qfp5p6qhc0we2vxp7p8qtoe3r\n"
            "u w\n"
            "s HELLO\n"
            "s BAD1\n"
            "s BAD2\n"
            "s DONE\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a902a2008d1e128e1f12a90ca200186d1e128d1e128a6d1f12aaad1e128d1e128e1f12a90aa200ec1f129007d00d"
            "cd1e129002f004a901d002a900a200c900d0034c4a1020fb104c5a10a92a8502a9128503a2022003cf2006cfa901a200"
            "8d1e128e1f12a900a200ec1f12d005cd1e12f0034ca910a901a2008d1e128e1f12a901a200ec1f12d005cd1e12f0034c"
            "961020ea104ca610a92f8502a9128503a2022003cf2006cf4c5a10a901a2008d1e128e1f12a901a200ec1f12d005cd1e"
            "12f0034c0010a9348502a9128503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9248502"
            "a9128503a2022003cf2006cf60a9398502a9128503a2022003cfa907a2008d1e128e1f12a9228502a9128503a000a200"
            "ad1f12c927901dd007ad1e12c910901438ad1e12e9108d1e12ad1f12e9278d1f12e8d0dce000d004c000f00e8a186930"
            "8d2212a2022003cfa001a200ad1f12c903901dd007ad1e12c9e8901438ad1e12e9e88d1e12ad1f12e9038d1f12e8d0dc"
            "e000d004c000f00e8a1869308d2212a2022003cfa001a200ad1f12c900901dd007ad1e12c964901438ad1e12e9648d1e"
            "12ad1f12e9008d1f12e8d0dce000d004c000f00e8a1869308d2212a2022003cfa001a200ad1f12c900901dd007ad1e12"
            "c90a901438ad1e12e90a8d1e12ad1f12e9008d1f12e8d0dce000d004c000f00e8a1869308d2212a2022003cfa001ad1e"
            "121869308d2212a2022003cf2006cf6000000000000048454c4c4f0042414431004241443200444f4e4500544f4f4c00"
        ),
        "expected_console": "TOOL7\nDONE\n",
    },
    "while_nested_do_until_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-nested-do-until-shared-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'WHILE 1 = 0 DO\r'
                'W()\r'
                'DO\r'
                'Q()\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'OD\r'
                'PrintE("DONE")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 36\n"
                "b dp0p1qfu0du1p2p3qtoxe0r\n"
                "u w\n"
                "u q\n"
                "s DONE\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 84, 0, 0, 0, 1, 65, 0, 17, 1, 0, 17,
                0, 0, 22, 24, 29, 0, 69, 38, 0, 69, 48, 0, 17, 1, 0, 17,
                1, 0, 22, 24, 13, 0, 25, 0, 0, 97, 65, 0, 73, 16, 255, 73,
                32, 255, 97, 70, 0, 73, 16, 255, 69, 58, 0, 72, 97, 75, 0,
                73, 16, 255, 69, 58, 0, 72, 97, 80, 0, 73, 16, 255, 72, 68,
                79, 78, 69, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69,
                78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 158, 16, 142, 159, 16, 169, 0, 162, 0,
                236, 159, 16, 208, 5, 205, 158, 16, 240, 3, 76, 63, 16, 32, 101, 16,
                32, 121, 16, 169, 1, 162, 0, 141, 158, 16, 142, 159, 16, 169, 1, 162,
                0, 236, 159, 16, 208, 5, 205, 158, 16, 240, 3, 76, 30, 16, 76, 0,
                16, 169, 162, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6,
                207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2,
                133, 3, 162, 2, 76, 15, 207, 169, 167, 133, 2, 169, 16, 133, 3, 162,
                2, 32, 3, 207, 32, 6, 207, 32, 141, 16, 96, 169, 172, 133, 2, 169,
                16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 32, 141, 16, 96, 169,
                177, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96,
                0, 0, 0, 0, 68, 79, 78, 69, 0, 77, 73, 68, 49, 0, 77, 73,
                68, 50, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "DONE\n",
    },
    "nested_if": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-if",
        "artifact_kind": "prg",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 1 THEN\r'
            'IF 1 = 0 THEN\r'
            'PrintE("BAD")\r'
            'FI\r'
            'PrintE("INNERDONE")\r'
            'FI\r'
            'PrintE("OUTERDONE")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 39\n"
            "b p0p1qhp2p3qhe0ve1ve2r\n"
            "s BAD\n"
            "s INNERDONE\n"
            "s OUTERDONE\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010"
            "a901a2008d7c108e7d10a901a200ec7d10d005cd7c10f0034c5610"
            "a901a2008d7c108e7d10a900a200ec7d10d005cd7c10f0034c4610"
            "a97e8502a9108503a2022003cf2006cf"
            "a9828502a9108503a2022003cf2006cf"
            "a98c8502a9108503a2022003cf2006cf"
            "8dd1038ed203a9a58dd003a90085028503a2024c0fcf"
            "000042414400494e4e4552444f4e45004f55544552444f4e4500"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 65, 0, 0, 0, 1, 41, 0, 17, 1, 0, 17,
                1, 0, 22, 24, 32, 0, 17, 1, 0, 17, 0, 0, 22, 24, 26, 0,
                97, 41, 0, 73, 16, 255, 97, 45, 0, 73, 16, 255, 97, 55, 0,
                73, 16, 255, 73, 32, 255, 66, 65, 68, 0, 73, 78, 78, 69, 82,
                68, 79, 78, 69, 0, 79, 85, 84, 69, 82, 68, 79, 78, 69, 0,
            ]
        ),
        "expected_console": "INNERDONE\nOUTERDONE\n",
    },
    "if_early_return": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-early-return",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'IF 1 = 1 THEN\r'
            'PrintE("EARLY")\r'
            'RETURN\r'
            'FI\r'
            'PrintE("BAD")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 30\n"
            "b e0p0p1qhe1rve2r\n"
            "s START\n"
            "s EARLY\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 50, 0, 0, 0, 1, 34, 0, 97, 34, 0, 73,
                16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 25, 0, 97, 40, 0, 73,
                16, 255, 25, 31, 0, 97, 46, 0, 73, 16, 255, 73, 32, 255, 83,
                84, 65, 82, 84, 0, 69, 65, 82, 76, 89, 0, 66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 85, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 81, 16, 142, 82, 16, 169, 1, 162, 0,
                236, 82, 16, 208, 5, 205, 81, 16, 240, 3, 76, 81, 16, 169, 91, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3,
                142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2,
                76, 15, 207, 0, 0, 0, 0, 83, 84, 65, 82, 84, 0, 69, 65, 82,
                76, 89, 0,
            ]
        ),
        "expected_console": "START\nEARLY\n",
    },
    "else_early_return": {
        "out_fs_name": "harness-actc-alink-direct-prg-else-early-return",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'IF 1 = 0 THEN\r'
            'PrintE("BAD")\r'
            'ELSE\r'
            'PrintE("EARLY")\r'
            'RETURN\r'
            'FI\r'
            'PrintE("BAD2")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 33\n"
            "b p0p1qhe0we1rve2r\n"
            "s BAD\n"
            "s EARLY\n"
            "s BAD2\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 52, 0, 0, 0, 1, 37, 0, 17, 1, 0, 17, 0,
                0, 22, 24, 19, 0, 97, 37, 0, 73, 16, 255, 25, 28, 0, 97, 41,
                0, 73, 16, 255, 25, 34, 0, 97, 47, 0, 73, 16, 255, 73, 32,
                255, 66, 65, 68, 0, 69, 65, 82, 76, 89, 0, 66, 65, 68, 50, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 84, 16, 142, 85, 16, 169, 0, 162, 0,
                236, 85, 16, 208, 5, 205, 84, 16, 240, 3, 76, 46, 16, 169, 88, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 76, 84, 16,
                169, 92, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 0, 0, 0, 0, 66, 65, 68, 0, 69, 65,
                82, 76, 89, 0,
            ]
        ),
        "expected_console": "EARLY\n",
    },
    "do_until_early_return": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-early-return",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'DO\r'
            'PrintE("EARLY")\r'
            'RETURN\r'
            'UNTIL 1 = 1\r'
            'OD\r'
            'PrintE("BAD")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 30\n"
            "b e0de1rp0p1qtoe2r\n"
            "s START\n"
            "s EARLY\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 50, 0, 0, 0, 1, 34, 0, 97, 34, 0, 73, 16,
                255, 97, 40, 0, 73, 16, 255, 25, 31, 0, 17, 1, 0, 17, 1, 0,
                22, 24, 6, 0, 97, 46, 0, 73, 16, 255, 73, 32, 255, 83, 84,
                65, 82, 84, 0, 69, 65, 82, 76, 89, 0, 66, 65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 58, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 64, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133,
                2, 133, 3, 162, 2, 76, 15, 207, 0, 0, 0, 0, 83, 84, 65, 82,
                84, 0, 69, 65, 82, 76, 89, 0,
            ]
        ),
        "expected_console": "START\nEARLY\n",
    },
    "while_early_return": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-early-return",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'WHILE 1 = 1 DO\r'
            'PrintE("EARLY")\r'
            'RETURN\r'
            'OD\r'
            'PrintE("BAD")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 33\n"
            "b e0dp0p1qfe1rxe2r\n"
            "s START\n"
            "s EARLY\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 53, 0, 0, 0, 1, 37, 0, 97, 37, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 28, 0, 97, 43, 0, 73, 16,
                255, 25, 34, 0, 25, 6, 0, 97, 49, 0, 73, 16, 255, 73, 32,
                255, 83, 84, 65, 82, 84, 0, 69, 65, 82, 76, 89, 0, 66, 65,
                68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 85, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 81, 16, 142, 82, 16, 169, 1, 162, 0,
                236, 82, 16, 208, 5, 205, 81, 16, 240, 3, 76, 81, 16, 169, 91, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3,
                142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2,
                76, 15, 207, 0, 0, 0, 0, 83, 84, 65, 82, 84, 0, 69, 65, 82,
                76, 89, 0,
            ]
        ),
        "expected_console": "START\nEARLY\n",
    },
    "nested_if_early_return": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-if-early-return",
        "source": (
            'MODULE MAIN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'IF 1 = 1 THEN\r'
            'IF 2 + 3 * 4 > 10 THEN\r'
            'PrintE("EARLY")\r'
            'RETURN\r'
            'ELSE\r'
            'PrintE("BAD1")\r'
            'FI\r'
            'ELSE\r'
            'PrintE("BAD2")\r'
            'FI\r'
            'PrintE("BAD3")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x main 0 62\n"
            "b e0p0p1qhp2p3ap4ghe1rwe2vwe3ve4r\n"
            "s START\n"
            "s EARLY\n"
            "s BAD1\n"
            "s BAD2\n"
            "s BAD3\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 93, 0, 0, 0, 1, 66, 0, 97, 66, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 51, 0, 17, 2, 0, 17, 12, 0,
                20, 17, 10, 0, 29, 24, 42, 0, 97, 72, 0, 73, 16, 255, 25, 63,
                0, 25, 48, 0, 97, 78, 0, 73, 16, 255, 25, 57, 0, 97, 83, 0,
                73, 16, 255, 97, 88, 0, 73, 16, 255, 73, 32, 255, 83, 84, 65,
                82, 84, 0, 69, 65, 82, 76, 89, 0, 66, 65, 68, 49, 0, 66, 65,
                68, 50, 0, 66, 65, 68, 51, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 153, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 149, 16, 142, 150, 16, 169, 1, 162, 0,
                236, 150, 16, 208, 5, 205, 149, 16, 240, 3, 76, 149, 16, 169, 2, 162,
                0, 141, 149, 16, 142, 150, 16, 169, 12, 162, 0, 24, 109, 149, 16, 141,
                149, 16, 138, 109, 150, 16, 170, 173, 149, 16, 141, 149, 16, 142, 150, 16,
                169, 10, 162, 0, 236, 150, 16, 144, 7, 208, 13, 205, 149, 16, 144, 2,
                240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 149,
                16, 169, 159, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6,
                207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2,
                133, 3, 162, 2, 76, 15, 207, 0, 0, 0, 0, 83, 84, 65, 82, 84,
                0, 69, 65, 82, 76, 89, 0,
            ]
        ),
        "expected_console": "START\nEARLY\n",
    },
    "if_return_local": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-return-local",
        "source": (
            'MODULE MAIN\r'
            'PROC HELLO()\r'
            'PrintE("HELLO")\r'
            'RETURN\r'
            'PROC MAIN()\r'
            'PrintE("START")\r'
            'IF 1 = 1 THEN\r'
            'HELLO()\r'
            'RETURN\r'
            'FI\r'
            'PrintE("BAD")\r'
            'RETURN\r'
        ),
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 27\n"
            "b e0r\n"
            "b e1p0p1qhc0rve2r\n"
            "s HELLO\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 54, 0, 7, 0, 1, 38, 0, 97, 38, 0, 73, 16,
                255, 72, 97, 44, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24,
                29, 0, 69, 0, 0, 25, 35, 0, 97, 50, 0, 73, 16, 255, 73, 32,
                255, 72, 69, 76, 76, 79, 0, 83, 84, 65, 82, 84, 0, 66, 65,
                68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 95, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 85, 16, 142, 86, 16, 169, 1, 162, 0,
                236, 86, 16, 208, 5, 205, 85, 16, 240, 3, 76, 68, 16, 32, 68, 16,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 169, 89, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 72, 69, 76, 76, 79,
                0, 83, 84, 65, 82, 84, 0,
            ]
        ),
        "expected_console": "START\nHELLO\n",
    },
    "if_return_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-return-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'RETURN\r'
                'FI\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 27\n"
                "b e0p0p1qhu0rve1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 27\n"
            "b e0p0p1qhu0rve1r\n"
            "u w\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 89, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 85, 16, 142, 86, 16, 169, 1, 162, 0,
                236, 86, 16, 208, 5, 205, 85, 16, 240, 3, 76, 68, 16, 32, 68, 16,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 169, 95, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 83, 84, 65, 82, 84,
                0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "expected_console": "START\nTOOL7\n",
    },
    "if_return_external_args_multi": {
        "out_fs_name": "harness-actc-alink-direct-prg-if-return-external-args-multi",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[2]\r'
                'INT Y=[3]\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'IF 1 = 1 THEN\r'
                'PrintIE(W(X,Y))\r'
                'RETURN\r'
                'FI\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(A,B)\r'
                'RETURN A+B\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 36\n"
                "b e0p0p1qhL0L1u0zrve1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "v x 2\n"
                "v y 3\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 14\n"
                "b S1S0L0L1ar\n"
                "v a 0\n"
                "v b 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 187, 133, 2, 169, 17, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 173, 17, 142, 174, 17, 169, 1, 162, 0,
                236, 174, 17, 208, 5, 205, 173, 17, 240, 3, 76, 121, 17, 173, 179, 17,
                174, 180, 17, 141, 173, 17, 142, 174, 17, 173, 181, 17, 174, 182, 17, 72,
                138, 72, 173, 173, 17, 141, 175, 17, 173, 174, 17, 141, 176, 17, 104, 170,
                104, 32, 121, 17, 141, 173, 17, 142, 174, 17, 169, 177, 133, 2, 169, 17,
                133, 3, 160, 0, 162, 0, 173, 174, 17, 201, 39, 144, 29, 208, 7, 173,
                173, 17, 201, 16, 144, 20, 56, 173, 173, 17, 233, 16, 141, 173, 17, 173,
                174, 17, 233, 39, 141, 174, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0,
                240, 14, 138, 24, 105, 48, 141, 177, 17, 162, 2, 32, 3, 207, 160, 1,
                162, 0, 173, 174, 17, 201, 3, 144, 29, 208, 7, 173, 173, 17, 201, 232,
                144, 20, 56, 173, 173, 17, 233, 232, 141, 173, 17, 173, 174, 17, 233, 3,
                141, 174, 17, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24,
                105, 48, 141, 177, 17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 174,
                17, 201, 0, 144, 29, 208, 7, 173, 173, 17, 201, 100, 144, 20, 56, 173,
                173, 17, 233, 100, 141, 173, 17, 173, 174, 17, 233, 0, 141, 174, 17, 232,
                208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 177,
                17, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 174, 17, 201, 0, 144,
                29, 208, 7, 173, 173, 17, 201, 10, 144, 20, 56, 173, 173, 17, 233, 10,
                141, 173, 17, 173, 174, 17, 233, 0, 141, 174, 17, 232, 208, 220, 224, 0,
                208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 177, 17, 162, 2, 32,
                3, 207, 160, 1, 173, 173, 17, 24, 105, 48, 141, 177, 17, 162, 2, 32,
                3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3,
                169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 141, 191, 1, 142, 192,
                1, 173, 175, 17, 174, 176, 17, 141, 189, 1, 142, 190, 1, 173, 189, 1,
                174, 190, 1, 141, 175, 17, 142, 176, 17, 173, 191, 1, 174, 192, 1, 24,
                109, 175, 17, 141, 175, 17, 138, 109, 176, 17, 170, 173, 175, 17, 96, 0,
                0, 0, 0, 0, 0, 2, 0, 3, 0, 0, 0, 0, 0, 83, 84, 65,
                82, 84, 0,
            ]
        ),
        "expected_console": "START\n5\n",
    },
    "else_return_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-else-return-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'IF 1 = 0 THEN\r'
                'PrintE("BAD")\r'
                'ELSE\r'
                'W()\r'
                'RETURN\r'
                'FI\r'
                'PrintE("BAD2")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 30\n"
                "b p0p1qhe0wu0rve1r\n"
                "u w\n"
                "s BAD\n"
                "s BAD2\n"
                "i 1\n"
                "i 0\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 30\n"
            "b p0p1qhe0wu0rve1r\n"
            "u w\n"
            "s BAD\n"
            "s BAD2\n"
            "i 1\n"
            "i 0\n"
            "k 2\n"
            "n main\n"
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 1, 162, 0, 141, 88, 16, 142, 89, 16, 169, 0, 162, 0,
                236, 89, 16, 208, 5, 205, 88, 16, 240, 3, 76, 46, 16, 169, 92, 133,
                2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 76, 71, 16,
                32, 71, 16, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0,
                133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 96, 133, 2, 169, 16, 133,
                3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 66, 65,
                68, 0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "expected_console": "TOOL7\n",
    },
    "do_until_return_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-return-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'DO\r'
                'W()\r'
                'RETURN\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 27\n"
                "b e0du0rp0p1qtoe1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 27\n"
            "b e0du0rp0p1qtoe1r\n"
            "u w\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 54, 0, 0, 0, 1, 38, 0, 97, 38, 0, 73, 16,
                255, 69, 31, 0, 25, 28, 0, 17, 1, 0, 17, 1, 0, 22, 24, 6,
                0, 97, 44, 0, 73, 16, 255, 73, 32, 255, 97, 48, 0, 73, 16,
                255, 72, 83, 84, 65, 82, 84, 0, 66, 65, 68, 0, 84, 79, 79,
                76, 55, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 62, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 32, 41, 16, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3,
                169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 68, 133, 2, 169,
                16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0,
                83, 84, 65, 82, 84, 0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "expected_console": "START\nTOOL7\n",
    },
    "while_return_local_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-return-local-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC HELLO()\r'
                'PrintE("HELLO")\r'
                'RETURN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'WHILE 1 = 1 DO\r'
                'HELLO()\r'
                'W()\r'
                'RETURN\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x hello 0 7\n"
                "x main 7 33\n"
                "b e0r\n"
                "b e1dp0p1qfc0u0rxe2r\n"
                "u w\n"
                "s HELLO\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 33\n"
            "b e0r\n"
            "b e1dp0p1qfc0u0rxe2r\n"
            "u w\n"
            "s HELLO\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 73, 0, 7, 0, 1, 51, 0, 97, 51, 0, 73, 16,
                255, 72, 97, 57, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24,
                35, 0, 69, 0, 0, 69, 44, 0, 25, 41, 0, 25, 13, 0, 97, 63,
                0, 73, 16, 255, 73, 32, 255, 97, 67, 0, 73, 16, 255, 72, 72,
                69, 76, 76, 79, 0, 83, 84, 65, 82, 84, 0, 66, 65, 68, 0, 84,
                79, 79, 76, 55, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 115, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 105, 16, 142, 106, 16, 169, 1, 162, 0,
                236, 106, 16, 208, 5, 205, 105, 16, 240, 3, 76, 71, 16, 32, 71, 16,
                32, 88, 16, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0,
                133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 109, 133, 2, 169, 16, 133,
                3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 169, 121, 133, 2, 169, 16,
                133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 72,
                69, 76, 76, 79, 0, 83, 84, 65, 82, 84, 0, 84, 79, 79, 76, 55,
                0,
            ]
        ),
        "expected_console": "START\nHELLO\nTOOL7\n",
    },
    "nested_if_return_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-if-return-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'IF 1 = 1 THEN\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'W()\r'
                'RETURN\r'
                'ELSE\r'
                'PrintE("BAD1")\r'
                'FI\r'
                'ELSE\r'
                'PrintE("BAD2")\r'
                'FI\r'
                'PrintE("BAD3")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 59\n"
                "b e0p0p1qhp2p3ap4ghu0rwe1vwe2ve3r\n"
                "u w\n"
                "s START\n"
                "s BAD1\n"
                "s BAD2\n"
                "s BAD3\n"
                "i 1\n"
                "i 1\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 59\n"
            "b e0p0p1qhp2p3ap4ghu0rwe1vwe2ve3r\n"
            "u w\n"
            "s START\n"
            "s BAD1\n"
            "s BAD2\n"
            "s BAD3\n"
            "i 1\n"
            "i 1\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 109, 0, 0, 0, 1, 80, 0, 97, 80, 0, 73,
                16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 48, 0, 17, 2, 0, 17,
                12, 0, 20, 17, 10, 0, 29, 24, 39, 0, 69, 63, 0, 25, 60, 0,
                25, 45, 0, 97, 86, 0, 73, 16, 255, 25, 54, 0, 97, 91, 0, 73,
                16, 255, 97, 96, 0, 73, 16, 255, 73, 32, 255, 97, 101, 0, 73,
                16, 255, 69, 73, 0, 72, 97, 105, 0, 73, 16, 255, 72, 83, 84,
                65, 82, 84, 0, 66, 65, 68, 49, 0, 66, 65, 68, 50, 0, 66, 65,
                68, 51, 0, 77, 73, 68, 0, 69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 177, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 173, 16, 142, 174, 16, 169, 1, 162, 0,
                236, 174, 16, 208, 5, 205, 173, 16, 240, 3, 76, 136, 16, 169, 2, 162,
                0, 141, 173, 16, 142, 174, 16, 169, 12, 162, 0, 24, 109, 173, 16, 141,
                173, 16, 138, 109, 174, 16, 170, 173, 173, 16, 141, 173, 16, 142, 174, 16,
                169, 10, 162, 0, 236, 174, 16, 144, 7, 208, 13, 205, 173, 16, 144, 2,
                240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 136,
                16, 32, 136, 16, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169,
                0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 183, 133, 2, 169, 16,
                133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 32, 156, 16, 96, 169, 187,
                133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0,
                0, 0, 0, 83, 84, 65, 82, 84, 0, 77, 73, 68, 0, 69, 78, 68,
                0,
            ]
        ),
        "expected_console": "START\nMID\nEND\n",
    },
    "do_until_return_branch_mixed": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-return-branch-mixed",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC HELLO()\r'
                'PrintE("HELLO")\r'
                'RETURN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'DO\r'
                'IF 2 + 3 * 4 > 10 THEN\r'
                'W()\r'
                'ELSE\r'
                'HELLO()\r'
                'FI\r'
                'RETURN\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x hello 0 7\n"
                "x main 7 47\n"
                "b e0r\n"
                "b e1dp0p1ap2ghu0wc0vrp3p4qtoe2r\n"
                "u w\n"
                "s HELLO\n"
                "s START\n"
                "s BAD\n"
                "i 2\n"
                "i 12\n"
                "i 10\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x hello 0 7\n"
            "x main 7 47\n"
            "b e0r\n"
            "b e1dp0p1ap2ghu0wc0vrp3p4qtoe2r\n"
            "u w\n"
            "s HELLO\n"
            "s START\n"
            "s BAD\n"
            "i 2\n"
            "i 12\n"
            "i 10\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 159, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 2, 162, 0, 141, 149, 16, 142, 150, 16, 169, 12, 162, 0,
                24, 109, 149, 16, 141, 149, 16, 138, 109, 150, 16, 170, 173, 149, 16, 141,
                149, 16, 142, 150, 16, 169, 10, 162, 0, 236, 150, 16, 144, 7, 208, 13,
                205, 149, 16, 144, 2, 240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201,
                0, 208, 3, 76, 90, 16, 32, 132, 16, 76, 93, 16, 32, 115, 16, 141,
                209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133, 3,
                162, 2, 76, 15, 207, 169, 153, 133, 2, 169, 16, 133, 3, 162, 2, 32,
                3, 207, 32, 6, 207, 96, 169, 165, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 72, 69, 76, 76, 79,
                0, 83, 84, 65, 82, 84, 0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "expected_console": "START\nTOOL7\n",
    },
    "do_until_return_branch_args_mixed": {
        "out_fs_name": "harness-actc-alink-direct-prg-do-until-return-branch-args-mixed",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[2]\r'
                'INT Y=[3]\r'
                'PROC ADD(A,B)\r'
                'RETURN A+B\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'DO\r'
                'IF X<Y THEN\r'
                'PrintIE(ADD(X,Y))\r'
                'PrintIE(W(X+1,Y+1))\r'
                'RETURN\r'
                'ELSE\r'
                'PrintE("BAD")\r'
                'FI\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD2")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(A,B)\r'
                'RETURN A+B\r'
            ),
        },
        "compile_modules": ["MAIN", "W"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x add 0 14\n"
                "x main 14 75\n"
                "b S3S2L2L3ar\n"
                "b e0dL0L1lhL0L1c0zL0p0aL1p1au0zrwe1vp2p3qtoe2r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "s BAD2\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "v x 2\n"
                "v y 3\n"
                "v a 0\n"
                "v b 0\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 14\n"
                "b S1S0L0L1ar\n"
                "v a 0\n"
                "v b 0\n"
                "k 0\n"
                "n w\n"
            ),
        },
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 95, 133, 2, 169, 19, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 173, 83, 19, 174, 84, 19, 141, 77, 19, 142, 78, 19, 173, 85,
                19, 174, 86, 19, 236, 78, 19, 144, 13, 208, 7, 205, 77, 19, 144, 6,
                240, 4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 229,
                18, 173, 83, 19, 174, 84, 19, 141, 77, 19, 142, 78, 19, 173, 85, 19,
                174, 86, 19, 32, 229, 18, 141, 77, 19, 142, 78, 19, 169, 81, 133, 2,
                169, 19, 133, 3, 160, 0, 162, 0, 173, 78, 19, 201, 39, 144, 29, 208,
                7, 173, 77, 19, 201, 16, 144, 20, 56, 173, 77, 19, 233, 16, 141, 77,
                19, 173, 78, 19, 233, 39, 141, 78, 19, 232, 208, 220, 224, 0, 208, 4,
                192, 0, 240, 14, 138, 24, 105, 48, 141, 81, 19, 162, 2, 32, 3, 207,
                160, 1, 162, 0, 173, 78, 19, 201, 3, 144, 29, 208, 7, 173, 77, 19,
                201, 232, 144, 20, 56, 173, 77, 19, 233, 232, 141, 77, 19, 173, 78, 19,
                233, 3, 141, 78, 19, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14,
                138, 24, 105, 48, 141, 81, 19, 162, 2, 32, 3, 207, 160, 1, 162, 0,
                173, 78, 19, 201, 0, 144, 29, 208, 7, 173, 77, 19, 201, 100, 144, 20,
                56, 173, 77, 19, 233, 100, 141, 77, 19, 173, 78, 19, 233, 0, 141, 78,
                19, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48,
                141, 81, 19, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 78, 19, 201,
                0, 144, 29, 208, 7, 173, 77, 19, 201, 10, 144, 20, 56, 173, 77, 19,
                233, 10, 141, 77, 19, 173, 78, 19, 233, 0, 141, 78, 19, 232, 208, 220,
                224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 81, 19, 162,
                2, 32, 3, 207, 160, 1, 173, 77, 19, 24, 105, 48, 141, 81, 19, 162,
                2, 32, 3, 207, 32, 6, 207, 173, 83, 19, 174, 84, 19, 141, 77, 19,
                142, 78, 19, 169, 1, 162, 0, 24, 109, 77, 19, 141, 77, 19, 138, 109,
                78, 19, 170, 173, 77, 19, 141, 77, 19, 142, 78, 19, 173, 85, 19, 174,
                86, 19, 141, 79, 19, 142, 80, 19, 169, 1, 162, 0, 24, 109, 79, 19,
                141, 79, 19, 138, 109, 80, 19, 170, 173, 79, 19, 72, 138, 72, 173, 77,
                19, 141, 79, 19, 173, 78, 19, 141, 80, 19, 104, 170, 104, 32, 25, 19,
                141, 77, 19, 142, 78, 19, 169, 81, 133, 2, 169, 19, 133, 3, 160, 0,
                162, 0, 173, 78, 19, 201, 39, 144, 29, 208, 7, 173, 77, 19, 201, 16,
                144, 20, 56, 173, 77, 19, 233, 16, 141, 77, 19, 173, 78, 19, 233, 39,
                141, 78, 19, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24,
                105, 48, 141, 81, 19, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 78,
                19, 201, 3, 144, 29, 208, 7, 173, 77, 19, 201, 232, 144, 20, 56, 173,
                77, 19, 233, 232, 141, 77, 19, 173, 78, 19, 233, 3, 141, 78, 19, 232,
                208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 81,
                19, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 78, 19, 201, 0, 144,
                29, 208, 7, 173, 77, 19, 201, 100, 144, 20, 56, 173, 77, 19, 233, 100,
                141, 77, 19, 173, 78, 19, 233, 0, 141, 78, 19, 232, 208, 220, 224, 0,
                208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 81, 19, 162, 2, 32,
                3, 207, 160, 1, 162, 0, 173, 78, 19, 201, 0, 144, 29, 208, 7, 173,
                77, 19, 201, 10, 144, 20, 56, 173, 77, 19, 233, 10, 141, 77, 19, 173,
                78, 19, 233, 0, 141, 78, 19, 232, 208, 220, 224, 0, 208, 4, 192, 0,
                240, 14, 138, 24, 105, 48, 141, 81, 19, 162, 2, 32, 3, 207, 160, 1,
                173, 77, 19, 24, 105, 48, 141, 81, 19, 162, 2, 32, 3, 207, 32, 6,
                207, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2,
                133, 3, 162, 2, 76, 15, 207, 141, 89, 19, 142, 90, 19, 173, 77, 19,
                174, 78, 19, 141, 87, 19, 142, 88, 19, 173, 87, 19, 174, 88, 19, 141,
                77, 19, 142, 78, 19, 173, 89, 19, 174, 90, 19, 24, 109, 77, 19, 141,
                77, 19, 138, 109, 78, 19, 170, 173, 77, 19, 96, 141, 99, 3, 142, 100,
                3, 173, 79, 19, 174, 80, 19, 141, 97, 3, 142, 98, 3, 173, 97, 3,
                174, 98, 3, 141, 79, 19, 142, 80, 19, 173, 99, 3, 174, 100, 3, 24,
                109, 79, 19, 141, 79, 19, 138, 109, 80, 19, 170, 173, 79, 19, 96, 0,
                0, 0, 0, 0, 0, 2, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 83, 84, 65, 82, 84, 0,
            ]
        ),
        "expected_console": "START\n5\n7\n",
    },
    "nested_do_until_return_external": {
        "out_fs_name": "harness-actc-alink-direct-prg-nested-do-until-return-external",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'DO\r'
                'DO\r'
                'W()\r'
                'RETURN\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("TOOL7")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 37\n"
                "b e0ddu0rp0p1qtop2p3qtoe1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 7\n"
                "b e0r\n"
                "s TOOL7\n"
                "k 2\n"
                "n w\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 37\n"
            "b e0ddu0rp0p1qtop2p3qtoe1r\n"
            "u w\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 64, 0, 0, 0, 1, 48, 0, 97, 48, 0, 73, 16,
                255, 69, 41, 0, 25, 38, 0, 17, 1, 0, 17, 1, 0, 22, 24, 6,
                0, 17, 1, 0, 17, 1, 0, 22, 24, 6, 0, 97, 54, 0, 73, 16, 255,
                73, 32, 255, 97, 58, 0, 73, 16, 255, 72, 83, 84, 65, 82, 84,
                0, 66, 65, 68, 0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 62, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 32, 41, 16, 141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3,
                169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 169, 68, 133, 2, 169,
                16, 133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0,
                83, 84, 65, 82, 84, 0, 84, 79, 79, 76, 55, 0,
            ]
        ),
        "expected_console": "START\nTOOL7\n",
    },
    "while_return_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-return-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'WHILE 1 = 1 DO\r'
                'W()\r'
                'RETURN\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 30\n"
                "b e0dp0p1qfu0rxe1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 30\n"
            "b e0dp0p1qfu0rxe1r\n"
            "u w\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 69, 0, 0, 0, 1, 51, 0, 97, 51, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 25, 0, 69, 34, 0, 25, 31,
                0, 25, 6, 0, 97, 57, 0, 73, 16, 255, 73, 32, 255, 97, 61, 0,
                73, 16, 255, 69, 44, 0, 72, 97, 65, 0, 73, 16, 255, 72, 83,
                84, 65, 82, 84, 0, 66, 65, 68, 0, 77, 73, 68, 0, 69, 78, 68,
                0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 109, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 105, 16, 142, 106, 16, 169, 1, 162, 0,
                236, 106, 16, 208, 5, 205, 105, 16, 240, 3, 76, 68, 16, 32, 68, 16,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 169, 115, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 32, 88, 16, 96, 169, 119, 133, 2, 169, 16,
                133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 83,
                84, 65, 82, 84, 0, 77, 73, 68, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "START\nMID\nEND\n",
    },
    "while_nested_do_until_return_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-nested-do-until-return-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'WHILE 1 = 1 DO\r'
                'DO\r'
                'W()\r'
                'RETURN\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 40\n"
                "b e0dp0p1qfdu0rp2p3qtoxe1r\n"
                "u w\n"
                "s START\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID\n"
                "k 2\n"
                "n w\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 40\n"
            "b e0dp0p1qfdu0rp2p3qtoxe1r\n"
            "u w\n"
            "s START\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 79, 0, 0, 0, 1, 61, 0, 97, 61, 0, 73, 16,
                255, 17, 1, 0, 17, 1, 0, 22, 24, 35, 0, 69, 44, 0, 25, 41,
                0, 17, 1, 0, 17, 1, 0, 22, 24, 16, 0, 25, 6, 0, 97, 67, 0,
                73, 16, 255, 73, 32, 255, 97, 71, 0, 73, 16, 255, 69, 54, 0,
                72, 97, 75, 0, 73, 16, 255, 72, 83, 84, 65, 82, 84, 0, 66,
                65, 68, 0, 77, 73, 68, 0, 69, 78, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 109, 133, 2, 169, 16, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 169, 1, 162, 0, 141, 105, 16, 142, 106, 16, 169, 1, 162, 0,
                236, 106, 16, 208, 5, 205, 105, 16, 240, 3, 76, 68, 16, 32, 68, 16,
                141, 209, 3, 142, 210, 3, 169, 165, 141, 208, 3, 169, 0, 133, 2, 133,
                3, 162, 2, 76, 15, 207, 169, 115, 133, 2, 169, 16, 133, 3, 162, 2,
                32, 3, 207, 32, 6, 207, 32, 88, 16, 96, 169, 119, 133, 2, 169, 16,
                133, 3, 162, 2, 32, 3, 207, 32, 6, 207, 96, 0, 0, 0, 0, 83,
                84, 65, 82, 84, 0, 77, 73, 68, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "START\nMID\nEND\n",
    },
    "while_nested_do_until_return_args_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-while-nested-do-until-return-args-transitive",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'INT X=[1]\r'
                'INT Y=[2]\r'
                'PROC MAIN()\r'
                'PrintE("START")\r'
                'WHILE X<3 DO\r'
                'DO\r'
                'IF W(X,Y)=3 THEN\r'
                'PrintIE(Q(X+3,Y+4))\r'
                'RETURN\r'
                'FI\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'X=X+1\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W(A,B)\r'
                'RETURN A+B\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q(A,B)\r'
                'RETURN Z(A,B)\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z(A,B)\r'
                'RETURN A+B\r'
            ),
        },
        "compile_modules": ["MAIN", "W", "Q", "Z"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 83\n"
                "b e0dL0p0lfdL0L1u0p1qhL0p2aL1p3au1zrvp4p5qtoL0p6aS0xe1r\n"
                "u w\n"
                "u q\n"
                "s START\n"
                "s BAD\n"
                "i 3\n"
                "i 3\n"
                "i 3\n"
                "i 4\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "v x 1\n"
                "v y 2\n"
                "k 6\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 14\n"
                "b S1S0L0L1ar\n"
                "v a 0\n"
                "v b 0\n"
                "k 0\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 16\n"
                "b S1S0L0L1u0r\n"
                "u z\n"
                "v a 0\n"
                "v b 0\n"
                "k 0\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 14\n"
                "b S1S0L0L1ar\n"
                "v a 0\n"
                "v b 0\n"
                "k 0\n"
                "n z\n"
            ),
        },
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 157, 0, 0, 0, 1, 131, 0, 97, 147, 0,
                73, 16, 255, 19, 131, 0, 17, 3, 0, 28, 24, 78, 0, 19, 131,
                0, 19, 133, 0, 69, 87, 0, 17, 3, 0, 22, 24, 55, 0, 19,
                131, 0, 17, 3, 0, 20, 19, 133, 0, 17, 4, 0, 20, 69, 101,
                0, 73, 49, 255, 25, 84, 0, 17, 1, 0, 17, 1, 0, 22, 24,
                16, 0, 19, 131, 0, 17, 1, 0, 20, 18, 131, 0, 25, 6, 0, 97,
                153, 0, 73, 16, 255, 73, 32, 255, 18, 137, 0, 18, 135, 0,
                19, 135, 0, 19, 137, 0, 20, 72, 18, 141, 0, 18, 139, 0,
                19, 139, 0, 19, 141, 0, 69, 117, 0, 72, 18, 145, 0, 18,
                143, 0, 19, 143, 0, 19, 145, 0, 20, 72, 1, 0, 2, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 83, 84, 65, 82, 84, 0, 66,
                65, 68, 0,
            ]
        ),
        "artifact_kind": "prg",
        "expected_prg": bytes(
            [
                0, 16, 169, 179, 133, 2, 169, 18, 133, 3, 162, 2, 32, 3, 207, 32,
                6, 207, 173, 163, 18, 174, 164, 18, 141, 157, 18, 142, 158, 18, 169,
                3, 162, 0, 236, 158, 18, 144, 13, 208, 7, 205, 157, 18, 144, 6, 240,
                4, 169, 1, 208, 2, 169, 0, 162, 0, 201, 0, 208, 3, 76, 251, 17,
                173, 163, 18, 174, 164, 18, 141, 157, 18, 142, 158, 18, 173, 165, 18, 174,
                166, 18, 72, 138, 72, 173, 157, 18, 141, 159, 18, 173, 158, 18, 141, 160,
                18, 104, 170, 104, 32, 251, 17, 141, 157, 18, 142, 158, 18, 169, 3, 162,
                0, 236, 158, 18, 208, 5, 205, 157, 18, 240, 3, 76, 251, 17, 173, 163,
                18, 174, 164, 18, 141, 157, 18, 142, 158, 18, 169, 3, 162, 0, 24, 109,
                157, 18, 141, 157, 18, 138, 109, 158, 18, 170, 173, 157, 18, 141, 157, 18,
                142, 158, 18, 173, 165, 18, 174, 166, 18, 141, 159, 18, 142, 160, 18, 169,
                4, 162, 0, 24, 109, 159, 18, 141, 159, 18, 138, 109, 160, 18, 170, 173,
                159, 18, 72, 138, 72, 173, 157, 18, 141, 159, 18, 173, 158, 18, 141, 160,
                18, 104, 170, 104, 32, 47, 18, 141, 157, 18, 142, 158, 18, 169, 161, 133,
                2, 169, 18, 133, 3, 160, 0, 162, 0, 173, 158, 18, 201, 39, 144, 29,
                208, 7, 173, 157, 18, 201, 16, 144, 20, 56, 173, 157, 18, 233, 16, 141,
                157, 18, 173, 158, 18, 233, 39, 141, 158, 18, 232, 208, 220, 224, 0, 208,
                4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 161, 18, 162, 2, 32, 3,
                207, 160, 1, 162, 0, 173, 158, 18, 201, 3, 144, 29, 208, 7, 173, 157,
                18, 201, 232, 144, 20, 56, 173, 157, 18, 233, 232, 141, 157, 18, 173, 158,
                18, 233, 3, 141, 158, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240,
                14, 138, 24, 105, 48, 141, 161, 18, 162, 2, 32, 3, 207, 160, 1, 162,
                0, 173, 158, 18, 201, 0, 144, 29, 208, 7, 173, 157, 18, 201, 100, 144,
                20, 56, 173, 157, 18, 233, 100, 141, 157, 18, 173, 158, 18, 233, 0, 141,
                158, 18, 232, 208, 220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105,
                48, 141, 161, 18, 162, 2, 32, 3, 207, 160, 1, 162, 0, 173, 158, 18,
                201, 0, 144, 29, 208, 7, 173, 157, 18, 201, 10, 144, 20, 56, 173, 157,
                18, 233, 10, 141, 157, 18, 173, 158, 18, 233, 0, 141, 158, 18, 232, 208,
                220, 224, 0, 208, 4, 192, 0, 240, 14, 138, 24, 105, 48, 141, 161, 18,
                162, 2, 32, 3, 207, 160, 1, 173, 157, 18, 24, 105, 48, 141, 161, 18,
                162, 2, 32, 3, 207, 32, 6, 207, 141, 209, 3, 142, 210, 3, 169, 165,
                141, 208, 3, 169, 0, 133, 2, 133, 3, 162, 2, 76, 15, 207, 141, 175,
                2, 142, 176, 2, 173, 159, 18, 174, 160, 18, 141, 173, 2, 142, 174, 2,
                173, 173, 2, 174, 174, 2, 141, 159, 18, 142, 160, 18, 173, 175, 2, 174,
                176, 2, 24, 109, 159, 18, 141, 159, 18, 138, 109, 160, 18, 170, 173, 159,
                18, 96, 141, 179, 2, 142, 180, 2, 173, 159, 18, 174, 160, 18, 141, 177,
                2, 142, 178, 2, 173, 177, 2, 174, 178, 2, 141, 159, 18, 142, 160, 18,
                173, 179, 2, 174, 180, 2, 72, 138, 72, 173, 157, 18, 141, 159, 18, 173,
                158, 18, 141, 160, 18, 104, 170, 104, 32, 105, 18, 96, 141, 183, 2, 142,
                184, 2, 173, 159, 18, 174, 160, 18, 141, 181, 2, 142, 182, 2, 173, 181,
                2, 174, 182, 2, 141, 159, 18, 142, 160, 18, 173, 183, 2, 174, 184, 2,
                24, 109, 159, 18, 141, 159, 18, 138, 109, 160, 18, 170, 173, 159, 18, 96,
                0, 0, 0, 0, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 83, 84, 65, 82, 84, 0,
            ]
        ),
        "expected_console": "START\n10\n",
    },
    "dense_mixed_nested_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-dense-mixed-nested-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'DO\r'
                'WHILE 1 = 0 DO\r'
                'W()\r'
                'PrintE("BAD")\r'
                'OD\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'PrintE("M")\r'
                'PrintE("N")\r'
                'PrintE("O")\r'
                'PrintE("P")\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 132\n"
                "b ddp0p1qfu0e0xu1e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFeGp2p3qtor\n"
                "u w\n"
                "u q\n"
                "s BAD\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s M\n"
                "s N\n"
                "s O\n"
                "s P\n"
                "i 1\n"
                "i 0\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 132\n"
            "b ddp0p1qfu0e0xu1e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFeGp2p3qtor\n"
            "u w\n"
            "u q\n"
            "s BAD\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "i 1\n"
            "i 0\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d9e118e9f11a900a200ec9f11d005cd9e11f0034c3110206511a9a28502a9118503a2022003cf2006cf4c0010207911a9a68502a9118503a2022003cf2006cfa9a88502a9118503a2022003cf2006cfa9aa8502a9118503a2022003cf2006cfa9ac8502a9118503a2022003cf2006cfa9ae8502a9118503a2022003cf2006cfa9b08502a9118503a2022003cf2006cfa9b28502a9118503a2022003cf2006cfa9b48502a9118503a2022003cf2006cfa9b68502a9118503a2022003cf2006cfa9b88502a9118503a2022003cf2006cfa9ba8502a9118503a2022003cf2006cfa9bc8502a9118503a2022003cf2006cfa9be8502a9118503a2022003cf2006cfa9c08502a9118503a2022003cf2006cfa9c28502a9118503a2022003cf2006cfa9c48502a9118503a2022003cf2006cfa901a2008d9e118e9f11a901a200ec9f11d005cd9e11f0034c00108dd1038ed203a9a58dd003a90085028503a2024c0fcfa9c68502a9118503a2022003cf2006cf208d1160a9cb8502a9118503a2022003cf2006cf208d1160a9d08502a9118503a2022003cf2006cf6000000000424144004100420043004400450046004700480049004a004b004c004d004e004f0050004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 211, 0, 0, 0, 1, 161, 0, 17, 1, 0,
                17, 0, 0, 22, 24, 22, 0, 69, 134, 0, 97, 161, 0, 73, 16,
                255, 25, 0, 0, 69, 144, 0, 97, 165, 0, 73, 16, 255, 97,
                167, 0, 73, 16, 255, 97, 169, 0, 73, 16, 255, 97, 171, 0,
                73, 16, 255, 97, 173, 0, 73, 16, 255, 97, 175, 0, 73, 16,
                255, 97, 177, 0, 73, 16, 255, 97, 179, 0, 73, 16, 255, 97,
                181, 0, 73, 16, 255, 97, 183, 0, 73, 16, 255, 97, 185, 0,
                73, 16, 255, 97, 187, 0, 73, 16, 255, 97, 189, 0, 73, 16,
                255, 97, 191, 0, 73, 16, 255, 97, 193, 0, 73, 16, 255, 97,
                195, 0, 73, 16, 255, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0, 73,
                32, 255, 97, 197, 0, 73, 16, 255, 69, 154, 0, 72, 97, 202,
                0, 73, 16, 255, 69, 154, 0, 72, 97, 207, 0, 73, 16, 255,
                72, 66, 65, 68, 0, 65, 0, 66, 0, 67, 0, 68, 0, 69, 0, 70,
                0, 71, 0, 72, 0, 73, 0, 74, 0, 75, 0, 76, 0, 77, 0, 78,
                0, 79, 0, 80, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69,
                78, 68, 0,
            ]
        ),
        "expected_console": "MID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "dense_return_nested_mixed_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-dense-return-nested-mixed-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'DO\r'
                'WHILE 1 = 1 DO\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'PrintE("M")\r'
                'PrintE("N")\r'
                'PrintE("O")\r'
                'PrintE("P")\r'
                'RETURN\r'
                'OD\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 133\n"
                "b ddp0p1qfu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrxp2p3qtoeGr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s M\n"
                "s N\n"
                "s O\n"
                "s P\n"
                "s BAD\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 133\n"
            "b ddp0p1qfu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrxp2p3qtoeGr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "s BAD\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d70118e7111a901a200ec7111d005cd7011f0034c3711203711204b11a9748502a9118503a2022003cf2006cfa9768502a9118503a2022003cf2006cfa9788502a9118503a2022003cf2006cfa97a8502a9118503a2022003cf2006cfa97c8502a9118503a2022003cf2006cfa97e8502a9118503a2022003cf2006cfa9808502a9118503a2022003cf2006cfa9828502a9118503a2022003cf2006cfa9848502a9118503a2022003cf2006cfa9868502a9118503a2022003cf2006cfa9888502a9118503a2022003cf2006cfa98a8502a9118503a2022003cf2006cfa98c8502a9118503a2022003cf2006cfa98e8502a9118503a2022003cf2006cfa9908502a9118503a2022003cf2006cfa9928502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9948502a9118503a2022003cf2006cf205f1160a9998502a9118503a2022003cf2006cf205f1160a99e8502a9118503a2022003cf2006cf60000000004100420043004400450046004700480049004a004b004c004d004e004f0050004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 214, 0, 0, 0, 1, 164, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 118, 0, 69, 137, 0, 69, 147, 0, 97,
                164, 0, 73, 16, 255, 97, 166, 0, 73, 16, 255, 97, 168,
                0, 73, 16, 255, 97, 170, 0, 73, 16, 255, 97, 172, 0, 73,
                16, 255, 97, 174, 0, 73, 16, 255, 97, 176, 0, 73, 16,
                255, 97, 178, 0, 73, 16, 255, 97, 180, 0, 73, 16, 255,
                97, 182, 0, 73, 16, 255, 97, 184, 0, 73, 16, 255, 97,
                186, 0, 73, 16, 255, 97, 188, 0, 73, 16, 255, 97, 190,
                0, 73, 16, 255, 97, 192, 0, 73, 16, 255, 97, 194, 0, 73,
                16, 255, 25, 134, 0, 25, 0, 0, 17, 1, 0, 17, 1, 0, 22,
                24, 0, 0, 97, 196, 0, 73, 16, 255, 73, 32, 255, 97, 200,
                0, 73, 16, 255, 69, 157, 0, 72, 97, 205, 0, 73, 16, 255,
                69, 157, 0, 72, 97, 210, 0, 73, 16, 255, 72, 65, 0, 66,
                0, 67, 0, 68, 0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74,
                0, 75, 0, 76, 0, 77, 0, 78, 0, 79, 0, 80, 0, 66, 65, 68,
                0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69, 78, 68, 0,
            ]
        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "dense_return_branch_nested_mixed_shared_transitive": {
        "out_fs_name": "harness-actc-alink-direct-prg-dense-return-branch-nested-mixed-shared-transitive",
        "artifact_kind": "prg",
        "sources": {
            "MAIN": (
                'MODULE MAIN\r'
                'PROC MAIN()\r'
                'DO\r'
                'WHILE 1 = 1 DO\r'
                'IF 1 = 1 THEN\r'
                'W()\r'
                'Q()\r'
                'PrintE("A")\r'
                'PrintE("B")\r'
                'PrintE("C")\r'
                'PrintE("D")\r'
                'PrintE("E")\r'
                'PrintE("F")\r'
                'PrintE("G")\r'
                'PrintE("H")\r'
                'PrintE("I")\r'
                'PrintE("J")\r'
                'PrintE("K")\r'
                'PrintE("L")\r'
                'PrintE("M")\r'
                'PrintE("N")\r'
                'PrintE("O")\r'
                'PrintE("P")\r'
                'RETURN\r'
                'ELSE\r'
                'PrintE("BAD1")\r'
                'FI\r'
                'OD\r'
                'UNTIL 1 = 1\r'
                'OD\r'
                'PrintE("BAD2")\r'
                'RETURN\r'
            ),
            "W": (
                'MODULE W\r'
                'PROC W()\r'
                'PrintE("MID1")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Q": (
                'MODULE Q\r'
                'PROC Q()\r'
                'PrintE("MID2")\r'
                'Z()\r'
                'RETURN\r'
            ),
            "Z": (
                'MODULE Z\r'
                'PROC Z()\r'
                'PrintE("END")\r'
                'RETURN\r'
            ),
        },
        "compile_modules": ["Z", "W", "Q", "MAIN"],
        "expected_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 152\n"
                "b ddp0p1qfp2p3qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrweGvxp4p5qtoeHr\n"
                "u w\n"
                "u q\n"
                "s A\n"
                "s B\n"
                "s C\n"
                "s D\n"
                "s E\n"
                "s F\n"
                "s G\n"
                "s H\n"
                "s I\n"
                "s J\n"
                "s K\n"
                "s L\n"
                "s M\n"
                "s N\n"
                "s O\n"
                "s P\n"
                "s BAD1\n"
                "s BAD2\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "i 1\n"
                "k 2\n"
                "n main\n"
            ),
            "W": (
                "AVO1\n"
                "x w 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID1\n"
                "k 2\n"
                "n w\n"
            ),
            "Q": (
                "AVO1\n"
                "x q 0 10\n"
                "b e0u0r\n"
                "u z\n"
                "s MID2\n"
                "k 2\n"
                "n q\n"
            ),
            "Z": (
                "AVO1\n"
                "x z 0 7\n"
                "b e0r\n"
                "s END\n"
                "k 2\n"
                "n z\n"
            ),
        },
        "expected_avo": (
            "AVO1\n"
            "x main 0 152\n"
            "b ddp0p1qfp2p3qhu0u1e0e1e2e3e4e5e6e7e8e9eAeBeCeDeEeFrweGvxp4p5qtoeHr\n"
            "u w\n"
            "u q\n"
            "s A\n"
            "s B\n"
            "s C\n"
            "s D\n"
            "s E\n"
            "s F\n"
            "s G\n"
            "s H\n"
            "s I\n"
            "s J\n"
            "s K\n"
            "s L\n"
            "s M\n"
            "s N\n"
            "s O\n"
            "s P\n"
            "s BAD1\n"
            "s BAD2\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "i 1\n"
            "k 2\n"
            "n main\n"
        ),
        "expected_prg": bytes.fromhex(
            "0010a901a2008d8b118e8c11a901a200ec8c11d005cd8b11f0034c5211a901a2008d8b118e8c11a901a200ec8c11d005cd8b11f0034c5211205211206611a98f8502a9118503a2022003cf2006cfa9918502a9118503a2022003cf2006cfa9938502a9118503a2022003cf2006cfa9958502a9118503a2022003cf2006cfa9978502a9118503a2022003cf2006cfa9998502a9118503a2022003cf2006cfa99b8502a9118503a2022003cf2006cfa99d8502a9118503a2022003cf2006cfa99f8502a9118503a2022003cf2006cfa9a18502a9118503a2022003cf2006cfa9a38502a9118503a2022003cf2006cfa9a58502a9118503a2022003cf2006cfa9a78502a9118503a2022003cf2006cfa9a98502a9118503a2022003cf2006cfa9ab8502a9118503a2022003cf2006cfa9ad8502a9118503a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcfa9af8502a9118503a2022003cf2006cf207a1160a9b48502a9118503a2022003cf2006cf207a1160a9b98502a9118503a2022003cf2006cf60000000004100420043004400450046004700480049004a004b004c004d004e004f0050004d494431004d49443200454e4400"
        ),
        "expected_avm": bytes(
            [
                65, 86, 77, 49, 2, 239, 0, 0, 0, 1, 183, 0, 17, 1, 0,
                17, 1, 0, 22, 24, 137, 0, 17, 1, 0, 17, 1, 0, 22, 24, 128,
                0, 69, 156, 0, 69, 166, 0, 97, 183, 0, 73, 16, 255, 97,
                185, 0, 73, 16, 255, 97, 187, 0, 73, 16, 255, 97, 189, 0,
                73, 16, 255, 97, 191, 0, 73, 16, 255, 97, 193, 0, 73, 16,
                255, 97, 195, 0, 73, 16, 255, 97, 197, 0, 73, 16, 255, 97,
                199, 0, 73, 16, 255, 97, 201, 0, 73, 16, 255, 97, 203, 0,
                73, 16, 255, 97, 205, 0, 73, 16, 255, 97, 207, 0, 73, 16,
                255, 97, 209, 0, 73, 16, 255, 97, 211, 0, 73, 16, 255, 97,
                213, 0, 73, 16, 255, 25, 153, 0, 25, 134, 0, 97, 215, 0,
                73, 16, 255, 25, 0, 0, 17, 1, 0, 17, 1, 0, 22, 24, 0, 0,
                97, 220, 0, 73, 16, 255, 73, 32, 255, 97, 225, 0, 73, 16,
                255, 69, 176, 0, 72, 97, 230, 0, 73, 16, 255, 69, 176, 0,
                72, 97, 235, 0, 73, 16, 255, 72, 65, 0, 66, 0, 67, 0, 68,
                0, 69, 0, 70, 0, 71, 0, 72, 0, 73, 0, 74, 0, 75, 0, 76,
                0, 77, 0, 78, 0, 79, 0, 80, 0, 66, 65, 68, 49, 0, 66, 65,
                68, 50, 0, 77, 73, 68, 49, 0, 77, 73, 68, 50, 0, 69, 78,
                68, 0,
            ]
        ),
        "expected_console": "MID1\nEND\nMID2\nEND\nA\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nO\nP\n",
    },
    "dup_basic": {
        "out_fs_name": "harness-actc-alink-direct-prg-dup-basic",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 8\n"
                "b p0Dazr\n"
                "i 1\n"
                "k 6\n"
                "n main\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010a901a2008d40118e4111186d40118d40118a6d4111aaad40118d40118e4111a9448502a9118503a000a200ad4111c927901dd007ad4011c910901438ad4011e9108d4011ad4111e9278d4111e8d0dce000d004c000f00e8a1869308d4411a2022003cfa001a200ad4111c903901dd007ad4011c9e8901438ad4011e9e88d4011ad4111e9038d4111e8d0dce000d004c000f00e8a1869308d4411a2022003cfa001a200ad4111c900901dd007ad4011c964901438ad4011e9648d4011ad4111e9008d4111e8d0dce000d004c000f00e8a1869308d4411a2022003cfa001a200ad4111c900901dd007ad4011c90a901438ad4011e90a8d4011ad4111e9008d4111e8d0dce000d004c000f00e8a1869308d4411a2022003cfa001ad40111869308d4411a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf000000000000"
        ),
        "expected_console": "2\n",
    },
    "drop_depth4": {
        "out_fs_name": "harness-actc-alink-direct-prg-drop-depth4",
        "artifact_kind": "prg",
        "source": 'MODULE MAIN\rPROC MAIN()\rRETURN\r',
        "compile_modules": [],
        "expected_objects": {},
        "seed_project_objects": {
            "MAIN": (
                "AVO1\n"
                "x main 0 22\n"
                "b p0p1p2p3Kaazr\n"
                "i 1\n"
                "i 2\n"
                "i 3\n"
                "i 4\n"
                "k 6\n"
                "n main\n"
            ),
        },
        "expected_prg": bytes.fromhex(
            "0010a901a2008d6d118e6e11a902a2008d6f118e7011a903a2008d71118e7211a904a200ad7111ae7211186d6f118d6f118a6d7011aaad6f11186d6d118d6d118a6d6e11aaad6d118d6d118e6e11a9738502a9118503a000a200ad6e11c927901dd007ad6d11c910901438ad6d11e9108d6d11ad6e11e9278d6e11e8d0dce000d004c000f00e8a1869308d7311a2022003cfa001a200ad6e11c903901dd007ad6d11c9e8901438ad6d11e9e88d6d11ad6e11e9038d6e11e8d0dce000d004c000f00e8a1869308d7311a2022003cfa001a200ad6e11c900901dd007ad6d11c964901438ad6d11e9648d6d11ad6e11e9008d6e11e8d0dce000d004c000f00e8a1869308d7311a2022003cfa001a200ad6e11c900901dd007ad6d11c90a901438ad6d11e90a8d6d11ad6e11e9008d6e11e8d0dce000d004c000f00e8a1869308d7311a2022003cfa001ad6d111869308d7311a2022003cf2006cf8dd1038ed203a9a58dd003a90085028503a2024c0fcf0000000000000000"
        ),
        "expected_console": "6\n",
    },
}


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        text=False,
        capture_output=True,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=stdout,
            stderr=stderr,
        )
    return subprocess.CompletedProcess(result.args, result.returncode, stdout, stderr)


def build_current_tools() -> None:
    run([str(ROOT / "tools" / "build_tool_abi_harness.sh")], cwd=ROOT)
    run([str(ROOT / "tools" / "build_actc_harness_udos.sh")], cwd=ROOT)
    # Use the production ALINK build here. The harness-specific ALINK build is
    # currently blocked by unrelated AVMRUN overlay build issues, while the
    # additive scenarios only need a working ALINK.PRG plus path-aware harness
    # verification.
    run([str(ROOT / "tools" / "build_alink_udos.sh")], cwd=ROOT)


def scenario_sources(scenario: dict) -> dict[str, str]:
    if "sources" in scenario:
        return {name.upper(): source for name, source in scenario["sources"].items()}
    return {"MAIN": scenario["source"]}


def prepare_workspace(base_fs: Path, out_fs: Path, scenario: dict) -> Path:
    project_root = out_fs / "IMAGES" / "ACTION.DNP" / "PROJ3"
    compile_modules = list(scenario_sources(scenario))
    shutil.rmtree(out_fs, ignore_errors=True)
    shutil.copytree(base_fs, out_fs)
    image_root = out_fs / "IMAGES" / "ACTION.DNP"
    for helper_name in ("RT_PRINT_STD_HELPER.BIN", "RT_PRINT_F_HELPER.BIN"):
        helper_src = ROOT / "build" / "udos_tools" / helper_name
        if helper_src.is_file():
            shutil.copy2(helper_src, image_root / helper_name)
    manifest = "ACTION PROJECT\r" + "".join(f"{module}.ACT\r" for module in scenario_sources(scenario))
    (project_root / "ACTION.PROJ").write_text(manifest, encoding="ascii")
    for module, source in scenario_sources(scenario).items():
        (project_root / "src" / f"{module.lower()}.act").write_text(source, encoding="ascii")
    stale_paths = [
        project_root / "bin" / "MAIN.AVM",
        project_root / "bin" / "main.avm",
        project_root / "bin" / "MAIN.PRG",
        project_root / "bin" / "main.prg",
        project_root / "MAIN.AVM",
        project_root / "main.avm",
        project_root / "MAIN.PRG",
        project_root / "main.prg",
    ]
    for module in compile_modules:
        stale_paths.extend(
            [
                project_root / "obj" / f"{module}.OBJ",
                project_root / "obj" / f"{module.lower()}.obj",
                project_root / f"{module}.OBJ",
                project_root / f"{module.lower()}.obj",
            ]
        )
    for stale in stale_paths:
        if stale.exists():
            stale.unlink()
    for module, object_text in scenario.get("seed_project_objects", {}).items():
        object_dir = project_root / "obj"
        object_dir.mkdir(exist_ok=True)
        (object_dir / f"{module.upper()}.OBJ").write_text(object_text, encoding="ascii")
    for module, object_text in scenario.get("seed_library_objects", {}).items():
        library_dir = project_root / "lib"
        library_dir.mkdir(exist_ok=True)
        (library_dir / f"{module.upper()}.OBJ").write_text(object_text, encoding="ascii")
    if scenario.get("use_udos_runtime_modules"):
        library_dir = project_root / "lib"
        library_dir.mkdir(exist_ok=True)
        for pattern in ("*.obj", "*.avo"):
            for runtime_object in sorted(UDOS_RUNTIME_MODULES.glob(pattern)):
                shutil.copy2(runtime_object, library_dir / runtime_object.name.upper())
    return project_root


def run_harness(prg: Path, workspace: Path, cmdline: str, labels: Path, extra: list[str]) -> dict:
    cmd = [
        str(HARNESS),
        "--prg",
        str(prg),
        "--workspace",
        str(workspace),
        "--cmdline",
        cmdline,
        "--services-inc",
        str(SERVICES_INC),
        "--labels",
        str(labels),
        "--max-steps",
        "4000000",
        *extra,
    ]
    result = run(cmd, cwd=ROOT)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"failed to decode harness output for {prg.name}:\n{result.stdout}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def find_last_op(summary: dict, kind: str) -> dict:
    matches = [op for op in summary.get("ops", []) if op.get("kind") == kind]
    require(bool(matches), f"missing {kind!r} operation in harness summary")
    return matches[-1]


def verify_actc(project_root: Path, summary: dict, module: str, expected_avo: str) -> None:
    require(summary["exit_status"] == 0, f"ACTC exited nonzero: {summary['exit_status']}")
    save_op = find_last_op(summary, "save")
    require(save_op["path"] == f"OBJ/{module}.OBJ", f"unexpected ACTC save path: {save_op['path']!r}")
    require(save_op["actual_len"] == len(expected_avo.encode("ascii")), f"unexpected ACTC object size: {save_op['actual_len']}")
    output_path = project_root / "obj" / f"{module}.OBJ"
    require(output_path.is_file(), f"missing ACTC output: {output_path}")
    text = output_path.read_text(encoding="ascii", errors="replace")
    require(text == expected_avo, f"unexpected ACTC object text:\n{text}")


def scenario_artifact_kind(scenario: dict) -> str:
    artifact_kind = scenario.get("artifact_kind", "avm")
    require(artifact_kind in ("avm", "prg"), f"unsupported artifact kind: {artifact_kind!r}")
    return artifact_kind


def verify_alink(project_root: Path, summary: dict, scenario: dict) -> tuple[str, Path]:
    require(summary["exit_status"] == 0, f"ALINK exited nonzero: {summary['exit_status']}")
    artifact_kind = scenario_artifact_kind(scenario)
    if artifact_kind == "prg":
        expected_prg = scenario.get("expected_prg")
        require(expected_prg is not None, "missing expected PRG bytes for direct-PRG scenario")
        save_ops = [op for op in summary.get("ops", []) if op.get("kind") == "save"]
        if save_ops:
            save_op = save_ops[-1]
            require(save_op["path"] == "BIN/MAIN.PRG", f"unexpected ALINK save path: {save_op['path']!r}")
            require(save_op["actual_len"] == len(expected_prg), f"unexpected ALINK PRG size: {save_op['actual_len']}")
        output_path = project_root / "bin" / "MAIN.PRG"
        require(output_path.is_file(), f"missing ALINK output: {output_path}")
        data = output_path.read_bytes()
        require(data == expected_prg, f"unexpected ALINK PRG bytes: {list(data)}")
        require(not (project_root / "bin" / "MAIN.AVM").exists(), "unexpected ALINK AVM output for helper-free direct PRG scenario")
        return "prg", output_path
    expected_avm = normalize_expected_avm_for_linked_printstd(scenario["expected_avm"])
    save_ops = [op for op in summary.get("ops", []) if op.get("kind") == "save"]
    if save_ops:
        save_op = next((op for op in save_ops if op.get("path") == "BIN/MAIN.AVM"), None)
        require(save_op is not None, f"missing ALINK AVM save op in summary: {save_ops!r}")
        require(save_op["path"] == "BIN/MAIN.AVM", f"unexpected ALINK save path: {save_op['path']!r}")
        require(save_op["actual_len"] == len(expected_avm), f"unexpected ALINK image size: {save_op['actual_len']}")
    else:
        open_ops: list[dict] = []
        close_ops: list[dict] = []
        chunk_ops: list[dict] = []
        active_stream_path = ""
        for op in summary.get("ops", []):
            kind = op.get("kind")
            if kind == "wopn":
                active_stream_path = op.get("path", "")
                if active_stream_path == "BIN/MAIN.AVM":
                    open_ops.append(op)
                continue
            if kind == "wcls":
                if active_stream_path == "BIN/MAIN.AVM":
                    close_ops.append(op)
                active_stream_path = ""
                continue
            if kind == "wrte" and active_stream_path == "BIN/MAIN.AVM":
                chunk_ops.append(op)
        require(bool(open_ops), "missing streamed write-begin operation in harness summary")
        require(bool(chunk_ops), "missing streamed write-chunk operation in harness summary")
        require(bool(close_ops), "missing streamed write-close operation in harness summary")
        total_len = sum(op.get("actual_len", 0) for op in chunk_ops)
        require(total_len == len(expected_avm), f"unexpected ALINK streamed image size: {total_len}")
    output_path = project_root / "bin" / "MAIN.AVM"
    require(output_path.is_file(), f"missing ALINK output: {output_path}")
    data = output_path.read_bytes()
    require(
        canonicalize_helper_flag_for_compare(data) == canonicalize_helper_flag_for_compare(expected_avm),
        f"unexpected ALINK bytes: {list(data)}",
    )
    return "avm", output_path


def normalize_expected_avm_for_linked_printstd(expected_avm: bytes) -> bytes:
    data = bytearray(expected_avm)
    replaced = False
    uses_printstd = False
    if len(data) >= 12:
        payload_len = data[5] | (data[6] << 8)
        payload = data[12 : 12 + payload_len]
        i = 0
        while i + 2 < len(payload):
            if payload[i] == 0x49 and payload[i + 1] in (0x00, 0x10, 0x30, 0x31) and payload[i + 2] in (0xFE, 0xFF):
                uses_printstd = True
                break
            i += 1
    i = 0
    while i + 2 < len(data):
        if data[i] == 0x49 and data[i + 2] == 0xFF and data[i + 1] in (0x00, 0x10, 0x30, 0x31):
            data[i + 2] = 0xFE
            replaced = True
            i += 3
            continue
        i += 1
    if replaced and len(data) > 9:
        data[9] |= 0x02
    if not uses_printstd:
        return bytes(data)
    helper_blob = (ROOT / "build" / "udos_tools" / "RT_PRINT_STD_HELPER.BIN").read_bytes()
    payload_len = data[5] | (data[6] << 8)
    trailer_offset = 12 + payload_len
    trailer = data[trailer_offset:]
    if trailer[:4] != b"AVH1":
        trailer = b"AVH1" + bytes([1, 2, len(helper_blob) & 0xFF, (len(helper_blob) >> 8) & 0xFF]) + helper_blob
        return bytes(data[:trailer_offset] + trailer)
    count = trailer[4]
    pos = 5
    entries: list[tuple[int, bytes]] = []
    for _ in range(count):
        if pos + 3 > len(trailer):
            raise RuntimeError("invalid expected AVM helper trailer")
        kind = trailer[pos]
        helper_len = trailer[pos + 1] | (trailer[pos + 2] << 8)
        pos += 3
        if pos + helper_len > len(trailer):
            raise RuntimeError("invalid expected AVM helper payload")
        entries.append((kind, bytes(trailer[pos : pos + helper_len])))
        pos += helper_len
    if any(kind == 2 for kind, _ in entries):
        return bytes(data)
    new_trailer = bytearray(b"AVH1")
    new_trailer.append(count + 1)
    for kind, blob in entries:
        new_trailer.append(kind)
        new_trailer.append(len(blob) & 0xFF)
        new_trailer.append((len(blob) >> 8) & 0xFF)
        new_trailer.extend(blob)
    new_trailer.append(2)
    new_trailer.append(len(helper_blob) & 0xFF)
    new_trailer.append((len(helper_blob) >> 8) & 0xFF)
    new_trailer.extend(helper_blob)
    return bytes(data[:trailer_offset] + new_trailer)


def canonicalize_helper_flag_for_compare(data: bytes) -> bytes:
    if len(data) < 12:
        return data
    payload_len = data[5] | (data[6] << 8)
    trailer_offset = 12 + payload_len
    if trailer_offset + 4 > len(data):
        return data
    if data[trailer_offset : trailer_offset + 4] != b"AVH1":
        return data
    normalized = bytearray(data)
    normalized[9] &= 0xFD
    return bytes(normalized)


def verify_avmrun(summary: dict, expected_console: str) -> None:
    require(summary["exit_status"] == 0, f"AVMRUN exited nonzero: {summary['exit_status']}")
    require(summary.get("console", "") == expected_console, f"unexpected AVMRUN console: {summary.get('console', '')!r}")


def run_direct_prg(project_root: Path, prg_path: Path) -> dict:
    result = subprocess.run(
        [
            str(HARNESS),
            "--prg",
            str(prg_path),
            "--workspace",
            str(project_root),
            "--cmdline",
            "",
            "--services-inc",
            str(SERVICES_INC),
            "--entry-addr",
            f"0x{DIRECT_PRG_ENTRY_ADDR:04X}",
            "--max-steps",
            "12000000",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"failed to decode harness output for {prg_path.name}:\n{result.stdout}") from exc
    require(summary["exit_status"] == 0, f"direct PRG exited nonzero: {summary['exit_status']}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run named ACTC -> ALINK additive harness proofs")
    parser.add_argument("--base-fs", type=Path, default=DEFAULT_BASE_FS)
    parser.add_argument("--out-fs", type=Path)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="additive")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep-workspace", action="store_true")
    args = parser.parse_args()
    scenario = SCENARIOS[args.scenario]

    if not args.base_fs.is_dir():
        raise RuntimeError(f"missing base fs tree: {args.base_fs}")

    if not args.skip_build:
        build_current_tools()

    out_fs = args.out_fs if args.out_fs is not None else (UDOS_ROOT / "build" / scenario["out_fs_name"])
    project_root = prepare_workspace(args.base_fs, out_fs, scenario)
    compile_modules = [module.upper() for module in scenario.get("compile_modules", ["MAIN"])]
    raw_expected_objects = scenario["expected_objects"] if "expected_objects" in scenario else {"MAIN": scenario["expected_avo"]}
    expected_objects = {
        module.upper(): expected
        for module, expected in raw_expected_objects.items()
    }

    for module in compile_modules:
        require(module in expected_objects, f"missing expected object text for {module}")
        actc = run_harness(
            ACTC_PRG,
            project_root,
            module,
            ACTC_LABELS,
            ["--op-dump-cstr", "target_path:32", "--op-dump-cstr", "content_buffer:256"],
        )
        verify_actc(project_root, actc, module, expected_objects[module])

    alink = run_harness(
        ALINK_PRG,
        project_root,
        "MAIN",
        ALINK_LABELS,
        ["--op-dump-cstr", "target_path:32", "--op-dump-cstr", "binary_target_path:32", "--op-dump", "content_buffer:80"],
    )
    artifact_kind, artifact_path = verify_alink(project_root, alink, scenario)

    if artifact_kind == "prg":
        runtime_kind = "direct_prg"
        runtime = run_direct_prg(project_root, artifact_path)
        require(runtime.get("console", "") == scenario["expected_console"], f"unexpected direct PRG console: {runtime.get('console', '')!r}")
    else:
        runtime_kind = "avmrunc"
        runtime = run_harness(
            AVMRUNC_PRG,
            project_root,
            "BIN/MAIN.AVM",
            AVMRUNC_LABELS,
            [],
        )
        verify_avmrun(runtime, scenario["expected_console"])

    summary = {
        "scenario": args.scenario,
        "workspace": str(project_root),
        "actc_object_path": str(project_root / "obj" / "MAIN.OBJ"),
        "artifact_kind": artifact_kind,
        "alink_artifact_path": str(artifact_path),
        "alink_image_path": str(artifact_path),
        "runtime_kind": runtime_kind,
        "runtime_console": runtime.get("console", ""),
        "runtime_exit_status": runtime["exit_status"],
        "avmrunc_console": runtime.get("console", "") if runtime_kind == "avmrunc" else "",
    }
    print(json.dumps(summary, indent=2))

    if not args.keep_workspace:
        shutil.rmtree(out_fs, ignore_errors=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
