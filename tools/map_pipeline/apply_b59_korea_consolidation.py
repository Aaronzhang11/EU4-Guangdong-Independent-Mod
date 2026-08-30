#!/usr/bin/env python3
"""Consolidate B58 Korea to 30 playable provinces and seven worldview areas.

This is the terminal correction after apply_b58_korea_refinement.py.  It keeps
29 peninsula provinces plus Jeju, retires nine B58-only playable IDs, and
replaces the five inherited Korean areas with four Zhuxia and three Samhan
areas.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
PLAN = ROOT / "planning/korea_consolidation_b59"
PROVINCES_BMP = MAP / "provinces.bmp"
BEFORE_PATCH = PLAN / "b59_before_patch.png"
AFTER_PATCH = PLAN / "b59_after_patch.png"
MANIFEST = PLAN / "b59_manifest.json"

MARKER = "GDD_B59_KOREA_30_PROVINCES_SEVEN_AREAS"
TRANSACTION_MARKERS = (
    "GDD_B58_KOREA_39_PROVINCES",
    "GDD_B59_KOREA_30_PROVINCES_SIX_AREAS",
    MARKER,
)
PARENT_TERRAIN = {
    735: "farmlands", 2745: "farmlands",
    733: "hills", 2694: "hills", 2742: "hills", 2744: "hills", 4229: "hills", 4231: "hills",
    732: "mountain", 734: "mountain", 2743: "mountain", 4232: "mountain",
    737: "grasslands", 1013: "grasslands", 1845: "grasslands", 4227: "grasslands", 4230: "grasslands",
    736: "highlands", 4228: "highlands",
}
CLIMATE_BLOCKS = ("mild_winter", "normal_winter", "severe_winter", "mild_monsoon", "normal_monsoon")


def manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = {int(pid): values for pid, values in data["development_targets"].items()}
    owner_by_id = {
        pid: owner
        for owner, ids in data["political_targets"].items()
        for pid in ids
    }
    disputed_cores_by_id = defaultdict(list)
    for tag, ids in data["disputed_core_targets"].items():
        for pid in ids:
            disputed_cores_by_id[pid].append(tag)
    for record in data["provinces"]:
        record["development"] = targets[record["id"]]
        record["owner"] = owner_by_id[record["id"]]
        record["culture"] = data["culture_targets"][record["owner"]]
        record["religion"] = data["religion_targets"][record["owner"]]
        record["disputed_cores"] = disputed_cores_by_id[record["id"]]
    return data


def block_bounds(text: str, name: str):
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        return None
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{": depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0: return match.start(), index + 1
    raise ValueError(f"Unclosed block {name}")


def delete_block(text: str, name: str) -> str:
    bounds = block_bounds(text, name)
    if bounds is None: return text
    return text[:bounds[0]] + text[bounds[1]:]


def replace_block(text: str, name: str, replacement: str) -> str:
    bounds = block_bounds(text, name)
    if bounds is None: return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[:bounds[0]] + replacement.rstrip() + text[bounds[1]:]


def remove_transaction_lines(text: str) -> str:
    markers = "(?:" + "|".join(re.escape(marker) for marker in TRANSACTION_MARKERS) + ")"
    return re.sub(rf"(?m)^.*{markers}.*\n?", "", text)


def append_to_block(text: str, name: str, ids: list[int], indent="    ") -> str:
    if not ids: return text
    bounds = block_bounds(text, name)
    if bounds is None: raise ValueError(f"Missing block {name}")
    block = text[bounds[0]:bounds[1]]; close = block.rfind("}")
    block = block[:close].rstrip() + f"\n{indent}{' '.join(map(str, sorted(ids)))} # {MARKER}\n" + block[close:]
    return text[:bounds[0]] + block + text[bounds[1]:]


def append_nested(text: str, outer: str, nested: str, ids: list[int]) -> str:
    if not ids: return text
    outer_bounds = block_bounds(text, outer)
    if outer_bounds is None: raise ValueError(f"Missing outer block {outer}")
    outer_block = text[outer_bounds[0]:outer_bounds[1]]
    nested_bounds = block_bounds(outer_block, nested)
    if nested_bounds is None: raise ValueError(f"Missing {nested} in {outer}")
    nested_block = outer_block[nested_bounds[0]:nested_bounds[1]]; close = nested_block.rfind("}")
    nested_block = nested_block[:close].rstrip() + f"\n        {' '.join(map(str, sorted(ids)))} # {MARKER}\n    " + nested_block[close:]
    outer_block = outer_block[:nested_bounds[0]] + nested_block + outer_block[nested_bounds[1]:]
    return text[:outer_bounds[0]] + outer_block + text[outer_bounds[1]:]


def rgb(path: Path):
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8, copy=True)


def apply_patch(data):
    current = rgb(PROVINCES_BMP)
    before = np.asarray(Image.open(BEFORE_PATCH).convert("RGBA")); after = np.asarray(Image.open(AFTER_PATCH).convert("RGBA"))
    x0, y0, x1, y1 = data["patch_box"]; mask = before[:, :, 3] > 0
    target = current[y0:y1, x0:x1]
    compatible = np.all(target == before[:, :, :3], axis=2) | np.all(target == after[:, :, :3], axis=2)
    if np.any(mask & ~compatible): raise ValueError(f"Guard conflict on {int(np.sum(mask & ~compatible))} pixels")
    changed = mask & np.any(target != after[:, :, :3], axis=2)
    target[mask] = after[:, :, :3][mask]
    Image.fromarray(current).save(PROVINCES_BMP, format="BMP")
    return current, int(changed.sum()), mask


def update_definitions(data):
    targets = {r["id"]: (r["english"], tuple(r["rgb"])) for r in data["provinces"]}
    targets.update({int(pid): (v["english"], tuple(v["rgb"])) for pid, v in data["mountains"].items()})
    retired = set(data["retired_ids"])
    path = MAP / "definition.csv"; rows = path.read_text(encoding="latin-1").splitlines(); output=[]; seen=set()
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit():
            pid = int(fields[0])
            if pid in retired: continue
            if pid in targets:
                name, colour = targets[pid]; output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x"); seen.add(pid); continue
        output.append(row)
    for pid, (name, colour) in sorted(targets.items()):
        if pid not in seen: output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_areas_regions(data):
    area_members = defaultdict(list)
    for record in data["provinces"]: area_members[record["area"]].append(record["id"])
    area_members["samhan_samnam_area"].append(data["jeju_id"])
    path = MAP / "area.txt"; text = path.read_text(encoding="latin-1")
    for key in data["obsolete_areas"]: text = delete_block(text, key)
    for key in data["areas"]: text = delete_block(text, key)
    blocks = []
    for key in data["areas"]:
        ids = " ".join(map(str, sorted(area_members[key])))
        blocks.append(f"{key} = {{ # {MARKER}\n    {ids}\n}}")
    hokkaido = block_bounds(text, "hokkaido_area")
    if hokkaido is None: raise ValueError("Missing hokkaido_area insertion anchor")
    prefix = text[:hokkaido[0]].rstrip() + "\n\n"
    suffix = text[hokkaido[0]:].lstrip("\n")
    text = prefix + "\n\n".join(blocks) + "\n\n" + suffix
    path.write_text(text, encoding="latin-1")

    path = MAP / "region.txt"; text = path.read_text(encoding="latin-1")
    areas = "\n".join(f"        {key}" for key in data["areas"])
    replacement = f"""korea_region = {{
    areas = {{
{areas}
    }}
    monsoon = {{
        00.06.01
        00.07.30
    }}
}}"""
    text = replace_block(text, "korea_region", replacement)
    path.write_text(text, encoding="latin-1")


def update_memberships(data):
    new_records = [r for r in data["provinces"] if r["id"] in data["new_playable_ids"]]
    new_ids = sorted(r["id"] for r in new_records); mountains = sorted(map(int, data["mountains"]))
    path = MAP / "continent.txt"; text = remove_transaction_lines(path.read_text(encoding="latin-1")); text = append_to_block(text, "asia", new_ids + mountains); path.write_text(text, encoding="latin-1")
    path = MAP / "climate.txt"; text = remove_transaction_lines(path.read_text(encoding="latin-1"))
    for climate in CLIMATE_BLOCKS:
        bounds = block_bounds(text, climate)
        if bounds:
            existing = set(map(int, re.findall(r"\b\d+\b", text[bounds[0]:bounds[1]])))
            text = append_to_block(text, climate, [r["id"] for r in new_records if r["parent_id"] in existing])
    text = append_to_block(text, "impassable", mountains); path.write_text(text, encoding="latin-1")
    path = MAP / "terrain.txt"; text = remove_transaction_lines(path.read_text(encoding="latin-1")); grouped=defaultdict(list)
    for r in new_records: grouped[PARENT_TERRAIN[r["parent_id"]]].append(r["id"])
    grouped["mountain"].extend(mountains)
    bounds = block_bounds(text, "categories"); categories = text[bounds[0]:bounds[1]]
    for terrain, ids in grouped.items(): categories = append_nested(categories, terrain, "terrain_override", ids)
    text = text[:bounds[0]] + categories + text[bounds[1]:]; path.write_text(text, encoding="latin-1")

    # B73 owns the terminal Korean trade node/company.  Do not restore the
    # consolidated Korean provinces to Nippon when B59 is replayed.


def history_matches(pid):
    return sorted((MOD / "history/provinces").glob(f"{pid} - *.txt"))


def first(text, key, default=""):
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\n]+)", text)
    return match.group(1).strip() if match else default


def replace_first(text, key, value):
    pattern = rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^#\n]+"
    return re.sub(pattern, rf"\g<1>{value}", text, count=1) if re.search(pattern, text) else text.rstrip() + f"\n{key} = {value}\n"


def fresh_history(record, parent):
    lines = [
        f"# {record['id']} - {record['english']} - {MARKER}", "", f"owner = {record['owner']}",
        f"controller = {record['owner']}", f"culture = {record['culture']}",
        f"religion = {record['religion']}", f"capital = \"{record['english']}\"",
        f"trade_goods = {first(parent,'trade_goods','grain')}", "hre = no", f"base_tax = {record['development'][0]}",
        f"base_production = {record['development'][1]}", f"base_manpower = {record['development'][2]}", "is_city = yes",
        f"add_core = {record['owner']}",
        *(f"add_core = {tag}" for tag in record["disputed_cores"]),
        "discovered_by = chinese", "discovered_by = nomad_group", "",
    ]
    return "\n".join(lines)


def update_histories(data):
    parent_ids = {r["parent_id"] for r in data["provinces"]}
    parents = {pid: history_matches(pid)[0].read_text(encoding="latin-1") for pid in parent_ids}
    for pid in data["retired_ids"]:
        for path in history_matches(pid): path.unlink()
    new_ids = set(data["new_playable_ids"])
    for record in data["provinces"]:
        pid = record["id"]
        if pid in new_ids:
            for path in history_matches(pid): path.unlink()
            path = MOD / "history/provinces" / f"{pid} - {record['english']}.txt"
            path.write_text(fresh_history(record, parents[record["parent_id"]]), encoding="latin-1"); continue
        matches = history_matches(pid)
        if len(matches) != 1: raise ValueError(f"Expected one history for {pid}")
        path = matches[0]; text = remove_transaction_lines(path.read_text(encoding="latin-1"))
        text = re.sub(r"\A\s*#.*\n", "", text, count=1)
        text = f"# {pid} - {record['english']} - {MARKER}\n" + text.lstrip()
        for key, value in (
            ("owner", record["owner"]),
            ("controller", record["owner"]),
            ("culture", record["culture"]),
            ("religion", record["religion"]),
            ("add_core", record["owner"]),
        ):
            text = replace_first(text, key, value)
        for key, value in zip(("base_tax","base_production","base_manpower"), record["development"]): text = replace_first(text,key,str(value))
        text = replace_first(text,"capital",f'"{record["english"]}"')
        for tag in record["disputed_cores"]:
            text = text.rstrip() + f"\nadd_core = {tag} # {MARKER}\n"
        path.write_text(text, encoding="latin-1")
    # 济州不参与半岛像素重绘，但仍属于朝鲜三十省的发展度平衡范围。
    jeju_path = history_matches(data["jeju_id"])[0]
    jeju_text = jeju_path.read_text(encoding="latin-1")
    for key, value in (
        ("owner", "KOR"), ("controller", "KOR"), ("culture", "gdd_samhan"),
        ("religion", data["religion_targets"]["KOR"]), ("add_core", "KOR"),
    ):
        jeju_text = replace_first(jeju_text, key, value)
    for key, value in zip(
        ("base_tax", "base_production", "base_manpower"),
        data["development_targets"][str(data["jeju_id"])],
    ):
        jeju_text = replace_first(jeju_text, key, str(value))
    jeju_path.write_text(jeju_text, encoding="latin-1")


def position_block(record, x, y):
    values = " ".join(f"{v:.3f}" for v in ([x,y]*6+[0.0,0.0]))
    return f'''# {record["english"]} - {MARKER}
{record["id"]}={{
    position={{
        {values}
    }}
    rotation={{
        0.000 0.000 0.000 0.000 0.000 0.000 0.000
    }}
    height={{
        0.000 0.000 1.000 0.000 0.000 0.000 0.000
    }}
}}'''


def update_positions(data, bitmap):
    path = MAP / "positions.txt"; text = remove_transaction_lines(path.read_text(encoding="latin-1"))
    for pid in data["retired_ids"]: text = delete_block(text, str(pid))
    for record in data["provinces"]:
        ys,xs=np.where(np.all(bitmap==tuple(record["rgb"]),axis=2)); cx,cy=xs.mean(),ys.mean(); nearest=int(np.argmin((xs-cx)**2+(ys-cy)**2))
        text=replace_block(text,str(record["id"]),position_block(record,float(xs[nearest]),float(bitmap.shape[0]-ys[nearest])))
    path.write_text(text.rstrip() + "\n",encoding="latin-1")


def update_localisation(data):
    source=MOD/"localisation_source/012_gdd_b59_korea_consolidation_readable_utf8.txt";lines=["l_english:"]
    records=list(data["provinces"])+[{"id":data["jeju_id"],"chinese":"济州"}]
    for r in sorted(records,key=lambda v:v["id"]): lines += [f' PROV{r["id"]}:0 "{r["chinese"]}"',f' PROV_ADJ{r["id"]}:0 "{r["chinese"]}"']
    for pid,v in sorted(data["mountains"].items(),key=lambda x:int(x[0])): lines += [f' PROV{pid}:0 "{v["chinese"]}"',f' PROV_ADJ{pid}:0 "{v["chinese"]}"']
    for key,v in data["areas"].items():
        lines += [f' {key}:0 "{v["chinese"]}"',f' {key}_name:0 "{v["chinese"]}"',f' {key}_adj:0 "{v["chinese"]}"']
    source.write_text("\n".join(lines)+"\n",encoding="utf-8")
    sys.path.insert(0,str(ROOT/"tools"));from encode_eu4_chinese_localisation import encode_file
    encode_file(source,MOD/"localisation/replace/012_gdd_b59_korea_consolidation_l_english.yml")


def validate(data, bitmap, mask):
    definitions={}
    for line in (MAP/"definition.csv").read_text(encoding="latin-1").splitlines():
        f=line.split(";")
        if f and f[0].isdigit(): definitions[int(f[0])]=tuple(map(int,f[1:4]))
    for r in data["provinces"]:
        if definitions.get(r["id"])!=tuple(r["rgb"]) or not np.any(np.all(bitmap==tuple(r["rgb"]),axis=2)): raise ValueError(f"Invalid playable {r['id']}")
        paths = history_matches(r["id"])
        if len(paths) != 1:
            raise ValueError(f"Province {r['id']} must have one history")
        history = paths[0].read_text(encoding="latin-1")
        for key, expected in (
            ("owner", r["owner"]),
            ("culture", r["culture"]),
            ("religion", r["religion"]),
        ):
            if first(history, key) != expected:
                raise ValueError(f"Province {r['id']} {key} drift")
    jeju_paths = history_matches(data["jeju_id"])
    if len(jeju_paths) != 1:
        raise ValueError("Jeju must have one history")
    jeju_history = jeju_paths[0].read_text(encoding="latin-1")
    for key, expected in (
        ("owner", "KOR"),
        ("culture", data["culture_targets"]["KOR"]),
        ("religion", data["religion_targets"]["KOR"]),
    ):
        if first(jeju_history, key) != expected:
            raise ValueError(f"Jeju {key} drift")
    liao_korea = {r["id"] for r in data["provinces"] if r["owner"] == "LIO"}
    if liao_korea != {2744, 4232, 5359}:
        raise ValueError(f"Liao Korean province set drifted: {sorted(liao_korea)}")
    goryeo = {r["id"] for r in data["provinces"] if r["owner"] == "KOR"}
    goryeo.add(data["jeju_id"])
    if len(goryeo) != 13:
        raise ValueError(f"Goryeo must have thirteen Mahayana provinces: {sorted(goryeo)}")
    for pid in data["retired_ids"]:
        if pid in definitions or history_matches(pid): raise ValueError(f"Retired ID still live {pid}")
    if int(mask.sum())!=data["editable_pixels"]: raise ValueError("Editable mask drift")


def main():
    data=manifest();bitmap,changed,mask=apply_patch(data);update_definitions(data);update_areas_regions(data);update_memberships(data);update_histories(data);update_positions(data,bitmap);update_localisation(data);validate(data,bitmap,mask)
    total_development = sum(sum(values) for values in data["development_targets"].values())
    print(f"B59_KOREA_APPLIED; playable=30; peninsula=29; areas={len(data['areas'])}; retired=9; changed_pixels={changed}; total_development={total_development}; average_development={total_development / data['playable_total']:.2f}")


if __name__=="__main__": main()
