from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.export_idun_workspace import LINUX_TOOL_NAMES


class TestAlpinePackaging(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        (self.root / "build").mkdir(exist_ok=True)

    @staticmethod
    def write_aarch64_elf(path: Path, machine: int = 183) -> None:
        header = bytearray(64)
        header[:4] = b"\x7fELF"
        header[4] = 2
        header[5] = 1
        header[6] = 1
        header[16:18] = (3).to_bytes(2, "little")
        header[18:20] = machine.to_bytes(2, "little")
        header[20:24] = (1).to_bytes(4, "little")
        path.write_bytes(header)
        path.chmod(0o755)

    def make_fixture(self, base: Path, machine: int = 183) -> tuple[Path, Path]:
        export = base / "export"
        tools = base / "tools"
        export.mkdir()
        tools.mkdir()
        (export / ".actionc64u-idun-export").write_text("fixture\n", encoding="ascii")
        (export / "ACTION.PROJ").write_text(
            "ACTION PROJECT\nHELLO.ACT\n", encoding="ascii"
        )
        for name in ("DOC", "LIB", "PLAYGROUND", "RES", "SRC"):
            (export / name).mkdir()
        (export / "DOC" / "action-help.sqlite3").write_bytes(b"SQLite format 3\0")
        (export / "DOC" / "README.txt").write_text("help\n", encoding="ascii")
        (export / "LIB" / "GFX1.ACT").write_text("MODULE\n", encoding="ascii")
        (export / "PLAYGROUND" / "HELLO.ACT").write_text(
            "PROC Main()\nRETURN\n", encoding="ascii"
        )
        (export / "SRC" / "HELLO.ACT").write_text(
            "PROC Main()\nRETURN\n", encoding="ascii"
        )
        (export / "RES" / "PLAYER.SPR").write_bytes(b"ASP1")
        self.write_aarch64_elf(tools / "action-workspace-tools", machine)
        (tools / "actsvc").write_bytes(bytes.fromhex("4c086dcb06104000"))
        return export, tools

    def prepare(self, export: Path, tools: Path, work: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(self.root / "tools" / "prepare_alpine_package.py"),
                "--export",
                str(export),
                "--tools-source",
                str(tools),
                "--work",
                str(work),
                "--version",
                "0.1.0_pre20260718",
                "--pkgrel",
                "3",
                "--source-date-epoch",
                "1700000000",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def test_preparer_creates_deduplicated_deterministic_apk_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.root / "build") as tmp:
            base = Path(tmp)
            export, tools = self.make_fixture(base)
            work = base / "work"
            first = self.prepare(export, tools, work)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            source = work / "idun_action-0.1.0_pre20260718.tar.gz"
            first_bytes = source.read_bytes()
            with tarfile.open(source, "r:gz") as archive:
                names = set(archive.getnames())
                multicall = archive.getmember(
                    "idun-action/TOOLS/action-workspace-tools"
                )
                helper = archive.getmember(
                    "idun-action/idun-action-new-workspace"
                )
            self.assertIn("idun-action/TOOLS/actsvc", names)
            self.assertIn("idun-action/LIB/GFX1.ACT", names)
            self.assertIn("idun-action/DOC/action-help.sqlite3", names)
            self.assertIn("idun-action/OBJ", names)
            self.assertIn("idun-action/BIN", names)
            self.assertNotIn("idun-action/TOOLS/actc", names)
            self.assertEqual(multicall.mode, 0o755)
            self.assertEqual(helper.mode, 0o755)
            self.assertEqual(multicall.uid, 0)
            self.assertEqual(multicall.mtime, 1700000000)

            apkbuild = (work / "APKBUILD").read_text(encoding="utf-8")
            digest = hashlib.sha512(first_bytes).hexdigest()
            self.assertIn("pkgname=idun_action\n", apkbuild)
            self.assertIn("subpackages=\"idun_action_full:_full\"", apkbuild)
            self.assertIn("pkgrel=3\n", apkbuild)
            self.assertIn(digest, apkbuild)
            self.assertIn(" ".join(LINUX_TOOL_NAMES), apkbuild)
            self.assertNotRegex(apkbuild, r"@[A-Z][A-Z0-9_]*@")

            second = self.prepare(export, tools, work)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(source.read_bytes(), first_bytes)

    def test_preparer_rejects_non_aarch64_tool_binary(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.root / "build") as tmp:
            base = Path(tmp)
            export, tools = self.make_fixture(base, machine=62)
            result = self.prepare(export, tools, base / "work")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not AArch64 ELF", result.stderr)

    def test_workspace_helper_copies_and_will_not_replace(self) -> None:
        helper = self.root / "packaging" / "alpine" / "idun-action-new-workspace"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            template = base / "template"
            destination = base / "workspace"
            (template / "SRC").mkdir(parents=True)
            (template / "SRC" / "HELLO.ACT").write_text("hello\n", encoding="ascii")
            environment = os.environ.copy()
            environment["IDUN_ACTION_TEMPLATE"] = str(template)
            created = subprocess.run(
                [str(helper), str(destination)],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            self.assertEqual(
                (destination / "SRC" / "HELLO.ACT").read_text(encoding="ascii"),
                "hello\n",
            )
            refused = subprocess.run(
                [str(helper), str(destination)],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("Refusing to replace", refused.stderr)

    def test_repository_and_web_templates_keep_private_key_outside_web_root(self) -> None:
        builder = (self.root / "tools" / "build_alpine_packages.sh").read_text(
            encoding="utf-8"
        )
        verifier = (self.root / "packaging" / "alpine" / "container-verify.sh").read_text(
            encoding="utf-8"
        )
        service = (self.root / "packaging" / "web" / "idun-action-apk.service.in").read_text(
            encoding="utf-8"
        )
        self.assertIn('KEY_DIR="${ACTION_APK_KEY_DIR:-$ROOT_DIR/.apk-keys}"', builder)
        self.assertIn('REPOSITORY="$APK_ROOT/repository"', builder)
        self.assertIn("test ! -e /repository/idun-action-apk.rsa", verifier)
        self.assertIn("NoNewPrivileges=true", service)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("ReadOnlyPaths=@REPOSITORY@", service)
        self.assertIn("InaccessiblePaths=@KEY_DIR@", service)
        self.assertIn("CapabilityBoundingSet=", service)

    @unittest.skipUnless(shutil.which("openssl"), "openssl is required")
    def test_signing_key_initializer_is_private_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_dir = Path(tmp) / "keys"
            environment = os.environ.copy()
            environment["ACTION_APK_KEY_DIR"] = str(key_dir)
            command = [
                "bash",
                str(self.root / "tools" / "init_alpine_signing_key.sh"),
            ]
            first = subprocess.run(
                command,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            private_key = key_dir / "idun-action-apk.rsa"
            public_key = key_dir / "idun-action-apk.rsa.pub"
            original = private_key.read_bytes()
            self.assertEqual(private_key.stat().st_mode & 0o777, 0o600)
            self.assertEqual(public_key.stat().st_mode & 0o777, 0o644)
            self.assertIn("BEGIN PRIVATE KEY", original.decode("ascii"))
            self.assertIn("BEGIN PUBLIC KEY", public_key.read_text(encoding="ascii"))

            second = subprocess.run(
                command,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(private_key.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
