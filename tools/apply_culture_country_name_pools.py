#!/usr/bin/env python3
"""Generate culture-appropriate Chinese country name pools for EU4.

The readable pools in this file are ordinary UTF-8.  Generated country files
use the raw double-byte escape format expected by the installed EU4 Chinese
patch.  Only ``monarch_names`` and ``leader_names`` are replaced; colors,
scores, army names, ship names and every other country setting are preserved.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from encode_eu4_chinese_localisation import to_escaped_bytes


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
COUNTRIES = MOD / "common/countries"
COUNTRY_HISTORY = MOD / "history/countries"
DEFAULT_VANILLA_ROOT = Path(
    r"E:/Program Files (x86)/Steam/steamapps/common/Europa Universalis IV"
)

GIVEN_NAME_SETS_BASE: dict[str, dict[str, tuple[str, ...]]] = {
    "han_classical": {
        "male": (
            "承志", "景明", "弘毅", "守仁", "文昭", "世安", "维桢", "启元",
            "克明", "允中", "伯谦", "仲达", "季良", "德裕", "元恺", "士衡",
            "子敬", "公辅", "廷玉", "绍宗", "彦章", "思齐", "惟新", "国维",
        ),
        "female": (
            "淑贞", "慧兰", "静姝", "令仪", "婉容", "清照",
            "玉英", "秀华", "素娥", "兰芳", "月娥", "瑞云",
        ),
    },
    "han_southern": {
        "male": (
            "文盛", "文远", "景泰", "世昌", "弘道", "启明", "继贤", "承恩",
            "守礼", "维新", "绍祖", "宗彦", "德润", "伯恭", "仲贤", "季安",
            "子谦", "廷芳", "瑞卿", "士元", "克勤", "允恭", "思远", "彦清",
        ),
        "female": (
            "惠娘", "兰英", "玉娘", "月华", "秀娘", "瑞娘",
            "静娴", "婉贞", "素云", "桂香", "春兰", "秋月",
        ),
    },
    "han_western": {
        "male": (
            "彦昭", "国忠", "守义", "承武", "景隆", "文泰", "弘烈", "世勋",
            "克复", "廷璋", "思恭", "德威", "绍武", "宗翰", "伯雄", "仲武",
            "季昌", "子英", "维岳", "启忠", "允成", "元礼", "怀德", "安国",
        ),
        "female": (
            "令月", "玉环", "静仪", "淑英", "惠芳", "兰玉",
            "月娘", "秀贞", "素英", "瑞香", "春华", "秋娘",
        ),
    },
    "zhou_classical": {
        "male": (
            "重耳", "夷吾", "小白", "纠", "寤生", "忽", "突", "御寇",
            "无宇", "午", "光", "夫差", "勾践", "申生", "圉", "完",
            "友", "黑肱", "辄", "蒯聩", "宜臼", "寿梦", "诸樊", "余祭",
        ),
        "female": (
            "静姝", "庄姜", "文姜", "宣姜", "哀姜", "叔隗",
            "季隗", "夏姬", "息妫", "樊姬", "孟任", "少姜",
        ),
    },
    "zhuang": {
        "male": (
            "智高", "宗旦", "继宗", "存福", "全福", "大惠", "文显", "志威",
            "世隆", "阿榜", "世念", "侬峒", "金龙", "保德", "福成", "达安",
        ),
        "female": ("阿侬", "亚仙", "娅兰", "娅宁", "银花", "玉凤", "凤英", "月妹"),
    },
    "miao": {
        "male": (
            "阿仰", "阿榜", "阿旺", "金保", "银保", "保佑", "务相", "务德",
            "务学", "德榜", "秀榜", "龙保", "该宋", "该昂", "该年", "该端",
        ),
        "female": ("阿彩", "阿莎", "仰妮", "金妹", "银花", "秀娘", "玉香", "阿仰"),
    },
    "yi": {
        "male": (
            "惹古", "尔古", "阿木", "阿支", "木呷", "拉铁", "日火", "吉克",
            "曲比", "沙马", "俄木", "海来", "阿侯", "勒格", "马海", "吉狄",
        ),
        "female": ("阿依", "阿呷", "曲莫", "沙沙", "妮古", "惹作", "木乃", "尔布"),
    },
    "bai": {
        "male": (
            "思平", "思良", "思聪", "思英", "素顺", "素英", "素隆", "正明",
            "正淳", "正严", "兴智", "智祥", "祥兴", "隆舜", "舜化", "和誉",
        ),
        "female": ("金姑", "玉娘", "阿盖", "月华", "素娥", "金花", "玉凤", "阿慈"),
    },
    "tibetan": {
        "male": (
            "扎西多吉", "次仁旺堆", "丹增罗布", "洛桑扎西", "索朗多杰",
            "格桑次仁", "尼玛多吉", "普布次仁", "贡觉曲培", "阿旺洛桑",
            "仁青宁布", "桑珠次仁", "旦增曲扎", "扎西顿珠", "多吉才仁",
            "平措旺堆", "洛桑丹增", "白玛多吉", "达瓦次仁", "益西旦增",
        ),
        "female": (
            "卓玛央宗", "格桑德吉", "白玛曲吉", "德庆曲珍", "次仁拉姆", "益西拉姆",
            "尼玛拉姆", "卓嘎拉姆", "索朗仓决", "旦增措姆", "白玛央宗", "曲珍卓玛",
        ),
    },
    "mongol": {
        "male": (
            "阿台", "阿岱", "阿鲁台", "也先", "脱脱", "巴图", "博罗", "满都鲁",
            "孛来", "孛罗忽", "乌格齐", "阿寨", "伯颜", "赛音", "布延", "额森",
            "帖木儿", "忽必烈", "蒙克", "脱欢", "阿剌知院", "阿噶巴尔济",
        ),
        "female": ("满都海", "孛儿帖", "海伦", "萨仁", "其其格", "阿茹娜", "乌云", "苏布德", "阿拉坦", "娜仁"),
    },
    "oirat": {
        "male": (
            "脱欢", "也先", "阿睦尔", "巴图拉", "哈剌忽剌", "僧格", "噶尔丹", "策妄",
            "达瓦齐", "固始", "鄂齐尔图", "阿拉布坦", "车凌", "和鄂尔勒克", "拜巴噶斯", "巴图尔",
            "乌巴什", "罗卜藏", "丹津", "班第",
        ),
        "female": ("满都海", "孛儿帖", "萨仁", "其其格", "乌云", "娜仁", "阿拉坦", "苏布德", "托娅", "高娃"),
    },
    "vietnamese": {
        "male": (
            "季犛", "汉苍", "澄", "利", "龙", "灏", "濬", "宜民", "思诚",
            "铮", "椿", "晪", "晛", "惠", "旵", "廌", "元龙", "光缵",
        ),
        "female": ("金英", "翠簪", "碧玉", "芳娥", "清草", "玄珍", "玉欣", "玉瑶"),
    },
    "diqiang": {
        "male": (
            "阿豺", "慕璝", "拾寅", "树洛干", "利鹿孤", "傉檀", "炽磐", "暮末",
            "弥姐", "梁祚", "伐德", "硕德", "像舒治", "阿若", "折掘", "吕纂",
            "乞伏", "吐谷浑",
        ),
        "female": ("阿若", "念珠", "娥遮", "折香", "勒姐", "月奴", "弥玉", "阿真"),
    },
}


# EU4 assigns regnal numbers when a country draws the same monarch given name
# more than once.  Small hand-written pools therefore produce many "I/II/III"
# rulers over a long campaign.  Keep the historical seed names above, then add
# deterministic culture-specific combinations.  Two-character Han names and
# transliterated non-Han names give substantially more variety without mixing
# unrelated naming traditions.
TARGET_MALE_NAMES = 256
TARGET_FEMALE_NAMES = 128

NAME_COMPONENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "han_classical": {
        "male_left": (
            "承", "景", "弘", "守", "文", "世", "维", "启", "克", "允",
            "伯", "仲", "季", "德", "元", "士", "子", "廷", "绍", "彦",
        ),
        "male_right": (
            "志", "明", "毅", "仁", "昭", "安", "桢", "元", "中", "谦",
            "达", "良", "裕", "恺", "衡", "敬", "辅", "玉", "宗", "章",
        ),
        "female_left": (
            "淑", "慧", "静", "令", "婉", "清", "玉", "秀", "素", "兰", "月", "瑞",
        ),
        "female_right": (
            "贞", "兰", "姝", "仪", "容", "华", "英", "娥", "芳", "云", "娘", "月",
        ),
    },
    "han_southern": {
        "male_left": (
            "文", "景", "世", "弘", "启", "继", "承", "守", "维", "绍",
            "宗", "德", "伯", "仲", "季", "子", "廷", "瑞", "士", "克",
        ),
        "male_right": (
            "盛", "远", "泰", "昌", "道", "明", "贤", "恩", "礼", "新",
            "祖", "彦", "润", "恭", "安", "谦", "芳", "卿", "元", "勤",
        ),
        "female_left": (
            "惠", "兰", "玉", "月", "秀", "瑞", "静", "婉", "素", "桂", "春", "秋",
        ),
        "female_right": (
            "娘", "英", "华", "娴", "贞", "云", "香", "兰", "月", "芳", "容", "仪",
        ),
    },
    "han_western": {
        "male_left": (
            "彦", "国", "守", "承", "景", "文", "弘", "世", "克", "廷",
            "思", "德", "绍", "宗", "伯", "仲", "季", "子", "维", "启",
        ),
        "male_right": (
            "昭", "忠", "义", "武", "隆", "泰", "烈", "勋", "复", "璋",
            "恭", "威", "翰", "雄", "昌", "英", "岳", "成", "礼", "德",
        ),
        "female_left": (
            "令", "玉", "静", "淑", "惠", "兰", "月", "秀", "素", "瑞", "春", "秋",
        ),
        "female_right": (
            "月", "环", "仪", "英", "芳", "玉", "娘", "贞", "香", "华", "云", "容",
        ),
    },
    "zhou_classical": {
        "male_left": (
            "伯", "仲", "叔", "季", "子", "公", "太", "少", "无", "有",
            "元", "昭", "景", "成", "怀", "惠", "灵", "庄", "襄", "顷",
        ),
        "male_right": (
            "牙", "友", "生", "光", "午", "完", "胜", "黑", "赤", "白",
            "喜", "忌", "寿", "梦", "同", "夷", "申", "章", "款", "捷",
        ),
        "female_left": (
            "孟", "仲", "叔", "季", "伯", "少", "文", "庄", "宣", "哀", "穆", "敬",
        ),
        "female_right": (
            "姜", "姬", "妫", "隗", "任", "嬴", "姒", "娥", "姝", "媛", "华", "兰",
        ),
    },
    "zhuang": {
        "male_left": (
            "阿", "亚", "达", "岑", "侬", "依", "布", "陆", "覃", "班",
            "波", "莫", "罗", "蒙", "纳", "隆", "农", "韦", "蓝", "甘",
        ),
        "male_right": (
            "高", "旦", "福", "威", "安", "成", "德", "龙", "保", "宁",
            "壮", "明", "盛", "康", "金", "良", "文", "勇", "泰", "全",
        ),
        "female_left": (
            "阿", "亚", "娅", "银", "玉", "凤", "月", "兰", "依", "莫", "覃", "侬",
        ),
        "female_right": (
            "侬", "仙", "兰", "宁", "花", "凤", "英", "妹", "香", "玉", "月", "珍",
        ),
    },
    "miao": {
        "male_left": (
            "阿", "务", "金", "银", "龙", "仰", "榜", "保", "德", "秀",
            "该", "麻", "石", "蒙", "昂", "亚", "巴", "吴", "廖", "雷",
        ),
        "male_right": (
            "彩", "莎", "旺", "保", "佑", "相", "德", "学", "榜", "秀",
            "宋", "昂", "年", "端", "龙", "金", "勇", "安", "良", "贵",
        ),
        "female_left": (
            "阿", "金", "银", "秀", "玉", "仰", "龙", "彩", "莎", "亚", "务", "蒙",
        ),
        "female_right": (
            "彩", "莎", "妮", "妹", "花", "娘", "香", "仰", "兰", "玉", "云", "英",
        ),
    },
    "yi": {
        "male_left": (
            "阿", "曲", "吉", "沙", "俄", "勒", "海", "马", "苏", "木",
            "日", "拉", "惹", "尔", "布", "格", "克", "洛", "瓦", "者",
        ),
        "male_right": (
            "木", "古", "支", "呷", "铁", "火", "克", "比", "马", "侯",
            "格", "海", "狄", "乃", "布", "作", "依", "惹", "莫", "沙",
        ),
        "female_left": (
            "阿", "曲", "沙", "妮", "惹", "木", "尔", "吉", "俄", "依", "海", "苏",
        ),
        "female_right": (
            "依", "呷", "莫", "沙", "古", "作", "乃", "布", "妮", "木", "惹", "果",
        ),
    },
    "bai": {
        "male_left": (
            "思", "素", "正", "兴", "智", "祥", "隆", "舜", "和", "仁",
            "义", "德", "文", "善", "明", "承", "宝", "元", "景", "世",
        ),
        "male_right": (
            "平", "良", "聪", "英", "顺", "隆", "明", "淳", "严", "智",
            "祥", "兴", "舜", "化", "誉", "安", "德", "和", "昌", "泰",
        ),
        "female_left": (
            "金", "玉", "阿", "月", "素", "白", "金花", "兰", "秀", "慈", "银", "云",
        ),
        "female_right": (
            "姑", "娘", "盖", "华", "娥", "花", "凤", "慈", "英", "兰", "月", "香",
        ),
    },
    "tibetan": {
        "male_left": (
            "扎西", "次仁", "丹增", "洛桑", "索朗", "格桑", "尼玛", "普布", "贡觉", "阿旺",
            "仁青", "桑珠", "旦增", "白玛", "达瓦", "益西", "平措", "嘉木样", "曲吉", "旺秋",
        ),
        "male_right": (
            "多吉", "旺堆", "罗布", "扎西", "次仁", "曲培", "洛桑", "丹增", "顿珠", "宁布",
            "曲扎", "平措", "才仁", "仁增", "嘉措", "桑布", "坚赞", "旺秋", "索南", "赤列",
        ),
        "female_left": (
            "卓玛", "格桑", "白玛", "德庆", "次仁", "益西", "尼玛", "卓嘎", "索朗", "旦增", "曲珍", "达瓦",
        ),
        "female_right": (
            "央宗", "德吉", "曲吉", "曲珍", "拉姆", "措姆", "卓玛", "仓决", "央金", "玉珍", "白姆", "吉宗",
        ),
    },
    "mongol": {
        "male_left": (
            "阿", "巴", "博", "孛", "乌", "伯", "赛", "布", "额", "帖",
            "忽", "蒙", "脱", "满", "阿剌", "阿噶", "合撒", "兀良", "哈剌", "博尔",
        ),
        "male_right": (
            "台", "岱", "鲁台", "图", "罗", "颜", "音", "延", "森", "木儿",
            "必烈", "克", "欢", "寨", "忽", "济", "帖木儿", "巴特尔", "汗", "不花",
        ),
        "female_left": (
            "满都", "孛儿", "萨", "其其", "阿茹", "乌", "苏布", "阿拉", "娜", "托", "高", "海",
        ),
        "female_right": (
            "海", "帖", "仁", "格", "娜", "云", "德", "坦", "仁", "娅", "娃", "伦",
        ),
    },
    "oirat": {
        "male_left": (
            "脱", "也", "阿睦", "巴图", "哈剌", "僧", "噶尔", "策", "达瓦", "固始",
            "鄂齐", "阿拉", "车", "和鄂", "拜巴", "乌巴", "罗卜", "丹", "班", "辉特",
        ),
        "male_right": (
            "欢", "先", "尔", "拉", "忽剌", "格", "丹", "妄", "齐", "尔图",
            "布坦", "凌", "尔勒克", "噶斯", "图尔", "什", "藏", "津", "第", "巴特尔",
        ),
        "female_left": (
            "满都", "孛儿", "萨", "其其", "乌", "娜", "阿拉", "苏布", "托", "高", "海", "辉特",
        ),
        "female_right": (
            "海", "帖", "仁", "格", "云", "仁", "坦", "德", "娅", "娃", "伦", "花",
        ),
    },
    "vietnamese": {
        "male_left": (
            "光", "日", "维", "福", "景", "明", "元", "文", "国", "世",
            "承", "弘", "绍", "思", "正", "隆", "永", "显", "德", "英",
        ),
        "male_right": (
            "利", "龙", "灏", "濬", "民", "诚", "铮", "椿", "晪", "晛",
            "惠", "旵", "廌", "缵", "英", "宗", "德", "盛", "安", "平",
        ),
        "female_left": (
            "金", "翠", "碧", "芳", "清", "玄", "玉", "月", "兰", "明", "瑞", "秀",
        ),
        "female_right": (
            "英", "簪", "玉", "娥", "草", "珍", "欣", "瑶", "兰", "香", "云", "华",
        ),
    },
    "diqiang": {
        "male_left": (
            "阿", "慕", "树", "利", "傉", "炽", "弥", "梁", "伐", "硕",
            "像", "乞", "吐", "折", "拓", "雷", "苻", "姚", "吕", "党项",
        ),
        "male_right": (
            "豺", "璝", "寅", "干", "孤", "檀", "磐", "末", "姐", "祚",
            "德", "治", "若", "纂", "伏", "谷浑", "掘", "跋", "弥", "隆",
        ),
        "female_left": (
            "阿", "念", "娥", "折", "勒", "月", "弥", "慕", "乞", "吐", "白", "雷",
        ),
        "female_right": (
            "若", "珠", "遮", "香", "姐", "奴", "玉", "真", "兰", "月", "娥", "英",
        ),
    },
}


def expanded_name_pool(
    seed: tuple[str, ...],
    left: tuple[str, ...],
    right: tuple[str, ...],
    target: int,
) -> tuple[str, ...]:
    names = list(dict.fromkeys(seed))
    for first in left:
        for second in right:
            candidate = first + second
            if first == second or candidate in names:
                continue
            names.append(candidate)
            if len(names) >= target:
                return tuple(names)
    raise ValueError(f"Only generated {len(names)} of {target} requested names")


def build_given_name_sets() -> dict[str, dict[str, tuple[str, ...]]]:
    result: dict[str, dict[str, tuple[str, ...]]] = {}
    for set_name, seeds in GIVEN_NAME_SETS_BASE.items():
        components = NAME_COMPONENTS[set_name]
        result[set_name] = {
            "male": expanded_name_pool(
                seeds["male"],
                components["male_left"],
                components["male_right"],
                TARGET_MALE_NAMES,
            ),
            "female": expanded_name_pool(
                seeds["female"],
                components["female_left"],
                components["female_right"],
                TARGET_FEMALE_NAMES,
            ),
        }
    return result


GIVEN_NAME_SETS = build_given_name_sets()


# Han-derived cultures share appropriate given-name traditions but retain
# regional surname composition.  Non-Han cultures have independent given-name
# and clan pools and never fall back to the Han sets here.
CULTURE_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "gdd_zhongyuan": ("zhou_classical", ("姬", "王", "李", "张", "刘", "赵", "郑", "韩", "魏", "陈", "宋", "郭", "许", "冯", "杨", "司马")),
    "gdd_jianghuai": ("han_classical", ("朱", "徐", "陈", "王", "张", "刘", "吴", "周", "沈", "陆", "顾", "蒋", "汪", "姚", "董", "方")),
    "gdd_chu": ("zhou_classical", ("熊", "屈", "景", "昭", "项", "伍", "斗", "成", "潘", "田", "黄", "向", "宋", "申", "白", "叶")),
    "gdd_gan": ("han_southern", ("熊", "胡", "罗", "余", "万", "彭", "邓", "涂", "饶", "廖", "曾", "傅", "徐", "周", "吴", "谢")),
    "gdd_hakka": ("han_southern", ("谢", "钟", "廖", "赖", "曾", "叶", "罗", "温", "丘", "蓝", "范", "刘", "黄", "陈", "邓", "何")),
    "gdd_gui": ("han_southern", ("周", "唐", "梁", "石", "廖", "莫", "韦", "覃", "黄", "李", "陆", "蓝", "蒙", "岑", "蒋", "苏")),
    "gdd_shu": ("han_western", ("李", "张", "王", "刘", "杨", "陈", "赵", "何", "罗", "冯", "谯", "费", "庞", "法", "秦", "杜")),
    "gdd_dian": ("han_western", ("爨", "孟", "雍", "高", "段", "董", "杨", "李", "赵", "罗", "尹", "寸", "王", "张")),
    "gdd_jin": ("zhou_classical", ("赵", "魏", "韩", "智", "范", "中行", "祁", "羊舌", "狐", "郤", "先", "栾", "郭", "裴", "王", "杨")),
    "gdd_qi": ("zhou_classical", ("姜", "田", "高", "国", "鲍", "晏", "崔", "庆", "管", "陈", "卢", "邴", "孙", "王", "孔", "徐")),
    "gdd_yan": ("zhou_classical", ("姬", "召", "乐", "剧", "郭", "祖", "韩", "卢", "高", "张", "刘", "王", "李", "慕容", "鲜于", "公孙")),
    "gdd_long": ("han_western", ("李", "赵", "董", "牛", "马", "韩", "杨", "索", "阴", "麹", "令狐", "盖", "辛", "皇甫", "梁", "安")),
    "gdd_guangfu": ("han_southern", ("陈", "李", "黄", "张", "梁", "何", "罗", "谭", "邓", "冯", "黎", "叶", "钟", "卢", "伍", "麦")),
    "gdd_wu": ("han_southern", ("姬", "吴", "孙", "顾", "陆", "朱", "张", "钱", "沈", "周", "徐", "虞", "贺", "凌", "丁", "施")),
    "gdd_min": ("han_southern", ("陈", "林", "黄", "郑", "詹", "邱", "何", "胡", "谢", "蔡", "许", "苏", "叶", "卢", "方", "翁")),
    "gdd_songwei": ("zhou_classical", ("子", "孔", "戴", "向", "华", "乐", "司马", "殷", "卫", "石", "宁", "孙", "宋", "曹", "商", "微")),
    "gdd_dongyi": ("zhou_classical", ("姜", "嬴", "妫", "姚", "任", "风", "己", "曹", "董", "彭", "偃", "子", "莱", "纪", "莒", "徐")),
    "gdd_zhuang": ("zhuang", ("莫", "韦", "覃", "农", "黄", "岑", "闭", "蒙", "罗", "甘", "侬", "蓝", "陆", "廖")),
    "miao": ("miao", ("吴", "龙", "廖", "石", "麻", "文", "龚", "蒲", "向", "舒", "皮", "马", "熊", "陶", "雷", "蒙")),
    "yi": ("yi", ("曲比", "吉克", "沙马", "阿侯", "俄木", "勒格", "海来", "马海", "吉狄", "苏呷", "阿说", "木乃")),
    "bai": ("bai", ("段", "高", "董", "杨", "赵", "王", "蒙", "尹", "白", "张", "李", "苏")),
    # EU4 always combines a given name with a dynasty token.  Tibetan people
    # traditionally often have no surname, so historical houses/regions are
    # used here instead of forcing Han surnames onto them.
    "tibetan": ("tibetan", ("噶尔", "琼波", "悉补野", "帕竹", "仁蚌", "萨迦", "止贡", "雅隆", "工布", "康巴", "安多", "朗氏")),
    "mongol": ("mongol", ("孛儿只斤", "弘吉剌", "札剌亦儿", "兀良哈", "汪古", "克烈", "乃蛮", "蔑儿乞", "塔塔儿", "土默特", "科尔沁", "喀尔喀")),
    "oirats": ("oirat", ("绰罗斯", "和硕特", "杜尔伯特", "土尔扈特", "辉特", "准噶尔", "斡亦剌", "巴尔虎", "鄂尔勒克", "克烈")),
    "vietnamese": ("vietnamese", ("黎", "陈", "阮", "胡", "莫", "郑", "吴", "范", "潘", "武", "邓", "裴", "杜", "杨", "丁", "何")),
    "gdd_diqiang": ("diqiang", ("苻", "姚", "吕", "杨", "窦", "雷", "烧当", "先零", "白马", "宕昌", "乞伏", "拓跋", "折掘", "党项")),
}


TAG_PATTERN = re.compile(r'^\s*([A-Z0-9]{3})\s*=\s*"countries/([^\"]+)"', re.MULTILINE)
PRIMARY_CULTURE_PATTERN = re.compile(r"^\s*primary_culture\s*=\s*(\S+)", re.MULTILINE)
GENERATED_COMMENT_PATTERN = re.compile(
    rb"(?m)^[ \t]*# Culture-specific Chinese personal names \([^\r\n]+\)\.\r?\n"
)


def country_tag_map(vanilla_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for directory in (
        vanilla_root / "common/country_tags",
        MOD / "common/country_tags",
    ):
        for path in sorted(directory.glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            result.update(TAG_PATTERN.findall(text))
    return result


def active_country_files(vanilla_root: Path) -> dict[str, str]:
    tags = country_tag_map(vanilla_root)
    result: dict[str, str] = {}
    for history_path in sorted(COUNTRY_HISTORY.glob("*.txt")):
        tag = history_path.name[:3]
        text = history_path.read_text(encoding="utf-8-sig", errors="replace")
        culture_match = PRIMARY_CULTURE_PATTERN.search(text)
        if not culture_match:
            raise ValueError(f"{history_path.name}: missing primary_culture")
        if tag not in tags:
            raise ValueError(f"{history_path.name}: country tag is not declared")
        country_file = tags[tag]
        culture = culture_match.group(1)
        previous = result.get(country_file)
        if previous is not None and previous != culture:
            raise ValueError(
                f"{country_file}: shared by incompatible cultures {previous} and {culture}"
            )
        result[country_file] = culture
    return result


def remove_assignment_block(data: bytes, assignment: str) -> bytes:
    pattern = re.compile(
        rb"(?m)^[ \t]*" + re.escape(assignment.encode("ascii")) + rb"[ \t]*=[ \t]*\{"
    )
    match = pattern.search(data)
    if not match:
        return data
    depth = 0
    end = None
    for index in range(match.end() - 1, len(data)):
        byte = data[index]
        if byte == ord("{"):
            depth += 1
        elif byte == ord("}"):
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise ValueError(f"Unclosed {assignment} block")
    while end < len(data) and data[end] in b" \t":
        end += 1
    if data[end:end + 2] == b"\r\n":
        end += 2
    elif data[end:end + 1] == b"\n":
        end += 1
    return data[:match.start()] + data[end:]


def readable_name_block(culture: str, newline: str) -> str:
    if culture not in CULTURE_SPECS:
        raise ValueError(f"No Chinese name pool defined for culture {culture}")
    given_set_name, surnames = CULTURE_SPECS[culture]
    given = GIVEN_NAME_SETS[given_set_name]
    lines = [
        f"# Culture-specific Chinese personal names ({culture}).",
        "monarch_names = {",
    ]
    lines.extend(f'    "{name} #0" = 10' for name in given["male"])
    lines.extend(f'    "{name} #0" = -1' for name in given["female"])
    lines.extend(("}", "", "leader_names = {"))
    lines.extend(f'    "{surname}"' for surname in surnames)
    lines.extend(("}", ""))
    return newline.join(lines)


def expected_suffix(culture: str, newline: str) -> bytes:
    return to_escaped_bytes(readable_name_block(culture, newline))


def source_country_path(country_file: str, vanilla_root: Path) -> Path:
    local = COUNTRIES / country_file
    if local.exists():
        return local
    inherited = vanilla_root / "common/countries" / country_file
    if not inherited.exists():
        raise FileNotFoundError(f"Missing country definition: {country_file}")
    return inherited


def generated_country_data(data: bytes, culture: str) -> bytes:
    # Keep generated mixed-byte scripts on LF.  Literal CR bytes make Git's
    # text diff treat every line as trailing whitespace on Windows.
    data = data.replace(b"\r\n", b"\n")
    # Keep generated overrides deterministic and avoid legacy trailing spaces
    # being reported as errors by Git's whitespace checker.
    data = re.sub(rb"[ \t]+(?=\n)", b"", data)
    newline_bytes = b"\n"
    newline = "\n"
    data = GENERATED_COMMENT_PATTERN.sub(b"", data)
    data = remove_assignment_block(data, "monarch_names")
    data = remove_assignment_block(data, "leader_names")
    data = data.rstrip(b" \t\r\n") + newline_bytes * 2
    return data + expected_suffix(culture, newline)


def apply(vanilla_root: Path, check: bool) -> dict[str, object]:
    assignments = active_country_files(vanilla_root)
    cultures: Counter[str] = Counter()
    changed: list[str] = []
    for country_file, culture in sorted(assignments.items()):
        cultures[culture] += 1
        source = source_country_path(country_file, vanilla_root)
        current = source.read_bytes()
        expected = generated_country_data(current, culture)
        target = COUNTRIES / country_file
        if check:
            if not target.exists():
                raise ValueError(f"{country_file}: generated mod override is missing")
            actual = target.read_bytes()
            if actual != generated_country_data(actual, culture):
                raise ValueError(f"{country_file}: Chinese name pool is stale or malformed")
            for assignment in (b"monarch_names", b"leader_names"):
                if len(re.findall(rb"(?m)^\s*" + assignment + rb"\s*=", actual)) != 1:
                    raise ValueError(f"{country_file}: expected exactly one {assignment.decode()} block")
        else:
            if not target.exists() or target.read_bytes() != expected:
                target.write_bytes(expected)
                changed.append(country_file)
    return {
        "active_country_definitions": len(assignments),
        "generated_name_pools": len(assignments),
        "male_names_per_pool": TARGET_MALE_NAMES,
        "female_names_per_pool": TARGET_FEMALE_NAMES,
        "changed_files": changed,
        "countries_by_culture": dict(sorted(cultures.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    args = parser.parse_args()
    print(json.dumps(apply(args.vanilla_root, args.check), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
