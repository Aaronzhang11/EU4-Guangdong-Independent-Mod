# 学宫生命周期实机回归证据（2026-08-26）

本目录保存学宫生命周期前十五轮实机回归的截图与存档断言。结论只覆盖证据中实际走到的路径；完整 `error.log` 仍含模组其他系统的既有报错，因此测试时只把与学宫、临时夹具和本轮修改器直接相关的新增记录作为判据。完整原始日志保留在测试机本地，不纳入 Git；下表中的日志文件名和行号是当轮记录，截图与 `assertions.txt` 才是仓库内的长期证据。

## 轮次总览

| 轮次 | 结论 | 证据与边界 |
| --- | --- | --- |
| `round_01` | 发现并修复真实产品问题 | 本地 `error_after.log` 第 30–31 行报告两个 `local_trade_power` 为未知修改器，位置均在 `zhx_academy_modifiers.txt`。后续已换为 EU4 1.37.5 可识别的 `province_trade_power_modifier`；第二轮之后未再出现这两条报错。第一轮没有形成学宫生命周期的有效截图验收。 |
| `round_02` | 无效测试轮 | 临时夹具 `zhxrt.1`–`.5` 缺少标题、描述、选项和图片；本地 `error_after.log` 第 574–593 行完整记录了这些夹具错误。由此弹出的“Missing Localisation”界面不能证明生产事件链是否正确。 |
| `round_03` | 无效测试轮 | 本地 `error_before.log` 与 `error_after.log` 仍保留同一组旧 `zhxrt` 夹具错误，实机也继续读取到无效夹具表现。本轮不能用来判断生产事件、迁徙或保护分支。 |
| `round_04` | 部分通过；暴露延迟回执测试缺口 | 新夹具能够进入异派学宫名册、显示逐学代价并扣除资源；但延迟一日的离境回执在自动化后台等待期间超时，且本地 `game_after.log` 第 175 行显示 `zhx_academy.220` 被 `Auto-selected`。因此只能证明事件被调度，不能证明玩家能够稳定看到并手动确认延迟回执。 |
| `round_05` | 即时离境回执通过 | [`01_immediate_departure_receipt.jpg`](round_05/01_immediate_departure_receipt.jpg) 显示“学宫离境”回执在结算后直接呈现；本地 `game_after.log` 第 166、169、170、171 行依次记录夹具设置、逐学选择、结算夹具与 `zhx_academy.220`，最后一条为玩家 `Selected`，不再是 `Auto-selected`。本轮的 `error_after.log` 未出现学宫、`zhxrt2` 或未知修改器相关报错。 |
| `round_06` | 保护取消、难民接纳与迁徙落点通过；事件队列表现待修 | [`01_protected_expulsion_cancelled.jpg`](round_06/01_protected_expulsion_cancelled.jpg) 显示“逐学令止息”保护回执；[`02_refuge_offer_visible_after_queue.jpg`](round_06/02_refuge_offer_visible_after_queue.jpg) 与本地 `game_after.log` 第 176 行证明玩家看见并接受 `zhx_academy.210`。存档核验表明崇礼学宫已迁入 `LUU` 的 2140，原址 5109 留下崇礼学宫遗址，详见 [`assertions.txt`](round_06/assertions.txt)。但普通事件窗口与 `.210` 出现堆叠/队列遮挡，仍待第七轮修复。 |
| `round_07` | 同步 `.210` 交付通过 | [`01_immediate_refuge_offer.jpg`](round_07/01_immediate_refuge_offer.jpg) 显示“流散学宫求庇”直接呈现在地图上，没有普通事件窗口堆叠；本地 `game_after.log` 第 172 行为玩家手动 `Selected zhx_academy.210`，且没有 `.210` / `.211` 的 `Auto-selected`。本轮只验证邀请的同步呈现与手动选择，不包含独立抵达回执，详见 [`assertions.txt`](round_07/assertions.txt)。 |
| `round_08` | **失败：首次 `.211` 省份事件没有交付回执** | [`01_refuge_offer.jpg`](round_08/01_refuge_offer.jpg) 与本地 `game_failed.log` 第 172 行证明 `.210` 仍被玩家接纳；但接纳后 [`02_missing_arrival_receipt.jpg`](round_08/02_missing_arrival_receipt.jpg) 只有空地图，日志没有任何 `Selected` 或 `Auto-selected zhx_academy.211`。这不是通过：首次 `.211` 省份事件方案未能产生玩家可见回执，已转入下一轮修复，详见 [`assertions.txt`](round_08/assertions.txt)。 |
| `round_09` | **失败：省份 → owner 同步 country `.211` 仍未交付** | 第二种方案先保存普通 event target，再从落点省份转到 `owner` 同步触发 country `.211`。[`01_refuge_offer.jpg`](round_09/01_refuge_offer.jpg) 与本地 `game_failed.log` 第 172 行证明玩家手动接纳 `.210`；但 [`02_missing_country_arrival_receipt.jpg`](round_09/02_missing_country_arrival_receipt.jpg) 仍只有地图，日志没有任何 `.211` 的 `Selected` 或 `Auto-selected`。本轮明确失败。随后改用“人类落点保存 global target → 回到 `.210` 玩家国家作用域统一触发 `.211` → 在 `.211` 清理 global target”的第三方案，并在 Round 10 通过，详见 [`assertions.txt`](round_09/assertions.txt)。 |
| `round_10` | **通过：第三种 global target `.211` 抵达回执成功** | [`01_arrival_receipt_success.jpg`](round_10/01_arrival_receipt_success.jpg) 清楚显示“学宫落脚”，正文点名崇礼学宫已在新址亳州重开讲席；本地 `game_after.log` 第 172、173 行依次为玩家手动 `Selected zhx_academy.210` 与 `.211`，两者均无 `Auto-selected`。聚焦学宫错误过滤为空。第三种投递链在这条单次实机路径通过，详见 [`assertions.txt`](round_10/assertions.txt)。 |
| `round_11` | **通过：`.211` 原生省份定位缎带可见** | [`01_arrival_native_goto.jpg`](round_11/01_arrival_native_goto.jpg) 显示“学宫落脚”窗口左上角的原生红色定位缎带，悬停提示清楚写着“转到省份”；本地 `game_after.log` 第 172、173 行连续记录玩家手动选择 `.210` 与 `.211`，均无 `Auto-selected`，聚焦学宫错误过滤为空。本轮证明缎带显示及悬停说明，未单独留存点击后镜头移动证据，详见 [`assertions.txt`](round_11/assertions.txt)。 |
| `round_12` | **通过：撤回逐学令回执与定位缎带** | [`01_withdrawal_receipt.jpg`](round_12/01_withdrawal_receipt.jpg) 显示 `.230`“撤销逐学令”：正文点名崇礼学宫与曲阜原址，并说明逐学压制解除及十年内不得再次逐学；长文本、按钮与装饰没有可见重叠或裁切。[`02_withdrawal_goto_tooltip.jpg`](round_12/02_withdrawal_goto_tooltip.jpg) 显示原生红色定位缎带悬停“转到省份”。本地 `game_after.log` 第 169–171 行依次为玩家 `Selected` `.100`、`zhxrt2.5`、`.230`，证明截图后 `.230` 选项被选择并执行事件选项流程；本轮没有直接读取存档内部冷却状态，详见 [`assertions.txt`](round_12/assertions.txt)。 |
| `round_13` | **通过：玩家拒绝后学宫保持流散并进入休眠** | [`01_refusal_result_tooltip.jpg`](round_13/01_refusal_result_tooltip.jpg) 显示鲁国收到崇礼学宫求庇；“婉拒其请”悬停说明明确写出不迁入、不永久删除、保持流散、天子每年 10% 尝试及无合格国时继续流散，界面无可见重叠或裁切。本地 `game_after.log` 第 166、169、171、172 行依次记录玩家 `Selected` `zhxrt2.1`、`.100`、`zhxrt2.2`、`.210 option 1`，均非 `Auto-selected`。一次性压缩存档解析得到 active 崇礼学宫 0、崇礼遗址 1、休眠标记 1，且 `LUU` 国家块的 pending/崇礼项均为 0；夹具仍在其他国家保留 13 个 pending，故不作全局清零或 5109 所有权断言。聚焦学宫错误为空，正常菜单退出后一秒进程检查为 `EU4_CLOSED`，详见 [`assertions.txt`](round_13/assertions.txt)。 |
| `round_14_failed_owner_scope` | **失败：所有者变化后旧国国家级逐学状态残留** | `own 5109` 后的压缩存档显示：5109 当前由 `WUU` 持有，崇礼学宫仍在该省，省份 `under_expulsion` 已为 0；但旧国 `QIN` 国家块仍各保留 1 个 `zhx_academy_expulsion_campaign` 与 `zhx_academy_expelling_chongli`。全存档没有崇礼遗址、休眠、冷却、结果或撤回目标，且本地 `game_failed.log` 只有 `zhxrt2.1`、`.100 option 7`、`zhxrt2.4`，没有所有者变化后的期限结算或回执。聚焦错误日志为空，说明这是静默状态清理失败。两张现场截图因 Sky 临时目录随 EU4 正常退出被清理而未落盘，本轮不冒充有截图证据，详见 [`assertions.txt`](round_14_failed_owner_scope/assertions.txt)。 |
| `round_15_owner_change_identity_pair` | **通过：所有者变化按旧国／学宫身份对清理** | 修复后重复同一路径，压缩存档显示 5109 已由 `WUU` 持有，崇礼学宫仍全世界唯一存在；`zhx_academy_under_expulsion`、`zhx_academy_expelling_chongli`、崇礼遗址和旧国逐学活动修正均为 0。[`01_post_transfer_map.jpg`](round_15_owner_change_identity_pair/01_post_transfer_map.jpg) 与 [`02_saved_state_menu.jpg`](round_15_owner_change_identity_pair/02_saved_state_menu.jpg) 留存现场，聚焦错误为空，详见 [`assertions.txt`](round_15_owner_change_identity_pair/assertions.txt)。 |

## 第四轮截图说明

- [`01_fixture_setup.jpg`](round_04/01_fixture_setup.jpg)：有效夹具正常显示“异派学宫”事件，不再出现缺少本地化的大型效果预览。
- [`02_expulsion_roster.jpg`](round_04/02_expulsion_roster.jpg)：逐学名册可见，悬停提示显示三年期限、50 行政点、1 稳定度、10 威望、外交关系与侵略扩张代价。
- [`03_expulsion_order_paid.jpg`](round_04/03_expulsion_order_paid.jpg)：选择逐学后，顶部资源从 584/稳定度 3/威望 100 变为 534/2/90，证明三项即时成本实际扣除。
- [`04_expulsion_deadline.jpg`](round_04/04_expulsion_deadline.jpg)：夹具的“逐学令结算”窗口已到达；它不是最终“学宫离境”回执。最终回执随后被后台自动选择，所以本图不能作为离境回执通过证据。

## 当前可以确认的最小闭环

现有证据可以确认：异派学宫进入名册 → 玩家查看逐学成本 → 支付行政点、稳定度与威望 → 强制到期结算 → 即时显示并手动确认“学宫离境”回执；测试夹具触发撤回路径后，会产生内容完整、带原生定位缎带且可由玩家手动确认的“撤销逐学令”回执；受主学派或第二学派保护时会撤销逐学令并给出“逐学令止息”回执；流散学宫邀请既可被玩家接纳，随后新省份落点并在原址留下遗址、显示带原生省份定位缎带的“学宫落脚”回执，也可被玩家拒绝，随后保持一处遗址、无 active 学宫并进入休眠。第一轮发现的纵横家学宫贸易力量修改器键已在后续启动日志中不再复现。

这些证据**尚未**覆盖以下分支，因此不能宣称整套生命周期已完成实机验收：

- 候选国优先级、不同发展度落点档位及没有合格省份时的全部分支；
- 多个候选国竞争、连续拒绝及后续转交行为；第十三轮只覆盖 LUU 的一次玩家拒绝；
- 多个国家或同日多次迁徙时，global target 抵达回执的隔离与清理；第十轮仅覆盖一次 `.210 → .211` 链；
- 主学派保护与第二学派保护两种来源的分别穷举验证；
- 所有者变化取消逐学已在第十五轮以崇礼学宫这一组“旧国／学宫身份对”通过；尚未穷举十二座学宫和并发逐学场景；
- 天子每年 10% 复建/重试的实际年度触发；第十三轮已验证拒绝后的休眠状态，但未推进年份观察重试；
- AI 年度逐学，以及撤回后的内部冷却状态、十年到期与重新逐学；第十二轮只直接验证撤回回执内容和 `.230` 选项执行。

## 日志使用注意

`round_02`–`round_15_owner_change_identity_pair` 使用过仅供回归的 `zhxrt` / `zhxrt2` 临时事件。第二、三轮的夹具错误属于测试设施本身；第四轮之后才使用可交互的新夹具。第六轮发现的 `.210` 普通事件队列遮挡在第七轮通过同步交付消除；第八、九轮的 `.211` 静默未交付分别保留为失败证据；第十轮第三种 global target 投递链才是抵达回执的首个通过证据；第十一轮进一步证明原生省份定位缎带及悬停提示正常显示；第十二轮证明撤回回执的专名内容、布局、定位缎带和玩家选项流程；第十三轮证明玩家拒绝说明、手动拒绝分支及拒绝后的崇礼学宫休眠状态；第十四轮保留了所有者变化后旧国国家级逐学状态残留的失败证据，第十五轮以同一身份对证明修复成立。第十四轮截图只在实测时目视检查，未从短命 Sky 临时目录复制出来，因此证据目录只保存日志和存档解析断言。临时夹具必须在最终交付前移除，并在无夹具的新战役中再做一次干净启动回归。
