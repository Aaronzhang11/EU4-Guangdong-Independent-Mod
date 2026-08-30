# 调试事件目录实机验收（2026-08-24）

测试环境：EU4 `1.37.5.0 Inca`，`religion` 分支，中国标签 `CZH`。

## 验收步骤

1. 新测试局打开决议页，确认默认不存在“调试”决议（`01_before_activation_no_debug_decision.png`）。
2. 控制台执行 `event zhx_debug.1 CZH`，选择“启用并打开调试目录”。
3. 检查第一页“天下公议”和第二页“礼教学派”：每页恰好六个选项，文字没有重叠、裁切或溢出（`02_catalog_page_1_tianxia.png`、`03_catalog_page_2_doctrines.png`）。
4. 选择“调试天下大辩”，确认正确转入 `zhx_debug.100` 的三种开发预览选择器；选择“暂不进行开发预览”，没有改变正式公议状态（`04_catalog_dispatches_great_debate.png`）。
5. 返回决议页，确认“调试”已经出现（`05_after_activation_debug_decision.png`），并可从该决议重新打开目录（`06_decision_reopens_catalog.png`）。
6. 在第二页选择“关闭并停用调试决议”，确认决议立即消失（`07_after_disable_no_debug_decision.png`）。
7. 检查本轮日志：`error.log` 没有新增涉及 `zhx_debug`、目录决议、事件编号、缺失本地化或解析的错误；`game.log` 只有预期的事件选项记录。
8. 通过游戏菜单正常退出，并确认 EU4 进程已经关闭。

## 引擎限制

EU4 1.37.5 的原生控制台 `debug_mode` 状态没有暴露给脚本触发器。实机探针中的 `is_debug = yes` 与 `debug_mode = yes` 均被引擎报告为未知触发器。因此目录采用一次性的控制台事件 `event zhx_debug.1 CZH` 设置存档内旗标；原生 `debug_mode` 仍可同时用于显示 ID 和开发提示，但不能单独控制模组决议的可见性。
