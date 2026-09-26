# 父子触点与端子报表专项验收（2026-09-24）

## 本轮计划与结果

1. 独立三页工程：完成。复制原合成双页工程，第三页增加 K1 常开触点和 X2:1、X2:2。
2. 父子引用 API 验证：完成。保存重开后，第二页 K1 线圈 XREFNO=3.3-C，第三页 HCR21 子触点 XREF=2.4-B。TAG1/TAG2 都为 -K1。
3. 原生端子报表接入 MCP：完成。export_electrical_project_report 新增 terminal_plan、terminal_numbers 两个 report_type。
4. 报表与预期设计逐项比较：完成。端子计划 4 行、端子线号 4 行、From/To 6 行；BOM 继电器 1、按钮 1、熔断器 1、端子 4。子触点未重复计入 BOM。
5. 导线验收缺口修复及自动测试：完成。77 passed，3 integration deselected；后者不能替代实机验收。
6. 父子引用封装为默认 MCP 工具：待完成；本轮仅完成原生 API 与保存重开验证。

## 修复依据

原生 ace_insert_wire 返回 9BE、9BF。9BE 正确连接 K1:14 与 X2:2；9BF 从 (211.25,170) 到 (208.75,170)，网络只有 X2:2 自身的 X1TERM01/X4TERM01，导致端子计划多出无对端的第 5 行。

旧接口只检查第一条返回线段。现逐段要求原生网络同时包含两个请求接线点；异常返回 success=false、created_wire_handles 和 retry_safe=false，供检查，不自动重试或删除。测试图中仅在确认几何与网络后移除了 9BF，再保存重开并通过真实 stdio MCP 导出报表。此结果不是自动布线已完全修复：原生 API 为什么额外创建此段仍待进一步调查，当前修复防止误报成功。

## 证据

本机工程：work/projects/contact-terminal-20260924-190524/CONTACT-TERMINAL.wdp。
原异常报表 terminal_plan.csv 和 extra-wire-before-repair.json 保留。
MCP 调用结果：同目录 mcp-191325/results.json、四份原生 CSV。
独立断言与父子属性回读：mcp-191325/acceptance.json。
复验脚本：python -m scripts.verify_contact_terminal <工程目录> <MCP结果目录>。脚本读取既有报表，关闭并重开已保存的测试页面，不自动保存未保存页面，也不重新生成报表。

API 签名来自本机 Electrical 2026 ACE_API.chm：c_wd_xref_doit.html、c_ace_termplan_r.html、c_wd_term_nums_rpt.html。两种端子报表为 9 参数列表，和 BOM 参数数量不同。

## 边界与下一项

默认工具数量仍为 21（共 58 项定义），本轮扩展已有报表工具，未扩大未验证工具暴露范围。未进行本轮图面视觉验收，未验收中文/英文图框、多触点/常闭/多线圈父子匹配、多层端子、端子排图形生成、生产级 TREBI 工程。

下一项为：父子引用 MCP 封装和项目目标保护；独立项目全流程复验；随后调查插线额外线段的触发条件。没有将当前合成图作为正式电气设计。
