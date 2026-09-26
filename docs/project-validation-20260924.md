# 跨页、BOM与项目报表验收 · 2026-09-24

结果：两页接口试验通过，随后建立的独立两页继电器项目也通过单独验收。真实本机 AutoCAD Electrical 2026；全部MCP通过stdio，不使用模型API key。

## 第一阶段：接口试验

目录 `work/acceptance/project-probe-20260924-163839/`，WDP为 `API-VALIDATION.wdp`，仅包含P01/P02。

跨页SIGCODE为MCP_CROSS_101，源/目标符号分别为HA1S1/HA1D3；源端101传播至目标。两端XREF为2.2-C与1.4-C。重开后仍正确。

`mcp-verification.json`为PASS。原生BOM导出RELAY_TEST、TERMINAL_TEST各1件；原生元件表1件；原生From/To确认X1:1→K1:A1，线号101，页1→页2。原生文件为mcp-bom.csv、mcp-components.csv、mcp-from_to.csv。

## 第二阶段：独立小项目

目录 `work/projects/relay-demo-20260924-164801/`。

- RELAY-DEMO.wdp：01-SUPPLY.dwg与02-CONTROL.dwg。
- 供电页：2个正式端子、1个熔断器、2个源信号。
- 控制页：按钮、继电器、2个目标信号。
- 原生BOM：4类5件；元件表3项；From/To 4条，其中2条跨页。
- 单独验收：`verification-20260924-165456/verification.json`为PASS；重新打开2页，核对9符号、8导线段、接线点、线号、对页引用，并重新导出原生报表匹配独立设计清单。
- Computer Use分别检查两页；额定值/目录号均为测试或待定值，不是施工设计。

详细图纸和报表清单见该输出目录中的“验收说明.md”。work被Git忽略，仓库只存可公开的合成设计清单和重现脚本。

## 新MCP能力

| 工具 | 范围及回读 |
| --- | --- |
| get_electrical_project | 原生读取WDP及完整图纸成员列表 |
| update_electrical_signals | 当前页源/目标引用与线号更新，读取SIGCODE/XREF/WIRENO；整个项目须逐页调用 |
| export_electrical_project_report | 指定WDP，原生bom/components/from_to，导出新CSV并读取全部行 |

项目工具核对预期WDP、当前图纸成员，在CAD表达式内再次核对WDP；导出后检查成员未变，拒绝覆盖已有CSV以避免陈旧结果。全字段原生CSV无表头，已按本机2026输出和设计清单进行验收；跨版本字段顺序仍待适配。文件生成不自动代表设计正确。

依据：本机ACE_API.chm中的c:wd_proj_wdp_write、c:wd_makeproj_current、c:ace_add_dwg_to_project、c:wd_proj_wdp_data、c:wd_mdb_freshen、c:ace_sig_update、c:wd_bomschr、c:wd_compr_sch、c:wd_frm2_r。c:ace_cb_insym_signal在当前会话未加载，实际使用已验证的c:wd_insym2插入源/目标库符号，再由原生更新接口处理连接。

## 测试与边界

66项非集成测试通过，3项上游mock集成测试未运行。新增测试覆盖错项目、非成员图纸、报告防覆盖、非法类型以及独立验收对漏连接、错端子、错误BOM的识别。

AutoCAD关闭/切换图纸偶发COM短暂不可用；独立验收只重试只读操作，不重试绘图或报告写入。仍不支持两个客户端并发写入同一实例。原有reports.py扫描/WDREPORT命令工具保留为实验能力；本次仅验证新原生工具。

尚未验收：父子触点跨页引用、多目标信号分支、大项目性能、端子排编辑器、目录数据库及子装配BOM、PDF/打印、真实TREBI国产化器件与安全回路。

## 重现

构建：`scripts/small_project_smoke.py --write --template <本机DWT绝对路径> --library <本机IEC2库绝对路径>`。

独立验收：`scripts/verify_small_project.py <生成的项目目录>`。该脚本从examples/relay-demo/design.json读取期望结果，每次使用新的verification目录。运行前让AutoCAD完成当前交互；保存所有项目图纸。
