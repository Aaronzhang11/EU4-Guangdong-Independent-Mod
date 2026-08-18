"""Generate raw EU4 double-byte country scripts from readable UTF-8 sources."""

from __future__ import annotations

import argparse
from pathlib import Path

from encode_eu4_chinese_localisation import from_escaped_bytes, to_escaped_bytes


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tools" / "country_sources"
TARGET_DIR = ROOT / "guangdong_independent_practice" / "common" / "countries"

FILES = {
    "Chaozhou_readable_utf8.txt": "Chaozhou.txt",
}


def readable_text(path: Path) -> str:
    """Return deterministic CRLF text to match the existing country scripts."""
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n")


def encode_file(source: Path, target: Path) -> bool:
    encoded = to_escaped_bytes(readable_text(source))
    previous = target.read_bytes() if target.exists() else None
    target.write_bytes(encoded)
    return previous != encoded


def verify_file(source: Path, target: Path) -> None:
    expected = readable_text(source)
    decoded = from_escaped_bytes(target.read_bytes())
    if decoded != expected:
        raise ValueError(f"{target.name}: encoded content does not round-trip to its source")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated country scripts without rewriting them",
    )
    args = parser.parse_args()

    for source_name, target_name in FILES.items():
        source = SOURCE_DIR / source_name
        target = TARGET_DIR / target_name
        if args.check:
            verify_file(source, target)
            print(f"{target_name}: valid")
        else:
            changed = encode_file(source, target)
            print(f"{target_name}: {'updated' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
