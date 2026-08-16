#!/usr/bin/env python3
"""Keep Nanjing-specific gameplay on Jiangning 1821, not new Liuhe 5056."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "guangdong_independent_practice"
JIANGNING = 1821  # original Nanjing map slot
LIUHE = 5056      # newly split province
STALE_OVERRIDES = (
    MOD / "common/great_projects/zz_gdd_nanjing_relocation.txt",
    MOD / "common/estate_agendas/zz_gdd_nanjing_relocation.txt",
)


def named_block(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise ValueError(f"Missing block: {name}")
    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start():index + 1]
    raise ValueError(f"Unclosed block: {name}")


def replace_named_block(text: str, name: str, replacement: str) -> str:
    old = named_block(text, name)
    return text.replace(old, replacement, 1)


def replace_province_id(text: str, old: int, new: int) -> str:
    return re.sub(rf"(?<!\d){old}(?!\d)", str(new), text)


def initial_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^#\r\n]+)", text)
    return match.group(1).strip() if match else None


def history_path(province_id: int) -> Path:
    paths = [
        path for path in (MOD / "history/provinces").glob("*.txt")
        if re.match(rf"{province_id}(?:\D|$)", path.name)
    ]
    if len(paths) != 1:
        raise ValueError(f"Expected one history for {province_id}; found {paths}")
    return paths[0]


def validate_histories() -> None:
    jiangning = history_path(JIANGNING).read_text(encoding="utf-8-sig")
    liuhe = history_path(LIUHE).read_text(encoding="utf-8-sig")
    expected = {
        "jiangning": {
            "culture": "gdd_wu", "trade_goods": "grain", "base_tax": "7",
            "base_production": "8", "base_manpower": "4",
        },
        "liuhe": {
            "culture": "gdd_jianghuai", "trade_goods": "silk", "base_tax": "2",
            "base_production": "2", "base_manpower": "1", "fort_15th": "yes",
        },
    }
    for label, text in (("jiangning", jiangning), ("liuhe", liuhe)):
        for key, value in expected[label].items():
            if initial_value(text, key) != value:
                raise ValueError(f"{label} {key} is not the reviewed value {value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla-root", type=Path, required=True)
    args = parser.parse_args()
    vanilla = args.vanilla_root.resolve()

    validate_histories()

    monument_source = (vanilla / "common/great_projects/01_monuments.txt").read_text(
        encoding="utf-8-sig"
    )
    for name in ("porcelain_tower_nanjing", "grand_canal_4"):
        block = named_block(monument_source, name)
        if not re.search(rf"(?m)^\s*start\s*=\s*{JIANGNING}\b", block):
            raise ValueError(f"{name} is not on Jiangning {JIANGNING} in vanilla")
        if re.search(rf"(?<!\d){LIUHE}(?!\d)", re.sub(r"#.*", "", block)):
            raise ValueError(f"{name} still references Liuhe {LIUHE}")

    agenda_source = (vanilla / "common/estate_agendas/09_eunuchs_agendas.txt").read_text(
        encoding="utf-8-sig"
    )
    agenda = named_block(agenda_source, "estate_eunuchs_porcelain_tower_agenda")
    executable_agenda = re.sub(r"#.*", "", agenda)
    if str(JIANGNING) not in executable_agenda or str(LIUHE) in executable_agenda:
        raise ValueError("Vanilla porcelain-tower agenda is not anchored to Jiangning")

    for path in STALE_OVERRIDES:
        if path.exists():
            path.unlink()

    modifiers_path = MOD / "common/triggered_modifiers/00_triggered_modifiers.txt"
    modifiers = modifiers_path.read_text(encoding="utf-8-sig")
    for name in ("ai_wants_chinese_capitals", "lost_control_of_nanjing"):
        block = named_block(modifiers, name)
        restored = replace_province_id(block, LIUHE, JIANGNING)
        modifiers = replace_named_block(modifiers, name, restored)
    modifiers_path.write_text(modifiers, encoding="utf-8")

    for path in (MOD / "common/great_projects").glob("*.txt"):
        text = re.sub(r"#.*", "", path.read_text(encoding="utf-8-sig"))
        if re.search(rf"(?m)^\s*start\s*=\s*{LIUHE}\b", text):
            raise ValueError(f"Liuhe still starts a great project in {path}")
    checked_modifiers = modifiers_path.read_text(encoding="utf-8")
    for name in ("ai_wants_chinese_capitals", "lost_control_of_nanjing"):
        block = named_block(checked_modifiers, name)
        executable = re.sub(r"#.*", "", block)
        if str(LIUHE) in executable or str(JIANGNING) not in executable:
            raise ValueError(f"Triggered modifier {name} is not restored to Jiangning")

    print("Nanjing semantics aligned: 1821 Jiangning; 5056 Liuhe has no great project")


if __name__ == "__main__":
    main()
