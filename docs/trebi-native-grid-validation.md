# TREBI 原生页区引用验收

2026-09-25：193 项默认自动测试通过，3 项 integration 未运行；工具定义仍 62 项，默认开放 25 项。实机验收使用独立合成工程，不代表整套 TREBI 电气图或所有工具已验收。

## 已通过的范围

电气图继续使用独立 KINTO_TREBI_ELECTRICAL_A3 图框（底部整行标题栏、顶部 0～9）。机械双语图框保留。新增内部 trebi_native_grid.configure，核对目标 DWG、唯一 WD_M 与 TREBI 图框后设置 REFNUMS=5、明确逻辑 SHEET、DATUMX=10、DATUMY=289、DISTH=40、CHAR_H=0,1,2,3,4,5,6,7,8,9，XREFFMT/ALT_XREFFMT=%S.%N。其他 WD_M 属性保持不变。

使用逻辑页 54、112，而非连续物理页 1、2：

| 对象 | 原生回读 |
| --- | --- |
| PAGE 54、第 2 区源箭头 | XREF=112.8 |
| PAGE 112、第 8 区目标箭头 | XREF=54.2 |
| PAGE 54、第 5 区常开触点 -112K1 | XREF=112.8 |
| PAGE 112、第 8 区线圈 -112K1 | XREFNO=54.5 |
| 两个跨页端子 | -X54:1 与 -X112:1，线号 501 |

上述引用均由原生更新生成，没有直接写入 XREF 属性。两页保存重开后属性与设置一致。BOM 原生读回继电器 -112K1/RELAY_DEMO 数量 1，端子 TERMINAL_DEMO 数量 2；From-To 一条跨页连接、逻辑页 54/112；端子计划和端子线号各两条，线号均 501。品牌/目录号均为测试值，不是采购型号；继电器线圈与触点本次只验证关联，未接入功能电路。

## 本轮发现并修复

原插入接口先自动生成父元件位号，再修改 TAG1，导致表面 TAG1=-112K1，但扩展数据 VIA_WD_BASETAG 仍是 K1；Electrical 将其视为 -K1，与触点不匹配。原生 XREF.BAD 和缓存 COMP 表均证实，重建数据库也没有纠正扩展数据。补全分区标签并不是此故障的修复。

依据本机 2026 ACE_API.chm 的 c:wd_insym2 选项定义，对显式传入 TAG1 或 TAGSTRIP 的插入使用 options=6（返回句柄并禁止自动生成位号）；其他插入保留 options=2。在新工程中通过原生引用及 BOM 验证。没有改写失败工程来伪造通过，也没有手工写基础位号或引用属性。此策略只覆盖新插入，既有错误位号的修复工具仍待实现。

第三次工程原生引用正确并已保存，但独立重开阶段读取 Documents.Open 方法发生瞬时 AttributeError，实际 Open 尚未提交。增加有次数上限的方法读取重试；实际打开命令只执行一次，调用失败不自动重放。独立复验随后通过，保留原始失败记录。

## 可追溯证据（本机私有 work）

- work/projects/trebi-zones-20260925-090430：首次失败、回读与恢复记录。
- work/projects/trebi-zones-20260925-090918：完整分区标签仍失败；XREF.BAD/REP/GO2、failure-readback.json、recovery-evidence.json、database-rebuild-diagnosis.json。
- work/projects/trebi-zones-20260925-092115/acceptance.json：第三次建图与默认 MCP 原生引用结果，原始状态保留 FAILED（重开方法读取失败）。
- work/projects/trebi-zones-20260925-092115/reverification-092447/report.json：独立重开、线号、四类原生报表 PASS；同目录保留 CSV。

复验入口：`.venv/Scripts/python.exe -m scripts.verify_trebi_native_grid <合成工程目录>`。创建入口：`-m scripts.trebi_native_grid_smoke --write`，依赖本机既有验收种子和 IEC2 库。脚本仅用于验收，不是正式项目创建工具。

## 仍待完成

- TREBI 标题栏 WDT 自动字段映射、正式项目创建和默认 MCP 模板选择。旧机械图框的 WDT 验收不能替代这一项。
- 同页引用、原生区域 0/9 边界、NC 触点在新模板中的专项验证。本轮真实引用只覆盖区域 2、5、8；全部十区仅有几何计算测试。
- 电位类别隔离、PLC 地址与端子、连接器、电缆和安全双通道的 TREBI 专项规则与实际回路验收。
- 新两页电路的视觉布局与 PDF 验收尚未执行；此前空白图框 PDF 通过不等于本次电路出图通过。

原始 TREBI PDF 保持只读，本轮未修改正式图纸，未生成生产可用安全电路。

## API 依据

本机 AutoCAD Electrical 2026 ACE_API.chm：c:wd_insym2、c:wd_modattrval、c:ace_GBL_wd_m、c:wd_xref_doit；提取文档在 work/api-2026。

[Autodesk 参数说明](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Electrical/files/GUID-8F803D63-4390-4617-BC71-F68AE7545D97.htm)说明 %S 为图纸页号、%N 为引用或顺序编号；[官方基础位号说明](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/To-use-Tag-Format-Family-Override-option-on-Cable-Markers-in-AutoCAD-Electrical.html)提及重编号产生的 VIA_WD_BASETAG。具体故障结论以本机对象和原生报表为证据。
