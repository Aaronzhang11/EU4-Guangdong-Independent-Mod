# B57 华东地形地标批次

- 目的：按用户提供的 6400×2560 `provinces.bmp` 轮廓，在当前地图实装大别山、泰山和微山湖，并让周边省界顺着山脊、湖岸收边。
- 正式脚本：`tools/map_pipeline/apply_b57_east_china_landmarks.py`
- 地图备份：`planning/east_china_landmarks_b57/pre_b57_provinces.bmp`
- 审核补丁：`b57_before_patch.png` / `b57_after_patch.png`，原点 `(4550,775)`，大小 `135×150`；仅 alpha=255 的像素可编辑。
- 正式预览：`b57_applied_preview.png`

## ID 与 RGB

| ID | 名称 | RGB | 语义 |
|---:|---|---|---|
| 4010 | 微山湖 | `100,14,110` | 复用原版零像素 RNW 湖泊预留 ID；保留在 `default.map/lakes` |
| 5354 | 大别山 | `87,9,10` | 新增不可通行山地 |
| 5355 | 泰山 | `27,57,174` | 新增不可通行山地 |

`max_provinces` 为排他上界，提升到 5356。

## 事务范围

- `provinces.bmp`：变化 745 像素；三处地形 654 像素，周边省界收边 91 像素；审核范围外变化 0。
- `definition.csv`：重命名 4010，新增 5354、5355。
- `default.map`：更新上界；4010 已在湖泊列表内。
- `climate.txt`：5354、5355 加入 `impassable`。
- `continent.txt`：5354、5355 加入 `asia`。
- `terrain.txt`：5354、5355 只加入 `mountain/terrain_override`。
- 本地化：可读源与 `localisation/replace` 中的 EU4dll 编码目标成对生成。
- 历史、positions、area、region、贸易节点、贸易公司：三者均非可玩陆地省份，故不加入。

## 有意的离散组件

参考轮廓本身由多个断续地形段组成；这是有意保留的山体／湖面外形，不是可玩省份飞地：

- 微山湖：2 个四向组件，30 / 14 像素。
- 大别山：4 个四向组件，345 / 79 / 4 / 3 像素。
- 泰山：3 个四向组件，167 / 9 / 3 像素。

所有被三处地形切到的正常陆地省份必须保持其原有或更少的四向组件数。
