#!/usr/bin/env python3
"""Build the pinned vanilla overrides needed to retire Confucian harmony.

The Ritual Teaching system owns doctrine practice and thought tension.  This
builder only repairs vanilla content which would otherwise keep calling the
removed Harmony API or leave mission conditions permanently unreachable.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
DEFAULT_VANILLA = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)

BASELINES = {
    "missions/DOM_Chinese_Missions.txt": "21727d7cd800461dfd637f7c2e4e334470e620ff66bae255ba7ac9a069a10ed5",
    "missions/DOM_Japanese_Missions.txt": "55917ac903b47ba943ed8e0256bdd19af7bec65443e2f72a633e3d4cded98525",
    "missions/Japanese_Missions.txt": "67b3f0abb6276fb11f2688c2f7269eb9086e0afd7a2d778e6bc4bf856c028fd5",
    "missions/Korean_Missions.txt": "66c4db9d89f62bc14966ea8d1456b30a3bb1aa84d4e6a056e85eb200cbfae207",
    "missions/Manchu_Missions.txt": "38e75e7ff7f7ea36b64d42ffb80a9f23bccf667b1fed314e3f25a7dfaea23d55",
    "missions/zzz_WoC_Shared_Horde_Missions.txt": "d3e73c6132a5bc542546082ca06be586356e73fa9da2e2135645713c6a34430c",
    "missions/zzzz_WoC_EoC_Yuan_Missions.txt": "4e28b76336e0d71da04b00d8c79b87583fb16a0c63b8911adc7e991870fed529",
    "decisions/ManchuDecisions.txt": "218489c34f6738ae05483ae35b128fafc3326b222fa64bbe28012eeebf557046",
    "events/Shinto.txt": "d7e912a50840ee93115601ce3fe8d034c87cb264f8403b2cc86b6ea026109fab",
    "events/Confucianism.txt": "c513ced4936d3da6c0eaa973897b5db48761f1eb7f52b6cbf6bd9fb27aa3e443",
    "common/scripted_effects/01_scripted_effects_for_estates.txt": "fa3f71509f86ea6b137e104336280f7b8eb49a712eeced918d670829dc04a8f1",
    "decisions/ShintoConversion.txt": "ebc0ed67014ecbec2af605dfe1f137b47decc5da52c4b51fb584657537124a66",
    "common/scripted_effects/02_scripted_effects_preview_missions.txt": "ee0cb773fa4ac1bc05b939f6c39e23f2a1cabf89fe8dbda531577de26f468e21",
    "common/rebel_types/confucianism.txt": "dc5edba6e27549a9de0c88eec8a0130be2e545bbe814749f7d052255eff45042",
    "events/Religious.txt": "2b85a411f0fe51d46fee788b4e248942a518a39372a1d83c0f242782e2636a50",
}


def read_pinned(vanilla_root: Path, relative: str) -> str:
    path = vanilla_root / relative
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    expected = BASELINES[relative]
    if digest != expected:
        raise ValueError(
            f"unsupported vanilla baseline for {relative}: {digest}; "
            f"expected EU4 1.37.5 {expected}"
        )
    # Several 1.37.5 script baselines contain Windows-1252/Latin-1 bytes in
    # comments. Latin-1 is used as a lossless byte-preserving transport; every
    # injected retirement token is ASCII.
    return data.decode("latin-1")


def replace_exact(text: str, old: str, new: str, *, count: int, label: str) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(f"{label}: expected {count} source matches, found {actual}")
    return text.replace(old, new)


def render_simple_cohesion(text: str, *, harmony: int, count: int, label: str) -> str:
    return replace_exact(
        text,
        f"harmony = {harmony} ",
        f"zhx_lijiao_cohesion_{harmony} = yes ",
        count=count,
        label=label,
    )


def render_dom_chinese(text: str) -> str:
    text = render_simple_cohesion(text, harmony=90, count=1, label="DOM Chinese harmony 90")
    return render_simple_cohesion(text, harmony=80, count=1, label="DOM Chinese harmony 80")


def render_dom_japanese(text: str) -> str:
    return render_simple_cohesion(text, harmony=90, count=1, label="DOM Japanese harmony 90")


def render_japanese(text: str) -> str:
    return replace_exact(
        text,
        "ROOT = { has_harmonized_with = PREV }",
        "tolerance_to_this = 3",
        count=4,
        label="Japanese Ainu religious accommodation",
    )


def render_korean(text: str) -> str:
    old_reward = """if = {
\t\t\t\tlimit = {
\t\t\t\t\thas_dlc = \"Mandate of Heaven\"
\t\t\t\t\tis_harmonizing_with = shinto
\t\t\t\t}
\t\t\t\tadd_harmonization_progress = 15
\t\t\t}
\t\t\telse_if = {
\t\t\t\tlimit = { has_harmonized_with = shinto }
\t\t\t\tadd_mil_power = 100
\t\t\t}
\t\t\telse_if = {
\t\t\t\tlimit = {
\t\t\t\t\thas_dlc = \"Mandate of Heaven\"
\t\t\t\t\tNOT = { has_harmonized_with = shinto }
\t\t\t\t\treligion = confucianism
\t\t\t\t}
\t\t\t\tcustom_tooltip = kor_defeat_shogun_tt
\t\t\t}
\t\t\telse = {
\t\t\t\tadd_mil_power = 100
\t\t\t}"""
    text = replace_exact(
        text,
        old_reward,
        "add_mil_power = 100",
        count=1,
        label="Korean Shinto harmonization reward",
    )
    text = replace_exact(
        text,
        "has_harmonized_with = shinto",
        "has_global_modifier_value = { which = tolerance_heretic value = 3 }",
        count=1,
        label="Korean Shinto accommodation mission",
    )
    return render_simple_cohesion(text, harmony=90, count=1, label="Korean harmony 90")


def render_manchu_missions(text: str) -> str:
    return replace_exact(
        text,
        "\t\t\t\tharmony = 100\n\t\t\t\tnum_of_harmonized = 3",
        "\t\t\t\tzhx_lijiao_cohesion_100 = yes\n\t\t\t\treligious_unity = 1",
        count=1,
        label="Manchu harmonious empire",
    )


def render_horde_missions(text: str) -> str:
    text = replace_exact(
        text,
        '''\t\t\t\t\t\t\tOR = {
\t\t\t\t\t\t\t\treligion = confucianism
\t\t\t\t\t\t\t\tis_or_was_mongol_nation = yes
\t\t\t\t\t\t\t}''',
        "\t\t\t\t\t\t\treligion = confucianism",
        count=1,
        label="Horde Confucian branch eligibility",
    )
    text = replace_exact(
        text,
        "has_harmonized_with = pagan",
        "has_global_modifier_value = { which = tolerance_heathen value = 3 }",
        count=1,
        label="Horde pagan accommodation",
    )
    return replace_exact(
        text,
        "\t\t\t\tnum_of_harmonized = 4\n\t\t\t\tharmony = 75",
        "\t\t\t\tzhx_lijiao_cohesion_75 = yes\n\t\t\t\treligious_unity = 0.9\n\t\t\t\thas_global_modifier_value = { which = tolerance_heathen value = 3 }",
        count=1,
        label="Horde plural empire",
    )


def render_yuan(text: str) -> str:
    return render_simple_cohesion(text, harmony=90, count=1, label="Yuan harmony 90")


def render_manchu_decisions(text: str) -> str:
    return replace_exact(
        text,
        """\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\tNOT = { religion = confucianism }
\t\t\t\t}
\t\t\t\tchange_religion = confucianism
\t\t\t\tadd_harmonized_religion = tengri_pagan_reformed
\t\t\t}
""",
        "",
        count=1,
        label="Manchu formation forced Ritual Teaching conversion",
    )


def render_shinto(text: str) -> str:
    text = replace_exact(
        text,
        "\n\t\tadd_harmonized_religion = shinto",
        "",
        count=1,
        label="Shinto conversion harmonized religion",
    )
    return replace_exact(
        text,
        '\t\tname = "shinto_events.46.b" #\n\t\tai_chance = {\n\t\t\tfactor = 20\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0.1',
        '\t\tname = "shinto_events.46.b" #\n\t\ttrigger = { always = no } # ZHX: non-Zhuxia states cannot adopt Ritual Teaching here\n\t\tai_chance = {\n\t\t\tfactor = 20\n\t\t\tmodifier = {\n\t\t\t\tfactor = 0.1',
        count=1,
        label="Shinto forced Ritual Teaching conversion option",
    )


def render_confucian_events(_text: str) -> str:
    # The vanilla engine/on_actions still name completion events 1-10 and pulse
    # events 19-20. Inert stubs preserve those external IDs without leaving an
    # active Harmony path. Events 11-18 and Dai Viet's non-Zhuxia conversion
    # event 21 have no required external callers and are deliberately absent.
    pictures = {
        19: "MERITOCRACY_eventPicture",
        20: "IMPERIAL_EXAMINATION_eventPicture",
    }
    stubs = "\n".join(
        f'''country_event = {{
\tid = confucian_events.{event_id}
\ttitle = "confucian_events.{event_id}.t"
\tdesc = "confucian_events.{event_id}.d"
\tpicture = {pictures.get(event_id, "NEO_CONFUCIANISM_INCIDENT_eventPicture")}
\thidden = yes
\tis_triggered_only = yes
\ttrigger = {{ always = no }}
\toption = {{ name = OK }}
}}'''
        for event_id in (*range(1, 11), 19, 20)
    )
    return f'''# ZHX: vanilla Confucian Harmony event lifecycle retired.
namespace = confucian_events

{stubs}
'''


def render_estate_scripted_effects(text: str) -> str:
    old = '''\tif = {
\t\tlimit = {
\t\t\treligion = confucianism
\t\t}
\t\tadd_harmony = 5
\t}
\tif = {
\t\tlimit = {
\t\t\tharmonization_progress = 1
\t\t}
\t\tadd_harmonization_progress = 1
\t}
'''
    text = replace_exact(
        text,
        old,
        "",
        count=1,
        label="institutionalized clergy live Harmony reward",
    )
    text, negated_count = re.subn(
        r"(?m)^[ \t]*owner = \{ NOT = \{ has_harmonized_with = PREV \} \}\s*\n",
        "",
        text,
    )
    if negated_count != 1:
        raise ValueError(
            "estate religious acceptance: expected one negated harmonized branch, "
            f"found {negated_count}"
        )
    text, passive_count = re.subn(
        r"(?m)^[ \t]*(?:has_harmonized_with = (?:PREV|ROOT)|"
        r"has_owner_harmonized_religion = yes)\s*\n",
        "",
        text,
    )
    if passive_count != 9:
        raise ValueError(
            "estate religious acceptance: expected nine passive harmonized branches, "
            f"found {passive_count}"
        )
    return text


def render_shinto_conversion_decision(text: str) -> str:
    return replace_exact(
        text,
        '''\tbecome_confucian_daimyo = {
\t\tmajor = yes
\t\tpotential = {
''',
        '''\tbecome_confucian_daimyo = {
\t\tmajor = yes
\t\tpotential = {
\t\t\talways = no # ZHX: Ritual Teaching is unavailable through the Shinto conversion decision
''',
        count=1,
        label="Shinto Ritual Teaching decision entry",
    )


def render_preview_mission_effects(text: str) -> str:
    old = '''select_current_missions_HORDES = {
\thidden_effect = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_country_flag = hordes_confucian_branch_flag
\t\t\t}
\t\t\tchange_religion = confucianism
\t\t}
\t}
}'''
    new = '''select_current_missions_HORDES = {
\thidden_effect = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_country_flag = hordes_confucian_branch_flag
\t\t\t\tNOT = {
\t\t\t\t\tAND = {
\t\t\t\t\t\treligion = confucianism
\t\t\t\t\t\tzhx_can_adopt_lijiao = yes
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t\tclr_country_flag = hordes_confucian_branch_flag
\t\t\tset_country_flag = hordes_tolerance_branch_flag
\t\t}
\t}
}'''
    return replace_exact(
        text,
        old,
        new,
        count=1,
        label="Horde forced Ritual Teaching mission conversion",
    )


def render_confucian_rebels(text: str) -> str:
    text = replace_exact(
        text,
        '''\tspawn_chance = {
\t\tfactor = 1
''',
        '''\tspawn_chance = {
\t\tfactor = 1
\t\tmodifier = {
\t\t\tfactor = 0
\t\t\towner = { NOT = { zhx_can_adopt_lijiao = yes } }
\t\t}
''',
        count=1,
        label="Confucian rebel owner eligibility",
    )
    text = replace_exact(
        text,
        '''\t\t\t\t\tNOT = { religion = confucianism }
\t\t\t\t\tis_reformation_center = no
\t\t\t\t\tNOT = { owner = { religion = confucianism } }''',
        '''\t\t\t\t\tNOT = { religion = confucianism }
\t\t\t\t\tis_reformation_center = no
\t\t\t\t\tNOT = { owner = { religion = confucianism } }
\t\t\t\t\towner = { zhx_can_adopt_lijiao = yes }''',
        count=1,
        label="Confucian rebel province conversion eligibility",
    )
    return replace_exact(
        text,
        '''\t\telse_if = {
\t\t\tlimit = {
\t\t\t\tNOT = { religion = confucianism }
\t\t\t\tdominant_religion = confucianism
\t\t\t}
\t\t\tchange_religion = confucianism''',
        '''\t\telse_if = {
\t\t\tlimit = {
\t\t\t\tNOT = { religion = confucianism }
\t\t\t\tdominant_religion = confucianism
\t\t\t\tzhx_can_adopt_lijiao = yes
\t\t\t}
\t\t\tchange_religion = confucianism''',
        count=1,
        label="Confucian rebel country conversion eligibility",
    )


def render_religious_events(text: str) -> str:
    text = replace_exact(
        text,
        '''\t\t\towner = {
\t\t\t\treligion = buddhism
\t\t\t\tconfucianism = 2
\t\t\t}''',
        '''\t\t\towner = {
\t\t\t\treligion = buddhism
\t\t\t\tzhx_can_adopt_lijiao = yes
\t\t\t\tconfucianism = 2
\t\t\t}''',
        count=1,
        label="Theravada province spread owner eligibility",
    )
    text = replace_exact(
        text,
        '''\t\t\towner = {
\t\t\t\treligion = vajrayana
\t\t\t\tconfucianism = 2
\t\t\t}''',
        '''\t\t\towner = {
\t\t\t\treligion = vajrayana
\t\t\t\tzhx_can_adopt_lijiao = yes
\t\t\t\tconfucianism = 2
\t\t\t}''',
        count=1,
        label="Vajrayana province spread owner eligibility",
    )
    text = replace_exact(
        text,
        '''\t\t\towner = {
\t\t\t\treligion = mahayana
\t\t\t\tconfucianism = 2
\t\t\t}''',
        '''\t\t\towner = {
\t\t\t\treligion = mahayana
\t\t\t\tzhx_can_adopt_lijiao = yes
\t\t\t\tconfucianism = 2
\t\t\t}''',
        count=1,
        label="Mahayana province spread owner eligibility",
    )
    text = replace_exact(
        text,
        '''\t\towner = {
\t\t\treligion = shinto
\t\t\tconfucianism = 2
\t\t}''',
        '''\t\towner = {
\t\t\treligion = shinto
\t\t\tzhx_can_adopt_lijiao = yes
\t\t\tconfucianism = 2
\t\t}''',
        count=1,
        label="Shinto province spread owner eligibility",
    )
    return replace_exact(
        text,
        '''\t\ttrigger = { any_owned_province = { religion = confucianism } }
\t\tchange_religion = confucianism''',
        '''\t\ttrigger = {
\t\t\tzhx_can_adopt_lijiao = yes
\t\t\tany_owned_province = { religion = confucianism }
\t\t}
\t\tchange_religion = confucianism''',
        count=1,
        label="generic Buddhist-to-Ritual-Teaching conversion eligibility",
    )


RENDERERS = {
    "missions/DOM_Chinese_Missions.txt": render_dom_chinese,
    "missions/DOM_Japanese_Missions.txt": render_dom_japanese,
    "missions/Japanese_Missions.txt": render_japanese,
    "missions/Korean_Missions.txt": render_korean,
    "missions/Manchu_Missions.txt": render_manchu_missions,
    "missions/zzz_WoC_Shared_Horde_Missions.txt": render_horde_missions,
    "missions/zzzz_WoC_EoC_Yuan_Missions.txt": render_yuan,
    "decisions/ManchuDecisions.txt": render_manchu_decisions,
    "events/Shinto.txt": render_shinto,
    "events/Confucianism.txt": render_confucian_events,
    "common/scripted_effects/01_scripted_effects_for_estates.txt": render_estate_scripted_effects,
    "decisions/ShintoConversion.txt": render_shinto_conversion_decision,
    "common/scripted_effects/02_scripted_effects_preview_missions.txt": render_preview_mission_effects,
    "common/rebel_types/confucianism.txt": render_confucian_rebels,
    "events/Religious.txt": render_religious_events,
}


def build(vanilla_root: Path) -> dict[str, str]:
    return {
        relative: RENDERERS[relative](read_pinned(vanilla_root, relative))
        for relative in BASELINES
    }


def run(vanilla_root: Path, check: bool) -> None:
    outputs = build(vanilla_root)
    stale: list[str] = []
    for relative, output in outputs.items():
        target = MOD / relative
        if check:
            if not target.exists() or target.read_bytes() != output.encode("latin-1"):
                stale.append(relative)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(output.encode("latin-1"))
    if stale:
        raise ValueError("stale Harmony-retirement overrides: " + ", ".join(stale))
    print(
        f"{'checked' if check else 'built'} Harmony retirement; "
        f"pinned_overrides={len(outputs)}; repaired_missions=7; "
        "preserved_inert_event_stubs=12; removed_legacy_events=9"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.vanilla_root.resolve(), args.check)


if __name__ == "__main__":
    main()
