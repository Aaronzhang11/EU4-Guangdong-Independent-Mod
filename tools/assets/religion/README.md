# 礼教宗教徽章素材

`zhx_lijiao_religion_icon_source.png` 是 2026-08-22 使用 Codex 内置 ImageGen 生成的原创源图；
`zhx_lijiao_religion_icon_preview.png` 展示替换后的 `64×64` 与 `32×32` 第 9 帧。
同一生成器还会生成两张 `42×42` 按钮覆盖层：
`zhx_lijiao_school_button.dds` 保留原生请士按钮的金色外圈并以礼鼎覆盖伊斯兰月牙；
`zhx_no_doctrine_school_button.dds` 使用不带学派徽记的中性礼制圆环，供透明的
“未立国论”生命周期哨兵使用。两者都允许鼠标穿透，不会改变伊斯兰国家的按钮，也
不会遮断原生按钮的点击区域。

生成提示词：

> Use case: logo-brand. Asset type: Europa Universalis IV religion emblem, designed to remain legible at 64x64 and 32x32 pixels. Primary request: an original emblem for an ancient Chinese Ritual Teaching religion, represented by one frontal bronze ritual ding vessel. Subject: a symmetrical three-legged bronze ding with two upright loop handles, compact proportions, unmistakable silhouette, restrained taotie-inspired engraved bands but no tiny clutter. Style/medium: polished hand-painted grand-strategy game UI icon, matching the visual weight and dimensionality of classic metallic religion emblems without copying any existing game asset. Composition/framing: single centered object, full vessel visible, generous padding, orthographic frontal view. Lighting/mood: subtle top-left highlight, dark bronze shadows, solemn and dignified. Color palette: aged bronze, muted gold edges, small verdigris accents. Scene/backdrop: perfectly flat solid #ff00ff chroma-key background for removal. Constraints: crisp closed silhouette, high contrast at thumbnail size, no cast shadow, no floor, no reflection, no gradient or texture in the background, do not use #ff00ff in the object. Avoid: text, Chinese characters, yin-yang, people, flags, buildings, extra objects, watermark.

运行时覆盖四张原版宗教图标表，只替换 `confucianism` 使用的第 9 帧，并另行生成
礼教与“未立国论”按钮覆盖层；生成器为 `tools/generate_lijiao_religion_icon.py`。
