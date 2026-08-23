#!/usr/bin/env python3
"""Build the Chinese 1.37 diplomacy view with safe school/name spacing."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "guangdong_independent_practice/interface/countrydiplomacyview.gui"
DEFAULT_DEPENDENCY = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/workshop/content/236850/2976470733"
)
EXPECTED_DEPENDENCY_SHA256 = (
    "74a02752cfc622ebcfbac1a359a7efe07fe6cbbec4a359987f67f205e113de4a"
)


def matching_close(text: str, opening: int) -> int:
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("GUI block has no matching closing brace")


def named_block_span(text: str, block_type: str, name: str) -> tuple[int, int]:
    match = re.search(
        rf'{re.escape(block_type)}\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"',
        text,
    )
    if match is None:
        raise ValueError(f'{block_type} "{name}" is missing')
    opening = text.find("{", match.start())
    return match.start(), matching_close(text, opening) + 1


def replace_text_box_layout(
    text: str,
    name: str,
    *,
    old_x: int,
    new_x: int,
    old_width: int,
    new_width: int,
) -> str:
    start, end = named_block_span(text, "instantTextBoxType", name)
    block = text[start:end]
    shifted, position_count = re.subn(
        rf"(position\s*=\s*\{{\s*x\s*=\s*){old_x}(\s+y\s*=)",
        rf"\g<1>{new_x}\2",
        block,
        count=1,
    )
    shifted, width_count = re.subn(
        rf"(maxWidth\s*=\s*){old_width}\b",
        rf"\g<1>{new_width}",
        shifted,
        count=1,
    )
    if position_count != 1 or width_count != 1:
        raise ValueError(f'{name} no longer matches the expected Chinese GUI layout')
    return text[:start] + shifted + text[end:]


def render(dependency_root: Path) -> str:
    source = dependency_root / "interface/countrydiplomacyview.gui"
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_DEPENDENCY_SHA256:
        raise ValueError(
            "unsupported Chinese diplomacy-view baseline: "
            f"{digest}; expected {EXPECTED_DEPENDENCY_SHA256}"
        )
    text = data.decode("utf-8")

    school_start, school_end = named_block_span(
        text, "iconType", "religious_school_icon"
    )
    school = text[school_start:school_end]
    if not (
        re.search(r"position\s*=\s*\{\s*x\s*=\s*110\s+y\s*=\s*142\s*\}", school)
        and re.search(r"scale\s*=\s*0\.5\b", school)
    ):
        raise ValueError("religious_school_icon no longer matches the supported layout")

    # At 52 px × 0.5 the native school icon reaches x=136. Moving the two
    # adjacent labels to x=142 leaves a six-pixel gutter. The engine shifts
    # them twenty pixels left when no school/secondary religion is visible,
    # which still leaves the primary religion badge unobstructed.
    text = replace_text_box_layout(
        text,
        "label_nation",
        old_x=132,
        new_x=142,
        old_width=200,
        new_width=190,
    )
    text = replace_text_box_layout(
        text,
        "label_fog",
        old_x=132,
        new_x=142,
        old_width=170,
        new_width=160,
    )
    return text


def run(dependency_root: Path, check: bool) -> None:
    output = render(dependency_root)
    if check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != output:
            raise ValueError("generated diplomacy-view override is stale")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(output, encoding="utf-8")
    print(
        f"{'checked' if check else 'built'} Chinese 1.37 diplomacy view; "
        "school/name gutter=6px"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dependency-root", type=Path, default=DEFAULT_DEPENDENCY
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.dependency_root.resolve(), args.check)


if __name__ == "__main__":
    main()
