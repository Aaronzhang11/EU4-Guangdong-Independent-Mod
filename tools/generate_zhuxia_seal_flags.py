#!/usr/bin/env python3
"""Generate deterministic small-seal-script flags for Zhuxia-culture states."""

from __future__ import annotations

import argparse
import base64
import json
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
FLAGS = MOD / "gfx/flags"
HISTORIES = MOD / "history/countries"
MASK_ARCHIVE = ROOT / "tools/assets/zhuxia_seal_masks.json.zlib"
ZHUXIA_CULTURES = {
    "gdd_zhongyuan", "gdd_jianghuai", "gdd_chu", "gdd_gan",
    "gdd_hakka", "gdd_gui", "gdd_shu", "gdd_dian",
    "gdd_jin", "gdd_qi", "gdd_yan", "gdd_long",
    "gdd_songwei",
}
INSCRIPTIONS = {
    "BAA": "巴", "CAG": "曹", "CAI": "蔡", "CCH": "巢", "CHC": "楚",
    "CHN": "陳", "CSA": "長沙", "CSH": "順", "CXI": "西", "CZH": "周",
    "CDE": "常",
    "DAE": "代", "DIA": "滇", "DQU": "宕渠", "EGU": "鄂", "GON": "共",
    "GUI": "桂", "GUN": "管", "GUO": "虢", "GYA": "貴", "GZH": "甘",
    "HAK": "客", "HNG": "衡", "HUA": "淮", "HYM": "揚", "HZH": "河",
    "HYA": "漢",
    "JIN": "晉", "JUU": "苴", "LCH": "臨川", "LFA": "蘭芳", "LIU": "六",
    "JJG": "九",
    "LNG": "梁", "LGU": "涼", "LUO": "羅", "LUU": "魯", "MNG": "明", "NCH": "南昌",
    "NNG": "寧", "QIC": "齊", "QIN": "秦", "QSH": "舒", "QVN": "權",
    "QWO": "曲沃", "SHE": "申", "SHU": "蜀", "SNG": "宋", "SUI": "隨",
    "TNG": "唐", "XNG": "邢", "ACG": "安成", "OUE": "甌", "WHU": "蕪",
    "TSF": "天師", "WEI": "魏", "XU2": "徐", "YAN": "燕", "YOU": "義渠",
    "YPG": "陰平", "WVG": "衞", "ZHA": "趙", "ZHG": "周公", "ZHU": "州",
    "ZNG": "鄭", "ZSH": "中山",
}
COLORS = {
    "BAA": (109,150,116), "CAG": (176,130,103), "CAI": (115,118,158),
    "CDE": (116,67,111),
    "CCH": (116,150,163), "CHC": (194,123,58), "CHN": (135,121,103),
    "CSA": (115,47,86), "CSH": (0,110,223), "CXI": (0,0,0),
    "CZH": (209,212,126), "DAE": (137,104,158), "DIA": (235,198,62),
    "DQU": (74,150,105), "EGU": (72,129,122), "GON": (115,118,158),
    "GUI": (78,155,84), "GUN": (232,232,220), "GUO": (96,143,139),
    "GYA": (112,170,205), "GZH": (133,148,154), "HAK": (118,70,140),
    "HYA": (48,77,135),
    "HNG": (93,117,160), "HUA": (67,112,100), "HYM": (72,143,160),
    "HZH": (166,116,120), "JIN": (94,131,154), "JUU": (139,113,153),
    "JJG": (164,82,43),
    "LCH": (85,135,210), "LFA": (203,37,37), "LIU": (245,245,230),
    "LNG": (17,45,69), "LGU": (48,91,112), "LUO": (108,137,124), "LUU": (82,130,172),
    "MNG": (241,196,37), "NCH": (205,82,72), "NNG": (72,123,63),
    "QIC": (200,156,0), "QIN": (5,5,5), "QSH": (157,113,137),
    "QVN": (178,138,75), "QWO": (196,166,74), "SHE": (166,116,120),
    "SHU": (70,162,48), "SNG": (157,113,137), "SUI": (159,129,111),
    "TNG": (150,55,95), "XNG": (99,72,123), "ACG": (63,104,128),
    "OUE": (174,101,74), "WHU": (202,151,70),
    "TSF": (171,136,146), "WEI": (176,130,103), "XU2": (179,128,104),
    "YAN": (168,86,187), "YOU": (157,113,137), "YPG": (126,130,159),
    "WVG": (109,150,116), "ZHA": (116,150,163), "ZHG": (96,143,139),
    "ZHU": (130,96,142), "ZNG": (181,151,101), "ZSH": (74,122,168),
}
# 长沙保留既有诸夏参考旗；河州回回虽使用 gdd_long 文化，但其边疆政权
# 旗由 generate_frontier_polity_flags.py 维护，不能被本生成器覆盖。
PRESERVED = {"CSA", "HZH"}
# 瓯、芜采用吴文化，但仍属于诸夏封国。显式纳入，避免把所有吴文化国家
# 一并改造成篆字旗。
ADDITIONAL_TARGETS = {"OUE", "WHU"}


def masks() -> dict[str, str]:
    return json.loads(zlib.decompress(MASK_ARCHIVE.read_bytes()))


def current_targets() -> set[str]:
    targets: set[str] = set()
    for path in HISTORIES.glob("*.txt"):
        tag = path.name.split(" - ", 1)[0]
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"(?m)^\s*primary_culture\s*=\s*([A-Za-z0-9_]+)", text
        )
        if match and match.group(1) in ZHUXIA_CULTURES:
            targets.add(tag)
    return targets | ADDITIONAL_TARGETS


def tga_bytes(tag: str, glyph_masks: dict[str, str]) -> bytes:
    background = COLORS[tag]
    ink = (232, 218, 164) if sum(background) < 480 else (48, 39, 32)
    alpha = base64.b64decode(glyph_masks[tag])
    if len(alpha) != 128 * 128:
        raise ValueError(f"{tag}: corrupt small-seal-script mask")
    header = struct.pack(
        "<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 128, 128, 24, 0x20
    )
    pixels = bytearray()
    for opacity in alpha:
        rgb = tuple(
            (background[index] * (255 - opacity) + ink[index] * opacity + 127)
            // 255
            for index in range(3)
        )
        pixels.extend((rgb[2], rgb[1], rgb[0]))
    return header + bytes(pixels)


def run(check: bool = False) -> None:
    actual = current_targets()
    expected = set(INSCRIPTIONS)
    if actual != expected:
        raise ValueError(
            f"Zhuxia target drift: missing={sorted(expected-actual)}, "
            f"extra={sorted(actual-expected)}"
        )
    glyph_masks = masks()
    if set(glyph_masks) != expected - PRESERVED:
        raise ValueError("small-seal-script mask archive does not match target policy")
    for tag in sorted(expected - PRESERVED):
        path = FLAGS / f"{tag}.tga"
        data = tga_bytes(tag, glyph_masks)
        if check:
            if not path.exists() or path.read_bytes() != data:
                raise ValueError(f"{tag}: flag is stale")
        else:
            path.write_bytes(data)
    action = "checked" if check else "generated"
    print(f"{action} {len(expected)} Zhuxia flags ({len(PRESERVED)} preserved)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
