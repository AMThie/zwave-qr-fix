"""Refuse files that contain DSKs which do not look synthetic.

A DSK (Device Specific Key) is part of Z-Wave S2 security and must never be
committed. By convention, every DSK in this repository is synthetic and
starts with the block ``12345``. This check flags anything else that looks
like a DSK: formatted (``xxxxx-xxxxx-...``), a bare 40-digit run, or the DSK
inside a complete SmartStart string (``9000...`` / ``9001...``).

Usage: python scripts/check_synthetic_dsk.py FILE [FILE ...]
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

SYNTHETIC_PREFIX = "12345"

FORMATTED_DSK = re.compile(r"(?<![\d-])\d{5}(?:-\d{5}){7}(?![\d-])")
BARE_DSK = re.compile(r"(?<!\d)\d{40}(?!\d)")
# lead-in 90, version 00/01, checksum (5), keys (3), then the 40-digit DSK
SMARTSTART = re.compile(r"(?<!\d)90(?:00|01)\d{8}(\d{40})")


def find_dsks(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line number, digits-only DSK) for every DSK-like match."""
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in FORMATTED_DSK.finditer(line):
            yield lineno, m.group().replace("-", "")
        for m in BARE_DSK.finditer(line):
            yield lineno, m.group()
        for m in SMARTSTART.finditer(line):
            yield lineno, m.group(1)


def mask(dsk: str) -> str:
    return f"{dsk[:5]}-xxxxx-…"


def main(paths: list[str]) -> int:
    failed = False
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, dsk in find_dsks(text):
            if not dsk.startswith(SYNTHETIC_PREFIX):
                print(
                    f"{path}:{lineno}: possible real DSK ({mask(dsk)}). "
                    f"Synthetic DSKs must start with {SYNTHETIC_PREFIX}."
                )
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
