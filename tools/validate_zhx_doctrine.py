#!/usr/bin/env python3
"""Static contract checks for the Ritual Teaching Ru/Fa/Mo prototype."""

from __future__ import annotations

import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

SCRIPT_PATHS = (
    MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt",
    MOD / "common/scripted_effects/zhx_doctrine_effects.txt",
    MOD / "common/event_modifiers/zhx_doctrine_modifiers.txt",
    MOD / "decisions/zhx_doctrine_decisions.txt",
    MOD / "events/zhx_doctrine_events.txt",
)
ON_ACTION_PATH = MOD / "common/on_actions/zhx_system_on_actions.txt"
NATIVE_GFX_PATH = MOD / "interface/zhx_doctrine_icons.gfx"
LIJIAO_GFX_PATH = MOD / "interface/zhx_lijiao_religion.gfx"
NATIVE_GUI_PATH = MOD / "interface/countryreligionview.gui"
NATIVE_DIPLOMACY_GUI_PATH = MOD / "interface/countrydiplomacyview.gui"
NATIVE_CUSTOM_GUI_PATH = MOD / "common/custom_gui/zhx_religion_gui.txt"
NATIVE_RELIGION_PATH = MOD / "common/religions/00_religion.txt"
NATIVE_RELIGION_BUILDER_PATH = ROOT / "tools/build_zhx_religions.py"
NATIVE_GUI_BUILDER_PATH = ROOT / "tools/build_zhx_countryreligionview.py"
NATIVE_DIPLOMACY_BUILDER_PATH = ROOT / "tools/build_zhx_countrydiplomacyview.py"
LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_doctrine_readable_utf8.txt"
)
NATIVE_LOCALISATION_PATH = (
    MOD / "localisation_source/zhx_native_schools_readable_utf8.txt"
)
TEMP_RUNTIME_EVENT_PATH = MOD / "events/zz_zhxtest_runtime.txt"

EXPECTED_EVENT_IDS = {"1", "10", "11", "12", "20", "90", "91", "92"}
EXPECTED_FLAGS = {
    "ru": "zhx_doctrine_ru",
    "fa": "zhx_doctrine_fa",
    "mo": "zhx_doctrine_mo",
}
NATIVE_SCHOOLS = {
    "zhx_ru_school": "GFX_zhx_doctrine_ru_school",
    "zhx_fa_school": "GFX_zhx_doctrine_fa_school",
    "zhx_mo_school": "GFX_zhx_doctrine_mo_school",
    "zhx_dao_school": "GFX_zhx_doctrine_dao_school",
    "zhx_bing_school": "GFX_zhx_doctrine_bing_school",
    "zhx_zongheng_school": "GFX_zhx_doctrine_zongheng_school",
}
NO_DOCTRINE_SCHOOL = {
    "zhx_no_doctrine_school": "GFX_zhx_no_doctrine_school",
}
ALL_NATIVE_SCHOOLS = NATIVE_SCHOOLS | NO_DOCTRINE_SCHOOL
NATIVE_SCHOOL_FLAGS = {
    "zhx_ru_school": "zhx_doctrine_ru",
    "zhx_fa_school": "zhx_doctrine_fa",
    "zhx_mo_school": "zhx_doctrine_mo",
    "zhx_dao_school": "zhx_doctrine_dao",
    "zhx_bing_school": "zhx_doctrine_bing",
    "zhx_zongheng_school": "zhx_doctrine_zongheng",
}
NATIVE_STATUS_FIELDS = {
    "zhx_religion_practice_value",
}
REMOVED_RELIGION_CARD_CONTROLS = {
    "zhx_religion_school_none_window",
    "zhx_religion_school_ru_window",
    "zhx_religion_school_fa_window",
    "zhx_religion_school_mo_window",
    "zhx_religion_school_dao_window",
    "zhx_religion_school_bing_window",
    "zhx_religion_school_zongheng_window",
    "zhx_religion_tier_hollow_window",
    "zhx_religion_tier_established_window",
    "zhx_religion_tier_flourishing_window",
    "zhx_religion_tier_exemplary_window",
    "zhx_religion_last_delta",
}
EXPECTED_MODIFIERS = {
    "zhx_doctrine_practice_hollow",
    "zhx_doctrine_ru_established",
    "zhx_doctrine_ru_flourishing",
    "zhx_doctrine_ru_exemplary",
    "zhx_doctrine_fa_established",
    "zhx_doctrine_fa_flourishing",
    "zhx_doctrine_fa_exemplary",
    "zhx_doctrine_mo_established",
    "zhx_doctrine_mo_flourishing",
    "zhx_doctrine_mo_exemplary",
    "zhx_doctrine_change_cooldown",
}
EXPECTED_LOCALISATION = {
    "zhx_convene_hundred_schools_debate_title",
    "zhx_convene_hundred_schools_debate_desc",
    "zhx_review_current_doctrine_title",
    "zhx_review_current_doctrine_desc",
    "zhx_doctrine.1.t",
    "zhx_doctrine.1.e",
    "zhx_doctrine.1.a",
    "zhx_doctrine.1.b",
    "zhx_doctrine.1.c",
    "zhx_doctrine.1.d",
    "zhx_doctrine.10.t",
    "zhx_doctrine.10.d",
    "zhx_doctrine.11.t",
    "zhx_doctrine.11.d",
    "zhx_doctrine.12.t",
    "zhx_doctrine.12.d",
    "zhx_doctrine.choose_ru",
    "zhx_doctrine.choose_fa",
    "zhx_doctrine.choose_mo",
    "zhx_doctrine.no_verdict",
    "zhx_doctrine_postpone_tt",
    "zhx_doctrine_inconclusive_tt",
    "zhx_adopt_ru_doctrine_tt",
    "zhx_adopt_fa_doctrine_tt",
    "zhx_adopt_mo_doctrine_tt",
    "zhx_doctrine.20.t",
    "zhx_doctrine.20.d.ru",
    "zhx_doctrine.20.d.fa",
    "zhx_doctrine.20.d.mo",
    "zhx_doctrine.20.a",
    "zhx_doctrine.90.t",
    "zhx_doctrine.90.d",
}
FORBIDDEN_TOKENS = {
    "add_treasury": "the doctrine must not be purchased with money",
    "add_adm_power": "the doctrine must not be purchased with ADM",
    "add_dip_power": "the doctrine must not be purchased with DIP",
    "add_mil_power": "the doctrine must not be purchased with MIL",
    "change_religion": "country religion must not be changed by doctrine",
    "change_province_religion": "province religion must remain stable",
    "every_country": "the prototype must not run a scripted full-country scan",
    "every_province": "the prototype must not run a scripted full-province scan",
    "on_monthly_pulse": "practice is intentionally annual, not monthly",
    "on_daily_pulse": "practice is intentionally annual, not daily",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8-sig")


def validate_braces(path: Path, text: str) -> None:
    """Balance Clausewitz braces while ignoring comments and quoted strings."""
    depth = 0
    in_string = False
    escaped = False
    in_comment = False
    for index, char in enumerate(text):
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
            require(
                depth >= 0,
                f"{path.relative_to(ROOT)}:{index}: closing brace without opener",
            )
    require(not in_string, f"{path.relative_to(ROOT)}: unterminated string")
    require(depth == 0, f"{path.relative_to(ROOT)}: unbalanced braces ({depth})")


def top_level_effect_body(text: str, effect: str) -> str:
    match = re.search(rf"(?m)^{re.escape(effect)}\s*=\s*\{{", text)
    require(match is not None, f"missing scripted effect {effect}")
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
                return text[opening + 1:index]
    raise ValueError(f"scripted effect {effect} has no closing brace")


def country_event_body(text: str, event_id: str) -> str:
    """Return one directly loaded country_event body selected by its literal ID."""
    matching_bodies: list[str] = []
    for match in re.finditer(r"(?m)^country_event\s*=\s*\{", text):
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
                    body = text[opening + 1:index]
                    if re.search(
                        rf"(?m)^\s*id\s*=\s*{re.escape(event_id)}\s*$", body
                    ):
                        matching_bodies.append(body)
                    break
    require(
        len(matching_bodies) == 1,
        f"expected exactly one directly loaded country_event {event_id}",
    )
    return matching_bodies[0]


def named_block_body(text: str, key: str) -> str:
    match = re.search(rf"(?m)^[ \t]*{re.escape(key)}\s*=\s*\{{", text)
    require(match is not None, f"missing block {key}")
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
                return text[opening + 1:index]
    raise ValueError(f"block {key} has no closing brace")


def named_window_body(text: str, name: str) -> str:
    match = re.search(
        rf'windowType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    require(match is not None, f'missing windowType "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'windowType "{name}" has no closing brace')


def named_custom_window_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_window\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_window "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'custom_window "{name}" has no closing brace')


def named_instant_text_box_body(text: str, name: str) -> str:
    match = re.search(
        rf'instantTextBoxType\s*=\s*\{{\s*name\s*=\s*"{re.escape(name)}"', text
    )
    require(match is not None, f'missing instantTextBoxType "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'instantTextBoxType "{name}" has no closing brace')


def named_custom_text_box_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_text_box\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_text_box "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'custom_text_box "{name}" has no closing brace')


def named_icon_body(text: str, name: str) -> str:
    match = re.search(
        rf'iconType\s*=\s*\{{\s*name\s*=\s*"?{re.escape(name)}"?', text
    )
    require(match is not None, f'missing iconType "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'iconType "{name}" has no closing brace')


def named_custom_icon_body(text: str, name: str) -> str:
    match = re.search(
        rf"custom_icon\s*=\s*\{{\s*name\s*=\s*{re.escape(name)}\b", text
    )
    require(match is not None, f'missing custom_icon "{name}"')
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
                return text[opening + 1:index]
    raise ValueError(f'custom_icon "{name}" has no closing brace')


def rectangle_from_body(body: str, name: str) -> tuple[int, int, int, int]:
    position = re.search(
        r"position\s*=\s*\{\s*x\s*=\s*(-?\d+)\s+y\s*=\s*(-?\d+)\s*\}",
        body,
    )
    size = re.search(
        r"size\s*=\s*\{\s*x\s*=\s*(\d+)\s+y\s*=\s*(\d+)\s*\}", body
    )
    if size is None:
        size = re.search(
            r"maxWidth\s*=\s*(\d+).*?maxHeight\s*=\s*(\d+)", body, re.S
        )
    require(position is not None and size is not None, f"{name} has no fixed rectangle")
    return tuple(int(value) for value in (*position.groups(), *size.groups()))


def window_rectangle(text: str, name: str) -> tuple[int, int, int, int]:
    body = named_window_body(text, name)
    return rectangle_from_body(body, name)


def instant_text_box_rectangle(text: str, name: str) -> tuple[int, int, int, int]:
    body = named_instant_text_box_body(text, name)
    return rectangle_from_body(body, name)


def decode_tga_alpha(texture: bytes, name: str) -> list[int]:
    """Decode alpha bytes from the uncompressed/RLE 32-bit TGAs we generate."""
    require(len(texture) >= 18, f"{name}: truncated TGA header")
    image_type = texture[2]
    width, height, depth = struct.unpack_from("<HHB", texture, 12)
    require(
        texture[1] == 0 and image_type in {2, 10} and depth == 32,
        f"{name}: unsupported TGA encoding",
    )
    pixel_count = width * height
    cursor = 18 + texture[0]
    alpha: list[int] = []
    if image_type == 2:
        end = cursor + pixel_count * 4
        require(end <= len(texture), f"{name}: truncated TGA pixel data")
        return list(texture[cursor + 3 : end : 4])

    while len(alpha) < pixel_count:
        require(cursor < len(texture), f"{name}: truncated TGA RLE packet")
        packet = texture[cursor]
        cursor += 1
        count = (packet & 0x7F) + 1
        if packet & 0x80:
            require(cursor + 4 <= len(texture), f"{name}: truncated TGA RLE pixel")
            alpha.extend([texture[cursor + 3]] * count)
            cursor += 4
        else:
            end = cursor + count * 4
            require(end <= len(texture), f"{name}: truncated TGA raw packet")
            alpha.extend(texture[cursor + 3 : end : 4])
            cursor = end
    require(len(alpha) == pixel_count, f"{name}: excess TGA RLE pixels")
    return alpha


def main() -> None:
    texts = {path: read(path) for path in SCRIPT_PATHS}
    on_action = read(ON_ACTION_PATH)
    localisation = read(LOCALISATION_PATH)
    native_gfx = read(NATIVE_GFX_PATH)
    lijiao_gfx = read(LIJIAO_GFX_PATH)
    native_gui = read(NATIVE_GUI_PATH)
    native_diplomacy_gui = read(NATIVE_DIPLOMACY_GUI_PATH)
    native_custom_gui = read(NATIVE_CUSTOM_GUI_PATH)
    native_religion = read(NATIVE_RELIGION_PATH)
    native_religion_builder = read(NATIVE_RELIGION_BUILDER_PATH)
    native_gui_builder = read(NATIVE_GUI_BUILDER_PATH)
    native_diplomacy_builder = read(NATIVE_DIPLOMACY_BUILDER_PATH)
    native_localisation = read(NATIVE_LOCALISATION_PATH)
    religion_view_body = named_window_body(native_gui, "countryreligionview")
    diplomacy_view_body = named_window_body(
        native_diplomacy_gui, "countrydiplomacyview"
    )

    for path, text in (
        *texts.items(),
        (ON_ACTION_PATH, on_action),
        (NATIVE_GFX_PATH, native_gfx),
        (LIJIAO_GFX_PATH, lijiao_gfx),
        (NATIVE_GUI_PATH, native_gui),
        (NATIVE_DIPLOMACY_GUI_PATH, native_diplomacy_gui),
        (NATIVE_CUSTOM_GUI_PATH, native_custom_gui),
        (NATIVE_RELIGION_PATH, native_religion),
    ):
        validate_braces(path, text)

    require(
        not TEMP_RUNTIME_EVENT_PATH.exists(),
        "temporary zhxtest runtime event must not ship in the mod",
    )
    forbidden_harness_names = re.compile(r"(?:zhxtest|fatest|motest)", re.I)
    leaked_harness_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path in MOD.rglob("*")
        if path.is_file() and forbidden_harness_names.search(path.name)
    )
    require(
        not leaked_harness_files,
        f"temporary religion harness files remain: {leaked_harness_files}",
    )
    production_clausewitz = {
        path: path.read_text(encoding="utf-8-sig", errors="ignore")
        for path in MOD.rglob("*.txt")
    }
    for path, text in production_clausewitz.items():
        require(
            re.search(r"\bzhxtest(?:\.\d+)?\b", text, re.I) is None
            and "ZHX_DIRECT_" not in text
            and "ZHX_DOCTRINE_CARD_ASSERT" not in text
            and "TEMP runtime harness" not in text,
            f"temporary religion probe remains in {path.relative_to(ROOT)}",
        )
    school_assignment_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path, text in production_clausewitz.items()
        if "set_religious_school" in text
    )
    require(
        school_assignment_files
        == ["guangdong_independent_practice/events/zhx_doctrine_events.txt"],
        "native doctrine assignments must live only in the directly loaded "
        f"religion event file; found={school_assignment_files}",
    )

    require(
        "609e2d235f3441c64b895d9faf3927bbf1399149cffa955137ab2d070b9645a6"
        in native_religion_builder
        and 'common/religions/00_religion.txt' in native_religion_builder,
        "religion builder must remain pinned to the EU4 1.37.5 baseline",
    )
    require(
        "ab1fd87cd2c54ba2fb334fd0353edfba84c8f223366bf64f048b76c4743cfd29"
        in native_gui_builder
        and "2976470733" in native_gui_builder
        and 'interface/countryreligionview.gui' in native_gui_builder,
        "religion-view builder must remain pinned to the required Chinese 1.37 baseline",
    )
    require(
        "74a02752cfc622ebcfbac1a359a7efe07fe6cbbec4a359987f67f205e113de4a"
        in native_diplomacy_builder
        and "2976470733" in native_diplomacy_builder
        and 'interface/countrydiplomacyview.gui' in native_diplomacy_builder,
        "diplomacy builder must remain pinned to the required Chinese 1.37 baseline",
    )
    overlay_name = "zhx_lijiao_school_button_overlay"
    overlay_sprite = "GFX_zhx_lijiao_school_button"
    overlay_body = named_icon_body(religion_view_body, overlay_name)
    require(
        religion_view_body.count(f'name = "{overlay_name}"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*180\s+y\s*=\s*148\s*\}",
            overlay_body,
        )
        is not None
        and f'spriteType = "{overlay_sprite}"' in overlay_body
        and "alwaystransparent = yes" in overlay_body
        and "scripted = yes" in overlay_body,
        "礼教 scholar-button overlay must cover the native 42 px button without "
        "intercepting its hitbox",
    )
    require(
        lijiao_gfx.count(f'name = "{overlay_sprite}"') == 1,
        "礼教 scholar-button sprite must be registered exactly once",
    )
    overlay_sprite_body = lijiao_gfx.split(f'name = "{overlay_sprite}"', 1)[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_lijiao_school_button.dds"'
        in overlay_sprite_body
        and 'loadType = "INGAME"' in overlay_sprite_body,
        "礼教 scholar-button sprite must load the generated in-game DDS",
    )
    overlay_texture_path = MOD / "gfx/interface/zhx_lijiao_school_button.dds"
    overlay_texture = (
        overlay_texture_path.read_bytes() if overlay_texture_path.is_file() else b""
    )
    require(
        len(overlay_texture) >= 128 and overlay_texture[:4] == b"DDS ",
        "missing or malformed 礼教 scholar-button DDS",
    )
    overlay_height, overlay_width = struct.unpack_from("<II", overlay_texture, 12)
    require(
        (overlay_width, overlay_height) == (42, 42),
        "礼教 scholar-button DDS must match the native 42x42 button",
    )
    require(
        native_custom_gui.count(f"name = {overlay_name}") == 1,
        "礼教 scholar-button overlay must have exactly one custom-icon binding",
    )
    overlay_custom_body = named_custom_icon_body(native_custom_gui, overlay_name)
    require(
        "zhx_is_lijiao_country = yes" in overlay_custom_body
        and "zhx_has_doctrine = yes" in overlay_custom_body
        and "has_religious_school = yes" in overlay_custom_body,
        "礼教 scholar-button overlay must be limited to doctrine-bearing Ritual "
        "Teaching countries with a native school",
    )
    sentinel_overlay_name = "zhx_no_doctrine_school_button_overlay"
    sentinel_overlay_sprite = "GFX_zhx_no_doctrine_school_button"
    sentinel_overlay_body = named_icon_body(
        religion_view_body, sentinel_overlay_name
    )
    require(
        religion_view_body.count(f'name = "{sentinel_overlay_name}"') == 1
        and re.search(
            r"position\s*=\s*\{\s*x\s*=\s*180\s+y\s*=\s*148\s*\}",
            sentinel_overlay_body,
        )
        is not None
        and f'spriteType = "{sentinel_overlay_sprite}"' in sentinel_overlay_body
        and "alwaystransparent = yes" in sentinel_overlay_body
        and "scripted = yes" in sentinel_overlay_body,
        "no-doctrine overlay must cover the native 42 px button without "
        "intercepting its hitbox",
    )
    require(
        lijiao_gfx.count(f'name = "{sentinel_overlay_sprite}"') == 1,
        "no-doctrine school-button sprite must be registered exactly once",
    )
    sentinel_sprite_body = lijiao_gfx.split(
        f'name = "{sentinel_overlay_sprite}"', 1
    )[1][:300]
    require(
        'texturefile = "gfx/interface/zhx_no_doctrine_school_button.dds"'
        in sentinel_sprite_body
        and 'loadType = "INGAME"' in sentinel_sprite_body,
        "no-doctrine button sprite must load the generated in-game DDS",
    )
    sentinel_button_path = MOD / "gfx/interface/zhx_no_doctrine_school_button.dds"
    sentinel_button = (
        sentinel_button_path.read_bytes() if sentinel_button_path.is_file() else b""
    )
    require(
        len(sentinel_button) >= 128 and sentinel_button[:4] == b"DDS ",
        "missing or malformed no-doctrine school-button DDS",
    )
    sentinel_button_height, sentinel_button_width = struct.unpack_from(
        "<II", sentinel_button, 12
    )
    require(
        (sentinel_button_width, sentinel_button_height) == (42, 42),
        "no-doctrine school-button DDS must match the native 42x42 button",
    )
    require(
        native_custom_gui.count(f"name = {sentinel_overlay_name}") == 1,
        "no-doctrine overlay must have exactly one custom-icon binding",
    )
    sentinel_custom_body = named_custom_icon_body(
        native_custom_gui, sentinel_overlay_name
    )
    require(
        "group = eastern" in sentinel_custom_body
        and "school = zhx_no_doctrine_school" in sentinel_custom_body
        and "zhx_has_doctrine = yes" not in sentinel_custom_body,
        "no-doctrine overlay must bind only to the exact eastern sentinel",
    )
    school_icon_body = named_icon_body(
        diplomacy_view_body, "religious_school_icon"
    )
    require(
        re.search(
            r"position\s*=\s*\{\s*x\s*=\s*110\s+y\s*=\s*142\s*\}",
            school_icon_body,
        )
        is not None
        and re.search(r"scale\s*=\s*0\.5\b", school_icon_body) is not None,
        "foreign-country native school icon must retain the supported anchor and scale",
    )
    nation_label = named_instant_text_box_body(
        diplomacy_view_body, "label_nation"
    )
    fog_label = named_instant_text_box_body(diplomacy_view_body, "label_fog")
    require(
        re.search(r"position\s*=\s*\{\s*x\s*=\s*142\s+y\s*=\s*123\s*\}", nation_label)
        is not None
        and re.search(r"maxWidth\s*=\s*190\b", nation_label) is not None
        and re.search(r"position\s*=\s*\{\s*x\s*=\s*142\s+y\s*=\s*145\s*\}", fog_label)
        is not None
        and re.search(r"maxWidth\s*=\s*160\b", fog_label) is not None,
        "foreign-country labels must leave a six-pixel gutter after the school icon",
    )
    eastern_body = named_block_body(native_religion, "eastern")
    require(
        eastern_body.count("religious_schools = {") == 1,
        "eastern must contain exactly one generated religious_schools block",
    )
    school_definitions = named_block_body(eastern_body, "religious_schools")
    actual_native_schools = set(
        re.findall(r"(?m)^\s*(zhx_[a-z0-9_]+_school)\s*=\s*\{", school_definitions)
    )
    require(
        actual_native_schools == set(ALL_NATIVE_SCHOOLS),
        "native school definition contract changed: "
        f"missing={sorted(set(ALL_NATIVE_SCHOOLS) - actual_native_schools)}, "
        f"extra={sorted(actual_native_schools - set(ALL_NATIVE_SCHOOLS))}",
    )
    allowed_school_fields = {
        "potential_invite_scholar",
        "can_invite_scholar",
        "on_invite_scholar",
        "picture",
    }
    for school, picture in ALL_NATIVE_SCHOOLS.items():
        require(
            school_definitions.count(f"{school} = {{") == 1,
            f"{school} must be defined exactly once in eastern",
        )
        school_body = named_block_body(school_definitions, school)
        assigned_fields = set(
            re.findall(r"(?m)^\s*([a-z_]+)\s*=", school_body)
        )
        require(
            assigned_fields == allowed_school_fields,
            f"{school} must remain a presentation-only school; "
            f"fields={sorted(assigned_fields)}",
        )
        require(
            school_body.count("always = yes") == 0
            and school_body.count("always = no") == 2
            and re.search(r"on_invite_scholar\s*=\s*\{\s*\}", school_body)
            is not None
            and f'picture = "{picture}"' in school_body
            and "religion_sub_modifier" not in school_body,
            f"{school} must be inert, non-invitable and use {picture}",
        )

    event_text = texts[MOD / "events/zhx_doctrine_events.txt"]
    event_ids = re.findall(r"(?m)^\s*id\s*=\s*zhx_doctrine\.(\d+)\s*$", event_text)
    require(len(event_ids) == len(set(event_ids)), "duplicate zhx_doctrine event ID")
    require(
        set(event_ids) == EXPECTED_EVENT_IDS,
        f"event ID contract changed: {sorted(event_ids)}",
    )
    require(
        len(re.findall(r"(?m)^\s*zhx_doctrine\.90\s*$", on_action)) == 1,
        "on_yearly_pulse must contain zhx_doctrine.90 exactly once",
    )
    startup_body = named_block_body(on_action, "on_startup")
    require(
        "zhx_doctrine.91" not in startup_body
        and "zhx_doctrine.92" not in startup_body
        and "zhxtest" not in startup_body.lower(),
        "new-game doctrine lifecycle must not carry startup migration or test events",
    )
    religion_change_body = named_block_body(on_action, "on_religion_change")
    require(
        len(re.findall(r"(?m)^\s*zhx_doctrine\.92\s*$", religion_change_body))
        == 1
        and on_action.count("zhx_doctrine.92") == 1,
        "on_religion_change must dispatch zhx_doctrine.92 exactly once",
    )
    yearly_body = named_block_body(on_action, "on_yearly_pulse")
    require(
        "zhx_doctrine.91" not in yearly_body
        and "zhx_doctrine.92" not in yearly_body,
        "the yearly pulse must reach school sync/retirement through shared effects",
    )

    modifier_text = texts[MOD / "common/event_modifiers/zhx_doctrine_modifiers.txt"]
    modifier_definitions = set(
        re.findall(r"(?m)^(zhx_doctrine_[a-z0-9_]+)\s*=\s*\{", modifier_text)
    )
    require(
        modifier_definitions == EXPECTED_MODIFIERS,
        "modifier definition contract changed: "
        f"missing={sorted(EXPECTED_MODIFIERS - modifier_definitions)}, "
        f"extra={sorted(modifier_definitions - EXPECTED_MODIFIERS)}",
    )

    all_scripts = "\n".join(texts.values())
    referenced_modifiers = set(
        re.findall(
            r"(?:name|has_country_modifier|remove_country_modifier)\s*=\s*"
            r"(zhx_doctrine_[a-z0-9_]+)",
            all_scripts,
        )
    )
    require(
        referenced_modifiers <= modifier_definitions,
        f"undefined doctrine modifiers: {sorted(referenced_modifiers - modifier_definitions)}",
    )

    effect_text = texts[MOD / "common/scripted_effects/zhx_doctrine_effects.txt"]
    trigger_text = texts[MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt"]
    for school, flag in EXPECTED_FLAGS.items():
        setters = re.findall(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", effect_text)
        require(len(setters) == 1, f"{flag} must be set exactly once")
        body = top_level_effect_body(effect_text, f"zhx_adopt_{school}_doctrine")
        require(
            re.search(rf"set_country_flag\s*=\s*{re.escape(flag)}\b", body) is not None,
            f"{flag} may only be set by its adoption effect",
        )

    all_doctrine_flags = set(NATIVE_SCHOOL_FLAGS.values())
    any_flag_trigger = named_block_body(trigger_text, "zhx_has_any_doctrine_flag")
    clear_flags_effect = top_level_effect_body(effect_text, "zhx_clear_doctrine_flags")
    for flag in all_doctrine_flags:
        require(
            any_flag_trigger.count(f"has_country_flag = {flag}") == 1
            and clear_flags_effect.count(f"clr_country_flag = {flag}") == 1,
            f"conversion lifecycle must detect and clear reserved doctrine flag {flag}",
        )
    clear_system_effect = top_level_effect_body(effect_text, "zhx_clear_doctrine_system")
    require(
        "zhx_remove_doctrine_tier_modifiers = yes" in clear_system_effect
        and "zhx_clear_doctrine_flags = yes" in clear_system_effect
        and "clr_country_flag = zhx_doctrine_practice_initialised"
        in clear_system_effect
        and "remove_country_modifier = zhx_doctrine_change_cooldown"
        in clear_system_effect
        and clear_system_effect.count("value = 0") == 2
        and "which = zhx_doctrine_practice" in clear_system_effect
        and "which = zhx_doctrine_last_delta" in clear_system_effect,
        "doctrine cleanup must clear flags, tier/cooldown modifiers, practice and "
        "annual delta",
    )

    registered_sprites = set(
        re.findall(r'(?m)^\s*name\s*=\s*"(GFX_zhx_doctrine_[a-z0-9_]+)"', native_gfx)
    )
    require(
        set(NATIVE_SCHOOLS.values()) <= registered_sprites,
        f"missing native school sprites: {sorted(set(NATIVE_SCHOOLS.values()) - registered_sprites)}",
    )
    for school, picture in NATIVE_SCHOOLS.items():
        slug = school.removeprefix("zhx_").removesuffix("_school")
        texture_path = MOD / f"gfx/interface/zhx_doctrine_{slug}_school.tga"
        texture = texture_path.read_bytes() if texture_path.is_file() else b""
        require(
            len(texture) >= 18,
            f"missing or truncated school texture: {texture_path.relative_to(ROOT)}",
        )
        width, height, depth = struct.unpack_from("<HHB", texture, 12)
        require(
            (width, height, depth) == (52, 52, 32)
            and texture[2] in {2, 10}
            and texture[17] & 0x0F == 8,
            f"{texture_path.name} must be a 52x52 32-bit true-colour TGA with alpha",
        )
        sprite_tail = native_gfx.split(f'name = "{picture}"', 1)[1][:260]
        require(
            f'texturefile = "gfx/interface/{texture_path.name}"' in sprite_tail
            and 'loadType = "INGAME"' in sprite_tail,
            f"{picture} must load {texture_path.name} as an in-game sprite",
        )

    no_doctrine_picture = NO_DOCTRINE_SCHOOL["zhx_no_doctrine_school"]
    require(
        native_gfx.count(f'name = "{no_doctrine_picture}"') == 1,
        "transparent no-doctrine school sprite must be registered exactly once",
    )
    no_doctrine_texture_path = MOD / "gfx/interface/zhx_no_doctrine_school.tga"
    no_doctrine_texture = (
        no_doctrine_texture_path.read_bytes()
        if no_doctrine_texture_path.is_file()
        else b""
    )
    require(
        len(no_doctrine_texture) >= 18,
        "missing or truncated transparent no-doctrine school texture",
    )
    no_doctrine_width, no_doctrine_height, no_doctrine_depth = struct.unpack_from(
        "<HHB", no_doctrine_texture, 12
    )
    require(
        (no_doctrine_width, no_doctrine_height, no_doctrine_depth) == (52, 52, 32)
        and no_doctrine_texture[2] in {2, 10}
        and no_doctrine_texture[17] & 0x0F == 8
        and not any(
            decode_tga_alpha(no_doctrine_texture, no_doctrine_texture_path.name)
        ),
        "no-doctrine school texture must be a fully transparent 52x52 RGBA TGA",
    )
    no_doctrine_sprite_tail = native_gfx.split(
        f'name = "{no_doctrine_picture}"', 1
    )[1][:260]
    require(
        'texturefile = "gfx/interface/zhx_no_doctrine_school.tga"'
        in no_doctrine_sprite_tail
        and 'loadType = "INGAME"' in no_doctrine_sprite_tail,
        "no-doctrine native sprite must load the transparent in-game TGA",
    )

    for removed_control in REMOVED_RELIGION_CARD_CONTROLS:
        require(
            removed_control not in religion_view_body
            and removed_control not in native_custom_gui,
            f"obsolete overlapping religion card control remains: {removed_control}",
        )

    text_box = "zhx_religion_practice_value"
    require(
        religion_view_body.count(f'name = "{text_box}"') == 1,
        f"{text_box} must occur exactly once inside countryreligionview",
    )
    practice_body = named_instant_text_box_body(religion_view_body, text_box)
    require(
        re.search(r'text\s*=\s*""', practice_body) is not None
        and re.search(r"scripted\s*=\s*yes", practice_body) is not None
        and re.search(r'font\s*=\s*"vic_18"', practice_body) is not None
        and re.search(r"format\s*=\s*centre", practice_body) is not None,
        f"{text_box} must be a centred, empty scripted text box",
    )
    x, y, width, height = instant_text_box_rectangle(native_gui, text_box)
    require(
        (x, y, width, height) == (151, 157, 28, 24),
        f"{text_box} must stay in the 28x24 gap of the native school row",
    )
    require(
        native_custom_gui.count(f"name = {text_box}") == 1,
        f"{text_box} must have exactly one custom-text binding",
    )
    custom_body = named_custom_text_box_body(native_custom_gui, text_box)
    require(
        "zhx_is_lijiao_country = yes" in custom_body
        and "zhx_has_doctrine = yes" in custom_body
        and "tooltip = zhx_religion_practice_value_tt" in custom_body,
        f"{text_box} must be doctrine-gated and expose its compact status tooltip",
    )
    sync_body = top_level_effect_body(effect_text, "zhx_sync_native_doctrine_school")
    require(
        re.fullmatch(
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.91\s*\}\s*",
            sync_body,
            re.S,
        )
        is not None
        and "set_religious_school" not in effect_text,
        "native-school scripted effect must only dispatch the directly loaded "
        "zhx_doctrine.91 mirror event",
    )
    mirror_event = country_event_body(event_text, "zhx_doctrine.91")
    mirror_trigger = named_block_body(mirror_event, "trigger")
    mirror_immediate = named_block_body(mirror_event, "immediate")
    mirror_option = named_block_body(mirror_event, "option")
    require(
        mirror_event.count("hidden = yes") == 1
        and mirror_event.count("is_triggered_only = yes") == 1
        and "zhx_is_lijiao_country = yes" in mirror_trigger,
        "zhx_doctrine.91 must be a hidden, triggered-only Ritual Teaching event",
    )
    require(
        not re.search(
            r"\b(?:mean_time_to_happen|random|random_list|days|months|years)\b",
            mirror_event,
        )
        and mirror_event.count("option = {") == 1
        and re.fullmatch(r"\s*name\s*=\s*OK\s*", mirror_option) is not None,
        "zhx_doctrine.91 must execute immediately and expose only an inert OK option",
    )
    require(
        mirror_immediate.count("set_religious_school = {") == len(NATIVE_SCHOOLS)
        and mirror_immediate.count("group = eastern") == len(NATIVE_SCHOOLS),
        "zhx_doctrine.91 must directly own six eastern native-school assignments",
    )
    retire_event = country_event_body(event_text, "zhx_doctrine.92")
    retire_trigger = named_block_body(retire_event, "trigger")
    retire_immediate = named_block_body(retire_event, "immediate")
    retire_option = named_block_body(retire_event, "option")
    require(
        retire_event.count("hidden = yes") == 1
        and retire_event.count("is_triggered_only = yes") == 1
        and "zhx_has_any_doctrine_flag = yes" in retire_trigger
        and "has_religious_school = yes" in retire_trigger
        and "NOT = { zhx_is_lijiao_country = yes }" in retire_trigger
        and "NOT = { zhx_has_any_doctrine_flag = yes }" in retire_trigger,
        "zhx_doctrine.92 must cover departure from 礼教 and stale-mirror "
        "retirement when returning without a doctrine",
    )
    require(
        retire_event.count("option = {") == 1
        and re.fullmatch(r"\s*name\s*=\s*OK\s*", retire_option) is not None
        and retire_immediate.count("set_religious_school = {") == 1
        and retire_immediate.count("group = eastern") == 2
        and retire_immediate.count("school = zhx_no_doctrine_school") == 1
        and "limit = { religion_group = eastern }" in retire_immediate
        and retire_immediate.count("zhx_clear_doctrine_system = yes") == 1,
        "zhx_doctrine.92 must gate one direct eastern sentinel assignment, then "
        "clear authoritative doctrine state",
    )
    retire_body = top_level_effect_body(effect_text, "zhx_retire_doctrine_system")
    require(
        re.fullmatch(
            r"\s*country_event\s*=\s*\{\s*id\s*=\s*zhx_doctrine\.92\s*\}\s*",
            retire_body,
            re.S,
        )
        is not None
        and "zhx_retire_doctrine_system = yes"
        in country_event_body(event_text, "zhx_doctrine.90"),
        "the annual safety path must dispatch the direct zhx_doctrine.92 "
        "lifecycle event through the retirement effect",
    )
    require(
        event_text.count("set_religious_school = {")
        == len(NATIVE_SCHOOLS) + len(NO_DOCTRINE_SCHOOL)
        and all(
            "set_religious_school" not in script
            for path, script in texts.items()
            if path != MOD / "events/zhx_doctrine_events.txt"
        )
        and "set_religious_school" not in on_action,
        "all production native-school assignments must live only in the direct "
        "zhx_doctrine.91/.92 events",
    )
    route_kinds = re.findall(r"(?m)^\s*(if|else_if)\s*=", mirror_immediate)
    require(
        route_kinds == ["if", "else_if", "else_if", "else_if", "else_if", "else_if"],
        "zhx_doctrine.91 must route the six doctrine flags through one exclusive if chain",
    )
    branch_offsets: list[int] = []
    for school, flag in NATIVE_SCHOOL_FLAGS.items():
        branch = re.search(
            rf"(?:if|else_if)\s*=\s*\{{\s*"
            rf"limit\s*=\s*\{{[^}}]*has_country_flag\s*=\s*{re.escape(flag)}"
            rf"[^}}]*\}}\s*set_religious_school\s*=\s*\{{\s*"
            rf"group\s*=\s*eastern\s*school\s*=\s*{re.escape(school)}\s*\}}\s*\}}",
            mirror_immediate,
            re.S,
        )
        require(
            branch is not None
            and mirror_trigger.count(f"has_country_flag = {flag}") == 1
            and mirror_immediate.count(f"has_country_flag = {flag}") == 1
            and mirror_immediate.count(f"school = {school}") == 1,
            f"zhx_doctrine.91 does not map {flag} to {school} exactly once",
        )
        branch_offsets.append(branch.start())
    require(
        branch_offsets == sorted(branch_offsets),
        "zhx_doctrine.91 school priority must remain Ru, Fa, Mo, Dao, Bing, Zongheng",
    )
    require(
        not re.search(
            r"\b(?:set_country_flag|clr_country_flag|set_variable|change_variable|"
            r"add_country_modifier|add_adm_power|add_dip_power|add_mil_power|"
            r"change_religion|change_province_religion|country_event|province_event|"
            r"hidden_effect|after)\b",
            mirror_immediate,
        ),
        "native-school mirror event must not mutate authoritative doctrine gameplay state",
    )
    require(
        "zhx_sync_native_doctrine_school = yes"
        in top_level_effect_body(effect_text, "zhx_finish_doctrine_adoption"),
        "doctrine adoption must retain the compatibility hook",
    )
    require(
        "zhx_sync_native_doctrine_school = yes"
        in top_level_effect_body(effect_text, "zhx_yearly_doctrine_tick"),
        "the yearly tick must retain the compatibility hook for existing saves",
    )
    require(
        len(
            re.findall(
                r"(?m)^\s*zhx_sync_native_doctrine_school\s*=\s*yes\s*$",
                all_scripts,
            )
        )
        == 2,
        "only doctrine adoption and the yearly tick may call the native-school sync hook",
    )

    for token, reason in FORBIDDEN_TOKENS.items():
        require(
            re.search(rf"\b{re.escape(token)}\b", all_scripts) is None,
            f"forbidden token {token}: {reason}",
        )

    require(
        "religion = confucianism" in texts[MOD / "common/scripted_triggers/zhx_doctrine_triggers.txt"],
        "the Ritual Teaching eligibility trigger must use confucianism",
    )
    require(
        "duration = 3650" in effect_text,
        "successful doctrine adoption must retain the ten-year cooldown",
    )
    require(event_text.count("duration = 1825") == 3, "each no-verdict path needs five years")
    require(event_text.count("duration = 730") == 1, "postponement needs two years")

    localisation_keys = re.findall(r"(?m)^\s*([^\s:#]+):\d+\s+\"", localisation)
    require(
        len(localisation_keys) == len(set(localisation_keys)),
        "duplicate keys in doctrine readable localisation",
    )
    actual_localisation = set(localisation_keys)
    expected_with_modifiers = EXPECTED_LOCALISATION | EXPECTED_MODIFIERS | {
        f"{modifier}_desc" for modifier in EXPECTED_MODIFIERS
    }
    require(
        expected_with_modifiers <= actual_localisation,
        f"missing doctrine localisation: {sorted(expected_with_modifiers - actual_localisation)}",
    )

    native_localisation_keys = re.findall(
        r'(?m)^\s*([^\s:#]+):\d+\s+"', native_localisation
    )
    require(
        len(native_localisation_keys) == len(set(native_localisation_keys)),
        "duplicate keys in native-school readable localisation",
    )
    expected_native_localisation = set(ALL_NATIVE_SCHOOLS) | {
        f"{school}_desc" for school in ALL_NATIVE_SCHOOLS
    } | NATIVE_STATUS_FIELDS | {
        "zhx_religion_practice_value_tt",
    }
    require(
        set(native_localisation_keys) == expected_native_localisation,
        "native school localisation contract changed",
    )

    print("Ritual Teaching doctrine prototype static contract: PASS")
    print(f"  Clausewitz files: {len(SCRIPT_PATHS) + 1}")
    print(f"  Events: {len(event_ids)}")
    print(f"  Doctrine modifiers: {len(modifier_definitions)}")
    print("  Compact native-row practice displays: 1")
    print(f"  Native visible school mirrors: {len(NATIVE_SCHOOLS)}")
    print(f"  Native no-doctrine sentinels: {len(NO_DOCTRINE_SCHOOL)}")
    print(f"  Readable localisation keys: {len(localisation_keys)}")


if __name__ == "__main__":
    main()
