---
name: eu4-add-impassable-mountains
description: 为 Europa Universalis IV 地图模组规划、绘制、登记、审计和测试不可通行山脉省份。用于处理 provinces.bmp 像素绘制、唯一省份 ID 和 RGB 分配、definition.csv、default.map、climate.txt、continent.txt、terrain.txt、本地化、山体四向连通、封锁道路、保留山口以及游戏内寻路验证。
---

# EU4 不可通行山脉实装流程

## 确认范围

- 定位包含 `descriptor.mod` 和 `map/provinces.bmp` 的模组根目录。
- 检查 Git 状态并保留无关修改。
- 确认用户允许修改的目录。
- 修改正式地图文件前，说明原因并取得用户同意。
- 未经明确授权，不修改 Steam 安装目录或启动器模组副本。

## 冻结通行设计

- 记录必须切断直接邻接的省份组合。
- 记录必须保留通行的省份组合。
- 使用正交公共边保留山口，不依赖对角像素。
- 为互不相连的山体分配不同省份 ID。
- 先检查现有邻接，再开始绘制。

## 分配 ID 与 RGB

- 读取 `map/definition.csv`，确定当前最高 ID。
- 为新增山体分配连续且未使用的 ID。
- 确认新 RGB 未在 `definition.csv` 和 `provinces.bmp` 中出现。
- 将 `max_provinces` 设置为最高有效 ID 加一。
- 绘图后不得随意更换已经冻结的 RGB。

## 绘制候选图

- 复制正式 `map/provinces.bmp` 作为候选图。
- 不直接在正式 BMP 上练习。
- 用户使用 Photoshop 时，读取 `references/photoshop.md`。
- 使用 RGB、24 位、无压缩 BMP。
- 禁用抗锯齿、透明度、羽化和颜色混合。
- 保证每段山体为可靠的四向连通块。
- 避免单像素飞地、单像素长颈和意外捷径。

## 审计几何

- 在正式写入前执行只读检查。
- 检查 BMP 尺寸、位深、压缩方式和像素偏移。
- 检查新颜色的像素数量和四向连通块数量。
- 确认需要切断的省份公共边为零。
- 确认预留山口仍有稳定的正交公共边。
- 确认受影响的可通行省份没有被意外切成多个部分。
- 存在审计脚本时，优先运行 `scripts/audit_mountain.py`。

## 登记山脉

候选几何审核通过后，按照 `references/workflow.md` 更新：

- `map/provinces.bmp`
- `map/definition.csv`
- `map/default.map`
- `map/climate.txt`
- `map/continent.txt`
- `map/terrain.txt`
- 可读本地化源
- 游戏读取的编码本地化

不可通行山地通常不创建：

- 省份历史；
- 所有者、核心和发展度；
- `positions.txt`；
- Area、Region、贸易节点或贸易公司成员；
- 普通特殊邻接。

## 验证

- 检查完整 Git 差异。
- 确认启动器实际读取的模组目录。
- 使用全新的 1444 年游戏测试。
- 使用 `debug_mode` 核对山体 ID 和名称。
- 测试不可进入、封锁路线和预留山口。
- 检查 `error.log` 与 `map.log`。