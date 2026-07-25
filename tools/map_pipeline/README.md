# 地图生成与校验工具

本目录把手工地图设计转成可重复生成、可静态检查的像素结果。`B01 广东`已经
同时提供审图流水线和正式模组资产生成器。所有脚本只读取 Steam 安装目录；
正式输出写入仓库内的 `guangdong_independent_practice/`。

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
顺序冻结总表中四十一个新省的 ID `4942–4982` 及唯一 RGB。B01 因而先占用
`4942–4946`，可独立做成连续 ID 的首批可玩切片，不会留下未定义的低位 ID。

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

## B01 广东审图

`b01_guangdong.json` 保存四个母省分区、五个新省的像素几何、城市/港口保留
锚点、面积目标与沿海属性。惠州、东莞和香港采用一次性三向分区，不依赖绘制
顺序。`build_b01_preview.py` 在内存中拆分母省并生成：

- `docs/map/previews/B01_guangdong_review.png`
- `docs/map/previews/B01_guangdong_pixels.png`
- `docs/map/previews/B01_guangdong_report.json`

运行：

```sh
python3 tools/map_pipeline/build_b01_preview.py \
  --vanilla-root "/path/to/Europa Universalis IV"
```

脚本会拒绝以下结果：基线文件不符、尺寸或位深错误、ID/RGB 冲突、四个母省外
出现变化、新省不连通、母省主陆块被切断、像素不守恒、保留锚点吸附过远、沿海
属性错误、最终邻接不符、公共边过短，或面积偏差超过容差。报告状态
`PREVIEW_GEOMETRY_PASS` 只代表几何预览通过。

如需为后续生产流程生成完整候选 BMP，只能写入仓库 `build/map/` 下的一次性
staging 路径；脚本会拒绝其他路径，避免覆盖原版或正式 Mod 资产：

```sh
python3 tools/map_pipeline/build_b01_preview.py \
  --vanilla-root "/path/to/Europa Universalis IV" \
  --candidate-bmp build/map/B01/provinces.bmp
```

候选 BMP 仍不是可玩地图；必须连同 `definition.csv`、`default.map`、区域、气候、
位置、贸易节点、贸易公司、历史和本地化等文件一起通过生产校验后，才能部署。

## B01 正式模组资产

`build_b01_mod.py` 从已锁定的 EU4 1.37.5 基线重新生成几何，并把完整覆盖文件
写入模组。当前只开放已经实现的 `4942–4946`，因此 `max_provinces = 4947`；
登记表中为后续批次预留的 ID 不会作为空省份进入游戏。

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

校验覆盖 BMP 尺寸与位深、定义颜色、像素范围和连通性、邻接、端口点、Area、
Region、洲、气候、地形、贸易节点、贸易公司、省份历史、发展度守恒和本地化。
