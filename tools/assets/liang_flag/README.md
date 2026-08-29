# 凉国小篆印章旗源资产

`liang_small_seal_reference.png` 是用户审定的“涼”字源图，SHA-256 为
`813697811e0964bdb0b59722ec427f67e28d820fb8bd61f00b5d3e298d9de437`。
`tools/generate_liang_small_seal_mask.py` 只执行白底去除、黑白反转、等比缩放与居中，
生成 `liang_small_seal_mask.png` 并写入诸夏共享蒙版库
`tools/assets/zhuxia_seal_masks.json.zlib`。最终的 128×128、24 位 RGB TGA 国旗由统一的
`tools/generate_zhuxia_seal_flags.py` 生成。

旗面写繁体小篆“涼”。生成过程不重画、不补笔、不调用字体，也不使用 AI 改造用户
审定的字形；它只把原始轮廓规范化为适合 EU4 小盾徽的固定蒙版，并与现有诸夏小篆旗
共用纯色旗底、明暗墨色和蒙版生成规则。

生成与验证：

```bash
python3 tools/generate_liang_small_seal_mask.py
python3 tools/generate_liang_small_seal_mask.py --check
python3 tools/generate_zhuxia_seal_flags.py --check
```
