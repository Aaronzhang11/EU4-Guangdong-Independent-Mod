#!/usr/bin/env python3
"""Apply the reviewed B44 worldview-safe province toponyms.

This terminal transaction changes no map geometry.  It gives inherited
province keys a deterministic ``localisation/replace`` provider, aligns the
definition and initial capital strings, and resolves the Jiangning/Liuhe
semantic split by explicit province ID.  Physical history filenames stay unchanged so
they continue to shadow the required dependency's exact virtual paths.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
MAP = MOD / "map"
HISTORIES = MOD / "history/provinces"
COUNTRY_HISTORIES = MOD / "history/countries"
SOURCE = MOD / "localisation_source/002_gdd_b44_worldview_toponyms_readable_utf8.txt"
TARGET = MOD / "localisation/replace/002_gdd_b44_worldview_toponyms_l_english.yml"
OUT = ROOT / "planning/worldview_toponyms_b44"
MANIFEST = OUT / "toponym_manifest.csv"
REPORT = OUT / "apply_report.json"
BATCH = "B44_worldview_toponyms"
TRIGGERED_MODIFIERS = MOD / "common/triggered_modifiers/00_triggered_modifiers.txt"
STALE_RELOCATION_OVERRIDES = (
    MOD / "common/great_projects/zz_gdd_nanjing_relocation.txt",
    MOD / "common/estate_agendas/zz_gdd_nanjing_relocation.txt",
)


# previous_chinese, target_chinese, previous_definition, target_definition,
# target initial capital (None for a water province), reviewed reason.
TOPONYMS: dict[int, tuple[str, str, str, str, str | None, str]] = {
    663: ("文山", "广南", "Wenshan", "Guangnan", "Guangnan", "align the map cell with its Guangnan history"),
    668: ("澳门", "香山", "Macau", "Xiangshan", "Xiangshan", "use the 1444 county-scale name"),
    669: ("闽侯", "福州", "Minhou", "Fuzhou", "Fuzhou", "avoid the modern Minhou composite"),
    678: ("康定", "打箭炉", "Kangding", "Dajianlu", "Dajianlu", "restore the pre-Kangding name"),
    702: ("呼和浩特", "丰州", "Ulaanchab", "Fengzhou", "Fengzhou", "the Hohhot city name postdates the start"),
    703: ("承德", "热河", "Chengde", "Rehe", "Rehe", "remove the Qing imperial-bestowal name"),
    1816: ("燕", "蓟", "Yan", "Ji", "Ji", "separate the Yan state name from its capital city"),
    1821: ("六合", "江宁", "Liuhe", "Jiangning", "Jiangning", "keep the original Nanjing map slot as Jiangning"),
    2136: ("宣化", "上谷", "Xuanhua", "Shanggu", "Shanggu", "remove the late imperial prefectural name"),
    2143: ("凤阳", "濠州", "Fengyang", "Haozhou", "Haozhou", "remove the Ming dynastic-patrimony name"),
    2149: ("宁波", "明州", "Ningbo", "Mingzhou", "Mingzhou", "remove a name coined around the Ming dynastic taboo"),
    2158: ("韶关", "韶州", "Shaoguan", "Shaozhou", "Shaozhou", "use the long-lived medieval prefectural name"),
    2178: ("潞安", "潞州", "Luan", "Luzhou", "Luzhou", "remove the post-1444 prefectural name"),
    4197: ("蕲州", "蕲州", "De'an", "Qizhou", "Qizhou", "unify the existing Qizhou override with its semantics"),
    4946: ("香港", "屯门", "Hong Kong", "Tuen Mun", "Tuen Mun", "use the existing historical seat instead of the modern city frame"),
    5008: ("郧阳", "郧", "Yunyang", "Yun", "Yun", "remove the post-1444 Yunyang prefectural name"),
    5010: ("承天", "安陆", "Chengtian", "Anlu", "Anlu", "remove the Jiajing imperial-patrimony title"),
    5035: ("武汉江段", "夏口江段", "Wuhan Reach", "Xiakou Reach", None, "remove the modern Wuhan composite"),
    5056: ("建业", "六合", "Jianye", "Liuhe", "Liuhe", "identify the newly split province as Liuhe"),
    5095: ("盐源", "盐井", "Yanyuan", "Yanjing", "Yanjing", "use the earlier salt-well name"),
    5104: ("淄博（临淄）", "临淄", "Linzi", "Linzi", "Linzi", "remove the modern Zibo composite"),
    5202: ("玉林", "郁林", "Yuzhou", "Yulin", "Yulin", "restore the historical Yulin spelling and semantics"),
    5211: ("山海关", "临渝关", "Shanhaiguan", "Linyuguan", "Linyuguan", "remove the Ming-era pass name"),
    5222: ("天津", "直沽", "Tianjin", "Zhigu", "Zhigu", "remove the emperor-dependent Tianjin name"),
    5228: ("保山", "永昌府", "Baoshan", "Yongchangfu", "Yongchang", "restore the pre-Baoshan regional seat"),
    5230: ("玉溪", "新兴州", "Yuxi", "Xinxingzhou", "Xinxing", "remove the modern Yuxi county name"),
    5232: ("昭通", "乌蒙", "Zhaotong", "Wumeng", "Wumeng", "remove the Qing conquest-era name"),
    5233: ("镇雄", "芒部", "Zhenxiong", "Mangbu", "Mangbu", "restore the pre-Zhenxiong polity name"),
    5234: ("宣威", "沾益", "Xuanwei", "Zhanyi", "Zhanyi", "remove the late imperial prefectural name"),
    5235: ("临沧", "勐缅", "Lincang", "Mengmian", "Mengmian", "remove the twentieth-century Lincang name"),
    5271: ("岐州", "邠州", "Binzhou", "Binzhou", "Binzhou", "fix the localisation/definition semantic mismatch"),
}


JIANGNING = {
    "owner": "WUU",
    "controller": "WUU",
    "culture": "gdd_wu",
    "base_tax": "7",
    "base_production": "8",
    "base_manpower": "4",
}
LIUHE = {
    "owner": "XU2",
    "controller": "XU2",
    "culture": "gdd_jianghuai",
    "base_tax": "2",
    "base_production": "2",
    "base_manpower": "1",
}
# B43/B50 later transfer Liuhe to Huai without changing the B44 toponym,
# culture or development policy.  The B44 checker must remain valid both
# immediately after B44 (XU2) and on the final integrated map (HUA).
LIUHE_VALID_OWNERS = {"XU2", "HUA"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_if_changed(path: Path, text: str, *, encoding: str = "utf-8") -> bool:
    current = path.read_text(encoding=encoding) if path.exists() else None
    if current == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return True


def history_path(province_id: int) -> Path:
    matches = [
        path for path in HISTORIES.glob("*.txt")
        if re.match(rf"{province_id}(?:\D|$)", path.name)
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one local history for {province_id}; found {matches}")
    return matches[0]


def initial_section(text: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\d+\.\d+\.\d+\s*=\s*\{", text)
    return (text[:match.start()], text[match.start():]) if match else (text, "")


def initial_value(text: str, key: str) -> str | None:
    initial, _dated = initial_section(text)
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\r\n]+)", initial)
    return match.group(1).strip().strip('"') if match else None


def set_initial_value(text: str, key: str, value: str) -> str:
    initial, dated = initial_section(text)
    rendered = (
        f'"{value}"'
        if key == "capital" and not value.isdigit()
        else value
    )
    initial, count = re.subn(
        rf"(?m)^(\s*{re.escape(key)}\s*=\s*)[^#\r\n]+?([ \t]*(?:#.*)?)$",
        lambda match: (
            f"{match.group(1)}{rendered}"
            + (f"\t{match.group(2).lstrip()}" if match.group(2).lstrip() else "")
        ),
        initial,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Missing initial {key}")
    return initial + dated


def set_initial_core(text: str, owner: str) -> str:
    initial, dated = initial_section(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    initial = re.sub(
        r"(?m)^\s*add_core\s*=\s*(?:WUU|XU2|MNG)\s*(?:\r?\n|$)",
        "",
        initial,
    )
    controller = re.search(r"(?m)^\s*controller\s*=\s*\S+\s*$", initial)
    if not controller:
        raise ValueError("Missing controller insertion point")
    initial = (
        initial[:controller.end()]
        + f"{newline}add_core = {owner}"
        + initial[controller.end():]
    )
    return initial + dated


def named_block(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing block {name}")
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise ValueError(f"Unclosed block {name}")


def replace_named_block(text: str, name: str, replacement: str) -> str:
    block = named_block(text, name)
    return text.replace(block, replacement, 1)


def restore_jiangning_gameplay_hooks() -> bool:
    text = read_text(TRIGGERED_MODIFIERS)
    updated = text
    for name in ("ai_wants_chinese_capitals", "lost_control_of_nanjing"):
        block = named_block(updated, name)
        restored = re.sub(r"(?<!\d)5056(?!\d)", "1821", block)
        updated = replace_named_block(updated, name, restored)
    return write_if_changed(TRIGGERED_MODIFIERS, updated)


def remove_stale_relocation_overrides() -> list[str]:
    removed: list[str] = []
    for path in STALE_RELOCATION_OVERRIDES:
        if path.exists():
            path.unlink()
            removed.append(str(path.relative_to(ROOT)))
    return removed


def validate_jiangning_gameplay_hooks() -> None:
    for path in (MOD / "common/great_projects").glob("*.txt"):
        text = read_text(path)
        if re.search(r"(?m)^\s*start\s*=\s*5056\b", text):
            raise ValueError(f"Liuhe 5056 still starts a great project in {path}")
    for path in (MOD / "common/estate_agendas").glob("*.txt"):
        text = read_text(path)
        if "estate_eunuchs_porcelain_tower_agenda" not in text:
            continue
        block = named_block(text, "estate_eunuchs_porcelain_tower_agenda")
        if re.search(r"(?<!\d)5056(?!\d)", re.sub(r"#.*", "", block)):
            raise ValueError(f"Liuhe 5056 still carries the Nanjing agenda in {path}")
    modifiers = read_text(TRIGGERED_MODIFIERS)
    for name in ("ai_wants_chinese_capitals", "lost_control_of_nanjing"):
        block = named_block(modifiers, name)
        executable = re.sub(r"#.*", "", block)
        if re.search(r"(?<!\d)5056(?!\d)", executable):
            raise ValueError(f"{name}: stale Liuhe 5056 reference")
        if not re.search(r"(?<!\d)1821(?!\d)", executable):
            raise ValueError(f"{name}: missing Jiangning 1821 reference")


def update_definition() -> bool:
    path = MAP / "definition.csv"
    rows = path.read_text(encoding="latin-1").splitlines()
    seen: set[int] = set()
    output: list[str] = []
    for row in rows:
        fields = row.split(";")
        if fields and fields[0].isdigit() and int(fields[0]) in TOPONYMS:
            province_id = int(fields[0])
            fields[4] = TOPONYMS[province_id][3]
            row = ";".join(fields)
            seen.add(province_id)
        output.append(row)
    missing = set(TOPONYMS) - seen
    if missing:
        raise ValueError(f"definition.csv is missing B44 IDs: {sorted(missing)}")
    return write_if_changed(path, "\n".join(output) + "\n", encoding="latin-1")


def update_histories() -> list[str]:
    changed: list[str] = []
    for province_id, policy in TOPONYMS.items():
        target_definition = policy[3]
        target_capital = policy[4]
        path = history_path(province_id)
        text = read_text(path)
        text = re.sub(
            rf"\A(?:\ufeff)?[^\r\n]*",
            f"# {province_id} - {target_definition}",
            text,
            count=1,
        )
        if target_capital is not None:
            text = set_initial_value(text, "capital", target_capital)
        if province_id in (1821, 5056):
            values = JIANGNING if province_id == 1821 else LIUHE
            for key, value in values.items():
                text = set_initial_value(text, key, value)
            text = set_initial_core(text, values["owner"])
            newline = "\r\n" if "\r\n" in text else "\n"
            text = text.rstrip("\r\n") + newline
        if write_if_changed(path, text):
            changed.append(path.name)
    return changed


def update_country_capitals() -> list[str]:
    changed: list[str] = []
    policies = {
        "WUU - Wu.txt": (1821, True),
        "MNG - Ming.txt": (1821, False),
    }
    for filename, (capital, fixed) in policies.items():
        path = COUNTRY_HISTORIES / filename
        text = read_text(path)
        text = set_initial_value(text, "capital", str(capital))
        if filename == "MNG - Ming.txt":
            text = re.sub(r"#\s*(?:Nanjing|Jianye|Jiangning)", "# Jiangning", text, count=1)
        if fixed:
            text = set_initial_value(text, "fixed_capital", str(capital))
        if write_if_changed(path, text):
            changed.append(filename)
    return changed


def remove_obsolete_readable_keys() -> list[str]:
    changed: list[str] = []
    ids = "|".join(str(province_id) for province_id in sorted(TOPONYMS))
    pattern = re.compile(
        rf'(?m)^[ \t]*PROV(?:_ADJ)?(?:{ids}):\d*[ \t]+"[^"]*"[ \t]*(?:\r?\n|$)'
    )
    for path in sorted((MOD / "localisation_source").glob("*.txt")):
        if path == SOURCE:
            continue
        text = read_text(path)
        updated = pattern.sub("", text)
        if updated != text and write_if_changed(path, updated, encoding="utf-8-sig"):
            changed.append(path.name)
    return changed


def write_localisation() -> bool:
    lines = ["l_english:"]
    for province_id, policy in sorted(TOPONYMS.items()):
        chinese = policy[1]
        lines.append(f' PROV{province_id}:0 "{chinese}"')
        lines.append(f' PROV_ADJ{province_id}:0 "{chinese}"')
    changed = write_if_changed(SOURCE, "\n".join(lines) + "\n", encoding="utf-8-sig")
    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import encode_file, verify_file

    encode_file(SOURCE, TARGET)
    verify_file(SOURCE, TARGET)
    return changed


def definition_rows() -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for row in (MAP / "definition.csv").read_text(encoding="latin-1").splitlines():
        fields = row.split(";")
        if fields and fields[0].isdigit():
            result[int(fields[0])] = fields
    return result


def write_manifest() -> None:
    rows = definition_rows()
    OUT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "batch", "province_id", "rgb", "previous_chinese", "target_chinese",
                "previous_definition", "target_definition", "history_file",
                "target_capital", "reason", "geometry_policy",
            ),
        )
        writer.writeheader()
        for province_id, policy in sorted(TOPONYMS.items()):
            fields = rows[province_id]
            writer.writerow({
                "batch": BATCH,
                "province_id": province_id,
                "rgb": ",".join(fields[1:4]),
                "previous_chinese": policy[0],
                "target_chinese": policy[1],
                "previous_definition": policy[2],
                "target_definition": policy[3],
                "history_file": history_path(province_id).name,
                "target_capital": policy[4] or "",
                "reason": policy[5],
                "geometry_policy": "no pixel or membership change",
            })


def validate() -> dict[str, object]:
    rows = definition_rows()
    readable = read_text(SOURCE)
    all_readable = {
        path: read_text(path)
        for path in (MOD / "localisation_source").glob("*.txt")
    }
    for province_id, policy in TOPONYMS.items():
        if rows[province_id][4] != policy[3]:
            raise ValueError(f"{province_id}: incorrect definition name")
        history = read_text(history_path(province_id))
        if policy[4] is not None and initial_value(history, "capital") != policy[4]:
            raise ValueError(f"{province_id}: incorrect initial capital")
        for prefix in ("PROV", "PROV_ADJ"):
            key = f"{prefix}{province_id}"
            expected = rf'(?m)^\s*{key}:0\s+"{re.escape(policy[1])}"\s*$'
            if len(re.findall(expected, readable)) != 1:
                raise ValueError(f"{key}: missing or incorrect B44 provider")
            provider_values = [
                (path, value)
                for path, text in all_readable.items()
                for value in re.findall(
                    rf'(?m)^\s*{key}:\d+\s+"([^"\r\n]*)"\s*$', text
                )
            ]
            if not provider_values:
                raise ValueError(f"{key}: readable provider is missing")
            conflicts = [
                str(path.relative_to(MOD))
                for path, value in provider_values
                if value != policy[1]
            ]
            if conflicts:
                raise ValueError(
                    f"{key}: conflicting readable provider(s): {', '.join(conflicts)}"
                )

    for province_id, expected in ((1821, JIANGNING), (5056, LIUHE)):
        text = read_text(history_path(province_id))
        for key, value in expected.items():
            actual = initial_value(text, key)
            if province_id == 5056 and key in {"owner", "controller"}:
                if actual not in LIUHE_VALID_OWNERS:
                    raise ValueError(f"{province_id}: {key} has invalid owner {actual}")
            elif actual != value:
                raise ValueError(f"{province_id}: {key} is not {value}")
        initial, _dated = initial_section(text)
        owner = initial_value(text, "owner")
        if len(re.findall(rf"(?m)^\s*add_core\s*=\s*{owner}\s*$", initial)) != 1:
            raise ValueError(f"{province_id}: incorrect owner core")
        possible_stale_cores = {"WUU", "XU2", "HUA"} - {owner}
        for other in possible_stale_cores:
            if re.search(rf"(?m)^\s*add_core\s*=\s*{other}\s*$", initial):
                raise ValueError(f"{province_id}: stale {other} core")

    combined_development = sum(
        int(initial_value(read_text(history_path(province_id)), key) or -1)
        for province_id in (1821, 5056)
        for key in ("base_tax", "base_production", "base_manpower")
    )
    if combined_development != 24:
        raise ValueError(f"Jiangning/Liuhe combined development changed: {combined_development}")

    for filename in ("WUU - Wu.txt", "MNG - Ming.txt"):
        text = read_text(COUNTRY_HISTORIES / filename)
        if initial_value(text, "capital") != "1821":
            raise ValueError(f"{filename}: capital is not Jiangning 1821")
    wuu = read_text(COUNTRY_HISTORIES / "WUU - Wu.txt")
    if initial_value(wuu, "fixed_capital") != "1821":
        raise ValueError("WUU fixed capital is not Jiangning 1821")

    validate_jiangning_gameplay_hooks()

    sys.path.insert(0, str(ROOT / "tools"))
    from encode_eu4_chinese_localisation import verify_file

    verify_file(SOURCE, TARGET)
    actual_liuhe = dict(LIUHE)
    liuhe_text = read_text(history_path(5056))
    actual_liuhe["owner"] = initial_value(liuhe_text, "owner")
    actual_liuhe["controller"] = initial_value(liuhe_text, "controller")
    return {
        "batch": BATCH,
        "toponym_count": len(TOPONYMS),
        "province_ids": sorted(TOPONYMS),
        "geometry": "unchanged",
        "jiangning": JIANGNING,
        "liuhe": actual_liuhe,
        "combined_development": combined_development,
        "localisation_source": str(SOURCE.relative_to(ROOT)),
        "localisation_target": str(TARGET.relative_to(ROOT)),
    }


def apply() -> dict[str, object]:
    bitmap = MAP / "provinces.bmp"
    before_bitmap = sha256(bitmap)
    changed = {
        "definition": update_definition(),
        "province_histories": update_histories(),
        "country_histories": update_country_capitals(),
        "jiangning_gameplay_hooks": restore_jiangning_gameplay_hooks(),
        "removed_stale_relocation_overrides": remove_stale_relocation_overrides(),
        "old_localisation_sources": remove_obsolete_readable_keys(),
        "b44_localisation_source": write_localisation(),
    }
    write_manifest()
    after_bitmap = sha256(bitmap)
    if before_bitmap != after_bitmap:
        raise ValueError("B44 changed provinces.bmp despite the no-geometry policy")
    result = validate()
    result["provinces_bmp_sha256"] = after_bitmap
    result["changed"] = changed
    result["backup_path"] = None
    result["changed_pixels"] = 0
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = validate() if args.check else apply()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
