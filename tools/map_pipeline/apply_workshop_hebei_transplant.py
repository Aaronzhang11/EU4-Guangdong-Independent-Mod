#!/usr/bin/env python3
"""Transplant the workshop mod's North Zhili geometry into this mod."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/hebei"
SOURCE_MOD = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/"
    "workshop/content/236850/1728520255"
)
SOURCE_MAP = SOURCE_MOD / "map"

# In North China the larger workshop canvas is the same projection with this
# constant margin. No resampling is required, so internal boundaries survive.
SOURCE_X_OFFSET = 438
SOURCE_Y_OFFSET = 9

SOURCE_AREAS = {
    "yandu_area": [1816, 5214, 5215, 5217, 5216],
    "dong_hebei_area": [4194, 5211, 5212, 5213],
    "zhong_hebei_area": [695, 696, 5222, 5223, 5219],
    "south_hebei_area": [2137, 4195, 5221, 5220, 5218],
}
SOURCE_IDS = [pid for ids in SOURCE_AREAS.values() for pid in ids]

# The source capital-ring geometries retain this timeline's Yandu identities.
SOURCE_TO_TARGET = {
    1816: 1816,   # Beijing slot -> Ji
    5214: 5114,   # Jizhou -> Miyun
    5215: 5113,   # Changping
    5216: 5115,   # Bazhou -> Tongzhou
    5217: 5116,   # Zhuozhou
    **{pid: pid for pid in SOURCE_IDS if pid not in {1816, 5214, 5215, 5216, 5217}},
}

OLD_SCOPE_IDS = {
    703, 2136, 4194, 695, 696, 2137, 4195,
    5113, 5114, 1816, 5115, 5116,
}

NAMES = {
    695: ("Hejian", "河间"),
    696: ("Baoding", "保定"),
    1816: ("Ji", "蓟"),
    2137: ("Daming", "大名"),
    4194: ("Yongping", "永平"),
    4195: ("Zhending", "真定"),
    5113: ("Changping", "昌平"),
    5114: ("Miyun", "密云"),
    5115: ("Tongzhou", "通州"),
    5116: ("Zhuozhou", "涿州"),
    5211: ("Linyuguan", "临渝关"),
    5212: ("Luanzhou", "滦州"),
    5213: ("Zunhua", "遵化"),
    5218: ("Yizhou", "易州"),
    5219: ("Jizhou", "冀州"),
    5220: ("Xingtai", "邢台"),
    5221: ("Guangping", "广平"),
    5222: ("Zhigu", "直沽"),
    5223: ("Cangzhou", "沧州"),
}

NEW_IDS = [5211, 5212, 5213, 5218, 5219, 5220, 5221, 5222, 5223]
# These two IDs inherit exact filenames from the Chinese map dependency.  The
# contents use the B44 names, but the paths must stay stable to shadow it.
HISTORY_FILENAMES = {
    5211: "5211 - Shanhaiguan.txt",
    5222: "5222 - Tianjin.txt",
}
GOODS = {
    5211: "grain", 5212: "fish", 5213: "iron",
    5218: "grain", 5219: "grain", 5220: "cloth",
    5221: "cotton", 5222: "salt", 5223: "salt",
}
CULTURE_BY_ID = {
    696: "gdd_yan",
    5211: "gdd_dongyi",
    5212: "gdd_yan",
    5213: "gdd_yan",
    5218: "gdd_yan",
    5219: "gdd_yan",
    5220: "gdd_yan",
    5221: "gdd_yan",
    5222: "gdd_qi",
    5223: "gdd_qi",
}


def read_definitions(path: Path):
    by_id, by_colour = {}, {}
    for line in path.read_text(encoding="latin-1").splitlines():
        fields = line.split(";")
        if len(fields) >= 5 and fields[0].isdigit():
            pid = int(fields[0])
            colour = tuple(map(int, fields[1:4]))
            by_id[pid] = (colour, fields[4])
            by_colour[colour] = pid
    return by_id, by_colour


def colour_mask(bitmap: np.ndarray, colours):
    packed = ((bitmap[:, :, 0].astype(np.uint32) << 16)
              | (bitmap[:, :, 1].astype(np.uint32) << 8)
              | bitmap[:, :, 2].astype(np.uint32))
    keys = np.array([(r << 16) | (g << 8) | b for r, g, b in colours], dtype=np.uint32)
    return np.isin(packed, keys)


def replace_block(text: str, key: str, replacement: str):
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*\{{", text)
    if not match:
        return text.rstrip() + "\n\n" + replacement + "\n"
    start, brace, depth = match.start(), text.find("{", match.start()), 0
    for end in range(brace, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
            if depth == 0:
                return text[:start] + replacement + text[end + 1:]
    raise ValueError(f"Unclosed block: {key}")


def components(mask: np.ndarray):
    seen = np.zeros(mask.shape, dtype=bool)
    result = []
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        queue, comp = deque([(sx, sy)]), []
        seen[sy, sx] = True
        while queue:
            x, y = queue.popleft()
            comp.append((x, y))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0]
                        and mask[ny, nx] and not seen[ny, nx]):
                    seen[ny, nx] = True
                    queue.append((nx, ny))
        result.append(comp)
    return result


def nearest_existing_fill(bitmap, fill_mask, forbidden_mask):
    """Fill unmatched outer-border pixels from the nearest existing neighbour."""
    height, width = fill_mask.shape
    assigned = np.zeros(fill_mask.shape, dtype=bool)
    colours = np.zeros((*fill_mask.shape, 3), dtype=np.uint8)
    queue = deque()
    for y, x in zip(*np.nonzero(fill_mask)):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and not forbidden_mask[ny, nx]):
                colours[y, x] = bitmap[ny, nx]
                assigned[y, x] = True
                queue.append((x, y))
                break
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and fill_mask[ny, nx]
                    and not assigned[ny, nx]):
                colours[ny, nx] = colours[y, x]
                assigned[ny, nx] = True
                queue.append((nx, ny))
    if np.any(fill_mask & ~assigned):
        raise ValueError("Could not fill all retired Hebei pixels")
    return colours


def build_geometry(base_bitmap=None):
    target_path = base_bitmap or (MAP / "provinces.bmp")
    target = np.asarray(Image.open(target_path).convert("RGB")).copy()
    source = np.asarray(Image.open(SOURCE_MAP / "provinces.bmp").convert("RGB"))
    target_defs, target_colour_ids = read_definitions(MAP / "definition.csv")
    source_defs, source_colour_ids = read_definitions(SOURCE_MAP / "definition.csv")

    translated_source = source[
        SOURCE_Y_OFFSET:SOURCE_Y_OFFSET + target.shape[0],
        SOURCE_X_OFFSET:SOURCE_X_OFFSET + target.shape[1],
    ]
    source_mask = colour_mask(translated_source, [source_defs[p][0] for p in SOURCE_IDS])
    old_mask = colour_mask(target, [target_defs[p][0] for p in OLD_SCOPE_IDS])

    # The other mod has a different coastline layer. Keep this mod's Bohai Sea
    # so the province bitmap stays aligned with terrain, rivers, and heightmap.
    bohai = target_defs[4233][0]
    source_mask &= ~np.all(target == bohai, axis=2)
    changed_scope = source_mask | old_mask
    retired = old_mask & ~source_mask

    result = target.copy()
    unmatched = np.zeros(old_mask.shape, dtype=bool)
    safe_neighbour_ids = {703, 2115, 2136, 4233}
    for y, x in zip(*np.nonzero(retired)):
        source_id = source_colour_ids.get(tuple(translated_source[y, x]))
        if source_id in safe_neighbour_ids and source_id in target_defs:
            result[y, x] = target_defs[source_id][0]
        else:
            unmatched[y, x] = True
    if np.any(unmatched):
        # Recognised retired pixels (chiefly Chengde and Chahar) are valid
        # frontier seeds for source-only neighbour provinces that this mod
        # does not define.
        fill = nearest_existing_fill(result, unmatched, source_mask | unmatched)
        result[unmatched] = fill[unmatched]

    target_colours = {pid: target_defs[pid][0] for pid in SOURCE_TO_TARGET.values() if pid in target_defs}
    for pid in NEW_IDS:
        target_colours[pid] = source_defs[pid][0]
    for source_id, target_id in SOURCE_TO_TARGET.items():
        pixels = np.all(translated_source == source_defs[source_id][0], axis=2) & source_mask
        result[pixels] = target_colours[target_id]

    # The preserved Bohai coastline clips two diagonal Tianjin pixels from its
    # main body. Absorb any such tiny detached remnant into its bordering land
    # province while leaving the imported outer mask unchanged.
    imported_colours = {tuple(colour) for colour in target_colours.values()}
    for target_id, colour in target_colours.items():
        comps = components(np.all(result == colour, axis=2))
        if len(comps) <= 1:
            continue
        keep = max(comps, key=len)
        for comp in comps:
            if comp is keep:
                continue
            neighbours = []
            for x, y in comp:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < result.shape[1] and 0 <= ny < result.shape[0]:
                        candidate = tuple(result[ny, nx])
                        if candidate != tuple(colour) and candidate != bohai and candidate in imported_colours:
                            neighbours.append(candidate)
            if not neighbours:
                raise ValueError(f"Detached province remnant without land neighbour: {target_id}")
            replacement = max(set(neighbours), key=neighbours.count)
            for x, y in comp:
                result[y, x] = replacement

    # If the new outer boundary clips a neighbouring target province, remove
    # only the tiny remnants it leaves behind (four Liaoxi pixels in practice).
    displaced_colours = np.unique(target[source_mask & ~old_mask].reshape(-1, 3), axis=0)
    for displaced_colour in map(tuple, displaced_colours):
        displaced_id = target_colour_ids.get(displaced_colour)
        if displaced_id is None or displaced_colour in imported_colours or displaced_id == 4233:
            continue
        before = components(np.all(target == displaced_colour, axis=2))
        after = components(np.all(result == displaced_colour, axis=2))
        if len(before) != 1 or len(after) <= 1:
            continue
        keep = max(after, key=len)
        for comp in after:
            if comp is keep:
                continue
            neighbours = []
            for x, y in comp:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < result.shape[1] and 0 <= ny < result.shape[0]:
                        candidate = tuple(result[ny, nx])
                        if candidate in imported_colours:
                            neighbours.append(candidate)
            if not neighbours:
                continue
            replacement = max(set(neighbours), key=neighbours.count)
            for x, y in comp:
                result[y, x] = replacement
                changed_scope[y, x] = True

    if np.any(result[~changed_scope] != target[~changed_scope]):
        raise AssertionError("Pixels outside Hebei/Yandu scope changed")

    return result, target, source_mask, old_mask, changed_scope, target_colours, source_defs


def update_definition(target_colours, source_defs):
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    replacements = {696: (target_colours[696], "Baoding")}
    replacements.update({pid: (source_defs[pid][0], NAMES[pid][0]) for pid in NEW_IDS})
    seen, output = set(), []
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in replacements:
            pid = int(fields[0])
            colour, name = replacements[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid in sorted(replacements):
        if pid not in seen:
            colour, name = replacements[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_areas():
    path = MAP / "area.txt"
    text = path.read_text()
    blocks = {
        "hebei_area": "hebei_area = {\n    703 2136 5351 5352 5353\n}",
        "yandu_area": "yandu_area = {\n    5113 5114 1816 5115 5116\n}",
        "dong_hebei_area": "dong_hebei_area = {\n    4194 5211 5212 5213\n}",
        "zhong_hebei_area": "zhong_hebei_area = {\n    695 696 5222 5223 5219\n}",
        "south_hebei_area": "south_hebei_area = {\n    2137 4195 5221 5220 5218\n}",
    }
    for key, block in blocks.items():
        text = replace_block(text, key, block)
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    for area in ("dong_hebei_area", "zhong_hebei_area"):
        if re.search(rf"(?m)^\s*{area}\s*$", text) is None:
            text = text.replace("        hebei_area\n", f"        hebei_area\n        {area}\n", 1)
    path.write_text(text)


def update_lists():
    new_line = "        5211 5212 5213 5218 5219 5220 5221 5222 5223 # Workshop North Zhili"
    path = MAP / "continent.txt"
    text = path.read_text()
    if "5211 5212 5213 5218" not in text:
        text = text.replace("        5113 5114 5115 5116 # B21 Yandu refinement",
                            "        5113 5114 5115 5116 # B21 Yandu refinement\n" + new_line, 1)
    path.write_text(text)

    path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = path.read_text()
    if "5211 5212 5213 5218" not in text:
        text = text.replace("        5113 5114 5115 5116 # B21 Yandu",
                            "        5113 5114 5115 5116 # B21 Yandu\n" + new_line, 1)
    path.write_text(text)

    path = MAP / "default.map"
    text = path.read_text()
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5224", text)
    path.write_text(text)


def history_text(pid):
    name = NAMES[pid][0]
    goods = GOODS[pid]
    tax, production, manpower = {
        5211: (2, 2, 2), 5212: (3, 3, 3), 5213: (3, 3, 3),
        5218: (3, 2, 3), 5219: (4, 3, 4), 5220: (4, 4, 5),
        5221: (3, 3, 3), 5222: (4, 4, 4), 5223: (3, 3, 3),
    }[pid]
    return f'''# {pid} - {name}\n\nowner = MNG\ncontroller = MNG\nadd_core = MNG\n'''+ \
        f'''culture = {CULTURE_BY_ID[pid]}\nreligion = confucianism\ncapital = "{name}"\ntrade_goods = {goods}\n''' + \
        f'''base_tax = {tax}\nbase_production = {production}\nbase_manpower = {manpower}\n''' + \
        '''is_city = yes\ndiscovered_by = chinese\ndiscovered_by = nomad_group\n'''


def update_histories():
    directory = MOD / "history/provinces"
    for pid in NEW_IDS:
        desired = directory / HISTORY_FILENAMES.get(pid, f"{pid} - {NAMES[pid][0]}.txt")
        for old in directory.glob(f"{pid} - *.txt"):
            if old != desired:
                old.unlink()
        desired.write_text(history_text(pid))

    # Province 696 moves from the old Xuanfu geometry to Baoding.
    for old in directory.glob("696 - *.txt"):
        old.unlink()
    (directory / "696 - Baoding.txt").write_text(
        '''# 696 - Baoding\n\nowner = MNG\ncontroller = MNG\nadd_core = MNG\n'''
        f'''culture = {CULTURE_BY_ID[696]}\nreligion = confucianism\ncapital = "Baoding"\ntrade_goods = grain\n'''
        '''base_tax = 5\nbase_production = 4\nbase_manpower = 4\nis_city = yes\n'''
        '''discovered_by = chinese\ndiscovered_by = nomad_group\n'''
    )


def update_positions(bitmap, target_colours):
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    ids = sorted(set(SOURCE_TO_TARGET.values()) | {703, 2136})
    definitions, _ = read_definitions(MAP / "definition.csv")
    for pid in ids:
        colour = target_colours.get(pid, definitions[pid][0])
        yy, xx = np.nonzero(np.all(bitmap == colour, axis=2))
        if not len(xx):
            raise ValueError(f"Province {pid} has no pixels")
        x, y = float(np.median(xx)), float(bitmap.shape[0] - np.median(yy))
        name = NAMES.get(pid, (definitions[pid][1], ""))[0]
        block = f'''#{name} - workshop North Zhili transplant\n{pid}={{\n    position={{\n        {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} 0.000 0.000\n    }}\n    rotation={{\n        0.000 0.000 0.000 0.000 0.000 0.000 0.000\n    }}\n    height={{\n        0.000 0.000 1.000 0.000 0.000 0.000 0.000\n    }}\n}}'''
        text = replace_block(text, str(pid), block)
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_b24_workshop_hebei_utf8.txt"
    lines = ["l_english:"]
    for pid in sorted(NAMES):
        _, chinese = NAMES[pid]
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' dong_hebei_area:0 "冀东"', ' dong_hebei_area_name:0 "冀东"',
        ' zhong_hebei_area:0 "冀中"', ' zhong_hebei_area_name:0 "冀中"',
        ' south_hebei_area:0 "冀南"', ' south_hebei_area_name:0 "冀南"',
    ]
    path.write_text("\n".join(lines) + "\n")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(path, MOD / "localisation/gdd_b24_workshop_hebei_l_english.yml")


def render_preview(bitmap, source_mask, target_colours):
    yy, xx = np.nonzero(source_mask)
    pad = 10
    x0, x1 = int(xx.min()) - pad, int(xx.max()) + pad
    y0, y1 = int(yy.min()) - pad, int(yy.max()) + pad
    crop = bitmap[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(bitmap).save(OUT / "workshop_north_zhili_transplant_full.bmp")
    Image.fromarray(crop).save(OUT / "workshop_north_zhili_transplant_draft.bmp")

    scale = 6
    shown = Image.fromarray(crop).resize((crop.shape[1] * scale, crop.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 460, max(shown.height, 760)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 17)
    small = ImageFont.truetype(font_path, 15)
    draw.text((shown.width + 22, 20), "北直隶原图移植", fill=(20, 20, 20), font=title)
    draw.text((shown.width + 22, 60), "原省界平移；燕都五省保留；海岸线锁定", fill=(75, 75, 75), font=small)
    area_names = {
        "yandu_area": "燕都", "dong_hebei_area": "冀东",
        "zhong_hebei_area": "冀中", "south_hebei_area": "冀南",
    }
    rows = []
    for area, source_ids in SOURCE_AREAS.items():
        for sid in source_ids:
            tid = SOURCE_TO_TARGET[sid]
            rows.append((tid, area_names[area]))
    for i, (pid, area) in enumerate(rows):
        col, row = i // 10, i % 10
        x, y = shown.width + 22 + col * 215, 100 + row * 50
        colour = target_colours[pid]
        draw.rectangle((x, y + 3, x + 24, y + 27), fill=colour, outline=(30, 30, 30))
        draw.text((x + 32, y), f"{NAMES[pid][1]} · {area}", fill=(25, 25, 25), font=body)
    draw.text((shown.width + 22, 640), "19省：燕都5、冀东4、冀中5、冀南5", fill=(55, 55, 55), font=small)
    draw.text((shown.width + 22, 670), "来源画布偏移：x−438，y−9", fill=(55, 55, 55), font=small)
    canvas.save(OUT / "workshop_north_zhili_transplant_annotated.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "pre_workshop_north_zhili_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)

    bitmap, original, source_mask, old_mask, changed_scope, target_colours, source_defs = build_geometry(backup)
    target_ids = sorted(set(SOURCE_TO_TARGET.values()))
    connectivity = {}
    for pid in target_ids:
        count = len(components(np.all(bitmap == target_colours[pid], axis=2)))
        if count != 1:
            connectivity[pid] = count
    if connectivity:
        raise ValueError(f"Disconnected imported provinces: {connectivity}")

    Image.fromarray(bitmap).save(MAP / "provinces.bmp", format="BMP")
    update_definition(target_colours, source_defs)
    update_areas()
    update_lists()
    update_histories()
    update_positions(bitmap, target_colours)
    update_localisation()
    render_preview(bitmap, source_mask, target_colours)

    changed = np.any(bitmap != original, axis=2)
    outside = int(np.count_nonzero(changed & ~changed_scope))
    print(f"WORKSHOP_HEBEI_TRANSPLANTED:19; CHANGED:{int(changed.sum())}; OUTSIDE:{outside}")


if __name__ == "__main__":
    main()
