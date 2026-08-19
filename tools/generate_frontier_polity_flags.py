#!/usr/bin/env python3
"""Generate deterministic EU4-style flags for non-Zhuxia frontier polities.

The B62 pass follows the visual grammar used by vanilla EU4 and the local
"Celestial empire on which the sun never sets" reference mod: a strong field,
one historically grounded central device, and enough internal detail to read
as heraldry rather than a modern flat icon.  All flags remain legible after
EU4 masks them into small shields.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from map_pipeline.apply_b57_changsha_khitan import liao_flag_bytes


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
FLAGS = MOD / "gfx/flags"
HISTORY = MOD / "history/countries"
OUTPUT = ROOT / "planning/frontier_polity_flags_b62"
ASSETS = ROOT / "tools/assets/frontier_flags"
GORYEO_REFERENCE = ASSETS / "goryeo_phoenix_reference.png"
TANGUT_XIA_MASK = ASSETS / "tangut_xia_u17d32_mask.png"
MONGOLIAN_DALI_MASK = ASSETS / "mongolian_dali_mask.png"
MANCHU_HELAN_MASK = ASSETS / "manchu_helan_mask.png"
YI_LIANGSHAN_MASK = ASSETS / "yi_liangshan_nimu_mask.png"
YI_YELANG_MASK = ASSETS / "yi_yelang_yina_mask.png"
SCALE = 4
SIZE = 128


DESIGNS = {
    "AMD": {"name": "安多果洛", "culture": "tibetan", "motif": "snow_peak", "bg": "633b73", "ink": "f2e7cf", "accent": "d89b35", "reason": "雪山、日轮与高原紫，表现果洛部落和安多高地。"},
    "BD2": {"name": "巴氐", "culture": "gdd_diqiang", "motif": "ram", "bg": "355f68", "ink": "ead8b4", "accent": "ba6236", "reason": "盘羊角与山口，强调氐羌山地联盟。"},
    "BMY": {"name": "白马弥药", "culture": "gdd_diqiang", "motif": "tangut_xia", "bg": "f0bd32", "ink": "17140f", "accent": "a62f2b", "reason": "党项弥药政权以西夏文“𗴲”（夏，U+17D32）为国徽，使用西夏常见的金、黑、赤强对比。"},
    "CZM": {"name": "辰州苗蛮", "culture": "miao", "motif": "bronze_drum", "bg": "7d294f", "ink": "e8c36a", "accent": "50a79a", "reason": "八芒铜鼓纹与苗疆织锦色。"},
    "DCH": {"name": "宕昌", "culture": "gdd_diqiang", "motif": "mountain_fort", "bg": "704b2f", "ink": "e5d2a0", "accent": "9f3c32", "reason": "层山上的石寨，表现宕昌羌的谷地堡寨。"},
    "DZH": {"name": "邓至", "culture": "gdd_diqiang", "motif": "twin_peaks", "bg": "4b6476", "ink": "e6dfc5", "accent": "d27b38", "reason": "双峰夹日，取邓至位于岷山交通孔道之意。"},
    "GUZ": {"name": "孤竹", "culture": "gdd_dongyi", "motif": "bronze_owl", "bg": "5b4934", "ink": "d8b65d", "accent": "324f4b", "reason": "商式青铜鸮与竹节边纹，表现孤竹的殷商遗绪。"},
    "HLD": {"name": "曷懒", "culture": "manchu", "motif": "manchu_helan", "bg": "24513f", "ink": "f0cf5a", "accent": "132f27", "reason": "仿原版建州、海西女真旗的框式构图，以竖排满文“ᡥᡝᠯᠠᠨ”（Helan／曷懒）取代猎鹰图腾。"},
    "HLI": {"name": "黎", "culture": "gdd_qiongli", "motif": "sun_waves", "bg": "173c57", "ink": "e8b843", "accent": "63a96a", "reason": "黎锦式日轮、海浪与五指山色带。"},
    "HZH": {"name": "河州回回", "culture": "gdd_long", "motif": "caravan_star", "bg": "245348", "ink": "ead9a5", "accent": "b66a38", "reason": "八角星、河桥与商路门廊，表现河州回回的河湟商贸共同体。"},
    "JRG": {"name": "嘉绒", "culture": "tibetan", "motif": "stone_tower", "bg": "753b34", "ink": "e5d5b4", "accent": "4e7580", "reason": "嘉绒碉楼立于横断山地。"},
    "LIL": {"name": "俚寮", "culture": "gdd_zhuang", "motif": "bronze_drum", "bg": "315d4c", "ink": "dfbd63", "accent": "ad4e35", "reason": "岭南铜鼓与红土色，替代无图案的临时旗。"},
    "LIO": {"name": "辽", "culture": "gdd_khitan", "motif": "khitan_seal_original", "bg": "b89748", "ink": "273036", "accent": "273036", "reason": "恢复 B57 原旗：使用契丹大字九叠篆官印字形，研究资料将其视为可能表示辽或契丹国家专称的字符。"},
    "LSH": {"name": "凉山", "culture": "yi", "motif": "yi_liangshan_wordmark", "bg": "171b21", "ink": "e0b342", "accent": "ae3534", "reason": "以凉山本地自称“ꆀꃅ”（Nimu）为竖排彝文徽记，保留彝族传统黑、赤、金强对比色。"},
    "MDL": {"name": "蒙古大理", "culture": "bai", "motif": "mongolian_dali", "bg": "ffffff", "ink": "000000", "accent": "000000", "reason": "纯白旗面中央竖书黑色传统蒙古文“ᠳᠠᠯᠢ”（Dali／大理），以蒙古统治身份覆盖旧塔湖纹样。"},
    "NUN": {"name": "侬国", "culture": "gdd_zhuang", "motif": "drum_spear", "bg": "285d52", "ink": "e6c36b", "accent": "b53d32", "reason": "铜鼓配交叉长矛，表现侬氏边寨军事联盟。"},
    "NZA": {"name": "南诏", "culture": "yi", "motif": "nanzhao_guanyin", "bg": "6e2934", "ink": "edc45b", "accent": "2d5754", "reason": "以《南诏图传》的阿嵯耶观音为核心，配合莲座与护国光轮，取代泛化的日鸟图腾。"},
    "SHZ": {"name": "沙州", "culture": "oirats", "motif": "dunhuang_banner", "bg": "80532d", "ink": "edcf87", "accent": "27777a", "reason": "按敦煌藏经洞九世纪丝绸幡的三角旗首、窄幅画心、侧带与尾旒重构沙州徽记。"},
    "TZZ": {"name": "田州寨", "culture": "gdd_zhuang", "motif": "mountain_fort", "bg": "4e6d35", "ink": "e8d28c", "accent": "a34833", "reason": "右江山寨与铜鼓色，强调土司堡寨。"},
    "WDU": {"name": "武都", "culture": "gdd_diqiang", "motif": "river_peak", "bg": "37566b", "ink": "e6d7ae", "accent": "4ea6a1", "reason": "白龙江穿行山谷，构成武都的地理徽记。"},
    "WGS": {"name": "汪古罗斯", "culture": "mongol", "motif": "ongud_nestorian_cross", "bg": "285c79", "ink": "e3c36d", "accent": "d9e3df", "reason": "使用元代内蒙古景教墓志常见的莲台十字，直接对应汪古部十三至十四世纪景教传统。"},
    "WLM": {"name": "武陵蛮", "culture": "miao", "motif": "sun_bird", "bg": "294f43", "ink": "e0bd58", "accent": "b84545", "reason": "武陵山神鸟与织锦菱纹。"},
    "WUZ": {"name": "无终", "culture": "gdd_dongyi", "motif": "black_bird", "bg": "c58c42", "ink": "20272a", "accent": "eee0b7", "reason": "玄鸟负日，呼应燕山以东的古老族源叙事。"},
    "WXG": {"name": "武兴", "culture": "gdd_diqiang", "motif": "mountain_gate", "bg": "4e6550", "ink": "e3d5ad", "accent": "ad5638", "reason": "三峰与关门，表现汉水上游山地要塞。"},
    "WXM": {"name": "五溪苗蛮", "culture": "miao", "motif": "five_streams", "bg": "216c68", "ink": "e6c15d", "accent": "173e66", "reason": "五道曲水织成苗锦式连续纹。"},
    "YEL": {"name": "夜郎", "culture": "yi", "motif": "yi_yelang_wordmark", "bg": "4b2768", "ink": "ebc24f", "accent": "58a07a", "reason": "采用彝语研究所释“yi-na”音形的规范彝文“ꑳꆅ”竖排，并以紫、金、绿保留夜郎的西南青铜感。"},
    "ZHI": {"name": "枳", "culture": "miao", "motif": "river_fort", "bg": "74315d", "ink": "ead39a", "accent": "4fa69a", "reason": "江峡、城门和巴地织纹组合。"},
    "KOR": {"name": "高丽", "culture": "gdd_samhan", "motif": "goryeo_phoenix", "bg": "f8d98d", "ink": "202229", "accent": "426764", "reason": "直接采用用户参考图中的凤凰主体，以高丽青瓷绿、朱红和绢黄金构成宫廷纹样。"},
}


# 旗面结构刻意轮换，避免二十八国都落入“底色 + 白框 + 扁平图标”的
# 现代徽标模板。结构只负责底纹，中央徽记仍由各国的历史设定决定。
FIELDS = {
    "AMD": "quartered", "BD2": "serrated", "BMY": "tangut",
    "CZM": "textile_roundel", "DCH": "chevron", "DZH": "split",
    "GUZ": "brocade_roundel", "HLD": "manchu_frame", "HLI": "horizontal",
    "HZH": "arched", "JRG": "quartered", "KOR": "reference",
    "LIL": "textile_roundel", "LIO": "legacy_exact", "LSH": "vertical",
    "MDL": "plain_exact", "NUN": "saltire", "NZA": "sun_disc",
    "SHZ": "plain", "TZZ": "bordered", "WDU": "river",
    "WGS": "roundel", "WLM": "sun_disc", "WUZ": "sunburst",
    "WXG": "chevron", "WXM": "textile", "YEL": "roundel",
    "ZHI": "horizontal",
}

for _tag, _field in FIELDS.items():
    DESIGNS[_tag]["field"] = _field


def rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, amount: float):
    return tuple(round(left * (1 - amount) + right * amount) for left, right in zip(a, b))


def alpha(color, opacity: int):
    return (*color, opacity)


def sc(points):
    return [(round(x * SCALE), round(y * SCALE)) for x, y in points]


def line(draw, points, fill, width=7, joint="curve"):
    draw.line(sc(points), fill=fill, width=width * SCALE, joint=joint)


def ellipse(draw, box, fill, outline=None, width=1):
    draw.ellipse(tuple(round(v * SCALE) for v in box), fill=fill, outline=outline, width=width * SCALE)


def polygon(draw, points, fill):
    draw.polygon(sc(points), fill=fill)


def rect(draw, box, fill, outline=None, width=1):
    draw.rectangle(tuple(round(v * SCALE) for v in box), fill=fill, outline=outline, width=width * SCALE)


def star(cx, cy, r1, r2, rays=8):
    points = []
    for index in range(rays * 2):
        radius = r1 if index % 2 == 0 else r2
        angle = -math.pi / 2 + index * math.pi / rays
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def border(draw, ink):
    rect(draw, (5, 5, 123, 123), None, ink, 3)


def draw_field(image: Image.Image, field: str, bg, ink, accent) -> None:
    """Paint a heraldic field behind the polity emblem."""
    draw = ImageDraw.Draw(image)
    pale = mix(bg, (255, 246, 218), 0.28)
    deep = mix(bg, (20, 17, 15), 0.30)
    muted = mix(bg, accent, 0.45)

    if field in {"plain", "reference"}:
        return
    if field == "quartered":
        rect(draw, (0, 0, 64, 64), muted)
        rect(draw, (64, 64, 128, 128), muted)
        line(draw, [(0, 64), (128, 64)], pale, 3)
        line(draw, [(64, 0), (64, 128)], pale, 3)
    elif field == "serrated":
        rect(draw, (0, 0, 24, 128), deep)
        for y in range(-8, 136, 16):
            polygon(draw, [(22, y), (40, y + 8), (22, y + 16)], deep)
        line(draw, [(24, 0), (24, 128)], accent, 3)
    elif field == "tangut":
        rect(draw, (0, 0, 128, 18), deep)
        rect(draw, (0, 110, 128, 128), deep)
        for x in range(10, 128, 24):
            polygon(draw, [(x, 18), (x + 10, 28), (x + 20, 18)], accent)
            polygon(draw, [(x, 110), (x + 10, 100), (x + 20, 110)], accent)
    elif field == "textile_roundel":
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for x in range(-24, 152, 24):
            od.line(sc([(x, 0), (x + 128, 128)]), fill=alpha(pale, 42), width=2 * SCALE)
            od.line(sc([(x, 128), (x + 128, 0)]), fill=alpha(pale, 42), width=2 * SCALE)
        image.alpha_composite(overlay)
        draw = ImageDraw.Draw(image)
        ellipse(draw, (18, 18, 110, 110), muted, pale, 4)
        ellipse(draw, (25, 25, 103, 103), bg, accent, 2)
    elif field == "chevron":
        polygon(draw, [(0, 0), (32, 0), (64, 42), (96, 0), (128, 0), (128, 25), (64, 69), (0, 25)], muted)
        polygon(draw, [(0, 128), (0, 106), (64, 69), (128, 106), (128, 128)], deep)
        line(draw, [(0, 106), (64, 69), (128, 106)], pale, 3)
    elif field == "split":
        polygon(draw, [(0, 0), (128, 0), (0, 128)], muted)
        line(draw, [(0, 128), (128, 0)], pale, 4)
    elif field == "brocade_roundel":
        ellipse(draw, (10, 10, 118, 118), muted, accent, 4)
        for radius in (45, 34, 24):
            polygon(draw, star(64, 64, radius, radius - 7, 12), None)
            line(draw, star(64, 64, radius, radius - 7, 12) + [star(64, 64, radius, radius - 7, 12)[0]], pale, 1)
        ellipse(draw, (26, 26, 102, 102), bg, pale, 2)
    elif field == "sun_disc":
        ellipse(draw, (14, 14, 114, 114), muted, pale, 4)
        ellipse(draw, (25, 25, 103, 103), bg, accent, 2)
    elif field == "horizontal":
        rect(draw, (0, 0, 128, 24), muted)
        rect(draw, (0, 104, 128, 128), deep)
        line(draw, [(0, 25), (128, 25)], pale, 3)
        line(draw, [(0, 103), (128, 103)], pale, 3)
    elif field == "arched":
        rect(draw, (0, 0, 128, 22), deep)
        line(draw, [(15, 112), (15, 54), (40, 28), (64, 54), (88, 28), (113, 54), (113, 112)], muted, 9)
        line(draw, [(14, 116), (114, 116)], pale, 4)
    elif field == "roundel":
        ellipse(draw, (12, 12, 116, 116), muted, pale, 4)
        ellipse(draw, (23, 23, 105, 105), bg, accent, 2)
    elif field == "vertical":
        rect(draw, (0, 0, 38, 128), deep)
        rect(draw, (90, 0, 128, 128), deep)
        line(draw, [(38, 0), (38, 128)], accent, 3)
        line(draw, [(90, 0), (90, 128)], accent, 3)
    elif field == "bordered":
        rect(draw, (0, 0, 128, 128), deep)
        rect(draw, (10, 10, 118, 118), bg, pale, 3)
        rect(draw, (17, 17, 111, 111), None, accent, 2)
    elif field == "saltire":
        polygon(draw, [(0, 0), (18, 0), (128, 110), (128, 128), (110, 128), (0, 18)], muted)
        polygon(draw, [(110, 0), (128, 0), (128, 18), (18, 128), (0, 128), (0, 110)], muted)
        line(draw, [(0, 0), (128, 128)], pale, 2)
        line(draw, [(128, 0), (0, 128)], pale, 2)
    elif field == "sunburst":
        center = (64, 64)
        for ray in range(16):
            a1 = ray * math.tau / 16
            a2 = (ray + 1) * math.tau / 16
            color = muted if ray % 2 == 0 else bg
            polygon(draw, [center, (64 + 100 * math.cos(a1), 64 + 100 * math.sin(a1)), (64 + 100 * math.cos(a2), 64 + 100 * math.sin(a2))], color)
        ellipse(draw, (20, 20, 108, 108), None, pale, 3)
    elif field == "diagonal":
        polygon(draw, [(0, 0), (42, 0), (128, 86), (128, 128), (86, 128), (0, 42)], muted)
        line(draw, [(0, 42), (86, 128)], pale, 3)
        line(draw, [(42, 0), (128, 86)], pale, 3)
    elif field == "river":
        polygon(draw, [(0, 91), (31, 70), (62, 86), (92, 60), (128, 79), (128, 128), (0, 128)], muted)
        line(draw, [(0, 103), (28, 84), (59, 101), (91, 75), (128, 94)], pale, 4)
    elif field == "textile":
        for row in range(-8, 136, 18):
            line(draw, [(0, row), (16, row + 9), (32, row), (48, row + 9), (64, row), (80, row + 9), (96, row), (112, row + 9), (128, row)], muted, 3)
    else:
        raise ValueError(f"unknown field: {field}")


def mountains(draw, ink, accent, y=92):
    polygon(draw, [(13, y), (43, 47), (61, 72), (82, 35), (116, y)], accent)
    polygon(draw, [(18, y), (43, 55), (61, 79), (82, 44), (110, y)], ink)


def waves(draw, color, y=100, count=3):
    for row in range(count):
        yy = y + row * 8
        line(draw, [(10, yy), (29, yy - 7), (48, yy), (67, yy - 7), (86, yy), (105, yy - 7), (122, yy)], color, 4)


def draw_motif(draw, motif, ink, accent):
    if motif == "snow_peak":
        ellipse(draw, (49, 14, 79, 44), accent)
        mountains(draw, ink, accent, 110)
        polygon(draw, [(43, 47), (53, 65), (62, 55), (82, 35), (93, 58), (82, 52), (70, 71), (58, 66)], (255, 250, 235))
    elif motif == "ram":
        mountains(draw, ink, accent, 111)
        ellipse(draw, (42, 36, 86, 80), None, ink, 6)
        ellipse(draw, (51, 45, 77, 71), accent)
        line(draw, [(42, 58), (29, 42), (25, 58), (39, 71)], ink, 7)
        line(draw, [(86, 58), (99, 42), (103, 58), (89, 71)], ink, 7)
    elif motif == "white_horse":
        polygon(draw, [(37, 95), (42, 43), (61, 25), (85, 34), (96, 58), (80, 77), (77, 104), (55, 104), (56, 75)], ink)
        polygon(draw, [(60, 31), (69, 13), (77, 35)], ink)
        ellipse(draw, (72, 47, 79, 54), accent)
        line(draw, [(47, 45), (64, 55), (87, 55)], accent, 5)
    elif motif == "bronze_drum":
        ellipse(draw, (23, 23, 105, 105), accent, ink, 5)
        polygon(draw, star(64, 64, 30, 12, 8), ink)
        ellipse(draw, (54, 54, 74, 74), accent)
        for x, y in [(18, 64), (110, 64), (64, 18), (64, 110)]: ellipse(draw, (x-4, y-4, x+4, y+4), ink)
    elif motif == "mountain_fort":
        mountains(draw, accent, ink, 115)
        rect(draw, (39, 57, 89, 100), ink)
        for x in (39, 59, 79): rect(draw, (x, 48, x+10, 64), ink)
        rect(draw, (57, 76, 71, 100), accent)
    elif motif == "twin_peaks":
        ellipse(draw, (51, 16, 77, 42), accent)
        polygon(draw, [(8, 110), (42, 46), (63, 79), (85, 42), (120, 110)], ink)
        polygon(draw, [(42, 46), (49, 60), (55, 57), (63, 79)], accent)
        polygon(draw, [(85, 42), (91, 56), (98, 55), (105, 81)], accent)
    elif motif == "falcon":
        ellipse(draw, (55, 16, 79, 40), accent)
        polygon(draw, [(64, 96), (48, 62), (14, 45), (28, 78), (50, 91)], ink)
        polygon(draw, [(64, 96), (80, 62), (114, 45), (100, 78), (78, 91)], ink)
        polygon(draw, [(57, 49), (64, 35), (71, 49), (82, 56), (71, 62), (64, 84), (57, 62), (46, 56)], ink)
        polygon(draw, [(64, 35), (72, 39), (65, 43)], accent)
    elif motif == "bronze_owl":
        polygon(draw, [(64, 30), (43, 42), (31, 68), (39, 102), (64, 111), (89, 102), (97, 68), (85, 42)], ink)
        polygon(draw, [(43, 42), (28, 24), (54, 35)], ink)
        polygon(draw, [(85, 42), (100, 24), (74, 35)], ink)
        ellipse(draw, (40, 49, 59, 68), accent)
        ellipse(draw, (69, 49, 88, 68), accent)
        polygon(draw, [(64, 61), (55, 74), (64, 82), (73, 74)], accent)
        for x in (14, 111):
            line(draw, [(x, 20), (x, 108)], accent, 4)
    elif motif == "sun_waves":
        ellipse(draw, (43, 18, 85, 60), ink)
        polygon(draw, [(12, 94), (40, 61), (64, 83), (88, 57), (116, 94)], accent)
        waves(draw, ink, 101, 2)
    elif motif == "stone_tower":
        mountains(draw, accent, ink, 117)
        polygon(draw, [(44, 101), (49, 35), (79, 35), (84, 101)], ink)
        for y in (48, 64, 80): rect(draw, (58, y, 70, y+7), accent)
        polygon(draw, [(45, 35), (64, 20), (83, 35)], ink)
    elif motif == "white_deer":
        ellipse(draw, (48, 16, 80, 48), accent)
        ellipse(draw, (39, 67, 88, 91), ink)
        polygon(draw, [(75, 72), (79, 48), (89, 43), (92, 53), (85, 65)], ink)
        line(draw, [(84, 46), (80, 34), (75, 29)], ink, 4)
        line(draw, [(86, 45), (93, 34), (98, 29)], ink, 4)
        for x in (48, 77): line(draw, [(x, 84), (x-3, 108)], ink, 5)
        line(draw, [(39, 72), (27, 65)], ink, 5)
    elif motif == "three_flames":
        for x, height, color in [(37, 54, accent), (64, 75, ink), (91, 54, accent)]:
            polygon(draw, [(x, 108), (x-18, 76), (x-7, 44+75-height), (x, 20+75-height), (x+7, 49+75-height), (x+18, 76)], color)
    elif motif == "pagoda_lake":
        mountains(draw, accent, ink, 83)
        for y, half in [(31, 13), (44, 18), (58, 22), (74, 27), (91, 32)]:
            polygon(draw, [(64-half, y), (64+half, y), (64+half-5, y+7), (64-half+5, y+7)], ink)
        rect(draw, (60, 30, 68, 101), ink)
        waves(draw, accent, 108, 2)
    elif motif == "drum_spear":
        line(draw, [(25, 106), (99, 22)], accent, 6)
        line(draw, [(29, 22), (103, 106)], accent, 6)
        polygon(draw, [(99, 22), (87, 28), (94, 35)], accent)
        polygon(draw, [(29, 22), (41, 28), (34, 35)], accent)
        ellipse(draw, (37, 37, 91, 91), ink)
        polygon(draw, star(64, 64, 20, 8, 8), accent)
    elif motif == "caravan_star":
        polygon(draw, star(64, 32, 20, 9, 8), ink)
        line(draw, [(21, 102), (21, 69), (42, 51), (64, 69), (86, 51), (107, 69), (107, 102)], accent, 7)
        line(draw, [(38, 102), (38, 75), (64, 57), (90, 75), (90, 102)], ink, 6)
        line(draw, [(13, 111), (115, 111)], ink, 6)
    elif motif == "sun_bird":
        ellipse(draw, (47, 16, 81, 50), ink)
        polygon(draw, [(64, 91), (46, 62), (12, 54), (35, 83), (55, 94)], accent)
        polygon(draw, [(64, 91), (82, 62), (116, 54), (93, 83), (73, 94)], accent)
        polygon(draw, [(56, 55), (64, 43), (72, 55), (68, 97), (60, 97)], accent)
    elif motif == "oasis":
        polygon(draw, [(0, 82), (38, 55), (73, 78), (128, 48), (128, 128), (0, 128)], ink)
        polygon(draw, [(0, 101), (43, 78), (80, 98), (128, 72), (128, 128), (0, 128)], accent)
        ellipse(draw, (44, 82, 85, 104), (70, 139, 132))
        polygon(draw, star(96, 26, 11, 5, 8), ink)
    elif motif == "river_peak":
        mountains(draw, ink, accent, 95)
        polygon(draw, [(54, 62), (72, 62), (66, 83), (80, 95), (68, 116), (50, 116), (62, 98), (48, 84)], accent)
    elif motif == "steppe_tamga":
        polygon(draw, star(97, 26, 11, 5, 8), accent)
        line(draw, [(37, 31), (37, 98), (64, 111), (91, 98), (91, 31)], ink, 8)
        line(draw, [(37, 52), (64, 68), (91, 52)], ink, 8)
        line(draw, [(64, 68), (64, 104)], ink, 8)
    elif motif == "black_bird":
        ellipse(draw, (49, 14, 83, 48), accent)
        polygon(draw, [(64, 98), (48, 62), (13, 48), (33, 82), (55, 92)], ink)
        polygon(draw, [(64, 98), (80, 62), (115, 48), (95, 82), (73, 92)], ink)
        polygon(draw, [(57, 51), (64, 38), (72, 52), (67, 103), (60, 103)], ink)
    elif motif == "mountain_gate":
        mountains(draw, ink, accent, 110)
        rect(draw, (39, 69, 89, 105), accent)
        rect(draw, (52, 80, 76, 105), ink)
        line(draw, [(37, 69), (64, 51), (91, 69)], accent, 7)
    elif motif == "five_streams":
        for row in range(5):
            y = 25 + row * 19
            line(draw, [(5, y), (27, y+8), (50, y-4), (73, y+8), (98, y-4), (123, y+7)], ink if row % 2 == 0 else accent, 6)
    elif motif == "sun_serpent":
        ellipse(draw, (44, 16, 84, 56), ink)
        line(draw, [(22, 97), (39, 76), (57, 93), (75, 70), (96, 89), (110, 73)], accent, 9)
        polygon(draw, [(105, 65), (121, 70), (109, 82)], accent)
    elif motif == "ongud_nestorian_cross":
        # Yuan-period Inner Mongolian Christian epitaphs repeatedly place a
        # flared cross above a lotus.  The pale under-stroke gives the small
        # EU4 shield the incised, metal-inlay appearance of those objects.
        line(draw, [(64, 27), (64, 84)], accent, 15)
        line(draw, [(38, 48), (90, 48)], accent, 15)
        line(draw, [(64, 27), (64, 84)], ink, 9)
        line(draw, [(38, 48), (90, 48)], ink, 9)
        for points in (
            [(64, 18), (55, 31), (73, 31)],
            [(29, 48), (42, 39), (42, 57)],
            [(99, 48), (86, 39), (86, 57)],
        ):
            polygon(draw, points, ink)
        # Lotus pedestal taken from the Chifeng bilingual epitaph type.
        polygon(draw, [(64, 103), (48, 82), (64, 88), (80, 82)], accent)
        polygon(draw, [(64, 105), (35, 91), (49, 110)], ink)
        polygon(draw, [(64, 105), (93, 91), (79, 110)], ink)
        polygon(draw, [(64, 107), (49, 85), (64, 91), (79, 85)], ink)
        line(draw, [(39, 112), (89, 112)], accent, 3)
    elif motif == "dunhuang_banner":
        # Compressed reconstruction of a Cave 17 silk banner: triangular
        # headpiece, narrow painted body, moss-green side streamers, lower
        # weighting board and four tail streamers.
        coral = (177, 79, 58)
        rose = (207, 125, 105)
        deep = (72, 42, 35)
        polygon(draw, [(64, 7), (34, 30), (94, 30)], rose)
        line(draw, [(64, 7), (34, 30), (94, 30), (64, 7)], coral, 3)
        rect(draw, (31, 29, 97, 95), ink, deep, 3)
        rect(draw, (38, 34, 90, 91), coral, accent, 2)
        polygon(draw, [(23, 28), (34, 31), (34, 96), (24, 105)], accent)
        polygon(draw, [(105, 28), (94, 31), (94, 96), (104, 105)], accent)
        # A lotus-and-halo devotional image remains legible without copying a
        # particular sacred figure from the source painting.
        ellipse(draw, (50, 39, 78, 67), ink, deep, 2)
        ellipse(draw, (57, 45, 71, 59), (236, 210, 159))
        polygon(draw, [(64, 59), (51, 79), (57, 89), (64, 80), (71, 89), (77, 79)], accent)
        polygon(draw, [(64, 90), (49, 82), (55, 94)], ink)
        polygon(draw, [(64, 90), (79, 82), (73, 94)], ink)
        rect(draw, (31, 94, 97, 100), deep)
        for x, color in ((37, accent), (51, rose), (65, accent), (79, rose)):
            polygon(draw, [(x, 100), (x + 10, 100), (x + 8, 121), (x + 5, 115), (x + 2, 121)], color)
    elif motif == "nanzhao_guanyin":
        # Stylised Ācārya Avalokiteśvara from the 899 Nanzhao Tuzhuan: tall,
        # frontal, crowned, haloed and standing on a lotus pedestal.
        pale = (244, 224, 174)
        ellipse(draw, (38, 10, 90, 62), ink, accent, 3)
        polygon(draw, [(52, 31), (57, 18), (64, 25), (71, 18), (76, 31)], accent)
        ellipse(draw, (54, 28, 74, 48), pale, accent, 2)
        polygon(draw, [(57, 47), (48, 76), (55, 101), (64, 91), (73, 101), (80, 76), (71, 47)], pale)
        polygon(draw, [(59, 50), (50, 71), (38, 82), (44, 87), (57, 75)], accent)
        polygon(draw, [(69, 50), (78, 71), (90, 82), (84, 87), (71, 75)], accent)
        line(draw, [(64, 48), (64, 94)], ink, 4)
        polygon(draw, [(64, 109), (43, 96), (54, 113)], ink)
        polygon(draw, [(64, 109), (85, 96), (74, 113)], ink)
        polygon(draw, [(64, 110), (53, 91), (64, 97), (75, 91)], pale)
    elif motif == "river_fort":
        waves(draw, accent, 91, 3)
        rect(draw, (35, 38, 93, 82), ink)
        for x in (35, 57, 79): rect(draw, (x, 29, x+14, 45), ink)
        rect(draw, (56, 57, 72, 82), accent)
    elif motif == "goryeo":
        ellipse(draw, (49, 14, 79, 44), accent)
        polygon(draw, [(10, 92), (39, 50), (62, 78), (84, 43), (118, 92)], ink)
        waves(draw, ink, 101, 2)
    else:
        raise ValueError(f"unknown motif: {motif}")


def fitted_mask(mask: Image.Image, width: int, height: int) -> Image.Image:
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError("empty motif mask")
    mask = mask.crop(bbox)
    scale = min(width / mask.width, height / mask.height)
    return mask.resize((round(mask.width * scale), round(mask.height * scale)), Image.Resampling.LANCZOS)


def tangut_xia_layer(ink) -> Image.Image:
    if not TANGUT_XIA_MASK.exists():
        raise FileNotFoundError(f"missing Tangut glyph mask: {TANGUT_XIA_MASK}")
    mask = fitted_mask(Image.open(TANGUT_XIA_MASK).convert("L"), 78 * SCALE, 82 * SCALE)
    layer = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    x = (layer.width - mask.width) // 2
    y = (layer.height - mask.height) // 2 + 2 * SCALE
    color = Image.new("RGBA", mask.size, (*ink, 255))
    color.putalpha(mask)
    layer.alpha_composite(color, (x, y))
    return layer


def yi_wordmark_layer(mask_path: Path, ink, accent) -> Image.Image:
    """Colour a fixed two-glyph Yi wordmark with a narrow manuscript edge."""
    if not mask_path.exists():
        raise FileNotFoundError(f"missing Yi wordmark mask: {mask_path}")
    mask = fitted_mask(Image.open(mask_path).convert("L"), 66 * SCALE, 90 * SCALE)
    layer = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    x = (layer.width - mask.width) // 2
    y = (layer.height - mask.height) // 2 + SCALE
    outline_mask = mask.filter(ImageFilter.MaxFilter(3 * SCALE + 1))
    outline = Image.new("RGBA", outline_mask.size, (*accent, 255))
    outline.putalpha(outline_mask)
    layer.alpha_composite(outline, (x, y))
    glyph = Image.new("RGBA", mask.size, (*ink, 255))
    glyph.putalpha(mask)
    layer.alpha_composite(glyph, (x, y))
    return layer


def mongolian_dali_flag() -> Image.Image:
    """Render a white flag with the connected vertical Mongolian word ᠳᠠᠯᠢ.

    The fixed mask was shaped from Noto Sans Mongolian with HarfBuzz before
    being rotated into the script's traditional top-to-bottom direction.  It
    is stored as an asset so future regeneration does not depend on the host's
    font or shaping engine.
    """
    if not MONGOLIAN_DALI_MASK.exists():
        raise FileNotFoundError(f"missing Mongolian Dali glyph mask: {MONGOLIAN_DALI_MASK}")
    mask = Image.open(MONGOLIAN_DALI_MASK).convert("L")
    image = Image.new("RGB", mask.size, (255, 255, 255))
    image.paste((0, 0, 0), (0, 0, mask.width, mask.height), mask)
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def manchu_helan_flag(bg, ink, accent) -> Image.Image:
    """Render Helan in the framed wordmark style of vanilla Jurchen flags."""
    if not MANCHU_HELAN_MASK.exists():
        raise FileNotFoundError(f"missing Manchu Helan glyph mask: {MANCHU_HELAN_MASK}")
    mask = Image.open(MANCHU_HELAN_MASK).convert("L")
    image = Image.new("RGB", mask.size, ink)
    draw = ImageDraw.Draw(image)
    inset = 13 * SCALE
    draw.rectangle((inset, inset, image.width - inset - 1, image.height - inset - 1), fill=bg, outline=accent, width=2 * SCALE)
    draw.rectangle((inset + 3 * SCALE, inset + 3 * SCALE, image.width - inset - 3 * SCALE - 1, image.height - inset - 3 * SCALE - 1), outline=mix(bg, ink, 0.42), width=SCALE)
    image.paste(ink, (0, 0, mask.width, mask.height), mask)
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def goryeo_phoenix_layer() -> Image.Image:
    """Extract the connected parchment background from the user reference."""
    if not GORYEO_REFERENCE.exists():
        raise FileNotFoundError(f"missing Goryeo reference: {GORYEO_REFERENCE}")
    reference = Image.open(GORYEO_REFERENCE).convert("RGB")
    width, height = reference.size
    # Relative coordinates make the extraction stable if the supplied preview
    # is losslessly rescaled.  They exclude the black hoist and four colour
    # bars while retaining the complete phoenix and its surrounding clouds.
    motif = reference.crop((round(width * 0.34), round(height * 0.12), round(width * 0.89), round(height * 0.91)))
    work = motif.copy()
    marker = (1, 2, 3)
    for seed in ((0, 0), (work.width - 1, 0), (0, work.height - 1), (work.width - 1, work.height - 1)):
        ImageDraw.floodfill(work, seed, marker, thresh=34)
    mask = Image.new("L", work.size, 255)
    source_pixels = work.get_flattened_data() if hasattr(work, "get_flattened_data") else work.getdata()
    mask.putdata([0 if pixel == marker else 255 for pixel in source_pixels])
    # A one-pixel soften removes the pale fringe created by the reference PNG's
    # antialiasing without eroding the phoenix's dark contour.
    mask = mask.filter(ImageFilter.GaussianBlur(0.65))
    bbox = mask.getbbox()
    motif = motif.crop(bbox)
    mask = mask.crop(bbox)
    scale = min((116 * SCALE) / motif.width, (112 * SCALE) / motif.height)
    size = (round(motif.width * scale), round(motif.height * scale))
    motif = motif.resize(size, Image.Resampling.LANCZOS)
    mask = mask.resize(size, Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
    x = (layer.width - motif.width) // 2 + 2 * SCALE
    y = (layer.height - motif.height) // 2
    motif.putalpha(mask)
    layer.alpha_composite(motif, (x, y))
    return layer


def add_emblem(image: Image.Image, emblem: Image.Image, bg) -> None:
    mask = emblem.getchannel("A")
    shadow_mask = mask.filter(ImageFilter.GaussianBlur(1.3 * SCALE))
    shadow = Image.new("RGBA", image.size, (*mix(bg, (0, 0, 0), 0.72), 255))
    shadow.putalpha(shadow_mask.point(lambda value: round(value * 0.52)))
    shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shifted.paste(shadow, (2 * SCALE, 2 * SCALE), shadow)
    image.alpha_composite(shifted)
    image.alpha_composite(emblem)


def antique_texture(image: Image.Image, tag: str) -> Image.Image:
    """Apply a restrained, deterministic dye-and-cloth texture at final size."""
    image = image.convert("RGB")
    rng = random.Random(f"frontier-flag-b62:{tag}")
    pixels = image.load()
    cx = cy = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            edge = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / 91
            weave = 1 if (x % 4 == 0 or y % 5 == 0) else 0
            delta = rng.choice((-2, -1, 0, 0, 0, 1, 2)) - round(max(0, edge - 0.55) * 5) + weave
            pixels[x, y] = tuple(max(0, min(255, channel + delta)) for channel in pixels[x, y])
    return image


def render_flag(tag: str, design: dict[str, str]) -> Image.Image:
    if design["motif"] == "mongolian_dali":
        return mongolian_dali_flag()

    bg, ink, accent = (rgb(design[key]) for key in ("bg", "ink", "accent"))
    if design["motif"] == "manchu_helan":
        return manchu_helan_flag(bg, ink, accent)

    image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (*bg, 255))
    draw_field(image, design["field"], bg, ink, accent)

    if design["motif"] == "goryeo_phoenix":
        emblem = goryeo_phoenix_layer()
    elif design["motif"] == "tangut_xia":
        emblem = tangut_xia_layer(ink)
    elif design["motif"] == "yi_liangshan_wordmark":
        emblem = yi_wordmark_layer(YI_LIANGSHAN_MASK, ink, accent)
    elif design["motif"] == "yi_yelang_wordmark":
        emblem = yi_wordmark_layer(YI_YELANG_MASK, ink, accent)
    else:
        emblem = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw_motif(ImageDraw.Draw(emblem), design["motif"], ink, accent)
    add_emblem(image, emblem, bg)

    # A dark edge survives EU4's shield mask better than the old universal
    # cream card frame and mirrors the native game's flag assets.
    draw = ImageDraw.Draw(image)
    rect(draw, (1, 1, 127, 127), None, mix(bg, ink, 0.72), 2)
    rendered = image.convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    return antique_texture(rendered, tag)


def history_culture(tag: str) -> str | None:
    paths = sorted(HISTORY.glob(f"{tag} - *.txt"))
    if not paths:
        return None
    match = re.search(r"(?m)^\s*primary_culture\s*=\s*([A-Za-z0-9_]+)", paths[0].read_text(encoding="utf-8", errors="ignore"))
    return match.group(1) if match else None


def font(size: int):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def contact_sheet(rendered: dict[str, Image.Image]) -> Image.Image:
    columns, cell_w, cell_h = 5, 260, 190
    rows = (len(rendered) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h + 64), (31, 32, 35))
    draw = ImageDraw.Draw(sheet)
    title_font, label_font, small_font = font(28), font(20), font(14)
    draw.text((24, 15), "B62 边疆与域外政权旗帜 · 原版纹章化修订", fill=(242, 236, 216), font=title_font)
    for index, tag in enumerate(sorted(rendered)):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h + 64
        sheet.paste(rendered[tag], (x + 14, y + 14))
        design = DESIGNS[tag]
        draw.text((x + 154, y + 24), tag, fill=(240, 204, 105), font=label_font)
        draw.text((x + 154, y + 54), design["name"], fill=(240, 240, 235), font=label_font)
        draw.text((x + 154, y + 88), design["culture"], fill=(165, 181, 184), font=small_font)
    return sheet


def expected_bytes(image: Image.Image) -> bytes:
    import io
    stream = io.BytesIO()
    image.save(stream, format="TGA", compression=None)
    return stream.getvalue()


def run(check: bool) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for tag, design in DESIGNS.items():
        actual_culture = history_culture(tag)
        if actual_culture != design["culture"]:
            raise ValueError(f"{tag}: expected {design['culture']}, found {actual_culture}")
        if tag == "LIO":
            # Keep the earlier B57 Khitan seal asset byte-for-byte identical.
            data = liao_flag_bytes()
            image = Image.open(io.BytesIO(data)).convert("RGB")
        else:
            image = render_flag(tag, design)
            data = expected_bytes(image)
        rendered[tag] = image
        target = FLAGS / f"{tag}.tga"
        if check:
            if not target.exists() or target.read_bytes() != data:
                raise ValueError(f"{tag}: stale frontier flag")
        else:
            target.write_bytes(data)

    sheet = contact_sheet(rendered)
    sheet_target = OUTPUT / "contact_sheet.png"
    manifest_target = OUTPUT / "batch_manifest.json"
    manifest = {
        "batch": "B62",
        "policy": "vanilla-style non-Zhuxia frontier heraldry",
        "references": {
            "style": ["EU4 1.37.5 vanilla flags", "Celestial empire on which the sun never sets (Workshop 1728520255)"],
            "goryeo": "tools/assets/frontier_flags/goryeo_phoenix_reference.png (user supplied)",
            "tangut_xia": "U+17D32 / Li Fanwen dictionary no. 0071",
            "mongolian_dali": "ᠳᠠᠯᠢ; HarfBuzz-shaped Noto Sans Mongolian fixed mask",
            "manchu_helan": "ᡥᡝᠯᠠᠨ; phonetic Helan rendering shaped with HarfBuzz, framed after vanilla MJZ/MHX flags",
            "liao": "B57 Khitan Large Script U+E23D / ninefold-seal U+F012 asset",
            "ongud_cross": "Yuan-period Inner Mongolian Church of the East epitaphs with cross-on-lotus imagery",
            "dunhuang_banner": "British Museum 1919,0101,0.120; 9th-century Cave 17 silk banner construction",
            "nanzhao": "899 Nanzhao Tuzhuan; Acuoye Guanyin as dynastic foundation image",
            "yi_wordmarks": "ꆀꃅ (Nimu, vernacular Liangshan) and ꑳꆅ (Yi-na, researched Yelang reading); fixed Noto Sans Yi masks",
        },
        "flags": DESIGNS,
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if check:
        stream = io.BytesIO()
        sheet.save(stream, format="PNG")
        if not sheet_target.exists() or sheet_target.read_bytes() != stream.getvalue():
            raise ValueError("B62 contact sheet is stale")
        if not manifest_target.exists() or manifest_target.read_bytes() != manifest_bytes:
            raise ValueError("B62 manifest is stale")
    else:
        sheet.save(sheet_target)
        manifest_target.write_bytes(manifest_bytes)
    print(f"{'checked' if check else 'generated'} {len(DESIGNS)} frontier flags")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
