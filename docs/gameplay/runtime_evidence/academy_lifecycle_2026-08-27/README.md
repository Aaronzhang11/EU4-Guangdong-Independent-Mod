# 学宫系统实机回归证据（2026-08-27）

本目录承接 2026-08-26 的生命周期回归。结论只覆盖截图、日志和压缩存档断言实际证明的路径；模组其他系统的既有地图与任务报错不计作学宫回归新增错误。

## Round 16：思想张力三档刷新

- [`01_heavy_three_unprotected_schools.jpg`](round_16_tension_tiers/01_heavy_three_unprotected_schools.jpg)：秦国先后接收儒、墨、道三种异派学宫所在省份后的现场。
- [`02_medium_after_returning_dao.jpg`](round_16_tension_tiers/02_medium_after_returning_dao.jpg)：归还道家学宫后切回秦国，作为两种未保护学派的中档现场。
- [`03_mild_after_returning_mo.jpg`](round_16_tension_tiers/03_mild_after_returning_mo.jpg)：再归还墨家学宫后切回秦国，作为一种未保护学派的轻档现场。
- [`04_mild_country_interface.jpg`](round_16_tension_tiers/04_mild_country_interface.jpg)：轻档状态下的国家界面目视检查；未见控件堆叠、裁切或遮挡。
- [`assertions.txt`](round_16_tension_tiers/assertions.txt)：三个压缩存档中秦国变量和国家修正的精确断言。
- 本轮完整 `error_after.log` 与 `game_after.log` 保留在测试机本地；仓库保存截图、断言和最终静态校验摘要。

结论：三档派别计数和 `mild → medium → heavy` 国家修正均在实机存档中正确刷新，法家主学派协同始终只保留一份；聚焦过滤未发现学宫、临时夹具或思想张力修改器新增错误。截图只证明本轮实际打开的界面没有重叠，未把四项数值的原版国家修正悬停栏留作独立截图；四项具体数值仍由脚本定义与静态校验保证。

## 截止签收（12:00）

- EU4 已先在战役菜单返回主菜单，再使用主菜单“退出”关闭；最终进程检查为空。
- 仅供学宫回归使用的 `events/zzz_zhx_academy_runtime_test_events.txt` 已删除。
- 正式调试目录中的天下大辩调试事件、决议和触发器不是学宫临时夹具，予以保留。
- 生产目录复查后不再存在 `zhxrt2`、`zzz_zhx_academy_runtime_test`、`zhxtest`、`fatest` 或 `motest` 注入。
- 删除夹具后已重跑完整投影、学宫、生命周期、礼教、开局学派、本地化及 `git diff --check` 校验；结果全部通过。
- 自动化 `automation`（“学宫边界回归至中午”）已在签收后暂停。
- 本轮未提交、未推送，也未处理无关的地图 definition 4946 基线差异。
