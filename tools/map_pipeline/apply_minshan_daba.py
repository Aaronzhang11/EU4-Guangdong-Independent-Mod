#!/usr/bin/env python3
"""Apply the reviewed minimum-change Minshan/Daba strategic barriers."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
OUT = ROOT / "planning/minshan_daba"
DRAFT = OUT / "minshan_daba_strategy_full_draft.bmp"
MOUNTAINS = {
    5175: ("Daba Mountains", "大巴山", (223, 27, 118)),
    5176: ("Min Mountains", "岷山", (166, 234, 140)),
}


def update_definitions():
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    output, seen = [], set()
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in MOUNTAINS:
            pid = int(fields[0])
            name, _, colour = MOUNTAINS[pid]
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
            seen.add(pid)
        else:
            output.append(row)
    for pid, (name, _, colour) in sorted(MOUNTAINS.items()):
        if pid not in seen:
            output.append(f"{pid};{colour[0]};{colour[1]};{colour[2]};{name};x")
    path.write_text("\n".join(output) + "\n", encoding="latin-1")


def update_lists():
    path = MAP / "climate.txt"
    text = path.read_text()
    text = re.sub(
        r"(?m)^\s*.*# (?:Shaanxi|Qin-Shu) mountain barriers\s*$",
        "    5175 5176 5183 5187 # Qin-Shu mountain barriers",
        text,
    )
    path.write_text(text)

    path = MAP / "continent.txt"
    text = path.read_text()
    text = re.sub(
        r"(?m)^\s*.*# (?:Shaanxi|Qin-Shu) impassables\s*$",
        "        5175 5176 5183 5187 # Qin-Shu impassables",
        text,
    )
    path.write_text(text)


def update_localisation():
    path = MOD / "localisation_source/gdd_b26_qinshu_mountains_utf8.txt"
    lines = ["l_english:"]
    for pid, (_, chinese, _) in sorted(MOUNTAINS.items()):
        lines += [f' PROV{pid}:0 "{chinese}"', f' PROV_ADJ{pid}:0 "{chinese}"']
    path.write_text("\n".join(lines) + "\n")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file
    encode_file(path, MOD / "localisation/gdd_b26_qinshu_mountains_l_english.yml")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "pre_minshan_daba_provinces.bmp"
    if not backup.exists():
        shutil.copy2(MAP / "provinces.bmp", backup)
    base = np.asarray(Image.open(backup).convert("RGB"))
    reviewed = np.asarray(Image.open(DRAFT).convert("RGB"))
    changed = np.any(base != reviewed, axis=2)
    result = base.copy()
    result[changed] = reviewed[changed]
    Image.fromarray(result).save(MAP / "provinces.bmp", format="BMP")
    update_definitions()
    update_lists()
    update_localisation()
    print(f"MINSHAN_DABA_APPLIED; CHANGED:{int(changed.sum())}; MINSHAN:607; DABA:681")


if __name__ == "__main__":
    main()
