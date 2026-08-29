# 凉国复国事件链：实机测试流痕

测试环境：EU4 `1.37.5.0 Inca`，模组校验和 `5b56`，1444 年 11 月 11 日普通单人新档。

## 截图顺序

| 阶段 | 实机结果 | 截图 |
| --- | --- | --- |
| 1. 新档基线 | 1444 开局时地图上没有凉国；`LGU` 是休眠 tag。 | [01_1444_fresh_start_no_liang.jpg](01_1444_fresh_start_no_liang.jpg) |
| 2. 自然开场 | 直接在国家选择界面选择周诸侯鲁国，不调用事件命令；开局自然运行后，于 1445-02-10 显示“使者来自周天子／亡凉遗使谒天子”。这对应脚本的 `days = 90` 调度。 | [02b_intro_natural_day90.jpg](02b_intro_natural_day90.jpg) |
| 3. 请封选择 | 被抽中的诸侯收到干净的二选一界面；选地扫描放进 `hidden_effect` 后，不再把临时发展度变量刷到事件正文。 | [03_petition_clean_lowest_dev_choice.jpg](03_petition_clean_lowest_dev_choice.jpg) |
| 4. 凉国复立 | 接受请封后 `LGU` 建国，并成为原诸侯的原版卫戍国（`subject_type = march`）。 | [04_liang_restored_as_march.jpg](04_liang_restored_as_march.jpg) |
| 5. 履约分支 | 原诸侯与凉国控制武威、靖远、永昌并稳定 30 天后，原诸侯履约；三处故土归凉、凉国迁都武威、初封地归还原诸侯，卫戍关系保留。 | [05_honor_return_to_wuwei.jpg](05_honor_return_to_wuwei.jpg) |
| 6. 国家与宗王 | 玩家切到凉国检查：使用用户指定的小篆“凉”印章旗；宗王显示为张承祚，26 岁，行政/外交/军事为 3/5/2。 | [06_liang_flag_ruler_age_stats.jpg](06_liang_flag_ruler_age_stats.jpg) |
| 7. 故土请求 | 玩家诸侯侧出现“请归凉土”，可选择履约或拒绝。 | [07_homeland_request_player_choice.jpg](07_homeland_request_player_choice.jpg) |
| 8. 拒绝分支 | 拒绝后显示“前约尽毁”；撤销永久正面加成，凉国独立倾向置为 100，并给原诸侯施加 20 年负面修正。 | [08_refusal_compact_destroyed.jpg](08_refusal_compact_destroyed.jpg) |
| 9. 调试页初态 | 全新 1444 档中，开发调试目录第三页正确显示“等待序章”，没有伪造尚不存在的请封对象。 | [09_debug_catalog_awaiting_intro.jpg](09_debug_catalog_awaiting_intro.jpg) |
| 10. 最近对象留痕 | 周天子正式收到请封并拒绝后，调试页显示“最近一次正式请封对象：周天子”；180 天等待期内保留该对象。 | [10_debug_catalog_recent_target.jpg](10_debug_catalog_recent_target.jpg) |
| 11. 正式随机抽取 | 运行事件链正式的无放回随机选择器后，本次抽中“辽”；其拒绝后调试页立即更新为“最近一次正式请封对象：辽”。 | [11_debug_catalog_random_target_liao.jpg](11_debug_catalog_random_target_liao.jpg) |

旧的 [02_intro_event_natural_queue.jpg](02_intro_event_natural_queue.jpg) 保留为第一次长时间运行的队列证据；其画面日期已经被原版弹窗积压拖后，因此不再用于证明 90 天时序。

## 存档状态核对

成功分支的明文存档显示：

- 凉国首都为动态选出的 5106 号省份（8 发展度），且该省带有“原始封地”追踪标记；
- 凉国拥有 5106，并拥有武威 708、靖远 2182、永昌 5295 的核心；
- `overlord = QIC`，依附关系为 `subject_type = march`；
- 凉国带有周天下成员标记，国教为儒教；
- 原诸侯拥有永久 `gdd_liang_preserver_of_fallen_state`，效果为 `+0.33` 外交声誉。

履约分支显示三处故土转交凉国、首都迁往武威，仍保留卫戍国关系；若初封地仍由凉国持有，它会归还原诸侯。

拒绝分支在次月存档中显示：

- 原诸侯的永久正面修正已经移除；
- `gdd_liang_repudiated_restoration_compact` 持续至 1464-11-11，即 20 年；
- 凉国缓存独立倾向为 `100.000`，月度结算后画面值为 `99.800`；
- 依附关系仍为原版 `march`。

## 测试方法与边界

90 天开场测试是完整自然运行：没有使用 `event` 命令。其余分支为提高复现速度，使用调试控制台固定玩家 tag、故土所有权和监视器检查点；事件选项、建国、领土转移、属国关系、修正和存档状态均由正式脚本执行。

调试目录验证在另一份全新 1444 普通档中完成。控制台只用于打开开发目录和加速到相应阶段；第 11 张图中的“辽”由生产事件 `.2` 的正式 `random_country` 无放回选择器抽出，并非手工写入事件目标。调试页中的目标只是只读观测镜像：它表示“最近一次正式请封对象”，下一站在选择器真正运行前并不存在，因此拒绝后的 180 天等待期仍显示上一站。

随机无放回询问、候选至少五城、首都排除、并列最低发展度随机选地和“名册耗尽后永久终止”已由静态验证器覆盖。完整逐国拒绝若按每次 180 天自然等待会跨越多年，本轮没有把整圈按墙钟时间播放到底。

## 最终检查

- `tools/validate_liang_restoration_tag.py`：PASS
- `tools/validate_liang_restoration_chain.py`：PASS
- `tools/validate_zhx_debug_catalog.py`：PASS（3 页均未超出原版事件窗口预算）
- `tools/encode_eu4_chinese_event_scripts.py --check`：PASS
- `tools/encode_eu4_chinese_localisation.py --check`：PASS
- `git diff --check`：PASS
- 最新 `error.log`、`setup_error.log`、`game.log` 中 `LGU` / `gdd_liang` 相关错误：0
- `setup.log` 确认 `LGU`、`gdd_liang_restoration` 命名空间和 12 个事件已载入。

全局日志仍含本模组既有的任务树和旧 area 报错；这些错误没有命中 `LGU` 或 `gdd_liang`，不属于本事件链。
