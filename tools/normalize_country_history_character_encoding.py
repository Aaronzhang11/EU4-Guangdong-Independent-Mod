#!/usr/bin/env python3
"""Normalize Chinese character names in country history scripts for EU4dll.

ASCII/Pinyin histories are left untouched. Histories already using EU4dll's
double-byte escape format are validated and preserved byte-for-byte. A legacy
UTF-8 or GBK history containing Chinese ``name``/``dynasty`` values is decoded
and rewritten with the escape format used by the installed Chinese patch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from encode_eu4_chinese_localisation import from_escaped_bytes, to_escaped_bytes


ROOT = Path(__file__).resolve().parents[1]
COUNTRY_HISTORY = ROOT / "guangdong_independent_practice/history/countries"
CHARACTER_ASSIGNMENT = re.compile(rb"(?m)^\s*(?:name|dynasty)\s*=")
EMPTY_CHARACTER_ASSIGNMENT = re.compile(
    rb'(?m)^\s*(?:name|dynasty)\s*=\s*"\s*"'
)
ESCAPE_BYTES = frozenset((0x10, 0x11, 0x12, 0x13))
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
# SNG was the sole legacy GBK history found by the initial audit. Its first
# conversion predated LF normalization, so keep the repair idempotent here.
FORCED_LF_FILES = frozenset(("SNG - Song.txt",))


def has_character_assignments(data: bytes) -> bool:
    return CHARACTER_ASSIGNMENT.search(data) is not None


def source_chinese_text(data: bytes, path: Path) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "gbk"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if CJK_PATTERN.search(text):
            return text, encoding
    raise ValueError(
        f"{path.name}: non-ASCII character history is neither readable UTF-8 nor GBK Chinese"
    )


def normalized_history_data(data: bytes, path: Path) -> tuple[bytes, str]:
    if not has_character_assignments(data):
        return data, "no-character-assignments"
    if EMPTY_CHARACTER_ASSIGNMENT.search(data):
        raise ValueError(f"{path.name}: empty character name or dynasty")

    if any(byte in ESCAPE_BYTES for byte in data):
        expected = (
            data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if path.name in FORCED_LF_FILES
            else data
        )
        decoded = from_escaped_bytes(expected)
        if "\ufffd" in decoded:
            raise ValueError(f"{path.name}: malformed EU4 double-byte character data")
        return expected, "eu4-escaped"

    if all(byte < 0x80 for byte in data):
        return data, "ascii"

    decoded, source_encoding = source_chinese_text(data, path)
    decoded = decoded.replace("\r\n", "\n").replace("\r", "\n")
    return to_escaped_bytes(decoded), source_encoding


def normalize_country_history_files(check: bool = False) -> dict[str, object]:
    scanned: list[str] = []
    changed: list[str] = []
    formats: dict[str, int] = {}
    for path in sorted(COUNTRY_HISTORY.glob("*.txt")):
        current = path.read_bytes()
        if not has_character_assignments(current):
            continue
        scanned.append(path.name)
        expected, source_format = normalized_history_data(current, path)
        formats[source_format] = formats.get(source_format, 0) + 1
        if expected == current:
            continue
        if check:
            raise ValueError(
                f"{path.name}: character names still use legacy {source_format} encoding"
            )
        path.write_bytes(expected)
        changed.append(path.name)

    return {
        "character_history_files": len(scanned),
        "formats": dict(sorted(formats.items())),
        "changed_files": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            normalize_country_history_files(check=args.check),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
