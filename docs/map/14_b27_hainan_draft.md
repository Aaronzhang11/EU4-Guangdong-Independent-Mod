# B27 海南五省与五指山草案

本草案以当前正式 `provinces.bmp` 中原版海南省（666）与崖州省（2160）的联合海岸线为硬边界，只在这两个旧省内部重新分割，不修改雷州半岛、海峡海域或其他相邻像素。

## 五个可通行省份

- 琼州：北岸府城与琼州海峡门户，粮食，七发展度。
- 儋州：西北海岸盐场与港湾，盐，六发展度。
- 昌化：西南沿海与黎峒边缘，热带木材，五发展度。
- 崖州：海南南端港口与南海航路，鱼类，六发展度。
- 万州：东岸季风港与热带作物，香料，六发展度。

五省合计三十发展度，单独组成一个两字名称的“海南”区域。全岛不设置贸易中心，商品全部来自原版游戏。

## 五指山

岛屿中央划出一块约一百零九像素的五指山不可通行省份，零发展度，不接触海岸。五个沿海省份围绕山地形成环状通路，仍可沿海岸依次通行，但不能直接横穿海南腹地。

## 文件

- 全尺寸草图：`planning/hainan_5_wuzhishan_formal_base_draft.bmp`
- 海南裁切 BMP：`planning/hainan_5_wuzhishan_crop.bmp`
- 标注预览：`docs/map/previews/B27_hainan_5_wuzhishan_draft.png`
- 生成脚本：`tools/map_pipeline/render_hainan_5_wuzhishan_draft.py`

## 正式实装

方案已写入正式地图。原版海南省（666）保留为琼州，原版崖州省（2160）保留为崖州；新增 `5301` 儋州、`5302` 昌化、`5303` 万州与 `5304` 五指山，`max_provinces` 提高至 `5305`。五个可通行省份统一归入“海南”区域，总发展度三十，贸易中心为零。五指山已加入不可通行列表，不属于区域、贸易节点或贸易公司。

- 正式预览：`docs/map/previews/B27_hainan_5_wuzhishan_formal.png`
- 实装脚本：`tools/map_pipeline/apply_hainan_5_wuzhishan_refinement.py`
- 实装前地图备份：`planning/pre_hainan_5_wuzhishan_provinces.bmp`
