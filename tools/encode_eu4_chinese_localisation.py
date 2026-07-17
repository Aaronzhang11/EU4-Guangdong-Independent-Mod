"""Encode readable Chinese localisation for the EU4 double-byte patch.

The readable source files are ordinary UTF-8 text.  EU4's Chinese language
patch stores every non-Latin character as an escape byte plus a little-endian
UCS-2 code point.  Some bytes are shifted to keep them safe inside Clausewitz
text, and bytes 0x80-0x9F must be represented through their Windows-1252
Unicode equivalents before the final UTF-8 file is written.

The escape constants and reserved-byte rules mirror matanki-saito/EU4dll.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

FILES = {
    "gdd_l_english_readable_utf8.txt": "gdd_l_english.yml",
    "gdd_treaty_readable_utf8.txt": "gdd_treaty_l_english.yml",
    "gdd_characters_readable_utf8.txt": "gdd_characters_l_english.yml",
    "gdd_invested_tributary_readable_utf8.txt": "gdd_invested_tributary_l_english.yml",
    "gdd_defiance_readable_utf8.txt": "gdd_defiance_l_english.yml",
}

# Bytes that the double-byte patch escapes inside either half of a UCS-2 code
# point.  These values come from convertWideTextToEscapedText in EU4dll.
RESERVED_BYTES = {
    0x00,
    0x0A,
    0x0D,
    0x20,
    0x22,
    0x23,
    0x24,
    0x2A,
    0x2F,
    0x3A,
    0x3B,
    0x3C,
    0x3D,
    0x3E,
    0x3F,
    0x40,
    0x5B,
    0x5C,
    0x5D,
    0x5F,
    0x7B,
    0x7C,
    0x7D,
    0x7E,
    0x80,
    0xA3,
    0xA4,
    0xA7,
    0xBD,
}

# Unicode characters that Windows-1252 uses for the C1 byte range.  Writing
# U+0080-U+009F directly makes EU4 log "Couldn't find Latin1 character" and
# corrupts the following Chinese glyphs.
CP1252_BYTE_TO_UNICODE = {
    0x80: 0x20AC,
    0x82: 0x201A,
    0x83: 0x0192,
    0x84: 0x201E,
    0x85: 0x2026,
    0x86: 0x2020,
    0x87: 0x2021,
    0x88: 0x02C6,
    0x89: 0x2030,
    0x8A: 0x0160,
    0x8B: 0x2039,
    0x8C: 0x0152,
    0x8E: 0x017D,
    0x91: 0x2018,
    0x92: 0x2019,
    0x93: 0x201C,
    0x94: 0x201D,
    0x95: 0x2022,
    0x96: 0x2013,
    0x97: 0x2014,
    0x98: 0x02DC,
    0x99: 0x2122,
    0x9A: 0x0161,
    0x9B: 0x203A,
    0x9C: 0x0153,
    0x9E: 0x017E,
    0x9F: 0x0178,
}
CP1252_UNICODE_TO_BYTE = {
    unicode_codepoint: byte for byte, unicode_codepoint in CP1252_BYTE_TO_UNICODE.items()
}


def to_escaped_bytes(text: str) -> bytes:
    result = bytearray()
    for character in text:
        codepoint = ord(character)

        if codepoint in CP1252_UNICODE_TO_BYTE:
            result.append(CP1252_UNICODE_TO_BYTE[codepoint])
            continue

        # EU4dll shifts these code points before writing their two-byte form.
        if 0x100 < codepoint < 0xA00:
            codepoint += 0xE000

        high = (codepoint >> 8) & 0xFF
        low = codepoint & 0xFF
        if high == 0:
            result.append(low)
            continue

        escape = 0x10
        if high in RESERVED_BYTES:
            escape += 2
            high = (high - 9) & 0xFF
        if low in RESERVED_BYTES:
            escape += 1
            low = (low + 14) & 0xFF

        result.extend((escape, low, high))
    return bytes(result)


def escaped_bytes_to_utf8(data: bytes) -> bytes:
    # Undefined Windows-1252 bytes (81, 8D, 8F, 90 and 9D) are intentionally
    # retained as the matching control code points, just as in the installed
    # Chinese language mod.
    encoded_text = "".join(
        chr(CP1252_BYTE_TO_UNICODE.get(byte, byte)) for byte in data
    )
    return b"\xef\xbb\xbf" + encoded_text.encode("utf-8")


def utf8_text_to_escaped_bytes(text: str) -> bytes:
    result = bytearray()
    for character in text:
        codepoint = ord(character)
        if codepoint in CP1252_UNICODE_TO_BYTE:
            result.append(CP1252_UNICODE_TO_BYTE[codepoint])
        elif codepoint <= 0xFF:
            result.append(codepoint)
        else:
            raise ValueError(f"Unexpected non-CP1252 character U+{codepoint:04X} in encoded file")
    return bytes(result)


def from_escaped_bytes(data: bytes) -> str:
    result: list[str] = []
    index = 0
    while index < len(data):
        byte = data[index]
        if byte not in (0x10, 0x11, 0x12, 0x13):
            result.append(chr(CP1252_BYTE_TO_UNICODE.get(byte, byte)))
            index += 1
            continue

        if index + 2 >= len(data):
            raise ValueError("Truncated double-byte escape at end of file")
        low = data[index + 1]
        high = data[index + 2]
        codepoint = low | (high << 8)
        if byte == 0x11:
            codepoint -= 0x0E
        elif byte == 0x12:
            codepoint += 0x900
        elif byte == 0x13:
            codepoint += 0x8F2
        if 0xE100 < codepoint < 0xEA00:
            codepoint -= 0xE000
        result.append(chr(codepoint))
        index += 3
    return "".join(result)


def encode_file(source: Path, target: Path) -> bool:
    readable = source.read_text(encoding="utf-8-sig")
    encoded = escaped_bytes_to_utf8(to_escaped_bytes(readable))
    previous = target.read_bytes() if target.exists() else None
    target.write_bytes(encoded)
    return previous != encoded


def verify_file(source: Path, target: Path) -> None:
    data = target.read_bytes()
    if not data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{target.name}: missing UTF-8 BOM")
    encoded_text = data.decode("utf-8-sig")
    forbidden_controls = sorted(
        {ord(character) for character in encoded_text if ord(character) in CP1252_BYTE_TO_UNICODE}
    )
    if forbidden_controls:
        rendered = ", ".join(f"U+{codepoint:04X}" for codepoint in forbidden_controls)
        raise ValueError(f"{target.name}: unconverted Windows-1252 controls: {rendered}")
    decoded = from_escaped_bytes(utf8_text_to_escaped_bytes(encoded_text))
    readable = source.read_text(encoding="utf-8-sig")
    if decoded != readable:
        raise ValueError(f"{target.name}: encoded content does not round-trip to its source")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify existing targets without rewriting them",
    )
    args = parser.parse_args()
    source_dir = MOD / "localisation_source"
    target_dir = MOD / "localisation"
    for source_name, target_name in FILES.items():
        source = source_dir / source_name
        target = target_dir / target_name
        if args.check:
            verify_file(source, target)
            print(f"{target_name}: valid")
        else:
            changed = encode_file(source, target)
            print(f"{target_name}: {'updated' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
