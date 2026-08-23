#!/usr/bin/env python3
"""Build EU4 1.37.5 religions with ZHX schools and adapted Nestorianism."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "guangdong_independent_practice/common/religions/00_religion.txt"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
EXPECTED_VANILLA_SHA256 = (
    "609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6"
)
SCHOOLS = (
    ("zhx_ru_school", "GFX_zhx_doctrine_ru_school"),
    ("zhx_fa_school", "GFX_zhx_doctrine_fa_school"),
    ("zhx_mo_school", "GFX_zhx_doctrine_mo_school"),
    ("zhx_dao_school", "GFX_zhx_doctrine_dao_school"),
    ("zhx_bing_school", "GFX_zhx_doctrine_bing_school"),
    ("zhx_zongheng_school", "GFX_zhx_doctrine_zongheng_school"),
)
NO_DOCTRINE_SCHOOL = (
    "zhx_no_doctrine_school",
    "GFX_zhx_no_doctrine_school",
)
ALL_SCHOOLS = SCHOOLS + (NO_DOCTRINE_SCHOOL,)


def build_nestorian_block() -> str:
    """Return the adapted Ante Bellum patriarch/icon mechanic.

    Five Orthodox entries are deliberately kept first and hidden.  EU4 uses
    definition order to address ``GFX_russian_icons_strip`` frames, so the
    visible Nestorian icons then map to frames 6-10 of our extended strip.
    """
    return r'''

	# ZHX: adapted from Ante Bellum's Church-of-the-East implementation.
	# The patriarch-authority shell and five-icon cadence are retained, while
	# Ante Bellum-only missions, monuments and St Timur unlocks are excluded.
	nestorian = {
		flags_with_emblem_percentage = 0
		flag_emblem_index_range = { 1 44 }
		color = { 255 199 44 }
		icon = 7

		country = {
			religious_unity = 0.15
			missionaries = 1
		}
		allowed_center_conversion = {
			catholic
			protestant
			hussite
			anglican
			reformed
		}
		country_as_secondary = {
			religious_unity = 0.1
			global_missionary_strength = 0.01
		}
		province = {
			local_missionary_strength = -0.02
		}

		has_patriarchs = yes
		misguided_heretic = yes
		heretic = { OLD_BELIEVER MOLOKAN DUKHOBOR KHLYST SKOPTSY ICONOCLAST }

		orthodox_icons = {
			# Hidden frame anchors preserve vanilla Orthodox art in frames 1-5.
			icon_michael = {
				discipline = 0.05
				manpower_recovery_speed = 0.1
				allow = { religion = orthodox }
				visible = { religion = orthodox }
				ai_will_do = { factor = 0 }
			}
			icon_eleusa = {
				global_unrest = -3
				harsh_treatment_cost = -0.25
				allow = { religion = orthodox }
				visible = { religion = orthodox }
				ai_will_do = { factor = 0 }
			}
			icon_pancreator = {
				development_cost = -0.10
				build_cost = -0.1
				allow = { religion = orthodox }
				visible = { religion = orthodox }
				ai_will_do = { factor = 0 }
			}
			icon_nicholas = {
				improve_relation_modifier = 0.25
				ae_impact = -0.1
				allow = { religion = orthodox }
				visible = { religion = orthodox }
				ai_will_do = { factor = 0 }
			}
			icon_climacus = {
				global_institution_spread = 0.25
				embracement_cost = -0.2
				allow = { religion = orthodox }
				visible = { religion = orthodox }
				ai_will_do = { factor = 0 }
			}

			icon_nestorius = {
				diplomatic_reputation = 1
				ae_impact = -0.1
				allow = { religion = nestorian }
				visible = { religion = nestorian }
				ai_will_do = {
					factor = 1
					modifier = { factor = 0 is_at_war = no }
					modifier = { factor = 3 is_in_important_war = yes }
				}
			}
			icon_mar_yelv = {
				global_unrest = -2
				reform_progress_growth = 0.2
				allow = { religion = nestorian }
				visible = { religion = nestorian }
				ai_will_do = {
					factor = 1
					modifier = { factor = 2 unrest = 4 }
				}
			}
			icon_jinghui = {
				global_missionary_strength = 0.02
				missionary_maintenance_cost = -0.25
				allow = { religion = nestorian }
				visible = { religion = nestorian }
				ai_will_do = { factor = 0 }
			}
			icon_thomas = {
				stability_cost_modifier = -0.25
				global_autonomy = -0.05
				allow = { religion = nestorian }
				visible = { religion = nestorian }
				ai_will_do = { factor = 0.5 }
			}
			icon_anthony = {
				land_morale = 0.1
				warscore_cost_vs_other_religion = -0.1
				allow = { religion = nestorian }
				visible = { religion = nestorian }
				ai_will_do = {
					factor = 1
					modifier = { factor = 0 is_at_war = no }
					modifier = { factor = 3 is_in_important_war = yes }
				}
			}
		}
	}
'''


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
    raise ValueError("religion group has no matching closing brace")


def build_school_block() -> str:
    definitions = "".join(
        f'''\
\t\t{school} = {{
\t\t\tpotential_invite_scholar = {{ always = no }}
\t\t\tcan_invite_scholar = {{ always = no }}
\t\t\ton_invite_scholar = {{ }}
\t\t\tpicture = "{picture}"
\t\t}}
'''
        for school, picture in ALL_SCHOOLS
    )
    return f'''\

\t# ZHX display mirrors. Doctrine flags remain authoritative; the six visible
\t# schools and transparent no-doctrine sentinel have no numeric modifiers.
\t# Both invitation gates stay closed: no scholar can be browsed or invited.
\treligious_schools = {{
{definitions}\t}}
'''


def append_to_group(text: str, group: str, block: str, unique_key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(group)}\s*=\s*\{{", text)
    if match is None:
        raise ValueError(f'vanilla religions are missing top-level group "{group}"')
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    body = text[opening + 1 : closing]
    if re.search(rf"(?m)^\s*{re.escape(unique_key)}\s*=\s*\{{", body):
        raise ValueError(f'{group} already defines "{unique_key}"')
    return text[:closing] + block + text[closing:]


def render(vanilla_root: Path) -> str:
    source = vanilla_root / "common/religions/00_religion.txt"
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_VANILLA_SHA256:
        raise ValueError(
            "unsupported vanilla religion baseline: "
            f"{digest}; expected EU4 1.37.5 {EXPECTED_VANILLA_SHA256}"
        )
    text = data.decode("utf-8")
    text = append_to_group(text, "christian", build_nestorian_block(), "nestorian")

    match = re.search(r"(?m)^eastern\s*=\s*\{", text)
    if match is None:
        raise ValueError('generated religions are missing top-level group "eastern"')
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    eastern_body = text[opening + 1 : closing]
    if "religious_schools" in eastern_body:
        raise ValueError('vanilla group "eastern" already defines religious_schools')
    return text[: opening + 1] + build_school_block() + text[opening + 1 :]


def run(vanilla_root: Path, check: bool) -> None:
    output = render(vanilla_root)
    if check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != output:
            raise ValueError("generated 1.37.5 religion override is stale")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(output, encoding="utf-8")
    print(
        f"{'checked' if check else 'built'} EU4 1.37.5 religions; "
        f"visible eastern mirrors={len(SCHOOLS)}; transparent sentinels=1; "
        "Nestorian patriarch icons=5"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.vanilla_root.resolve(), args.check)


if __name__ == "__main__":
    main()
