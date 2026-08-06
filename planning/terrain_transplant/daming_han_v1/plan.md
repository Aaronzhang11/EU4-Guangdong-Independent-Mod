# B38 大明日不落东亚—东南亚 terrain.bmp 视觉移植

- 目的：将创意工坊 `1728520255` 的东亚与东南亚陆地纹理移植到当前模组，增强山脉、丘陵、森林与农田的视觉层次，同时消除原汉地矩形边缘。
- 正式目标：`guangdong_independent_practice/map/terrain.bmp`。
- 源图：`/Users/xinanyapiao/Library/Application Support/Steam/steamapps/workshop/content/236850/1728520255/map/terrain.bmp`。
- 配准：源图相对当前地图 `X + 438`、`Y + 9`；直接裁切，不缩放、不插值。
- 核心区域：蒙古、满洲、朝鲜、日本、青藏、华北、华南、西南、缅甸、印度支那、马来亚、印度尼西亚与摩鹿加等游戏区域。
- 过渡方式：由核心区域向中亚、西伯利亚、印度和海岛外围生成约 `120` 像素的低频不规则渐变带，不使用矩形硬边。
- 可编辑像素：双方均为陆地纹理、且当前省份不是海洋或湖泊的像素；当前水域、海岸线和源图水域全部锁定。
- 游戏性保护：已有 `terrain_override` 的省份可采用完整源纹理；其余省份只替换为同一游戏地形类别的源索引，因此逐像素保证玩法地形类别不变。
- 不修改：`terrain.txt`、`heightmap.bmp`、`rivers.bmp`、`provinces.bmp`、省份历史、区域、贸易和本地化。
- 一次性备份：`pre_b38/map/terrain.bmp`。
- 青藏连续化：仅在 `tibet_region` 内对现有山地族索引进行半径 `6 px` 的闭合，填补内部小断裂；锁定水域与海岸，并验证无未覆盖省份的主地形类别变化。
- 青藏连续化前备份：`pre_b40_white_tibet/map/terrain.bmp`。
- 正式预览：`daming_han_terrain_formal_preview.png`。
- 实装脚本：`tools/map_pipeline/apply_b38_daming_han_terrain_visual.py`，必须可重复运行并保持哈希稳定。
