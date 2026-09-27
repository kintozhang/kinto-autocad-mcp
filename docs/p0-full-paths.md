# P0 完整普通控制路径

2026-09-27。默认工具数量不变，通过 `plan_trebi_batch` / `execute_trebi_batch` 扩展 schema_version=4、recipe=remote_io_button_lamp_paths、purpose=test_only。本版本固定逻辑页102/300，支持一台PNP R2的Port0/X00输入和Port2/Y00继电器输出样板；不是全通道任意布线或正式选型器。

## 数据与约束

在v3公共字段schema_version、recipe、purpose、manifest、symbol_path、mapping之外，增加routes和binding。完整测试规格保存在CAD输出目录，不将原始图纸资料放入公开示例。

routes恰好四项：button_supply、button_return、lamp_feed、lamp_return。每项必须有id、original、strip、terminal、cable、core、socket、plug、socket_pin、plug_pin、device、device_terminal、source。同一电缆的芯号、端子、连接器针脚不得重复；插头插座为不同对象，配对针号一致；按钮13/14、灯1/2逐项检查。原信号、电位、线号、物理通道和NC50地址分别保存。

binding包含controller=NC50E-FE、protocol=EtherCAT、ss_potential=TEST_0V、output_common_potential=TEST_24V、source，以及observations中的BUTTON/LAMP。每个观察值可为空；非空时须有object_index、subindex、bit、plc_address、source，必须匹配端口/通道和明确填写的NC50地址。输入模式本版固定PNP，S/S为0V；C0为测试24V。未知实物Revision、站序、地址或PDO位观察允许测试，阻止正式出图。匹配用户提供的观察记录不等于已在线读取硬件。

## 原生执行

插头和插座使用c:ace_ins_parametric_connector的4/8选项分别插入，再核对真实TERM与X?TERM属性。2026本机的type=2弹出not implemented，不调用该选项。两侧是独立智能元件；其配对为显式声明，不伪造导线短接两半，也不声称原生自动管理所有配对关系。

使用原生垂直按钮、指示灯、端子和信号箭头，原生接线/线号；导线生成后插入HW01/HW02电缆父子标记，回读芯号并更新引用。最终验证76个R2接点、完整元件清单、逐导线网络（包括非预期端点）、精确页区引用、四芯From/To、BOM零件与数量、端子报表。

成功批次生成同名.wdp旁的.p0.json，绑定项目/DWG哈希与原始回执哈希。audit_cad_project自动发现并重新计算P0结果；变更DWG/回执、未知硬件绑定或缺独立验收均阻断。保存重开、PDF视觉和工程复核仍分别提供证据；该工具不会给出可施工批准。

## 验收状态

R7完整默认MCP批次、独立保存重开、四类原生报表和两页PDF检查通过。539项离线回归通过，3项integration排除；离线测试不能替代实机证据。实物/NC50绑定和工程审核仍阻断正式出图。

## 中断原则

首次失败现场单独保留。命令失败后不重放；只有核对目标和已执行对象后才能解除保护。创建与批量保存前等待目标稳定空闲；统一AutoLISP桥接在提交前和回执后确认目标空闲。同一页不重复激活，不反复设置同一个当前项目，已匹配的v4空白图框不重复改写。接线点采用单次属性枚举，完整接线点/线网快照可有限重读；SendCommand仅对方法查找重试，命令调用不重放。完整批次最长1800秒，逐步回执仍持续保存。此改动降低无必要COM切换，不保证所有COM故障消失。


## 原生连接器回读差异

本机R4复现：插入电缆标记后，wd_get_wire_netlst的wlst同时包含两段导线，但cmpconlst漏报参数化插座；刷新WD_M无效。原生From/To能准确返回两端及电缆芯。P0保留原始cmpconlst，对连接器路径另外要求：仅一行From/To关联该线网、两侧导线句柄均在原生wlst、元件句柄/位号/针脚完整一致、线号与两侧图层一致、无额外原生端点。不是根据几何邻近或计划补造连接。

R4已保存的诊断图通过四路径和四类报表核验；这只是诊断回读，不是独立重开，也没有覆盖原失败批次状态。R5默认批次停在交叉引用更新前的只读快照，submitted=false；已保存接线不重放。该快照及空白页元数据检查已补充有限只读重试，R6承担完整流程复验。


只读忙碌补充：交叉引用快照按整个快照有限重读，不能返回半份属性；空白页预检查的文档枚举、对象清单和属性映射同样有限重读。创建入口跳过已保存图纸的冗余Save。只读重读耗尽仍失败停止；不重放插入、接线、保存或引用更新命令。


R6在S/S接线步骤遇到COM读取中断，现场已另存，不据空created_wire_handles断言未提交。已集中审查并补齐原生WD_M扫描、既有导线扫描、接点对象查找、插线后对象核验、线号前对象检查和最终元件清单的有限只读重读；连接失败回执增加phase/write_attempted。故障注入证明接线后回读忙碌不会重复ace_insert_wire；写入异常仍停止。完整回归529项通过，实机完整批次以R7最终回执为准。


PDF衔接补充：新建DWT的修订、签署等草稿字段可为空。仅synthetic_trebi_a3导出允许明确列举的十项元数据留空，并返回draft_title_metadata_pending；不伪造签署、修订或客户信息，图面保留测试水印。BRAND、PAGE、OF、PREV、NEXT及所有字段的类型/长度仍校验，普通标题校验默认保持严格。打开打印副本后重新取得就绪的文档对象；对已识别的GetAttributes.TagString/TextString元数据短暂未就绪做有限只读重读，其他AttributeError不吞掉。电缆引用MText的恢复探针也已补齐。539项回归通过；完整PDF结果以最终证据为准。


## 最终独立样板 R7

工程：`C:\kinto\CAD_Projects\TREBI_Localization\electrical\poc\P0-PATHS-R7-20260927`。代码绘图版本c466348、PDF导出版本a259203；仅测试普通控制四路径。18个元件/箭头加4个电缆标记，17组线网，76个R2接点，插头与插座各4针。原生报表行数：{"bom": 6, "from_to": 15, "terminal_plan": 9, "terminal_numbers": 9}。保存关闭重开后，四类报表逐行多重集一致，源WDP/DWG哈希未变化；PDF保留逻辑PAGE102/300与OF2，PDF含6个内部链接、2个书签、0个SHX文字批注；两页均完成视觉检查。10种修订/客户/签字等草稿字段仍为空，不代表已签发。

证据统一放在工程evidence/、reports/和exports/；同名.p0.json指向该目录的batch-receipt.json，不依赖代码目录work/的临时回执。audit_cad_project自动重算P0路径证据；七类自动/视觉证据归档，硬件身份、完整I/O绑定与工程审核仍待补齐，production_ready/formal_export_allowed均为false。

这不是全TREBI项目、NC50程序逻辑或安全回路验收；没有冻结真实通道分配。R1-R6失败记录保留，不能把R7成功解释为COM永不失败。客户端重新启动MCP后加载当前代码；默认工具仍33项、全部定义73项，本轮扩展既有批量入口。
