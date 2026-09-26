---
name: autocad-mechanical
description: 在本项目中通过 AutoCAD MCP 与 Computer Use 绘制简单机械二维图，如安装板、开孔图和支架图，并核验几何、尺寸及打印输出。
---

# 机械二维图工作流

先看[API与技能覆盖](../../docs/api-skill-coverage.md)及[工具清单](../../docs/tool-inventory.md)，按已验收范围选工具。Mechanical技能是绘图步骤，不是AutoCAD Mechanical专业工具集或机械设计规范的完整实现。

确认单位、WCS/绘图平面、尺寸基准及目标DWG。基本直线、圆、矩形使用draw_line/draw_circle/draw_rectangle；这些操作走AutoCAD通用ActiveX，不走Electrical专用AutoLISP。

已验收add_aligned_dimension、add_diameter_dimension及get_dimension_info，当前标注不关联几何。几何变化后重新核对Measurement和对象位置；不能依靠文字覆盖值证明尺寸正确。圆弧、通用多段线、填充、修剪/偏移、其他标注和3D目前没有完整MCP验收，不因工具存在就标记可用。

保留profiles/titleblock-zh-en.json机械图框；不要套用TREBI电气页号位号规则。模型空间真实尺寸与布局打印比例分开核验。电气项目PDF验收不能证明机械图1:1/1:2等定比例打印正确。

写入前传入expected_drawing_path，涉及实例选择时再传expected_instance_hwnd。需要界面功能时读取本机Computer Use技能，MCP与UI串行；先在独立样板验证所需操作。写入结果未知时读回，不自动重放。

交付前核对孔径、孔距、外形、尺寸对象及保存重开；需要PDF时另查字体、线型、比例和裁切。已有样例见[安装板任务](../../examples/mechanical-plate.md)。
