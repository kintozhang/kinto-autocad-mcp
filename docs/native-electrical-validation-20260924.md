# Electrical 原生接口验收 · 2026-09-24

结果：PASS。真实 AutoCAD Electrical 2026（25.1s LMS Tech），通过新进程 MCP stdio 完成调用；没有调用模型 API 或使用 API key。此结果验证 MCP 服务，不代表 Codex/Claude 桌面客户端配置已重新加载。

## 独立合成图结果

输出目录：`work/acceptance/native-mcp-20260924-161426-273308/`。

- `native-electrical.dwg`：全新图，来自本机 ACE_Din_a3_Color.dwt，含 WD_M。
- `report.json`：每次 MCP 参数与返回值、元件属性、保存重开前后线网与线号、图面检查。
- `verified-from-to.csv`：由已核验原生线网和属性生成的单行连接表，不是 Electrical 项目报表导出。

| 验收项 | 回读证据 | 结果 |
| --- | --- | --- |
| 继电器 | HCR1，句柄 8B8，位置 (120,150)，自动标记 -K1，A1/A2 | 通过 |
| 正式端子 | HT0001，句柄 922，位置 (70,150)，TAGSTRIP=X1，TERM01=1 | 通过 |
| 接线点 | 端子只返回4个 X?TERMnn；排除 TERMDESC/PIN 属性 | 通过 |
| 原生导线 | 97C，MCP_WIRE，起点 (71.25,150)，终点 (112.5,150) | 通过 |
| 原生线网 | 922/X1TERM01 与 8B8/X4TERM01，映射 X1:1 → -K1:A1 | 通过 |
| 线号 | 101，线号块 98C；原生查询及两端 XTERM 缓存均为101 | 通过 |
| 保存重开 | 元件全部属性、接线点、线网、线号和导线几何一致 | 通过 |
| 图面 | Computer Use 检查可见 X1、1、101、-K1、A1/A2及导线 | 通过 |

A2 故意未连接；这是接口验收样板，不是完整可施工回路。单个独立 DWG 未加入 WDP，没有修改 GBDEMO 示例项目或 TREBI 原图。

## 接口与来源

权威依据是本机随 2026 安装的 `C:/Program Files/Autodesk/AutoCAD 2026/Acade/Help/zh-CN/Help/ACE_API.chm`。解包仅放在被 Git 忽略的 work/api-2026；不发布 Autodesk 文档和符号库。

| MCP 工具 | 原生实现 |
| --- | --- |
| insert_electrical_symbol | c:wd_insym2，options=2 返回新句柄；c:wd_modattrval 修改后回读 |
| get_electrical_connections | 读取块属性 X[01248]TERM 两位数字的实际坐标及 TERM 标签 |
| connect_electrical_terminals | c:ace_new_wiretype、c:ace_insert_wire；c:wd_get_wire_netlst 核对两端 |
| set_electrical_wire_number | c:wd_putwn；c:ace_get_wnum 回读 |
| get_electrical_wire | 只读线号、原生线网、导线图层与坐标 |

内部桥接为每次表达式生成唯一回执，捕获 Lisp 错误并核对活动文件。完成回执仍需对象回读证明业务正确。失败返回 unverified；已知部分写入返回对象句柄，不能盲目重试。

## 本次修正与测试边界

旧 ACET-INSERT-BLOCK 路径已替换。HT0_01 缺少正式端子排属性，首次探测未获得两端线网证明；改用 HT0001 后通过。第一次 MCP 保存重开测试错误地与插入瞬间的空 XTERM 属性比较；检查发现原生编号会将101写入连接点缓存。验收现明确断言此变化，再比较保存前后完整属性；早期失败记录保留。

58项非集成测试通过，3项上游带 mock 的集成测试未运行。新增覆盖非法属性不得触发写入、旧句柄不得重标、部分失败返回新句柄、描述属性不属于接线点、回执解析与新工具注册。

尚未验收：WDP项目数据库、跨页源/目标、父子交叉引用、端子排编辑器、多导线路由、BOM与Electrical原生项目报表、国产器件映射及TREBI整套图。当前不支持任意旋转，须选用库中的H/V符号。桥接锁仅覆盖同一服务进程中的表达式，不提供跨客户端互斥；COM调用也无硬超时。操作期间勿切换文档或让两个客户端同时写图。

## 重现

在项目目录运行（每次新建独立图，不复用现有图）：

```powershell
.\.venv\Scripts\python.exe scripts/native_electrical_smoke.py --write --template 'C:\Users\James\AppData\Local\Autodesk\AutoCAD Electrical 2026\R25.1\chs\Template\ACE_Din_a3_Color.dwt' --library 'C:\Users\Public\Documents\Autodesk\Acade 2026\Libs\iec2'
```

该脚本生成机器可读报告；最终图面由 Computer Use 人工式检查。仍须以实际项目资料核对生产设计。
