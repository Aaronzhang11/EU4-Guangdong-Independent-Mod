#!/usr/bin/env python3
"""Apply the reviewed workshop Shaanxi and four-province Chang'an area."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import apply_workshop_hebei_transplant as common
import render_workshop_shaanxi_draft as preview


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/shaanxi"
DRAFT = OUT / "shaanxi_changan_4_full_draft.bmp"

PROVINCES = {
    700: ("Changan", "长安", (74, 157, 215), "cloth", 7, 6, 5),
    5283: ("Xianyang", "咸阳", (210, 73, 128), "grain", 5, 4, 4),
    5284: ("Haojing", "镐京", (226, 157, 42), "grain", 5, 4, 4),
    5285: ("Lantian", "蓝田", (78, 179, 91), "iron", 3, 3, 3),
    5271: ("Binzhou", "彬州", (195, 253, 181), "grain", 3, 3, 3),
    5269: ("Tongzhou", "同州", (163, 189, 226), "grain", 4, 4, 4),
    5270: ("Huazhou", "华州", (181, 232, 133), "iron", 3, 3, 3),
    5268: ("Fuzhou", "富州", (181, 205, 7), "wool", 3, 2, 3),
    5267: ("Suide", "绥德", (142, 230, 68), "wool", 3, 3, 4),
    5266: ("Yulin", "榆林", (172, 177, 84), "livestock", 3, 3, 4),
    5265: ("Jiazhou", "葭州", (137, 77, 206), "grain", 3, 2, 3),
    5275: ("Ningqiang", "宁羌", (121, 0, 220), "iron", 3, 3, 3),
    5274: ("Xingan", "兴安", (223, 187, 206), "grain", 3, 3, 3),
    5273: ("Jinzhou", "金州", (20, 114, 228), "iron", 3, 3, 3),
    5272: ("Shangzhou", "商州", (180, 185, 165), "iron", 3, 3, 3),
    5276: ("Qinan", "秦安", (168, 43, 246), "grain", 3, 3, 3),
    5277: ("Guyuan", "固原", (131, 142, 25), "livestock", 3, 3, 4),
    5278: ("Jingning", "静宁", (52, 141, 13), "wool", 3, 3, 3),
}
OBSOLETE_PROVINCES = {5282}

EXISTING = {
    4198: ("Fengxiang", "凤翔"), 2179: ("Yanan", "延安"),
    689: ("Hanzhong", "汉中"), 2181: ("Pingliang", "平凉"),
}

MOUNTAINS = {
    5183: ("Qinling Mountains", "秦岭", (33, 242, 192)),
    5187: ("Long Mountains", "陇山", (247, 111, 255)),
}
OBSOLETE_MOUNTAINS = {5175, 5176, 5180, 5182}

AREA_BLOCKS = {
    "changan_area": [700, 5283, 5284, 5285],
    "shaanxi_area": [4198, 5271, 5269, 5270],
    "bei_shaanxi_area": [2179, 5268, 5267, 5266, 5265],
    "nan_shaanxi_area": [689, 5275, 5274, 5273, 5272],
    "xi_shaanxi_area": [2181, 5276, 5277, 5278],
}


def colour_components(bitmap, colour):
    return common.components(np.all(bitmap == colour, axis=2))


def clean_neighbour_fragments(base, proposed, import_colours):
    changed = np.any(base != proposed, axis=2)
    affected = np.unique(np.concatenate([base[changed], proposed[changed]]), axis=0)
    import_colours = {tuple(c) for c in import_colours}
    cleaned = proposed.copy()
    cleanup = np.zeros(changed.shape, dtype=bool)
    for _ in range(3):
        progress = False
        for colour_array in affected:
            colour = tuple(colour_array)
            if colour in import_colours:
                continue
            before = colour_components(base, colour)
            after = colour_components(cleaned, colour)
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
                        if 0 <= nx < cleaned.shape[1] and 0 <= ny < cleaned.shape[0]:
                            candidate = tuple(cleaned[ny, nx])
                            if candidate != colour:
                                neighbours.append(candidate)
                if not neighbours:
                    continue
                replacement = Counter(neighbours).most_common(1)[0][0]
                for x, y in comp:
                    cleaned[y, x] = replacement
                    cleanup[y, x] = True
                progress = True
        if not progress:
            break
    return cleaned, cleanup


def fill_unlabelled(owner, unlabelled):
    """Extend existing imported jurisdictions into the few uncovered pixels."""
    from collections import deque
    queue = deque()
    seen = np.zeros(unlabelled.shape, dtype=bool)
    height, width = unlabelled.shape
    for y, x in zip(*np.nonzero(unlabelled)):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not unlabelled[ny, nx] and owner[ny, nx] >= 0:
                owner[y, x] = owner[ny, nx]
                seen[y, x] = True
                queue.append((x, y))
                break
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and unlabelled[ny, nx]
                    and not seen[ny, nx]):
                owner[ny, nx] = owner[y, x]
                seen[ny, nx] = True
                queue.append((nx, ny))
    if np.any(unlabelled & ~seen):
        raise ValueError("Uncovered Shaanxi pixels could not be assigned")
    return owner


def grow_edge_core(mask, seed, size):
    from collections import deque
    sx, sy = seed
    chosen = np.zeros(mask.shape, dtype=bool)
    queue, seen = deque([(sx, sy)]), {(sx, sy)}
    while queue and int(chosen.sum()) < size:
        x, y = queue.popleft()
        if not mask[y, x]:
            continue
        chosen[y, x] = True
        neighbours = []
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0] and (nx, ny) not in seen:
                seen.add((nx, ny))
                if mask[ny, nx]:
                    neighbours.append((nx, ny))
        neighbours.sort(key=lambda p: (p[0], abs(p[1] - sy)))
        queue.extend(neighbours)
    if int(chosen.sum()) != size:
        raise ValueError("Could not carve Jingzhou")
    return chosen


def apply_geometry(backup):
    base = np.asarray(Image.open(backup).convert("RGB"))
    draft = np.asarray(Image.open(DRAFT).convert("RGB"))
    definitions, _ = common.read_definitions(MAP / "definition.csv")
    allowed = np.all(base == (100, 152, 0), axis=2)  # old province 700 colour
    for pid in (689, 2179, 4198, 2181):
        allowed |= np.all(base == definitions[pid][0], axis=2)

    inhabited = {pid: data[2] for pid, data in PROVINCES.items()}
    inhabited.update({pid: definitions[pid][0] for pid in EXISTING})
    mountain_colours = {pid: data[2] for pid, data in MOUNTAINS.items()}
    owner = np.full(allowed.shape, -1, dtype=np.int32)
    pids = list(inhabited)
    for index, pid in enumerate(pids):
        owner[allowed & np.all(draft == inhabited[pid], axis=2)] = index
    mountain_mask = np.zeros(allowed.shape, dtype=bool)
    for colour in mountain_colours.values():
        mountain_mask |= allowed & np.all(draft == colour, axis=2)
    owner[mountain_mask] = -2

    unlabelled = allowed & (owner == -1)
    owner = fill_unlabelled(owner, unlabelled)
    proposed = base.copy()
    for index, pid in enumerate(pids):
        proposed[owner == index] = inhabited[pid]
    for pid, colour in mountain_colours.items():
        proposed[allowed & np.all(draft == colour, axis=2)] = colour

    # Jingzhou lies just west of the locked outer boundary in the source mod.
    # Carve a compact western border province from the oversized Qin'an body.
    donor_colour = inhabited[5276]
    donor = np.all(proposed == donor_colour, axis=2) & allowed
    yy, xx = np.nonzero(donor)
    nearest = int(np.argmin((xx - 4437) ** 2 + (yy - 790) ** 2))
    jingzhou = grow_edge_core(donor, (int(xx[nearest]), int(yy[nearest])), 140)
    proposed[jingzhou] = inhabited[5277]

    # Remove detached imported fragments created by clipping; each fragment is
    # absorbed by the province sharing most of its boundary.
    import_colours = set(map(tuple, inhabited.values()))
    for pid, colour in inhabited.items():
        comps = colour_components(proposed, colour)
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
                    if 0 <= nx < proposed.shape[1] and 0 <= ny < proposed.shape[0]:
                        candidate = tuple(proposed[ny, nx])
                        if candidate != tuple(colour):
                            neighbours.append(candidate)
            if not neighbours:
                raise ValueError(f"Detached imported fragment: {pid}")
            replacement = Counter(neighbours).most_common(1)[0][0]
            for x, y in comp:
                proposed[y, x] = replacement

    cleanup = np.zeros(allowed.shape, dtype=bool)
    Image.fromarray(proposed).save(MAP / "provinces.bmp", format="BMP")
    return proposed, base, cleanup


def update_definitions():
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    records = {pid: (data[2], data[0]) for pid, data in PROVINCES.items()}
    records.update({pid: (data[2], data[0]) for pid, data in MOUNTAINS.items()})
    output, seen = [], set()
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in (OBSOLETE_MOUNTAINS | OBSOLETE_PROVINCES):
            continue
        if fields and fields[0].isdigit() and int(fields[0]) in records:
            pid = int(fields[0])
            colour, name = records[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid in sorted(records):
        if pid not in seen:
            colour, name = records[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_areas_regions():
    path = MAP / "area.txt"
    text = path.read_text()
    for key, ids in AREA_BLOCKS.items():
        block = f"{key} = {{\n    {' '.join(map(str, ids))}\n}}"
        text = common.replace_block(text, key, block)
    text = common.replace_block(text, "gansu_area", "gansu_area = {\n    698 699 2180 2183\n}")
    path.write_text(text)

    path = MAP / "region.txt"
    text = path.read_text()
    for area in ("changan_area", "bei_shaanxi_area", "nan_shaanxi_area", "xi_shaanxi_area"):
        if re.search(rf"(?m)^\s*{area}\s*$", text) is None:
            text = text.replace("        shaanxi_area\n", f"        shaanxi_area\n        {area}\n", 1)
    path.write_text(text)


def update_map_lists():
    inhabited = " ".join(map(str, sorted(pid for pid in PROVINCES if pid != 700)))
    mountains = " ".join(map(str, sorted(MOUNTAINS)))
    path = MAP / "continent.txt"
    text = path.read_text()
    marker = "        5211 5212 5213 5218 5219 5220 5221 5222 5223 # Workshop North Zhili"
    text = re.sub(r"(?m)^\s*.*# Shaanxi refinement\n?", "", text)
    text = re.sub(r"(?m)^\s*.*# Shaanxi impassables\n?", "", text)
    text = text.replace(marker, marker + f"\n        {inhabited} # Shaanxi refinement\n        {mountains} # Shaanxi impassables", 1)
    path.write_text(text)

    path = MOD / "common/tradenodes/00_tradenodes.txt"
    text = path.read_text()
    text = re.sub(r"(?m)^\s*.*# Shaanxi and Changan refinement\n?", "", text)
    marker = "        4967 5045 5046 5047 5048 5049 5050 5051 5052 5053 5054 5055 # B14 Henan refinement"
    text = text.replace(marker, marker + f"\n        {inhabited} # Shaanxi and Changan refinement", 1)
    path.write_text(text)

    path = MAP / "default.map"
    text = path.read_text()
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5286", text)
    path.write_text(text)

    path = MAP / "climate.txt"
    text = path.read_text()
    text = re.sub(r"(?m)^\s*.*# Shaanxi mountain barriers\n?", "", text)
    text = text.replace("    5029 # B08 Taiwan central range",
                        f"    5029 # B08 Taiwan central range\n    {mountains} # Shaanxi mountain barriers", 1)
    path.write_text(text)


def history_text(pid, data):
    name, _, _, goods, tax, production, manpower = data
    return f'''# {pid} - {name}\n\nowner = MNG\ncontroller = MNG\nadd_core = MNG\n'''+ \
        f'''culture = zhili\nreligion = confucianism\ncapital = "{name}"\ntrade_goods = {goods}\n''' + \
        f'''base_tax = {tax}\nbase_production = {production}\nbase_manpower = {manpower}\n''' + \
        '''is_city = yes\ndiscovered_by = chinese\ndiscovered_by = nomad_group\n'''


def update_histories():
    directory = MOD / "history/provinces"
    for pid in OBSOLETE_PROVINCES:
        for old in directory.glob(f"{pid} - *.txt"):
            old.unlink()
    for pid, data in PROVINCES.items():
        for old in directory.glob(f"{pid} - *.txt"):
            old.unlink()
        (directory / f"{pid} - {data[0]}.txt").write_text(history_text(pid, data))


def update_positions(bitmap):
    path = MAP / "positions.txt"
    text = path.read_text(encoding="latin-1")
    definitions, _ = common.read_definitions(MAP / "definition.csv")
    for pid in OBSOLETE_PROVINCES:
        text = re.sub(rf"(?ms)^#.*\n{pid}=\{{.*?^\}}\s*", "", text)
    records = {pid: (data[0], data[2]) for pid, data in PROVINCES.items()}
    records.update({pid: (name, definitions[pid][0]) for pid, (name, _) in EXISTING.items()})
    for pid, (name, colour) in records.items():
        yy, xx = np.nonzero(np.all(bitmap == colour, axis=2))
        if not len(xx):
            raise ValueError(f"No pixels for {pid} {name}")
        x, y = float(np.median(xx)), float(bitmap.shape[0] - np.median(yy))
        block = f'''#{name} - Shaanxi refinement\n{pid}={{\n    position={{\n        {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} {x:.3f} {y:.3f} 0.000 0.000\n    }}\n    rotation={{\n        0.000 0.000 0.000 0.000 0.000 0.000 0.000\n    }}\n    height={{\n        0.000 0.000 1.000 0.000 0.000 0.000 0.000\n    }}\n}}'''
        text = common.replace_block(text, str(pid), block)
    path.write_text(text, encoding="latin-1")


def update_localisation():
    path = MOD / "localisation_source/gdd_b25_shaanxi_refinement_utf8.txt"
    lines = ["l_english:"]
    for pid, data in sorted(PROVINCES.items()):
        chinese = data[1]
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    for pid, (_, chinese) in sorted(EXISTING.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    for pid, (_, chinese, _) in sorted(MOUNTAINS.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    lines += [
        ' changan_area:0 "长安"', ' changan_area_name:0 "长安"', ' changan_area_adj:0 "长安"',
        ' shaanxi_area:0 "关中"', ' shaanxi_area_name:0 "关中"', ' shaanxi_area_adj:0 "关中"',
        ' bei_shaanxi_area:0 "陕北"', ' bei_shaanxi_area_name:0 "陕北"', ' bei_shaanxi_area_adj:0 "陕北"',
        ' nan_shaanxi_area:0 "陕南"', ' nan_shaanxi_area_name:0 "陕南"', ' nan_shaanxi_area_adj:0 "陕南"',
        ' xi_shaanxi_area:0 "陇东"', ' xi_shaanxi_area_name:0 "陇东"', ' xi_shaanxi_area_adj:0 "陇东"',
    ]
    path.write_text("\n".join(lines) + "\n")
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(path, MOD / "localisation/gdd_b25_shaanxi_map_l_english.yml")


def render_review(bitmap, base):
    changed = np.any(bitmap != base, axis=2)
    yy, xx = np.nonzero(changed)
    pad = 8
    x0, x1 = int(xx.min()) - pad, int(xx.max()) + pad
    y0, y1 = int(yy.min()) - pad, int(yy.max()) + pad
    crop = bitmap[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop).save(OUT / "shaanxi_refinement_formal_draft.bmp")
    review = crop.copy()
    for pid, (_, _, colour) in MOUNTAINS.items():
        grey = (72, 72, 72) if pid == 5183 else (125, 125, 125)
        review[np.all(crop == colour, axis=2)] = grey
    scale = 6
    shown = Image.fromarray(review).resize(
        (review.shape[1] * scale, review.shape[0] * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (shown.width + 420, max(shown.height, 850)), "white")
    canvas.paste(shown, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    title = ImageFont.truetype(font_path, 27)
    body = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 15)
    lx = shown.width + 22
    draw.text((lx, 20), "陕西正式细化", fill=(20, 20, 20), font=title)
    draw.text((lx, 62), "22省；外轮廓锁定；长城未加入", fill=(70, 70, 70), font=small)
    y = 110
    for area, ids in AREA_BLOCKS.items():
        label = {"changan_area": "长安", "shaanxi_area": "关中", "bei_shaanxi_area": "陕北",
                 "nan_shaanxi_area": "陕南", "xi_shaanxi_area": "陇东"}[area]
        draw.text((lx, y), f"{label}：{len(ids)}省", fill=(25, 25, 25), font=body)
        y += 42
    draw.rectangle((lx, y + 8, lx + 26, y + 34), fill=(72, 72, 72), outline=(30, 30, 30))
    draw.text((lx + 36, y + 5), "秦岭（不可通行）", fill=(25, 25, 25), font=body)
    y += 48
    draw.rectangle((lx, y + 8, lx + 26, y + 34), fill=(125, 125, 125), outline=(30, 30, 30))
    draw.text((lx + 36, y + 5), "陇山（不可通行）", fill=(25, 25, 25), font=body)
    draw.text((lx, y + 75), "长安：咸阳、镐京、长安、蓝田", fill=(55, 55, 55), font=small)
    draw.text((lx, y + 108), "未覆盖云南、四川等既有细化省", fill=(55, 55, 55), font=small)
    canvas.save(OUT / "shaanxi_refinement_formal_annotated.png")


def main():
    backup = OUT / "pre_shaanxi_refinement_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    bitmap, base, cleanup = apply_geometry(backup)
    update_definitions()
    update_areas_regions()
    update_map_lists()
    update_histories()
    update_positions(bitmap)
    update_localisation()
    render_review(bitmap, base)
    changed = np.any(bitmap != base, axis=2)
    print(f"SHAANXI_REFINEMENT_APPLIED:22; MOUNTAINS:{len(MOUNTAINS)}; CHANGED:{int(changed.sum())}; CLEANUP:{int(cleanup.sum())}")


if __name__ == "__main__":
    main()
