from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest

from . import __version__


ACTIVE_TEST_MODULES = (
    "tests.test_linux_workspace_tools",
    "tests.test_action_help",
    "tests.test_idun_workspace_export",
    "tests.test_idun_prg_runtime",
    "tests.test_idun_fork_layout",
    "tests.test_vice_smoke",
    "tests.test_layout",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pytest",
        description="Bootstrap pytest compatibility runner for ActionC64U.",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="reduce test output")
    parser.add_argument("--version", action="store_true", help="print the local shim version")
    parser.add_argument("paths", nargs="*", help="optional test path roots")
    args, unknown = parser.parse_known_args(argv)

    if args.version:
        print(f"pytest {__version__}")
        return 0

    if unknown:
        parser.error(f"unsupported arguments for bootstrap runner: {' '.join(unknown)}")

    root = Path.cwd().resolve()
    loader = unittest.defaultTestLoader
    if not args.paths:
        suite = loader.loadTestsFromNames(ACTIVE_TEST_MODULES)
    else:
        suites: list[unittest.TestSuite] = []
        for raw_path in args.paths:
            candidate = (root / raw_path).resolve()
            if candidate.is_dir():
                suites.append(loader.discover(str(candidate), pattern="test_*.py"))
            elif candidate.is_file():
                try:
                    relative = candidate.relative_to(root).with_suffix("")
                except ValueError:
                    parser.error(f"test path is outside the repository: {candidate}")
                suites.append(loader.loadTestsFromName(".".join(relative.parts)))
            else:
                parser.error(f"test path not found: {candidate}")
        suite = unittest.TestSuite(suites)
    runner = unittest.TextTestRunner(verbosity=1 if args.quiet else 2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
