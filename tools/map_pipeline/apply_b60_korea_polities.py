#!/usr/bin/env python3
"""Apply the four-polity Korea worldbuilding layer after B59.

The batch does not alter province geometry.  It assigns the seven Korean
areas to Jizi Joseon, Liao, Helan Jurchens, and Goryeo; installs the two new
country tags; and records Jizi Joseon and Liao as politically Zhou-aligned but
engine-independent states.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from apply_culture_name_pools import readable_culture_name_blocks  # noqa: E402
from country_name_pool_support import country_definition_bytes  # noqa: E402
from encode_eu4_chinese_localisation import (  # noqa: E402
    from_escaped_bytes,
    to_escaped_bytes,
)

MOD = ROOT / "guangdong_independent_practice"
PLAN = ROOT / "planning/korea_polities_b60"
MANIFEST = PLAN / "b60_manifest.json"
B59 = ROOT / "tools/map_pipeline/apply_b59_korea_consolidation.py"
MARKER = "GDD_B60_KOREA_FOUR_POLITIES"
VANILLA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)


def data() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_text(relative: str, content: str, encoding: str = "utf-8") -> None:
    path = MOD / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding=encoding)


def write_eu4_chinese_script(relative: str, content: str) -> None:
    """Write Chinese character data in the installed EU4dll byte format."""
    path = MOD / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(to_escaped_bytes(content.rstrip() + "\n"))


def update_country_tags() -> None:
    path = MOD / "common/country_tags/gdd_country_tags.txt"
    text = path.read_text(encoding="latin-1")
    text = re.sub(
        rf"(?ms)^# {MARKER}_BEGIN\n.*?^# {MARKER}_END\n?",
        "",
        text,
    ).rstrip()
    block = f'''# {MARKER}_BEGIN
JIZ = "countries/B60_Jizi_Joseon.txt"
HLD = "countries/B60_Helan.txt"
# {MARKER}_END'''
    path.write_text(text + "\n\n" + block + "\n", encoding="latin-1")


def write_country_definitions() -> None:
    (MOD / "common/countries/B60_Jizi_Joseon.txt").write_bytes(
        country_definition_bytes(
            '''# B60: Jizi-descended Zhou-aligned state in northern Korea.
graphical_culture = asiangfx
color = { 47 91 102 }
revolutionary_colors = { 1 7 5 }''',
            "korean",
        )
    )
    (MOD / "common/countries/B60_Helan.txt").write_bytes(
        country_definition_bytes(
            '''# B60: Jurchen tribal federation of Helandian and Hamgyong.
graphical_culture = asiangfx
color = { 78 116 72 }
revolutionary_colors = { 3 8 1 }''',
            "manchu",
        )
    )


def write_samhan_culture() -> None:
    name_blocks = readable_culture_name_blocks("gdd_samhan", "      ")
    write_eu4_chinese_script(
        "common/cultures/gdd_b60_samhan_culture.txt",
        '''# B60: the native southern Han culture is distinct from Jizi Joseon.
gdd_samhan_group = {
    graphical_culture = asiangfx
    gdd_samhan = {
        primary = KOR

''' + name_blocks + '''
    }
}''',
    )


def write_country_histories() -> None:
    write_eu4_chinese_script(
        "history/countries/JIZ - Jizi Joseon.txt",
        '''# B60: Jizi Joseon, an independent state that observes Zhou rites.
government = monarchy
add_government_reform = feudalism_reform
government_rank = 1
technology_group = chinese
religion = confucianism
primary_culture = korean
capital = 1845
fixed_capital = 1845

1444.1.1 = {
    monarch = {
        name = "玄"
        dynasty = "箕"
        adm = 4
        dip = 4
        mil = 3
    }
    heir = {
        name = "准"
        monarch_name = "准"
        dynasty = "箕"
        birth_date = 1426.1.1
        claim = 80
        adm = 3
        dip = 3
        mil = 4
    }
}

1444.10.29 = {
    add_truce_with = LIO
}''',
    )
    write_eu4_chinese_script(
        "history/countries/HLD - Helan.txt",
        '''# B60: the Helandian Jurchen federation in Hamgyong.
government = tribal
add_government_reform = tribal_federation
government_rank = 1
technology_group = nomad_group
religion = tengri_pagan_reformed
secondary_religion = confucianism
primary_culture = manchu
capital = 732

1444.1.1 = {
    monarch = {
        name = "孟特穆"
        dynasty = "斡朵里"
        adm = 3
        dip = 3
        mil = 4
    }
    heir = {
        name = "充善"
        monarch_name = "充善"
        dynasty = "斡朵里"
        birth_date = 1428.1.1
        claim = 70
        adm = 2
        dip = 3
        mil = 4
    }
}''',
    )
    # Exact vanilla filename shadows the inherited Joseon history.  This KOR
    # is the independent southern Goryeo state, not the Jizi polity.
    write_eu4_chinese_script(
        "history/countries/KOR - Korea.txt",
        '''# B60: independent native Goryeo in southern Korea.
government = monarchy
add_government_reform = korean_monarchy
government_rank = 2
technology_group = chinese
religion = mahayana
primary_culture = gdd_samhan
capital = 735

1444.1.1 = {
    monarch = {
        name = "玄"
        dynasty = "王"
        adm = 4
        dip = 5
        mil = 3
    }
    heir = {
        name = "祐"
        monarch_name = "祐"
        dynasty = "王"
        birth_date = 1427.1.1
        claim = 85
        adm = 3
        dip = 3
        mil = 3
    }
}''',
    )


def block_bounds(text: str, name: str, start: int = 0) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text[start:])
    if not match:
        raise ValueError(f"missing block {name}")
    begin = start + match.start()
    brace = text.find("{", begin)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return begin, index + 1
    raise ValueError(f"unclosed block {name}")


def register_startup_event() -> None:
    path = MOD / "common/on_actions/gdd_on_actions.txt"
    text = path.read_text(encoding="latin-1")
    text = re.sub(rf"(?m)^\s*gdd_korea\.1\s+# {MARKER}\n?", "", text)
    outer_start, outer_end = block_bounds(text, "on_startup")
    outer = text[outer_start:outer_end]
    events_start, events_end = block_bounds(outer, "events")
    events = outer[events_start:events_end]
    close = events.rfind("}")
    events = events[:close].rstrip() + f"\n        gdd_korea.1 # {MARKER}\n    " + events[close:]
    outer = outer[:events_start] + events + outer[events_end:]
    path.write_text(text[:outer_start] + outer + text[outer_end:], encoding="latin-1")


def write_event() -> None:
    write_text(
        "events/gdd_korea_polity_events.txt",
        '''namespace = gdd_korea

country_event = {
    id = gdd_korea.1
    title = gdd_korea.1.t
    desc = gdd_korea.1.d
    picture = DIPLOMACY_eventPicture
    is_triggered_only = yes

    trigger = {
        ai = no
        OR = { tag = JIZ tag = LIO tag = HLD tag = KOR }
        NOT = { has_country_flag = gdd_b60_korea_world_explained }
    }

    immediate = { set_country_flag = gdd_b60_korea_world_explained }

    option = {
        name = gdd_korea.1.a
    }
}''',
        "latin-1",
    )


def write_localisation() -> None:
    source = MOD / "localisation_source/013_gdd_b60_korea_polities_readable_utf8.txt"
    source.write_text(
        '''l_english:
 JIZ:0 "朝鲜"
 JIZ_ADJ:0 "朝鲜"
 HLD:0 "曷懒"
 HLD_ADJ:0 "曷懒"
 KOR:0 "高丽"
 KOR_ADJ:0 "高丽"
 JIZ_ideas:0 "箕氏朝鲜理念"
 HLD_ideas:0 "曷懒理念"
 KOR_ideas:0 "高丽理念"
 gdd_samhan_group:0 "三韩"
 gdd_samhan:0 "韩"
 gdd_korea.1.t:0 "海东四国"
 gdd_korea.1.d:0 "海东旧有四种秩序。平壤的箕氏朝鲜自称殷商遗裔，以独立之国奉周礼而列于诸侯；契丹辽国越过鸭绿，占据浿水三城，也在政治上尊奉周室，但不构成游戏中的属国关系。咸镜山海之间，曷懒女真结成部落联盟，不受周礼约束。汉城以南则由王氏高丽统合三韩故地，以本土之国自立于天下之外。"
 gdd_korea.1.a:0 "海东形势，自此而始。"
''',
        encoding="utf-8",
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file

    encode_file(
        source,
        MOD / "localisation/replace/013_gdd_b60_korea_polities_l_english.yml",
    )


def write_flags() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    from shang_flag_emblems import shang_flag_bytes

    flags = MOD / "gfx/flags"
    flags.mkdir(parents=True, exist_ok=True)
    # 箕子朝鲜是奉周礼的独立诸夏成员。其旗使用甲骨文“箕”的簸箕格纹象形，
    # 并与 B62 的孤竹、无终共享一套离线矢量生成逻辑；不得退回现代楷书字形。
    # 曷懒旗则仍由后续边疆旗批次维护，这里不覆盖。
    (flags / "JIZ.tga").write_bytes(
        shang_flag_bytes(
            "JIZ",
            "ji",
            (47, 91, 102),
            (232, 218, 164),
            (169, 117, 62),
        )
    )


def first_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    if not match:
        raise ValueError(f"missing {key}")
    return match.group(1).strip()


def validate(config: dict) -> None:
    expected = {}
    expected_culture = {}
    expected_religion = {}
    for tag in ("JIZ", "HLD", "KOR"):
        expected.update({pid: tag for pid in config["polities"][tag]["provinces"]})
        expected_culture.update(
            {
                pid: config["polities"][tag]["primary_culture"]
                for pid in config["polities"][tag]["provinces"]
            }
        )
        expected_religion.update(
            {
                pid: config["polities"][tag]["province_religion"]
                for pid in config["polities"][tag]["provinces"]
            }
        )
    expected.update({pid: "LIO" for pid in config["polities"]["LIO"]["new_korea_provinces"]})
    expected_culture.update(
        {pid: "korean" for pid in config["polities"]["LIO"]["new_korea_provinces"]}
    )
    expected_religion.update(
        {
            pid: config["polities"]["LIO"]["province_religion"]
            for pid in config["polities"]["LIO"]["new_korea_provinces"]
        }
    )
    for pid, owner in expected.items():
        paths = list((MOD / "history/provinces").glob(f"{pid} - *.txt"))
        if len(paths) != 1:
            raise ValueError(f"province {pid} has {len(paths)} local histories")
        text = paths[0].read_text(encoding="latin-1")
        if first_value(text, "owner") != owner or first_value(text, "controller") != owner:
            raise ValueError(f"province {pid} ownership drift")
        if first_value(text, "culture") != expected_culture[pid]:
            raise ValueError(f"province {pid} culture drift")
        if first_value(text, "religion") != expected_religion[pid]:
            raise ValueError(f"province {pid} religion drift")
    if len(expected) != 30:
        raise ValueError("the four polities do not cover exactly 30 Korean provinces")
    for tag in ("JIZ", "HLD"):
        if not (MOD / f"gfx/flags/{tag}.tga").exists():
            raise ValueError(f"missing {tag} flag")
    for pid in config["polities"]["LIO"]["liaodong_provinces"]:
        paths = list((MOD / "history/provinces").glob(f"{pid} - *.txt"))
        if len(paths) != 1 or first_value(
            paths[0].read_text(encoding="latin-1"), "religion"
        ) != config["polities"]["LIO"]["liaodong_province_religion"]:
            raise ValueError(f"Liao Liaodong province {pid} religion drift")
    country_histories = {
        "JIZ": "JIZ - Jizi Joseon.txt",
        "LIO": "LIO - Liao.txt",
        "HLD": "HLD - Helan.txt",
        "KOR": "KOR - Korea.txt",
    }
    for tag, filename in country_histories.items():
        history = from_escaped_bytes((MOD / "history/countries" / filename).read_bytes())
        if first_value(history, "religion") != config["polities"][tag]["country_religion"]:
            raise ValueError(f"{tag} country religion drift")
        if tag == "KOR" and "add_harmonized_religion = mahayana" in history:
            raise ValueError("Mahayana Goryeo must not harmonize its own state religion")
    expected_opening_characters = {
        "JIZ - Jizi Joseon.txt": ("玄", "准", "箕"),
        "HLD - Helan.txt": ("孟特穆", "充善", "斡朵里"),
        "KOR - Korea.txt": ("玄", "祐", "王"),
    }
    for filename, expected_names in expected_opening_characters.items():
        history = from_escaped_bytes((MOD / "history/countries" / filename).read_bytes())
        for expected_name in expected_names:
            if f'"{expected_name}"' not in history:
                raise ValueError(f"{filename}: missing Chinese opening character {expected_name}")
        if re.search(r'(?m)^\s*(?:name|monarch_name)\s*=\s*"[^"]+\s+[IVX]+"', history):
            raise ValueError(f"{filename}: European regnal numeral remains")
    localisation = (MOD / "localisation_source/012_gdd_b59_korea_consolidation_readable_utf8.txt").read_text(encoding="utf-8")
    for name in ("狼林山脉", "太白山脉"):
        if name not in localisation:
            raise ValueError(f"missing mountain localisation {name}")


def main() -> None:
    config = data()
    subprocess.run([sys.executable, str(B59)], check=True)
    update_country_tags()
    write_country_definitions()
    write_samhan_culture()
    write_country_histories()
    register_startup_event()
    write_event()
    write_localisation()
    write_flags()
    validate(config)
    print("B60_KOREA_APPLIED; polities=4; provinces=30; zhou_aligned_independent=2; geometry_changed=no")


if __name__ == "__main__":
    main()
