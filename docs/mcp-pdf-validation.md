# MCP 多页 PDF 工具验收（2026-09-24）

新增默认工具 export_electrical_project_pdf。当前共 61 项工具定义，24 项默认提供，37 项隐藏。

## 使用范围

参数 project_path 为绝对 WDP 路径，output_path 为新的绝对 PDF 路径，template_mode 必须明确传 synthetic_din_a3。首版只支持已验证的 DIN_tblock_a3 合成测试模板、Model 布局、同目录普通 DWG 条目的 UTF-8 WDP；不是正式项目或机械定比例打印接口。

活动项目必须匹配，活动图必须是成员，所有项目页必须打开且已保存。WDP 解析顺序必须与 Electrical 原生项目顺序一致。服务端创建独立副本，加入测试用途和页码标识、将比例字段设为 NTS，按横向 A3/monochrome.ctb/适应纸张逐页出图。不会保存源图或向实体打印机发送任务。

原生出图与合并分别复用 src/autocad/project_plot.py、src/autocad/pdf_merge.py；旧 CLI 脚本继续调用共享模块，服务端不导入验收脚本。运行时需要可选 pdf 依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[pdf]"
```

本机已安装 pypdf 6.10.0；不需要模型 API key，也不依赖 Codex 专属 Python 路径，Claude 使用相同本地虚拟环境即可。Codex 项目白名单已增加此工具；Claude Code 配置沿用服务端默认列表。本轮通过真实 stdio MCP 客户端验证，未验证已打开的 Codex/Claude 会话是否重新加载工具。

## 保护及返回值

拒绝已有输出、已有 partial、错误项目、未保存/缺失页面、页序不一致；检查打印配置回读、源文件与副本哈希、原生生成结果、合并后逐页内容流和纸张尺寸。成功后恢复原活动图纸，并再次检查项目及源文件哈希。

success=true/status=pdf_structure_verified 仅表示结构检查通过；visual_review 仍为 PENDING，调用者必须渲染并逐页查看。操作目录包含打印副本、原始 PDF、plot-manifest.json 和 result.json；失败保留 error.json、不自动重试写入。内部锁只覆盖同进程相关操作，不解决跨客户端竞争或 COM 硬超时。失败时可能停留在打印副本，应根据回执只读确认状态。

## 实机证据

- 首轮实验列表调用：work/projects/pdf-mcp-20260924-213746/mcp-acceptance.json，错项目拒绝、三页导出成功、重复输出拒绝。
- 默认列表实测：work/projects/pdf-mcp-20260924-213901/mcp-acceptance.json，返回 24 个默认工具，同样完成出图及拒绝用例。交付 output/pdf/electrical-mcp-three-page-20260924.pdf。
- 默认出图后的测试脚本文档枚举发生 COM TypeError，未将整段验收改记为一次通过，也没有重发出图。独立 scripts/verify_pdf_project.py 在新会话中完成关闭重开和原生回读，证据 independent-reverification/report.json 为 PASS。
- 重开后 202 线号、两个正确端点，以及 BOM、From/To、端子计划和端子编号报表均通过已有语义校验器。此验证针对合成工程，不代表真实 TREBI 图纸已验收。
- 最终三页 PDF 1.7，1191 × 842 pt，Poppler 无格式告警。100 dpi 全页渲染逐页检查通过：页序、图框、线号和引用可读，无明显裁切/重叠。最终 visual-acceptance.json 单独记录人工视觉验收，未篡改工具原始 PENDING 回执。

自动测试：131 passed，3 deselected。包含可选 PDF 测试（本机依赖已安装），新增模式、输出、保存状态、缺页、错项目与页序保护；基础出图参数、连接及报表仍依赖真实 CAD 证据。

后续：中英双语图框及字体、固定比例机械 PDF、更广模板/多布局支持、跨客户端互斥与 COM 异常恢复。
