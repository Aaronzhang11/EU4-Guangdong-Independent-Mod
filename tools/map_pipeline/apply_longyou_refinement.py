#!/usr/bin/env python3
"""Apply the reviewed B34 Qinzhou–Gongchang/Longyou refinement transactionally."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/longyou"
DRAFT = PLAN / "tianshui_gongchang_geojson_7_full_draft.bmp"
BACKUP_DIR = PLAN / "pre_b34"
MARKER = "B34 Longyou refinement"

PROVINCES = {
    2180: ((138, 152, 194), "Qinzhou Gansu"),
    5291: ((224, 208, 220), "Gongchang"),
    5305: ((47, 187, 209), "Qingshui Gansu"),
    5306: ((207, 109, 43), "Tongwei"),
}
NEW_IDS = (5305, 5306)
AREAS = {
    "longyou_area": (2181, 5276, 5278, 5305),
    "xi_shaanxi_area": (2180, 5277, 5291, 5306),
    "longnan_area": (2183, 5289, 5290),
}


def read(path: Path) -> str:
    return path.read_text(encoding="cp1252")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="cp1252")


def backup_once(path: Path) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / path.relative_to(MOD)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def block_bounds(text: str, name: str) -> tuple[int, int] | None:
    # Keep newlines out of the leading whitespace match.  Using ``\s*`` here
    # gradually consumed neighbouring blank lines on repeated applications.
    match = re.search(rf"(?m)^[ \t]*{re.escape(name)}[ \t]*=[ \t]*\{{", text)
    if not match:
        return None
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    raise ValueError(f"Unclosed block: {name}")


def replace_block(text: str, name: str, replacement: str) -> str:
    bounds = block_bounds(text, name)
    if bounds is None:
        return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def append_ids(text: str, block_name: str, ids: tuple[int, ...], marker: str) -> str:
    bounds = block_bounds(text, block_name)
    if bounds is None:
        raise ValueError(f"Missing block: {block_name}")
    block = text[bounds[0]:bounds[1]]
    block = re.sub(rf"(?m)^\s*.*# {re.escape(marker)}\n?", "", block)
    close = block.rfind("}")
    block = block[:close].rstrip() + f"\n    {' '.join(map(str, ids))} # {marker}\n" + block[close:]
    return text[:bounds[0]] + block + text[bounds[1]:]


def append_nested_ids(text: str, top: str, nested: str, ids: tuple[int, ...], marker: str) -> str:
    bounds = block_bounds(text, top)
    if bounds is None:
        raise ValueError(f"Missing block: {top}")
    updated = append_ids(text[bounds[0]:bounds[1]], nested, ids, marker)
    return text[:bounds[0]] + updated + text[bounds[1]:]


def definitions() -> dict[int, tuple[int, int, int]]:
    result = {}
    for line in read(MAP / "definition.csv").splitlines():
        fields = line.split(";")
        if fields[0].isdigit():
            result[int(fields[0])] = tuple(map(int, fields[1:4]))
    return result


def safe_point(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        raise ValueError("Cannot place position in empty province")
    target_x, target_y = float(xs.mean()), float(ys.mean())
    border = np.zeros_like(mask)
    border |= mask & ~np.roll(mask, 1, 0)
    border |= mask & ~np.roll(mask, -1, 0)
    border |= mask & ~np.roll(mask, 1, 1)
    border |= mask & ~np.roll(mask, -1, 1)
    candidates = np.column_stack(np.where(mask & ~border))
    if not len(candidates):
        candidates = np.column_stack((ys, xs))
    distances = (candidates[:, 1] - target_x) ** 2 + (candidates[:, 0] - target_y) ** 2
    y, x = candidates[int(np.argmin(distances))]
    return int(x), int(mask.shape[0] - y)


def apply_geometry() -> tuple[np.ndarray, dict[int, tuple[int, int]], dict[str, int]]:
    formal_path = MAP / "provinces.bmp"
    backup_once(formal_path)
    current = np.asarray(Image.open(formal_path).convert("RGB"))
    draft = np.asarray(Image.open(DRAFT).convert("RGB"))
    if current.shape != draft.shape:
        raise ValueError("Reviewed draft and formal map dimensions differ")

    defs = definitions()
    old_colours = {defs[2180], defs[5291]}
    editable_colours = old_colours | {PROVINCES[5305][0], PROVINCES[5306][0]}
    editable = np.zeros(current.shape[:2], dtype=bool)
    for colour in editable_colours:
        editable |= np.all(current == colour, axis=2)

    allowed_draft = np.zeros(current.shape[:2], dtype=bool)
    for colour, _name in PROVINCES.values():
        allowed_draft |= np.all(draft == colour, axis=2)
    if np.any(editable & ~allowed_draft):
        raise ValueError("Reviewed draft does not fully cover the editable parent mask")

    output = current.copy()
    output[editable] = draft[editable]
    Image.fromarray(output, mode="RGB").save(formal_path, format="BMP")

    centres = {}
    counts = {}
    for province_id, (colour, _name) in PROVINCES.items():
        mask = np.all(output == colour, axis=2)
        centres[province_id] = safe_point(mask)
        counts[str(province_id)] = int(mask.sum())
    return output, centres, counts


def update_definition() -> None:
    path = MAP / "definition.csv"
    backup_once(path)
    lines = read(path).splitlines()
    records = {5305: PROVINCES[5305], 5306: PROVINCES[5306]}
    output, seen = [], set()
    for line in lines:
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in records:
            pid = int(head); colour, name = records[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(pid)
        else:
            output.append(line)
    for pid in NEW_IDS:
        if pid not in seen:
            colour, name = records[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    write(path, "\n".join(output) + "\n")


def update_areas_and_region() -> None:
    path = MAP / "area.txt"; backup_once(path); text = read(path)
    for area, ids in AREAS.items():
        text = replace_block(text, area, f"{area} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}")
    write(path, text)

    path = MAP / "region.txt"; backup_once(path); text = read(path)
    bounds = block_bounds(text, "north_china_region")
    if bounds is None:
        raise ValueError("Missing north_china_region")
    block = text[bounds[0]:bounds[1]]
    if not re.search(r"(?m)^\s*longyou_area\s*$", block):
        block = block.replace("        longnan_area\n", "        longnan_area\n        longyou_area\n", 1)
    write(path, text[:bounds[0]] + block + text[bounds[1]:])


def set_initial(path: Path, values: dict[str, str]) -> None:
    backup_once(path)
    text = path.read_text(encoding="utf-8-sig")
    for key, value in values.items():
        pattern = rf"(?m)^(\s*{re.escape(key)}\s*=\s*).*$"
        if not re.search(pattern, text):
            raise ValueError(f"Missing {key} in {path.name}")
        text = re.sub(pattern, rf"\g<1>{value}", text, count=1)
    path.write_text(text, encoding="utf-8")


def history_text(pid: int, name: str, goods: str, dev: tuple[int, int, int]) -> str:
    tax, production, manpower = dev
    return f'''# {pid} - {name}\n\nowner = MNG\ncontroller = MNG\nadd_core = MNG\nculture = xibei\nreligion = confucianism\ncapital = "{name}"\ntrade_goods = {goods}\nbase_tax = {tax}\nbase_production = {production}\nbase_manpower = {manpower}\nis_city = yes\ndiscovered_by = chinese\ndiscovered_by = nomad_group\n'''


def update_histories() -> None:
    directory = MOD / "history/provinces"
    set_initial(directory / "2180 - Qinzhou Gansu.txt", {"base_tax":"3", "base_production":"3", "base_manpower":"2"})
    set_initial(directory / "5291 - Gongchang.txt", {"base_tax":"2", "base_production":"2", "base_manpower":"1"})
    new = {
        5305: ("Qingshui Gansu", "livestock", (1, 1, 1)),
        5306: ("Tongwei", "wool", (1, 1, 1)),
    }
    for pid, (name, goods, dev) in new.items():
        path = directory / f"{pid} - {name}.txt"
        if path.exists(): backup_once(path)
        for other in directory.glob(f"{pid} - *.txt"):
            if other != path: other.unlink()
        path.write_text(history_text(pid, name, goods, dev), encoding="utf-8")


def position_block(pid: int, name: str, point: tuple[int, int]) -> str:
    x, y = point
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f'''#{name} - {MARKER}\n{pid}={{\n    position={{\n        {points}\n    }}\n    rotation={{\n        0.000 0.000 0.000 0.000 0.000 0.000 0.000\n    }}\n    height={{\n        0.000 0.000 1.000 0.000 0.000 0.000 0.000\n    }}\n}}'''


def update_positions(centres: dict[int, tuple[int, int]]) -> None:
    path = MAP / "positions.txt"; backup_once(path); text = read(path)
    text = re.sub(rf"(?m)^#.* - {re.escape(MARKER)}\n", "", text)
    for pid, (_colour, name) in PROVINCES.items():
        text = replace_block(text, str(pid), position_block(pid, name, centres[pid]))
    write(path, text)


def update_memberships() -> None:
    path = MAP / "continent.txt"; backup_once(path)
    write(path, append_ids(read(path), "asia", NEW_IDS, MARKER))

    path = MAP / "climate.txt"; backup_once(path)
    write(path, append_ids(read(path), "mild_winter", NEW_IDS, MARKER))

    path = MAP / "terrain.txt"; backup_once(path); text = read(path)
    text = append_nested_ids(text, "hills", "terrain_override", NEW_IDS, MARKER + " hills")
    write(path, text)

    path = MOD / "common/tradenodes/00_tradenodes.txt"; backup_once(path)
    write(path, append_nested_ids(read(path), "xian", "members", NEW_IDS, MARKER + " Xian"))

    path = MOD / "common/trade_companies/00_trade_companies.txt"; backup_once(path)
    write(path, append_nested_ids(read(path), "trade_company_xian", "provinces", NEW_IDS, MARKER + " Xian"))

    path = MAP / "default.map"; backup_once(path); text = read(path)
    current = int(re.search(r"(?m)^max_provinces\s*=\s*(\d+)", text).group(1))
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", f"max_provinces = {max(current, 5307)}", text)
    write(path, text)


def update_localisation() -> None:
    source = MOD / "localisation_source/gdd_b34_longyou_map_readable_utf8.txt"
    target = MOD / "localisation/gdd_b34_longyou_map_l_english.yml"
    source.write_text('''l_english:\n PROV5305:0 "清水"\n PROV_ADJ5305:0 "清水"\n PROV5306:0 "通渭"\n PROV_ADJ5306:0 "通渭"\n longyou_area:0 "陇右"\n longyou_area_name:0 "巩昌"\n longyou_area_adj:0 "陇右"\n''', encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file
    encode_file(source, target)
    verify_file(source, target)


def write_outputs(bitmap: np.ndarray, counts: dict[str, int]) -> None:
    colours = [value[0] for value in PROVINCES.values()]
    mask = np.zeros(bitmap.shape[:2], dtype=bool)
    for colour in colours: mask |= np.all(bitmap == colour, axis=2)
    ys, xs = np.where(mask); pad = 10
    x0, x1 = max(0, int(xs.min())-pad), min(bitmap.shape[1], int(xs.max())+pad+1)
    y0, y1 = max(0, int(ys.min())-pad), min(bitmap.shape[0], int(ys.max())+pad+1)
    crop = Image.fromarray(bitmap[y0:y1, x0:x1], mode="RGB")
    crop.save(PLAN / "longyou_formal_crop.bmp", format="BMP")
    preview = crop.resize((crop.width*7, crop.height*7), Image.Resampling.NEAREST)
    preview_path = ROOT / "docs/map/previews/B34_longyou_formal.png"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(preview_path)
    report = {
        "formal_map_changed": True,
        "provinces": counts,
        "areas": {key:list(value) for key,value in AREAS.items()},
        "development": {"2180":[3,3,2],"5305":[1,1,1],"5291":[2,2,1],"5306":[1,1,1]},
        "trade_node": {"5305":"xian","5306":"xian"},
        "trade_centers_added": 0,
    }
    (PLAN / "formal_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def main() -> None:
    bitmap, centres, counts = apply_geometry()
    update_definition()
    update_areas_and_region()
    update_histories()
    update_positions(centres)
    update_memberships()
    update_localisation()
    write_outputs(bitmap, counts)
    print("B34_LONGYOU_REFINEMENT_APPLIED")


if __name__ == "__main__":
    main()
