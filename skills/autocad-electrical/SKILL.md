---
name: autocad-electrical
description: 在本项目中通过 MCP 与 Computer Use 创建、修改及核验 AutoCAD Electrical 电气工程，适用于原生元件、端子接线、线号、交叉引用、项目报表与TREBI规则。
---

# Electrical 工程工作流

按[API与技能覆盖](../../docs/api-skill-coverage.md)和[工具清单](../../docs/tool-inventory.md)选择操作。技能、配置、MCP定义、底层API与实机验收分别看待；profiles/autocad-electrical-2026.yaml仍是环境草案，不代表运行时约束。

## TREBI项目准备

读[图页清单](../../docs/trebi-page-manifest.md)与[位号/标题栏验收](../../docs/trebi-component-title-validation.md)。先建立有效图页和完整设备清单；默认plan_trebi_batch可离线预检限定配方，execute_trebi_batch在已准备并打开保存的空白TREBI工程页串联原生操作。参数样例、准备条件和失败处理见[批量入口](../../docs/trebi-batch-validation.md)。已有内容的正式图页会被拒绝；规划不扫描DWG位号、不自动选型。只读CLI scripts.plan_trebi_components仍支持独立清单规划。

PAGE是逻辑地址，OF来自明确纳入的有效图页；附件不计入，前后页按清单顺序。主元件按所属功能页编号，异页触点继承主元件位号；existing_tag保留，独立端子排/电缆使用明确编号。规划器不自动收集既有DWG全部位号，需先完整登记才能避免重号。

电气使用profiles/trebi-electrical-a3.json的底部整行图框，机械模板另保留。标题栏PAGE/OF已通过WDT原生更新、导航通过明确属性更新；LINE20必须与有效图页数一致。默认批量的两页样板已通过保存重开及报表验收；通用项目创建、完整标题栏字段仍需专项验收；两页电路PDF已通过视觉/重开/报表检查。

## 原生绘图与回读

使用get_symbol_list查询真实库；insert_electrical_symbol插入已确认符号并传入计划位号。内部对显式TAG1/TAGSTRIP关闭自动位号生成，防止TAG1与VIA_WD_BASETAG不同；既有元件改号不是这项插入能力。

get_electrical_connections读取接线属性，connect_electrical_terminals连接；不要把块插入点、端子描述文字或线条视觉接触当作原生电气连接。分支只在已验收范围使用branch_electrical_terminal_to_wire。set_electrical_wire_number后用get_electrical_wire核对线号、端点和网络。

源/目标箭头用update_electrical_signals，线圈/触点用update_electrical_cross_references；后者当前要求项目图纸均已打开且保存。更新后检查双向确切引用，不仅检查非空。TREBI的电位名、PLC地址、针脚与页区引用分开，不能统称为线号。

export_electrical_project_report可导出已验收的原生BOM、元件、From-To、端子计划和端子线号报表；按已知项目清单核对内容。export_electrical_project_pdf支持synthetic_trebi_a3，打印前核对逻辑PAGE/OF、原生分区和项目导航；保留逻辑页号，PDF顺序另标。两页样板已通过，更多页或高密度电路仍需全页渲染检查；机械定比例出图另验收。见[PDF验收](../../docs/trebi-pdf-validation.md)。

写操作传expected_drawing_path；确认目标实例时传expected_instance_hwnd。MCP与UI串行；需要对话框先读取本机Computer Use技能。结果未知时用get_execution_diagnostics及实际对象/原生回执核对，不重放写入；本机COM仍可能拒绝调用。

PLC模块、完整I/O映射、连接器/电缆芯线、柜内布局与安全双通道尚未完整验收。Delta CNC/远程I/O输入见[资料清单](../../docs/delta-cnc-io-intake.md)。未知型号或引脚标待核实；不通过普通几何或文字伪造Electrical语义。最终验收包括保存重开、确切跨引用、接线及BOM报表，出图时另做全页视觉检查。


TREBI PDF导航：synthetic_trebi_a3默认按原生信号XREF及标题PREV/NEXT边界生成内部跳转，按逻辑页清单解析目标，附PAGE书签；不可将逻辑页号当PDF页序。当前仅单一page.zone信号引用，不自动链接PLC POSITION或多项触点引用。无法唯一识别打印图框或目标页缺失时拒绝生成。证据见[导航验收](../../docs/pdf-navigation-validation.md)。


## 工程化入口

新工程先调用plan_cad_project，再按同一规格调用create_cad_project；必须明确机械/电气模板、输出根目录、逻辑页及电气base_project，不使用临时命令替代已提供入口。创建只产生草案，生产用途未开放。使用[统一工作流](../../docs/engineering-project-workflow.md)了解参数与验收边界。

默认批量与实验修改已有写入前备份。中断后先检查诊断和回执；需要恢复时用restore_cad_project生成独立目录及新项目名，再做保存重开、线网和报表核验。不要覆盖失败现场或盲目重放。其他底层写工具未自动全覆盖备份。

调用audit_cad_project汇总当前版本的证据。未知硬件、地址、连接或缺失证据必须作为阻断；全部证据齐备仍需工程审核，不得把evidence_complete称为可施工批准。正式PDF发布尚不支持。


## 扩展符号和中断恢复

按[扩展验收](../../docs/extended-electrical-acceptance.md)区分样板与正式能力。实验连接器仅为合并P/J；实验PLC固定AB 1771-IAD，不是Delta。电缆号、芯号、针脚、PLC地址分栏回读。双网络端点隔离不代表实际安全双通道认证或功能通过。

标准MCP中断先诊断，再调用recover_cad_interruption的inspect，核对操作记录、已执行对象、DWG和实例；只有快照与预期一致才用同一operation_id/snapshot_id执行release。工具不会重放、保存或撤销；未保存/复杂实体现场被拒绝时保持隔离。禁止为通过恢复擅自保存用户未知改动。两步细则见[恢复说明](../../docs/interruption-recovery.md)。
