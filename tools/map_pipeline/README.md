# 地图配套资产与校验工具

本目录为手绘 EU4 地图生成配套文本资产并执行静态检查。B01 广东的正式几何
不是脚本生成结果，而是用户直接维护的：

`guangdong_independent_practice/map/provinces.bmp`

这张 BMP 是唯一 canonical 地图。`build_b01_mod.py` 会先审计它，再生成
`definition.csv`、`default.map`、点位、区域、气候、地形与贸易文件；它绝不
生成、复制或覆盖 `provinces.bmp` 的像素。

## 环境

- Python 3.11+
- `numpy`
- `Pillow`
- 本机 EU4 版本须为 1.37.5；脚本会校验省份图、定义表、默认地图和特殊邻接表的
  固定 SHA-256

安装依赖：

```sh
python3 -m pip install -r tools/map_pipeline/requirements.txt
```

## 省份 ID 与 RGB

`allocate_registry.py` 以原版最高省份 ID `4941` 为基线，按 `draw_batch`
顺序冻结总表中的新省 ID 与唯一 RGB。当前 B01 占用连续区间 `4942–4949`：
佛山、东莞、梅州、高州、香港、罗定、南雄和陆丰。正式地图使用
`max_provinces = 4950`，不会把尚未实现的预留省份作为空省暴露给游戏。

首次写入：

```sh
python3 tools/map_pipeline/allocate_registry.py \
  --vanilla-root "/path/to/Europa Universalis IV" \
  --write
```

日常只校验，不重写：

```sh
python3 tools/map_pipeline/allocate_registry.py \
  --vanilla-root "/path/to/Europa Universalis IV"
```

## 手绘地图约束

当前正式 BMP 必须保持：

- `5632 × 2048`；
- RGB、24 位；
- 经典 40 字节 DIB 头，像素偏移 `54`；
- 无压缩 `BI_RGB`；
- 每个像素只能使用原版 `definition.csv` 或注册表中已经冻结的精确 RGB；
- 不使用抗锯齿、透明度、颜色混合或调色板模式。

本轮审定图相对 EU4 1.37.5 原版有 `1627` 个变化像素。八省正式像素数依次为：

```text
4942 佛山 201
4943 东莞 71
4944 梅州 166
4945 高州 398
4946 香港 28
4947 罗定 293
4948 南雄 265
4949 陆丰 155
```

这些数值、连通块和邻接写在 `b01_guangdong_manual.json` 中，作为对当前手绘
版本的审定断言。以后再次手绘省界时，校验失败是预期的安全提示；应当先审图，
再有意识地更新配置、点位与相关规则，不能通过运行生成器来“恢复”像素。

## 旧 AI 预览

`b01_guangdong.json`、`build_b01_preview.py` 和下列文件记录早期五省 AI 几何：

- `docs/map/previews/B01_guangdong_review.png`
- `docs/map/previews/B01_guangdong_pixels.png`
- `docs/map/previews/B01_guangdong_report.json`

它们现在只用于历史追溯和方案对照，不再驱动正式地图。运行旧预览脚本只会更新
预览或 `build/map/` 下的 staging 候选，不得把候选图复制回正式 Mod。

如需重现旧方案：

```sh
python3 tools/map_pipeline/build_b01_preview.py \
  --vanilla-root "/path/to/Europa Universalis IV"
```

旧脚本若输出完整 BMP，也只能写入 `build/map/`：

```sh
python3 tools/map_pipeline/build_b01_preview.py \
  --vanilla-root "/path/to/Europa Universalis IV" \
  --candidate-bmp build/map/B01/provinces.bmp
```

该候选 BMP 不是当前可玩地图，不能替代用户手绘的 canonical BMP。

## B01 正式配套资产

`build_b01_mod.py` 对 canonical BMP 执行只读几何审计，然后从锁定的 EU4
1.37.5 基线生成配套文件。它会检查经典 BMP 头、变化像素、八省颜色与像素数，
并在报告中确认正式图哈希保持不变。

```sh
python3 tools/map_pipeline/build_b01_mod.py \
  --vanilla-root "/path/to/Europa Universalis IV"
```

正式静态校验：

```sh
python3 tools/map_pipeline/validate_b01_mod.py \
  --vanilla-root "/path/to/Europa Universalis IV"

python3 tools/encode_eu4_chinese_localisation.py --check
```

校验覆盖 BMP 格式、定义颜色、变化范围、像素数、连通块、邻接、港口点、Area、
Region、洲、气候、地形、贸易节点、贸易公司、省份历史、发展度与本地化。
当前八省、`max_provinces = 4950`、罗定/南雄/陆丰的历史，以及南雄 1 级贸易
中心、陆丰 15 世纪堡垒均已通过静态校验。

发展度按母省组守恒；唯一有意例外是惠州—东莞—香港—陆丰组净增一点人力。

静态通过不等于引擎实机通过。正式交付前仍需用全新 1444 年存档检查地图日志、
寻路、港口和堡垒模型，以及保存/读取。
