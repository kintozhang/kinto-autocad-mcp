# 工程入口、恢复与验收

## 默认工具

- plan_cad_project：离线规划新工程，选mechanical或trebi_electrical，明确输出根目录、名称和逻辑页清单。
- create_cad_project：新目录内从对应DWT创建DWG。电气项目同时创建WDP/WDT、设置原生逻辑页与0..9分区、PAGE/OF/PREV/NEXT。仅test_only或design_draft；不选型、不宣称可施工。
- restore_cad_project：备份文件校验后恢复至不存在的新目录，要求新项目名；WDP/WDT改名、相对DWG引用保持。只支持同目录文件，不推断外部依赖。恢复后须打开新WDP并验收。
- audit_cad_project：按当前WDP/DWG哈希汇总10类证据，缺失、未知、失败、过期或源证据被改动均阻断；不会依据success或“无报错”批准正式出图。

原list_drawings已使用稳定文档清单，活动图按名称+完整路径确认，未保存图不以空路径当身份；不再从文件名推断逻辑页号。

## 新建工程示例

```json
{
  "schema_version": 1,
  "name": "TREBI-DRAFT-01",
  "output_root": "C:/kinto/CAD_Projects",
  "discipline": "trebi_electrical",
  "pages": ["54", "112"],
  "purpose": "design_draft",
  "base_project": "C:/path/to/explicit-base.wdp"
}
```

调用plan_cad_project检查；调用create_cad_project前打开base_project中的图纸并传expected_drawing_path和expected_instance_hwnd。base_project必须明确存在且当前有效，只继承它的原生项目设置，不复制元件或图页。没有隐式使用任意当前项目。机械模式不需要base_project，选择mechanical和页清单即可。模板主文件在templates中；模板哈希写入规划与回执。

新工程输出为output_root/name，包含drawings、exports/pdf、reports、backups、evidence；电气WDP/WDT与DWG同放drawings，符合当前备份支持范围。project.json保存规格及规划，evidence/create-project.json保存每步状态。创建后恢复调用前的活动图纸和基础项目上下文。新项目需在Electrical项目管理器打开对应WDP使用，不覆盖原工程。

## 中断与恢复

entered/partial_or_unknown均不得自动重放；先读get_execution_diagnostics、创建/绘图回执及对象状态。备份位于相应work/batches或work/changes回执所列目录；恢复是分叉出新的工程，不覆盖失败现场，也不会清除会话锁。restore_cad_project返回cad_reopen_verified=false，只有独立原生回读/报表检查之后才能更新验收记录。备份不含未保存内容和外部符号/目录数据库；这些依赖必须另行管理。

## 验收证据格式与边界

调用audit_cad_project(project_path,evidence_files)，首次可传空列表，报告将返回subjects（当前WDP和全部DWG的SHA256）及缺失项。需要10类：hardware_identity、io_mapping、tag_uniqueness、connections、cross_references、bom、terminals、save_reopen、pdf_review、engineering_review。

每个证据JSON包含schema_version=1、kind、subjects、reviewer，以及非空checks。每条check必须有唯一id、status=pass、实际源文件的绝对source_path和source_sha256。任何图纸更改后旧证据失效；缺失或unknown不能当作pass。这个汇总工具核对证据版本与完整性，不自动测量实物、不替代原生回读，也不直接扫描DWG重号。父子触点共享位号的合法性由tag_uniqueness专项证据说明。

即使全部证据齐全也只返回evidence_complete=true；production_ready和formal_export_allowed仍为false，正式发布流程尚未开放。现有PDF出口仍是受限合成/草案验证，不应把文件导出当成施工批准。统一报告已实现，但自动采集所有专项证据、PLC/硬件核实和正式出图批准不属于本轮完成范围。

## 接入与验证

Codex用户级及项目级已配置，客户端工具超时660秒；Claude Desktop配置本地stdio。scripts.check_client_mcp根据两份实际配置启动新进程核对清单，不能替代桌面应用重启验收。本轮新增4项默认工具，合计32项默认、70项定义。客户端需重新连接后才能发现新工具。

仓库脚本scripts.verify_engineering_workflow支持对明确的test_only项目保存重开、通过MCP恢复备份、比较四类原生报表并检查缺失证据阻断。2026-09-26：Engineering_Acceptance下机械1页、电气54/112两页创建与重开对象完全一致；恢复三页工程的BOM、From/To、端子计划和端子线号与备份前参考报表完全相同，缺失10类证据正确阻断。输出WORKFLOW-VERIFIED/summary.json；正式工程及原资料未改动。
