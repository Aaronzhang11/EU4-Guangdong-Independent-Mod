# B62 边疆与域外政权旗帜：原版纹章化修订

本批次在 B61 的二十八国名单和世界观辨识度基础上，统一改为更接近 EU4 原版及本地工作坊模组“1.37 Celestial empire on which the sun never sets”（ID 1728520255）的旗帜构图。

设计原则：

- 去掉 B61 普遍使用的“浅色卡片边框 + 扁平图标”模板，改用通栏、分割、日芒、织锦、圆章和斜带等传统旗面结构。
- 旗帜采用一个明确的中央徽记；山川、动物、铜鼓、塔木加和地方建筑仍服务于各政权的世界观身份。
- 高丽直接使用用户提供参考图中的凤凰主体，移除相连的绢黄背景后缩入 116×112 的盾徽安全区；不采用近现代太极旗。
- 白马弥药按党项弥药政权处理，中央徽记改为西夏文 `𗴲`（U+17D32，《夏汉字典》序号 0071，“夏”）。生成器读取已经固化的字形蒙版，不依赖运行机器安装西夏文字体。
- 全部成品仍为 128×128、24 位 RGB TGA，并以固定种子加入轻微染料／布纹变化；重复生成的字节必须完全一致。

参考与资产：

- 原版风格参考：EU4 1.37.5 `gfx/flags/`。
- 模组风格参考：工作坊 1728520255 `gfx/flags/`；只学习构图密度和配色关系，不复制国家徽记。
- 高丽原图：`tools/assets/frontier_flags/goryeo_phoenix_reference.png`，用户提供。
- 西夏文字形：`tools/assets/frontier_flags/tangut_xia_u17d32_mask.png`，由 Noto Serif Tangut 生成；字体采用 SIL Open Font License 1.1。

生成与校验：

```bash
python3 tools/generate_frontier_polity_flags.py
python3 tools/generate_frontier_polity_flags.py --check
```

完整色板、旗面结构、纹样理由与来源记录在 `batch_manifest.json`；总览见 `contact_sheet.png`。
