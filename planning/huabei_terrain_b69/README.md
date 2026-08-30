# B69 华北地形纠正

部分新增华北省份没有明确的 `terrain_override`，并继承了 `terrain.bmp`
中的旧沙漠像素。本批次同时修正脚本地形与图形地形，但不修改省界：

- 农田：北京—河北平原、鲁西平原和主要山东农业盆地。
- 丘陵：燕山山麓、关隘、胶东丘陵、泰山及沂蒙山区。

图形地形使用本项目调色板中的农田索引 `11`、丘陵索引 `1`；海洋、内海
和海岸线过渡像素（`15/17/35`）保持原状。修改前地形位图保存在
`pre_b69_terrain.bmp`。

重放命令：

```bash
python3 tools/map_pipeline/apply_b69_huabei_terrain_normalization.py
```
