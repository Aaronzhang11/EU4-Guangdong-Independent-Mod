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
    (
        "zhx_ru_school",
        "GFX_zhx_doctrine_ru_school",
        "zhx_ru_invited_scholar_modifier",
    ),
    (
        "zhx_fa_school",
        "GFX_zhx_doctrine_fa_school",
        "zhx_fa_invited_scholar_modifier",
    ),
    (
        "zhx_mo_school",
        "GFX_zhx_doctrine_mo_school",
        "zhx_mo_invited_scholar_modifier",
    ),
    (
        "zhx_dao_school",
        "GFX_zhx_doctrine_dao_school",
        "zhx_dao_invited_scholar_modifier",
    ),
    (
        "zhx_bing_school",
        "GFX_zhx_doctrine_bing_school",
        "zhx_bing_invited_scholar_modifier",
    ),
    (
        "zhx_zongheng_school",
        "GFX_zhx_doctrine_zongheng_school",
        "zhx_zongheng_invited_scholar_modifier",
    ),
)
NO_DOCTRINE_SCHOOL = (
    "zhx_no_doctrine_school",
    "GFX_zhx_no_doctrine_school",
)
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
\t\t\t# The native selector supplies FROM as a country whose permanent
\t\t\t# school matches this entry. The source must know and esteem THIS;
\t\t\t# the player's permanent doctrine and practice remain untouched.
\t\t\tpotential_invite_scholar = {{
\t\t\t\treligion = confucianism
\t\t\t\thas_religious_school = yes
\t\t\t\tNOT = {{
\t\t\t\t\treligious_school = {{
\t\t\t\t\t\tgroup = eastern
\t\t\t\t\t\tschool = zhx_no_doctrine_school
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t\tNOT = {{
\t\t\t\t\treligious_school = {{
\t\t\t\t\t\tgroup = eastern
\t\t\t\t\t\tschool = {school}
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t\tknows_of_scholar_country_capital_trigger = yes
\t\t\t}}
\t\t\tcan_invite_scholar = {{
\t\t\t\treverse_has_opinion = {{ who = FROM value = 150 }}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ ai = yes }}
\t\t\t\t\tNOT = {{ has_country_modifier = has_invited_scholar_recently }}
\t\t\t\t}}
\t\t\t\tNOT = {{ has_country_modifier = {modifier} }}
\t\t\t}}
\t\t\ton_invite_scholar = {{
\t\t\t\tzhx_clear_invited_school_modifiers = yes
\t\t\t\tcustom_tooltip = zhx_invite_school_country_tt
\t\t\t\tadd_country_modifier = {{ name = {modifier} duration = 7300 }}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ ai = yes }}
\t\t\t\t\tadd_country_modifier = {{
\t\t\t\t\t\tname = has_invited_scholar_recently
\t\t\t\t\t\tduration = 7300
\t\t\t\t\t\thidden = yes
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}}
\t\t\tinvite_scholar_modifier_display = {modifier}
\t\t\tpicture = "{picture}"
\t\t}}
'''
        for school, picture, modifier in SCHOOLS
    )
    no_doctrine, no_doctrine_picture = NO_DOCTRINE_SCHOOL
    sentinel = f'''\
\t\t{no_doctrine} = {{
\t\t\tpotential_invite_scholar = {{ always = no }}
\t\t\tcan_invite_scholar = {{ always = no }}
\t\t\ton_invite_scholar = {{ }}
\t\t\tpicture = "{no_doctrine_picture}"
\t\t}}
'''
    return f'''\

\t# ZHX native school mirrors. Doctrine flags and practice remain authoritative.
\t# The six visible schools also expose the native scholar selector: a foreign
\t# school whose country knows us and has 150 opinion can grant one temporary,
\t# entry-tier modifier. The transparent no-doctrine sentinel remains inert.
\treligious_schools = {{
{definitions}{sentinel}\t}}
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
