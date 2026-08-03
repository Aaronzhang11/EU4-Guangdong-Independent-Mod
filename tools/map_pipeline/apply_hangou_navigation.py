#!/usr/bin/env python3
"""Apply the reviewed single-province Hangou navigable waterway."""

from pathlib import Path
import re

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
DRAFT = ROOT / "planning/hangou/hangou_single_full_draft.bmp"
PROVINCE_ID = 5117
COLOR = (29, 106, 158)


def apply_bitmaps():
    current = np.asarray(Image.open(MAP / "provinces.bmp").convert("RGB")).copy()
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    mask = np.all(reviewed == COLOR, axis=2)
    current[mask] = COLOR
    Image.fromarray(current).save(MAP / "provinces.bmp", format="BMP")

    height = np.asarray(Image.open(MAP / "heightmap.bmp").convert("L")).copy()
    height[mask] = 93
    Image.fromarray(height).save(MAP / "heightmap.bmp", format="BMP")

    with Image.open(MAP / "rivers.bmp") as image:
        palette = image.getpalette()
        rivers = np.asarray(image).copy()
    rivers[mask] = 254
    river_image = Image.fromarray(rivers, mode="P")
    river_image.putpalette(palette)
    river_image.save(MAP / "rivers.bmp", format="BMP")
    return current, mask


def update_definition():
    path = MAP / "definition.csv"
    lines = path.read_text(encoding="latin-1").splitlines()
    row = f"{PROVINCE_ID};{COLOR[0]};{COLOR[1]};{COLOR[2]};Hangou;x"
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{PROVINCE_ID};"):
            lines[i] = row
            replaced = True
            break
    if not replaced:
        lines.append(row)
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")


def update_map_lists():
    path = MAP / "default.map"
    text = path.read_text()
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5118", text)
    marker = "5032 5033 5034 5035 5036 5037 5038 5039 5040 5041 5042 5043 5044 1655 1897 1896"
    if "5117 # Navigable Yangtze, Huai and Hangou waterways" not in text:
        text = text.replace(marker + " # Navigable Yangtze and Huai waterways", marker + " 5117 # Navigable Yangtze, Huai and Hangou waterways")
    path.write_text(text)

    path = MAP / "area.txt"
    text = path.read_text()
    if "hangou_waterway_area" not in text:
        anchor = "huai_river_area = { #7\n    5039 5040 5041 5042 1896 5043 5044\n}"
        text = text.replace(anchor, anchor + "\n\nhangou_waterway_area = { #1\n    5117\n}")
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    if "        hangou_waterway_area" not in text:
        text = text.replace("        huai_river_area", "        huai_river_area\n        hangou_waterway_area", 1)
    path.write_text(text)

    path = MAP / "terrain.txt"
    text = path.read_text()
    marker = "5032 5033 5034 5035 5036 5037 5038 1655 1897 5039 5040 5041 5042 1896 5043 5044"
    if marker + " 5117" not in text:
        text = text.replace(marker + " # Navigable Yangtze and Huai", marker + " 5117 # Navigable Yangtze, Huai and Hangou")
    path.write_text(text)


def update_history():
    path = MOD / "history/provinces/5117 - Hangou.txt"
    path.write_text("""discovered_by = chinese
discovered_by = nomad_group
add_permanent_province_modifier = {
    name = huai_river_engagement
    duration = -1
}
1519.1.1 = { discovered_by = POR }
""")


def update_position(bitmap, mask):
    yy, xx = np.nonzero(mask)
    x = float(np.median(xx))
    y = float(2048 - np.median(yy))
    block = f"""#Hangou navigable waterway
5117={{
    position={{
        {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} 0.000 0.000
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
}}"""
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    if re.search(r"(?m)^5117\s*=\s*\{", text):
        start = re.search(r"(?m)^5117\s*=\s*\{", text).start()
        brace = text.find("{", start)
        depth = 0
        for end in range(brace, len(text)):
            if text[end] == "{": depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    text = text[:start] + block + text[end + 1:]
                    break
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_hangou_navigation_readable_utf8.txt"
    path.write_text("""l_english:
 PROV5117:0 "邗沟"
 PROV_ADJ5117:0 "邗沟"
 hangou_waterway_area:0 "邗沟水道"
 hangou_waterway_area_name:0 "邗沟"
 hangou_waterway_area_adj:0 "邗沟水道"
""")


def main():
    bitmap, mask = apply_bitmaps()
    update_definition()
    update_map_lists()
    update_history()
    update_position(bitmap, mask)
    update_localisation()
    print(f"HANGOU_NAVIGATION_APPLIED:{int(mask.sum())}")


if __name__ == "__main__":
    main()
