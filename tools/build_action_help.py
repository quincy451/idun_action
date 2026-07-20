#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any


ALLOWED_KINDS = {"keyword", "type", "builtin", "constant"}
REQUIRED_KEYWORDS = {
    "AND",
    "ARRAY",
    "ASMBLOCK",
    "BYTE",
    "CARD",
    "CHAR",
    "CONST",
    "DEFINE",
    "DO",
    "ELSE",
    "ELSEIF",
    "ENDOVERLAY",
    "ENDFUNC",
    "ENDPROC",
    "EXIT",
    "FI",
    "FOR",
    "FUNC",
    "IF",
    "INCLUDE",
    "INT",
    "LSH",
    "MOD",
    "MODULE",
    "OD",
    "OVERLAY",
    "OR",
    "POINTER",
    "PROC",
    "REAL",
    "RESOURCE",
    "RETURN",
    "RSH",
    "REU",
    "SET",
    "STEP",
    "THEN",
    "TO",
    "TYPE",
    "UNTIL",
    "WHILE",
    "XOR",
}


class CatalogError(RuntimeError):
    pass


def source_table_body(source: str, function_name: str, table_name: str) -> str:
    function = re.search(
        rf"\b{re.escape(function_name)}\s*\([^)]*\)\s*\{{(.*?)(?=\n\}}\n)",
        source,
        flags=re.DOTALL,
    )
    if function is None:
        raise CatalogError(f"cannot locate compiler function {function_name}")
    table = re.search(
        rf"\b{re.escape(table_name)}\s*=\s*\{{(.*?)\n\s*\}};",
        function.group(1),
        flags=re.DOTALL,
    )
    if table is None:
        raise CatalogError(f"cannot locate compiler table {table_name}")
    return table.group(1)


def compiler_builtin_tokens(root: Path) -> set[str]:
    source = (root / "src" / "tools_linux" / "action_workspace_tools.cpp").read_text(
        encoding="utf-8"
    )
    body = source_table_body(source, "builtin_call", "calls")
    return {name.upper() for name in re.findall(r'^\s*\{"([A-Z][A-Z0-9_]*)"', body, re.MULTILINE)}


def compiler_constant_tokens(root: Path) -> set[str]:
    source = (root / "src" / "tools_linux" / "action_workspace_tools.cpp").read_text(
        encoding="utf-8"
    )
    body = source_table_body(source, "builtin_integer_constants", "constants")
    return {name.upper() for name in re.findall(r'^\s*\{"([A-Z][A-Z0-9_]*)"', body, re.MULTILINE)}


def library_tokens(root: Path) -> set[str]:
    found: set[str] = set()
    declaration = re.compile(
        r"^\s*(?:(?:BYTE|CARD|INT|REAL)\s+FUNC|PROC|(?:BYTE|CARD|INT|REAL)\s+CONST)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    for path in sorted((root / "lib").glob("*.act")):
        found.update(
            name.upper()
            for name in declaration.findall(path.read_text(encoding="ascii"))
            if not name.startswith("_")
        )
    return found


def require_string(record: dict[str, Any], key: str, context: str) -> str:
    value = record.get(key, "")
    if not isinstance(value, str):
        raise CatalogError(f"{context}: {key} must be a string")
    return value.strip()


def flatten_catalog(payload: dict[str, Any]) -> tuple[list[dict[str, str]], list[tuple[str, str]]]:
    if payload.get("schema_version") != 1:
        raise CatalogError("unsupported or missing catalog schema_version")

    flattened: list[dict[str, str]] = []
    aliases: list[tuple[str, str]] = []
    seen: set[str] = set()
    seen_aliases: set[str] = set()

    groups: list[tuple[dict[str, Any], str, str, str]] = []
    top_topics = payload.get("topics")
    if not isinstance(top_topics, list):
        raise CatalogError("topics must be a list")
    for topic in top_topics:
        groups.append((topic, "", "", ""))

    libraries = payload.get("libraries")
    if not isinstance(libraries, list):
        raise CatalogError("libraries must be a list")
    for library in libraries:
        if not isinstance(library, dict):
            raise CatalogError("library records must be objects")
        name = require_string(library, "name", "library")
        details = require_string(library, "details", f"library {name}")
        target_notes = require_string(library, "target_notes", f"library {name}")
        topics = library.get("topics")
        if not isinstance(topics, list):
            raise CatalogError(f"library {name}: topics must be a list")
        for topic in topics:
            groups.append((topic, name, details, target_notes))

    identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    for raw, default_library, default_details, default_target_notes in groups:
        if not isinstance(raw, dict):
            raise CatalogError("topic records must be objects")
        token = require_string(raw, "token", "topic")
        context = f"topic {token or '<missing>'}"
        if not identifier.fullmatch(token):
            raise CatalogError(f"{context}: token must be an Action identifier")
        canonical = token.upper()
        if canonical in seen:
            raise CatalogError(f"duplicate topic token: {token}")
        seen.add(canonical)

        kind = require_string(raw, "kind", context) or "builtin"
        if kind not in ALLOWED_KINDS:
            raise CatalogError(f"{context}: unsupported kind {kind}")
        signature = require_string(raw, "signature", context)
        summary = require_string(raw, "summary", context)
        if not signature or not summary:
            raise CatalogError(f"{context}: signature and summary are required")
        record = {
            "token": token,
            "kind": kind,
            "signature": signature,
            "summary": summary,
            "details": require_string(raw, "details", context) or default_details,
            "example": require_string(raw, "example", context),
            "library": require_string(raw, "library", context) or default_library,
            "target_notes": require_string(raw, "target_notes", context)
            or default_target_notes,
        }
        flattened.append(record)

        raw_aliases = raw.get("aliases", [])
        if not isinstance(raw_aliases, list):
            raise CatalogError(f"{context}: aliases must be a list")
        for alias_value in raw_aliases:
            if not isinstance(alias_value, str) or not identifier.fullmatch(alias_value):
                raise CatalogError(f"{context}: invalid alias {alias_value!r}")
            alias = alias_value.upper()
            if alias in seen or alias in seen_aliases:
                raise CatalogError(f"duplicate or shadowing alias: {alias_value}")
            seen_aliases.add(alias)
            aliases.append((alias_value, token))

    return flattened, aliases


def validate_completeness(root: Path, topics: list[dict[str, str]]) -> None:
    available = {topic["token"].upper() for topic in topics}
    checks = {
        "compiler builtin": compiler_builtin_tokens(root),
        "compiler constant": compiler_constant_tokens(root),
        "library declaration": library_tokens(root),
        "required language keyword": REQUIRED_KEYWORDS,
    }
    failures: list[str] = []
    for label, required in checks.items():
        missing = sorted(required - available)
        if missing:
            failures.append(f"missing {label} topics: {', '.join(missing)}")
    missing_examples = sorted(
        topic["token"] for topic in topics if not topic["example"]
    )
    if missing_examples:
        failures.append(
            "missing topic examples: " + ", ".join(missing_examples)
        )
    if failures:
        raise CatalogError("; ".join(failures))


def build_database(
    output: Path,
    payload: dict[str, Any],
    topics: list[dict[str, str]],
    aliases: list[tuple[str, str]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        database = sqlite3.connect(temporary)
        try:
            database.executescript(
                """
                PRAGMA page_size=4096;
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                CREATE TABLE metadata(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                ) WITHOUT ROWID;
                CREATE TABLE topics(
                    token TEXT PRIMARY KEY COLLATE NOCASE,
                    kind TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details TEXT NOT NULL,
                    example TEXT NOT NULL,
                    library TEXT NOT NULL,
                    target_notes TEXT NOT NULL
                ) WITHOUT ROWID;
                CREATE TABLE aliases(
                    alias TEXT PRIMARY KEY COLLATE NOCASE,
                    token TEXT NOT NULL REFERENCES topics(token)
                ) WITHOUT ROWID;
                CREATE INDEX topics_kind ON topics(kind, token COLLATE NOCASE);
                """
            )
            database.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?)",
                [
                    ("schema_version", str(payload["schema_version"])),
                    ("catalog", str(payload.get("catalog", "Action language help"))),
                    ("topic_count", str(len(topics))),
                ],
            )
            database.executemany(
                """
                INSERT INTO topics(
                    token,kind,signature,summary,details,example,library,target_notes
                ) VALUES(
                    :token,:kind,:signature,:summary,:details,:example,:library,:target_notes
                )
                """,
                sorted(topics, key=lambda topic: topic["token"].upper()),
            )
            database.executemany(
                "INSERT INTO aliases(alias,token) VALUES(?,?)",
                sorted(aliases, key=lambda item: item[0].upper()),
            )
            database.execute(f"PRAGMA user_version={int(payload['schema_version'])}")
            database.commit()
            result = database.execute("PRAGMA integrity_check").fetchone()
            if result != ("ok",):
                raise CatalogError(f"SQLite integrity check failed: {result!r}")
        finally:
            database.close()
        temporary.chmod(0o644)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Action help metadata and build its SQLite catalog"
    )
    parser.add_argument("--source", default="resources/action_help.json")
    parser.add_argument("--output", default="build/linux_tools/action-help.sqlite3")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    source = (root / args.source).resolve() if not Path(args.source).is_absolute() else Path(args.source)
    output = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CatalogError("catalog root must be an object")
        topics, aliases = flatten_catalog(payload)
        validate_completeness(root, topics)
        if not args.check_only:
            build_database(output, payload, topics, aliases)
    except (CatalogError, OSError, json.JSONDecodeError, sqlite3.Error) as error:
        parser.error(str(error))

    action = "validated" if args.check_only else "built"
    print(f"{action} {len(topics)} help topics")
    if not args.check_only:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
