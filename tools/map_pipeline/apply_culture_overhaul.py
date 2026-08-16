#!/usr/bin/env python3
"""Apply the approved four-group, twenty-four-culture map transaction.

The authoritative province mapping is the reviewed CSV in
``planning/culture_overhaul``.  The transaction keeps the engine-facing
``east_asian`` key for Chinese mechanics, preserves inherited name lists for
Korean, Vietnamese, Miao, Bai and Yi, and moves those definitions brace-safely
to their approved groups.  Province and country history, inherited mechanism
overrides, replayable map scripts and encoded localisation are updated
together and are required to be idempotent.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from apply_culture_name_pools import apply_to_culture_files

MAP = MOD / "map"
VANILLA = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/common/Europa Universalis IV"
)
CHINESE_SUPPLEMENT = Path(
    "/Users/xinanyapiao/Library/Application Support/Steam/steamapps/workshop/content/236850/1999055990"
)
OUT = ROOT / "planning/culture_overhaul"
MANIFEST = OUT / "culture_assignment_manifest.csv"
APPROVED_ASSIGNMENTS = OUT / "approved_province_culture_assignments.csv"
SUMMARY = OUT / "culture_assignment_summary.md"
MARKER = "B41 approved Han-Baiyue-Yinshang-Qiang culture overhaul"


HAN_CULTURES = {
    "gdd_zhongyuan": ("中原", "CZH"),
    "gdd_jianghuai": ("江淮", "MNG"),
    "gdd_chu": ("楚", "CXI"),
    "gdd_gan": ("赣", "NNG"),
    "gdd_hakka": ("客家", "LFA"),
    "gdd_gui": ("桂", None),
    "gdd_shu": ("蜀", "SHU"),
    "gdd_dian": ("滇", None),
    "gdd_jin": ("晋", "JIN"),
    "gdd_qi": ("齐", "QIC"),
    "gdd_yan": ("燕", "YAN"),
    "gdd_long": ("陇", "CSH"),
}

BAIYUE_CUSTOM_CULTURES = {
    "gdd_guangfu": ("粤", "GDD"),
    "gdd_zhuang": ("壮侗", "CGS"),
    "gdd_wu": ("吴越", "WUU"),
    "gdd_min": ("闽越", "MIN"),
}

YINSHANG_CUSTOM_CULTURES = {
    "gdd_songwei": ("宋卫", "SNG"),
    "gdd_dongyi": ("东夷", None),
}

QIANG_CUSTOM_CULTURES = {
    "gdd_diqiang": ("氐羌", None),
}

# These active inherited keys keep their original full definitions (including
# dynasty/name pools and primary tags) and are moved between culture groups.
MOVED_INHERITED_CULTURES = {
    "vietnamese": ("安南", "gdd_baiyue_group"),
    "miao": ("苗瑶", "gdd_baiyue_group"),
    "korean": ("朝鲜", "korean_g"),
    "bai": ("白", "gdd_qiang_group"),
    "yi": ("彝", "gdd_qiang_group"),
}

CULTURE_DISPLAY = {
    **{key: value[0] for key, value in HAN_CULTURES.items()},
    **{key: value[0] for key, value in BAIYUE_CUSTOM_CULTURES.items()},
    **{key: value[0] for key, value in YINSHANG_CUSTOM_CULTURES.items()},
    **{key: value[0] for key, value in QIANG_CUSTOM_CULTURES.items()},
    **{key: value[0] for key, value in MOVED_INHERITED_CULTURES.items()},
}
ALL_NEW_CULTURES = set(CULTURE_DISPLAY)

# Compatibility alias used by the inherited Chinese accepted-culture rewrite.
ZHONGHUA_CULTURES = HAN_CULTURES

# These inherited definitions are superseded, not merely left unused.  The
# Chinese supplementary dependency also adds a second Zhuang definition named
# zhuang_new, so both inherited Zhuang keys must be removed.
REMOVED_CULTURE_DEFINITIONS = {
    "chihan",
    "cantonese",
    "jin",
    "wu",
    "chimin",
    "hakka",
    "gan",
    "xiang",
    "sichuanese",
    "jianghuai",
    "xibei",
    "hubei",
    "zhongyuan",
    "shandong_culture",
    "zhuang",
    "zhuang_new",
    # Retired B40 regional cultures.
    "gdd_zhao",
    "gdd_qin",
    "gdd_lu",
    "gdd_huaisi",
    "gdd_yue",
    "gdd_xiang",
    "gdd_ba",
    "gdd_chaoshan",
    "gdd_qiong",
    "gdd_li",
}

# Safe defaults are refined below by current areas and explicit frontier IDs.
OLD_TO_DEFAULT = {
    "chihan": "gdd_yan",
    "zhili": "gdd_yan",
    "yan": "gdd_yan",
    "jin": "gdd_jin",
    "xibei": "gdd_long",
    "shandong": "gdd_qi",
    "shandong_culture": "gdd_qi",
    "zhongyuan": "gdd_zhongyuan",
    "jianghuai": "gdd_jianghuai",
    "wu": "gdd_wu",
    "chimin": "gdd_min",
    "hakka": "gdd_hakka",
    "gan": "gdd_gan",
    "xiang": "gdd_chu",
    "hubei": "gdd_chu",
    "sichuanese": "gdd_shu",
    "cantonese": "gdd_guangfu",
    "zhuang": "gdd_zhuang",
    "zhuang_new": "gdd_zhuang",
    # B40 -> approved B41 fallbacks.  The approved CSV is applied last and is
    # authoritative wherever the document makes a province-level decision.
    "gdd_zhao": "gdd_yan",
    "gdd_qin": "gdd_long",
    "gdd_lu": "gdd_qi",
    "gdd_huaisi": "gdd_jianghuai",
    "gdd_yue": "gdd_wu",
    "gdd_xiang": "gdd_chu",
    "gdd_ba": "gdd_shu",
    "gdd_chaoshan": "gdd_min",
    "gdd_qiong": "gdd_zhuang",
    "gdd_li": "gdd_zhuang",
}

# Merge regressions left both the old and renamed history files in the tree.
# These names select the semantically current file before inherited filenames
# are canonicalised.  The final on-disk filename may intentionally retain the
# dependency's old Latin spelling: EU4's VFS shadows files by relative path,
# not by the numeric province ID embedded in that filename.
PREFERRED_HISTORY_NAMES = {
    # B43's country implementation gives the Fuyang file the authoritative
    # CHN/XU2 political history and the later QNG dated block.  It also matches
    # the dependency's VFS filename, so keeping it avoids a second effective
    # history for province 2144 while the displayed name remains localisation-
    # driven Yingzhou.
    2144: "2144 - Fuyang.txt",
    # The culture merge can leave the dependency-canonical Ngaichow path with
    # content misdetected from province 5015.  Select B43's political Yazhou
    # history first, then canonicalise that content to Ngaichow's VFS path.
    2160: "2160 - Yazhou.txt",
    4197: "4197 - Huangzhou.txt",
    5009: "5009 - Suizhou.txt",
    5012: "5012 - Huangzhou.txt",
    5015: "5015 - Mianyang.txt",
}

COUNTRY_POLICY = {
    "MNG": ("gdd_jianghuai", ()),
    "CZH": ("gdd_zhongyuan", ()),
    "QIC": ("gdd_qi", ()),
    "YAN": ("gdd_yan", ()),
    "JIN": ("gdd_jin", ()),
    "QIN": ("gdd_zhongyuan", ()),
    "WUU": ("gdd_wu", ()),
    "YUE": ("gdd_wu", ()),
    "MIN": ("gdd_min", ()),
    "SHU": ("gdd_shu", ()),
    "CHC": ("gdd_chu", ()),
    "CXI": ("gdd_chu", ()),
    "NNG": ("gdd_gan", ()),
    "TNG": ("gdd_zhongyuan", ()),
    "LNG": ("gdd_zhongyuan", ()),
    "HUA": ("gdd_jianghuai", ()),
    "CSH": ("gdd_long", ()),
    "LFA": ("gdd_hakka", ()),
    "FRM": ("gdd_min", ()),
    "CGS": ("gdd_zhuang", ()),
    "GDD": ("gdd_guangfu", ("gdd_hakka", "gdd_min")),
    "CZC": ("gdd_min", ("gdd_guangfu",)),
    "SNG": ("gdd_songwei", ()),
    "XU2": ("gdd_zhongyuan", ()),

    # B42 regional states.  Their primary cultures follow the approved
    # province-ID map; accepted cultures preserve the reviewed polity design.
    "CSA": ("gdd_chu", ("gdd_gui", "gdd_guangfu")),
    "CZM": ("miao", ()),
    "DIA": ("gdd_dian", ("yi",)),
    "GUI": ("gdd_gui", ("gdd_zhuang",)),
    "GYA": ("gdd_shu", ("miao",)),
    "HAK": ("gdd_hakka", ("gdd_min",)),
    "LCH": ("gdd_gan", ()),
    "LIL": ("gdd_zhuang", ("gdd_min",)),
    "NCH": ("gdd_gan", ()),
    "NUN": ("gdd_zhuang", ("yi",)),
    "TZZ": ("gdd_zhuang", ()),
    "WXM": ("miao", ()),
    "YEL": ("yi", ()),

    # B43 China-subcontinent states.  These are explicit rather than generic
    # OLD_TO_DEFAULT replacements because several capitals belong to a more
    # specific approved culture (for example WLM=miao and GUZ=gdd_dongyi).
    "AMD": ("tibetan", ()),
    "BAA": ("gdd_shu", ()),
    "BD2": ("gdd_diqiang", ()),
    "BMY": ("gdd_diqiang", ()),
    "CAG": ("gdd_zhongyuan", ()),
    "CAI": ("gdd_zhongyuan", ()),
    "CCH": ("gdd_jianghuai", ()),
    "CHN": ("gdd_zhongyuan", ()),
    "DAE": ("gdd_jin", ()),
    "DCH": ("gdd_diqiang", ()),
    "DZH": ("gdd_diqiang", ()),
    "GON": ("gdd_zhongyuan", ()),
    "GUN": ("gdd_zhongyuan", ()),
    "GUO": ("gdd_zhongyuan", ()),
    "GUZ": ("gdd_dongyi", ()),
    "GZH": ("gdd_long", ()),
    "HZH": ("gdd_long", ()),
    "JRG": ("tibetan", ()),
    "JUU": ("gdd_shu", ()),
    "LIU": ("gdd_jianghuai", ()),
    "LSH": ("yi", ()),
    "LUO": ("gdd_zhongyuan", ()),
    "LUU": ("gdd_qi", ()),
    "MDL": ("bai", ()),
    "NZA": ("yi", ()),
    "QSH": ("gdd_jianghuai", ("gdd_wu",)),
    "QWO": ("gdd_jin", ()),
    "SHE": ("gdd_zhongyuan", ("gdd_chu",)),
    "SHZ": ("oirats", ()),
    "SUI": ("gdd_chu", ()),
    "TSF": ("gdd_gan", ()),
    "WDU": ("gdd_diqiang", ()),
    "WEI": ("gdd_yan", ("gdd_jin",)),
    "WGS": ("mongol", ("gdd_long",)),
    "WLM": ("miao", ()),
    "WUZ": ("gdd_dongyi", ()),
    "WVG": ("gdd_songwei", ()),
    "WXG": ("gdd_diqiang", ()),
    "YOU": ("gdd_jin", ()),
    "YPG": ("gdd_long", ()),
    "ZHA": ("gdd_jin", ("gdd_yan",)),
    "ZHG": ("gdd_zhongyuan", ()),
    "ZNG": ("gdd_zhongyuan", ()),
    "ZSH": ("gdd_yan", ("gdd_jin",)),
}

# B43 intentionally reuses several vanilla tags.  Ordinary localisation does
# not reliably override an inherited first-loaded value, so these complete
# name/adjective families are generated in localisation/replace instead.
COUNTRY_NAME_OVERRIDES = {
    "CHC": ("楚公国", "楚"),
    "CZH": ("周天子", "周"),
    "KAM": ("康巴", "康巴"),
    "KSD": ("和硕特蒙古", "和硕特"),
    "MIN": ("闽侯国", "闽侯"),
    "QIN": ("秦公国", "秦"),
    "SHU": ("蜀公国", "蜀"),
    "WUU": ("吴公国", "吴"),
    "YUE": ("越公国", "越"),
}

# Explicit non-culture terminal values retained by this transaction.  The
# 1821/5056 development exchange is the user-approved post-document override.
# The other entries reconcile B41's province semantics with B43's political
# histories: ownership, cores and dated blocks stay untouched.
INITIAL_HISTORY_OVERRIDES = {
    1821: {"base_tax": "7", "base_production": "8", "base_manpower": "4"},
    2144: {
        "capital": '"Yingzhou"',
        "base_tax": "4",
        "base_production": "4",
        "base_manpower": "2",
    },
    5012: {
        "capital": '"Huangzhou"',
        "base_tax": "4",
        "base_production": "4",
        "base_manpower": "2",
    },
    5015: {
        "capital": '"Mianyang"',
        "base_tax": "2",
        "base_production": "2",
        "base_manpower": "2",
    },
    5056: {"base_tax": "2", "base_production": "2", "base_manpower": "1"},
}


def blocks(text: str, suffix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(rf"(?m)^\s*([A-Za-z0-9_]+{re.escape(suffix)})\s*=\s*\{{")
    for match in pattern.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f"Unclosed block {match.group(1)}")
        result[match.group(1)] = text[match.end() : index - 1]
    return result


def clean(text: str) -> str:
    return re.sub(r"#.*", "", text)


def area_members() -> tuple[dict[str, list[int]], dict[int, str]]:
    bodies = blocks((MAP / "area.txt").read_text(encoding="cp1252"), "_area")
    areas: dict[str, list[int]] = {}
    reverse: dict[int, str] = {}
    for area, body in bodies.items():
        value = re.sub(r"(?ms)\bcolor\s*=\s*\{.*?\}", "", clean(body))
        ids = [int(number) for number in re.findall(r"\b\d+\b", value)]
        areas[area] = ids
        for province_id in ids:
            reverse[province_id] = area
    return areas, reverse


def initial_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([A-Za-z0-9_]+)", text)
    return match.group(1) if match else None


def province_id(path: Path) -> int:
    match = re.match(r"(\d+)", path.name)
    if not match:
        raise ValueError(f"History filename lacks province ID: {path}")
    return int(match.group(1))


def history_paths(directory: Path, pid: int) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*.txt")
        if re.match(r"\d+", path.name) and province_id(path) == pid
    )


def read_history(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError(f"Cannot decode history file {path}")


def write_history(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def approved_assignments() -> dict[int, str]:
    """Load the reviewed province-ID mapping used as transaction input."""
    if not APPROVED_ASSIGNMENTS.exists():
        raise FileNotFoundError(f"Missing approved culture mapping: {APPROVED_ASSIGNMENTS}")
    assignments: dict[int, str] = {}
    with APPROVED_ASSIGNMENTS.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"province_id", "target_culture"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"Approved mapping requires columns {sorted(required)}; got {reader.fieldnames}"
            )
        for line_number, row in enumerate(reader, start=2):
            try:
                pid = int(row["province_id"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid province ID on approved mapping line {line_number}") from exc
            culture = row["target_culture"].strip()
            if culture not in ALL_NEW_CULTURES:
                raise ValueError(
                    f"Unknown target culture {culture!r} for province {pid} on line {line_number}"
                )
            if pid in assignments:
                raise ValueError(f"Duplicate approved province ID {pid} on line {line_number}")
            assignments[pid] = culture
    if not assignments:
        raise ValueError("Approved culture mapping is empty")
    return assignments


def build_targets(_areas: dict[str, list[int]]) -> dict[int, str]:
    """Build safe fallbacks, then apply the reviewed document map last."""
    targets: dict[int, str] = {}
    for path in (MOD / "history/provinces").glob("*.txt"):
        old = initial_value(read_history(path), "culture")
        if old in OLD_TO_DEFAULT:
            targets[province_id(path)] = OLD_TO_DEFAULT[old]
        elif old in ALL_NEW_CULTURES:
            targets[province_id(path)] = old

    # Explicit document decisions deliberately outrank all fallbacks and any
    # cultures left by a previous transaction run.
    targets.update(approved_assignments())
    return targets


def preferred_history(pid: int, paths: list[Path]) -> Path:
    preferred = PREFERRED_HISTORY_NAMES.get(pid)
    if preferred:
        chosen = MOD / "history/provinces" / preferred
        if chosen in paths:
            return chosen
    inherited = supplement_history_path(pid)
    if inherited is not None:
        canonical = MOD / "history/provinces" / inherited.name
        if canonical in paths:
            return canonical
    if len(paths) != 1:
        raise ValueError(f"Province {pid} has ambiguous history files: {[path.name for path in paths]}")
    return paths[0]


def supplement_history_path(pid: int) -> Path | None:
    # Do not rely on spacing around the hyphen.  The dependency contains, for
    # example, ``2153 -Tingzhou.txt`` and EU4 still treats its numeric prefix as
    # province 2153.
    paths = history_paths(CHINESE_SUPPLEMENT / "history/provinces", pid)
    if len(paths) > 1:
        raise ValueError(f"Dependency has ambiguous province history for {pid}: {paths}")
    return paths[0] if paths else None


def canonicalize_inherited_history_filenames() -> dict[int, tuple[str, str]]:
    """Make local inherited histories shadow the dependency's exact VFS path.

    A differently named ``2176 - Guide.txt`` does not replace the dependency's
    ``2176 - Shangqiu.txt``.  Both histories then load for province 2176, and
    the dependency can restore a removed culture such as ``zhongyuan``.  Keep
    the local file content, but use the dependency filename for every inherited
    province ID.  Custom IDs without a dependency history are left untouched.
    """
    directory = MOD / "history/provinces"
    grouped: dict[int, list[Path]] = {}
    for path in directory.glob("*.txt"):
        grouped.setdefault(province_id(path), []).append(path)

    renamed: dict[int, tuple[str, str]] = {}
    for pid, paths in sorted(grouped.items()):
        inherited = supplement_history_path(pid)
        if inherited is None:
            continue
        target = directory / inherited.name
        chosen = preferred_history(pid, sorted(paths))
        for duplicate in paths:
            if duplicate != chosen:
                duplicate.unlink()
        if chosen != target:
            old_name = chosen.name
            if target.exists():
                target.unlink()
            chosen.replace(target)
            renamed[pid] = (old_name, target.name)
    return renamed


def ensure_history(pid: int) -> tuple[Path, list[Path]]:
    directory = MOD / "history/provinces"
    existing = history_paths(directory, pid)
    if existing:
        return preferred_history(pid, existing), existing
    supplement = supplement_history_path(pid)
    if supplement is not None:
        target = directory / supplement.name
        shutil.copy2(supplement, target)
        return target, [target]
    vanilla = history_paths(VANILLA / "history/provinces", pid)
    if len(vanilla) != 1:
        raise ValueError(f"Cannot resolve inherited history for province {pid}: {vanilla}")
    target = directory / vanilla[0].name
    shutil.copy2(vanilla[0], target)
    return target, [target]


def existing_manifest_old_values() -> dict[int, str]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        return {int(row["province_id"]): row["previous_culture"] for row in csv.DictReader(handle)}


def baseline_culture(path: Path, pid: int) -> str:
    """Read the pre-transaction culture from Git or the inherited vanilla file."""
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        text = result.stdout.decode("latin-1")
        value = initial_value(text, "culture")
        if value:
            return value
    vanilla = history_paths(VANILLA / "history/provinces", pid)
    if len(vanilla) == 1:
        value = initial_value(vanilla[0].read_bytes().decode("latin-1"), "culture")
        if value:
            return value
    return "unknown"


def update_province_histories(targets: dict[int, str]) -> tuple[dict[int, str], dict[int, str]]:
    old_values = existing_manifest_old_values()
    history_names: dict[int, str] = {}
    previous: dict[int, str] = {}
    for pid, target_culture in sorted(targets.items()):
        path, duplicates = ensure_history(pid)
        text = read_history(path)
        old = initial_value(text, "culture")
        if old is None:
            raise ValueError(f"Province {pid} lacks an initial culture in {path.name}")
        previous[pid] = old_values.get(pid, baseline_culture(path, pid) if old in ALL_NEW_CULTURES else old)
        updated, count = re.subn(
            r"(?m)^(\s*culture\s*=\s*)[A-Za-z0-9_]+",
            rf"\g<1>{target_culture}",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"Could not update culture for province {pid}")
        for key, value in INITIAL_HISTORY_OVERRIDES.get(pid, {}).items():
            updated, count = re.subn(
                rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^#\r\n]+",
                rf"\g<1>{value}",
                updated,
                count=1,
            )
            if count != 1:
                raise ValueError(f"Province {pid} lacks initial {key}")
        write_history(path, updated)
        for duplicate in duplicates:
            if duplicate != path:
                duplicate.unlink()
        history_names[pid] = path.name

    # Remove the five known merge-reintroduced duplicates even when a culture
    # mapping is later narrowed; these removals are recoverable through Git.
    for pid, preferred in PREFERRED_HISTORY_NAMES.items():
        inherited = supplement_history_path(pid)
        canonical = inherited.name if inherited is not None else preferred
        for path in (MOD / "history/provinces").glob(f"{pid} - *.txt"):
            if path.name != canonical:
                path.unlink()
    return previous, history_names


def validate_effective_history_uniqueness() -> None:
    """Reject numeric province IDs that still resolve to multiple VFS files."""
    effective: dict[str, Path] = {}
    for root in (
        VANILLA / "history/provinces",
        CHINESE_SUPPLEMENT / "history/provinces",
        MOD / "history/provinces",
    ):
        if root.exists():
            for path in root.glob("*.txt"):
                effective[path.name] = path

    local_ids = {province_id(path) for path in (MOD / "history/provinces").glob("*.txt")}
    resolved: dict[int, list[Path]] = {}
    for path in effective.values():
        resolved.setdefault(province_id(path), []).append(path)
    collisions = {
        pid: sorted(path.name for path in paths)
        for pid, paths in resolved.items()
        if pid in local_ids and len(paths) > 1
    }
    if collisions:
        rendered = "; ".join(f"{pid}: {names}" for pid, names in sorted(collisions.items()))
        raise ValueError(f"Effective province-history filename collisions remain: {rendered}")


COMMON_DYNASTIES = "Li Wang Zhang Liu Chen Yang Zhao Huang Zhou Wu Xu Sun Ma Zhu Hu Guo Lin He Gao Luo Zheng Liang Xie Song Tang Han Feng Cao Peng Xiao Tian Dong Yuan Pan Yu Jiang Cai"
COMMON_MALE_NAMES = "Wen Wu Cheng De Ren Yi Li Zhi Xin Ming Yuan Jun An Ping Tai Guang Hong Sheng Jian Zhong Bo Liang Qing Hao Rui"
COMMON_FEMALE_NAMES = "Hua Lan Mei Ying Yue Yun Xiu Zhen Ning Hui Fang Yan Ling Qing Yu"


def culture_entry(key: str, primary: str | None) -> str:
    primary_line = f"\n\t\tprimary = {primary}" if primary else ""
    return (
        f"\t{key} = {{{primary_line}\n"
        f"\t\tdynasty_names = {{ {COMMON_DYNASTIES} }}\n"
        f"\t\tmale_names = {{ {COMMON_MALE_NAMES} }}\n"
        f"\t\tfemale_names = {{ {COMMON_FEMALE_NAMES} }}\n"
        "\t}"
    )


def matching_brace(text: str, opening: int) -> int:
    depth = 1
    quoted = False
    comment = False
    index = opening + 1
    while index < len(text):
        char = text[index]
        if comment:
            if char in "\r\n":
                comment = False
        elif char == '"':
            quoted = not quoted
        elif not quoted and char == "#":
            comment = True
        elif not quoted and char == "{":
            depth += 1
        elif not quoted and char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError("Unclosed culture block")


def top_level_block_span(text: str, key: str) -> tuple[int, int, int]:
    depth = 0
    offset = 0
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*\{{")
    for line in text.splitlines(keepends=True):
        visible = line.split("#", 1)[0]
        match = pattern.match(visible)
        if depth == 0 and match:
            opening = offset + visible.find("{", match.start())
            closing = matching_brace(text, opening)
            return offset, opening, closing
        depth += visible.count("{") - visible.count("}")
        offset += len(line)
    raise ValueError(f"Missing top-level culture group: {key}")


def direct_child_spans(body: str, keys: set[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    offset = 0
    pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{")
    for line in body.splitlines(keepends=True):
        visible = line.split("#", 1)[0]
        match = pattern.match(visible)
        if depth == 0 and match and match.group(1) in keys:
            opening = offset + visible.find("{", match.start())
            closing = matching_brace(body, opening)
            end = closing + 1
            while end < len(body) and body[end] in " \t":
                end += 1
            if end < len(body) and body[end] == "\r":
                end += 1
            if end < len(body) and body[end] == "\n":
                end += 1
            spans.append((offset, end))
        depth += visible.count("{") - visible.count("}")
        offset += len(line)
    return spans


def rewrite_group(
    text: str,
    group: str,
    removed: set[str],
    appended_entries: tuple[str, ...] = (),
) -> str:
    _start, opening, closing = top_level_block_span(text, group)
    body = text[opening + 1 : closing]
    for start, end in reversed(direct_child_spans(body, removed)):
        body = body[:start] + body[end:]
    if appended_entries:
        body = body.rstrip() + "\n\n" + "\n\n".join(appended_entries) + "\n"
    return text[: opening + 1] + body + text[closing:]


def direct_child_definition(text: str, group: str, key: str) -> str:
    """Return one complete direct culture definition without rebuilding it."""
    _start, opening, closing = top_level_block_span(text, group)
    body = text[opening + 1 : closing]
    spans = direct_child_spans(body, {key})
    if len(spans) != 1:
        raise ValueError(f"Expected one {key} definition in {group}; found {len(spans)}")
    start, end = spans[0]
    return body[start:end].strip()


def inherited_culture_source() -> Path:
    supplementary = CHINESE_SUPPLEMENT / "common/cultures/00_cultures.txt"
    if supplementary.exists():
        return supplementary
    vanilla = VANILLA / "common/cultures/00_cultures.txt"
    if vanilla.exists():
        return vanilla
    raise FileNotFoundError("Cannot find an inherited common/cultures/00_cultures.txt")


def direct_definitions(text: str, candidates: set[str]) -> set[str]:
    found: set[str] = set()
    depth = 0
    pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{")
    for line in text.splitlines():
        visible = line.split("#", 1)[0]
        match = pattern.match(visible)
        if depth == 1 and match and match.group(1) in candidates:
            found.add(match.group(1))
        depth += visible.count("{") - visible.count("}")
    return found


def write_culture_definitions() -> None:
    directory = MOD / "common/cultures"
    directory.mkdir(parents=True, exist_ok=True)
    han_entries = tuple(culture_entry(key, primary) for key, (_name, primary) in HAN_CULTURES.items())
    baiyue_custom = tuple(
        culture_entry(key, primary) for key, (_name, primary) in BAIYUE_CUSTOM_CULTURES.items()
    )
    yinshang_custom = tuple(
        culture_entry(key, primary) for key, (_name, primary) in YINSHANG_CUSTOM_CULTURES.items()
    )
    qiang_custom = tuple(
        culture_entry(key, primary) for key, (_name, primary) in QIANG_CUSTOM_CULTURES.items()
    )

    # A later file can add cultures but cannot delete inherited definitions.
    # Shadow the dependency's exact virtual path and move inherited definitions
    # intact before removing their original direct-child blocks.
    source = inherited_culture_source()
    source_text = source.read_bytes().decode("latin-1")
    preserved = {
        "vietnamese": direct_child_definition(source_text, "southeastasian_group", "vietnamese"),
        "miao": direct_child_definition(source_text, "tibetan_group", "miao"),
        "korean": direct_child_definition(source_text, "korean_g", "korean"),
        "bai": direct_child_definition(source_text, "tibetan_group", "bai"),
        "yi": direct_child_definition(source_text, "tibetan_group", "yi"),
    }
    zhuang_new = direct_child_definition(source_text, "east_asian", "zhuang_new")
    zhuang_new = re.sub(r"^zhuang_new\b", "gdd_zhuang_new", zhuang_new, count=1)
    inherited = source_text
    inherited = rewrite_group(
        inherited,
        "east_asian",
        REMOVED_CULTURE_DEFINITIONS | ALL_NEW_CULTURES,
        han_entries + (zhuang_new,),
    )
    inherited = rewrite_group(
        inherited,
        "korean_g",
        set(YINSHANG_CUSTOM_CULTURES),
        yinshang_custom,
    )
    inherited = rewrite_group(inherited, "southeastasian_group", {"vietnamese"})
    inherited = rewrite_group(inherited, "tibetan_group", {"miao", "bai", "yi"})
    inherited = rewrite_group(inherited, "thai_group", {"zhuang"})
    marker = f"# {MARKER}: shadows inherited common/cultures/00_cultures.txt and removes superseded cultures\n"
    (directory / "00_cultures.txt").write_bytes((marker + inherited).encode("latin-1"))

    path = directory / "99_gdd_culture_overhaul.txt"
    def group_text(key: str, entries: tuple[str, ...]) -> str:
        return (
            f"{key} = {{\n\tgraphical_culture = asiangfx\n\n"
            + "\n\n".join(entries)
            + "\n}\n"
        )

    text = f"# {MARKER}\n# Inherited definitions are preserved byte-for-byte before Chinese name-pool replacement.\n\n"
    text += group_text(
        "gdd_baiyue_group",
        baiyue_custom + (preserved["vietnamese"], preserved["miao"]),
    )
    text += "\n" + group_text(
        "gdd_qiang_group",
        qiang_custom + (preserved["bai"], preserved["yi"]),
    )
    remaining_old = direct_definitions(inherited, REMOVED_CULTURE_DEFINITIONS)
    if remaining_old:
        raise ValueError(f"Inherited culture definitions survived replacement: {sorted(remaining_old)}")
    inherited_targets = direct_definitions(inherited, ALL_NEW_CULTURES)
    expected_inherited = set(HAN_CULTURES) | set(YINSHANG_CUSTOM_CULTURES) | {"korean"}
    if inherited_targets != expected_inherited:
        raise ValueError(
            "Unexpected target definitions left in 00_cultures.txt: "
            f"expected {sorted(expected_inherited)}, got {sorted(inherited_targets)}"
        )
    if "gdd_zhuang_new" not in direct_definitions(inherited, {"gdd_zhuang_new"}):
        raise ValueError("Missing sinicized compatibility definition gdd_zhuang_new")
    separate_targets = direct_definitions(text, ALL_NEW_CULTURES)
    expected_separate = ALL_NEW_CULTURES - expected_inherited
    if separate_targets != expected_separate:
        raise ValueError(
            "Unexpected target definitions in 99_gdd_culture_overhaul.txt: "
            f"expected {sorted(expected_separate)}, got {sorted(separate_targets)}"
        )
    # ``preserved`` contains Latin-1 byte surrogates from the inherited file.
    # Writing it as UTF-8 double-encodes the EU4 Chinese escape bytes and
    # creates mojibake in Vietnamese, Miao, Bai and Yi names.
    path.write_bytes(text.encode("latin-1"))
    apply_to_culture_files(check=False)


def country_history_path(tag: str) -> Path:
    local = sorted((MOD / "history/countries").glob(f"{tag} - *.txt"))
    if len(local) == 1:
        return local[0]
    if len(local) > 1:
        raise ValueError(f"Multiple country histories for {tag}: {local}")
    vanilla = sorted((VANILLA / "history/countries").glob(f"{tag} - *.txt"))
    if len(vanilla) != 1:
        raise ValueError(f"Cannot resolve vanilla country history for {tag}: {vanilla}")
    target = MOD / "history/countries" / vanilla[0].name
    shutil.copy2(vanilla[0], target)
    return target


def update_country_histories() -> None:
    for tag, (primary, accepted) in COUNTRY_POLICY.items():
        path = country_history_path(tag)
        text = path.read_text(encoding="latin-1")
        text, count = re.subn(
            r"(?m)^(\s*primary_culture\s*=\s*)[A-Za-z0-9_]+",
            rf"\g<1>{primary}",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"Country {tag} lacks primary_culture in {path.name}")
        managed_cultures = "|".join(
            map(re.escape, sorted(set(OLD_TO_DEFAULT) | ALL_NEW_CULTURES, key=lambda value: (-len(value), value)))
        )
        text = re.sub(
            rf"(?m)^[ \t]*add_accepted_culture[ \t]*=[ \t]*(?:{managed_cultures})[ \t]*(?:\r?\n|$)",
            "",
            text,
        )
        if accepted:
            insertion = "".join(f"add_accepted_culture = {culture}\n" for culture in accepted)
            text = re.sub(
                rf"(?m)^(\s*primary_culture\s*=\s*{re.escape(primary)}\s*\n)",
                rf"\g<1>{insertion}",
                text,
                count=1,
            )
        path.write_text(text, encoding="latin-1")


def replace_old_tokens(text: str) -> str:
    for old, new in sorted(OLD_TO_DEFAULT.items(), key=lambda item: -len(item[0])):
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


CULTURE_ASSIGNMENT_KEYS = (
    "primary_culture",
    "culture",
    "change_culture",
    "change_primary_culture",
    "accepted_culture",
    "add_accepted_culture",
    "dominant_culture",
)


def replace_culture_assignments(text: str) -> str:
    keys = "|".join(map(re.escape, CULTURE_ASSIGNMENT_KEYS))
    for old, new in sorted(OLD_TO_DEFAULT.items(), key=lambda item: -len(item[0])):
        text = re.sub(
            rf"(\b(?:{keys})\s*=\s*){re.escape(old)}\b",
            rf"\g<1>{new}",
            text,
        )
    return text


def rewrite_zhonghua_accepted_lists(text: str) -> str:
    """Replace inherited Chinese calc_true_if lists with all 12 Han cultures."""
    pattern = re.compile(r"\bcalc_true_if\s*=\s*\{")
    replacements: list[tuple[int, int, str]] = []
    managed = REMOVED_CULTURE_DEFINITIONS | ALL_NEW_CULTURES
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_brace(text, opening)
        block = text[opening + 1 : closing]
        inherited = set(
            re.findall(r"(?m)^\s*accepted_culture\s*=\s*([A-Za-z0-9_]+)\s*$", block)
        )
        if not (inherited & REMOVED_CULTURE_DEFINITIONS):
            continue
        lines = block.splitlines(keepends=True)
        filtered = [
            line
            for line in lines
            if not (
                (culture_match := re.match(r"^\s*accepted_culture\s*=\s*([A-Za-z0-9_]+)\s*(?:\r?\n)?$", line))
                and culture_match.group(1) in managed
            )
        ]
        amount_index = next(
            (index for index, line in enumerate(filtered) if re.match(r"^\s*amount\s*=", line)),
            None,
        )
        if amount_index is None:
            raise ValueError("Chinese accepted-culture calc_true_if block lacks amount")
        amount_line = filtered[amount_index]
        indent = re.match(r"^(\s*)", amount_line).group(1)
        newline = "\r\n" if "\r\n" in block else "\n"
        culture_lines = [f"{indent}accepted_culture = {culture}{newline}" for culture in ZHONGHUA_CULTURES]
        filtered[amount_index:amount_index] = culture_lines
        replacements.append((opening + 1, closing, "".join(filtered)))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text


def effective_inherited_script_sources() -> dict[Path, Path]:
    sources: dict[Path, Path] = {}
    for source_root in (VANILLA, CHINESE_SUPPLEMENT):
        if not source_root.exists():
            continue
        for folder in ("common", "events", "decisions", "missions"):
            root = source_root / folder
            if not root.exists():
                continue
            for path in root.rglob("*.txt"):
                relative = path.relative_to(source_root)
                if relative.parts[:2] == ("common", "cultures"):
                    continue
                sources[relative] = path
    return sources


def preserve_moved_culture_mechanics(text: str, relative: Path) -> str:
    """Keep moved-culture mechanics while narrowing Korean-only features."""
    updated = text
    # Keep the long-established korean_g engine key for the new Yinshang group,
    # but narrow the three genuinely Korean-only mechanics to Korean itself.
    if relative.as_posix() == "common/government_reforms/06_government_reforms_common.txt":
        updated = re.sub(r"\bculture_group\s*=\s*korean_g\b", "culture = korean", updated)
    elif relative.as_posix() == "common/naval_doctrines/00_naval_doctrines.txt":
        updated = re.sub(r"\bculture_group\s*=\s*korean_g\b", "primary_culture = korean", updated)
    elif relative.as_posix() == "decisions/KoreanDecisions.txt":
        updated = re.sub(r"\bculture_group\s*=\s*korean_g\b", "primary_culture = korean", updated)
    # Vietnamese historically qualified for these broad Southeast-Asian OR
    # lists.  Add it without changing cultures that stay in the old group.
    pattern = re.compile(r"(?m)^(\s*)culture_group\s*=\s*southeastasian_group(\s*(?:#.*)?)$")
    return pattern.sub(
        lambda match: (
            f"{match.group(1)}culture_group = southeastasian_group{match.group(2)}\n"
            f"{match.group(1)}culture = vietnamese"
        ),
        updated,
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected one {label} block; found {text.count(old)}")
    return text.replace(old, new, 1)


def rewrite_sinicize_decision(text: str) -> str:
    """Preserve the vanilla Sinicize decision after Bai/Yi/Miao group moves."""
    text = replace_once(
        text,
        "\t\t\t\tprimary_culture = gdd_zhuang\n\t\t\t\tculture_group = tibetan_group",
        "\t\t\t\tprimary_culture = gdd_zhuang\n"
        "\t\t\t\tprimary_culture = miao\n"
        "\t\t\t\tprimary_culture = bai\n"
        "\t\t\t\tprimary_culture = yi\n"
        "\t\t\t\tculture_group = tibetan_group",
        "Sinicize potential",
    )
    text = replace_once(
        text,
        "\t\t\t\tlimit = { ROOT = { culture_group = tibetan_group } }\n"
        "\t\t\t\tculture_group = tibetan_group",
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tROOT = {\n"
        "\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\tculture_group = tibetan_group\n"
        "\t\t\t\t\t\t\tprimary_culture = miao\n"
        "\t\t\t\t\t\t\tprimary_culture = bai\n"
        "\t\t\t\t\t\t\tprimary_culture = yi\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\t\t\t\tOR = {\n"
        "\t\t\t\t\tculture_group = tibetan_group\n"
        "\t\t\t\t\tculture = miao\n"
        "\t\t\t\t\tculture = bai\n"
        "\t\t\t\t\tculture = yi\n"
        "\t\t\t\t}",
        "Sinicize province highlight",
    )
    # The first remaining single-group limit is the allow-tooltip branch.
    old_limit = "\t\t\t\tlimit = {\n\t\t\t\t\tculture_group = tibetan_group\n\t\t\t\t}"
    if text.count(old_limit) != 2:
        raise ValueError(f"Expected two Sinicize Tibetan limits; found {text.count(old_limit)}")
    text = text.replace(
        old_limit,
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\tculture_group = tibetan_group\n"
        "\t\t\t\t\t\tprimary_culture = miao\n"
        "\t\t\t\t\t\tprimary_culture = bai\n"
        "\t\t\t\t\t\tprimary_culture = yi\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}",
        1,
    )
    text = replace_once(
        text,
        "\t\t\t\t\t\t\tculture_group = ROOT",
        "\t\t\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\t\t\tculture_group = tibetan_group\n"
        "\t\t\t\t\t\t\t\tculture = miao\n"
        "\t\t\t\t\t\t\t\tculture = bai\n"
        "\t\t\t\t\t\t\t\tculture = yi\n"
        "\t\t\t\t\t\t\t}",
        "Sinicize unowned-culture check",
    )
    text = replace_once(
        text,
        "\t\t\t\t\tculture_group = tibetan_group\n\t\t\t\t}\n"
        "\t\t\t\tupdate_entire_culture_group",
        "\t\t\t\t\tOR = {\n"
        "\t\t\t\t\t\tculture_group = tibetan_group\n"
        "\t\t\t\t\t\tprimary_culture = miao\n"
        "\t\t\t\t\t\tprimary_culture = bai\n"
        "\t\t\t\t\t\tprimary_culture = yi\n"
        "\t\t\t\t\t}\n"
        "\t\t\t\t}\n"
        "\t\t\t\tupdate_entire_culture_group",
        "Sinicize effect limit",
    )
    return text


def rewrite_women_history_cultures(text: str) -> str:
    """Replace the old generic Chinese culture per historical event.

    The inherited file used ``chihan`` for all four characters.  Mapping that
    retired key through the generic northern fallback would make every one of
    them Yan.  Restrict each correction to its numbered event block and assert
    the exact number of assignments so an upstream file change fails closed.
    """
    replacements = {
        48: ("mongol", 2),          # Empress Dowager Xiaozhuang
        52: ("gdd_shu", 1),         # Qin Liangyu
        54: ("gdd_jianghuai", 1),   # Wang Zhenyi
        91: ("gdd_guangfu", 1),     # Ching Shih
    }
    for event_id, (culture, expected_count) in replacements.items():
        id_match = re.search(
            rf"(?m)^\s*id\s*=\s*women_history_events\.{event_id}\s*$",
            text,
        )
        if id_match is None:
            raise ValueError(f"Missing Women in History event {event_id}")
        event_start = text.rfind("country_event = {", 0, id_match.start())
        if event_start < 0:
            raise ValueError(f"Cannot locate Women in History event block {event_id}")
        opening = text.find("{", event_start, id_match.start())
        closing = matching_brace(text, opening)
        block = text[event_start : closing + 1]
        block, count = re.subn(
            r"(?m)^(\s*culture\s*=\s*)gdd_yan\b",
            rf"\g<1>{culture}",
            block,
        )
        if count != expected_count:
            raise ValueError(
                f"Women in History event {event_id} expected {expected_count} "
                f"generic Chinese culture assignments; found {count}"
            )
        text = text[:event_start] + block + text[closing + 1 :]
    return text


def write_inherited_reference_overrides() -> list[Path]:
    old_values = "|".join(map(re.escape, sorted(REMOVED_CULTURE_DEFINITIONS, key=lambda value: -len(value))))
    keys = "|".join(map(re.escape, CULTURE_ASSIGNMENT_KEYS))
    reference_pattern = re.compile(rf"\b(?:{keys})\s*=\s*(?:{old_values})\b")
    written: list[Path] = []
    for relative, source in sorted(effective_inherited_script_sources().items()):
        text = source.read_bytes().decode("latin-1")
        compatible = preserve_moved_culture_mechanics(text, relative)
        if not reference_pattern.search(text) and compatible == text:
            continue
        updated = replace_culture_assignments(rewrite_zhonghua_accepted_lists(compatible))
        if relative.as_posix() == "decisions/Sinicize.txt":
            updated = rewrite_sinicize_decision(updated)
        elif relative.as_posix() == "events/WomenInHistory.txt":
            updated = rewrite_women_history_cultures(updated)
        if reference_pattern.search(updated):
            raise ValueError(f"Superseded culture reference survived in {relative}")
        target = MOD / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        marker = f"# {MARKER}: inherited culture reference override\n"
        target.write_bytes((marker + updated).encode("latin-1"))
        written.append(relative)
    manifest = OUT / "inherited_reference_overrides.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    previous = set()
    if manifest.exists():
        previous = {
            Path(line)
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    current = set(written)
    for stale in sorted(previous - current):
        target = MOD / stale
        if not target.exists():
            continue
        first_line = target.read_bytes().decode("latin-1").splitlines()[:1]
        if first_line and (
            first_line[0].startswith("# B40 Zhonghua-Baiyue culture overhaul:")
            or first_line[0].startswith(f"# {MARKER}:")
        ):
            target.unlink()
    manifest.write_text("\n".join(path.as_posix() for path in written) + "\n", encoding="utf-8")
    return written


def retarget_manifest_lines(text: str, targets: dict[int, str]) -> str:
    managed = set(OLD_TO_DEFAULT) | ALL_NEW_CULTURES
    culture_pattern = re.compile(
        r'"(' + "|".join(map(re.escape, sorted(managed, key=lambda value: (-len(value), value)))) + r')"'
    )
    output: list[str] = []
    for line in text.splitlines(keepends=True):
        match = re.match(r"\s*(\d+)\s*:", line)
        if not match:
            match = re.search(r"\bProvince\((\d+)\s*,", line)
        if match and int(match.group(1)) in targets:
            desired = targets[int(match.group(1))]
            line = culture_pattern.sub(f'"{desired}"', line)
        output.append(line)
    return "".join(output)


def update_replayable_scripts(targets: dict[int, str]) -> None:
    for path in sorted((ROOT / "tools/map_pipeline").glob("*.py")):
        if path == Path(__file__).resolve():
            continue
        data = path.read_bytes()
        text = data.decode("utf-8")
        updated = retarget_manifest_lines(replace_culture_assignments(text), targets)

        # These generators encode culture in a function-level expression rather
        # than on an ID-bearing manifest line, so keep their minimal approved
        # expressions explicit and deterministic.
        if path.name == "apply_fujian_refinement.py":
            updated = re.sub(
                r'f"culture = \{\(\{4957:.*?\}\)\.get\(p\.province_id, \'gdd_min\'\)\}"',
                '"culture = gdd_min"',
                updated,
            )
        elif path.name == "apply_hainan_5_wuzhishan_refinement.py":
            approved = {pid: targets[pid] for pid in (666, 5301, 5302, 5303, 2160)}
            expression = f'f"culture = {{({approved!r})[p.province_id]}}"'
            updated = re.sub(r'f"culture = \{\(\{.*?\}\)\[p\.province_id\]\}"', expression, updated)
        if updated != text:
            path.write_bytes(updated.encode("utf-8"))


def update_mod_script_tokens() -> None:
    roots = [MOD / "common", MOD / "events", MOD / "decisions", MOD / "missions"]
    excluded_parts = {"cultures", "history"}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.txt"):
            if any(part in excluded_parts for part in path.parts):
                continue
            data = path.read_bytes()
            text = data.decode("latin-1")
            updated = replace_culture_assignments(text)
            if updated != text:
                path.write_bytes(updated.encode("latin-1"))

    # gdd_chaoshan and gdd_min merge into Minyue.  Remove the now-adjacent
    # duplicate trigger left in this mod-owned privilege instead of widening a
    # generic dedupe across unrelated scripts.
    privilege = MOD / "common/estate_privileges/gdd_estate_privileges.txt"
    if privilege.exists():
        text = privilege.read_bytes().decode("latin-1")
        updated = re.sub(
            r"(?m)^(\s*culture\s*=\s*gdd_min\s*\r?\n)\s*culture\s*=\s*gdd_min\s*\r?\n",
            r"\1",
            text,
        )
        if updated != text:
            privilege.write_bytes(updated.encode("latin-1"))


def restore_tracked_line_endings() -> None:
    """Keep each tracked text file's pre-transaction newline convention."""
    roots = [
        MOD / "common",
        MOD / "events",
        MOD / "decisions",
        MOD / "missions",
        MOD / "history/countries",
        MOD / "history/provinces",
        ROOT / "tools/map_pipeline",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.txt"):
            relative = path.relative_to(ROOT).as_posix()
            result = subprocess.run(
                ["git", "show", f"HEAD:{relative}"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode != 0:
                continue
            current = path.read_bytes()
            baseline = result.stdout
            normalized = current.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if b"\r\n" in baseline:
                desired = normalized.replace(b"\n", b"\r\n")
            else:
                desired = normalized
            if desired != current:
                path.write_bytes(desired)


def write_localisation() -> None:
    obsolete = (
        MOD / "localisation_source/gdd_b40_culture_overhaul_readable_utf8.txt",
        MOD / "localisation/gdd_b40_culture_overhaul_l_english.yml",
        MOD / "localisation_source/gdd_b41_culture_overhaul_readable_utf8.txt",
        MOD / "localisation/gdd_b41_culture_overhaul_l_english.yml",
        MOD / "localisation/000_gdd_b41_culture_overhaul_l_english.yml",
    )
    for path in obsolete:
        path.unlink(missing_ok=True)
    # Existing group keys come from inherited aow/text localisation.  EU4's
    # localisation/replace layer deterministically overrides those duplicates;
    # the 000 prefix also keeps this file first within that layer.
    source = MOD / "localisation_source/000_gdd_b41_culture_overhaul_readable_utf8.txt"
    target = MOD / "localisation/replace/000_gdd_b41_culture_overhaul_l_english.yml"
    lines = [
        "l_english:",
        ' east_asian:0 "诸夏"',
        ' gdd_baiyue_group:0 "百越"',
        ' korean_g:0 "殷商"',
        ' gdd_qiang_group:0 "羌"',
    ]
    for key, name in CULTURE_DISPLAY.items():
        lines.append(f' {key}:0 "{name}"')
    lines.append(' gdd_zhuang_new:0 "汉化壮侗"')
    source.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file

    encode_file(source, target)
    verify_file(source, target)

    country_source = MOD / "localisation_source/001_gdd_b43_country_name_overrides_readable_utf8.txt"
    country_target = MOD / "localisation/replace/001_gdd_b43_country_name_overrides_l_english.yml"
    country_lines = ["l_english:"]
    for tag, (name, adjective) in COUNTRY_NAME_OVERRIDES.items():
        country_lines.append(f' {tag}:0 "{name}"')
        country_lines.append(f' {tag}_ADJ:0 "{adjective}"')
    country_source.write_text("\n".join(country_lines) + "\n", encoding="utf-8-sig")
    encode_file(country_source, country_target)
    verify_file(country_source, country_target)

    main_source = MOD / "localisation_source/gdd_l_english_readable_utf8.txt"
    text = main_source.read_text(encoding="utf-8-sig")
    for tag in COUNTRY_NAME_OVERRIDES:
        text = re.sub(
            rf'(?m)^[ \t]*{re.escape(tag)}(?:_ADJ)?:\d*[ \t]+"[^"]*"[ \t]*(?:\r?\n|$)',
            "",
            text,
        )
    text = text.replace(
        "所有§Y广府§!、§Y客家§!、§Y潮汕§!或§Y闽§!文化的直属省份",
        "所有§Y粤§!、§Y客家§!或§Y闽越§!文化的直属省份",
    )
    main_source.write_text(text, encoding="utf-8-sig")
    main_target = MOD / "localisation/gdd_l_english.yml"
    encode_file(main_source, main_target)
    verify_file(main_source, main_target)


def localisation_names() -> dict[int, str]:
    result: dict[int, str] = {}
    for path in (MOD / "localisation_source").glob("*.txt"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for pid, name in re.findall(r'^\s*PROV(\d+):\d*\s+"([^"]+)"', text, re.M):
            result[int(pid)] = name
    return result


def write_manifest(
    targets: dict[int, str],
    previous: dict[int, str],
    history_names: dict[int, str],
    reverse_areas: dict[int, str],
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    names = localisation_names()
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("province_id", "province_name", "area", "previous_culture", "target_culture", "history_file"),
        )
        writer.writeheader()
        for pid, target in sorted(targets.items()):
            writer.writerow(
                {
                    "province_id": pid,
                    "province_name": names.get(pid, ""),
                    "area": reverse_areas.get(pid, ""),
                    "previous_culture": previous[pid],
                    "target_culture": target,
                    "history_file": history_names[pid],
                }
            )

    counts = Counter(targets.values())
    lines = [
        "# 诸夏—百越—殷商—羌文化重构分配摘要",
        "",
        f"- 批次：{MARKER}",
        f"- 已更新省份历史：{len(targets)}",
        "- 诸夏文化：12",
        "- 百越文化：6",
        "- 殷商文化：3",
        "- 羌文化：3",
        "- 已通过同路径 `00_cultures.txt` 覆盖删除旧定义，并原样迁移朝鲜、安南、苗瑶、白、彝的人名库",
        "",
        "| 文化代码 | 名称 | 已分配历史文件数 |",
        "|---|---|---:|",
    ]
    for key, name in CULTURE_DISPLAY.items():
        lines.append(f"| `{key}` | {name} | {counts[key]} |")
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    renamed = canonicalize_inherited_history_filenames()
    areas, reverse_areas = area_members()
    targets = build_targets(areas)
    write_culture_definitions()
    previous, history_names = update_province_histories(targets)
    update_country_histories()
    write_inherited_reference_overrides()
    update_mod_script_tokens()
    update_replayable_scripts(targets)
    restore_tracked_line_endings()
    write_localisation()
    write_manifest(targets, previous, history_names, reverse_areas)
    validate_effective_history_uniqueness()
    print(
        f"{MARKER}: {len(targets)} province histories updated; "
        f"{len(renamed)} inherited filenames canonicalised"
    )


if __name__ == "__main__":
    main()
