# 暂停断点：传感器批量／回路复用／验收（2026-09-27）

## 最新状态（2026-09-27 晚，Claude Desktop续做）：步骤1–8已完成

- 完整回归648通过（638+信号箭头路径10项）。
- C批次148/149步完成，失败于`verify_full_paths`：v5验收对信号箭头要求针脚身份。已在`delta_path_acceptance.py`新增`verify_signal_path`修复；C回执离线复算通过。C保留不重放。
- **D工程`SENSOR-FULL-20260927-D`完整通过**：175/175步，`native_readback_verified`，save_reopen verified；16连接/14网络，-X15:I546→-301A1:TB2:X02。回执`work/batches/3aac660c4a6c49d3b8853393decabaf0/report.json`。
- 两页PDF结构与视觉核对通过；audit 7/10类归入，硬件/I/O映射/工程审核及P0绑定仍阻断。证据副本在D/evidence。
- 已更新README、tool-capabilities（及生成的tool-inventory）、electrical SKILL、sensor-path-preflight。
- 剩余：Wiki同步、提交并推送private main（需用户确认）。
- 项目上下文坑：项目管理器"激活"不刷新图纸内`c:wd_proj_wdp_data`缓存；须在目标图内`(c:wd_makeproj_current ...)`再读回。

以下为暂停时原始记录。

用户因额度将用尽要求暂停，待额度刷新后继续。**不要自动继续绘图**；下一次明确继续后按本文恢复。当前修改已在磁盘，尚未提交或推送；私有仓库上次提交为2fdbb3e。

## 目标和边界

用户授权完成三项：补齐传感器批量执行；把已验证按钮、灯、传感器等整理为可复用模块；接入备份、失败回执、保存重开及统一验收。仅独立合成测试，不启动正式国产化工程，不改raw资料。

## 代码现状（尚未完成原生全流程验收）

- `src/tools/circuit_blocks.py`：按钮/灯/三线传感器器件工厂、连接器/电缆模块、信号源目标引用、装配校验、实际分支线段选择、同名已打开图纸检查。
- `delta_full_paths.py`旧v4复用器件与电缆模块；`delta_sensor_paths.py`v5不带execution仍只读，带execution调用新`sensor_circuit.py`。
- execution字段为`symbol_path`与`shared_loads`。固定已验证R2资产SHA不变；输入仅Port0通道0–2。manifest两页可配置，传感器位号跟随现场页。共享按钮/灯另一端接测试边界，不等于完整I545/O529控制链。
- `trebi_batch.py`增加分支执行、v5完整原生检查、自动保存重开复核；仍修改前备份、持久逐步回执，失败不重放。加入批次开始时同名DWG检查。
- `delta_path_acceptance.py`从真实From/To句柄、针脚和线网成员证明分支连通，不把计划端点冒充回读；支持3芯/4芯。v5证据必须带独立重开快照。
- `batch_reopen.py`只关闭本批次已保存、非只读图；重开读对象/线网/四报表并验收，检查磁盘哈希未变。**实际自动重开尚未跑到，需继续验证。**
- `project_acceptance.py`可从重算通过的.p0证据归入位号/连接/引用/BOM/端子；v5另归入重开。硬件、地址、PDF和工程审核仍独立阻断。
- 恢复快照新增AcDbArc与AcDbPolyline完整几何，已实际inspect/release；只读子进程上限25→60秒，实际两次快照约40–46秒。
- isolated.py修正仅预检v5返回qualification_required且submitted=false时不错误隔离；已提交/未知仍隔离。

测试：最近完整回归 **636 passed, 3 deselected**，之后新增器件工厂与同名预检两个测试，相关局部测试通过（最新50通过）。预期完整数量638，**未重新全跑，不要写成638已通过**。工厂提取曾出现局部device变量遮蔽，已改为device_component并通过相关93项测试。

## 实际工程与失败证据

输出根 `C:/kinto/CAD_Projects/TREBI_Localization/electrical/poc`。

### A：SENSOR-FULL-20260927-A

默认create和execute调用。批次回执：
`C:/kinto/Autocad-mcp/work/batches/17754e59c09044c1bb8fc1cdee8d1821/report.json`

供电分支通过；0V分支预设tap(280,200)不在实际自动绕线路径上，分支未提交。实际0V首段x197..278.5、y200，随后绕至y193.75，并有跨线圆弧。灯改为x240，tap(240,200)。A两张图均已保存保留，随后关闭以避免同名冲突。

标准恢复操作18f47c76c03a4fb880d186aa3769bbba，快照f1c2583a120345a79041b2a56f8cf97f，已release；没有重放。该现场推动了圆弧/多段线支持和60秒只读超时。

### B：SENSOR-FULL-20260927-B

通过默认restore从A修改前备份恢复，WDP改名B，DWG仍叫A-102/A-300。回执：
`C:/kinto/Autocad-mcp/work/batches/204c18beef39421ebfc735297869e492/report.json`

全部16项连接检查所需绘图已提交；供电和0V两个三端点分支均原生通过，三个电缆标记已插入，信号引用更新与保存完成。

失败于parent_child_references：A、B同时打开且DWG同名，原生引用更新拒绝，**submitted=false**。不是引用已更新，也不是全图验收通过。已把同名检查提前到批次开始。A已关闭，B保留已保存状态。B现场页14个元件属性与计划逐项核对后，标准恢复操作041feccf8f3f46729899df62b1512dff、快照eab1c4b58bc54c29b61621b35441d384已release。

### C：SENSOR-FULL-20260927-C（暂停时正在创建空白工程）

唯一新文件名，测试参数改为逻辑页103/301、传感器-103B2、R2 Port0通道2/TB2:X02。原始信号仍I546，NC50地址与硬件仍未知。

规格：`work/sensor-batch-20260927/spec-c.json`。
第一次创建在提交前因B图的项目上下文过期被拒绝，确认C目录不存在后显式激活B WDP，再调用create。请求`create-c.json`，结果`create-c-result-v2.json`。创建结束将恢复B原图/原项目，不能直接假设C活动。

**C尚未执行绘图批次。** 创建最终状态见本文件末尾补记。

## 继续步骤

1. 读AGENTS、本文，git status保留所有改动；核实C的`evidence/create-project.json`与本地create-c-result-v2.json，确认没有工作进程还在运行。检查诊断仅打印marker/最近指定操作摘要，别输出全部历史。
2. 跑`.venv/Scripts/python.exe -m pytest -m "not integration"`。确认无代码问题。
3. C创建成功后，明确激活`.../C/drawings/SENSOR-FULL-20260927-C-103.dwg`及`.../C/drawings/SENSOR-FULL-20260927-C.wdp`（实际目录名SENSOR-FULL-20260927-C）。两图已打开保存；用spec-c通过默认execute_trebi_batch。不要重跑A/B。
4. 现有stdio驱动：`.venv/Scripts/python.exe work/p0_call.py 请求.json 结果.json`，默认KINTO_MCP_EXPERIMENTAL=0。执行最长1800秒，客户端1900秒；用持续回执看进度，CAD串行。需要新请求execute-c.json，参数project_path/drawing_path/expected_drawing_path/spec。
5. 重点核对电缆父子精确引用、16项连接/14个独立网络预期、三芯From/To、BOM、R2输入X02；数字以实际结果为准。独立重开与原生报表验证当前未完成；出现问题保留回执，不能把部分成功算完整。
6. 若成功，用默认PDF导出synthetic_trebi_a3；PDF技能渲染两页检查布局、PAGE103/301、OF2、导航与无SHX弹窗。灯/按钮短导线处自动线号可能带引线，需要视觉核验。
7. 默认audit_cad_project验证.p0证据自动归入六类，硬件/地址/工程审核继续阻断。证据复制至外部CAD工程evidence，别放raw。
8. 更新README、capabilities、electrical SKILL末尾的旧“v5只读”说明和docs/sensor-path-preflight.md，写清真实通过范围与剩余限制；同步Wiki页/索引/log。
9. 检查差异，提交已验收代码并只推送private main。当前新代码**未归档同步**，不能宣称已交付完整版本。

## 工具与目录提示

仓库写入/外部CAD目录/COM需exec_command require_escalated，用户已授权。Wiki工作区可直接写。不要生成API key或调用硬件控制。

MCP创建后的项目选择需同时切DWG与Electrical WDP。直接COM用于明确目标激活：get_connection、wait_for_document、evaluate `(c:wd_makeproj_current ...)`；有隔离锁先检查/恢复，不能手删锁。

批次会持久记录步骤，不要读取全get_execution_diagnostics（很大）。当前客户端工具描述可能旧；新stdio会话已验证加载当前代码。

渲染用本机bundled Poppler：`C:/Users/James/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe`。Python bundled有pypdf，无fitz。若控制UI必须先读computer-use技能，只用sky入口。

## 暂停收尾确认

C工程创建已完成：`create-c-result-v2.json`返回success=true、status=empty_project_created，完成时间2026-09-27 16:03。创建回执位于C/evidence/create-project.json。两张空白图103/301已保存，工具恢复原B图和B项目。**没有启动C的execute批次，目前没有本轮仍在运行的CAD操作。**

## Claude Desktop共享读取

Claude Desktop已配置kinto_autocad，启动文件为`C:/kinto/Autocad-mcp/.venv/Scripts/autocad-mcp.exe`。默认`get_tool_capabilities`会附带本文件的project_handoff字段，两个客户端读取同一份磁盘记录；不依赖另一客户端的聊天历史，不需要增加API key或文件系统服务。

建议下一次提示：先调用kinto_autocad的get_tool_capabilities，读取project_handoff.content。说明当前状态和未完成项；未经我明确要求继续，不执行CAD写操作。若我确认继续，先核对回执和工作区，再从C测试工程继续，禁止重放A/B失败批次。
