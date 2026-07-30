"""Build companion assets for the hand-drawn B01 Guangdong map.

``map/provinces.bmp`` is the canonical, user-authored geometry.  This script
audits that bitmap and writes the coupled Clausewitz text assets, but it never
generates, copies, or overwrites province pixels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOD_ROOT = REPO_ROOT / "guangdong_independent_practice"
DEFAULT_REGISTRY = REPO_ROOT / "docs/map/china_province_split_registry.csv"
DEFAULT_CONFIG = Path(__file__).with_name("b01_guangdong_manual.json")
DEFAULT_REPORT = REPO_ROOT / "docs/map/previews/B01_mod_build_report.json"

IMPLEMENTED_IDS = tuple(range(4942, 4950))
P02_IDS = tuple(range(4950, 4962))
DRAWN_P02_IDS = (
    4950, 4951, 4952, 4953, 4954, 4955,
    4956, 4957, 4958, 4959, 4960, 4961,
)
PREPARED_IDS = tuple(value for value in P02_IDS if value not in DRAWN_P02_IDS)
JIANGXI_IDS = (4979, 4980, 4992, 4993, 4994, 4995)
HUNAN_IDS = (4982, 4983, 4996, 4997, 4998, 4999, 5000, 5001)
ZHEJIANG_IDS = (5002, 5003, 5004, 5005, 5006, 5007)
HUBEI_NEW_IDS = (4981, 5008, 5009, 5010, 5011, 5012, 5013, 5014, 5015, 5016)
HUBEI_ALL_IDS = (681, 682, 2171, 2172, 4197) + HUBEI_NEW_IDS
JIANGSU_NEW_IDS = (4976, 4977, 5018, 5020, 5021, 5022, 5023, 5024, 5025)
JIANGSU_ALL_IDS = (2141, 5018, 2142, 5020, 4196,
                   685, 5021, 4977, 5022, 5023,
                   1821, 2145, 5024, 5025, 1822, 4976)
CHONGQING_NEW_IDS = (4987, 5026, 5027, 5028)
CHONGQING_ALL_IDS = (680,) + CHONGQING_NEW_IDS
TAIWAN_MOUNTAIN_ID = 5029
TAIWAN_REVIEW_IDS = (738, 2154, 2155, 4955, 4961, TAIWAN_MOUNTAIN_ID)
WANGJI_NEW_IDS = (4966, 5030, 5031)
WANGJI_ALL_IDS = (688,) + WANGJI_NEW_IDS
YANGTZE_SEA_IDS = (5032, 5033, 5034, 5035, 5036, 5037, 5038)
YANGTZE_DEFINITIONS = {
    5032: ((230, 223, 132), "Yangtze Estuary"),
    5033: ((230, 200, 135), "Lower Yangtze"),
    5034: ((230, 142, 111), "Anqing Reach"),
    5035: ((225, 171, 16), "Wuhan Reach"),
    5036: ((230, 199, 86), "Jingzhou Reach"),
    5037: ((230, 157, 30), "Yichang Reach"),
    5038: ((230, 200, 85), "Jiujiang Reach"),
}
FORMAL_GEOMETRY_IDS = (
    IMPLEMENTED_IDS + DRAWN_P02_IDS + JIANGXI_IDS + HUNAN_IDS
    + ZHEJIANG_IDS + HUBEI_NEW_IDS + JIANGSU_NEW_IDS + CHONGQING_NEW_IDS
    + (TAIWAN_MOUNTAIN_ID,) + WANGJI_NEW_IDS
)
PREPARED_DESIGN_KEYS = (
    "S-04",
    "S-05",
    "S-11",
    "S-12",
    "S-17",
    "S-18",
    "S-23",
    "S-24",
    "S-25",
    "S-26",
    "S-27",
    "S-28",
)
JIANGXI_DESIGN_KEYS = ("S-06", "S-07", "S-29", "S-30", "S-31", "S-32")
HUNAN_DESIGN_KEYS = (
    "S-09", "S-10", "S-33", "S-34", "S-35", "S-36", "S-37", "S-38",
)
ZHEJIANG_DESIGN_KEYS = ("S-39", "S-40", "S-41", "S-42", "S-43", "S-44")
HUBEI_DESIGN_KEYS = (
    "S-08", "S-45", "S-46", "S-47", "S-48",
    "S-49", "S-50", "S-51", "S-52", "S-53",
)
JIANGSU_DESIGN_KEYS = (
    "S-01", "S-02", "S-55", "S-57",
    "S-58", "S-59", "S-60", "S-61", "S-62",
)
CHONGQING_DESIGN_KEYS = ("XN-04", "XN-09", "XN-10", "XN-11")
TAIWAN_MOUNTAIN_DESIGN_KEYS = ("S-63",)
WANGJI_DESIGN_KEYS = ("N-06", "N-15", "N-16")
ACTIVE_IDS = tuple(
    sorted(
        IMPLEMENTED_IDS + P02_IDS + JIANGXI_IDS + HUNAN_IDS
        + ZHEJIANG_IDS + HUBEI_NEW_IDS + JIANGSU_NEW_IDS
        + CHONGQING_NEW_IDS + (TAIWAN_MOUNTAIN_ID,) + WANGJI_NEW_IDS
    )
)
GAME_MAX_PROVINCES = 5039
NEW_DEFINITION_NAMES = {
    4942: "Foshan",
    4943: "Dongguan",
    4944: "Meizhou",
    4945: "Gaozhou",
    4946: "Hong Kong",
    4947: "Luoding",
    4948: "Nanxiong",
    4949: "Lufeng",
    4950: "Huzhou",
    4951: "Taizhou",
    4952: "Putian",
    4953: "Zhangzhou",
    4954: "Xunzhou",
    4955: "Zhuluo",
    4956: "Quzhou",
    4957: "Shaowu",
    4958: "Xiamen",
    4959: "Qingyuan",
    4960: "Taiping",
    4961: "Kavalan",
    4979: "Jiujiang",
    4980: "Linchuan",
    4992: "Ruizhou",
    4993: "Guangxin",
    4994: "Yuanzhou",
    4995: "Nan'an",
    4982: "Yuezhou",
    4983: "Baoqing",
    4996: "Lizhou",
    4997: "Yiyang",
    4998: "Xiangtan",
    4999: "Jingzhou (Hunan)",
    5000: "Yongzhou",
    5001: "Chenzhou (South Hunan)",
    5002: "Jiaxing",
    5003: "Yanzhou",
    5004: "Changguo",
    5005: "Ninghai",
    5006: "Yiwu",
    5007: "Chuzhou (Zhejiang)",
    4981: "Hanyang",
    5008: "Yunyang",
    5009: "Suizhou",
    5010: "Chengtian",
    5011: "Hankou",
    5012: "Huangzhou",
    5013: "Shizhou",
    5014: "Gongan",
    5015: "Mianyang",
    5016: "Xingguo",
    4976: "Songjiang",
    4977: "Taizhou (Jiangsu)",
    5018: "Suqian",
    5020: "Yancheng",
    5021: "Gaoyou",
    5022: "Tongzhou",
    5023: "Rugao",
    5024: "Changzhou",
    5025: "Wuxi",
    4987: "Wanzhou",
    5026: "Hezhou (Chongqing)",
    5027: "Fuzhou (Chongqing)",
    5028: "Kuizhou",
    5029: "Taiwan Mountains",
    4966: "Xingyang",
    5030: "Zhengzhou",
    5031: "Chenliu",
}

# Positions use Clausewitz coordinates, whose vertical axis is the inverse of
# provinces.bmp.  Each tuple contains city, unit, text, port, two auxiliary
# points, and the unused seventh point.
POSITION_DATA = {
    664: {
        "comment": "Lingyun - positioned from painted Guangxi geometry",
        "positions": (
            4472, 1032, 4475, 1038, 4468, 1046, 4472, 1032,
            4471, 1036, 4476, 1033, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    738: {
        "comment": "Sakam - adjusted after Zhuluo split",
        "positions": (
            4690, 1013, 4691, 1013, 4691, 1010, 4687, 1013,
            4690, 1011, 4692, 1012, 0, 0,
        ),
        "rotation": (0, 0, 0, 1.745, 0, 0, 0),
    },
    2155: {
        "comment": "Middag - port adjusted after Taiwan split",
        "positions": (
            4696, 1034, 4693, 1034, 4696, 1034, 4684, 1042,
            4696, 1034, 4694, 1034, 4696, 1034,
        ),
        "rotation": (0, 0, 0, 2.356, 0, 0, 0),
    },
    1840: {
        "comment": "Guilin - positioned from painted Guangxi geometry",
        "positions": (
            4531, 1053, 4538, 1049, 4543, 1048, 4531, 1053,
            4537, 1053, 4534, 1049, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2162: {
        "comment": "Ngchow - positioned from painted Guangxi geometry",
        "positions": (
            4536, 1025, 4534, 1023, 4538, 1029, 4536, 1025,
            4530, 1020, 4542, 1024, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2163: {
        "comment": "Liuzhou - positioned from painted Guangxi geometry",
        "positions": (
            4512, 1044, 4515, 1051, 4519, 1058, 4512, 1044,
            4514, 1040, 4515, 1055, 0, 0,
        ),
        "rotation": (3.142, 0, 0, 0, 0, 0, 0),
    },
    2164: {
        "comment": "Namning - positioned from painted Guangxi geometry",
        "positions": (
            4493, 1023, 4496, 1031, 4503, 1027, 4493, 1023,
            4492, 1027, 4495, 1035, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    665: {
        "comment": "Shiuhing",
        "positions": (
            4556, 1012, 4559, 1019, 4554, 1011, 4555.5, 1001.5,
            4558, 1013, 4552, 1010, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    667: {
        "comment": "Canton",
        "positions": (
            4575, 1022, 4575, 1026, 4581, 1034, 4578, 1021,
            4584, 1035, 4579, 1029, 0, 0,
        ),
        "rotation": (0, 0, 0, -0.262, 0, 0, 0),
    },
    2157: {
        "comment": "Waichow",
        "positions": (
            4602, 1041, 4606, 1039, 4601, 1045, 4597, 1019,
            4604, 1035, 4598, 1039, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2158: {
        "comment": "Shiukwan",
        "positions": (
            4578.5, 1051, 4572, 1050, 4576, 1052, 4565, 1051,
            4576, 1052, 4581, 1048, 4576, 1052,
        ),
        "rotation": (1.571, 0, 0, 0, 0, 0, 0),
    },
    2159: {
        "comment": "Leichow",
        "positions": (
            4522, 988, 4524, 993, 4523, 985, 4529.5, 978,
            4522, 991, 4526, 981, 4532, 998,
        ),
        "rotation": (0, 0, 0, -0.785, 0, 0, 0),
    },
    4942: {
        "comment": "Foshan",
        "positions": (
            4571, 1027, 4570, 1024, 4571, 1024, 4571, 1009,
            4572, 1021, 4572, 1024, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4943: {
        "comment": "Dongguan",
        "positions": (
            4585, 1019, 4587, 1018, 4586, 1021, 4594, 1018,
            4583, 1018, 4589, 1017, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4944: {
        "comment": "Meizhou",
        "positions": (
            4618, 1051, 4615, 1054, 4619, 1048, 4618, 1051,
            4620, 1045, 4615, 1050, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4945: {
        "comment": "Gaozhou",
        "positions": (
            4540, 1011, 4541, 1004, 4539, 1008, 4541, 997,
            4539, 1014, 4544, 1003, 0, 0,
        ),
        "rotation": (0, 0, 0, -0.785, 0, 0, 0),
    },
    4946: {
        "comment": "Hong Kong",
        "positions": (
            4587, 1013, 4585, 1012, 4589, 1012, 4589, 1014,
            4586, 1015, 4588, 1010, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4947: {
        "comment": "Luoding",
        "positions": (
            4552, 1026, 4551, 1028, 4554, 1025, 4552, 1023,
            4552, 1030, 4550, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4948: {
        "comment": "Nanxiong",
        "positions": (
            4586, 1058, 4587, 1056, 4585, 1060, 4583, 1058,
            4591, 1060, 4586, 1054, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4949: {
        "comment": "Lufeng",
        "positions": (
            4610, 1025, 4608, 1024, 4613, 1024, 4611, 1021,
            4611, 1027, 4607, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    684: {
        "comment": "Hangzhou - adjusted after fourteen-province Zhejiang split",
        "positions": (
            4678, 1151, 4676, 1150, 4679, 1153, 4682, 1149,
            4677, 1153, 4679, 1150, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    1824: {
        "comment": "Wenzhou - adjusted after fourteen-province Zhejiang split",
        "positions": (
            4689, 1112, 4687, 1111, 4691, 1114, 4689, 1110,
            4688, 1114, 4691, 1111, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2148: {
        "comment": "Shaoxing - Yue capital at Kuaiji",
        "positions": (
            4684, 1139, 4682, 1138, 4686, 1141, 4689, 1146,
            4683, 1141, 4686, 1138, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2149: {
        "comment": "Ningbo - adjusted after Changguo split",
        "positions": (
            4699, 1137, 4697, 1136, 4701, 1139, 4703, 1131,
            4698, 1139, 4701, 1136, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2150: {
        "comment": "Jinhua - adjusted after Yiwu and Quzhou split",
        "positions": (
            4670, 1119, 4668, 1118, 4672, 1120, 4670, 1119,
            4669, 1121, 4672, 1118, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4950: {
        "comment": "Huzhou - Wu southern frontier",
        "positions": (
            4669, 1157, 4669, 1156, 4672, 1159, 4669, 1157,
            4669, 1157, 4671, 1156, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4951: {
        "comment": "Taizhou - adjusted after Ninghai split",
        "positions": (
            4693, 1125, 4691, 1124, 4695, 1127, 4702, 1121,
            4692, 1127, 4695, 1124, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4952: {
        "comment": "Putian - provisional anchor until hand drawing",
        "positions": (
            4659, 1062, 4658, 1062, 4660, 1063, 4662, 1062,
            4659, 1061, 4660, 1062, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4953: {
        "comment": "Zhangzhou - provisional anchor until hand drawing",
        "positions": (
            4638, 1038, 4637, 1038, 4639, 1039, 4638, 1037,
            4638, 1039, 4639, 1038, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4954: {
        "comment": "Xunzhou - positioned from painted province geometry",
        "positions": (
            4527, 1034, 4525, 1029, 4521, 1025, 4527, 1034,
            4530, 1031, 4523, 1034, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4955: {
        "comment": "Zhuluo - positioned from painted province geometry",
        "positions": (
            4688, 1020, 4687, 1021, 4686, 1022, 4681, 1020,
            4686, 1023, 4685, 1022, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4956: {
        "comment": "Quzhou - Xianxia Pass gateway",
        "positions": (
            4658, 1120, 4656, 1119, 4660, 1122, 4658, 1120,
            4657, 1122, 4660, 1119, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4957: {
        "comment": "Shaowu - provisional anchor until hand drawing",
        "positions": (
            4638, 1095, 4637, 1095, 4639, 1096, 4638, 1095,
            4638, 1094, 4639, 1095, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4958: {
        "comment": "Xiamen - positioned from painted province geometry",
        "positions": (
            4647, 1051, 4646, 1051, 4647, 1050, 4649, 1051,
            4646, 1052, 4648, 1051, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4959: {
        "comment": "Qingyuan - positioned from painted province geometry",
        "positions": (
            4495, 1053, 4491, 1052, 4484, 1052, 4495, 1053,
            4487, 1055, 4499, 1052, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4960: {
        "comment": "Taiping - positioned from painted province geometry",
        "positions": (
            4480, 1015, 4479, 1013, 4483, 1021, 4480, 1015,
            4481, 1017, 4475, 1014, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4961: {
        "comment": "Kavalan - positioned from painted province geometry",
        "positions": (
            4707, 1055, 4706, 1055, 4707, 1054, 4708, 1055,
            4706, 1054, 4707, 1055, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    670: {
        "comment": "Ganzhou - adjusted after Nan'an split",
        "positions": (
            4611, 1076, 4608, 1075, 4614, 1079, 4611, 1076,
            4609, 1078, 4613, 1074, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    683: {
        "comment": "Nanchang - adjusted after Jiujiang and Ruizhou split",
        "positions": (
            4610, 1117, 4607, 1115, 4612, 1122, 4610, 1117,
            4608, 1119, 4613, 1116, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    1833: {
        "comment": "Ji'an - adjusted after Linchuan and Yuanzhou split",
        "positions": (
            4610, 1093, 4608, 1091, 4612, 1095, 4610, 1093,
            4609, 1095, 4612, 1092, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2151: {
        "comment": "Raozhou - adjusted after Guangxin split",
        "positions": (
            4632, 1121, 4630, 1119, 4634, 1124, 4632, 1121,
            4631, 1123, 4634, 1120, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4979: {
        "comment": "Jiujiang",
        "positions": (
            4609, 1135, 4606, 1134, 4611, 1138, 4609, 1135,
            4607, 1137, 4612, 1134, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4980: {
        "comment": "Linchuan",
        "positions": (
            4624, 1103, 4622, 1101, 4626, 1106, 4624, 1103,
            4623, 1105, 4626, 1102, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4992: {
        "comment": "Ruizhou",
        "positions": (
            4592, 1108, 4590, 1107, 4594, 1111, 4592, 1108,
            4591, 1110, 4594, 1107, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4993: {
        "comment": "Guangxin",
        "positions": (
            4646, 1118, 4644, 1116, 4648, 1121, 4646, 1118,
            4645, 1120, 4648, 1117, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4994: {
        "comment": "Yuanzhou",
        "positions": (
            4594, 1091, 4592, 1089, 4596, 1094, 4594, 1091,
            4593, 1093, 4596, 1090, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4995: {
        "comment": "Nan'an",
        "positions": (
            4603, 1061, 4601, 1059, 4605, 1064, 4603, 1061,
            4602, 1063, 4605, 1060, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    671: {
        "comment": "Changsha - adjusted after Hunan split",
        "positions": (
            4576, 1117, 4573, 1115, 4579, 1120, 4576, 1117,
            4574, 1119, 4579, 1116, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    672: {
        "comment": "Changde - adjusted after Lizhou split",
        "positions": (
            4544, 1127, 4543, 1127, 4545, 1127, 4544, 1127,
            4544, 1128, 4544, 1126, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2173: {
        "comment": "Chenzhou (Yuanling) - adjusted after Jingzhou split",
        "positions": (
            4528, 1107, 4525, 1105, 4531, 1110, 4528, 1107,
            4526, 1109, 4531, 1106, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2174: {
        "comment": "Hengzhou - adjusted after southern Hunan split",
        "positions": (
            4570, 1084, 4567, 1082, 4573, 1087, 4570, 1084,
            4568, 1086, 4573, 1083, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4982: {
        "comment": "Yuezhou",
        "positions": (
            4580, 1135, 4577, 1133, 4583, 1138, 4580, 1135,
            4578, 1137, 4583, 1134, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4983: {
        "comment": "Baoqing",
        "positions": (
            4549, 1085, 4546, 1083, 4552, 1088, 4549, 1085,
            4547, 1087, 4551, 1084, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4996: {
        "comment": "Lizhou",
        "positions": (
            4529, 1140, 4528, 1139, 4531, 1142, 4529, 1140,
            4528, 1142, 4531, 1140, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4997: {
        "comment": "Yiyang",
        "positions": (
            4550, 1114, 4547, 1112, 4553, 1117, 4550, 1114,
            4548, 1116, 4553, 1113, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4998: {
        "comment": "Xiangtan",
        "positions": (
            4573, 1103, 4572, 1102, 4575, 1105, 4573, 1103,
            4572, 1105, 4575, 1103, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4999: {
        "comment": "Jingzhou (Hunan)",
        "positions": (
            4524, 1087, 4521, 1085, 4527, 1090, 4524, 1087,
            4522, 1089, 4527, 1086, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5000: {
        "comment": "Yongzhou",
        "positions": (
            4552, 1065, 4549, 1063, 4555, 1068, 4552, 1065,
            4550, 1067, 4555, 1064, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5001: {
        "comment": "Chenzhou (South Hunan)",
        "positions": (
            4568, 1068, 4566, 1067, 4570, 1070, 4568, 1068,
            4567, 1070, 4570, 1068, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5002: {
        "comment": "Jiaxing - Wu canal frontier",
        "positions": (
            4681, 1154, 4679, 1154, 4683, 1156, 4684, 1151,
            4680, 1156, 4683, 1153, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5003: {
        "comment": "Yanzhou - Jiande on the upper Fuchun River",
        "positions": (
            4665, 1135, 4663, 1134, 4667, 1137, 4665, 1135,
            4664, 1137, 4667, 1134, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5004: {
        "comment": "Changguo - Zhoushan maritime base",
        "positions": (
            4712, 1145, 4711, 1145, 4713, 1145, 4715, 1145,
            4712, 1146, 4714, 1145, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5005: {
        "comment": "Ninghai - Sanmen Bay",
        "positions": (
            4697, 1131, 4695, 1130, 4699, 1133, 4702, 1130,
            4696, 1133, 4699, 1130, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5006: {
        "comment": "Yiwu - eastern Jinhua basin",
        "positions": (
            4672, 1122, 4671, 1121, 4674, 1124, 4672, 1122,
            4671, 1124, 4674, 1122, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5007: {
        "comment": "Chuzhou (Zhejiang) - Lishui and Longquan",
        "positions": (
            4670, 1108, 4668, 1107, 4672, 1110, 4670, 1108,
            4669, 1110, 4672, 1107, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    681: {
        "comment": "Yiling - Three Gorges gate",
        "positions": (4537,1159,4536,1159,4538,1159,4537,1160,4537,1158,4536,1160,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    682: {
        "comment": "Wuchang - south-bank Chu capital",
        "positions": (4596,1153,4595,1153,4597,1153,4596,1154,4596,1152,4595,1154,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2171: {
        "comment": "Xiangyang - Han River fortress",
        "positions": (4542,1184,4541,1184,4543,1184,4542,1185,4542,1183,4541,1185,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2172: {
        "comment": "Jingzhou - north-bank river port",
        "positions": (4556,1150,4555,1150,4557,1150,4556,1151,4556,1149,4555,1151,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4197: {
        "comment": "De'an - Dabie foothills",
        "positions": (4598,1167,4597,1167,4599,1167,4598,1168,4598,1166,4597,1168,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4981: {
        "comment": "Hanyang - Han River west bank",
        "positions": (4588,1153,4587,1153,4589,1153,4588,1154,4588,1152,4587,1154,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5008: {
        "comment": "Yunyang - Wudang frontier",
        "positions": (4521,1186,4520,1186,4522,1186,4521,1187,4521,1185,4520,1187,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5009: {
        "comment": "Suizhou - Suizao corridor",
        "positions": (4582,1171,4581,1171,4583,1171,4582,1172,4582,1170,4581,1172,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5010: {
        "comment": "Chengtian - middle Han River",
        "positions": (4561,1167,4560,1167,4562,1167,4561,1168,4561,1166,4560,1168,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5011: {
        "comment": "Hankou - protected free city",
        "positions": (4590,1160,4589,1160,4591,1160,4590,1161,4590,1159,4589,1161,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5012: {
        "comment": "Huangzhou - eastern Hubei tea market",
        "positions": (4605,1159,4604,1159,4606,1159,4605,1160,4605,1158,4604,1160,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5013: {
        "comment": "Shizhou - Qing River highlands",
        "positions": (4510,1147,4509,1147,4511,1147,4510,1148,4510,1146,4509,1148,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5014: {
        "comment": "Gongan - south bank opposite Jingzhou",
        "positions": (4548,1148,4547,1148,4549,1148,4548,1149,4548,1147,4547,1149,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5015: {
        "comment": "Mianyang - southern Hubei river plain",
        "positions": (4595,1140,4594,1140,4596,1140,4595,1141,4595,1139,4594,1141,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5016: {
        "comment": "Xingguo - Daye mining district",
        "positions": (4602,1147,4601,1147,4603,1147,4602,1148,4602,1146,4601,1148,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    680: {
        "comment": "Chongqing - Jialing and Yangtze confluence",
        "positions": (4468,1137,4469,1137,4467,1138,4468,1137,4467,1136,4469,1138,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4987: {
        "comment": "Wanzhou - middle Xiajiang river port",
        "positions": (4500,1151,4501,1151,4499,1152,4500,1151,4499,1150,4501,1152,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5026: {
        "comment": "Hezhou - upper Jialing gateway",
        "positions": (4474,1149,4475,1149,4473,1150,4474,1149,4473,1148,4475,1150,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5027: {
        "comment": "Fuzhou - Wu River confluence",
        "positions": (4491,1130,4492,1130,4490,1131,4491,1130,4490,1129,4492,1131,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5028: {
        "comment": "Kuizhou - Qutang Gorge gate",
        "positions": (4517,1167,4518,1167,4516,1168,4517,1167,4516,1166,4518,1168,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    688: {
        "comment": "Kaifeng - Zhou royal capital on the Bian corridor",
        "positions": (4589,1230,4590,1230,4588,1231,4589,1230,4588,1229,4590,1231,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    4966: {
        "comment": "Xingyang - Hulao western gate of the royal domain",
        "positions": (4577,1228,4578,1228,4576,1229,4577,1228,4576,1227,4578,1229,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5030: {
        "comment": "Zhengzhou - southwestern hinterland of Kaifeng",
        "positions": (4582,1217,4583,1217,4581,1218,4582,1217,4581,1216,4583,1218,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    5031: {
        "comment": "Chenliu - eastern Bian River gate",
        "positions": (4599,1232,4600,1232,4598,1233,4599,1232,4598,1231,4600,1233,0,0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
}

JIANGSU_POSITION_CENTERS = {
    2141: (4629, 1226), 5018: (4647, 1222),
    2142: (4665, 1213), 5020: (4678, 1214),
    4196: (4663, 1226), 685: (4670, 1192), 5021: (4671, 1203),
    4977: (4681, 1196), 5022: (4695, 1183), 5023: (4687, 1189),
    1821: (4652, 1186), 2145: (4665, 1177), 5024: (4673, 1181),
    5025: (4685, 1176), 1822: (4692, 1170), 4976: (4700, 1164),
}
JIANGSU_PORT_POINTS = {
    4976: (4702, 1159), 4977: (4689, 1202), 5020: (4684, 1218),
    5022: (4699, 1184), 5023: (4692, 1192), 5025: (4686, 1180),
}
for _province_id, (_x, _y) in JIANGSU_POSITION_CENTERS.items():
    _port_x, _port_y = JIANGSU_PORT_POINTS.get(_province_id, (_x, _y))
    POSITION_DATA[_province_id] = {
        "comment": "Jiangsu refinement - compact historical seat",
        "positions": (_x, _y, _x, _y, _x, _y, _port_x, _port_y,
                      _x, _y, _x, _y, 0, 0),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    }

TAIWAN_POSITION_CENTERS = {
    738: (4687, 1018),
    2154: (4703, 1057),
    2155: (4689, 1040),
    4955: (4686, 1030),
    4961: (4703, 1048),
}
TAIWAN_PORT_POINTS = {
    738: (4694, 1015),
    2154: (4699, 1060),
    2155: (4685, 1043),
    4955: (4680, 1028),
    4961: (4704, 1039),
}
for _province_id, (_x, _y) in TAIWAN_POSITION_CENTERS.items():
    _port_x, _port_y = TAIWAN_PORT_POINTS[_province_id]
    POSITION_DATA[_province_id] = {
        "comment": "Taiwan coastal ring around the impassable central range",
        "positions": (
            _x, _y, _x, _y, _x, _y, _port_x, _port_y,
            _x, _y, _x, _y, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    }

HUBEI_POSITION_CENTERS = {
    681: (4533, 1172),
    682: (4593, 1153),
    2171: (4542, 1188),
    2172: (4546, 1165),
    4197: (4584, 1172),
    4981: (4581, 1150),
    5008: (4525, 1185),
    5009: (4570, 1181),
    5010: (4561, 1166),
    5011: (4583, 1158),
    5012: (4600, 1166),
    5013: (4510, 1148),
    5014: (4546, 1151),
    5015: (4563, 1148),
    5016: (4608, 1150),
}
for _province_id, (_x, _y) in HUBEI_POSITION_CENTERS.items():
    POSITION_DATA[_province_id] = {
        "comment": "Hubei river-defined refinement - compact historical seat",
        "positions": (
            _x, _y, _x, _y, _x, _y, _x, _y,
            _x, _y, _x, _y, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    }

POSITION_DATA.update({
    686: {
        "comment": "Anqing - adjusted for navigable Yangtze",
        "positions": (
            4631, 1151, 4631, 1158, 4651, 1174, 4656, 1179,
            4651, 1167, 4630, 1152, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    1838: {
        "comment": "Hefei - adjusted for navigable Yangtze",
        "positions": (
            4641, 1178, 4647, 1172, 4633, 1215, 4638, 1220,
            4633, 1215, 4641, 1173, 0, 0,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2143: {
        "comment": "Fengyang - adjusted for navigable Yangtze",
        "positions": (
            4646, 1197, 4639, 1197, 4639, 1199, 4644, 1204,
            4639, 1199, 4640, 1196, 4639, 1199,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2146: {
        "comment": "Ningguo - adjusted for navigable Yangtze",
        "positions": (
            4662, 1159, 4668, 1161, 4661, 1157, 4666, 1162,
            4661, 1157, 4662, 1157, 4661, 1157,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
    2147: {
        "comment": "Huizhou - adjusted for navigable Yangtze",
        "positions": (
            4653, 1142, 4648, 1141, 4647, 1140, 4652, 1145,
            4647, 1140, 4653, 1140, 4647, 1140,
        ),
        "rotation": (0, 0, 0, 0, 0, 0, 0),
    },
})

YANGTZE_PORT_POINTS = {
    683: (1655, 4621, 1125),
    2151: (1655, 4625, 1125),
    4979: (5038, 4612, 1141),
    671: (1897, 4568, 1124),
    672: (1897, 4553, 1131),
    4982: (5036, 4576, 1139),
    4996: (1897, 4553, 1132),
    4997: (1897, 4555, 1124),
    681: (5037, 4531, 1164),
    682: (5035, 4593, 1155),
    2172: (5037, 4542, 1159),
    4981: (5035, 4582, 1146),
    5011: (5035, 4587, 1155),
    5012: (5035, 4598, 1157),
    5013: (5037, 4526, 1162),
    5014: (5036, 4545, 1151),
    5015: (5036, 4560, 1146),
    5016: (5038, 4605, 1146),
    685: (5033, 4670, 1188),
    4977: (5032, 4681, 1186),
    5022: (5032, 4695, 1180),
    5023: (5032, 4684, 1185),
    1821: (5033, 4654, 1185),
    2145: (5033, 4667, 1184),
    5024: (5033, 4674, 1183),
    5025: (5032, 4687, 1178),
    1822: (5032, 4695, 1174),
    4976: (5032, 4703, 1169),
    4987: (5037, 4496, 1153),
    5028: (5037, 4517, 1164),
    1838: (5033, 4652, 1178),
    2146: (5034, 4654, 1168),
    2147: (5034, 4644, 1158),
    686: (5034, 4630, 1151),
}
for _province_id, (_sea_id, _port_x, _port_y) in YANGTZE_PORT_POINTS.items():
    _data = POSITION_DATA[_province_id]
    _positions = list(_data["positions"])
    _positions[6:8] = (_port_x, _port_y)
    _data["positions"] = tuple(_positions)

YANGTZE_RELOCATED_CENTERS = {
    5014: (4539, 1152),
    5016: (4595, 1142),
    685: (4664, 1192),
    1838: (4638, 1175),
    686: (4621, 1156),
}
for _province_id, (_x, _y) in YANGTZE_RELOCATED_CENTERS.items():
    _data = POSITION_DATA[_province_id]
    _positions = list(_data["positions"])
    for _slot in (0, 1, 2, 4, 5):
        _positions[_slot * 2:_slot * 2 + 2] = (_x, _y)
    _data["positions"] = tuple(_positions)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one exact match, found {count}")
    return text.replace(old, new, 1)


def find_named_block(text: str, name: str, start: int = 0) -> tuple[int, int]:
    pattern = re.compile(rf"(?m)^[ \t]*{re.escape(name)}[ \t]*=[ \t]*\{{")
    match = pattern.search(text, start)
    if not match:
        raise ValueError(f"Could not find block {name!r}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    index = opening
    while index < len(text):
        character = text[index]
        if in_comment:
            if character == "\n":
                in_comment = False
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == "#":
            in_comment = True
        elif character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
        index += 1
    raise ValueError(f"Unclosed block {name!r}")


def replace_named_block(text: str, name: str, replacement: str) -> str:
    start, end = find_named_block(text, name)
    return text[:start] + replacement + text[end:]


def append_to_named_block(text: str, name: str, line: str) -> str:
    start, end = find_named_block(text, name)
    block = text[start:end]
    closing = block.rfind("}")
    if closing < 0:
        raise ValueError(f"{name}: missing closing brace")
    block = block[:closing].rstrip() + "\n" + line.rstrip() + "\n" + block[closing:]
    return text[:start] + block + text[end:]


def modify_nested_block(
    text: str,
    outer_name: str,
    modifier: Callable[[str], str],
) -> str:
    start, end = find_named_block(text, outer_name)
    block = text[start:end]
    modified = modifier(block)
    if modified == block:
        raise ValueError(f"{outer_name}: nested modifier made no change")
    return text[:start] + modified + text[end:]


def read_text(path: Path) -> str:
    return path.read_text(encoding="cp1252")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [line.expandtabs(4).rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    path.write_text("\n".join(lines) + "\n", encoding="cp1252", newline="\n")


def load_active_registry(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row["draw_batch"] == "B01"
            or row["design_key"] in PREPARED_DESIGN_KEYS
            or row["design_key"] in JIANGXI_DESIGN_KEYS
            or row["design_key"] in HUNAN_DESIGN_KEYS
            or row["design_key"] in ZHEJIANG_DESIGN_KEYS
            or row["design_key"] in HUBEI_DESIGN_KEYS
            or row["design_key"] in JIANGSU_DESIGN_KEYS
            or row["design_key"] in CHONGQING_DESIGN_KEYS
            or row["design_key"] in TAIWAN_MOUNTAIN_DESIGN_KEYS
            or row["design_key"] in WANGJI_DESIGN_KEYS
        ]
    rows.sort(key=lambda row: int(row["game_id"]))
    ids = tuple(int(row["game_id"]) for row in rows)
    if ids != ACTIVE_IDS:
        raise ValueError(f"Active registry IDs must be {ACTIVE_IDS}, found {ids}")
    return rows


def load_definition_colors(
    path: Path,
) -> tuple[dict[tuple[int, int, int], int], set[int]]:
    colors: dict[tuple[int, int, int], int] = {}
    ids: set[int] = set()
    with path.open(encoding="cp1252", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row or not row[0].isdigit():
                continue
            province_id = int(row[0])
            color = (int(row[1]), int(row[2]), int(row[3]))
            colors[color] = province_id
            ids.add(province_id)
    return colors, ids


def validate_classic_bmp_header(path: Path) -> None:
    header = path.read_bytes()[:54]
    if len(header) < 54 or header[:2] != b"BM":
        raise ValueError("provinces.bmp is not a Windows BMP")
    pixel_offset = struct.unpack_from("<I", header, 10)[0]
    dib_size = struct.unpack_from("<I", header, 14)[0]
    planes = struct.unpack_from("<H", header, 26)[0]
    bits_per_pixel = struct.unpack_from("<H", header, 28)[0]
    compression = struct.unpack_from("<I", header, 30)[0]
    actual_size = path.stat().st_size
    declared_size = struct.unpack_from("<I", header, 2)[0]
    if (
        pixel_offset != 54
        or dib_size != 40
        or planes != 1
        or bits_per_pixel != 24
        or compression != 0
        or declared_size != actual_size
    ):
        raise ValueError(
            "provinces.bmp must use the classic 40-byte, 24-bit, "
            "uncompressed BI_RGB header"
        )


def audit_manual_geometry(
    vanilla_root: Path,
    provinces_path: Path,
    registry_rows: list[dict[str, str]],
    config: dict[str, object],
) -> dict[str, object]:
    if config.get("source_policy") != "hand_drawn_canonical_bmp":
        raise ValueError("Manual map config has an unexpected source policy")
    configured = (REPO_ROOT / str(config["canonical_bmp"])).resolve()
    if provinces_path.resolve() != configured:
        raise ValueError(
            f"Canonical hand-drawn bitmap must be {configured}, found {provinces_path}"
        )

    baseline_verified: dict[str, bool] = {}
    for filename, expected_hash in config["baseline_file_sha256"].items():
        path = vanilla_root / "map" / filename
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"EU4 baseline {filename} hash {actual_hash} does not match "
                f"the locked {config['baseline_version']} baseline"
            )
        baseline_verified[filename] = True

    validate_classic_bmp_header(provinces_path)
    with Image.open(provinces_path) as image:
        expected_size = tuple(int(value) for value in config["expected_size"])
        if image.size != expected_size or image.mode != config["expected_mode"]:
            raise ValueError(
                f"provinces.bmp must be {expected_size} {config['expected_mode']}, "
                f"found {image.size} {image.mode}"
            )
        province_map = np.asarray(image, dtype=np.uint8)
    with Image.open(vanilla_root / "map/provinces.bmp") as image:
        baseline_map = np.asarray(image, dtype=np.uint8)

    changed_mask = np.any(province_map != baseline_map, axis=2)
    changed_pixels = int(changed_mask.sum())
    expected_changed = int(config["expected_changed_pixels"])
    if changed_pixels != expected_changed:
        raise ValueError(
            f"Hand-drawn map has {changed_pixels} pixels changed from vanilla; "
            f"the reviewed geometry expects {expected_changed}"
        )

    vanilla_colors, _vanilla_ids = load_definition_colors(
        vanilla_root / "map/definition.csv"
    )
    allowed_sources = {int(value) for value in config["allowed_vanilla_source_ids"]}
    actual_sources = {
        vanilla_colors[tuple(int(channel) for channel in color)]
        for color in np.unique(baseline_map[changed_mask].reshape(-1, 3), axis=0)
    }
    if not actual_sources <= allowed_sources:
        raise ValueError(
            "Hand-drawn changes escaped the reviewed Guangdong source provinces: "
            f"{sorted(actual_sources - allowed_sources)}"
        )

    defined_colors = set(vanilla_colors)
    for row in registry_rows:
        defined_colors.add(
            (int(row["rgb_r"]), int(row["rgb_g"]), int(row["rgb_b"]))
        )
    defined_colors.update(rgb for rgb, _name in YANGTZE_DEFINITIONS.values())
    unknown_colors = [
        tuple(int(channel) for channel in color)
        for color in np.unique(province_map.reshape(-1, 3), axis=0)
        if tuple(int(channel) for channel in color) not in defined_colors
    ]
    if unknown_colors:
        raise ValueError(
            f"provinces.bmp contains colors absent from definition data: "
            f"{unknown_colors[:10]}"
        )

    pixel_counts: dict[str, int] = {}
    for province in config["provinces"]:
        color = np.array(province["rgb"], dtype=np.uint8)
        count = int(np.all(province_map == color, axis=2).sum())
        expected = int(province["expected_pixels"])
        if count != expected:
            raise ValueError(
                f"{province['game_id']} has {count} pixels; expected {expected}"
            )
        pixel_counts[str(province["game_id"])] = count

    return {
        "baseline_version": config["baseline_version"],
        "baseline_verified_by_sha256": baseline_verified,
        "source_policy": config["source_policy"],
        "changed_pixels": changed_pixels,
        "province_pixels": pixel_counts,
        "provinces_sha256": sha256_file(provinces_path),
    }


def build_definition(
    vanilla_root: Path,
    output: Path,
    registry_rows: list[dict[str, str]],
) -> None:
    source = read_text(vanilla_root / "map/definition.csv").rstrip("\r\n")
    source, renamed = re.subn(
        r"(?m)^4197;148;197;227;Huangzhou;x$",
        "4197;148;197;227;De'an;x",
        source,
    )
    if renamed != 1:
        raise ValueError("definition.csv: could not rename province 4197 to De'an")
    _colors, existing_ids = load_definition_colors(
        vanilla_root / "map/definition.csv"
    )
    if existing_ids & set(ACTIVE_IDS):
        raise ValueError("Vanilla definition unexpectedly contains an active mod ID")
    additions = [
        f"{row['game_id']};{row['rgb_r']};{row['rgb_g']};{row['rgb_b']};"
        f"{NEW_DEFINITION_NAMES[int(row['game_id'])]};x"
        for row in registry_rows
    ]
    additions.extend(
        f"{province_id};{rgb[0]};{rgb[1]};{rgb[2]};{name};x"
        for province_id, (rgb, name) in YANGTZE_DEFINITIONS.items()
    )
    write_text(output, source + "\n" + "\n".join(additions) + "\n")


def build_default_map(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/default.map")
    text, count = re.subn(
        r"(?m)^max_provinces\s*=\s*\d+\s*$",
        f"max_provinces = {GAME_MAX_PROVINCES}",
        text,
    )
    if count != 1:
        raise ValueError(f"default.map: expected one max_provinces, found {count}")
    sea_ids = " ".join(str(value) for value in YANGTZE_SEA_IDS)
    text = append_to_named_block(
        text,
        "sea_starts",
        f"\t{sea_ids} 1655 1897 # Navigable Yangtze, Dongting and Poyang",
    )
    for lake_id in (1655, 1897):
        text = modify_nested_block(
            text,
            "lakes",
            lambda block, value=lake_id: re.sub(
                rf"(?<!\d){value}(?!\d)", "", block
            ),
        )
    write_text(output, text)


def build_area(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/area.txt")
    pearl_and_east = """pearl_river_delta_area = { #5
\t667 668 4942 4943 4946
}

guangdong_area = { #6
\t2156 2157 2158 4944 4948 4949
}"""
    text = replace_named_block(text, "guangdong_area", pearl_and_east)
    text = replace_named_block(
        text,
        "west_guangdong_area",
        """west_guangdong_area = { #7
\t665 666 2159 2160 2161 4945 4947
}""",
    )
    text = replace_named_block(
        text,
        "zhejiang_area",
        """zhejiang_area = { #5 (Taihu and Qiantang)
\t4950 5002 684 5003 2148
}

east_zhejiang_area = { #5 (Eastern Maritime Zhejiang)
\t2149 5004 5005 4951 1824
}

jinqu_chuzhou_area = { #4 (Jinhua, Quzhou and Chuzhou)
\t2150 5006 4956 5007
}""",
    )
    text = replace_named_block(
        text,
        "jiangxi_area",
        """jiangxi_area = { #5 (North Jiangxi)
\t683 2151 4979 4992 4993
}

south_jiangxi_area = { #5
\t670 1833 4980 4994 4995
}""",
    )
    text = replace_named_block(
        text,
        "fujian_area",
        """fujian_area = { #5 (East Fujian)
\t669 1829 4952 4953 4958
}

west_fujian_area = { #3
\t2152 2153 4957
}""",
    )
    text = replace_named_block(
        text,
        "taiwan_area",
        """taiwan_area = { #5
\t738 2154 2155 4955 4961
}""",
    )
    text = replace_named_block(
        text,
        "guangxi_area",
        """guangxi_area = { #4 (Zuojiang)
\t2162 2164 4954 4960
}

youjiang_area = { #4
\t664 1840 2163 4959
}""",
    )
    text = replace_named_block(
        text,
        "hunan_area",
        """dongting_area = { #4
\t672 4982 4996 4997
}

hunan_area = { #4 (Central Hunan)
\t671 2174 4983 4998
}

southwest_hunan_area = { #4
\t2173 4999 5000 5001
}""",
    )
    text = replace_named_block(
        text,
        "huguang_area",
        """hanjiang_xiangyun_area = { #3 (Han River and Xiang-Yun)
\t5008 2171 5010
}

jingyi_shinan_area = { #5 (Jingzhou, Yiling, Shinan, and Mianyang)
\t681 2172 5013 5014 5015
}

dean_qihuang_area = { #3 (Eastern Hubei)
\t5009 4197 5012
}

wuhan_enan_area = { #4 (Wuhan Three Towns and Xingguo)
\t4981 682 5011 5016
}""",
    )
    text = replace_named_block(
        text,
        "jiangsu_area",
        """xuhuai_haizhou_area = { #5 (North Jiangsu)
\t2141 5018 2142 5020 4196
}

huaiyang_tongtai_area = { #5 (Central Jiangsu)
\t685 5021 4977 5022 5023
}""",
    )
    text = replace_named_block(
        text,
        "south_jiangsu_area",
        """jinling_wuhui_area = { #6 (South Jiangsu)
\t1821 2145 5024 5025 1822 4976
}""",
    )
    text = replace_named_block(
        text,
        "sichuan_area",
        """sichuan_area = { #2 (Chengdu basin west)
\t679 4212
}

chongqing_area = { #5 (Ba and the upper Yangtze gorges)
\t680 5026 5027 4987 5028
}""",
    )
    text = replace_named_block(
        text,
        "north_henan_area",
        """north_henan_area = { #2 (Western Henan outside the royal domain)
\t692 1836
}

wangji_area = { #4 (Kaifeng royal domain)
\t688 4966 5030 5031
}""",
    )
    yangtze_area = """yangtze_river_area = { #9
\t5032 5033 5034 5035 5036 5037 5038 1655 1897
}

"""
    text = replace_once(
        text,
        "east_china_sea_area = {",
        yangtze_area + "east_china_sea_area = {",
        "Yangtze sea area insertion",
    )
    write_text(output, text)


def build_region(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/region.txt")

    def add_area(block: str) -> str:
        block = replace_once(
            block,
            "\t\tguangdong_area\n",
            "\t\tpearl_river_delta_area\n\t\tguangdong_area\n",
            "south_china_region areas",
        )
        block = replace_once(
            block,
            "\t\tfujian_area\n",
            "\t\tfujian_area\n\t\twest_fujian_area\n",
            "south_china_region Fujian areas",
        )
        block = replace_once(
            block,
            "\t\tjiangxi_area\n",
            "\t\tjiangxi_area\n\t\tsouth_jiangxi_area\n",
            "south_china_region Jiangxi areas",
        )
        block = replace_once(
            block,
            "\t\tzhejiang_area\n",
            "\t\tzhejiang_area\n\t\teast_zhejiang_area\n\t\tjinqu_chuzhou_area\n",
            "south_china_region Zhejiang areas",
        )
        block = replace_once(
            block,
            "\t\thunan_area\n",
            "\t\tdongting_area\n\t\thunan_area\n\t\tsouthwest_hunan_area\n",
            "south_china_region Hunan areas",
        )
        block = replace_once(
            block,
            "\t\thuguang_area\n",
            "\t\thanjiang_xiangyun_area\n\t\tjingyi_shinan_area\n"
            "\t\tdean_qihuang_area\n\t\twuhan_enan_area\n",
            "south_china_region Hubei areas",
        )
        block = replace_once(
            block,
            "\t\tsouth_jiangsu_area\n",
            "\t\tjinling_wuhui_area\n",
            "south_china_region South Jiangsu area",
        )
        return replace_once(
            block,
            "\t\tguangxi_area\n",
            "\t\tguangxi_area\n\t\tyoujiang_area\n",
            "south_china_region Guangxi areas",
        )

    text = modify_nested_block(text, "south_china_region", add_area)
    text = modify_nested_block(
        text,
        "north_china_region",
        lambda block: replace_once(
            block,
            "\t\tjiangsu_area\n",
            "\t\txuhuai_haizhou_area\n\t\thuaiyang_tongtai_area\n",
            "north_china_region North and Central Jiangsu areas",
        ),
    )
    text = modify_nested_block(
        text,
        "xinan_region",
        lambda block: replace_once(
            block,
            "\t\tsichuan_area\n",
            "\t\tsichuan_area\n\t\tchongqing_area\n",
            "xinan_region Chongqing area",
        ),
    )
    text = modify_nested_block(
        text,
        "north_china_region",
        lambda block: replace_once(
            block,
            "\t\tnorth_henan_area\n",
            "\t\tnorth_henan_area\n\t\twangji_area\n",
            "north_china_region royal domain area",
        ),
    )
    text = modify_nested_block(
        text,
        "east_china_sea_region",
        lambda block: append_to_named_block(
            block,
            "areas",
            "\t\tyangtze_river_area",
        ),
    )
    write_text(output, text)


def build_continent(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/continent.txt")
    text = append_to_named_block(
        text,
        "asia",
        "\t4942 4943 4944 4945 4946 4947 4948 4949 # B01 Guangdong",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4950 4951 4952 4953 4954 4955 4956 4957 4958 4959 4960 4961"
        " # P02 Southeast prepared",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4979 4980 4992 4993 4994 4995 # B07 Jiangxi",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4982 4983 4996 4997 4998 4999 5000 5001 # B07 Hunan",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t5002 5003 5004 5005 5006 5007 # B06 Zhejiang expansion",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4981 5008 5009 5010 5011 5012 5013 5014 5015 5016 # B10 Hubei",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4976 4977 5017 5018 5019 5020 5021 5022 5023 5024 5025"
        " # B11 Jiangsu",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4987 5026 5027 5028 # B09 Chongqing five-way split",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t5029 # B08 impassable Taiwan central range",
    )
    text = append_to_named_block(
        text,
        "asia",
        "\t4966 5030 5031 # B03 Kaifeng royal domain",
    )
    write_text(output, text)


def build_climate(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/climate.txt")
    text = append_to_named_block(
        text,
        "tropical",
        "\t4945 # B01 Gaozhou inherits the Leichow tropical climate",
    )
    text = append_to_named_block(
        text,
        "tropical",
        "\t4954 4955 4960 4961 # P02 southern subtropical frontier",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4942 4943 4944 4945 4946 4947 4948 4949 # B01 Guangdong",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4950 4951 4952 4953 4955 4956 4957 4958 4960 4961"
        " # P02 monsoon provinces",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4979 4980 4992 4993 4994 4995 # B07 Jiangxi",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4982 4983 4996 4997 4998 4999 5000 5001 # B07 Hunan",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t5002 5003 5004 5005 5006 5007 # B06 Zhejiang expansion",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4981 5008 5009 5010 5011 5012 5013 5014 5015 5016 # B10 Hubei",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4976 4977 5017 5018 5019 5020 5021 5022 5023 5024 5025"
        " # B11 Jiangsu",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4987 5026 5027 5028 # B09 Chongqing",
    )
    text = append_to_named_block(
        text,
        "impassable",
        "\t5029 # B08 Taiwan central range",
    )
    text = append_to_named_block(
        text,
        "normal_monsoon",
        "\t4966 5030 5031 # B03 Kaifeng royal domain",
    )
    write_text(output, text)


def build_terrain(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/terrain.txt")
    for province_id in (
        684, 1824, 2148, 2149, 2150,
        681, 682, 2172, 4197,
        685, 1821, 1822, 2141, 2142, 2145, 4196,
        680, 688,
    ):
        text = re.sub(rf"(?<!\d){province_id}(?!\d)", "", text)
    text = replace_once(
        text,
        "\t\t\t665 667 2156 2157 2159 2163 700",
        "\t\t\t665 667 2156 2157 2159 2163 700 4942 4943 4950 4954 "
        "4979 4982 684 2148 2149 5002 682 2171 2172 4981 5011 "
        "685 1821 1822 2141 2142 2145 4196 "
        "4976 4977 5017 5018 5019 5020 5021 5022 5023 5024 5025",
        "farmlands terrain override",
    )
    text = replace_once(
        text,
        "\t\t\t2146 2147 2152 2153 2158 2171 2173 2174 ",
        "\t\t\t2146 2147 2152 2153 2158 2174 "
        "4944 4945 4946 4947 4948 4949 4951 4952 4953 "
        "4956 4957 4958 4960 4961 4980 4983 4992 4993 4994 "
        "4996 4997 4998 5000 1824 2150 5003 5004 5005 5006 "
        "681 5012 5015 5016 ",
        "hills terrain override",
    )
    text = modify_nested_block(
        text,
        "grasslands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4955 4197 5009 5010 5014 # P02 Zhuluo and B10 Hubei plains",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4959 # P02 Qingyuan karst frontier",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4995 # B07 Nan'an Meiguan highlands",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t2173 4999 5001 # B07 Xiangxi and Nanling highlands",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t5007 # B06 Chuzhou Kuocang highlands",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t5008 5013 # B10 Yunyang and Shizhou highlands",
        ),
    )
    text = modify_nested_block(
        text,
        "hills",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t680 4987 5026 5027 # B09 Chongqing and Xiajiang hills",
        ),
    )
    text = modify_nested_block(
        text,
        "highlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t5028 # B09 Kuizhou gorge highlands",
        ),
    )
    text = modify_nested_block(
        text,
        "farmlands",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t688 5030 5031 # B03 Kaifeng, Zhengzhou and Chenliu plains",
        ),
    )
    text = modify_nested_block(
        text,
        "hills",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t4966 # B03 Xingyang and the Hulao approach",
        ),
    )
    text = modify_nested_block(
        text,
        "inland_ocean",
        lambda block: append_to_named_block(
            block,
            "terrain_override",
            "\t\t\t5032 5033 5034 5035 5036 5037 5038 1655 1897"
            " # Navigable Yangtze",
        ),
    )
    write_text(output, text)


def format_position_block(province_id: int, *, include_comment: bool = True) -> str:
    data = POSITION_DATA[province_id]
    positions = " ".join(f"{float(value):.3f}" for value in data["positions"])
    rotations = " ".join(f"{float(value):.3f}" for value in data["rotation"])
    heights = "0.000 0.000 1.000 0.000 0.000 0.000 0.000"
    comment = f"#{data['comment']}\n" if include_comment else ""
    return f"""{comment}{province_id}={{
\tposition={{
\t\t{positions}
\t}}
\trotation={{
\t\t{rotations}
\t}}
\theight={{
\t\t{heights}
\t}}
}}"""


def build_positions(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/positions.txt")
    for province_id in (
        664, 665, 667, 738, 1840, 2154, 2155, 2157, 2158, 2159,
        2162, 2163, 2164, 670, 671, 672, 683, 1833, 2151, 2173, 2174,
        684, 1824, 2148, 2149, 2150,
        681, 682, 2171, 2172, 4197,
        685, 1821, 1822, 2141, 2142, 2145, 4196,
        686, 1838, 2143, 2146, 2147,
        680, 688,
    ):
        text = replace_named_block(
            text,
            str(province_id),
            format_position_block(province_id, include_comment=False),
        )
    text = text.rstrip() + "\n\n"
    text += "\n\n".join(
        format_position_block(province_id)
        for province_id in ACTIVE_IDS
        if province_id != TAIWAN_MOUNTAIN_ID
    )
    write_text(output, text + "\n")


def build_adjacencies(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/adjacencies.csv")
    sentinel = "-1;-1;;-1;-1;-1;-1;-1;-1;"
    straits = (
        "2149;5004;sea;1373;-1;-1;-1;-1;Ningbo-Changguo (Zhoushan) Strait",
        "2145;685;sea;5033;-1;-1;-1;-1;Zhenjiang-Yangzhou crossing",
        "1821;2143;sea;5033;-1;-1;-1;-1;Nanjing-Fengyang crossing",
        "1821;1838;sea;5033;-1;-1;-1;-1;Nanjing-Hefei crossing",
        "2146;686;sea;5034;-1;-1;-1;-1;Ningguo-Anqing crossing",
        "4979;686;sea;5038;-1;-1;-1;-1;Jiujiang-Anqing crossing",
        "5011;682;sea;5035;-1;-1;-1;-1;Hankou-Wuchang crossing",
        "4981;682;sea;5035;-1;-1;-1;-1;Hanyang-Wuchang crossing",
        "5012;682;sea;5035;-1;-1;-1;-1;Huangzhou-Wuchang crossing",
        "2172;681;sea;5037;-1;-1;-1;-1;Jingzhou-Yichang crossing",
    )
    text = replace_once(
        text,
        sentinel,
        "\n".join(straits) + "\n" + sentinel,
        "Zhoushan and Yangtze strait adjacencies",
    )
    write_text(output, text)


def build_trade_winds(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "map/trade_winds.txt").rstrip()
    directions = {
        5032: -5,
        5033: 0,
        5034: 45,
        5035: 10,
        5036: 0,
        5037: -15,
        5038: 0,
    }
    additions = "\n".join(
        f"{province_id} = {direction}"
        for province_id, direction in directions.items()
    )
    write_text(output, text + "\n" + additions + "\n")


def append_members_to_outer_block(
    text: str,
    outer_name: str,
    member_ids: tuple[int, ...],
    comment: str,
) -> str:
    def modify_outer(block: str) -> str:
        member_start, member_end = find_named_block(block, "members")
        members = block[member_start:member_end]
        closing = members.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in member_ids)
            + f" # {comment}\n\t"
        )
        members = members[:closing].rstrip() + insertion + members[closing:]
        return block[:member_start] + members + block[member_end:]

    return modify_nested_block(text, outer_name, modify_outer)


def build_trade_nodes(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/tradenodes/00_tradenodes.txt")
    text = append_members_to_outer_block(
        text,
        "hangzhou",
        (4950, 4951, 4952, 4953, 4956, 4957, 4958)
        + JIANGXI_IDS
        + ZHEJIANG_IDS,
        "P02/B06 Zhejiang and Fujian plus B07 Jiangxi",
    )
    text = append_members_to_outer_block(
        text,
        "canton",
        IMPLEMENTED_IDS + (4954, 4955, 4959, 4960, 4961) + HUNAN_IDS,
        "B01 Guangdong, P02 Guangxi/Taiwan and B07 Hunan",
    )
    text = append_members_to_outer_block(
        text,
        "xian",
        HUBEI_NEW_IDS,
        "B10 Hubei refinement",
    )
    text = append_members_to_outer_block(
        text,
        "hangzhou",
        JIANGSU_NEW_IDS,
        "B11 Jiangsu refinement",
    )
    text = append_members_to_outer_block(
        text,
        "chengdu",
        CHONGQING_NEW_IDS,
        "B09 Chongqing five-way split",
    )
    text = append_members_to_outer_block(
        text,
        "xian",
        WANGJI_NEW_IDS,
        "B03 Kaifeng royal domain",
    )
    write_text(
        output,
        text,
    )


def build_trade_companies(vanilla_root: Path, output: Path) -> None:
    text = read_text(vanilla_root / "common/trade_companies/00_trade_companies.txt")

    def add_company_provinces(
        block: str,
        province_ids: tuple[int, ...],
        comment: str,
    ) -> str:
        start, end = find_named_block(block, "provinces")
        provinces = block[start:end]
        closing = provinces.rfind("}")
        insertion = (
            "\n\t\t"
            + " ".join(str(value) for value in province_ids)
            + f" # {comment}\n\t"
        )
        provinces = provinces[:closing].rstrip() + insertion + provinces[closing:]
        return block[:start] + provinces + block[end:]

    text = modify_nested_block(
        text,
        "trade_company_south_china",
        lambda block: add_company_provinces(
            block,
            IMPLEMENTED_IDS + (4954, 4955, 4959, 4960, 4961) + HUNAN_IDS,
            "B01 Guangdong, P02 Guangxi/Taiwan and B07 Hunan",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_east_china",
        lambda block: add_company_provinces(
            block,
            (4950, 4951, 4952, 4953, 4956, 4957, 4958)
            + JIANGXI_IDS
            + ZHEJIANG_IDS,
            "P02/B06 Zhejiang and Fujian plus B07 Jiangxi",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_east_china",
        lambda block: add_company_provinces(
            block,
            JIANGSU_NEW_IDS,
            "B11 Jiangsu refinement",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_xian",
        lambda block: add_company_provinces(
            block,
            HUBEI_NEW_IDS,
            "B10 Hubei refinement",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_chengdu",
        lambda block: add_company_provinces(
            block,
            CHONGQING_NEW_IDS,
            "B09 Chongqing five-way split",
        ),
    )
    text = modify_nested_block(
        text,
        "trade_company_xian",
        lambda block: add_company_provinces(
            block,
            WANGJI_NEW_IDS,
            "B03 Kaifeng royal domain",
        ),
    )
    write_text(output, text)


def write_report(
    report_path: Path,
    mod_root: Path,
    geometry_report: dict[str, object],
    outputs: list[Path],
) -> None:
    report = {
        "status": (
            "B01_P02_B03_B06_B07_B09_B10_B11_AND_YANGTZE_ASSETS_PREPARED"
        ),
        "scope": "Southeast including Taiwan, Kaifeng royal domain, Chongqing, Hubei, and Jiangsu implementation",
        "baseline_version": geometry_report["baseline_version"],
        "baseline_verified_by_sha256": geometry_report[
            "baseline_verified_by_sha256"
        ],
        "baseline_source": "EU4_INSTALL_ROOT",
        "geometry_source": geometry_report["source_policy"],
        "canonical_geometry_preserved": True,
        "mod_root": mod_root.name,
        "implemented_ids": list(IMPLEMENTED_IDS),
        "prepared_ids": list(PREPARED_IDS),
        "jiangxi_ids": list(JIANGXI_IDS),
        "hunan_ids": list(HUNAN_IDS),
        "zhejiang_ids": list(ZHEJIANG_IDS),
        "hubei_ids": list(HUBEI_ALL_IDS),
        "jiangsu_ids": list(JIANGSU_ALL_IDS),
        "taiwan_ids": list(TAIWAN_REVIEW_IDS),
        "chongqing_ids": list(CHONGQING_ALL_IDS),
        "wangji_ids": list(WANGJI_ALL_IDS),
        "max_provinces": GAME_MAX_PROVINCES,
        "changed_pixels": geometry_report["changed_pixels"],
        "province_pixels": geometry_report["province_pixels"],
        "outputs": {
            str(path.relative_to(mod_root)): {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in outputs
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, required=True)
    parser.add_argument("--mod-root", type=Path, default=DEFAULT_MOD_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    vanilla_root = args.vanilla_root.expanduser().resolve()
    mod_root = args.mod_root.expanduser().resolve()
    if not (mod_root / "descriptor.mod").is_file():
        raise ValueError(f"Not an EU4 mod root: {mod_root}")

    registry_rows = load_active_registry(args.registry)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    provinces_output = mod_root / "map/provinces.bmp"
    geometry_report = audit_manual_geometry(
        vanilla_root,
        provinces_output,
        registry_rows,
        config,
    )

    builders = [
        (build_definition, mod_root / "map/definition.csv"),
        (build_default_map, mod_root / "map/default.map"),
        (build_area, mod_root / "map/area.txt"),
        (build_region, mod_root / "map/region.txt"),
        (build_continent, mod_root / "map/continent.txt"),
        (build_climate, mod_root / "map/climate.txt"),
        (build_terrain, mod_root / "map/terrain.txt"),
        (build_positions, mod_root / "map/positions.txt"),
        (build_adjacencies, mod_root / "map/adjacencies.csv"),
        (build_trade_winds, mod_root / "map/trade_winds.txt"),
        (
            build_trade_nodes,
            mod_root / "common/tradenodes/00_tradenodes.txt",
        ),
        (
            build_trade_companies,
            mod_root / "common/trade_companies/00_trade_companies.txt",
        ),
    ]
    terrain_bitmap = mod_root / "map/terrain.bmp"
    if not terrain_bitmap.is_file():
        raise ValueError("map/terrain.bmp is required for the Taiwan central range")
    heightmap_bitmap = mod_root / "map/heightmap.bmp"
    rivers_bitmap = mod_root / "map/rivers.bmp"
    if not heightmap_bitmap.is_file() or not rivers_bitmap.is_file():
        raise ValueError(
            "map/heightmap.bmp and map/rivers.bmp are required for the "
            "navigable Yangtze"
        )
    outputs = [
        provinces_output,
        terrain_bitmap,
        heightmap_bitmap,
        rivers_bitmap,
    ]
    for builder, output in builders:
        if builder is build_definition:
            builder(vanilla_root, output, registry_rows)
        else:
            builder(vanilla_root, output)
        outputs.append(output)

    write_report(
        report_path=args.report,
        mod_root=mod_root,
        geometry_report=geometry_report,
        outputs=outputs,
    )
    print(f"{provinces_output}: canonical hand-drawn geometry preserved")
    print(f"{mod_root}: active assets written through province ID 5038")
    print(
        f"{args.report}: "
        "B01_P02_B03_B06_B07_B09_B10_B11_AND_YANGTZE_ASSETS_PREPARED"
    )


if __name__ == "__main__":
    main()
