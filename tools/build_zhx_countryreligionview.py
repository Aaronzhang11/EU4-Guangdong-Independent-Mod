#!/usr/bin/env python3
"""Build the Chinese 1.37 religion view with native-school doctrine controls."""

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
TENSION_SPRITE_REPLACEMENTS = {
    'name ="low_harmony"\n\t\t\t\tspriteType = "GFX_low_harmony"': (
        'name ="low_harmony"\n'
        '\t\t\t\tspriteType = "GFX_zhx_thought_tension_low"'
    ),
    'name ="high_harmony"\n\t\t\t\tspriteType = "GFX_high_harmony"': (
        'name ="high_harmony"\n'
        '\t\t\t\tspriteType = "GFX_zhx_thought_tension_high"'
    ),
}
HARMONY_DYNAMIC_CONTROL_REPLACEMENTS = {
    'name = "harmonizing_with_button"\n\t\t\t\tposition = { x = 275 y = 261 }': (
        'name = "harmonizing_with_button"\n'
        '\t\t\t\tposition = { x = 2000 y = 2000 }'
    ),
    'name ="harmonizing_with_icon"\n\t\t\t\tspriteType = "GFX_icon_religion_small"\n'
    '\t\t\t\tposition = { x= 280 y = 265 }': (
        'name ="harmonizing_with_icon"\n'
        '\t\t\t\tspriteType = "GFX_icon_religion_small"\n'
        '\t\t\t\tposition = { x= 2000 y = 2000 }'
    ),
    'name ="harmonization_progress"\n\t\t\t\tspriteType = "GFX_treasure_fleet_progressbar2"\n'
    '\t\t\t\tposition = { x= 322 y = 291 }': (
        'name ="harmonization_progress"\n'
        '\t\t\t\tspriteType = "GFX_treasure_fleet_progressbar2"\n'
        '\t\t\t\tposition = { x= 2000 y = 2000 }'
    ),
    'name ="harmonization_progress_frame"\n'
    '\t\t\t\tspriteType = "GFX_treasure_fleet_progress_frame2"\n'
    '\t\t\t\tposition = { x= 315 y = 263 }': (
        'name ="harmonization_progress_frame"\n'
        '\t\t\t\tspriteType = "GFX_treasure_fleet_progress_frame2"\n'
        '\t\t\t\tposition = { x= 2000 y = 2000 }'
    ),
    'name ="harmonized_listbox"\n\t\t\t\tposition = { x = 35 y = 300 }': (
        'name ="harmonized_listbox"\n'
        '\t\t\t\tposition = { x = 2000 y = 2000 }'
    ),
}
DOCTRINE_STATUS = r'''

			# GDD: The engine-owned Confucian harmony widget cannot be rebound to
			# academy state. This late-drawn panel preserves every required native
			# control underneath, but replaces the visible 0-100 meter with the four
			# actual thought-tension tiers maintained by the academy lifecycle.
			iconType = {
				name = "zhx_thought_tension_panel_bg"
				spriteType = "GFX_religion_overlay_big_bg"
				position = { x = 26 y = 231 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_thought_tension_panel_label"
				position = { x = 40 y = 245 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 230
				maxHeight = 24
				Orientation = "UPPER_LEFT"
				format = centre
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_progress_bg"
				spriteType = "GFX_piety_bar_bg"
				position = { x = 62 y = 276 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_progress_frame"
				spriteType = "GFX_ideaView_progress_frame_long"
				position = { x = 55 y = 273 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_low_endpoint"
				spriteType = "GFX_zhx_thought_tension_low"
				position = { x = 38 y = 265 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_high_endpoint"
				spriteType = "GFX_zhx_thought_tension_high"
				position = { x = 238 y = 265 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			# Four fixed anchors quantize the old continuous pointer. Their
			# custom-gui potentials are deliberately mutually exclusive.
			iconType = {
				name = "zhx_thought_tension_none_indicator"
				spriteType = "GFX_war_overview_indicator"
				position = { x = 64 y = 273 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_mild_indicator"
				spriteType = "GFX_war_overview_indicator"
				position = { x = 106 y = 273 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_medium_indicator"
				spriteType = "GFX_war_overview_indicator"
				position = { x = 148 y = 273 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_thought_tension_heavy_indicator"
				spriteType = "GFX_war_overview_indicator"
				position = { x = 190 y = 273 }
				Orientation = "UPPER_LEFT"
				alwaystransparent = yes
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_thought_tension_none_label"
				position = { x = 64 y = 279 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 52
				maxHeight = 24
				format = centre
				alwaystransparent = yes
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_thought_tension_mild_label"
				position = { x = 106 y = 279 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 52
				maxHeight = 24
				format = centre
				alwaystransparent = yes
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_thought_tension_medium_label"
				position = { x = 148 y = 279 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 52
				maxHeight = 24
				format = centre
				alwaystransparent = yes
				scripted = yes
			}

			instantTextBoxType = {
				name = "zhx_thought_tension_heavy_label"
				position = { x = 190 y = 279 }
				font = "vic_18"
				borderSize = { x = 0 y = 0 }
				text = ""
				maxWidth = 52
				maxHeight = 24
				format = centre
				alwaystransparent = yes
				scripted = yes
			}

			# A panel-sized invisible top button owns hover and blocks the obsolete
			# native harmonisation selector that still exists beneath the repaint.
			guiButtonType = {
				name = "zhx_thought_tension_tooltip_button"
				quadTextureSprite = "GFX_zhx_thought_tension_hitbox"
				position = { x = 26 y = 231 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			# GDD: The Ritual Teaching tripod is a mouse-transparent reskin of
			# the engine-owned invite_scholar_button beneath it. The native button
			# therefore remains the sole owner of future school invitations.
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

			# GDD: religious_schools belongs to the whole eastern group, so the
			# engine also instantiates its Islamic-looking invite button for Buddhist
			# and Shinto countries. This later, non-transparent inert button restores
			# the panel/divider and closes the banner with a mirrored scroll cap while
			# owning the hit target; gameplay remains fail-closed in all three native
			# invitation script gates.
			guiButtonType = {
				name = "zhx_non_lijiao_invite_school_blocker"
				spriteType = "GFX_zhx_non_lijiao_school_button_blocker"
				position = { x = 180 y = 148 }
				size = { x = 42 y = 42 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			# GDD: The engine-owned school sub-modifier icon only exposes the
			# school name. Six mutually-exclusive, fully transparent 26x26 icons
			# sit on that exact slot and supply the complete school-card tooltip.
			iconType = {
				name = "zhx_religion_school_ru_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			iconType = {
				name = "zhx_religion_school_fa_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			iconType = {
				name = "zhx_religion_school_mo_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			iconType = {
				name = "zhx_religion_school_dao_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			iconType = {
				name = "zhx_religion_school_bing_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			iconType = {
				name = "zhx_religion_school_zongheng_tooltip_icon"
				spriteType = "GFX_zhx_school_tooltip_hitbox"
				position = { x = 93 y = 193 }
				Orientation = "UPPER_LEFT"
				scripted = yes
			}

			# GDD: An invited scholar is a static religion sub-modifier, so the
			# engine draws the icon of its first numeric effect rather than the
			# source school's picture. These mutually-exclusive, mouse-transparent
			# overlays cover that second native slot with the actual 52px school
			# emblem at the same 0.5 scale. The native item underneath retains its
			# exact modifier and expiry tooltip.
			iconType = {
				name = "zhx_invited_school_ru_icon"
				spriteType = "GFX_zhx_doctrine_ru_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_invited_school_fa_icon"
				spriteType = "GFX_zhx_doctrine_fa_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_invited_school_mo_icon"
				spriteType = "GFX_zhx_doctrine_mo_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_invited_school_dao_icon"
				spriteType = "GFX_zhx_doctrine_dao_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_invited_school_bing_icon"
				spriteType = "GFX_zhx_doctrine_bing_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			iconType = {
				name = "zhx_invited_school_zongheng_icon"
				spriteType = "GFX_zhx_doctrine_zongheng_school"
				position = { x = 124 y = 193 }
				Orientation = "UPPER_LEFT"
				scale = 0.5
				alwaystransparent = yes
				scripted = yes
			}

			# GDD: Four mutually-exclusive practice values share
			# the same native-school-row anchor. The engine already renders the
			# school name and emblem; this 28x24 gap is clear of both the invite
			# button and Defender of the Faith. Localisation retains the tier colour;
			# its tooltip lists only cached factors that currently contribute.
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

			# GDD: One fully transparent 28x24 button owns hover and click input
			# for all four mutually-exclusive practice readouts. The coloured text
			# remains visible underneath; clicking opens the complete rulebook.
			guiButtonType = {
				name = "zhx_religion_practice_rules_button"
				quadTextureSprite = "GFX_zhx_practice_click_hitbox"
				position = { x = 151 y = 157 }
				Orientation = "UPPER_LEFT"
				clicksound = click
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
    for old, new in TENSION_SPRITE_REPLACEMENTS.items():
        if text.count(old) != 1:
            raise ValueError(
                "Chinese religion-view baseline no longer has exactly one "
                f"thought-tension endpoint block: {old!r}"
            )
        text = text.replace(old, new, 1)
    for old, new in HARMONY_DYNAMIC_CONTROL_REPLACEMENTS.items():
        if text.count(old) != 1:
            raise ValueError(
                "Chinese religion-view baseline no longer has exactly one "
                f"harmony dynamic-control block: {old!r}"
            )
        text = text.replace(old, new, 1)
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
        "native school-button overlays=1; non-Lijiao blockers=1; "
        "school-tooltip hit targets=6; "
        "invited-school emblem overlays=6; "
        "no-doctrine overlays=1; "
        "thought-tension endpoint reskins=2; hidden harmony dynamics=5; "
        "four-tier tension panels=1; "
        "mutually-exclusive tier practice displays=4; "
        "practice-number hit targets=1; hover-factor readouts=4"
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
