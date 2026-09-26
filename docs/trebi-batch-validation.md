# TREBI 默认 MCP 批量入口

2026-09-25：新增 `plan_trebi_batch` 与 `execute_trebi_batch`。当前64项工具定义、27项默认开放、37项隐藏；262项默认测试通过、3项旧integration测试未运行。

## 使用与范围

配方见 [两页合成样例](../examples/trebi-batch.json)。先调用 `plan_trebi_batch(spec)`，检查逻辑页清单、有效总页数、主元件位号、继承位号和精确引用。这个入口不连接CAD，也不扫描既有工程、选择国产替代型号或判断器件兼容性。

再调用 `execute_trebi_batch(project_path, spec, drawing_path, expected_drawing_path, expected_instance_hwnd)`。路径使用本机绝对路径；drawing_path必须是当前活动图页，expected参数来自实际连接状态。spec仍传完整配方，执行端重新预检。

执行入口要求已创建WDP，所有目标页已打开并保存，每页模型空间仅有WD_M和KINTO_TREBI_ELECTRICAL_A3两个块。WDP成员及顺序必须与有效图页清单完全相同，项目同名WDT必须与profiles/trebi-electrical-a3.wdt相同，LINE20须等于有效图页数量。本轮建项目/复制空白种子的准备过程仍由验收脚本完成，尚未封装进默认批量入口。

本版最多8页、48个符号、48条连接；实机证据覆盖两页6符号2条连接。支持IEC2中的HCR1继电器、HCR21常开触点、HT0001端子、HA1S1/HA1D3跨页箭头；每个主元件最多一个常开子触点。坐标位于可用图面，水平连接须间隔至少20图形单位、接线点相向；这是本版配方约束，不代表通用布线器。符号库当前绑定已验收的2026本机IEC2路径。

主元件由owner_page生成位号，子触点跨页继承；保留existing_tag。端子排和针脚显式提供，不与元件位号或线号混用。PAGE采用逻辑页号，OF由有效图页计数，PREV/NEXT采用清单顺序。电气底部整行图框与机械模板分别保留。

## 执行顺序和失败行为

整批结构/文件/图页预检 → 原生页区与标题栏 → 父元件及子元件/端子/箭头 → 接线/线号 → 保存 → 跨页及父子引用 → 精确属性与线号回读 → 保存 → 四类原生报表 → 恢复原活动图页。

整个写批次共用跨客户端锁、一个独立STA工作进程和600秒上限；每页切换后重新绑定目标并核对项目。每个阶段在提交前记入work/batches/<id>/report.json，完成后再记回执。失败立即停止，不自动重放或宣称回滚。超时/部分失败保留隔离标记，用get_execution_diagnostics与批次回执调查。明确submitted=false的批次预检拒绝正常释放锁。

重复配方在已填充图页上被拒绝；这只是防止重复写入的保护，不是可断点重放的事务系统。工具success代表本轮原生回读成功，保存重开和报表内容应独立核验；PDF另需视觉检查。

## 实机证据

通过默认stdio MCP（KINTO_MCP_EXPERIMENTAL=0）实际调用规划与执行两个新入口，47个执行阶段完成，未发生本轮写入重试或隔离恢复。

- 工程：work/projects/trebi-batch-20260925-110804/
- 批次回执：work/batches/fac8810046c4435c823e8cb8ba5a0c54/report.json
- 原始MCP结果：工程目录execute_trebi_batch.json、plan_trebi_batch.json
- 重复提交拒绝：工程目录replay-rejection.json（submitted=false）
- 独立重开/报表：工程目录reverification-111022/report.json，PASS

两页PAGE分别54、112，OF均为2，前后页对应清单。线圈和子触点均为-112K1；子触点引用112.8，线圈引用54.5；源箭头112.8、目标箭头54.2，线号501两端读回。关闭重开后属性、页区设置及标题栏一致。

BOM为1个RELAY_DEMO和2个TERMINAL_DEMO；From/To只有1条501连接，端点-X54:1/-X112:1，逻辑页54/112；端子计划与端子线号各2行，501一致。执行后隔离标记为空。

复现：`python -m scripts.trebi_batch_smoke --write`创建独立合成副本，再运行`python -m scripts.verify_trebi_native_grid <新工程目录>`。不要把生产工程传给验收脚本。

## 实际调用的 API

MCP负责工具协议和业务封装，COM/ActiveX负责本机连接、文档/对象访问与命令提交。Electrical专用能力已通过其原生AutoLISP API调用：

| 工作 | 原生接口示例 |
| --- | --- |
| 智能符号/属性 | c:wd_insym2、c:wd_modattrval |
| 导线/线号 | c:ace_insert_wire、c:wd_putwn |
| 跨页/父子引用 | c:ace_sig_update、c:wd_xref_doit |
| 页区/标题栏 | c:ace_GBL_wd_m、c:wd_tb_process_one |
| 报表 | c:wd_bomschr、c:wd_frm2_r、c:ace_termplan_r、c:wd_term_nums_rpt |

接口签名依据本机2026的ACE_API帮助及合成工程回读。API调用不需要模型API key，模型仍由Codex/Claude订阅客户端提供。本项目尚无自定义.NET/ObjectARX插件，也没有调用或验收全部API。机械基础图元和尺寸目前使用通用AutoCAD ActiveX API。

下一步：TREBI电路PDF与全页视觉检查；随后分别建立PLC/I/O、连接器/电缆和国产型号替换的最小样板。当前不承诺153页原图自动重建、完整安全回路设计或施工图审查。
