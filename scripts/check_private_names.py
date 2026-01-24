#!/usr/bin/env python3
"""Check for private names (single underscore prefix) in Python source files.

Allows dunders (__name__) but blocks private names (_name, __name).
"""
import re
import sys
from pathlib import Path

PRIVATE_PATTERN = re.compile(r"\b_[a-z][a-z0-9_]*\b(?!__)")
DUNDER_PATTERN = re.compile(r"__[a-z][a-z0-9_]*__")


def check_file(path: Path) -> list[tuple[int, str, str]]:
    errors = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        # Skip comments and strings (rough heuristic)
        if line.strip().startswith("#"):
            continue
        # Find private names that aren't dunders
        for match in PRIVATE_PATTERN.finditer(line):
            name = match.group()
            # Skip if it's part of a dunder
            if DUNDER_PATTERN.search(line):
                continue
            # Skip common exceptions
            if name in ("_", "_conn"):  # _ for unused, _conn for sqlalchemy
                continue
            errors.append((i, name, line.strip()))
    return errors


def main():
    root = Path("ninjamagic")
    if not root.exists():
        print("Run from project root", file=sys.stderr)
        return 1

    all_errors = []
    for path in root.rglob("*.py"):
        errors = check_file(path)
        for line_no, name, line in errors:
            all_errors.append(f"{path}:{line_no}: private name '{name}' - {line}")

    if all_errors:
        print("Private names found (use public names instead):\n")
        for err in all_errors:
            print(err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
