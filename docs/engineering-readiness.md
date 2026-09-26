# P0/P1 工程化进度

## 本轮完成：显式文件备份与恢复

离线入口 `python -m scripts.engineering_archive`，无需连接AutoCAD或模型API。不自动保存正在编辑的图纸，不清除MCP锁，不覆盖工程。尚未自动挂接绘图工具；写入前须显式调用。

在仓库目录执行，路径替换为实际项目及新的独立输出目录：

```powershell
.venv/Scripts/python.exe -m scripts.engineering_archive backup C:/CAD/Project C:/CAD/Archives/run-001 Project.wdp Project.wdt drawings/page.dwg
.venv/Scripts/python.exe -m scripts.engineering_archive verify C:/CAD/Archives/run-001
.venv/Scripts/python.exe -m scripts.engineering_archive restore C:/CAD/Archives/run-001 C:/CAD/Recovered/run-001
.venv/Scripts/python.exe -m scripts.engineering_archive receipts C:/CAD/receipts/report.json
```

backup要求明确文件列表，保存相对路径、字节大小和SHA256；复制完成后再次比较源文件。目录跨界、重复文件、缺失文件、已存在目标拒绝。未完成的备份没有manifest.json，保留现场但不能作为有效备份。

必须在工程停止编辑时执行；文件哈希检查不能提供跨多文件事务快照。仅包含磁盘已保存内容，不含AutoCAD未保存状态。文件清单由操作者明确提供，本工具不解析WDP依赖；DWG、WDP、WDT以外所需的符号、模板、外部参照、数据库等必须另行列入。不要将此备份称为自动完整工程备份。

restore先核验清单，再复制到不存在的新目录。不会改写WDP绝对路径、重命名项目或加载CAD。恢复目录是原文件的副本，打开前应检查引用路径及项目名冲突；AutoCAD项目恢复验收仍需独立执行。中断/校验失败产生的不完整目录应保留检查，不能继续覆写或直接投入使用。

## 本轮完成：执行回执汇总基础

receipts输出文件哈希、未完成步骤、失败步骤、保存重开状态，以及完成、未提交、部分/未知分类。缺失、损坏或不认识的回执保持未知；entered/failed_or_unknown不得重放。即使success=true也不作为工程验收或施工批准。此入口只汇总执行证据，不读取DWG、不检测重号、不核对硬件/I/O，不自动放行正式出图。

## 验证

410项默认测试通过，3项integration未运行。新增覆盖不覆盖恢复、哈希损坏、目录跨界、复制期间源文件变化及未知回执保守分类。

本机已对change-numbered-validation的WDP/WDT和三张DWG完成5文件备份与新目录恢复，恢复内容SHA256全部一致；两个真实MCP修改回执正确归类为执行完成但需独立验收。输出位于CAD_Projects/TREBI_Localization/electrical/poc/engineering-archive-validation-20260926及engineering-restore-validation-20260926。本轮没有打开恢复工程，不宣称CAD恢复成功。

## 后续尚未完成

- P0：备份接入写入工具，并对已保存项目/依赖清单强制检查；在新项目名下进行CAD恢复、原生报表验收。
- P0：统一项目创建与机械/TREBI模板选择入口。
- P0：整理现有代码提交私有仓库；Codex和Claude实际重启后的接入复核。
- P1：以项目版本绑定映射、硬件、线网、跨页、报表、PDF等证据的统一验收报告和正式出图阻断。目前回执汇总不承担这一功能。


## 自动备份接入实验修改工具

execute_trebi_test_change在任何CAD写入前备份当前WDP、WDT及项目清单中的全部DWG，要求文件处于同一目录；备份到被Git忽略的work/changes/<操作ID>/backup。校验完成后再次核对目标DWG哈希、Saved状态及项目上下文。备份失败返回submitted=false，不换块、不修剪、不保存。执行回执backup字段记录范围、路径和各文件哈希。

该接入仅覆盖实验换灯/通道改接工具，不涵盖默认批量绘图和其他写工具。备份仅包含磁盘版本，其他已打开图页的未保存修改不包含在内；外部依赖和项目数据库不包含。备份所在repo/work受Git忽略，不会随代码推送；清理工作目录前应另行保存需要保留的工程快照。

413项默认测试通过。在change-backup-validation/DELTA-CHANGE-BACKUP.wdp新副本通过真实MCP换灯及改接、保存重开、13段线、4个跨页引用及四类原生报表验收。两个操作各生成5文件备份，目标DWG的备份哈希与请求中的原版本完全一致；两个备份各恢复至新目录并逐文件核验。恢复文件未在AutoCAD中打开，尚不宣称原生项目恢复验收。原工程哈希不变。备份与回执摘要见该私有测试目录acceptance-summary.json。


## 默认批量入口备份接入：代码完成，实机待验收

execute_trebi_batch现于全部空白图页预检后、任何激活/设置/插入之前备份WDP、WDT及项目DWG。复用engineering_archive.backup_saved_project，备份路径写入回执backup字段。备份后再次核对项目清单、各图Saved状态及磁盘哈希；失败返回submitted=false。实验修改工具也改用同一备份实现。

414项默认测试通过，3项integration未运行。新增批量备份失败测试确认不激活、不插入、不接线、不写线号、不保存、不生成报表。此改动尚未完成新增入口的实机验收，不能将上一版批量绘图通过当作本版备份集成通过。

实机尝试在两个独立目录delta-batch-backup-20260926、delta-batch-backup-retry-20260926准备空白工程，分别出现COM调用被拒绝和Add.SaveAs属性访问失败，均未进入批量工具。只读确认准备进程已退出、CAD空闲、生成图仅含WD_M和TREBI图框，未创建WDP；保留preparation-failure-evidence.json及空白图。核对确切进程/操作标记后解除对应中断隔离，没有关闭、保存或删除失败现场。第二次留下新建未保存空白图。下一步先修复验收脚本的文档创建/就绪处理，再用新工程完成批量备份实机验证。


## 文档创建就绪修复及批量备份实机完成

新增com_runtime.create_document_from_template：Add和SaveAs各提交一次；忽略Add可能未完整初始化的返回代理，按创建前后文档名称集合确认唯一新文档，读取其活动身份、CMDACTIVE及空闲状态；等待连续空闲样本后才取得SaveAs方法。忙碌HRESULT、已知属性元数据缺失和新建后文档集合短暂不可枚举仅在有界只读探测内等待。出现其他错误或写入异常立即停止，不自动重放。调用方必须持有会话锁。

419项默认测试通过。首次修复复测暴露了文档集合不可枚举的额外过渡状态，失败空白图和证据保留；补齐只读等待后，delta-batch-backup-ready-20260926/DELTA-BATCH-BACKUP-READY.wdp三张空白图全部创建保存成功，真实默认MCP批量绘图及备份成功。独立保存重开确认11段线、4个跨页引用、BOM三件、From/To9行、两种端子报表各7行，报表前后完全一致。备份5文件核验并恢复至独立目录通过，恢复文件未在CAD打开。本轮没有重新生成PDF。之前“默认批量备份实机待验收”的缺口在本样板范围已补齐。

本修复用于新的模板创建辅助函数及验收入口；不是全部COM路径永不失败的保证，也没有自动重试写命令。通用项目创建MCP入口、完整依赖恢复及正式国产化回路仍待继续。


收尾说明：关闭遗留未保存空白图时文档集合读取再次返回COM忙碌，停止清理。核对清理进程已退出、CAD空闲及尚存空白对象一致后解除该确切中断标记；未继续关闭。旧失败证据的FullName为空，不能唯一标识多个未保存文档，因此不能确认每张旧空白图的关闭归属，保留剩余图不再自动清理。blank-cleanup.json保留此次核对。此事件不改变上述三页工程创建/批量/重开/报表验收结果，但仍证明其他COM操作不具备全局无故障保证。


## 稳定文档清单与未保存图身份

新增document_inventory及只读诊断入口 `.venv/Scripts/python.exe -m scripts.inspect_cad_documents`。连续两次清单一致才返回；仅对忙碌HRESULT、元数据暂不可用和已知不可枚举错误有限重试。已保存图按完整路径区分（不同项目可同名），未保存图按文档名区分，并记录实例HWND。身份仅代表当前快照，不授予以后自动关闭权限。缺失/重复身份拒绝，不以空FullName识别文档。

425项默认测试通过。本机读取42张文档成功，未保存文档Drawing17.dwg单独识别；旧失败记录只有空FullName，无法证明其归属，因此保留不关闭。首次诊断因不同项目同名图被保守拒绝，修正为完整路径区分后通过。记录位于work/document-inventory-20260926-verified.json。诊断未提交CAD写操作，不清除其他中断标记，也没有增加默认MCP工具数量。此项解决诊断身份和读取稳定性；未实现自动关闭/恢复流程。


## 代码归档与客户端接入整理

2026-09-26：Codex用户级新增kinto_autocad，保留既有配置，仓库/Wiki/用户级客户端超时统一660秒，高于批量工作进程600秒。Claude按用户选择配置Windows Desktop本地stdio。两者使用同一venv可执行入口，默认实验集关闭，不需要模型API key。scripts.check_client_mcp分别读取两份真实配置、各启动全新进程，初始化、默认28工具清单与能力查询通过；桌面UI重启尚未验收，脚本握手不替代客户端验收。

配置依据：https://developers.openai.com/codex/mcp 、https://code.claude.com/docs/en/mcp 。现有425项默认测试基线；代码、文档和测试归档到private远端，原origin/upstream保留。未包含原始厂家资料、工作目录、DWG/PDF或本机客户端配置。
