# B26 甘肃—宁夏二十三省细化

本草案以本模组当前正式 `provinces.bmp` 为绝对底图，只在现有甘肃、宁夏八个省份的外轮廓内部重新分区。创意工坊 `1728520255` 的像素轮廓仅作为内部边界的参考种子，不覆盖正式图的省界，也不修改陕西、青海、蒙古等相邻地区。

## 结构

- 宁夏（4）：宁夏、中卫、灵州、松山。
- 陇南（5）：秦州、洮州、阶州、岷州、巩昌。
- 陇中（5）：西宁、兰州、碾伯、河州、狄道。
- 河西（5）：武威、靖远、永昌、张掖、嘉峪。
- 瓜沙（4）：玉门、瓜州、苦峪、沙州。

共二十三个可通行省份。源图把武威、凉州并列拆分，但凉州即武威的历史府州名，因此按照该色块所在的黄河峡谷位置改为靖远。

## 地形

不新增不可通行省份。源图只用于确定可通行省份的轮廓；祁连山、贺兰山等地理影响沿用原版游戏已有的普通地形与战斗机制表达。

## 经济

建议总发展度约一百七十四。兰州设二级贸易中心，张掖设一级贸易中心；宁夏与西宁不再增加贸易中心。商品仅使用原版游戏已有的粮食、牲畜、羊毛、盐、铜、铁、宝石和丝绸，不加入自定义商品或其他额外机制。

## 文件

- 全尺寸草图：`planning/gansu_ningxia_23_formal_base_draft.bmp`
- 裁切 BMP：`planning/gansu_ningxia_23_formal_base_crop.bmp`
- 带标注预览：`docs/map/previews/B26_gansu_ningxia_23_draft.png`
- 生成脚本：`tools/map_pipeline/render_gansu_ningxia_workshop_draft.py`

## 正式实装

方案已写入正式地图。实装继续锁定原甘宁八省的外轮廓，只修改其内部像素；新增省份 ID 为 `5286`—`5300`，`max_provinces` 提高至 `5301`。省份历史、五个区域、贸易节点与公司归属、普通地形、气候、本地化以及城市和单位位置均已同步。

- 正式预览：`docs/map/previews/B26_gansu_ningxia_23_formal.png`
- 实装脚本：`tools/map_pipeline/apply_gansu_ningxia_refinement.py`
- 实装前地图备份：`planning/pre_gansu_ningxia_23_provinces.bmp`
