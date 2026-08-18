#!/usr/bin/env python3
"""Apply two-character, pre-imperial-style names to mainland China areas.

This transaction changes localisation only.  It deliberately leaves area keys,
province memberships, regions, history, and bitmap data untouched.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "guangdong_independent_practice" / "localisation_source"
AUTHORITATIVE_SOURCE = SOURCE_DIR / "gdd_zzz_chunqiu_area_overrides_readable_utf8.txt"

AREA_NAMES = {
    # South China mainland
    "pearl_river_delta_area": "南海",
    "guangdong_area": "曲江",
    "dongjiang_area": "龙川",
    "chaoshan_area": "揭阳",
    "west_guangdong_area": "高凉",
    "fujian_area": "东冶",
    "minnan_area": "南安",
    "west_fujian_area": "建安",
    "jiangxi_area": "豫章",
    "south_jiangxi_area": "庐陵",
    "hanjiang_xiangyun_area": "汉沔",
    "jingyi_shinan_area": "荆楚",
    "dean_qihuang_area": "随黄",
    "wuhan_enan_area": "江夏",
    "zhejiang_area": "钱唐",
    "east_zhejiang_area": "会稽",
    "jinqu_chuzhou_area": "姑蔑",
    "wanjiang_area": "皖江",
    "huining_area": "丹阳",
    "yingtian_area": "金陵",
    "jinling_wuhui_area": "吴会",
    "dongting_area": "云梦",
    "hunan_area": "长沙",
    "southwest_hunan_area": "湘沅",
    "wuling_hunan_area": "黔中",
    "lishui_area": "澧水",
    "hengchen_area": "衡湘",
    "xunyang_area": "艾邑",
    "gannan_area": "南野",
    "guangxi_area": "桂林",
    "guidong_area": "苍梧",
    "youjiang_area": "象郡",
    # Southwest China mainland
    "sichuan_area": "蜀郡",
    "chongqing_area": "巴郡",
    "yunnan_area": "滇池",
    "diannan_area": "句町",
    "dianxinan_area": "哀牢",
    "diandong_area": "朱提",
    "dianxi_area": "叶榆",
    "dianxibei_area": "神川",
    "qianxi_area": "夜郎",
    "qiandong_area": "牂牁",
    "chuannan_area": "犍为",
    "chuanbei_area": "巴西",
    "liangshan_area": "邛都",
    "ganzi_area": "白狼",
    "aba_area": "冉駹",
    "songmao_area": "湔氐",
    "jiaya_area": "青衣",
    "baqu_area": "巴渠",
    "fuling_area": "枳涪",
    "xiajiang_area": "巫峡",
    # North China mainland
    "hebei_area": "上谷",
    "zhong_hebei_area": "河间",
    "dong_hebei_area": "孤竹",
    "yandu_area": "燕都",
    "south_hebei_area": "赵地",
    "luxi_area": "东郡",
    "qizhou_area": "临淄",
    "denglai_area": "东莱",
    "lunan_area": "鲁邦",
    "guide_xuchen_area": "宋陈",
    "runing_nanyang_area": "宛汝",
    "shanxi_area": "晋阳",
    "hedong_area": "河东",
    "shangdang_area": "上党",
    "yanmen_area": "雁门",
    "gansu_area": "金城",
    "hexi_area": "河西",
    "longnan_area": "陇西",
    "longyou_area": "天水",
    "ningxia_area": "朔方",
    "shaanxi_area": "岐丰",
    "xi_shaanxi_area": "西垂",
    "nan_shaanxi_area": "汉中",
    "bei_shaanxi_area": "上郡",
    "changan_area": "宗周",
    "chengzhou_area": "成周",
    "hebei_zhangwei_area": "河内",
    "wangji_area": "大梁",
    "west_gansu_area": "敦煌",
    "xuhuai_haizhou_area": "徐泗",
    "huaiyang_tongtai_area": "淮扬",
    "huaiying_area": "淮颍",
    "jianghuai_area": "江淮",
}
if (ROOT / "planning/chuandongbei_chongqing_b46/batch_manifest.json").exists():
    AREA_NAMES["chuanbei_area"] = "苴阆"
    AREA_NAMES["chongqing_area"] = "巴渝"

# These vanilla-derived areas did not previously have readable custom keys.
OWNER_HINTS = {
    "west_guangdong_area": "gdd_b01_map_readable_utf8.txt",
    "hebei_area": "gdd_b24_workshop_hebei_utf8.txt",
}

LINE_RE = re.compile(r'^(\s*)([A-Za-z0-9_]+):0\s+".*"\s*$')


def family(area: str) -> tuple[str, str, str]:
    return area, f"{area}_name", f"{area}_adj"


def main() -> None:
    assert len(AREA_NAMES) == 85
    assert all(len(name) == 2 for name in AREA_NAMES.values())

    paths = sorted(path for path in SOURCE_DIR.glob("*.txt") if path != AUTHORITATIVE_SOURCE)
    texts = {path: path.read_text(encoding="utf-8-sig") for path in paths}
    owners: dict[str, Path] = {}
    present: set[str] = set()

    for path, text in texts.items():
        output: list[str] = []
        for line in text.splitlines():
            match = LINE_RE.match(line)
            if match:
                key = match.group(2)
                for area, name in AREA_NAMES.items():
                    if key in family(area):
                        line = f'{match.group(1)}{key}:0 "{name}"'
                        owners.setdefault(area, path)
                        present.add(key)
                        break
            output.append(line)
        texts[path] = "\n".join(output) + "\n"

    missing_by_path: dict[Path, list[str]] = {}
    for area, name in AREA_NAMES.items():
        owner = owners.get(area)
        if owner is None:
            owner = SOURCE_DIR / OWNER_HINTS[area]
        for key in family(area):
            if key not in present:
                missing_by_path.setdefault(owner, []).append(f' {key}:0 "{name}"')

    for path, lines in missing_by_path.items():
        marker = " # CHUNQIU_AREA_NAMES: generated missing area family keys"
        text = texts[path]
        if marker not in text:
            text += "\n" + marker + "\n" + "\n".join(lines) + "\n"
        texts[path] = text

    changed = []
    for path, text in texts.items():
        before = path.read_text(encoding="utf-8-sig")
        if text != before:
            path.write_text(text, encoding="utf-8-sig", newline="\n")
            changed.append(path.name)

    # Keep one authoritative copy of every display family.  The encoder puts
    # it in localisation/replace so these display strings override vanilla;
    # underlying area keys and memberships remain untouched, preserving
    # mission and decision references.
    override_lines = ["l_english:"]
    for area, name in AREA_NAMES.items():
        override_lines.extend(
            (
                f' {area}:0 "{name}"',
                f' {area}_name:0 "{name}"',
                f' {area}_adj:0 "{name}"',
            )
        )
    override_text = "\n".join(override_lines) + "\n"
    previous = AUTHORITATIVE_SOURCE.read_text(encoding="utf-8-sig") if AUTHORITATIVE_SOURCE.exists() else None
    if previous != override_text:
        AUTHORITATIVE_SOURCE.write_text(override_text, encoding="utf-8", newline="\n")
        changed.append(AUTHORITATIVE_SOURCE.name)

    print(f"Applied {len(AREA_NAMES)} area names; changed {len(changed)} source files")
    for name in changed:
        print(name)


if __name__ == "__main__":
    main()
