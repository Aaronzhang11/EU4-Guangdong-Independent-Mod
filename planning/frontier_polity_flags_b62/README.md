# B62 边疆与域外政权旗帜：原版纹章化修订

本批次在 B61 的二十八国名单和世界观辨识度基础上，统一改为更接近 EU4 原版及本地工作坊模组“1.37 Celestial empire on which the sun never sets”（ID 1728520255）的旗帜构图。

设计原则：

- 去掉 B61 普遍使用的“浅色卡片边框 + 扁平图标”模板，改用通栏、分割、日芒、织锦、圆章和斜带等传统旗面结构。
- 旗帜采用一个明确的中央徽记；山川、动物、铜鼓、塔木加和地方建筑仍服务于各政权的世界观身份。
- 高丽直接使用用户提供参考图中的凤凰主体，移除相连的绢黄背景后缩入 116×112 的盾徽安全区；不采用近现代太极旗。
- 白马弥药按党项弥药政权处理，中央徽记改为西夏文 `𗴲`（U+17D32，《夏汉字典》序号 0071，“夏”）。生成器读取已经固化的字形蒙版，不依赖运行机器安装西夏文字体。
- 蒙古大理采用纯白底、黑色传统蒙古文 `ᠳᠠᠯᠢ`（Dali／大理）。字形先经 HarfBuzz 连写塑形，再转为传统竖排并固化为蒙版，避免显示为互不相连的孤立字母。
- 辽恢复 B57 的契丹大字九叠篆官印旗；不再使用 B61/B62 初稿的契丹白鹿图案，且生成结果与原旗逐字节一致。
- 曷懒取消猎鹰图腾，改用金框、森林绿地和竖排满文 `ᡥᡝᠯᠠᠨ`（Helan／曷懒）；框式布局直接参考原版建州女真、海西女真旗，但不复制二者国名或配色。
- 汪古罗斯取消泛用塔木加，改用元代内蒙古景教墓志上的“莲台十字”组合；十字对应汪古部景教传统，莲台则直接来自汉地景教文物的本土化构图。
- 沙州取消泛用绿洲图标，改用敦煌藏经洞九世纪丝绸幡：三角旗首、窄幅画心、苔绿色侧带、压幡板和四条尾旒全部压缩进方形 EU4 盾徽。
- 南诏取消日鸟图腾，改用 899 年《南诏图传》中的阿嵯耶观音形象；保留正面立姿、宝冠、光轮与莲座等可在小盾徽中辨识的核心特征。
- 凉山使用本地自称 `ꆀꃅ`（Nimu），夜郎根据彝语研究中的 `yi-na` 释读使用 `ꑳꆅ`；二者采用由传统古彝文整理而来的凉山规范彝文字形，并按传统经书习惯竖排。夜郎方案属于有文献依据的世界观复原，不宣称是已出土的夜郎官方国号。
- 全部成品仍为 128×128、24 位 RGB TGA；除按裁决保持纯白的蒙古大理和复用旧旗的辽外，其余旗帜以固定种子加入轻微染料／布纹变化。重复生成的字节必须完全一致。

参考与资产：

- 原版风格参考：EU4 1.37.5 `gfx/flags/`。
- 模组风格参考：工作坊 1728520255 `gfx/flags/`；只学习构图密度和配色关系，不复制国家徽记。
- 高丽原图：`tools/assets/frontier_flags/goryeo_phoenix_reference.png`，用户提供。
- 西夏文字形：`tools/assets/frontier_flags/tangut_xia_u17d32_mask.png`，由 Noto Serif Tangut 生成；字体采用 SIL Open Font License 1.1。
- 蒙古大理文字形：`tools/assets/frontier_flags/mongolian_dali_mask.png`，由 Noto Sans Mongolian + HarfBuzz 生成；`ᠳᠠᠯᠢ` 的拼写依据[蒙古国国家语言政策委员会蒙古语大词典](https://www.mongoltoli.mn/dictionary/detail/31365)。
- 曷懒满文字形：`tools/assets/frontier_flags/manchu_helan_mask.png`，由 Noto Sans Mongolian + HarfBuzz 按满文规则连写并转为竖排；固定蒙版避免运行机器缺少满文字体。
- 凉山、夜郎彝文字形：`tools/assets/frontier_flags/yi_liangshan_nimu_mask.png` 与 `yi_yelang_yina_mask.png`，由 Noto Sans Yi 固化；凉山自称参考现代学术文献对 `ꆀꃅ`／`ꆃꎭ` 的区分，夜郎读音参考彝学研究网有关 `yi-na` 的彝语地名研究。
- 汪古十字参考：[元代内蒙古赤峰景教双语墓志](https://commons.wikimedia.org/wiki/File:An_epitaph_of_a_Nestorian_Christian.jpg)与[东亚艺术博物馆十三至十四世纪景教铜十字](https://collections.meaa.org.uk/view-item?i=1664)的“十字立于莲花”构图；本批仅进行矢量化重绘，不复制现代教会徽章。
- 沙州敦煌幡参考：[大英博物馆 `1919,0101,0.120`](https://www.britishmuseum.org/collection/object/A_1919-0101-0-120) 与 [International Dunhuang Programme](https://idp.bl.uk/discover/learning/dunhuang/collection-items/cave-17-the-library-cave/) 对其结构、色带和用途的说明。
- 南诏参考：[899 年《南诏图传》及其阿嵯耶观音图像](https://commons.wikimedia.org/wiki/Category:Nanzhao_Tuzhuan)；本批使用适配 128×128 盾徽的概括性重绘。
- 辽国字形沿用 `tools/map_pipeline/apply_b57_changsha_khitan.py` 中的 B57 固定蒙版，避免两套生成器再次互相覆盖；字形考据见 [BabelStone：Khitan Seals](https://www.babelstone.co.uk/Blog/2012/10/khitan-seals.html)。

生成与校验：

```bash
python3 tools/generate_frontier_polity_flags.py
python3 tools/generate_frontier_polity_flags.py --check
```

完整色板、旗面结构、纹样理由与来源记录在 `batch_manifest.json`；总览见 `contact_sheet.png`。
