# 能力与验证状态

**当前基线（2026-09-26）：73项定义、33项默认、40项隐藏；473项默认测试通过。**

最新[扩展电气样板与恢复验收](extended-electrical-acceptance.md)记录连接器、电缆、通用PLC、灯片段及双网络的具体边界。恢复工具已通过两次真实中断现场，不能自动回滚任意图纸。

新增独立STA工作进程、调用时限、失败隔离和只读诊断。见[执行隔离验收](execution-isolation.md)。下方按日期追加的旧记录是历史快照，以最新专项说明为准。

联调状态：2026 COM/MCP 查询和基础二维几何已通过；Electrical 原生插入、正式端子连接、线号及保存重开已通过单图样板验收。
配置文件、文档及技能不构成运行时保护措施。

| 能力 | 当前代码 | 验证/缺口 |
| --- | --- | --- |
| MCP stdio | src/server.py | stdio 初始化、列工具、真实查询和基础二维调用通过 |
| COM、活动文档查询 | src/autocad/connection.py | 2026 活动实例和图纸查询通过；通用多实例/多文档保护待实现 |
| 2026 检测 | 上游 detector.py | 版本表仍以旧版为主，待适配 |
| 基础二维/三维图元 | drawing.py / drawing3d.py | 直线、矩形、圆、文本、缩放及保存重开已验证；其他几何/3D未验证 |
| 符号插入 | electrical.py | 已替换为 c:wd_insym2；HCR1、HT0001及属性回读通过 |
| 元件间接线 | native_electrical.py / wires.py | 新 connect_electrical_terminals 两端原生线网通过；旧 wires.py 工具仍不作证明 |
| 线号/交叉引用 | native_electrical.py / electrical.py | 新 set_electrical_wire_number 与只读 get_electrical_wire 通过；源/目标跨页引用通过两页项目验收；父子常开触点已通过三页 MCP 样板验收，复杂匹配待验证 |
| 报表 | native_project.py / reports.py | 新原生项目BOM、元件表、From/To通过；旧扫描报表仍为实验能力 |
| 操作 ID、完成回执 | lisp_bridge.py | 每表达式回执、跨客户端锁、独立工作进程及操作日志已实现 |
| 目标文档检查及写入恢复 | lisp_bridge.py | 已增加工作进程绑定/前后检查与超时隔离；全工具严格绑定、回滚和自动恢复仍未完成 |
| 2026 profile 自动加载 | 未实现 | 当前只保存规格 |
| 尺寸标注、布局/PDF | dimensions.py | 对齐/直径尺寸与保存重开已验收，非关联；三页 DIN A3 合成 PDF 已验收；其他布局/定比例未验收 |

Computer Use 由 Codex 现有插件提供，不嵌入 Python 服务、不调用 Computer Use API。
[本机联调记录](live-validation-20260924.md)包含证据与验证边界。

[原生 Electrical 验收详情](native-electrical-validation-20260924.md)。单图验收后已完成[两页项目验收](project-validation-20260924.md)：WDP、信号跨页、BOM、元件表和From/To通过；真实工程未验收。

## 工具默认集与机械标注

[本轮治理结果](tool-hardening-results.md)：61项定义中24项默认提供，37项隐藏；详见[逐项清单](tool-inventory.md)。符号查询已读取真实文件；旧中心连线及直接移动/删除已停用。原生对齐/直径标注已通过机械样板及保存重开，非关联；合成电气三页 PDF 已验收，机械定比例待验收。


2026-09-24 后续专项：已有原生报表工具新增 `terminal_plan`、`terminal_numbers`，独立三页工程通过 MCP 报表与保存重开回读；父子引用尚为原生 API 验证。详见 [专项验收](contact-terminal-validation.md)。导线返回结果现逐段校验网络，异常不再误报成功。


最新加固见 [接线与父子引用](wire-xref-hardening.md)：默认增加父子引用工具；已对齐接线选项修复通过新的 MCP 重建、保存重开及报表验收；新增过期项目上下文检查。


[常闭、双触点与交叉线专项](multicontact-crossing-validation.md)：NO/NC 双触点、两组折线、交叉电气隔离及保存重开通过独立验证；一次 COM 瞬时断连的失败调用保留，由只读确认后的独立验收完成核对。T 形分支和通用恢复仍待完善。


[最新 T 分支与 PDF 专项](branch-pdf-validation.md)：默认分支工具及顺序重复连接预检已验收；单页 A3 原生出图加 PDF 规范化、渲染通过。当前默认23项，97项测试通过；多页/固定比例出图、跨客户端并发与分支项目报表仍待验证。


[双分支项目报表验收](branch-project-validation.md)：修复新增分支接线点线号缓存未更新的问题；普通/固定501、四端子双分支、原生BOM与端子/From-To报表、保存重开均通过。默认仍23项，111项测试通过。

[三页 PDF 验收](multipage-pdf-validation.md)：按 WDP 顺序导出独立副本，三页 A3 PDF 合并结构及逐页视觉检查通过。当前为 CLI 验收脚本，非默认 MCP 工具；中英图框、固定比例机械打印及多布局未验收。116项默认测试通过，7项可选 PDF 测试另行通过。

[默认 MCP PDF 验收](mcp-pdf-validation.md)：61项定义、24项默认、37项隐藏。三页合成 DIN A3 出图及逐页视觉通过；后续 COM 枚举异常后独立完成重开线网/报表验收。131项测试通过。仅 synthetic_din_a3 模式；中英模板和定比例机械打印待验收。

[双语标题栏验收](bilingual-titleblock-validation.md)：synthetic_zh_en_a3 模式已通过三页中文 PDF 检查、字段与字体保存重开及原生报表校验。仅标题栏双语，未翻译整图说明；WD_TB 自动映射和正式图框待实现。136项测试通过，默认工具仍24项。

[COM 加固与 WDT 映射](com-stability-title-mapping.md)：忙碌状态保留连接，核心只读操作有限重试，打印使用目标就绪检查；20次切换及单次写入/重开通过。原生WDT项目名/版本/页码三页验证通过；148项测试通过，默认仍24项。不是全部COM路径无故障保证。

[跨客户端互斥验收](client-concurrency.md)：新版MCP工具调用共用进程间锁，冲突请求在执行前拒绝，中断标记持续拦截；独立副本画圆及保存重开通过。152项测试通过，默认仍24项；旧服务需重新连接，UI/直接COM不受此锁约束。

[统一目标参数与隔离PDF复验](target-pdf-isolation.md)：错误DWG/实例在进入工具前拒绝；三页双语PDF、逐页视觉、源图哈希及独立重开报表通过。170项测试通过，默认仍25项。

[TREBI电气模板与规则](trebi-template-rules.md)：保留机械图框，新建底部整行电气标题栏及0..9分区；空白DWG回读/保存重开和原生PDF通过。后续原生页区引用验收见下。

[TREBI 原生页区引用验收](trebi-native-grid-validation.md)：两页54/112的导线、线圈/触点引用与线号501保存重开通过，四类原生报表一致。修正显式位号插入时保留旧基础位号的问题，增加COM打开方法查找重试。193项测试通过，默认25项；新电路PDF、WDT映射及完整TREBI语义仍待验证。

[TREBI有效图页清单](trebi-page-manifest.md)：按显式有效图页计算OF、生成PAGE/PREV/NEXT，配置功能页分组并校验引用目标。215项测试通过；本轮离线规则验证，尚未自动写入WDT/DWG。

[TREBI位号与标题栏联调](trebi-component-title-validation.md)：按所属页生成主元件位号，异页触点继承；新电气图框PAGE/OF原生WDT及清单导航通过两页保存重开和四类报表独立复验。244项测试通过；内部规划/验收接口，默认工具仍25项。COM拒绝调用发生过，保留失败与恢复证据。

[API与绘图技能覆盖审计](api-skill-coverage.md)：区分底层API、MCP、技能与实机证据；同步62/25工具清单、机械尺寸工作流和TREBI电气流程。没有调用全部API，本轮未扩大默认工具范围。

[默认TREBI批量入口](trebi-batch-validation.md)：64项定义/27项默认；两页原生批量、重开及四类报表通过，262项测试通过。仅已准备空白图页和限定IEC2符号；PLC/国产选型与新电路PDF另验收。

[TREBI电路PDF验收](trebi-pdf-validation.md)：默认PDF工具增加TREBI模式，两页全页视觉、源文件哈希、出图后独立重开及四类报表通过。273项测试通过；型号专用PLC/I/O映射待厂家资料。

[Delta R2 I/O 只读规划](delta-io-planning.md)：默认入口 `plan_delta_r2_io` 已通过离线与 stdio 验证；保留端口、公共端与 PDO 来源，不分配 NC50 地址、不执行 CAD 写入。


2026-09-26：[Delta 受限批量验收](delta-batch-validation.md)：默认 TREBI 入口新增 test_only R2＋指示灯配方，独立工程生成、保存重开与确切报表对照通过。318 项默认测试通过；正式国产化仍待实物、地址及元件选型确认。


2026-09-26 最新三页验证：默认批量v3接入合成DI/DO映射；14个元件/箭头、11段导线、四个跨页引用、BOM/From-To/端子报表、保存重开和三页PDF检查通过。341项默认测试通过；元件替换和通道改接仍待验证。见[三页验收](delta-three-page-validation.md)。


2026-09-26 PDF导航：TREBI信号跨页引用、前后页链接和逻辑页书签已接入默认导出流程；三页保存快照验证8个内部链接、3个书签、图面渲染不变，351项默认测试通过。多触点引用及DWG超链接未覆盖。见[导航验收](pdf-navigation-validation.md)。


2026-09-26 既有图修改：实验MCP灯替换、Y00→Y01改接，经保存重开、全回路线网、BOM/From-To/端子报表、带链接PDF验收。原工程未变；默认隐藏，限合成样板。363项默认测试通过。见[修改验收](trebi-test-change-validation.md)。


2026-09-26 PDF清理：默认合并移除AutoCAD SHX文字弹窗批注，保留其他批注、链接和书签。样板清除125项，8个链接/3个书签与图面验证通过；365项默认测试通过。见[SHX清理](pdf-shx-cleanup.md)。


2026-09-26 修改工具加固：保存前对象差异保护和写入失败停止测试通过；新副本MCP灯替换/通道改接及独立重开复核通过。374项默认测试通过。见[修改验收](trebi-test-change-validation.md)。


[P0/P1 工程化进度](engineering-readiness.md)：离线备份/新目录恢复和执行回执汇总已实现，尚未自动接入写工具；项目创建、客户端重启与正式验收报告待完成。


2026-09-26 [统一项目工作流](engineering-project-workflow.md)：默认增加项目规划/创建、独立目录恢复、版本绑定验收汇总4项工具。机械及TREBI模板创建/重开、恢复工程四类报表与缺失证据阻断已验证。443项测试通过；正式发布仍未开放，客户端桌面重启加载仍需确认。
