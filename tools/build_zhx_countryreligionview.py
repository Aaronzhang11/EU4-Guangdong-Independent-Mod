#!/usr/bin/env python3
"""Build the Chinese 1.37 religion view with tier-coloured practice readouts."""

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

			# GDD: Four mutually-exclusive, tier-coloured practice values share
			# the same native-school-row anchor. The engine already renders the
			# school name and emblem; this 28x24 gap is clear of both the invite
			# button and Defender of the Faith.
			instantTextBoxType = {
				name = "zhx_religion_practice_hollow_value"
				position = { x = 151 y = 157 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 28
				maxHeight = 24
				format = centre
				scripted = yes
			}

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

			instantTextBoxType = {
				name = "zhx_religion_practice_flourishing_value"
				position = { x = 151 y = 157 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 28
				maxHeight = 24
				format = centre
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_religion_practice_exemplary_value"
				position = { x = 151 y = 157 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 28
				maxHeight = 24
				format = centre
				scripted = yes
			}

			# GDD: Four transparent hit targets sit over the four mutually-exclusive
			# practice readouts. Only the matching tier is enabled by custom_gui, so
			# clicking the visible number opens one reusable on-demand ledger event.
			guiButtonType = {
				name = "zhx_religion_practice_hollow_ledger_button"
				position = { x = 151 y = 157 }
				quadTextureSprite = "GFX_resource_transparent"
				buttonText = ""
				Orientation = "UPPER_LEFT"
				clicksound = click
				scale = 0.875
				scripted = yes
			}

			guiButtonType = {
				name = "zhx_religion_practice_established_ledger_button"
				position = { x = 151 y = 157 }
				quadTextureSprite = "GFX_resource_transparent"
				buttonText = ""
				Orientation = "UPPER_LEFT"
				clicksound = click
				scale = 0.875
				scripted = yes
			}

			guiButtonType = {
				name = "zhx_religion_practice_flourishing_ledger_button"
				position = { x = 151 y = 157 }
				quadTextureSprite = "GFX_resource_transparent"
				buttonText = ""
				Orientation = "UPPER_LEFT"
				clicksound = click
				scale = 0.875
				scripted = yes
			}

			guiButtonType = {
				name = "zhx_religion_practice_exemplary_ledger_button"
				position = { x = 151 y = 157 }
				quadTextureSprite = "GFX_resource_transparent"
				buttonText = ""
				Orientation = "UPPER_LEFT"
				clicksound = click
				scale = 0.875
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
        "school-button overlays=2; mutually-exclusive tier practice displays=4; "
        "practice-ledger hit targets=4"
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
