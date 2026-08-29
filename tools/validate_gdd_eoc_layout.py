#!/usr/bin/env python3
"""Validate the integrated Mandate / Zhou-member window layout."""

from __future__ import annotations

from io import BytesIO
import re
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
GUI = MOD / "interface/celestialempireview.gui"
CUSTOM_GUI = MOD / "common/custom_gui/gdd_celestial_vassal_shields.txt"
LOCALISATION = MOD / "localisation_source/gdd_l_english_readable_utf8.txt"


def controls(text: str) -> dict[str, dict[str, float | int]]:
    """Read direct children of celestial_window; nested position braces are safe."""
    parsed: dict[str, dict[str, float | int]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if re.match(r"^\t\t(?:guiButtonType|iconType|instantTextBoxType) = \{$", line):
            current = [line]
            continue
        if current is None:
            continue
        current.append(line)
        if line != "\t\t}":
            continue
        block = "\n".join(current)
        current = None
        name_match = re.search(r'\bname = "([^"]+)"', block)
        if not name_match:
            continue
        values: dict[str, float | int] = {}
        position = re.search(r"position = \{ x = (-?\d+) y = (-?\d+) \}", block)
        scale = re.search(r"\bscale = ([0-9.]+)", block)
        size = re.search(r"size = \{ x = (\d+) y = (\d+) \}", block)
        if position:
            values["x"], values["y"] = map(int, position.groups())
        if scale:
            values["scale"] = float(scale.group(1))
        if size:
            values["width"], values["height"] = map(int, size.groups())
        parsed[name_match.group(1)] = values
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def custom_block(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^custom_(?:button|icon) = \{{\n    name = {re.escape(name)}\n.*?^\}}$",
        text,
    )
    require(match is not None, f"missing scripted GUI binding: {name}")
    return match.group(0)


def main() -> None:
    gui_text = GUI.read_text(encoding="utf-8")
    custom_text = CUSTOM_GUI.read_text(encoding="utf-8")
    parsed = controls(gui_text)

    require(gui_text.count("{") == gui_text.count("}"), "unbalanced GUI braces")
    require(custom_text.count("{") == custom_text.count("}"),
            "unbalanced scripted-GUI braces")

    decree_names = [
        name
        for name in parsed
        if name.startswith("gdd_decree_") and name.endswith("_button")
    ]
    expected_decree_rows = {150 + 38 * row for row in range(12)}
    require(len(decree_names) == 18, "expected 18 decree controls")
    require(
        {int(parsed[name]["y"]) for name in decree_names} == expected_decree_rows,
        "decree rows do not fill the paged 12-row viewport",
    )
    require(
        all(
            parsed[name].get("x") == 123 and parsed[name].get("scale") == 1.0
            for name in decree_names
        ),
        "native-size compact decree scrolls are not centred",
    )
    require(
        gui_text.count('quadTextureSprite = "GFX_gdd_eoc_decree_button_compact"') == 18,
        "every visible decree must use the compact native-size scroll",
    )
    require(parsed["meritocracy_icon"]["x"] == 182
            and parsed["meritocracy_value"]["x"] == 190
            and parsed["meritocracy_value"]["y"] == 127,
            "meritocracy icon/value group is not aligned")

    page_one_decrees = [
        "expand_bureaucracy", "improved_expand_bureaucracy",
        "conduct_census", "improved_conduct_census",
        "promote_naval_officers", "increase_tariff_control",
        "improve_defence_effort", "boost_officer_corps",
        "fund_new_centers_of_education", "proclaim_dynastic_name",
        "issue_the_great_warnings", "six_ordinances",
        "sacred_edict_of_confucianism", "promote_taoist_studies",
    ]
    page_two_decrees = [
        "appoint_entrusted_eunuchs", "increase_trade_cooperation",
        "reinforce_the_inner_guard", "issue_bureaucratic_imperial_seal",
    ]
    for stem in page_one_decrees:
        for suffix in ("button", "active"):
            require("NOT = { has_country_flag = gdd_eoc_decree_page_2 }"
                    in custom_block(custom_text, f"gdd_decree_{stem}_{suffix}"),
                    f"page-one condition missing from {stem}_{suffix}")
    for stem in page_two_decrees:
        for suffix in ("button", "active"):
            require("has_country_flag = gdd_eoc_decree_page_2"
                    in custom_block(custom_text, f"gdd_decree_{stem}_{suffix}"),
                    f"page-two condition missing from {stem}_{suffix}")
    custom_block(custom_text, "gdd_eoc_decree_scroll_up")
    custom_block(custom_text, "gdd_eoc_decree_scroll_down")

    for name in ("gdd_eoc_member_scroll_up", "gdd_eoc_member_scroll_down"):
        block = custom_block(custom_text, name)
        require("hidden_trigger = { always = yes }" in block,
                f"member-scroll condition is visible for {name}")
        require("tooltip =" not in block,
                f"member-scroll arrow still exposes explanatory text: {name}")

    member_count_match = re.search(
        r"(?ms)^custom_text_box = \{\n    name = gdd_eoc_member_count\n.*?^\}$",
        custom_text,
    )
    require(member_count_match is not None, "missing member-count text binding")
    require("tooltip =" not in member_count_match.group(0),
            "member-count ribbon still exposes explanatory text")

    for index in range(1, 66):
        name = f"gdd_eoc_member_shield_{index:02d}"
        item = parsed.get(name)
        require(item is not None, f"missing member shield {index:02d}")
        page_index = (index - 1) % 48
        column = page_index % 8
        row = page_index // 8
        require(
            item.get("x") == 105 + column * 23
            and item.get("y") == 698 + row * 30
            and item.get("scale") == 0.55,
            f"member shield {index:02d} is outside the paged grid",
        )

    bindings = custom_text.split("# GDD_EOC_MEMBER_BINDINGS_BEGIN", 1)[1].split(
        "# GDD_EOC_MEMBER_BINDINGS_END", 1
    )[0]
    require(bindings.count("gdd_eoc_member_roster_page_2") == 65,
            "every member shield must have one page condition")

    require(parsed["gdd_eoc_member_frame"] == {
        "x": 98,
        "y": 650,
        "width": 220,
        "height": 250,
    }, "member frame geometry drifted")
    require(parsed["gdd_eoc_member_count"]["x"] == 108
            and parsed["gdd_eoc_member_count"]["y"] == 659,
            "member count is not centred in the reused original ribbon")
    require("gdd_eoc_decree_frame" not in parsed, "decree gold frame must stay removed")
    require(parsed["gdd_eoc_decree_scroll_track"]["x"] == 302,
            "decree scrollbar is not on the right edge")
    require(parsed["gdd_eoc_decree_scroll_track"]["height"] == 380,
            "decree scrollbar does not span the extended decree column")
    require(parsed["gdd_eoc_member_scroll_track"]["x"] == 300,
            "member scrollbar is not on the right edge")
    require(parsed["gdd_principal_vassal_slot"]["y"] == 746, "principal feudatory not lowered")
    for index in range(1, 7):
        require(parsed[f"gdd_vassal_slot_{index}"]["y"] == 820, "great feudatory row not lowered")
    require(parsed["gdd_eoc_authority_track"]["y"] == 328, "authority track is not tucked under the nameplate")
    require(parsed["emperor_label"]["y"] == 258, "emperor label is not centred on the extended nameplate")
    require(parsed["decisions_label"]["x"] == 812
            and parsed["decisions_label"]["y"] == 91,
            "Celestial Reforms title moved off its original green ribbon")
    require(parsed["influence_label"]["y"] == 91
            and parsed["influence_value"]["x"] == 625
            and parsed["influence_value"]["y"] == 128
            and parsed["influence_growth"]["x"] == 625
            and parsed["influence_growth"]["y"] == 168,
            "Mandate label and values are not aligned as one block")

    localisation = LOCALISATION.read_text(encoding="utf-8-sig")
    require(
        "GDD_CELESTIAL_GREAT_FEUDATORIES:0 \"七大诸侯\"" in localisation,
        "missing seven-great-feudatories localisation",
    )

    sys.path.insert(0, str(ROOT / "tools"))
    import generate_gdd_eoc_reform_groups as groups
    import generate_gdd_eoc_wide_background as background

    require(background.OUTPUT.read_bytes() == background.render(), "stale Mandate background")
    require(groups.OUTPUT.read_bytes() == groups.render(), "stale grouped-panel overlay")
    require(groups.DECREE_OUTPUT.read_bytes() == groups.render_compact_decree_button(),
            "stale compact decree scroll")

    overlay = Image.open(BytesIO(groups.render())).convert("RGBA")
    for gui_x, gui_y, label in (
        (900, 200, "ordinary"),
        (900, 500, "centralising"),
        (900, 780, "decentralising"),
        (900, 95, "Celestial Reforms ribbon"),
    ):
        alpha = overlay.getpixel((gui_x - groups.BACKGROUND_X,
                                  gui_y - groups.BACKGROUND_Y))[3]
        require(alpha == 0, f"overlay still covers transparent {label} area")
    print("Integrated Mandate / Zhou-member layout: PASS")
    print("  Centred decrees fill the extended functional 12 + 4 page viewport")
    print("  Short member panel uses a functional 48 + 17 page scrollbar")
    print("  Emperor and Mandate share the top row; authority track is tucked below")
    print("  Principal plus six great feudatories occupy the lower centre")


if __name__ == "__main__":
    main()
