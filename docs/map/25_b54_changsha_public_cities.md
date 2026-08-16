# B54 长沙扩地与三公邑

## 开局调整

- 益阳（4997）、安化（5322）改归长沙国（`CSA`），长沙由 3 省 27
  发展变为 5 省 39 发展。
- 常德（672）独立为“常”公邑（`CDE`）。
- 九江（4979）独立为“九”公邑（`JJG`）。
- 汉阳（4981）独立为“汉”公邑（`HYA`）。

三座公邑均为单省、独立的寡头共和国，不是长沙、楚或武陵的附庸；原国家不保留
这些省份的开局核心。国名和形容词都使用一个汉字，旗帜使用统一的小篆字形。

## 不变项

本批不修改省份边界、发展度、区域、贸易节点、贸易路线或贸易中心。常德、九江、
汉阳分别保留 15、20、9 发展度。目标审计同时补全了常德（672）原先遗漏的
`mild_monsoon` 气候归属；这不改变区域或贸易结构。

## 重放与验证

```bash
python3 tools/map_pipeline/apply_b54_changsha_public_cities.py
python3 tools/map_pipeline/apply_b54_changsha_public_cities.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
python3 tools/generate_zhuxia_seal_flags.py --check
```
