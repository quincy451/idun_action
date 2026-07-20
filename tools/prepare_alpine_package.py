#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile

from export_idun_workspace import LINUX_TOOL_NAMES


PACKAGE_ROOT = "idun-action"
REQUIRED_EXPORT_ITEMS = (
    "ACTION.PROJ",
    "DOC",
    "LIB",
    "PLAYGROUND",
    "RES",
    "SRC",
)
VERSION_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:[a-z])?(?:_(?:alpha|beta|pre|rc|cvs|svn|git|hg|p)[0-9]*)*$")


def fail(message: str) -> None:
    raise RuntimeError(message)


def validate_aarch64_elf(path: Path) -> None:
    header = path.read_bytes()[:20]
    if len(header) < 20 or header[:4] != b"\x7fELF":
        fail(f"Linux multicall executable is not ELF: {path}")
    if header[4] != 2 or header[5] != 1:
        fail(f"Linux multicall executable is not 64-bit little-endian ELF: {path}")
    machine = int.from_bytes(header[18:20], "little")
    if machine != 183:
        fail(f"Linux multicall executable is not AArch64 ELF: {path}")


def copy_export_payload(export: Path, tools: Path, stage: Path, root: Path) -> None:
    marker = export / ".actionc64u-idun-export"
    if not marker.is_file():
        fail(f"refusing unmarked Idun export: {export}")
    for name in REQUIRED_EXPORT_ITEMS:
        if not (export / name).exists():
            fail(f"Idun export is missing {name}: {export}")

    multicall = tools / "action-workspace-tools"
    target_service = tools / "actsvc"
    if not multicall.is_file() or not os.access(multicall, os.X_OK):
        fail(f"missing executable AArch64 multicall tool: {multicall}")
    validate_aarch64_elf(multicall)
    if not target_service.is_file():
        fail(f"missing Idun C64 target service: {target_service}")

    stage.mkdir(parents=True)
    tools_stage = stage / "TOOLS"
    tools_stage.mkdir()
    shutil.copy2(multicall, tools_stage / multicall.name)
    shutil.copy2(target_service, tools_stage / target_service.name)
    for name in REQUIRED_EXPORT_ITEMS:
        source = export / name
        target = stage / name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    for name in ("OBJ", "BIN"):
        (stage / name).mkdir()
    shutil.copy2(root / "LICENSE", stage / "LICENSE")
    helper = root / "packaging" / "alpine" / "idun-action-new-workspace"
    shutil.copy2(helper, stage / helper.name)


def normalized_mode(path: Path) -> int:
    if path.is_dir():
        return 0o755
    if path.name in {"action-workspace-tools", "idun-action-new-workspace"}:
        return 0o755
    return 0o644


def add_path(archive: tarfile.TarFile, source: Path, arcname: str, epoch: int) -> None:
    info = archive.gettarinfo(str(source), arcname=arcname)
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = epoch
    info.mode = normalized_mode(source)
    if info.isfile():
        with source.open("rb") as handle:
            archive.addfile(info, handle)
    else:
        archive.addfile(info)


def make_source_archive(stage: Path, output: Path, epoch: int) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                add_path(archive, stage, PACKAGE_ROOT, epoch)
                for source in sorted(stage.rglob("*"), key=lambda item: item.as_posix()):
                    relative = source.relative_to(stage).as_posix()
                    add_path(archive, source, f"{PACKAGE_ROOT}/{relative}", epoch)
    digest = hashlib.sha512()
    with output.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_apkbuild(template: Path, output: Path, version: str, pkgrel: int, digest: str) -> None:
    rendered = template.read_text(encoding="utf-8")
    replacements = {
        "@PKGVER@": version,
        "@PKGREL@": str(pkgrel),
        "@SHA512@": digest,
        "@ACTION_COMMANDS@": " ".join(LINUX_TOOL_NAMES),
    }
    for token, value in replacements.items():
        if token not in rendered:
            fail(f"APKBUILD template is missing placeholder {token}")
        rendered = rendered.replace(token, value)
    if re.search(r"@[A-Z][A-Z0-9_]*@", rendered):
        fail("APKBUILD template contains an unresolved placeholder")
    output.write_text(rendered, encoding="utf-8")


def safe_reset_work(work: Path, root: Path) -> None:
    work = work.resolve()
    build_root = (root / "build").resolve()
    if build_root not in work.parents:
        fail(f"package work directory must be below {build_root}: {work}")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the Idun Alpine APKBUILD input")
    parser.add_argument("--export", default="build/idun-action-aarch64")
    parser.add_argument("--tools-source", default="build/linux_tools-aarch64")
    parser.add_argument("--work", default="build/alpine-apk/work")
    parser.add_argument("--template", default="packaging/alpine/APKBUILD.in")
    parser.add_argument("--version", required=True)
    parser.add_argument("--pkgrel", type=int, default=0)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    version = args.version.strip()
    if not VERSION_PATTERN.fullmatch(version):
        parser.error(f"invalid Alpine package version: {version}")
    if args.pkgrel < 0:
        parser.error("--pkgrel must not be negative")
    if args.source_date_epoch < 0:
        parser.error("--source-date-epoch must not be negative")

    export = (root / args.export).resolve() if not Path(args.export).is_absolute() else Path(args.export).resolve()
    tools = (root / args.tools_source).resolve() if not Path(args.tools_source).is_absolute() else Path(args.tools_source).resolve()
    work = (root / args.work).resolve() if not Path(args.work).is_absolute() else Path(args.work).resolve()
    template = (root / args.template).resolve() if not Path(args.template).is_absolute() else Path(args.template).resolve()

    safe_reset_work(work, root)
    stage = work / "stage" / PACKAGE_ROOT
    copy_export_payload(export, tools, stage, root)
    source_name = f"idun_action-{version}.tar.gz"
    source_archive = work / source_name
    digest = make_source_archive(stage, source_archive, args.source_date_epoch)
    render_apkbuild(template, work / "APKBUILD", version, args.pkgrel, digest)
    shutil.rmtree(stage.parent)

    print(f"work={work}")
    print(f"source={source_archive}")
    print(f"apkbuild={work / 'APKBUILD'}")
    print(f"sha512={digest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"prepare_alpine_package: {error}", file=sys.stderr)
        raise SystemExit(1) from error
