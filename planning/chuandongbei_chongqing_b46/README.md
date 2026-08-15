# B46 川东北—重庆 GeoJSON 第二轮细化

状态：已正式实装并通过静态验证。

## 推荐版本：GeoJSON v2

在比较天朝日不落、岁在甲子和风云世纪两千年的已安装地图后，推荐将初版几何分割升级为县级 GeoJSON 引导。参考模组只用于判断密度、边界语言与山河关系，不复制其省份像素。

- 当前川北＋巴东 10 省细化为 22 省，新增 12 省。
- 新增省份：昭化、蓬州、遂州、巴州、渠州、昌州、江津、南川、彭水、忠州、开州、石砫。
- 区域总发展度仍为 106；巴在本区域由初版 46 降为 42。
- 巴州改由巴中—达州父区分出，不再从阆中作几何硬切。
- 县界使用阿里云 DataV 四川、重庆县级 GeoJSON；预览叠加项目 `heightmap.bmp` 与 `rivers.bmp`。
- 22 个省、5 个 Area、6 个国家在预览几何中均为四向连通。

### GeoJSON v2 Area

| Area | 省份 | 发展度 |
| --- | --- | ---: |
| 剑阆 | 绵州、剑州、昭化、阆中、遂州 | 31 |
| 巴渠 | 蓬州、巴州、顺庆、达州、渠州 | 18 |
| 巴渝 | 合州、昌州、重庆、江津 | 26 |
| 涪陵 | 涪州、南川、彭水、忠州、石砫 | 17 |
| 峡江 | 万州、开州、夔州 | 14 |

### GeoJSON v2 国家与文化

| 国家 | 省份 | 本区发展度 | 文化政策 |
| --- | --- | ---: | --- |
| 蜀 | 绵州、遂州 | 16 | `gdd_shu` |
| 苴 | 剑州、昭化 | 8 | `gdd_shu` |
| 巴 | 阆中、蓬州、顺庆、合州、昌州、重庆、江津 | 42 | `gdd_shu` |
| 宕渠（新） | 巴州、达州、渠州、万州、开州 | 17 | 主文化 `gdd_shu`，接受 `gdd_diqiang` |
| 枳（新） | 涪州、南川、彭水、忠州、石砫 | 17 | 主文化 `miao`，接受 `gdd_shu` |
| 巴氐 | 夔州 | 6 | `gdd_diqiang` |

正式预览为 `b46_geojson_country_preview.png` 与 `b46_geojson_area_preview.png`。
`b46_reviewed_provinces.bmp` 是冻结的审图几何，正式脚本只复制十个母省范围内的
像素；`pre_b46_provinces.bmp` 保存实施前基线，事务清单写入 `batch_manifest.json`。

## 正式实现

- 新增省份 ID 固定为 `5329–5340`，`max_provinces = 5341`。
- `apply_b46_chuandongbei_chongqing_refinement.py` 同步地图、定义、历史、Area、Region、
  位置、洲、气候、地形、成都贸易节点、成都贸易公司、国家、旗帜、文化 CSV 与本地化。
- 旧 B18 四川生成器在 B46 清单存在时不再重建旧版地图，而是转交 B46 终端事务。
- 宕渠使用 `DQU`，枳使用 `ZHI`；两个 tag 已确认不与原版及当前依赖冲突。
- 审计结果：22/22 省、5/5 Area、6/6 本区国家均四向连通；区域发展度为 106；
  相对 B46 基线的可编辑范围外变化为 0 像素。

```sh
python3 tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py
python3 tools/map_pipeline/apply_b46_chuandongbei_chongqing_refinement.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

`render_b46_geojson_proposal.py` 仅用于重新制作参考预览；正式复现不联网，也不会重新
投影 GeoJSON。旧的 20 省 v1 图片和渲染脚本保留作设计过程对照，不再是实现依据。
