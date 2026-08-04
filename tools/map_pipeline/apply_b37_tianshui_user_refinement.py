#!/usr/bin/env python3
"""Register the reviewed user-drawn B37 Tianshui five-province geometry."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from apply_longyou_refinement import append_ids, append_nested_ids, block_bounds, replace_block, safe_point

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/tianshui_user_edit_review"
BACKUP = PLAN / "pre_b37/provinces.bmp"
MARKER = "B37 Tianshui user refinement"

PROVINCES = {
    2180: ((138, 152, 194), "Tianshui", "天水"),
    5291: ((224, 208, 220), "Minzhou", "岷州"),
    5307: ((171, 163, 193), "Lintao", "临洮"),
    5308: ((219, 0, 220), "Gongchang", "巩昌"),
    5309: ((0, 211, 220), "Wudu", "武都"),
}
NEW_IDS = (5307, 5308, 5309)
AREAS = {
    "longyou_area": (2180, 5291, 5307, 5308, 5309),
    "xi_shaanxi_area": (2181, 5276, 5277, 5278, 5305, 5306),
}


def read(path: Path) -> str:
    return path.read_text(encoding="cp1252")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="cp1252")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_definition() -> None:
    path = MAP / "definition.csv"
    wanted = {
        2180: (138, 152, 194, "Tianshui"),
        5290: (141, 71, 29, "Dangchang"),
        5291: (224, 208, 220, "Minzhou"),
        5307: (171, 163, 193, "Lintao"),
        5308: (219, 0, 220, "Gongchang"),
        5309: (0, 211, 220, "Wudu"),
    }
    out, seen = [], set()
    for line in read(path).splitlines():
        head = line.split(";", 1)[0]
        if head.isdigit() and int(head) in wanted:
            pid = int(head); r, g, b, name = wanted[pid]
            out.append(f"{pid};{r};{g};{b};{name};x"); seen.add(pid)
        else:
            out.append(line)
    for pid in (5307, 5308, 5309):
        if pid not in seen:
            r, g, b, name = wanted[pid]
            out.append(f"{pid};{r};{g};{b};{name};x")
    write(path, "\n".join(out) + "\n")


def update_area() -> None:
    path = MAP / "area.txt"; text = read(path)
    for name, ids in AREAS.items():
        text = replace_block(text, name, f"{name} = {{ # {MARKER}\n    {' '.join(map(str, ids))}\n}}")
    write(path, text)


def history_text(pid: int, name: str, goods: str, dev: tuple[int, int, int], culture="xibei", religion="confucianism") -> str:
    return f'''# {pid} - {name}\n\nowner = MNG\ncontroller = MNG\nadd_core = MNG\nculture = {culture}\nreligion = {religion}\ncapital = "{name}"\ntrade_goods = {goods}\nbase_tax = {dev[0]}\nbase_production = {dev[1]}\nbase_manpower = {dev[2]}\nis_city = yes\ndiscovered_by = chinese\ndiscovered_by = nomad_group\n'''


def set_history(pid: int, filename: str, text: str) -> None:
    directory = MOD / "history/provinces"
    target = directory / filename
    for path in directory.glob(f"{pid} - *.txt"):
        if path != target:
            path.unlink()
    target.write_text(text, encoding="utf-8")


def update_histories() -> None:
    set_history(2180, "2180 - Tianshui.txt", history_text(2180, "Tianshui", "grain", (3, 3, 2)))
    set_history(5290, "5290 - Dangchang.txt", history_text(5290, "Dangchang", "livestock", (2, 2, 2), "tibetan", "vajrayana"))
    set_history(5291, "5291 - Minzhou.txt", history_text(5291, "Minzhou", "grain", (2, 2, 1)))
    set_history(5307, "5307 - Lintao.txt", history_text(5307, "Lintao", "livestock", (1, 1, 1)))
    set_history(5308, "5308 - Gongchang.txt", history_text(5308, "Gongchang", "grain", (1, 1, 1)))
    set_history(5309, "5309 - Wudu.txt", history_text(5309, "Wudu", "livestock", (1, 1, 1)))


def position_block(pid: int, name: str, point: tuple[int, int]) -> str:
    x, y = point
    points = " ".join([f"{x:.3f} {y:.3f}"] * 6 + ["0.000 0.000"])
    return f'''#{name} - {MARKER}\n{pid}={{\n    position={{\n        {points}\n    }}\n    rotation={{\n        0.000 0.000 0.000 0.000 0.000 0.000 0.000\n    }}\n    height={{\n        0.000 0.000 1.000 0.000 0.000 0.000 0.000\n    }}\n}}'''


def update_positions(bitmap: np.ndarray) -> None:
    path = MAP / "positions.txt"; text = read(path)
    text = re.sub(rf"(?m)^#.* - {re.escape(MARKER)}\n", "", text)
    for pid, (colour, name, _zh) in PROVINCES.items():
        point = safe_point(np.all(bitmap == colour, axis=2))
        text = replace_block(text, str(pid), position_block(pid, name, point))
    write(path, text)


def update_memberships() -> None:
    for filename, block in (("continent.txt", "asia"), ("climate.txt", "mild_winter")):
        path = MAP / filename; write(path, append_ids(read(path), block, NEW_IDS, MARKER))
    path = MAP / "terrain.txt"
    write(path, append_nested_ids(read(path), "hills", "terrain_override", NEW_IDS, MARKER + " hills"))
    path = MOD / "common/tradenodes/00_tradenodes.txt"
    write(path, append_nested_ids(read(path), "xian", "members", NEW_IDS, MARKER + " Xian"))
    path = MOD / "common/trade_companies/00_trade_companies.txt"
    write(path, append_nested_ids(read(path), "trade_company_xian", "provinces", NEW_IDS, MARKER + " Xian"))
    path = MAP / "default.map"; text = read(path)
    text = re.sub(r"(?m)^max_provinces\s*=\s*\d+", "max_provinces = 5310", text)
    write(path, text)


def replace_loc(text: str, key: str, value: str) -> str:
    pattern = rf'(?m)^([ \t]*{re.escape(key)}:0[ \t]+)"[^"]*"'
    if not re.search(pattern, text):
        raise ValueError(f"Missing localisation key {key}")
    return re.sub(pattern, rf'\g<1>"{value}"', text, count=1)


def update_localisation() -> None:
    b26 = MOD / "localisation_source/gdd_b26_gansu_ningxia_map_readable_utf8.txt"
    text = b26.read_text(encoding="utf-8-sig")
    for pid, zh in ((2180, "天水"), (5290, "宕昌"), (5291, "岷州")):
        text = replace_loc(text, f"PROV{pid}", zh)
        text = replace_loc(text, f"PROV_ADJ{pid}", zh)
    b26.write_text(text, encoding="utf-8")
    source = MOD / "localisation_source/gdd_b37_tianshui_refinement_readable_utf8.txt"
    source.write_text('''l_english:\n PROV5307:0 "临洮"\n PROV_ADJ5307:0 "临洮"\n PROV5308:0 "巩昌"\n PROV_ADJ5308:0 "巩昌"\n PROV5309:0 "武都"\n PROV_ADJ5309:0 "武都"\n''', encoding="utf-8")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file
    pairs = [
        (b26, MOD / "localisation/gdd_b26_gansu_ningxia_map_l_english.yml"),
        (source, MOD / "localisation/gdd_b37_tianshui_refinement_l_english.yml"),
    ]
    for source_path, target in pairs:
        encode_file(source_path, target); verify_file(source_path, target)


def verify_bitmap(bitmap: np.ndarray) -> dict[str, int]:
    counts = {}
    for pid, (colour, _name, _zh) in PROVINCES.items():
        mask = np.all(bitmap == colour, axis=2)
        count = int(mask.sum())
        if not count:
            raise ValueError(f"Province {pid} has no pixels")
        counts[str(pid)] = count
    return counts


def write_preview(bitmap: np.ndarray, counts: dict[str, int]) -> None:
    mask = np.zeros(bitmap.shape[:2], dtype=bool)
    for colour, _name, _zh in PROVINCES.values(): mask |= np.all(bitmap == colour, axis=2)
    ys, xs = np.where(mask); pad = 10
    crop = bitmap[max(0,ys.min()-pad):ys.max()+pad+1, max(0,xs.min()-pad):xs.max()+pad+1]
    PLAN.mkdir(parents=True, exist_ok=True)
    Image.fromarray(crop).save(PLAN / "tianshui_five_formal_crop.bmp")
    preview = Image.fromarray(crop).resize((crop.shape[1]*7, crop.shape[0]*7), Image.Resampling.NEAREST)
    out = ROOT / "docs/map/previews/B37_tianshui_five_formal.png"; out.parent.mkdir(parents=True, exist_ok=True); preview.save(out)
    report = {"marker": MARKER, "bitmap_unchanged": True, "pixels": counts, "areas": {k:list(v) for k,v in AREAS.items()}, "new_development": 9, "trade_centers_added": 0}
    (PLAN / "b37_formal_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def main() -> None:
    bmp = MAP / "provinces.bmp"
    before = sha256(bmp)
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists(): shutil.copy2(bmp, BACKUP)
    bitmap = np.asarray(Image.open(bmp).convert("RGB"))
    counts = verify_bitmap(bitmap)
    update_definition(); update_area(); update_histories(); update_positions(bitmap)
    update_memberships(); update_localisation(); write_preview(bitmap, counts)
    if sha256(bmp) != before: raise ValueError("B37 must not rewrite the reviewed provinces.bmp")
    print(json.dumps({"status":"B37_APPLIED", "pixels":counts, "bmp_sha256":before}, ensure_ascii=False))


if __name__ == "__main__":
    main()
