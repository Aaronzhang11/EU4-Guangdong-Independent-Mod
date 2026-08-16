#!/usr/bin/env python3
"""Apply the user-confirmed B43 1444 polity map without changing province geometry.

Hard constraints:
- B51 invests a Khitan Liao state in the six-province Liaodong area, while
  Ningyuan and Yongping remain with WUZ and GUZ respectively.
- QIC keeps its already assigned provinces exactly.
- DAE uses Daizhou (5244) as its capital.
- Jiarong uses JRG and owns Ngawa (5091) and Barkam (5089).
- Huzhou (4950) belongs to YUE; the B50 eastern balance partition creates
  Huai, Ou and the Yang/Wu/Zhou commercial city-states without map changes.
- Badi uses the conflict-free tag BD2; legacy BAS data is removed.
- B52 restores E, Quan and Zhou as small Chu vassals, with Chu seated at
  Jiangling and retaining its main river corridor.
- CHC, MIN and WUU use exact core sets, with explicit YUE/XU2 cleanup.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
PROVINCE_HISTORY = MOD / "history/provinces"
COUNTRY_HISTORY = MOD / "history/countries"
COUNTRIES = MOD / "common/countries"
FLAGS = MOD / "gfx/flags"
REPORT_DIR = ROOT / "planning/chunqiu_polities_b43"
DEFAULT_VANILLA_ROOT = Path(
    r"E:/Program Files (x86)/Steam/steamapps/common/Europa Universalis IV"
)
MIN_ADJACENT_COLOR_DELTA_E = 12.0


TAG_PROVINCES = {
    "LSH": (5095, 2748, 5094, 5232),
    "MDL": (5226, 2167, 661, 5229, 5227),
    "NZA": (5235, 2165, 5237, 5228),
    "CHC": (4994, 4992, 4982, 5014, 2172, 5345, 5012, 4197, 5011, 5320),
    "JJG": (4979,),
    "HYA": (4981,),
    "EGU": (682, 5016),
    "QVN": (5010, 5343),
    "ZHU": (5015, 5344),
    "QSH": (686, 5065, 5067),
    "WUU": (2147, 2146, 5068, 1821, 5024, 2145, 5057, 5025, 1822, 5022, 5023),
    "YUE": (4956, 5003, 2149, 2148, 684, 4976, 5002, 4950, 5005, 5006, 2150),
    "MIN": (669, 1829, 4952, 4953, 4958, 5097, 5098, 2152, 5096, 5099),
    "OUE": (1824, 4951, 5007),
    "ZHO": (5004,),
    "WHU": (5066,),
    "HYM": (685, 5021, 4977),
    "CCH": (5061, 5062),
    "BAA": (5026, 5082, 680, 4213, 2168, 2169, 5330, 5334, 5335),
    "BD2": (5013, 5028),
    "CSA": (671, 4998, 5321, 4997, 5322),
    "WLM": (4996, 5312, 5313, 5316, 5317),
    "CDE": (672,),
    "BMY": (2170, 5087, 5086, 5090),
    "DZH": (5088, 5289),
    "XU2": (2141, 5018, 4196, 2142, 5020),
    "HUA": (2143, 5059, 1838, 5063, 5064, 5056),
    "LUU": (5112, 5109, 5108, 2140),
    "SNG": (5110, 5058, 2176, 5050),
    "CAG": (5111, 5031),
    "CAI": (5054, 5349),
    "CHN": (2144, 5051),
    "GUN": (2137, 4966),
    "CZH": (688, 5053, 5046, 1836),
    "SUI": (2175, 5350, 5009),
    "LUO": (2171, 5342),
    "GON": (687, 5347, 5055, 5348),
    "ZSH": (2136, 696, 5218),
    "ZHA": (5246, 5247, 693, 5248, 5251, 5245, 5255, 5220, 5221, 5048),
    "WEI": (4195, 5219, 2178, 5252, 694, 5256, 5249, 5253, 5254, 5269),
    "DAE": (702, 2177, 697, 5243, 5244, 5242),
    "YOU": (701, 5266, 5265, 5267, 2179, 5268),
    "ZNG": (5273, 5272),
    "JUU": (689, 5274, 5081, 5329),
    "DQU": (5332, 4211, 5333, 4987, 5339),
    "ZHI": (5027, 5336, 5337, 5338, 5340),
    "WDU": (5309, 5308),
    "DCH": (5290, 5092),
    "QIN": (5307, 5306, 5305, 5291, 2180, 2181, 5278, 4198, 5271, 5283, 700, 5285, 5270),
    "WGS": (2191, 4676, 708, 5295, 2182, 5292, 5288, 5286, 5287, 5277, 5276, 4223, 698, 709),
    "GZH": (5296, 707, 5297),
    "SHZ": (5300, 5299, 2122),
    "HZH": (2184, 5293, 699, 2183),
    "SHU": (5080, 5078, 5085, 5083, 5077, 4212, 5084, 5079, 5076, 679, 5075, 5331),
    "YPG": (5294,),
    "QWO": (5250,),
    "WVG": (5047, 5049),
    "GUO": (5052, 5045),
    "LIU": (5060,),
    "WXG": (5275,),
    "KSD": (4204, 706, 711, 2123, 4693),
    "AMD": (2134, 705),
    "KAM": (2133, 2135, 2131, 2132, 5093, 678, 5224, 5225),
    "JRG": (5091, 5089),
    "TSF": (4993, 5326),
    "ZHG": (4967,),
    "SHE": (5030, 5008, 5341, 681, 5346, 5284),
    "GUZ": (4194, 5211),
    "WUZ": (704, 5209),
    "YAN": (703, 1816, 5113, 5114, 5115, 5116, 5212, 5213, 4672, 5206, 5207),
    "LIO": (726, 5204, 5205, 2112, 4652, 2113),
}


# Low-saturation palette approved from the real-boundary political-map preview.
# Reused vanilla tags retain their original hue families, while every other
# country uses a restrained gray-toned color chosen against its actual map
# neighbors.
MUTED_COUNTRY_COLORS = {
    "AMD": (115, 118, 158),
    "BAA": (109, 150, 116),
    "BD2": (101, 132, 157),
    "BMY": (113, 149, 141),
    "CAG": (176, 130, 103),
    "CAI": (115, 118, 158),
    "CCH": (116, 150, 163),
    "CHC": (231, 176, 194),
    "CDE": (116, 67, 111),
    "CHN": (135, 121, 103),
    "CSA": (113, 149, 141),
    "CZC": (139, 113, 153),
    "CZH": (190, 192, 141),
    "CZM": (128, 149, 109),
    "DAE": (137, 104, 158),
    "DCH": (128, 149, 109),
    "DQU": (74, 150, 105),
    "DIA": (126, 130, 159),
    "DZH": (145, 120, 142),
    "EGU": (72, 129, 122),
    "GDD": (190, 72, 72),
    "GON": (115, 118, 158),
    "GUI": (65, 120, 158),
    "GUN": (232, 232, 220),
    "GUZ": (35, 37, 40),
    "GUO": (96, 143, 139),
    "GYA": (48, 76, 120),
    "GZH": (133, 148, 154),
    "HAK": (181, 151, 101),
    "HZH": (166, 116, 120),
    "HNG": (93, 117, 160),
    "HUA": (67, 112, 100),
    "HYM": (72, 143, 160),
    "HYA": (48, 77, 135),
    "JRG": (176, 130, 103),
    "JJG": (164, 82, 43),
    "JUU": (139, 113, 153),
    "KAM": (64, 146, 106),
    "KSD": (209, 120, 83),
    "LCH": (193, 166, 82),
    "LIL": (156, 204, 158),
    "LIO": (184, 151, 72),
    "LIU": (245, 245, 230),
    "LSH": (108, 137, 124),
    "LUO": (108, 137, 124),
    "LUU": (82, 130, 172),
    "MDL": (245, 245, 220),
    "MIN": (203, 223, 205),
    "NCH": (82, 136, 174),
    "NUN": (109, 150, 116),
    "NZA": (109, 150, 116),
    "OUE": (174, 101, 74),
    "QIC": (83, 149, 116),
    "QIN": (38, 42, 46),
    "QSH": (157, 113, 137),
    "QWO": (196, 166, 74),
    "QVN": (178, 138, 75),
    "SHE": (166, 116, 120),
    "SHU": (145, 64, 81),
    "SHZ": (139, 113, 153),
    "SNG": (157, 113, 137),
    "SUI": (159, 129, 111),
    "TSF": (171, 136, 146),
    "TZZ": (184, 213, 228),
    "WDU": (176, 130, 103),
    "WEI": (176, 130, 103),
    "WGS": (150, 156, 104),
    "WLM": (159, 129, 111),
    "WUU": (133, 111, 175),
    "WHU": (202, 151, 70),
    "WVG": (109, 150, 116),
    "WXG": (96, 143, 139),
    "WXM": (139, 113, 153),
    "XU2": (150, 156, 104),
    "WUZ": (103, 137, 166),
    "YAN": (201, 68, 54),
    "YEL": (178, 142, 117),
    "ZHO": (183, 168, 75),
    "YOU": (157, 113, 137),
    "YPG": (126, 130, 159),
    "YUE": (116, 130, 194),
    "ZHA": (116, 150, 163),
    "ZHG": (96, 143, 139),
    "ZNG": (181, 151, 101),
    "ZSH": (74, 122, 168),
    "ZHI": (161, 86, 151),
    "ZHU": (130, 96, 142),
}


POLITIES = {
    "LSH": {"file": "B43_Liangshan.txt", "history": "LSH - Liangshan.txt", "capital": 2748, "rank": 1, "color": MUTED_COUNTRY_COLORS["LSH"]},
    "MDL": {"file": "B43_Mongol_Dali.txt", "history": "MDL - Mongol Dali.txt", "capital": 661, "rank": 1, "color": MUTED_COUNTRY_COLORS["MDL"]},
    "NZA": {"file": "B43_Nanzhao.txt", "history": "NZA - Nanzhao.txt", "capital": 5235, "rank": 1, "color": MUTED_COUNTRY_COLORS["NZA"]},
    "QSH": {"file": "B43_Qunshu.txt", "history": "QSH - Qunshu.txt", "capital": 686, "rank": 1, "color": MUTED_COUNTRY_COLORS["QSH"]},
    "JJG": {"file": "B54_Jiujiang.txt", "history": "JJG - Jiujiang.txt", "capital": 4979, "rank": 1, "color": MUTED_COUNTRY_COLORS["JJG"], "government": "republic", "reform": "oligarchy_reform"},
    "HYA": {"file": "B54_Hanyang.txt", "history": "HYA - Hanyang.txt", "capital": 4981, "rank": 1, "color": MUTED_COUNTRY_COLORS["HYA"], "government": "republic", "reform": "oligarchy_reform"},
    "EGU": {"file": "B52_E.txt", "history": "EGU - E.txt", "capital": 682, "rank": 1, "color": MUTED_COUNTRY_COLORS["EGU"]},
    "QVN": {"file": "B52_Quan.txt", "history": "QVN - Quan.txt", "capital": 5343, "rank": 1, "color": MUTED_COUNTRY_COLORS["QVN"]},
    "ZHU": {"file": "B52_Zhou.txt", "history": "ZHU - Zhou.txt", "capital": 5344, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZHU"]},
    "LIO": {"file": "B51_Liao.txt", "history": "LIO - Liao.txt", "capital": 5204, "rank": 1, "color": MUTED_COUNTRY_COLORS["LIO"], "culture": "mongol", "accepted": ("manchu", "gdd_qi")},
    "HUA": {"file": "B50_Huai.txt", "history": "HUA - Huai.txt", "capital": 5059, "rank": 1, "color": MUTED_COUNTRY_COLORS["HUA"]},
    "OUE": {"file": "B50_Ou.txt", "history": "OUE - Ou.txt", "capital": 1824, "rank": 1, "color": MUTED_COUNTRY_COLORS["OUE"]},
    "HYM": {"file": "B50_Yang.txt", "history": "HYM - Yang.txt", "capital": 685, "rank": 1, "color": MUTED_COUNTRY_COLORS["HYM"], "government": "republic", "reform": "oligarchy_reform"},
    "WHU": {"file": "B50_Wuhu.txt", "history": "WHU - Wuhu.txt", "capital": 5066, "rank": 1, "color": MUTED_COUNTRY_COLORS["WHU"], "government": "republic", "reform": "oligarchy_reform"},
    "ZHO": {"file": "B50_Zhou.txt", "history": "ZHO - Zhou.txt", "capital": 5004, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZHO"], "government": "republic", "reform": "oligarchy_reform"},
    "CCH": {"file": "B43_Chao.txt", "history": "CCH - Chao.txt", "capital": 5061, "rank": 1, "color": MUTED_COUNTRY_COLORS["CCH"]},
    "BAA": {"file": "B43_Ba.txt", "history": "BAA - Ba.txt", "capital": 680, "rank": 2, "color": MUTED_COUNTRY_COLORS["BAA"]},
    "BD2": {"file": "B43_Badi.txt", "history": "BD2 - Badi.txt", "capital": 5013, "rank": 1, "color": MUTED_COUNTRY_COLORS["BD2"]},
    "WLM": {"file": "B43_Wuling.txt", "history": "WLM - Wuling.txt", "capital": 4996, "rank": 1, "color": MUTED_COUNTRY_COLORS["WLM"]},
    "CDE": {"file": "B54_Changde.txt", "history": "CDE - Changde.txt", "capital": 672, "rank": 1, "color": MUTED_COUNTRY_COLORS["CDE"], "government": "republic", "reform": "oligarchy_reform"},
    "BMY": {"file": "B43_Baima_Miyao.txt", "history": "BMY - Baima Miyao.txt", "capital": 5086, "rank": 1, "color": MUTED_COUNTRY_COLORS["BMY"]},
    "DZH": {"file": "B43_Dengzhi.txt", "history": "DZH - Dengzhi.txt", "capital": 5088, "rank": 1, "color": MUTED_COUNTRY_COLORS["DZH"]},
    "DQU": {"file": "B46_Dangqu.txt", "history": "DQU - Dangqu.txt", "capital": 5333, "rank": 1, "color": MUTED_COUNTRY_COLORS["DQU"], "accepted": ("gdd_diqiang",)},
    "ZHI": {"file": "B46_Zhi.txt", "history": "ZHI - Zhi.txt", "capital": 5027, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZHI"], "accepted": ("gdd_shu",)},
    "LUU": {"file": "B43_Lu.txt", "history": "LUU - Lu.txt", "capital": 5109, "rank": 1, "color": MUTED_COUNTRY_COLORS["LUU"]},
    "CAG": {"file": "B43_Cao.txt", "history": "CAG - Cao.txt", "capital": 5111, "rank": 1, "color": MUTED_COUNTRY_COLORS["CAG"]},
    "CAI": {"file": "B43_Cai.txt", "history": "CAI - Cai.txt", "capital": 5054, "rank": 1, "color": MUTED_COUNTRY_COLORS["CAI"]},
    "CHN": {"file": "B43_Chen.txt", "history": "CHN - Chen.txt", "capital": 5051, "rank": 1, "color": MUTED_COUNTRY_COLORS["CHN"]},
    "GUN": {"file": "B43_Guan.txt", "history": "GUN - Guan.txt", "capital": 2137, "rank": 1, "color": MUTED_COUNTRY_COLORS["GUN"]},
    "SUI": {"file": "B43_Sui.txt", "history": "SUI - Sui.txt", "capital": 5009, "rank": 1, "color": MUTED_COUNTRY_COLORS["SUI"]},
    "LUO": {"file": "B43_Luo.txt", "history": "LUO - Luo.txt", "capital": 2171, "rank": 1, "color": MUTED_COUNTRY_COLORS["LUO"]},
    "GON": {"file": "B43_Gong.txt", "history": "GON - Gong.txt", "capital": 687, "rank": 1, "color": MUTED_COUNTRY_COLORS["GON"]},
    "ZSH": {"file": "B43_Zhongshan.txt", "history": "ZSH - Zhongshan.txt", "capital": 696, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZSH"]},
    "ZHA": {"file": "B43_Zhao.txt", "history": "ZHA - Zhao.txt", "capital": 693, "rank": 2, "color": MUTED_COUNTRY_COLORS["ZHA"]},
    "WEI": {"file": "B43_Wei.txt", "history": "WEI - Wei.txt", "capital": 4195, "rank": 2, "color": MUTED_COUNTRY_COLORS["WEI"]},
    "DAE": {"file": "B43_Dai.txt", "history": "DAE - Dai.txt", "capital": 5244, "rank": 1, "color": MUTED_COUNTRY_COLORS["DAE"]},
    "YOU": {"file": "B43_Yiqu.txt", "history": "YOU - Yiqu.txt", "capital": 2179, "rank": 1, "color": MUTED_COUNTRY_COLORS["YOU"]},
    "ZNG": {"file": "B43_Zheng.txt", "history": "ZNG - Zheng.txt", "capital": 5273, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZNG"]},
    "JUU": {"file": "B43_Ju.txt", "history": "JUU - Ju.txt", "capital": 689, "rank": 1, "color": MUTED_COUNTRY_COLORS["JUU"]},
    "WDU": {"file": "B43_Wudu.txt", "history": "WDU - Wudu.txt", "capital": 5309, "rank": 1, "color": MUTED_COUNTRY_COLORS["WDU"]},
    "DCH": {"file": "B43_Dangchang.txt", "history": "DCH - Dangchang.txt", "capital": 5290, "rank": 1, "color": MUTED_COUNTRY_COLORS["DCH"]},
    "WGS": {"file": "B43_Wanggu_Russia.txt", "history": "WGS - Wanggu Russia.txt", "capital": 4223, "rank": 2, "color": MUTED_COUNTRY_COLORS["WGS"]},
    "GZH": {"file": "B43_Ganzhou.txt", "history": "GZH - Ganzhou.txt", "capital": 5296, "rank": 1, "color": MUTED_COUNTRY_COLORS["GZH"]},
    "SHZ": {"file": "B43_Shazhou.txt", "history": "SHZ - Shazhou.txt", "capital": 5300, "rank": 1, "color": MUTED_COUNTRY_COLORS["SHZ"]},
    "HZH": {"file": "B43_Hezhou_Huihui.txt", "history": "HZH - Hezhou Huihui.txt", "capital": 5293, "rank": 1, "color": MUTED_COUNTRY_COLORS["HZH"]},
    "YPG": {"file": "B43_Yinping.txt", "history": "YPG - Yinping.txt", "capital": 5294, "rank": 1, "color": MUTED_COUNTRY_COLORS["YPG"]},
    "QWO": {"file": "B43_Quwo.txt", "history": "QWO - Quwo.txt", "capital": 5250, "rank": 1, "color": MUTED_COUNTRY_COLORS["QWO"]},
    "WVG": {"file": "B43_Wei_State.txt", "history": "WVG - Wei State.txt", "capital": 5047, "rank": 1, "color": MUTED_COUNTRY_COLORS["WVG"]},
    "GUO": {"file": "B43_Guo.txt", "history": "GUO - Guo.txt", "capital": 5052, "rank": 1, "color": MUTED_COUNTRY_COLORS["GUO"]},
    "LIU": {"file": "B43_Liu.txt", "history": "LIU - Liu.txt", "capital": 5060, "rank": 1, "color": MUTED_COUNTRY_COLORS["LIU"]},
    "WXG": {"file": "B43_Wuxing.txt", "history": "WXG - Wuxing.txt", "capital": 5275, "rank": 1, "color": MUTED_COUNTRY_COLORS["WXG"]},
    "AMD": {"file": "B43_Amdo_Golog.txt", "history": "AMD - Amdo Golog.txt", "capital": 2134, "rank": 1, "color": MUTED_COUNTRY_COLORS["AMD"]},
    "JRG": {"file": "B43_Jiarong.txt", "history": "JRG - Jiarong.txt", "capital": 5091, "rank": 1, "color": MUTED_COUNTRY_COLORS["JRG"]},
    "TSF": {"file": "B43_Tianshi_Fu.txt", "history": "TSF - Tianshi Fu.txt", "capital": 4993, "rank": 1, "color": MUTED_COUNTRY_COLORS["TSF"]},
    "ZHG": {"file": "B43_Zhougong.txt", "history": "ZHG - Zhougong.txt", "capital": 4967, "rank": 1, "color": MUTED_COUNTRY_COLORS["ZHG"]},
    "SHE": {"file": "B43_Shen.txt", "history": "SHE - Shen.txt", "capital": 5030, "rank": 1, "color": MUTED_COUNTRY_COLORS["SHE"]},
    "GUZ": {"file": "B43_Guzhu.txt", "history": "GUZ - Guzhu.txt", "capital": 4194, "rank": 1, "color": MUTED_COUNTRY_COLORS["GUZ"]},
    "WUZ": {"file": "B43_Wuzhong.txt", "history": "WUZ - Wuzhong.txt", "capital": 704, "rank": 1, "color": MUTED_COUNTRY_COLORS["WUZ"]},
}


BORROWED_CAPITALS = {
    "WUU": {"history": "WUU - Wu.txt", "capital": 1821, "rank": 2},
    "YUE": {"history": "YUE - Yue.txt", "capital": 684, "rank": 2},
    "QIN": {"history": "QIN - Qin.txt", "capital": 700, "rank": 2},
    "SHU": {"history": "SHU - Shu.txt", "capital": 679, "rank": 2},
    "KSD": {"history": "KSD - Khoshuud.txt", "capital": 4204, "rank": 2},
    "KAM": {"history": "KAM - Mdo Khams.txt", "capital": 2133, "rank": 2},
}

# Existing and borrowed tags also need explicit mod definitions, otherwise
# their vanilla colors can collide with the generated B43 countries.
EXISTING_COUNTRY_COLORS = {
    "CHC": {"file": "Chu.txt", "color": MUTED_COUNTRY_COLORS["CHC"]},
    "CZH": {"file": "Zhou.txt", "color": MUTED_COUNTRY_COLORS["CZH"]},
    "MIN": {"file": "Min.txt", "color": MUTED_COUNTRY_COLORS["MIN"]},
    "QIC": {"file": "Qi.txt", "color": MUTED_COUNTRY_COLORS["QIC"]},
    "YAN": {"file": "Yan.txt", "color": MUTED_COUNTRY_COLORS["YAN"]},
    "QIN": {"file": "Qin.txt", "color": MUTED_COUNTRY_COLORS["QIN"]},
    "SHU": {"file": "Shu.txt", "color": MUTED_COUNTRY_COLORS["SHU"]},
    "SNG": {"file": "SNG.txt", "color": MUTED_COUNTRY_COLORS["SNG"]},
    "WUU": {"file": "Wu.txt", "color": MUTED_COUNTRY_COLORS["WUU"]},
    "XU2": {"file": "Xu2.txt", "color": MUTED_COUNTRY_COLORS["XU2"]},
    "YUE": {"file": "Yue.txt", "color": MUTED_COUNTRY_COLORS["YUE"]},
    "KAM": {"file": "Mdokhams.txt", "color": MUTED_COUNTRY_COLORS["KAM"]},
    "KSD": {"file": "Khoshuud.txt", "color": MUTED_COUNTRY_COLORS["KSD"]},
    "GDD": {"file": "Guangdong.txt", "color": MUTED_COUNTRY_COLORS["GDD"]},
    "LIL": {"file": "Liliao.txt", "color": MUTED_COUNTRY_COLORS["LIL"]},
    "NUN": {"file": "Nong.txt", "color": MUTED_COUNTRY_COLORS["NUN"]},
    "HAK": {"file": "Hakka.txt", "color": MUTED_COUNTRY_COLORS["HAK"]},
    "GUI": {"file": "Guilin.txt", "color": MUTED_COUNTRY_COLORS["GUI"]},
    "CSA": {"file": "Changsha.txt", "color": MUTED_COUNTRY_COLORS["CSA"]},
    "TZZ": {"file": "Tianzhou.txt", "color": MUTED_COUNTRY_COLORS["TZZ"]},
    "DIA": {"file": "Dian.txt", "color": MUTED_COUNTRY_COLORS["DIA"]},
    "YEL": {"file": "Yelang.txt", "color": MUTED_COUNTRY_COLORS["YEL"]},
    "WXM": {"file": "Wuxi_Miao.txt", "color": MUTED_COUNTRY_COLORS["WXM"]},
    "CZM": {"file": "Chenzhou_Miao.txt", "color": MUTED_COUNTRY_COLORS["CZM"]},
    "LCH": {"file": "Linchuan.txt", "color": MUTED_COUNTRY_COLORS["LCH"]},
    "NCH": {"file": "Nanchang.txt", "color": MUTED_COUNTRY_COLORS["NCH"]},
    "GYA": {"file": "Guiyang.txt", "color": MUTED_COUNTRY_COLORS["GYA"]},
    "CZC": {"file": "Chaozhou.txt", "color": MUTED_COUNTRY_COLORS["CZC"]},
    "HNG": {"file": "B45_Heng.txt", "color": MUTED_COUNTRY_COLORS["HNG"]},
}

RESET_OWNERS: dict[int, str] = {
    2154: "MNG",  # Tamsui
}

# User-confirmed core cleanup. Major and B50 eastern tags retain cores only
# on their intended opening territory.
EXACT_CORE_TAGS = {
    "CHC": set(TAG_PROVINCES["CHC"]),
    "JJG": set(TAG_PROVINCES["JJG"]),
    "HYA": set(TAG_PROVINCES["HYA"]),
    "CSA": set(TAG_PROVINCES["CSA"]),
    "CDE": set(TAG_PROVINCES["CDE"]),
    "WLM": set(TAG_PROVINCES["WLM"]),
    "EGU": set(TAG_PROVINCES["EGU"]),
    "QVN": set(TAG_PROVINCES["QVN"]),
    "ZHU": set(TAG_PROVINCES["ZHU"]),
    "MIN": set(TAG_PROVINCES["MIN"]),
    "SHU": set(TAG_PROVINCES["SHU"]),
    "WUU": set(TAG_PROVINCES["WUU"]),
    "YUE": set(TAG_PROVINCES["YUE"]),
    # Yingzhou (2144) keeps the previously reviewed historical XU2 core.
    "XU2": set(TAG_PROVINCES["XU2"]) | {2144},
    "HUA": set(TAG_PROVINCES["HUA"]),
    "OUE": set(TAG_PROVINCES["OUE"]),
    "HYM": set(TAG_PROVINCES["HYM"]),
    "WHU": set(TAG_PROVINCES["WHU"]),
    "ZHO": set(TAG_PROVINCES["ZHO"]),
    "KAM": set(TAG_PROVINCES["KAM"]),
    "KSD": set(TAG_PROVINCES["KSD"]),
    "YAN": set(TAG_PROVINCES["YAN"]),
    "LIO": set(TAG_PROVINCES["LIO"]),
    "DQU": set(TAG_PROVINCES["DQU"]),
    "ZHI": set(TAG_PROVINCES["ZHI"]),
}

# B54 public cities are fully sovereign one-province republics.  Their
# capitals start with no foreign core, so an older regional claim cannot turn
# the release into an immediate reconquest target.
EXCLUSIVE_CORE_OWNERS = {672: "CDE", 4979: "JJG", 4981: "HYA"}

FORCED_CORE_REMOVALS = {
    "YUE": {
        665, 667, 668,
        2157, 2159,
        4942, 4943, 4945, 4946, 4947, 4949,
        5214, 5215,
    },
    "XU2": {4977, 5022, 5023, 1821},
    "BAS": {5013, 5028},
    "HMI": {707, 2122, 5299, 5300},
    "QIN": {689, 2179},
    "WVG": {5048, 5270},
    "MNG": {663, 666, 2162, 2164, 4949, 5217, 5303},
}

LEGACY_COUNTRY_ARTIFACTS = (
    COUNTRIES / "B43_Bashi.txt",
    COUNTRY_HISTORY / "BAS - Bashi.txt",
    FLAGS / "BAS.tga",
    COUNTRIES / "B43_Shen_Han_Mian.txt",
    COUNTRY_HISTORY / "SH2 - Shen Han Mian.txt",
    FLAGS / "SH2.tga",
)

PRESERVED_OWNERSHIP = {
    "QIC": {690, 691, 695, 2138, 2139, 5101, 5102, 5103, 5104, 5105, 5106, 5107, 5222, 5223},
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def initial_section(text: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return (text[:match.start()], text[match.start():]) if match else (text, "")


def initial_value(text: str, key: str) -> str:
    initial, _dated = initial_section(text)
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\s#]+)", initial)
    if not match:
        raise ValueError(f"Missing initial {key}")
    return match.group(1)


def apply_owner(text: str, owner: str) -> str:
    initial, dated = initial_section(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    missing_keys: list[str] = []
    for key in ("owner", "controller"):
        initial, count = re.subn(
            rf"(?m)^(\s*{key}\s*=\s*)\S+\s*$",
            rf"\g<1>{owner}",
            initial,
            count=1,
        )
        if count == 0:
            missing_keys.append(key)
    if missing_keys:
        assignments = "".join(f"{key} = {owner}{newline}" for key in missing_keys)
        initial = assignments + initial
    cores = re.findall(r"(?m)^\s*add_core\s*=\s*(\S+)", initial)
    if owner not in cores:
        marker = re.search(r"(?m)^\s*controller\s*=\s*\S+\s*$", initial)
        if not marker:
            raise ValueError("Missing controller insertion point")
        initial = initial[:marker.end()] + f"{newline}add_core = {owner}" + initial[marker.end():]
    return initial + dated


def province_id_from_path(path: Path) -> int | None:
    match = re.match(r"(\d+)\s*-", path.name)
    return int(match.group(1)) if match else None


def initial_cores(text: str) -> set[str]:
    initial, _dated = initial_section(text)
    return set(re.findall(r"(?m)^\s*add_core\s*=\s*(\S+)", initial))


def country_rgb(path: Path) -> tuple[int, int, int]:
    match = re.search(
        rb"(?m)^\s*color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}\s*$",
        path.read_bytes(),
    )
    if not match:
        raise ValueError(f"{path.name}: missing country color")
    return tuple(int(channel) for channel in match.groups())


def color_lab(color: tuple[int, int, int]) -> np.ndarray:
    rgb = np.asarray(color, dtype=np.float64) / 255.0
    linear = np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        ((rgb + 0.055) / 1.055) ** 2.4,
    )
    xyz = np.asarray(
        (
            (0.4124564, 0.3575761, 0.1804375),
            (0.2126729, 0.7151522, 0.0721750),
            (0.0193339, 0.1191920, 0.9503041),
        )
    ) @ linear
    xyz /= np.asarray((0.95047, 1.0, 1.08883))
    epsilon = 216 / 24389
    kappa = 24389 / 27
    transformed = np.where(
        xyz > epsilon,
        xyz ** (1 / 3),
        (kappa * xyz + 16) / 116,
    )
    return np.asarray(
        (
            116 * transformed[1] - 16,
            500 * (transformed[0] - transformed[1]),
            200 * (transformed[1] - transformed[2]),
        )
    )


def assigned_owner(province_id: int, vanilla_root: Path) -> str | None:
    for tag, provinces in TAG_PROVINCES.items():
        if province_id in provinces:
            return tag
    for tag, provinces in PRESERVED_OWNERSHIP.items():
        if province_id in provinces:
            return tag
    if province_id in RESET_OWNERS:
        return RESET_OWNERS[province_id]
    for history_root in (
        PROVINCE_HISTORY,
        vanilla_root / "history/provinces",
    ):
        owners: set[str] = set()
        for path in sorted(history_root.glob(f"{province_id} - *.txt")):
            try:
                owners.add(initial_value(read_text(path), "owner"))
            except ValueError:
                pass
        if owners:
            return sorted(owners)[0]
    return None


def country_color_path(tag: str, vanilla_root: Path) -> Path | None:
    tag_map: dict[str, str] = {}
    for base in (vanilla_root / "common/country_tags", MOD / "common/country_tags"):
        for path in sorted(base.glob("*.txt")):
            tag_map.update(
                re.findall(
                    r'(?m)^\s*([A-Z0-9]{3})\s*=\s*"([^"]+)"',
                    read_text(path),
                )
            )
    relative = tag_map.get(tag)
    if not relative:
        return None
    mod_path = MOD / "common" / relative
    vanilla_path = vanilla_root / "common" / relative
    if mod_path.exists():
        return mod_path
    return vanilla_path if vanilla_path.exists() else None


def validate_adjacent_colors(vanilla_root: Path) -> dict[str, object]:
    definition: dict[int, int] = {}
    with (MOD / "map/definition.csv").open(
        encoding="cp1252", errors="replace", newline=""
    ) as handle:
        for row in handle:
            columns = row.split(";")
            if columns and columns[0].isdigit():
                province_id = int(columns[0])
                packed = (
                    (int(columns[1]) << 16)
                    | (int(columns[2]) << 8)
                    | int(columns[3])
                )
                definition[packed] = province_id
    image = np.asarray(Image.open(MOD / "map/provinces.bmp").convert("RGB"))
    packed = (
        (image[:, :, 0].astype(np.uint32) << 16)
        | (image[:, :, 1].astype(np.uint32) << 8)
        | image[:, :, 2].astype(np.uint32)
    )
    province_edges: set[tuple[int, int]] = set()
    for left, right in (
        (packed[:, :-1], packed[:, 1:]),
        (packed[:-1], packed[1:]),
    ):
        changed = left != right
        pairs = np.stack((left[changed], right[changed]), axis=1)
        pairs.sort(axis=1)
        for first, second in np.unique(pairs, axis=0):
            a = definition.get(int(first))
            b = definition.get(int(second))
            if a is not None and b is not None and a != b:
                province_edges.add((min(a, b), max(a, b)))
    relevant_tags = set(TAG_PROVINCES)
    country_edges: set[tuple[str, str]] = set()
    for a, b in province_edges:
        owner_a = assigned_owner(a, vanilla_root)
        owner_b = assigned_owner(b, vanilla_root)
        if (
            owner_a
            and owner_b
            and owner_a != owner_b
            and (owner_a in relevant_tags or owner_b in relevant_tags)
        ):
            country_edges.add(tuple(sorted((owner_a, owner_b))))
    colors: dict[str, tuple[int, int, int]] = {}
    labs: dict[str, np.ndarray] = {}
    for tag in {tag for edge in country_edges for tag in edge}:
        path = country_color_path(tag, vanilla_root)
        if path is None:
            raise ValueError(f"{tag}: no country definition for color audit")
        colors[tag] = country_rgb(path)
        labs[tag] = color_lab(colors[tag])
    distances = {
        edge: float(np.linalg.norm(labs[edge[0]] - labs[edge[1]]))
        for edge in country_edges
    }
    minimum = min(distances.values())
    if minimum < MIN_ADJACENT_COLOR_DELTA_E:
        conflicts = sorted(
            (distance, edge)
            for edge, distance in distances.items()
            if distance < MIN_ADJACENT_COLOR_DELTA_E
        )
        details = ", ".join(
            f"{edge[0]}-{edge[1]}={distance:.1f}"
            for distance, edge in conflicts[:20]
        )
        raise ValueError(
            f"Adjacent colors are too similar: {details}"
        )
    closest_edges = sorted(
        (
            {"tags": list(edge), "delta_e": round(distance, 1)}
            for edge, distance in distances.items()
        ),
        key=lambda item: item["delta_e"],
    )[:10]
    return {
        "country_edge_count": len(country_edges),
        "minimum_required_delta_e": MIN_ADJACENT_COLOR_DELTA_E,
        "minimum_delta_e": round(minimum, 1),
        "closest_edges": closest_edges,
    }


def should_remove_core(tag: str, province_id: int) -> bool:
    if province_id in EXCLUSIVE_CORE_OWNERS and tag != EXCLUSIVE_CORE_OWNERS[province_id]:
        return True
    if tag == "MNG" and any(
        province_id in provinces for provinces in TAG_PROVINCES.values()
    ):
        return True
    if tag in EXACT_CORE_TAGS and province_id not in EXACT_CORE_TAGS[tag]:
        return True
    return province_id in FORCED_CORE_REMOVALS.get(tag, set())


def remove_initial_core(text: str, tag: str) -> str:
    initial, dated = initial_section(text)
    initial = re.sub(
        rf"(?m)^\s*add_core\s*=\s*{re.escape(tag)}\s*\r?\n?",
        "",
        initial,
    )
    return initial + dated


def ensure_core_override_files(vanilla_root: Path, write: bool) -> list[Path]:
    """Override vanilla filenames whose inherited cores must be removed.

    EU4 loads province history by filename. Some refined mod histories use a
    corrected spelling, so the vanilla filename also needs an override or its
    old add_core line can remain active alongside the mod history.
    """
    created: list[Path] = []
    vanilla_history = vanilla_root / "history/provinces"
    for vanilla_path in vanilla_history.glob("*.txt"):
        province_id = province_id_from_path(vanilla_path)
        if province_id is None:
            continue
        cores = initial_cores(read_text(vanilla_path))
        if not any(should_remove_core(tag, province_id) for tag in cores):
            continue
        target = PROVINCE_HISTORY / vanilla_path.name
        if target.exists():
            continue
        if not write:
            raise ValueError(
                f"{vanilla_path.name}: missing exact-name override for core cleanup"
            )
        alternatives = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
        seed = alternatives[0] if alternatives else vanilla_path
        target.write_text(read_text(seed), encoding="utf-8")
        created.append(target)
    return created


def ensure_province_history(province_id: int, vanilla_root: Path, write: bool) -> list[Path]:
    matches = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
    vanilla_matches = sorted((vanilla_root / "history/provinces").glob(f"{province_id} - *.txt"))
    if matches:
        missing_exact = [
            vanilla_path
            for vanilla_path in vanilla_matches
            if not (PROVINCE_HISTORY / vanilla_path.name).exists()
        ]
        if missing_exact and not write:
            missing_names = ", ".join(path.name for path in missing_exact)
            raise ValueError(
                f"Province {province_id}: missing exact vanilla filename override(s): {missing_names}"
            )
        for vanilla_path in missing_exact:
            target = PROVINCE_HISTORY / vanilla_path.name
            target.write_text(read_text(matches[0]), encoding="utf-8")
            matches.append(target)
        return sorted(matches)
    if len(vanilla_matches) != 1:
        raise ValueError(
            f"Province {province_id}: expected one vanilla history file, found {len(vanilla_matches)}"
        )
    target = PROVINCE_HISTORY / vanilla_matches[0].name
    if not write:
        raise ValueError(f"Province {province_id}: missing mod history override {target.name}")
    target.write_text(read_text(vanilla_matches[0]), encoding="utf-8")
    return [target]


def capital_attributes(capital: int, vanilla_root: Path) -> tuple[str, str]:
    paths = ensure_province_history(capital, vanilla_root, write=False)
    text = read_text(paths[0])
    return initial_value(text, "culture"), initial_value(text, "religion")


def country_definition(color: tuple[int, int, int]) -> str:
    red, green, blue = color
    return (
        "# B43 Chunqiu polity definition.\n"
        "graphical_culture = asiangfx\n\n"
        f"color = {{ {red} {green} {blue} }}\n"
        "revolutionary_colors = { 5 8 1 }\n"
    )


def replace_country_color(text: str, color: tuple[int, int, int]) -> str:
    red, green, blue = color
    replacement = f"color = {{ {red} {green} {blue} }}"
    new, count = re.subn(
        r"(?m)^\s*color\s*=\s*\{\s*\d+\s+\d+\s+\d+\s*\}\s*$",
        replacement,
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("Country definition is missing a color assignment")
    return new


def replace_country_color_bytes(data: bytes, color: tuple[int, int, int]) -> bytes:
    """Replace the ASCII color line without decoding legacy mixed-byte files."""
    red, green, blue = color
    replacement = f"color = {{ {red} {green} {blue} }}".encode("ascii")
    new, count = re.subn(
        rb"(?m)^\s*color\s*=\s*\{\s*\d+\s+\d+\s+\d+\s*\}\s*$",
        replacement,
        data,
        count=1,
    )
    if count != 1:
        raise ValueError("Country definition is missing a color assignment")
    return new


def country_history(
    capital: int,
    rank: int,
    culture: str,
    religion: str,
    accepted: tuple[str, ...] = (),
    government: str = "monarchy",
    reform: str = "gdd_local_fiefdom_reform",
) -> str:
    return (
        "# B43 Chunqiu polity history.\n"
        f"government = {government}\n"
        f"add_government_reform = {reform}\n"
        f"government_rank = {rank}\n"
        "technology_group = chinese\n"
        f"religion = {religion}\n"
        f"primary_culture = {culture}\n"
        + "".join(f"add_accepted_culture = {value}\n" for value in accepted)
        +
        f"capital = {capital}\n"
        f"fixed_capital = {capital}\n"
    )


def flag_bytes(color: tuple[int, int, int], width: int = 128, height: int = 128) -> bytes:
    red, green, blue = color
    light = tuple(min(255, channel + 52) for channel in color)
    dark = tuple(max(0, channel - 52) for channel in color)
    header = struct.pack(
        "<BBBHHBHHHHBB",
        0, 0, 2, 0, 0, 0, 0, 0, width, height, 24, 0x20,
    )
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            if abs(x - y) < 11:
                pixel = light
            elif abs((width - 1 - x) - y) < 9:
                pixel = dark
            else:
                pixel = (red, green, blue)
            pixels.extend((pixel[2], pixel[1], pixel[0]))
    return header + bytes(pixels)


def set_existing_country_capital(path: Path, capital: int, write: bool) -> bool:
    # Existing country histories can contain EU4 double-byte character data.
    # Patch ASCII keys at the byte level so ruler names are never transcoded.
    data = path.read_bytes()
    date_match = re.search(rb"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", data)
    if date_match:
        initial, dated = data[:date_match.start()], data[date_match.start():]
    else:
        initial, dated = data, b""
    initial, count = re.subn(
        rb"(?m)^([ \t]*capital[ \t]*=[ \t]*)\d+([^\r\n]*)(\r?)$",
        lambda match: (
            match.group(1)
            + str(capital).encode("ascii")
            + match.group(2)
            + match.group(3)
        ),
        initial,
        count=1,
    )
    if count != 1:
        raise ValueError(f"{path.name}: missing capital")
    if re.search(rb"(?m)^\s*fixed_capital\s*=", initial):
        initial = re.sub(
            rb"(?m)^(\s*fixed_capital\s*=\s*)\d+",
            lambda match: match.group(1) + str(capital).encode("ascii"),
            initial,
            count=1,
        )
    else:
        capital_line = re.search(rb"(?m)^\s*capital\s*=.*$", initial)
        initial = (
            initial[:capital_line.end()]
            + f"\nfixed_capital = {capital}".encode("ascii")
            + initial[capital_line.end():]
        )
    if capital == 2176:
        initial = initial.replace(b"#Beijing", b"#Shangqiu")
    if capital == 2141:
        initial = initial.replace(b"#Fengyang", b"#Xuzhou")
    if capital == 2172:
        initial = initial.replace(b"#Wuchang", b"#Jiangling")
    new = initial + dated
    changed = new != data
    if write and changed:
        path.write_bytes(new)
    return changed


def current_owned_ids(tag: str) -> set[int]:
    owned: set[int] = set()
    for path in PROVINCE_HISTORY.glob("*.txt"):
        match = re.match(r"(\d+)\s*-", path.name)
        if not match:
            continue
        try:
            owner = initial_value(read_text(path), "owner")
        except ValueError:
            continue
        if owner == tag:
            owned.add(int(match.group(1)))
    return owned


def current_core_ids(tag: str) -> set[int]:
    cores: set[int] = set()
    for path in PROVINCE_HISTORY.glob("*.txt"):
        province_id = province_id_from_path(path)
        if province_id is not None and tag in initial_cores(read_text(path)):
            cores.add(province_id)
    return cores


def validate(vanilla_root: Path, check_colors: bool = True) -> dict[str, object]:
    all_ids = [province_id for provinces in TAG_PROVINCES.values() for province_id in provinces]
    if len(all_ids) != 303 or len(set(all_ids)) != 303:
        raise ValueError("Expanded polity policy must contain 303 unique provinces after B54")
    ensure_core_override_files(vanilla_root, write=False)
    for tag, provinces in TAG_PROVINCES.items():
        for province_id in provinces:
            paths = ensure_province_history(province_id, vanilla_root, write=False)
            for path in paths:
                text = read_text(path)
                if initial_value(text, "owner") != tag:
                    raise ValueError(f"{path.name}: owner is not {tag}")
                if initial_value(text, "controller") != tag:
                    raise ValueError(f"{path.name}: controller is not {tag}")
                initial, _dated = initial_section(text)
                if not re.search(rf"(?m)^\s*add_core\s*=\s*{tag}\s*$", initial):
                    raise ValueError(f"{path.name}: missing initial {tag} core")
                if re.search(r"(?m)^\s*add_core\s*=\s*MNG\s*$", initial):
                    raise ValueError(f"{path.name}: residual MNG core remains")
        actual = current_owned_ids(tag)
        expected = set(provinces)
        if actual != expected:
            raise ValueError(
                f"{tag}: exact ownership mismatch; actual={sorted(actual)}, expected={sorted(expected)}"
            )
    for province_id, owner in RESET_OWNERS.items():
        for path in ensure_province_history(province_id, vanilla_root, write=False):
            if initial_value(read_text(path), "owner") != owner:
                raise ValueError(f"{path.name}: reset owner is not {owner}")
    for tag, expected in PRESERVED_OWNERSHIP.items():
        actual = current_owned_ids(tag)
        if actual != expected:
            raise ValueError(f"{tag} ownership changed: {sorted(actual)} != {sorted(expected)}")
    for tag, expected in EXACT_CORE_TAGS.items():
        actual = current_core_ids(tag)
        if actual != expected:
            raise ValueError(
                f"{tag}: exact core mismatch; actual={sorted(actual)}, expected={sorted(expected)}"
            )
    for province_id, owner in EXCLUSIVE_CORE_OWNERS.items():
        paths = ensure_province_history(province_id, vanilla_root, write=False)
        for path in paths:
            actual = initial_cores(read_text(path))
            if actual != {owner}:
                raise ValueError(
                    f"{path.name}: public-city cores {sorted(actual)} != [{owner}]"
                )
    for tag, removed_ids in FORCED_CORE_REMOVALS.items():
        remaining = current_core_ids(tag) & removed_ids
        if remaining:
            raise ValueError(f"{tag}: forbidden cores remain in {sorted(remaining)}")
    if current_owned_ids("BAS") or current_core_ids("BAS"):
        raise ValueError("Legacy BAS ownership/core data remains after migration to BD2")
    if current_owned_ids("SH2") or current_core_ids("SH2"):
        raise ValueError("Legacy SH2 ownership/core data remains after migration to SHE")
    remaining_legacy_artifacts = [path for path in LEGACY_COUNTRY_ARTIFACTS if path.exists()]
    if remaining_legacy_artifacts:
        names = ", ".join(path.name for path in remaining_legacy_artifacts)
        raise ValueError(f"Legacy country artifacts remain: {names}")
    if POLITIES["DAE"]["capital"] != 5244:
        raise ValueError("DAE capital must remain Daizhou (5244)")
    for tag, config in POLITIES.items():
        if config["capital"] not in TAG_PROVINCES[tag]:
            raise ValueError(f"{tag}: capital is outside assigned provinces")
        if not (COUNTRIES / config["file"]).exists():
            raise ValueError(f"{tag}: missing common country definition")
        history = COUNTRY_HISTORY / config["history"]
        if not history.exists():
            raise ValueError(f"{tag}: missing country history")
        text = read_text(history)
        if int(initial_value(text, "capital")) != config["capital"]:
            raise ValueError(f"{tag}: incorrect capital")
        if not (FLAGS / f"{tag}.tga").exists():
            raise ValueError(f"{tag}: missing flag")
        if (FLAGS / f"{tag}.tga").stat().st_size != 18 + 128 * 128 * 3:
            raise ValueError(f"{tag}: invalid placeholder flag size")
    for tag, config in EXISTING_COUNTRY_COLORS.items():
        path = COUNTRIES / config["file"]
        if not path.exists():
            raise ValueError(f"{tag}: missing color override {config['file']}")
        if country_rgb(path) != config["color"]:
            raise ValueError(f"{tag}: incorrect color override")
    tag_text = read_text(MOD / "common/country_tags/gdd_country_tags.txt")
    for tag, config in POLITIES.items():
        expected = rf'(?m)^\s*{tag}\s*=\s*"countries/{re.escape(config["file"])}"\s*$'
        if not re.search(expected, tag_text):
            raise ValueError(f"{tag}: missing or incorrect country-tag declaration")
    vanilla_tag_text = "\n".join(
        read_text(path) for path in (vanilla_root / "common/country_tags").glob("*.txt")
    )
    if re.search(r"(?m)^\s*BD2\s*=", vanilla_tag_text):
        raise ValueError("BD2 conflicts with a vanilla country tag")
    if re.search(r"(?m)^\s*BAS\s*=", tag_text):
        raise ValueError("Legacy BAS tag declaration remains")
    if re.search(r"(?m)^\s*SH2\s*=", tag_text):
        raise ValueError("Legacy SH2 tag declaration remains")
    localisation = "\n".join(
        read_text(path)
        for path in sorted((MOD / "localisation_source").glob("*.txt"))
    )
    for tag in set(POLITIES) | set(BORROWED_CAPITALS) | {"CHC", "QSH", "XU2", "SNG", "CZH"}:
        for key in (tag, f"{tag}_ADJ"):
            if len(re.findall(rf"(?m)^\s*{key}:0\s+", localisation)) != 1:
                raise ValueError(
                    f"{key}: readable localisation must occur exactly once"
                )
    for tag, config in BORROWED_CAPITALS.items():
        history = COUNTRY_HISTORY / config["history"]
        if not history.exists() or int(initial_value(read_text(history), "capital")) != config["capital"]:
            raise ValueError(f"{tag}: incorrect borrowed-tag history")
    song_history = COUNTRY_HISTORY / "SNG - Song.txt"
    if int(initial_value(read_text(song_history), "capital")) != 2176:
        raise ValueError("SNG capital must be Shangqiu/Guide (2176)")
    xu_history = COUNTRY_HISTORY / "XU2 - Xu2.txt"
    if int(initial_value(read_text(xu_history), "capital")) != 2141:
        raise ValueError("XU2 capital must be Xuzhou (2141) after B50")
    song_province = ensure_province_history(2176, vanilla_root, write=False)[0]
    song_text = read_text(song_province)
    if initial_value(song_text, "owner") != "SNG" or "SNG" not in initial_cores(song_text):
        raise ValueError("Shangqiu/Guide (2176) must be owned and cored by SNG")
    adjacent_color_audit = (
        validate_adjacent_colors(vanilla_root)
        if check_colors
        else {"status": "skipped"}
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from generate_zhuxia_seal_flags import run as check_zhuxia_seal_flags

    check_zhuxia_seal_flags(check=True)
    return {
        "province_count": len(all_ids),
        "polity_count": len(TAG_PROVINCES),
        "generated_tag_count": len(POLITIES),
        "preserved_qi": sorted(PRESERVED_OWNERSHIP["QIC"]),
        "yan_territory": sorted(TAG_PROVINCES["YAN"]),
        "liao_territory": sorted(TAG_PROVINCES["LIO"]),
        "chu_vassals": {
            tag: sorted(TAG_PROVINCES[tag]) for tag in ("EGU", "QVN", "ZHU")
        },
        "dae_capital": 5244,
        "badi_tag": "BD2",
        "adjacent_color_audit": adjacent_color_audit,
        "core_cleanup": {
            "exact": {tag: sorted(ids) for tag, ids in EXACT_CORE_TAGS.items()},
            "removed": {tag: sorted(ids) for tag, ids in FORCED_CORE_REMOVALS.items()},
        },
    }


def apply(vanilla_root: Path, check_colors: bool = True) -> dict[str, object]:
    changed_history_files: list[str] = []
    created_from_vanilla: list[str] = []
    for tag, provinces in TAG_PROVINCES.items():
        for province_id in provinces:
            before = sorted(PROVINCE_HISTORY.glob(f"{province_id} - *.txt"))
            paths = ensure_province_history(province_id, vanilla_root, write=True)
            if not before:
                created_from_vanilla.extend(path.name for path in paths)
            for path in paths:
                old = read_text(path)
                new = apply_owner(old, tag)
                if new != old:
                    path.write_text(new, encoding="utf-8")
                    changed_history_files.append(path.name)

    for province_id, owner in RESET_OWNERS.items():
        for path in ensure_province_history(province_id, vanilla_root, write=True):
            old = read_text(path)
            new = apply_owner(old, owner)
            if new != old:
                path.write_text(new, encoding="utf-8")
                changed_history_files.append(path.name)

    core_override_files = ensure_core_override_files(vanilla_root, write=True)
    created_from_vanilla.extend(path.name for path in core_override_files)
    for path in PROVINCE_HISTORY.glob("*.txt"):
        province_id = province_id_from_path(path)
        if province_id is None:
            continue
        old = read_text(path)
        new = old
        for tag in initial_cores(old):
            if should_remove_core(tag, province_id):
                new = remove_initial_core(new, tag)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed_history_files.append(path.name)

    COUNTRIES.mkdir(parents=True, exist_ok=True)
    COUNTRY_HISTORY.mkdir(parents=True, exist_ok=True)
    FLAGS.mkdir(parents=True, exist_ok=True)
    removed_legacy_artifacts: list[str] = []
    for path in LEGACY_COUNTRY_ARTIFACTS:
        if path.exists():
            path.unlink()
            removed_legacy_artifacts.append(str(path.relative_to(ROOT)))
    generated_country_files: list[str] = []
    for tag, config in POLITIES.items():
        capital_culture, capital_religion = capital_attributes(config["capital"], vanilla_root)
        culture = str(config.get("culture", capital_culture))
        religion = str(config.get("religion", capital_religion))
        country_path = COUNTRIES / config["file"]
        history_path = COUNTRY_HISTORY / config["history"]
        country_path.write_text(country_definition(config["color"]), encoding="utf-8")
        history_path.write_text(
            country_history(
                config["capital"], config["rank"], culture, religion,
                tuple(config.get("accepted", ())),
                str(config.get("government", "monarchy")),
                str(config.get("reform", "gdd_local_fiefdom_reform")),
            ),
            encoding="utf-8",
        )
        (FLAGS / f"{tag}.tga").write_bytes(flag_bytes(config["color"]))
        generated_country_files.extend((str(country_path.relative_to(ROOT)), str(history_path.relative_to(ROOT))))

    for tag, config in EXISTING_COUNTRY_COLORS.items():
        target = COUNTRIES / config["file"]
        if target.exists():
            source = target
        else:
            source = vanilla_root / "common/countries" / config["file"]
        if not source.exists():
            raise ValueError(f"{tag}: missing source country definition {config['file']}")
        target.write_bytes(
            replace_country_color_bytes(source.read_bytes(), config["color"])
        )
        generated_country_files.append(str(target.relative_to(ROOT)))

    for tag, config in BORROWED_CAPITALS.items():
        culture, religion = capital_attributes(config["capital"], vanilla_root)
        path = COUNTRY_HISTORY / config["history"]
        path.write_text(
            country_history(config["capital"], config["rank"], culture, religion),
            encoding="utf-8",
        )
        generated_country_files.append(str(path.relative_to(ROOT)))

    if set_existing_country_capital(COUNTRY_HISTORY / "SNG - Song.txt", 2176, write=True):
        generated_country_files.append("guangdong_independent_practice/history/countries/SNG - Song.txt")
    if set_existing_country_capital(COUNTRY_HISTORY / "XU2 - Xu2.txt", 2141, write=True):
        generated_country_files.append("guangdong_independent_practice/history/countries/XU2 - Xu2.txt")

    for tag in ("SNG", "XU2"):
        if not (FLAGS / f"{tag}.tga").exists():
            source_color = (65, 105, 150) if tag == "SNG" else (179, 128, 104)
            (FLAGS / f"{tag}.tga").write_bytes(flag_bytes(source_color))

    # Country batches historically emitted diagonal placeholder flags. Reapply
    # the B53 Zhuxia seal standard last so a full B43 replay stays deterministic.
    sys.path.insert(0, str(ROOT / "tools"))
    from generate_zhuxia_seal_flags import run as generate_zhuxia_seal_flags

    generate_zhuxia_seal_flags(check=False)

    validation = validate(vanilla_root, check_colors=check_colors)
    report = {
        "batch": "B43_chunqiu_polities",
        "constraints": {
            "yan_liao": "B51 invests LIO in the six-province Liaodong area",
            "qi": "preserved; no QIC province changes",
            "dae_capital": "Daizhou (5244)",
            "jiarong": "JRG owns Ngawa (5091) and Barkam (5089)",
            "geometry": "unchanged",
            "huzhou": "YUE owns and cores 4950",
            "eastern_balance": "B50 splits Huai, Ou, Yang, Wu and Zhou from WUU/YUE/XU2",
            "chu_vassals": "B52 splits E, Quan and Zhou from CHC as starting vassals",
            "changsha_public_cities": "B54 gives Yiyang and Anhua to CSA and releases Changde, Jiujiang and Hanyang as public cities",
            "shangqiu": "SNG owns and cores 2176",
            "badi_tag": "BD2; legacy BAS removed",
            "shen_consolidation": "SHE inherits former SH2 provinces; legacy SH2 removed",
            "ming_cores": "removed from every B43-assigned province",
            "southern_ming_core_cleanup": [663, 666, 2162, 2164, 4949, 5217, 5303],
        },
        "policy": {tag: list(provinces) for tag, provinces in TAG_PROVINCES.items()},
        "reset_owners": {str(province_id): owner for province_id, owner in RESET_OWNERS.items()},
        "created_from_vanilla": sorted(set(created_from_vanilla)),
        "changed_history_files": sorted(set(changed_history_files)),
        "removed_legacy_artifacts": sorted(set(removed_legacy_artifacts)),
        "legacy_artifacts_required_absent": [
            str(path.relative_to(ROOT)) for path in LEGACY_COUNTRY_ARTIFACTS
        ],
        "generated_country_files": sorted(set(generated_country_files)),
        "validation": validation,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "ownership_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-color-audit", action="store_true")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(args.vanilla_root, check_colors=not args.skip_color_audit), ensure_ascii=False))
    else:
        print(json.dumps(apply(args.vanilla_root, check_colors=not args.skip_color_audit), ensure_ascii=False))


if __name__ == "__main__":
    main()
