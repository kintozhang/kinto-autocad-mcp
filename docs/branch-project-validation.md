# 双分支项目报表与线号缓存验收（2026-09-24）

## 本轮结果

四个 HT0001 端子 XB:1/2/3/4，通过一条主线和上下两条支线连接。全部为同页等电位网络 501，两个 T 接点。分别建立普通线号、固定线号的独立 WDP 工程，通过默认 MCP 建图、重复调用测试、保存重开和原生项目报表。

- BOM：BRANCH_TERMINAL / KINTO_TEST 共 4 件，一行。
- 端子线号表：4 行，每个端子均为 501。
- From/To：3 条连接覆盖全部 4 个端子；当前原生顺序为 1-3、3-4、4-2。
- 端子计划：6 条端点记录，与 From/To 的双向端点记录逐项一致。分支报表中一个端子可以有多条合法记录，不能一概当作重复错误删除。
- 保存重开：3 条 LINE 几何与设计完全一致，每条原生网络均识别全部四个接线点；普通 WIRENO、固定 WIRENOF 类型分别保持。
- 重复主线、反向主线、重复两处分支不会增加图元。固定线号工程已进行结构图面检查，两处分支和接点清楚，线号处于接点之间。

本样板只定义同电位网络，不指定现场逐根接线顺序。独立验收检查 From/To 是覆盖四个端子的连通无环图，并与端子计划一致，不把原生排序冒充用户规定的物理接线顺序。

## 修复的问题

首个项目 branch-project-20260924-202322 的线网回读均为 501，但两个新增分支端子的 X8TERM01/X2TERM01 为空，原生端子线号表因此漏号。之前的单图网络检查不能覆盖该报表缺口。

分支工具现在在插入并核对网络后调用 c:wd_putwn 或 c:wd_putwnf 更新现有线号，保留普通/固定类型，然后严格回读全部端点的 X?TERMxx 属性及号码类型。已连接但缓存过期的旧图不再被当作完整验收通过，返回明确错误，且不重复画线。

来源为本机 Electrical 2026 ACE_API.chm 的 c_wd_putwn、c_wd_putwnf、c_ace_get_wnum。官方 wd_putwnf 示例明确说明更新会重置所连接元件的 X?TERMxx 属性。未直接伪造缓存值，使用原生编号 API 更新。

## 证据及复验

- 普通线号：work/projects/branch-project-20260924-202728/report.json、semantic-acceptance.json 和四份 CSV。
- 固定线号：work/projects/branch-project-20260924-203117/report.json、semantic-acceptance.json 和四份 CSV；number_kind_reopened=PASS。
- 原缺口现场：branch-project-20260924-202322 的原始四份 CSV 保留，其中新增端子的线号为空。一次额外报表探测遇到 COM 忙碌并返回失败，也保留；未用它作为修复通过证据。
- examples/branch-project/design.json 为独立设计规格。scripts/verify_branch_project.py 核验 BOM、端子/句柄/线号、From/To 连通图、端子计划对端及保存后的几何。
- tests/fixtures/branch-project-evidence.json 为删除本机路径后的真实合成回读样本，不含 TREBI 原图或真实采购数据。

构建：python -m scripts.branch_project_smoke --write；固定版本增加 --fixed。独立复验：python -m scripts.verify_branch_project <工程目录>。构建脚本依赖本机已知 DWT、IEC2 库和前轮合成 WDP 配置，尚不是跨机器部署包。

自动测试 111 passed，3 deselected。新增负例覆盖空分支线号、错误 BOM、断开的报表连接图、端子计划错误对端/重复记录、重复句柄、保存后的端点缺失和普通/固定类型歧义。

## 范围

默认工具仍为 23（总定义 60）。本轮完成同页两分支项目，未证明跨页分支总线、任意障碍物绕线、跨客户端事务或 COM 通用恢复。没有新增或改动上轮 PDF，没有制作双语模板，也未修改真实 TREBI 工程。
