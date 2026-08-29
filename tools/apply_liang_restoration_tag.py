#!/usr/bin/env python3
"""Idempotently create the dormant LGU Liang restoration country tag."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from apply_culture_country_name_pools import apply as apply_country_name_pools
from generate_liang_small_seal_mask import run as generate_liang_mask


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"

TAG_FILE = MOD / "common/country_tags/gdd_country_tags.txt"
COUNTRY_FILE = MOD / "common/countries/B76_Liang.txt"
HISTORY_FILE = MOD / "history/countries/LGU - Liang.txt"
LOCALISATION_SOURCE = MOD / "localisation_source/gdd_liang_restoration_readable_utf8.txt"
LOCALISATION_TARGET = MOD / "localisation/gdd_liang_restoration_l_english.yml"
ENCODER = ROOT / "tools/encode_eu4_chinese_localisation.py"
SEAL_GENERATOR = ROOT / "tools/generate_zhuxia_seal_flags.py"
CULTURE_GENERATOR = ROOT / "tools/map_pipeline/apply_culture_overhaul.py"
VANILLA = Path.home() / "Library/Application Support/Steam/steamapps/common/Europa Universalis IV"

BEGIN = "# GDD_B76_LIANG_RESTORATION_TAG_BEGIN"
END = "# GDD_B76_LIANG_RESTORATION_TAG_END"

COUNTRY_TEXT = """# B76 dormant Liang restoration country definition.
graphical_culture = asiangfx

color = { 48 91 112 }
revolutionary_colors = { 5 8 1 }

historical_units = {
    chinese_longspear
    eastern_bow
    chinese_footsoldier
    chinese_steppe
    asian_arquebusier
    asian_charge_cavalry
    asian_mass_infantry
    manchu_banner
    han_banner
    asian_musketeer
    chinese_dragoon
    reformed_asian_musketeer
    reformed_asian_cavalry
    reformed_manchu_rifle
}

ship_names = {
    Wuwei Guzang Liangzhou Yongchang Jingyuan Qilian Yanzhi
    Bailong Heishui Jincheng Shandan Xiutu Hongchi Tianshui
}
"""

HISTORY_TEXT = """# B76 dormant Liang restoration tag.
# No 1444 ownership or cores: the restoration chain will create the polity.
government = monarchy
add_government_reform = feudalism_reform
government_rank = 1
technology_group = chinese
religion = confucianism
primary_culture = gdd_long
capital = 708
"""

LOCALISATION_TEXT = """l_english:
 LGU:0 "凉"
 LGU_ADJ:0 "凉"

 gdd_liang_restoration.1.t:0 "亡凉遗使谒天子"
 gdd_liang_restoration.1.d:0 "凉国覆亡以后，宗庙丘墟，旧臣离散，只有嗣君张承祚与少数随从仍奉守国统。今日，老臣段守节携张承祚入朝，献上故国谱牒与残存印信，请天子承认凉国宗祀未绝，并准许他们遍告诸侯，求取一地以续国命。\\n\\n天子可以承认凉国嗣君的身份并授予使团符节，却不命令任何诸侯割地；复凉与否，将由列国自行决定。"
 gdd_liang_restoration.1.a:0 "赐之符节，许告列国"
 gdd_liang_restoration.1.a.tt:0 "记录所有直接拥有至少§Y5§!个省份的周天下国家，并随机排定一次不重复的请封行程。第一站将在约§Y90天§!后抵达。"

 gdd_liang_restoration.10.t:0 "凉使至庭"
 gdd_liang_restoration.10.d.grant:0 "持天子符节的凉国使团已经抵达我国。张承祚自称亡凉嗣君，段守节则代他陈说来意：他们不求恢复全部旧疆，只请我国从境内授予一座城邑，使凉国得以复立宗庙，并世代作为我国的卫戍国。\\n\\n依照他们提出的盟约，若我国日后与凉国共同收回武威、靖远和永昌，三地应归还凉国，而今日授予的原始封地则交还我国。愿意存亡继绝的诸侯，也将由此获得天下称颂。"
 gdd_liang_restoration.10.d.homeland:0 "持天子符节的凉国使团已经抵达我国。张承祚自称亡凉嗣君，段守节则指出，武威、靖远和永昌三处凉国故土如今恰好都在我国治下。他们请求我国不再另授寄居之地，而是直接以三地恢复凉国，使其世代作为我国的卫戍国。\\n\\n天子并未命令我国割地；是否以故土复凉，完全取决于我们的选择。愿意存亡继绝的诸侯，也将由此获得天下称颂。"
 gdd_liang_restoration.10.a:0 "存亡继绝，许其复国"
 gdd_liang_restoration.10.b:0 "国土不可轻授"
 gdd_liang_restoration.10.a.tt:0 "凉国将获得符合盟约的土地，成为我国的§Y卫戍国§!并立即加入§Y周天下§!；我国永久获得§G+0.33外交声誉§!的§Y存亡继绝§!修正。"
 gdd_liang_restoration.10.a.tt.grant:0 "自动将本国总发展度最低的合格省份授予凉国。首都、未完成殖民地以及武威、靖远、永昌不参与选择；并列最低者随机决定。凉国将成为我国的§Y卫戍国§!并加入§Y周天下§!，我国永久获得§Y存亡继绝§!修正。"
 gdd_liang_restoration.10.a.tt.homeland:0 "武威、靖远和永昌将直接归凉国，凉国以武威为都，成为我国的§Y卫戍国§!并加入§Y周天下§!；我国永久获得§Y存亡继绝§!修正。"
 gdd_liang_restoration.10.b.tt:0 "本次拒绝不会带来惩罚。使团将在约§Y180天§!后前往名单中的下一国；若整轮行程无人接纳，复凉之议将永久结束。"

 gdd_liang_restoration.20.t:0 "凉国复祀"
 gdd_liang_restoration.20.d.grant:0 "一座城邑已经辟作凉国的新封土。张承祚在残存宗室与旧臣的拥立下即位，重建社稷，并以获授之地为临时国都。凉国同时重申对武威、靖远和永昌的故土权利，承诺为恩主守御疆土；若三地日后尽归恩主与凉国之手，双方便应履行今日订立的归土盟约。\\n\\n凉国已经成为恩主的卫戍国，并以复立诸侯的身份加入周天下。"
 gdd_liang_restoration.20.d.homeland:0 "武威、靖远和永昌已经一并交给凉国。张承祚在残存宗室与旧臣的拥立下即位，以武威为都，重建宗庙社稷，并承诺世代为恩主守御疆土。由于故土已经完整归还，本次复国无需另设寄居封地。\\n\\n凉国已经成为恩主的卫戍国，并以复立诸侯的身份加入周天下。"
 gdd_liang_restoration.20.a:0 "宗祀得续"

 gdd_liang_restoration.30.t:0 "凉使空还"
 gdd_liang_restoration.30.d:0 "持天子符节遍访列国的凉国使团已经回到王畿。名单中的诸侯或是拒绝割地，或是在使团抵达前便已失去接纳他们的能力，最终无人愿意承担复凉之约。\\n\\n段守节交还符节，张承祚解散流亡朝廷，凉国宗室自此退为编户，不再以故国名义请封。列国并未违背天子之命，因为这趟行程从来不是强制的诏令；然而凉国复祀的最后机会，也已随使团空还而消逝。"
 gdd_liang_restoration.30.a:0 "礼绝于此"

 gdd_liang_restoration.40.t:0 "请归凉土"
 gdd_liang_restoration.40.d:0 "武威、靖远和永昌如今已经全部归于我国与凉国的共同体系，战事也已平息。张承祚遣段守节持当年的盟书前来，请求履行复国之初的约定：三处故土尽归凉国，以武威为都；若那座最初的寄居封地仍在凉国手中，则同时交还我国。\\n\\n我们可以践约，使凉国在故土上继续充当卫戍国；也可以扣留三地，但这将公开毁掉使我国获得天下声望的旧约。"
 gdd_liang_restoration.40.a:0 "践其前约"
 gdd_liang_restoration.40.b:0 "此土不可再分"
 gdd_liang_restoration.40.a.tt:0 "武威、靖远和永昌全部归§Y凉国§!，凉国迁都武威并继续作为我国的§Y卫戍国§!。若最初授予的临时封地仍由凉国拥有，该省将返还我国；凉国后来取得的其他土地不受影响。"
 gdd_liang_restoration.40.b.tt:0 "保留现有故土，移除§Y存亡继绝§!修正，并获得持续§Y20年§!的§R背弃复凉之约§!：§R-0.5外交声誉§!、§R-10%改善关系§!、§R-0.5年度威望§!。凉国增加§R100独立倾向§!，但不会立刻发动战争。"

 gdd_liang_restoration.41.t:0 "归都武威"
 gdd_liang_restoration.41.d:0 "盟书所载的承诺终于全部履行。凉国接收武威、靖远和永昌，张承祚迁都武威，重新在故土上祭告宗庙；仍由凉国持有的原始寄居封地也依约归还恩主。\\n\\n迁归故土没有改变两国之间的卫戍关系。凉国仍奉最初使其复立的诸侯为恩主，只是从此不再寄居异乡。"
 gdd_liang_restoration.41.a:0 "旧约既成"

 gdd_liang_restoration.42.t:0 "前约尽毁"
 gdd_liang_restoration.42.d:0 "恩主拒绝把武威、靖远和永昌交还凉国。当年用来称颂复凉义举的盟书，如今反而成了背约的明证。张承祚没有立即举兵，却下令停止一切恭顺姿态，遣使寻求外援，并准备在力量允许时挣脱卫戍关系。\\n\\n天下也已知道，所谓存亡继绝的声名再不属于背约者。"
 gdd_liang_restoration.42.a:0 "盟书已成空文"

 gdd_liang_restoration.50.t:0 "复凉之约已毁"
 gdd_liang_restoration.50.d.revoked:0 "凉国尚未迁回故土，恩主便主动撤销了它的卫戍国身份。这一举动虽然终止了原有的宗属关系，却不能抹去复国时公开订立的盟约。存亡继绝的声望已经消散，凉国朝廷也把这次毁约视为对其国统的直接威胁。"
 gdd_liang_restoration.50.d.annexed:0 "凉国尚未迁回故土，恩主便主动吞并了这个由自己一手恢复的国家。复凉盟约至此无从履行，存亡继绝的声望也随凉国社稷一并消散。天下记住的将不再是保存亡国宗祀的义举，而是借复立之名行兼并之实。"
 gdd_liang_restoration.50.a:0 "天下自有公论"

 gdd_liang_preserver_of_fallen_state:0 "存亡继绝"
 desc_gdd_liang_preserver_of_fallen_state:0 "这个国家自愿授予凉国复立之地，使亡国宗祀得以延续；这一义举为其赢得了长久的天下声望。"
 gdd_liang_repudiated_restoration_compact:0 "背弃复凉之约"
 desc_gdd_liang_repudiated_restoration_compact:0 "这个国家背弃了恢复凉国时公开订立的归土盟约。列国不再相信它会遵守类似承诺，朝野也因失信而蒙羞。"
"""


def write_if_changed(path: Path, text: str) -> bool:
    previous = path.read_text(encoding="utf-8-sig") if path.exists() else None
    if previous == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_country_prefix() -> bool:
    """Preserve the generated mixed-byte name pools below the owned prefix."""
    marker = b"# Culture-specific Chinese personal names ("
    suffix = b""
    if COUNTRY_FILE.exists():
        current = COUNTRY_FILE.read_bytes()
        position = current.find(marker)
        if position >= 0:
            suffix = current[position:]
    expected = COUNTRY_TEXT.encode("utf-8")
    if suffix:
        expected = expected.rstrip() + b"\n\n" + suffix
    previous = COUNTRY_FILE.read_bytes() if COUNTRY_FILE.exists() else None
    if previous == expected:
        return False
    COUNTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNTRY_FILE.write_bytes(expected)
    return True


def upsert_marker_block(path: Path, block: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if text.count(BEGIN) != text.count(END):
        raise ValueError("unbalanced B76 tag marker")
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END, start) + len(END)
        updated = text[:start] + block + text[finish:]
    else:
        updated = text.rstrip() + "\n\n" + block + "\n"
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def insert_once(path: Path, entry: str, anchor: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(entry)
    if count > 1:
        raise ValueError(f"duplicate managed entry in {path}: {entry.strip()}")
    if count == 1:
        return False
    if text.count(anchor) != 1:
        raise ValueError(f"anchor drift in {path}: {anchor.strip()}")
    updated = text.replace(anchor, anchor + entry, 1)
    path.write_text(updated, encoding="utf-8")
    return True


def patch_seal_policy() -> bool:
    text = SEAL_GENERATOR.read_text(encoding="utf-8")
    updated = text
    if '"LGU": "涼"' not in updated:
        updated = updated.replace('"LNG": "梁",', '"LNG": "梁", "LGU": "涼",', 1)
    if '"LGU": (48,91,112)' not in updated:
        updated = updated.replace('"LNG": (17,45,69),', '"LNG": (17,45,69), "LGU": (48,91,112),', 1)
    updated = updated.replace('PRESERVED = {"CSA", "HZH", "LGU"}', 'PRESERVED = {"CSA", "HZH"}')
    for required in ('"LGU": "涼"', '"LGU": (48,91,112)'):
        if required not in updated:
            raise ValueError(f"failed to register Liang seal policy: {required}")
    if re.search(r'PRESERVED\s*=\s*\{[^}]*"LGU"', updated):
        raise ValueError("LGU must be generated by the shared small-seal generator")
    if updated == text:
        return False
    SEAL_GENERATOR.write_text(updated, encoding="utf-8")
    return True


def patch_culture_policy() -> bool:
    text = CULTURE_GENERATOR.read_text(encoding="utf-8")
    entry = '    "LGU": ("gdd_long", ()),\n'
    if text.count(entry) == 1:
        return False
    if text.count(entry) > 1:
        raise ValueError("duplicate LGU culture policy")
    anchor = '    "LNG": ("gdd_zhongyuan", ()),\n'
    if text.count(anchor) != 1:
        raise ValueError("LNG culture-policy anchor drifted")
    CULTURE_GENERATOR.write_text(text.replace(anchor, anchor + entry, 1), encoding="utf-8")
    return True


def load_encoder():
    spec = importlib.util.spec_from_file_location("gdd_localisation_encoder", ENCODER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load localisation encoder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_seal_generator():
    spec = importlib.util.spec_from_file_location("gdd_zhuxia_seal_generator", SEAL_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Zhuxia seal generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    changed: list[str] = []
    tag_block = f'{BEGIN}\nLGU = "countries/B76_Liang.txt"\n{END}'
    if upsert_marker_block(TAG_FILE, tag_block):
        changed.append(str(TAG_FILE.relative_to(ROOT)))
    if write_country_prefix():
        changed.append(str(COUNTRY_FILE.relative_to(ROOT)))
    if write_if_changed(HISTORY_FILE, HISTORY_TEXT):
        changed.append(str(HISTORY_FILE.relative_to(ROOT)))
    if write_if_changed(LOCALISATION_SOURCE, LOCALISATION_TEXT):
        changed.append(str(LOCALISATION_SOURCE.relative_to(ROOT)))

    encoder_entry = '    "gdd_liang_restoration_readable_utf8.txt": "gdd_liang_restoration_l_english.yml",\n'
    encoder_anchor = '    "gdd_characters_readable_utf8.txt": "gdd_characters_l_english.yml",\n'
    if insert_once(ENCODER, encoder_entry, encoder_anchor):
        changed.append(str(ENCODER.relative_to(ROOT)))
    if patch_seal_policy():
        changed.append(str(SEAL_GENERATOR.relative_to(ROOT)))
    if patch_culture_policy():
        changed.append(str(CULTURE_GENERATOR.relative_to(ROOT)))

    generate_liang_mask(check=False)
    load_seal_generator().run(check=False)
    name_report = apply_country_name_pools(VANILLA, check=False)
    changed.extend(
        f"guangdong_independent_practice/common/countries/{name}"
        for name in name_report["changed_files"]
    )
    encoder = load_encoder()
    if encoder.encode_file(LOCALISATION_SOURCE, LOCALISATION_TARGET):
        changed.append(str(LOCALISATION_TARGET.relative_to(ROOT)))
    encoder.verify_file(LOCALISATION_SOURCE, LOCALISATION_TARGET)
    print(f"applied GDD_B76_LIANG_RESTORATION_TAG; changed={changed}")


if __name__ == "__main__":
    main()
