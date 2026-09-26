# AutoCAD 2026 API、MCP与绘图技能覆盖审计

2026-09-25：没有调用或验收全部API。当前64个MCP定义、27个默认开放、37个隐藏；默认工具也只在其样板范围内通过。最近一次产品回归273项通过；后续默认TREBI批量已完成两页实机验收，见[批量入口](trebi-batch-validation.md)。

## 四个层次

1. API：AutoCAD通用ActiveX/AutoLISP及Electrical专用函数等底层能力。Mechanical绘图主要使用通用AutoCAD能力；本项目没有实现.NET/ObjectARX桥接，也没有声称实现AutoCAD Mechanical专业工具集。
2. MCP工具：封装API供客户端调用。一个工具可能调用多个API；API调用出现于脚本不代表默认MCP已经封装。
3. 技能：告诉Codex如何选工具、组织项目规则、回读和验收。技能文本本身不执行CAD，也不证明底层接口正确。
4. 验收：合成工程的确切对象/原生报表、保存重开及需要时图面检查。单元测试、工具注册、命令提交均不能替代。

## 机械绘图

| 工作流 | 接口/工具 | 已验证范围 | 尚缺 |
| --- | --- | --- | --- |
| 基础二维轮廓/孔 | ActiveX AddLine、AddCircle、AddLightWeightPolyline；draw_line/draw_circle/draw_rectangle | 简单安装板、矩形、圆孔样板 | AddLightWeightPolyline用于矩形通过，不等于任意多段线通过 |
| 尺寸 | AddDimAligned、AddDimDiametric；add_aligned_dimension/add_diameter_dimension/get_dimension_info | 对齐/直径尺寸对象、Measurement回读与重开 | 当前非关联；角度、半径、坐标、基线/连续标注、公差未验收 |
| 圆弧/通用多段线 | draw_arc/draw_polyline有代码但默认隐藏 | 无完整实机验收 | 几何、圆弧方向、闭合、宽度等专项 |
| 编辑/剖面 | 本项目暂无已验收的专用机械流程 | 未验收 | 偏移、修剪、延伸、圆角、倒角、阵列、填充 |
| 图框/出图 | 独立双语机械图框保留 | 图框前期验收可复用 | 机械定比例、多视口、线型/线宽、完整标注样式；电气PDF不能代替 |
| 三维 | draw_box/sphere/cylinder等旧工具有代码、默认隐藏 | 无完整三维验收 | 实体编辑、布尔运算、装配等不在当前已验证范围 |

证据：[工具治理/尺寸](tool-hardening-results.md)、[双语图框](bilingual-titleblock-validation.md)；具体工具证据以[全工具清单](tool-inventory.md)为准。

## 电气绘图

| 工作流 | 主要底层接口 | 当前接入/证据 | 尚缺 |
| --- | --- | --- | --- |
| 符号及显式位号 | c:wd_insym2、c:wd_modattrval | 默认MCP；继电器/端子/部分保护器和按钮样板；显式TAG1时关闭自动生成位号 | 全符号库、通用既有元件改号、原生移动/删除后接线修复 |
| 端子接线/分支/线号 | c:ace_insert_wire、c:wd_get_wire_netlst、c:wd_putwn、c:ace_get_wnum等 | 默认MCP；正交、有限折线路由、T分支、普通/固定线号保持样板 | 任意障碍布线、复杂母线、全部线型与网络情形 |
| 跨页/父子引用 | c:ace_sig_update、c:wd_xref_doit | 默认MCP；源/目标，NO/NC样板；TREBI54/112页区引用 | 任意规模、多个INST/LOC同名位号与更复杂触点集合 |
| 项目与原生报表 | c:wd_proj_wdp_data、c:wd_bomschr、c:wd_compr_sch、c:wd_frm2_r、c:ace_termplan_r、c:wd_term_nums_rpt | 项目读取及五类报表类型有样板证据 | PLC I/O专用报表、完整端子排编辑器与柜内安装布局 |
| TREBI页号/位号/标题栏 | 规划Python模块；c:ace_GBL_wd_m、c:wd_tb_process_one等 | 默认MCP规划/批量入口，PAGE/OF、导航、位号插入及报表重开通过 | 通用项目创建、完整标题字段、实际设备选型替换流程 |
| PLC/连接器/电缆 | 有部分旧MCP工具，但未形成已验收语义流程 | 不把旧工具的存在视为完成 | 模块原生插入、I/O地址/端子、连接器针脚、电缆芯线屏蔽 |
| 安全回路 | 本轮未验证功能设计 | 无完整安全双通道设计验收 | 实际安全元件/双通道映射与独立工程核验 |
| PDF | AutoCAD原生打印与合并 | 默认工具支持限定DIN/双语/TREBI合成模板；两页TREBI电路PDF及视觉通过 | 高密度电路布局、任意图框及机械定比例打印 |

证据：[TREBI位号与标题栏](trebi-component-title-validation.md)、[父子触点](multicontact-crossing-validation.md)、[分支](branch-project-validation.md)、[PDF与目标隔离](target-pdf-isolation.md)。实际COM仍可能失败，独立复验成功不等于无故障。

## 可重复静态索引

`python -m scripts.audit_api_coverage --write`：从本机已提取work/api-2026中的c_*.html标题索引到242条c: AutoLISP函数文档；其中24个名称在src/或scripts/的文本中出现。

这24是静态文本命中，包含注释，不是24个已实测API，更不是API覆盖率。242也不是AutoCAD全部接口数量，不包含通用ActiveX/.NET/ObjectARX与其他命名前缀。缺少静态名称也不能证明过去从未手动调用。逐项静态索引位于私有work/acceptance/api-coverage/static-api-index.json，实际验收应查上述独立证据。

该脚本同时从profiles/tool-capabilities.json重建工具清单，修正旧清单61/24数量及PDF旧限制描述，避免文档与工具策略分离维护。不会调用AutoCAD或改变工具开放策略。

## 技能落地与下一轮顺序

仓库中的skills/autocad-electrical/SKILL.md已连接TREBI准备、原生接线、精确引用及报表流程；skills/autocad-mechanical/SKILL.md已补齐实际尺寸工具、非关联限制与机械打印边界。它们由本项目AGENTS.md引用，仍不是已安装到全局目录、可被任意客户端自动发现的独立技能包。

后续按实际任务补齐，避免为了数量盲目执行修改型API：

1. 电气：默认MCP批量入口已在准备好的空白图页通过两页验收；小项目PDF全页检查已通过，后续补通用项目准备入口。
2. 电气：PLC模块/I/O、连接器/电缆、端子排与选型替换分别建立最小样板及原生报表验收。
3. 机械：先补圆弧/通用多段线和必要编辑操作，接着完成关联/补充尺寸、填充和固定比例打印。
4. 每批通过对象回读、保存重开及相应报表或图面验收后再扩大默认工具范围。
