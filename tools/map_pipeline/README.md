# 地图配套资产与校验工具

本目录为手绘 EU4 地图生成配套文本资产并执行静态检查。B01 广东的正式几何
不是脚本生成结果，而是用户直接维护的：

`guangdong_independent_practice/map/provinces.bmp`

这张 BMP 是唯一 canonical 地图。`build_b01_mod.py` 会先审计它，再生成
`definition.csv`、`default.map`、点位、区域、气候、地形与贸易文件；它绝不
生成、复制或覆盖 `provinces.bmp` 的像素。

浙江昌国（5004）仅包含最外海两组舟山岛屿，近岸两组大岛归宁波；生成器会在
`adjacencies.csv` 中加入宁波（2149）至昌国、经东海海区 1373 的海峡连接。

跨批次的完整实施顺序、联动文件、排错方法和实机验收标准见
[`docs/map/04_manual_map_implementation_workflow.md`](../../docs/map/04_manual_map_implementation_workflow.md)；
新批次可复制
[`docs/map/templates/province_split_batch_template.md`](../../docs/map/templates/province_split_batch_template.md)。

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
顺序冻结总表中的新省 ID 与唯一 RGB。当前 B01 占用 `4942–4949`；优先准备的
浙江、福建、广西与台湾十二省占用 `4950–4961`；江西 B07 使用
`4979`、`4980` 与 `4992–4995`；湖南 B07 使用 `4982`、`4983` 与
`4996–5001`；浙江扩展六省使用 `5002–5007`。正式地图使用
`max_provinces = 5017`。东南批次、江西十省、湖南十二省、浙江十四省和湖北
十五省均已
写入正式 `provinces.bmp` 并纳入静态校验。

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

## B01 正式配套资产与 P02 待手绘资产

`build_b01_mod.py` 对 canonical BMP 执行只读几何审计，然后从锁定的 EU4
1.37.5 基线生成 B01 与 P02 配套文件。它会检查经典 BMP 头、广东八省颜色与
像素数，并在报告中确认正式图哈希保持不变；不会要求尚未手绘的十二种颜色出现。

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
当前广东、东南、浙江、赣湘 B07、湖北 B10 及江苏 B11 的地图资产、
`max_provinces = 5026`、双字节中文本地化、各省发展度与贸易中心均纳入静态校验。
当前登记的东南各省均已有正式几何；后续批次仍按同一审图门槛扩展。

发展度按母省组守恒；唯一有意例外是惠州—东莞—香港—陆丰组净增一点人力。

静态通过不等于引擎实机通过。正式交付前仍需用全新 1444 年存档检查地图日志、
寻路、港口和堡垒模型，以及保存/读取。

## B44 世界观地名收口

国家版图（B43）和文化（B41）重放完成后，最后运行 B44，把帝号、近现代名称及
省份语义错配统一到无帝制世界观。该事务不改 `provinces.bmp`，并会核验正式图
SHA-256、31 个 definition/history/localisation 映射以及江宁—六合的政治与发展度
交换：

```sh
python3 tools/map_pipeline/apply_b44_worldview_toponyms.py
python3 tools/map_pipeline/apply_b44_worldview_toponyms.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

权威映射见 `planning/worldview_toponyms_b44/toponym_manifest.csv`。旧批次生成器仍保留
依赖模组的精确 history 文件名，以保证 EU4 虚拟文件系统遮蔽关系不会因重放改名
而失效。

## B45 湖南—江西平衡细化

B45 按审定效果图把湖南扩为 23 个省、江西扩为 16 个省，共新增 17 个省份，
同时把两地重组为 10 个陆地连续 Area。长沙国只保留长沙、湘潭、浏阳三省，
总发展度固定为 27；衡州—郴州—永州另立衡国，防止拆省后长沙无条件坐大。

```sh
python3 tools/map_pipeline/apply_b45_hunan_jiangxi_refinement.py
python3 tools/map_pipeline/apply_b45_hunan_jiangxi_refinement.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

几何参考、冻结的 ID/RGB、国家文化政策和验证结果见
`planning/hunan_jiangxi_refinement_b45/batch_manifest.json`。B45 是 B41/B43/B44
之后的终端地图事务；若重放旧地图生成器，最后必须再次运行 B45。

## B46 川东北—重庆 GeoJSON 二次细化

B46 把川北与巴东现有 10 省细化为 22 省，新增 `5329–5340`，并重组为剑阆、
巴渠、巴渝、涪陵、峡江五个连续 Area。区域发展度保持 106，不因拆省膨胀；
新增宕渠（`DQU`）与枳（`ZHI`），巴国在本区控制 42 发展度。

```sh
python3 tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py
python3 tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

脚本只在十个冻结母省内复制审定像素，正式复现不联网。几何源、GeoJSON 设计记录、
预览和静态事务清单位于 `planning/chuandongbei_chongqing_b46/`。B46 已取代旧 B18
生成器在该区域的终端权威；B18 在检测到 B46 清单后只转交 B46，不再写回旧图。
