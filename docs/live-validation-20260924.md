# 2026-09-24 本机联调

## 已通过

- Computer Use 识别并恢复 AutoCAD Electrical 2026 窗口，在开始页新建空白图纸。
- 活动 COM 实例：AutoCAD，版本 25.1s (LMS Tech)。
- 通过真实 MCP stdio 子进程调用 get_autocad_info、get_active_drawing、list_drawings 成功。
- 使用 MCP draw_rectangle、draw_circle、draw_text、zoom_extents 绘制合成样板。
- 样板：120 × 80 mm，四孔 Ø6，中心 (10,10)、(110,10)、(110,70)、(10,70)。
- COM 独立回读确认：闭合矩形面积 9600 mm²、四孔位置和半径、文本、毫米单位、共六个实体。
- 保存、关闭测试文档、重新打开，再次回读完全一致；Computer Use 目视检查通过。
- 图纸创建/保存/重开由测试脚本的 COM 操作完成，不代表这些功能已有 MCP 封装。

复验命令（会创建新的合成测试图）：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/live_smoke.py --write
```

脚本在每次工具调用前检查目标路径和 CMDACTIVE；这只是验收脚本保护，
不等于上游 MCP 已实现原子文档绑定或跨进程互斥。勿并发操作 CAD。

## Electrical 插入失败及修正

实际使用本机存在的 IEC2/HCR1.dwg。AutoCAD 命令行返回：
`no function definition: ACET-INSERT-BLOCK`。
修正前 MCP 返回 success=true，但模型空间对象数仍为 0。

修正 src/tools/electrical.py：发送前记录原对象句柄；仅接受本次新增的匹配块，
并回读位置、旋转及属性。没有新增块返回 success=false/status=unverified，
不把已有同名块改为本次请求的属性。该状态不能用于盲目重试。
即使块验证成功，也明确 electrical_semantics_verified=false。

真实 MCP 复测：对象仍为 0，正确返回未验证。
**电气插入功能尚未修复为可用，需要依据本机 2026 Electrical API 替换旧入口。**
其他电气工具的执行回执尚未统一改造，不可类推已经全部修复。

## 本机资料

- 已找到 IEC2、IEC-60617、GB2 等符号库，以及 HCR1、HCR21、wd_m 文件。
- 库根目录：C:/Users/Public/Documents/Autodesk/Acade 2026/Libs/
- API 帮助：C:/Program Files/Autodesk/AutoCAD 2026/Acade/Help/zh-CN/Help/ACE_API.chm
- 当前检测通过窗口标题识别 2026；安装路径/产品 ID 探测仍待改造。

## 证据与范围

本机输出：work/acceptance/20260924-124854-988431/
- mcp-plate-120x80.dwg、report.json：几何测试通过。
- electrical-symbol-probe.dwg、electrical-probe.json：修复前误报证据。
- electrical-probe-after-fix.json：修复后真实回执。

自动测试：45 passed, 3 deselected。
未执行电气项目关联、原生报表、自动编号、布局/PDF 或真实设备接线验证。
本次使用协议测试客户端连接项目服务；不代表已验证 Codex/Claude 客户端配置加载。
用户原有图纸未修改；测试图纸和输出仅在 work/ 下。未推送 GitHub。