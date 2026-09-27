# Kinto AutoCAD MCP

面向 Windows 本机 AutoCAD Electrical 2026 的 Codex MCP 项目。
通过 Codex 的 ChatGPT 订阅会话调用本机工具；MCP 服务自身不调用模型、不需要 API key。

当前阶段：**2026 本机基础几何和单页 Electrical 原生操作已验收**。
元件、正式端子连接、线号及保存重开通过真实 MCP 测试；两页合成项目的跨页信号与原生项目报表也已验收；真实整套工程仍待验收。
不能把工具返回 success 当作可施工图纸的证明。

当前版本：**73项定义、33项默认工具，591项默认测试通过**（2026-09-27）。
独立COM工作进程、超时隔离与诊断见[本轮验收](docs/execution-isolation.md)。
[扩展电气与恢复验收](docs/extended-electrical-acceptance.md)：连接器/三芯电缆、通用PLC、灯支路和双网络样板；新增受限中断恢复。Delta整模块和实际安全功能仍待验收。
下方逐次验收链接保留历史状态；最新能力以本轮说明及能力清单为准。

## 目录

| 目录 | 用途 |
| --- | --- |
| src/ | 保留上游 MCP 服务、COM 和工具实现 |
| cad_bridge/ | 待验证的 Electrical API / AutoLISP 桥接开发区 |
| profiles/ | 2026 环境、符号库、模板和项目设置草案 |
| skills/ | 电气与机械制图工作流；尚未安装到用户技能目录 |
| tests/ | 上游单元测试及本机验收说明 |
| examples/ | 可公开的合成样板任务 |
| docs/ | 安装、Codex 接入、能力清单、排错、路线图 |
| scripts/、web/ | 保留的上游脚本和可选 Web 模式 |

## 开始

在项目目录中使用 Windows Python 3.11+：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

[安装与 Codex 接入](docs/setup.md)包含本机 stdio 配置。
[能力清单](docs/capabilities.md)区分已有代码与已验证能力。
[首轮验收](tests/acceptance/README.md)定义真实 CAD 验收标准。

初始化保留上游依赖和 config.yaml，以免破坏现有测试及 Web 模式。
其中模型 SDK 的安装不代表需要填写密钥；订阅流程只启动 src.server。
依赖精简和供应商配置解耦列入下一阶段。

真实工程、采购资料和厂家文件放在 Git 忽略的 work/ 或独立私有目录。
examples/ 只放合成资料，不包含 TREBI 原图。

## 来源与许可

Fork: https://github.com/kintozhang/kinto-autocad-mcp
Upstream: https://github.com/Igualguana/AUTOCAD-ELECTRICAL-MCP

保留上游 AGPL-3.0 LICENSE 和历史。[上游说明快照](docs/upstream/README.md)
用于追溯，不代表本 fork 已验证其全部能力。
## Claude 订阅与本机配置

已生成 Codex 项目配置 .codex/config.toml 和 Claude Code 项目配置 .mcp.json，
两者均为 Git 忽略的本机文件。客户端加载仍取决于项目信任和订阅登录。
Claude Code/Claude Desktop 的接入步骤见 [Claude 接入](docs/claude-setup.md)。
不要让 Codex 和 Claude 同时控制同一个 AutoCAD 实例。

[初始化验证记录](docs/initialization-report.md)：42 项测试通过，3 项集成测试未运行；
包含不连接 CAD 的真实 stdio 握手测试。实际客户端配置加载仍需单独验证；后续本机绘图结果见下方。

[2026 本机联调](docs/live-validation-20260924.md)：MCP 几何样板及保存重开通过；电气符号插入失败回执已修正，45 项回归测试通过。

[原生电气验收](docs/native-electrical-validation-20260924.md)：旧符号接口已替换，端子至继电器连接及101线号逐项回读通过；58项回归测试通过。

[跨页及小项目验收](docs/project-validation-20260924.md)：两页继电器演示，原生BOM共5件、From/To共4条，独立保存重开验收通过；66项回归测试通过。

[最新工具加固](docs/wire-xref-hardening.md)：59项工具定义、22项默认提供，37项仍隐藏；父子常开触点、接线修复、项目上下文保护及三页 MCP 报表复验通过。87项自动测试通过。


[最新双触点与交叉线验证](docs/multicontact-crossing-validation.md)：常闭触点、两组折线和交叉隔离通过独立验收；89 项自动测试通过。默认工具仍为22项；COM瞬时断连的稳定性问题尚未全部解决。


[最新 T 分支与 PDF 验证](docs/branch-pdf-validation.md)：默认23项工具，97项自动测试通过；T分支、重复连接保护与A3单页PDF样张已验收，复杂分支和批量出图仍待验证。


[最新双分支项目验收](docs/branch-project-validation.md)：普通/固定线号及项目报表通过，修复新增分支端子线号漏报；111项自动测试通过，默认仍23项。

[三页 PDF 出图验收](docs/multipage-pdf-validation.md)：按 WDP 页序原生导出三页 A3 合成工程，合并后内容流/纸张尺寸及全页渲染通过；源图哈希不变。默认回归116项通过，另7项 PDF 专项在捆绑运行时通过。当前为验收脚本，尚未增加默认 MCP 出图工具。

[默认 MCP 多页 PDF 工具](docs/mcp-pdf-validation.md)：新增受限 DIN A3 合成项目出图，默认24项/总定义61项；真实默认 MCP 出图、逐页视觉和独立保存重开报表通过。131项测试通过；有一次出图后的 COM 枚举异常，保留失败记录及独立复验。

[中英双语标题栏](docs/bilingual-titleblock-validation.md)：三页合成图框、空白 DWG 种子、字段及字体保存重开、原生报表和默认 MCP PDF 逐页检查通过。采用黑体 TTF，修复中文问号；136项测试通过。仍为显式字段映射，未实现 WD_TB 自动更新；默认24项。

[COM 稳定性与原生标题栏映射](docs/com-stability-title-mapping.md)：修复忙碌误断连、增加有限只读重试及目标就绪检查；20次实机切换、单次写入与重开通过。三页项目名/版本/页码经原生WDT更新并通过报表复验。148项测试通过；跨客户端互斥和COM硬超时尚未实现。

[跨客户端互斥验收](docs/client-concurrency.md)：新版MCP工具调用共用进程间锁，冲突请求在执行前拒绝，中断标记持续拦截；独立副本画圆及保存重开通过。152项测试通过，默认仍24项；旧服务需重新连接，UI/直接COM不受此锁约束。

[统一目标参数与隔离PDF复验](docs/target-pdf-isolation.md)：错误DWG/实例在进入工具前拒绝；三页双语PDF、逐页视觉、源图哈希及独立重开报表通过。170项测试通过，默认仍25项。

[TREBI电气模板与规则](docs/trebi-template-rules.md)：保留机械图框，新建底部整行电气标题栏及0..9分区；空白DWG回读/保存重开和原生PDF通过。后续原生页区引用验收见下。

[TREBI 原生页区引用验收](docs/trebi-native-grid-validation.md)：两页54/112的导线、线圈/触点引用与线号501保存重开通过，四类原生报表一致。修正显式位号插入时保留旧基础位号的问题，增加COM打开方法查找重试。193项测试通过，默认25项；新电路PDF、WDT映射及完整TREBI语义仍待验证。

[TREBI有效图页清单](docs/trebi-page-manifest.md)：按显式有效图页计算OF、生成PAGE/PREV/NEXT，配置功能页分组并校验引用目标。215项测试通过；本轮离线规则验证，尚未自动写入WDT/DWG。

[TREBI位号与标题栏联调](docs/trebi-component-title-validation.md)：按所属页生成主元件位号，异页触点继承；新电气图框PAGE/OF原生WDT及清单导航通过两页保存重开和四类报表独立复验。244项测试通过；内部规划/验收接口，默认工具仍25项。COM拒绝调用发生过，保留失败与恢复证据。

[API与绘图技能覆盖审计](docs/api-skill-coverage.md)：区分底层API、MCP、技能与实机证据；同步62/25工具清单、机械尺寸工作流和TREBI电气流程。没有调用全部API，本轮未扩大默认工具范围。

[默认TREBI批量入口](docs/trebi-batch-validation.md)：新增离线规划和原生批量执行，两页保存重开、精确引用、501线号与四类报表验收通过；重复提交在预检拒绝。仅已准备的空白TREBI图页及限定IEC2符号，尚不含通用项目创建/国产选型。

[TREBI电路PDF验收](docs/trebi-pdf-validation.md)：默认PDF工具增加TREBI模式，两页全页视觉、源文件哈希、出图后独立重开及四类报表通过。273项测试通过；型号专用PLC/I/O映射待厂家资料。

[Delta R2 I/O 只读规划](docs/delta-io-planning.md)：默认入口 `plan_delta_r2_io` 已通过离线与 stdio 验证；保留端口、公共端与 PDO 来源，不分配 NC50 地址、不执行 CAD 写入。


2026-09-26：[Delta 受限批量验收](docs/delta-batch-validation.md)：默认 TREBI 入口新增 test_only R2＋指示灯配方，独立工程生成、保存重开与确切报表对照通过。318 项默认测试通过；正式国产化仍待实物、地址及元件选型确认。


2026-09-26 最新三页验证：默认批量v3接入合成DI/DO映射；14个元件/箭头、11段导线、四个跨页引用、BOM/From-To/端子报表、保存重开和三页PDF检查通过。341项默认测试通过；元件替换和通道改接仍待验证。见[三页验收](docs/delta-three-page-validation.md)。


2026-09-26 PDF导航：TREBI信号跨页引用、前后页链接和逻辑页书签已接入默认导出流程；三页保存快照验证8个内部链接、3个书签、图面渲染不变，351项默认测试通过。多触点引用及DWG超链接未覆盖。见[导航验收](docs/pdf-navigation-validation.md)。


2026-09-26 既有图修改：实验MCP灯替换、Y00→Y01改接，经保存重开、全回路线网、BOM/From-To/端子报表、带链接PDF验收。原工程未变；默认隐藏，限合成样板。363项默认测试通过。见[修改验收](docs/trebi-test-change-validation.md)。


2026-09-26 PDF清理：默认合并移除AutoCAD SHX文字弹窗批注，保留其他批注、链接和书签。样板清除125项，8个链接/3个书签与图面验证通过；365项默认测试通过。见[SHX清理](docs/pdf-shx-cleanup.md)。


2026-09-26 修改工具加固：保存前对象差异保护和写入失败停止测试通过；新副本MCP灯替换/通道改接及独立重开复核通过。374项默认测试通过。见[修改验收](docs/trebi-test-change-validation.md)。


[P0/P1 工程化进度](docs/engineering-readiness.md)：新增离线显式文件备份、新目录恢复和回执汇总入口；5文件真实工程副本哈希验证通过。尚未自动接入绘图写操作，不等于完整工程恢复验收。


2026-09-26 [统一项目工作流](docs/engineering-project-workflow.md)：默认增加项目规划/创建、独立目录恢复、版本绑定验收汇总4项工具。机械及TREBI模板创建/重开、恢复工程四类报表与缺失证据阻断已验证。443项测试通过；正式发布仍未开放，客户端桌面重启加载仍需确认。

[Delta完整端子清单](docs/delta-full-module-inventory.md)：默认规划入口v3已生成76点无地址清单；远程I/O智能符号76点已回读对应，完整回路仍待验收。


2026-09-27 [P0四路径原生验收](docs/p0-full-paths.md)：默认TREBI批量v4已验证I545/O529普通控制样板、独立插头/插座、四芯、电缆父子引用、R2共用端、保存重开及PDF；539项回归通过。R2是远程I/O；实物Revision、NC50站序/地址/PDO和工程审核仍阻断正式出图。失败现场与COM边界保留。


2026-09-27：[NC50测试地址规划](docs/nc50-test-mapping.md)接入默认plan_delta_r2_io v4，手册范围校验、起始地址变更及候选/实机绑定分离通过三个stdio会话。仅只读规划，本轮未改DWG。


2026-09-27：NC50 X256/Y256候选已接入默认四路径绘图的原生DESC说明与BOM校验，独立重开/四报表/两页PDF通过。修复COM只读查询重试和符号自带描述比较；失败批次与独立复验证据分别保留。参见NC50测试地址规划说明。


2026-09-27：NC50候选起始256→288通过独立重建、默认MCP完整批次、保存重开、原生属性/报表差异及两页PDF验收。仅三个地址说明字段改变，原256工程保留。详情见NC50测试地址规划说明；本轮未修改程序。


2026-09-27：[三线传感器路径预检](docs/sensor-path-preflight.md)接入默认批量规划v5；仅预检，完整原生绘图配方未验收，执行入口保持阻断。

2026-09-27：[三线传感器批量与回路模块](docs/sensor-path-preflight.md)v5带execution时可执行：按钮/灯/传感器器件工厂、连接器/电缆模块、供电/0V分支、跨页信号路径验收，以及自动保存重开复核。独立工程D完整通过（175步、16连接/14网络、R2 TB2:X02、四报表、重开、两页PDF）；A/B/C失败或部分回执保留不重放。audit 7/10类归入，硬件/I/O映射/工程审核仍阻断。648项测试通过。
