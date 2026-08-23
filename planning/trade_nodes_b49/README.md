# B49 中华八节点贸易网络

B49 将原先过大的北京、广州、成都、杭州、西安五个中国核心贸易节点重构为八个
春秋化节点，并把吴越设为唯一的中国内部终点节点。特许贸易区同步重构为相同的
八区边界；区域、国家、文化、省份发展度与 B48 贸易中心等级不改变。

## 正式节点

| 内部键 | 显示名 | 地理范围 | 角色 |
|---|---|---|---|
| `hangzhou` | 吴越 | 江浙、皖江、江淮 | 唯一终点贸易黑洞 |
| `canton` | 百越 | 闽粤桂、海南、台湾 | 南海入口 |
| `huguang` | 荆楚 | 湖北、湖南、江西 | 长江中游汇流 |
| `chengdu` | 巴蜀 | 四川、重庆 | 上游节点 |
| `yungui` | 夜郎 | 云南、贵州 | 西南入口 |
| `xian` | 秦陇 | 陕西、甘肃、宁夏、河西东段 | 西北汇流 |
| `zhongyuan` | 河济 | 河南、山东、冀南 | 黄淮汇流 |
| `beijing` | 幽燕 | 河北、山西、辽西及赵地 | 北方汇流 |

玉门—沙州、蒙古、藏地、满洲仍属于八节点以外的既有边疆节点；安南按用户裁决
归入百越。`south_hebei_area` 显示为“赵地”，其完整六省统一归入幽燕；这里按
Area 语义处理，不按赵国开局领土处理。贸易流全局必须保持无环。

## 特许贸易区

八个核心节点的陆地成员必须逐省等于对应的吴越、百越、荆楚、巴蜀、夜郎、
秦陇、河济、幽燕特许贸易区。安南九省是百越的额外成员；玉门、吉林、拉萨三个
边疆节点则分别使用各自既有的特许贸易区。节点定位用的海湾、湖泊和海面锚点不
进入特许贸易区。B49 校验会拒绝漏区、重复归属或跨节点串区。

特许贸易区地图模式读取 `trade_company_*` 本体键，实际贸易公司名称读取其
`names` 中的 `GDD_TRADE_COMPANY_*` 键；两套键都必须写入 `localisation/replace`
并通过编码回环，否则地图模式会回退到原版英文 Charter 名称。

## 重放与校验

```sh
python3 tools/map_pipeline/apply_b49_eight_node_trade_network.py
python3 tools/map_pipeline/apply_b49_eight_node_trade_network.py --check
python3 tools/encode_eu4_chinese_localisation.py --check
```

任何会重写旧贸易节点归属的早期地图生成器运行后，最后必须依次重跑 B48 与 B49。
正式备份为 `pre_b49_00_tradenodes.txt` 与
`pre_b49_user_fix_00_trade_companies.txt`，权威面积映射、边疆迁移、八区特许贸易
归属和验收统计记录在 `batch_manifest.json`。
