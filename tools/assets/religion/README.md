# 礼教与景教宗教美术素材

`zhx_lijiao_religion_icon_source.png` 是 2026-08-22 使用 Codex 内置 ImageGen 生成的原创源图；
`zhx_lijiao_religion_icon_preview.png` 展示替换后的 `64×64`、`32×32` 宗教帧，
以及东正教五帧加景教五帧的牧首圣像条。
同一生成器还会生成三张 `42×42` 按钮覆盖层：
`zhx_lijiao_school_button.dds` 保留原生请士按钮的金色外圈并以礼鼎覆盖伊斯兰月牙；
`zhx_no_doctrine_school_button.dds` 使用不带学派徽记的中性礼制圆环，供透明的
“未立国论”生命周期哨兵使用；`zhx_non_lijiao_school_button_blocker.dds` 则还原按钮
所在位置的宗教页底板和金色分隔线，并把横幅左端卷轴头水平镜像为对称右端。前两者允许鼠标穿透，
不会遮断礼教原生按钮的点击区域；第三者只在非礼教东方国家出现并截获误生成的按钮。

生成提示词：

> Use case: logo-brand. Asset type: Europa Universalis IV religion emblem, designed to remain legible at 64x64 and 32x32 pixels. Primary request: an original emblem for an ancient Chinese Ritual Teaching religion, represented by one frontal bronze ritual ding vessel. Subject: a symmetrical three-legged bronze ding with two upright loop handles, compact proportions, unmistakable silhouette, restrained taotie-inspired engraved bands but no tiny clutter. Style/medium: polished hand-painted grand-strategy game UI icon, matching the visual weight and dimensionality of classic metallic religion emblems without copying any existing game asset. Composition/framing: single centered object, full vessel visible, generous padding, orthographic frontal view. Lighting/mood: subtle top-left highlight, dark bronze shadows, solemn and dignified. Color palette: aged bronze, muted gold edges, small verdigris accents. Scene/backdrop: perfectly flat solid #ff00ff chroma-key background for removal. Constraints: crisp closed silhouette, high contrast at thumbnail size, no cast shadow, no floor, no reflection, no gradient or texture in the background, do not use #ff00ff in the object. Avoid: text, Chinese characters, yin-yang, people, flags, buildings, extra objects, watermark.

运行时覆盖四张原版宗教图标表，只替换 `confucianism` 使用的第 9 帧，并另行生成
礼教、“未立国论”与非礼教空白遮挡层；生成器为
`tools/generate_lijiao_religion_icon.py`。

## 景教原创素材

2026-08-23 使用 Codex 内置 ImageGen 生成下列原创源图：

- `zhx_nestorian_religion_icon_source.png`：十字架立于莲台的景教宗教徽章；
- `zhx_nestorian_nestorius_source.png`：圣聂斯脱里；
- `zhx_nestorian_yelv_source.png`：虚构的契丹籍都主教耶律明信；
- `zhx_nestorian_jinghui_source.png`：虚构的诸夏籍女性译经士景惠；
- `zhx_nestorian_thomas_source.png`：圣多马宗徒；
- `zhx_nestorian_anthony_source.png`：埃及的圣安东尼。

宗教徽章以透明背景、缩略图可读性和东叙利亚十字架为约束；五张圣像统一要求
正面半身、旧绘圣像质感、暖色羊皮纸背景、深褐金边，并保证缩至 `58×58` 时仍能
辨认面容。其中耶律明信与景惠为本模组世界线原创人物，不声称有现实历史原型。

《战争前夜》（Ante Bellum）只作为“景教复用牧首权威与圣像机制”的设计参考。
本机版本未提供可转授权声明，因此本仓库没有复制或截取其景教 DDS 美术；宗教徽章
与五张圣像全部为上述原创图像。生成器把景教徽章写入原版未使用的第 7 帧，同时
保留礼教第 9 帧，并把五张原创圣像追加到原版五张东正教圣像之后。
