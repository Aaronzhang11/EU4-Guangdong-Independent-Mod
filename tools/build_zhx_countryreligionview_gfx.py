#!/usr/bin/env python3
"""Build EU4 1.37.5 religion GFX with ten patriarch-icon frames."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "guangdong_independent_practice/interface/countryreligionview.gfx"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
EXPECTED_VANILLA_SHA256 = (
    "2d2705b073cc82c7d96de43cc8c31168f77f926069d0f93df0fd1749365c23a4"
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
    raise ValueError("sprite block has no matching closing brace")


def render(vanilla_root: Path) -> str:
    source = vanilla_root / "interface/countryreligionview.gfx"
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_VANILLA_SHA256:
        raise ValueError(
            "unsupported vanilla religion-GFX baseline: "
            f"{digest}; expected EU4 1.37.5 {EXPECTED_VANILLA_SHA256}"
        )
    text = data.decode("utf-8")
    match = re.search(
        r'spriteType\s*=\s*\{\s*name\s*=\s*"GFX_russian_icons_strip"',
        text,
    )
    if match is None:
        raise ValueError("GFX_russian_icons_strip is missing")
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    block = text[match.start() : closing + 1]
    block, count = re.subn(
        r"(noOfFrames\s*=\s*)5\b",
        r"\g<1>10",
        block,
        count=1,
    )
    if count != 1:
        raise ValueError("GFX_russian_icons_strip is no longer a five-frame baseline")
    output = text[: match.start()] + block + text[closing + 1 :]
    # Keep the generated full-file override deterministic without preserving
    # incidental trailing whitespace from the vanilla baseline.
    lines = [line.rstrip() for line in output.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def run(vanilla_root: Path, check: bool) -> None:
    output = render(vanilla_root)
    if check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != output:
            raise ValueError("generated countryreligionview.gfx is stale")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(output, encoding="utf-8")
    print(
        f"{'checked' if check else 'built'} EU4 1.37.5 religion GFX; "
        "patriarch-icon frames=10"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.vanilla_root.resolve(), args.check)


if __name__ == "__main__":
    main()
