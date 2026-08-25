#!/usr/bin/env python3
"""Static contract checks for the adapted ZHX Nestorian mechanic."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
RELIGIONS = MOD / "common/religions/00_religion.txt"
RELIGION_GFX = MOD / "interface/countryreligionview.gfx"
LOCALISATION = MOD / "localisation_source/zhx_nestorian_readable_utf8.txt"
COUNTRY_HISTORY = MOD / "history/countries"
PROVINCE_HISTORY = MOD / "history/provinces"

LIAODONG_NESTORIAN = {726, 5204, 5205, 2112, 4652, 2113}
LIAO_KOREA_LIJAO = {2744, 4232, 5359}
GORYEO_MAHAYANA = {
    734,
    735,
    736,
    737,
    1013,
    2694,
    2741,
    2745,
    4227,
    4228,
    4229,
    4230,
    5365,
}
ICON_ORDER = (
    "icon_michael",
    "icon_eleusa",
    "icon_pancreator",
    "icon_nicholas",
    "icon_climacus",
    "icon_nestorius",
    "icon_mar_yelv",
    "icon_jinghui",
    "icon_thomas",
    "icon_anthony",
)
REQUIRED_LOCALISATION = {
    "nestorian",
    "nestorian_desc",
    "nestorian_religion_desc",
    "icon_nestorius",
    "icon_nestorius_desc",
    "icon_mar_yelv",
    "icon_mar_yelv_desc",
    "icon_jinghui",
    "icon_jinghui_desc",
    "icon_thomas",
    "icon_thomas_desc",
    "icon_anthony",
    "icon_anthony_desc",
    "nestorian_rebels_demand",
    "nestorian_rebels_demand_desc",
    "nestorian_rebels_title",
    "nestorian_rebels_name",
    "nestorian_rebels_desc",
    "nestorian_rebels_army",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


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
            require(depth >= 0, "closing brace without opener")
            if depth == 0:
                return index
    raise ValueError("block has no matching closing brace")


def block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
    opening = text.find("{", match.start())
    closing = matching_close(text, opening)
    return text[opening + 1 : closing]


def initial_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    require(match is not None, f"missing {key}")
    return match.group(1).strip()


def province_text(province_id: int) -> str:
    paths = list(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
    require(len(paths) == 1, f"province {province_id} has {len(paths)} histories")
    return paths[0].read_text(encoding="latin-1")


def validate_religion_definition() -> None:
    text = RELIGIONS.read_text(encoding="utf-8")
    christian = block_body(text, "christian")
    require(
        len(re.findall(r"(?m)^\s*nestorian\s*=\s*\{", christian)) == 1,
        "nestorian must occur exactly once inside christian",
    )
    nestorian = block_body(christian, "nestorian")
    require(initial_value(nestorian, "icon") == "7", "nestorian must use icon 7")
    require(
        "has_patriarchs = yes" in nestorian
        and "misguided_heretic = yes" in nestorian,
        "nestorian must retain patriarch authority and misguided-heretic status",
    )
    require("icon_timur" not in nestorian and "tomb_timur" not in nestorian,
            "Ante Bellum-only Timur content must not be imported")
    icons = block_body(nestorian, "orthodox_icons")
    actual = tuple(
        re.findall(r"(?m)^\s*(icon_[a-z0-9_]+)\s*=\s*\{", icons)
    )
    require(actual == ICON_ORDER, f"Nestorian icon frame order drifted: {actual}")
    for key in ICON_ORDER[:5]:
        body = block_body(icons, key)
        require(
            body.count("religion = orthodox") == 2,
            f"{key} must remain a hidden Orthodox frame anchor",
        )
    for key in ICON_ORDER[5:]:
        body = block_body(icons, key)
        require(
            body.count("religion = nestorian") == 2,
            f"{key} must be visible only to Nestorian countries",
        )
    require("diplomatic_reputation = 1" in block_body(icons, "icon_nestorius"),
            "Nestorius effect drifted")
    require("reform_progress_growth = 0.2" in block_body(icons, "icon_mar_yelv"),
            "Yelv effect drifted")
    require("global_missionary_strength = 0.02" in block_body(icons, "icon_jinghui"),
            "Jinghui effect drifted")
    require("global_autonomy = -0.05" in block_body(icons, "icon_thomas"),
            "Thomas effect drifted")
    require("land_morale = 0.1" in block_body(icons, "icon_anthony"),
            "Anthony effect drifted")


def validate_art() -> None:
    sheet_frames = {
        "icon_religion.dds": 64,
        "country_icon_religion.dds": 64,
        "icon_religion_small.dds": 32,
        "province_view_religion.dds": 32,
    }
    for name, frame in sheet_frames.items():
        image = Image.open(MOD / "gfx/interface" / name).convert("RGBA")
        require(image.size == (29 * frame, frame), f"{name} must remain 29 frames")
        nestorian = image.crop((6 * frame, 0, 7 * frame, frame))
        lijiao = image.crop((8 * frame, 0, 9 * frame, frame))
        require(nestorian.getchannel("A").getbbox() is not None,
                f"{name} has an empty Nestorian frame")
        require(lijiao.getchannel("A").getbbox() is not None,
                f"{name} lost the Ritual Teaching frame")
    patriarchs = Image.open(MOD / "gfx/interface/russian_icons_strip.dds").convert("RGBA")
    require(patriarchs.size == (580, 58), "patriarch icon strip must be 10x58")
    for index in range(10):
        frame = patriarchs.crop((index * 58, 0, (index + 1) * 58, 58))
        require(frame.getchannel("A").getbbox() is not None,
                f"patriarch icon frame {index + 1} is empty")
    gfx = RELIGION_GFX.read_text(encoding="utf-8")
    match = re.search(
        r'name\s*=\s*"GFX_russian_icons_strip"(?P<body>.*?)\}',
        gfx,
        re.S,
    )
    require(match is not None and re.search(r"noOfFrames\s*=\s*10\b", match.group("body")),
            "GFX_russian_icons_strip must expose ten frames")


def validate_geography() -> None:
    liao = (COUNTRY_HISTORY / "LIO - Liao.txt").read_text(encoding="utf-8-sig")
    require(initial_value(liao, "religion") == "nestorian", "LIO must be Nestorian")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import from_escaped_bytes

    goryeo = from_escaped_bytes((COUNTRY_HISTORY / "KOR - Korea.txt").read_bytes())
    require(initial_value(goryeo, "religion") == "mahayana", "KOR must be Mahayana")
    require("add_harmonized_religion = mahayana" not in goryeo,
            "Mahayana KOR must not harmonize its own faith")
    for province_id in LIAODONG_NESTORIAN:
        require(initial_value(province_text(province_id), "religion") == "nestorian",
                f"Liaodong province {province_id} must be Nestorian")
    for province_id in LIAO_KOREA_LIJAO:
        require(initial_value(province_text(province_id), "religion") == "confucianism",
                f"Liao-held Korean province {province_id} must be Ritual Teaching")
    for province_id in GORYEO_MAHAYANA:
        require(initial_value(province_text(province_id), "religion") == "mahayana",
                f"Korean province {province_id} must be Mahayana")


def validate_localisation_and_builders() -> None:
    localisation = LOCALISATION.read_text(encoding="utf-8-sig")
    actual = set(re.findall(r"(?m)^\s*([a-z0-9_]+):\d+\s+", localisation))
    require(REQUIRED_LOCALISATION <= actual,
            f"missing Nestorian localisation: {sorted(REQUIRED_LOCALISATION - actual)}")
    religion_builder = (ROOT / "tools/build_zhx_religions.py").read_text()
    icon_builder = (ROOT / "tools/generate_lijiao_religion_icon.py").read_text()
    gfx_builder = (ROOT / "tools/build_zhx_countryreligionview_gfx.py").read_text()
    require("609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6" in religion_builder,
            "religion builder lost its EU4 1.37.5 baseline pin")
    require("NESTORIAN_FRAME_INDEX = 6" in icon_builder,
            "religion atlas builder lost the unused-frame contract")
    require("2d2705b073cc82c7d96de43cc8c31168f77f926069d0f93df0fd1749365c23a4" in gfx_builder,
            "religion GFX builder lost its EU4 1.37.5 baseline pin")
    trigger = (MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt").read_text()
    lijiao = block_body(trigger, "zhx_is_lijiao_country")
    require("religion = confucianism" in lijiao and "nestorian" not in lijiao,
            "Nestorian countries must never enter the Ritual Teaching doctrine system")
    doctrine_events = (MOD / "events/zhx_doctrine_events.txt").read_text()
    require(re.search(r"\bLIO\b", doctrine_events) is None,
            "LIO must not receive a scripted Ritual Teaching school")


def main() -> None:
    validate_religion_definition()
    validate_art()
    validate_geography()
    validate_localisation_and_builders()
    print(
        "ZHX_NESTORIAN_VALID; religion=christian/patriarchs; icons=5; "
        "LIO=nestorian; Liaodong=6; Liao_Korea=3_lijiao; KOR=13_mahayana"
    )


if __name__ == "__main__":
    main()
