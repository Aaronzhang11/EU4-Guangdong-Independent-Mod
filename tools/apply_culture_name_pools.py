#!/usr/bin/env python3
"""Write culture-level Chinese dynasty and personal-name pools.

This complements ``apply_culture_country_name_pools.py``.  Country pools cover
advisors, envoys and most generated personal names; culture ``dynasty_names``
supplies the dynasty of a random monarch and is also the fallback for dynamic
countries.  The output uses the raw double-byte format required by EU4's
Chinese patch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from apply_culture_country_name_pools import CULTURE_SPECS, GIVEN_NAME_SETS
from encode_eu4_chinese_localisation import from_escaped_bytes, to_escaped_bytes


ROOT = Path(__file__).resolve().parents[1]
CULTURE_DIRECTORY = ROOT / "guangdong_independent_practice/common/cultures"
CULTURE_FILES = (
    CULTURE_DIRECTORY / "00_cultures.txt",
    CULTURE_DIRECTORY / "99_gdd_culture_overhaul.txt",
)
GENERATED_COMMENT = b"# Culture-specific Chinese dynasty and personal names."
OLD_INHERITED_COMMENT = b"# Inherited name pools below are preserved verbatim."
NEW_INHERITED_COMMENT = (
    b"# Inherited definitions are preserved byte-for-byte before Chinese name-pool replacement."
)


def balanced_block_end(data: bytes, opening_brace: int) -> int:
    depth = 0
    for index in range(opening_brace, len(data)):
        byte = data[index]
        if byte == ord("{"):
            depth += 1
        elif byte == ord("}"):
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("Unclosed culture block")


def culture_spans(data: bytes, culture: str) -> list[tuple[int, int]]:
    pattern = re.compile(
        rb"(?m)^[ \t]*" + re.escape(culture.encode("ascii")) + rb"[ \t]*=[ \t]*\{"
    )
    return [
        (match.start(), balanced_block_end(data, match.end() - 1))
        for match in pattern.finditer(data)
    ]


def assignment_span(data: bytes, assignment: str) -> tuple[int, int] | None:
    pattern = re.compile(
        rb"(?m)^[ \t]*" + re.escape(assignment.encode("ascii")) + rb"[ \t]*=[ \t]*\{"
    )
    match = pattern.search(data)
    if not match:
        return None
    end = balanced_block_end(data, match.end() - 1)
    while end < len(data) and data[end] in b" \t":
        end += 1
    if data[end:end + 2] == b"\r\n":
        end += 2
    elif data[end:end + 1] == b"\n":
        end += 1
    return match.start(), end


def remove_assignment(data: bytes, assignment: str) -> bytes:
    span = assignment_span(data, assignment)
    if span is None:
        return data
    return data[:span[0]] + data[span[1]:]


def readable_culture_name_blocks(culture: str, indent: str = "\t") -> str:
    if culture not in CULTURE_SPECS:
        raise ValueError(f"No Chinese name pool defined for culture {culture}")
    given_set_name, dynasties = CULTURE_SPECS[culture]
    given = GIVEN_NAME_SETS[given_set_name]
    lines = [
        f"{indent}# Culture-specific Chinese dynasty and personal names.",
        f"{indent}dynasty_names = {{",
    ]
    lines.extend(f'{indent}  "{name}"' for name in dynasties)
    lines.extend((f"{indent}}}", "", f"{indent}male_names = {{"))
    lines.extend(f'{indent}  "{name}"' for name in given["male"])
    lines.extend((f"{indent}}}", "", f"{indent}female_names = {{"))
    lines.extend(f'{indent}  "{name}"' for name in given["female"])
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def generated_culture_block(block: bytes, culture: str) -> bytes:
    block = block.replace(b"\r\n", b"\n")
    block = re.sub(
        rb"(?m)^[ \t]*" + re.escape(GENERATED_COMMENT) + rb"[ \t]*\n",
        b"",
        block,
    )
    for assignment in ("dynasty_names", "male_names", "female_names"):
        block = remove_assignment(block, assignment)

    closing_line = block.rfind(b"\n", 0, len(block) - 1)
    if closing_line < 0:
        raise ValueError(f"{culture}: malformed culture block")
    closing_indent = block[closing_line + 1:-1]
    if closing_indent.strip(b" \t"):
        raise ValueError(f"{culture}: malformed closing indentation")
    readable = readable_culture_name_blocks(culture, closing_indent.decode("ascii") + "  ")
    prefix = block[:closing_line].rstrip(b" \t\n")
    return prefix + b"\n\n" + to_escaped_bytes(readable) + b"\n" + closing_indent + b"}"


def locate_culture(
    contents: dict[Path, bytes], culture: str
) -> tuple[Path, int, int]:
    found: list[tuple[Path, int, int]] = []
    for path, data in contents.items():
        found.extend((path, start, end) for start, end in culture_spans(data, culture))
    if len(found) != 1:
        rendered = [(item[0].name, item[1]) for item in found]
        raise ValueError(f"{culture}: expected one definition, found {rendered}")
    return found[0]


def validate_generated_block(block: bytes, culture: str) -> None:
    if block != generated_culture_block(block, culture):
        raise ValueError(f"{culture}: Chinese culture name pool is stale or malformed")
    for assignment in ("dynasty_names", "male_names", "female_names"):
        count = len(
            re.findall(
                rb"(?m)^\s*" + re.escape(assignment.encode("ascii")) + rb"\s*=",
                block,
            )
        )
        if count != 1:
            raise ValueError(f"{culture}: expected one {assignment} block, found {count}")
    marker = block.index(GENERATED_COMMENT)
    decoded = from_escaped_bytes(block[marker:])
    if not re.search(r"[\u3400-\u9fff]", decoded):
        raise ValueError(f"{culture}: generated culture pool contains no Chinese text")


def apply_to_culture_files(check: bool = False) -> dict[str, object]:
    contents = {path: path.read_bytes() for path in CULTURE_FILES}
    overhaul = CULTURE_DIRECTORY / "99_gdd_culture_overhaul.txt"
    if not check:
        contents[overhaul] = contents[overhaul].replace(
            OLD_INHERITED_COMMENT,
            NEW_INHERITED_COMMENT,
        )
    changed_cultures: list[str] = []
    for culture in CULTURE_SPECS:
        path, start, end = locate_culture(contents, culture)
        current_block = contents[path][start:end]
        expected_block = generated_culture_block(current_block, culture)
        if check:
            validate_generated_block(current_block, culture)
        elif current_block != expected_block:
            contents[path] = contents[path][:start] + expected_block + contents[path][end:]
            changed_cultures.append(culture)

    if not check:
        for path, data in contents.items():
            if path.read_bytes() != data:
                path.write_bytes(data)

    locations = {
        path.name: sum(1 for culture in CULTURE_SPECS if culture_spans(contents[path], culture))
        for path in CULTURE_FILES
    }
    return {
        "culture_name_pools": len(CULTURE_SPECS),
        "changed_cultures": changed_cultures,
        "definitions_by_file": locations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(apply_to_culture_files(check=args.check), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
