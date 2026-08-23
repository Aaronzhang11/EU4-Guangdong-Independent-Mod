#!/usr/bin/env python3
"""Build the Chinese 1.37 religion view with a compact practice readout."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "guangdong_independent_practice/interface/countryreligionview.gui"
DEFAULT_DEPENDENCY = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/workshop/content/236850/2976470733"
)
EXPECTED_DEPENDENCY_SHA256 = "ab1fd87cd2c54ba2fb334fd0353edfba84c8f223366bf64f048b76c4743cfd29"
DOCTRINE_STATUS = r'''

			# GDD: Visual-only overlay for the native invite-scholar button. It is
			# scripted so only Ritual Teaching countries replace the Islamic art;
			# alwaystransparent preserves the engine-owned button hitbox beneath it.
			iconType = {
				name = "zhx_lijiao_school_button_overlay"
				spriteType = "GFX_zhx_lijiao_school_button"
				position = { x = 180 y = 148 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			# GDD: Neutral cover for the transparent no-doctrine sentinel. It
			# occupies the same engine-owned button but cannot overlap the 礼鼎
			# overlay because retiring the doctrine also clears its flags.
			iconType = {
				name = "zhx_no_doctrine_school_button_overlay"
				spriteType = "GFX_zhx_no_doctrine_school_button"
				position = { x = 180 y = 148 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			# GDD: Compact, read-only practice value in the native school row.
			# The engine already renders the school name and emblem. Keeping this
			# value in the gap before invite_scholar_button avoids both the
			# Defender-of-Faith block and the province-conversion list.
			instantTextBoxType = {
				name = "zhx_religion_practice_value"
				position = { x = 151 y = 157 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 28
				maxHeight = 24
				format = centre
				scripted = yes
			}
'''


def find_named_window_close(text: str, name: str) -> int:
    """Return the matching closing brace for one named windowType block."""
    match = re.search(
        rf'windowType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    if match is None:
        raise ValueError(f'vanilla GUI is missing windowType "{name}"')

    opening = text.find("{", match.start())
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
    raise ValueError(f'windowType "{name}" has no matching closing brace')


def render(dependency_root: Path) -> str:
    source = dependency_root / "interface/countryreligionview.gui"
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_DEPENDENCY_SHA256:
        raise ValueError(
            "unsupported Chinese religion-view baseline: "
            f"{digest}; expected {EXPECTED_DEPENDENCY_SHA256}"
        )
    text = data.decode("utf-8")
    close = find_named_window_close(text, "countryreligionview")
    insertion = DOCTRINE_STATUS
    return text[:close] + insertion + text[close:]


def run(dependency_root: Path, check: bool) -> None:
    output = render(dependency_root)
    if check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != output:
            raise ValueError("country religion-view override is stale")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(output, encoding="utf-8")
    print(
        f"{'checked' if check else 'built'} Chinese 1.37 religion view; "
        "school-button overlays=2; compact native-row practice display=1"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dependency-root",
        "--vanilla-root",
        dest="dependency_root",
        type=Path,
        default=DEFAULT_DEPENDENCY,
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.dependency_root.resolve(), args.check)


if __name__ == "__main__":
    main()
