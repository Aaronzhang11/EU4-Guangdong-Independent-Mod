#!/usr/bin/env python3
"""Generate EU4dll-safe event/scripted-effect files from readable UTF-8."""

from __future__ import annotations

import argparse
from pathlib import Path

from encode_eu4_chinese_localisation import from_escaped_bytes, to_escaped_bytes


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tools" / "event_sources"
FILES = {
    "gdd_liang_restoration_character_effects_readable_utf8.txt": (
        ROOT
        / "guangdong_independent_practice"
        / "common"
        / "scripted_effects"
        / "gdd_liang_restoration_character_effects.txt"
    ),
}


def readable_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def encode_file(source: Path, target: Path) -> bool:
    encoded = to_escaped_bytes(readable_text(source))
    previous = target.read_bytes() if target.exists() else None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded)
    return previous != encoded


def verify_file(source: Path, target: Path) -> None:
    expected = readable_text(source)
    decoded = from_escaped_bytes(target.read_bytes())
    if decoded != expected:
        raise ValueError(f"{target.name}: encoded content does not round-trip")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    for source_name, target in FILES.items():
        source = SOURCE_DIR / source_name
        if args.check:
            verify_file(source, target)
            print(f"{target.name}: valid")
        else:
            changed = encode_file(source, target)
            print(f"{target.name}: {'updated' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
