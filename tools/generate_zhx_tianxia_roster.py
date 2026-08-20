#!/usr/bin/env python3
"""Generate the dynamic Zhou-member shield grid and presentation cache."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "guangdong_independent_practice/interface/countrydecisionsview.gui"
CUSTOM_GUI = ROOT / "guangdong_independent_practice/common/custom_gui/zhx_tianxia_gui.txt"
EFFECTS = ROOT / "guangdong_independent_practice/common/scripted_effects/zhx_gui_roster_effects.txt"
EOC_GUI = ROOT / "guangdong_independent_practice/interface/celestialempireview.gui"
EOC_CUSTOM_GUI = ROOT / "guangdong_independent_practice/common/custom_gui/gdd_celestial_vassal_shields.txt"

SLOTS = 200
EOC_SLOTS = 65
EOC_COLUMNS = 12
EOC_ROWS = 4
EOC_PAGE_SIZE = EOC_COLUMNS * EOC_ROWS
EOC_GRID_X = 347
EOC_GRID_Y = 671
EOC_COLUMN_STEP = 27
EOC_ROW_STEP = 26


def replace_generated_block(path: Path, begin: str, end: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    before, remainder = text.split(begin, maxsplit=1)
    _, after = remainder.split(end, maxsplit=1)
    path.write_text(f"{before}{begin}\n{body}\n{end}{after}", encoding="utf-8")


def gui_blocks() -> str:
    blocks = []
    for index in range(1, SLOTS + 1):
        column = (index - 1) % 24
        row = (index - 1) // 24
        x = 83 + column * 34
        y = 575 + row * 33
        blocks.append(
            "\n".join(
                [
                    "\t\t\tguiButtonType = {",
                    f"\t\t\t\tname = \"zhx_gui_member_shield_{index:02d}\"",
                    "\t\t\t\tquadTextureSprite = \"GFX_shield_small\"",
                    f"\t\t\t\tposition = {{ x = {x} y = {y} }}",
                    "\t\t\t\tclicksound = click",
                    "\t\t\t\tscripted = yes",
                    "\t\t\t}",
                ]
            )
        )
    return "\n\n".join(blocks)


def binding_blocks() -> str:
    blocks = []
    for index in range(1, SLOTS + 1):
        target = f"zhx_roster_{index:02d}"
        blocks.append(
            "\n".join(
                [
                    "custom_shield = {",
                    f"    name = zhx_gui_member_shield_{index:02d}",
                    "    potential = {",
                    "        has_global_flag = zhx_gui_roster_initialised",
                    f"        has_saved_global_event_target = {target}",
                    f"        event_target:{target} = {{",
                    "            exists = yes",
                    "            has_country_flag = zhx_member",
                    "        }",
                    "    }",
                    "    trigger = { always = yes }",
                    "    tooltip = zhx_gui_member_shield_tt",
                    f"    global_event_target = {target}",
                    "    open_country = yes",
                    "}",
                ]
            )
        )
    return "\n\n".join(blocks)


def eoc_gui_blocks() -> str:
    """Build the paged Mandate copy using the vanilla tributary shield spacing."""
    blocks = []
    for index in range(1, EOC_SLOTS + 1):
        page_index = (index - 1) % EOC_PAGE_SIZE
        column = page_index % EOC_COLUMNS
        row = page_index // EOC_COLUMNS
        # Four rows fit wholly inside the original tributary frame. The second
        # page restarts at the top instead of spilling through the lower border.
        x = EOC_GRID_X + column * EOC_COLUMN_STEP
        y = EOC_GRID_Y + row * EOC_ROW_STEP
        blocks.append(
            "\n".join(
                [
                    "\t\tguiButtonType = {",
                    f"\t\t\tname = \"gdd_eoc_member_shield_{index:02d}\"",
                    "\t\t\tquadTextureSprite = \"GFX_shield_small\"",
                    f"\t\t\tposition = {{ x = {x} y = {y} }}",
                    "\t\t\tclicksound = click",
                    "\t\t\tscale = 0.75",
                    "\t\t\tscripted = yes",
                    "\t\t}",
                ]
            )
        )
    return "\n\n".join(blocks)


def eoc_binding_blocks() -> str:
    blocks = []
    for index in range(1, EOC_SLOTS + 1):
        target = f"gdd_eoc_member_roster_{index:02d}"
        if index <= EOC_PAGE_SIZE:
            page_condition = "        NOT = { has_country_flag = gdd_eoc_member_roster_page_2 }"
        else:
            page_condition = "        has_country_flag = gdd_eoc_member_roster_page_2"
        blocks.append(
            "\n".join(
                [
                    "custom_shield = {",
                    f"    name = gdd_eoc_member_shield_{index:02d}",
                    "    potential = {",
                    "        has_global_flag = gdd_eoc_member_roster_initialised",
                    page_condition,
                    f"        has_saved_global_event_target = {target}",
                    f"        event_target:{target} = {{",
                    "            exists = yes",
                    "            has_country_flag = zhx_member",
                    "            NOT = { tag = MNG }",
                    "        }",
                    "    }",
                    "    trigger = { always = yes }",
                    "    tooltip = GDD_EOC_MEMBER_SHIELD_TT",
                    f"    global_event_target = {target}",
                    "    open_country = yes",
                    "}",
                ]
            )
        )
    return "\n\n".join(blocks)


def effect_file() -> str:
    lines = [
        "# Generated by tools/generate_zhx_tianxia_roster.py.",
        "# These event targets are a GUI cache; zhx_member remains authoritative.",
        "zhx_clear_gui_roster = {",
    ]
    for index in range(1, SLOTS + 1):
        lines.extend(
            [
                "    if = {",
                f"        limit = {{ has_saved_global_event_target = zhx_roster_{index:02d} }}",
                f"        clear_global_event_target = zhx_roster_{index:02d}",
                "    }",
            ]
        )
    lines.extend(["}", "", "zhx_allocate_gui_roster_slot = {"])
    for index in range(1, SLOTS + 1):
        keyword = "if" if index == 1 else "else_if"
        lines.extend(
            [
                f"    {keyword} = {{",
                f"        limit = {{ NOT = {{ has_saved_global_event_target = zhx_roster_{index:02d} }} }}",
                f"        save_global_event_target_as = zhx_roster_{index:02d}",
                "    }",
            ]
        )
    lines.extend(
        [
            "}",
            "",
            "zhx_build_gui_roster = {",
            "    zhx_clear_gui_roster = yes",
            "    every_country = {",
            "        limit = {",
            "            exists = yes",
            "            has_country_flag = zhx_member",
            "        }",
            "        zhx_allocate_gui_roster_slot = yes",
            "    }",
            "    set_global_flag = zhx_gui_roster_initialised",
            "    gdd_build_eoc_member_roster = yes",
            "}",
            "",
        ]
    )

    lines.extend(
        [
            "# Independent compact cache for the Mandate-window copy.",
            "# MNG is deliberately excluded without changing the Zhou Council roster.",
            "gdd_clear_eoc_member_roster = {",
        ]
    )
    for index in range(1, EOC_SLOTS + 1):
        lines.extend(
            [
                "    if = {",
                f"        limit = {{ has_saved_global_event_target = gdd_eoc_member_roster_{index:02d} }}",
                f"        clear_global_event_target = gdd_eoc_member_roster_{index:02d}",
                "    }",
            ]
        )
    lines.extend(["}", "", "gdd_allocate_eoc_member_roster_slot = {"])
    for index in range(1, EOC_SLOTS + 1):
        keyword = "if" if index == 1 else "else_if"
        lines.extend(
            [
                f"    {keyword} = {{",
                f"        limit = {{ NOT = {{ has_saved_global_event_target = gdd_eoc_member_roster_{index:02d} }} }}",
                f"        save_global_event_target_as = gdd_eoc_member_roster_{index:02d}",
                "    }",
            ]
        )
    lines.extend(
        [
            "}",
            "",
            "gdd_build_eoc_member_roster = {",
            "    gdd_clear_eoc_member_roster = yes",
            "    CZH = {",
            "        set_variable = {",
            "            which = gdd_eoc_member_count_cache",
            "            value = 0",
            "        }",
            "    }",
            "    every_country = {",
            "        limit = {",
            "            exists = yes",
            "            has_country_flag = zhx_member",
            "            NOT = { tag = MNG }",
            "        }",
            "        gdd_allocate_eoc_member_roster_slot = yes",
            "        CZH = {",
            "            change_variable = {",
            "                which = gdd_eoc_member_count_cache",
            "                value = 1",
            "            }",
            "        }",
            "    }",
            "    set_global_flag = gdd_eoc_member_roster_initialised",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    replace_generated_block(
        GUI,
        "\t\t\t# ZHX_ROSTER_SHIELDS_BEGIN",
        "\t\t\t# ZHX_ROSTER_SHIELDS_END",
        gui_blocks(),
    )
    replace_generated_block(
        CUSTOM_GUI,
        "# ZHX_ROSTER_BINDINGS_BEGIN",
        "# ZHX_ROSTER_BINDINGS_END",
        binding_blocks(),
    )
    replace_generated_block(
        EOC_GUI,
        "\t\t# GDD_EOC_MEMBER_SHIELDS_BEGIN",
        "\t\t# GDD_EOC_MEMBER_SHIELDS_END",
        eoc_gui_blocks(),
    )
    replace_generated_block(
        EOC_CUSTOM_GUI,
        "# GDD_EOC_MEMBER_BINDINGS_BEGIN",
        "# GDD_EOC_MEMBER_BINDINGS_END",
        eoc_binding_blocks(),
    )
    EFFECTS.write_text(effect_file(), encoding="utf-8")
    print(
        f"generated {SLOTS} Zhou Council slots and "
        f"{EOC_SLOTS} Mandate-window member slots"
    )


if __name__ == "__main__":
    main()
