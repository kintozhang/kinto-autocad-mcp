# Delta R2 I/O 只读规划验证

2026-09-25：新增默认 MCP 工具 `plan_delta_r2_io(spec)`。65 项定义、28 项默认、37 项隐藏；默认测试 286 passed、3 deselected。

## 实现与证据

`src/tools/delta_io.py` 加载 `profiles/delta-r2-ec0902.json`，检查模块实例、端口、通道占用、输入制式及继电器公共端电位冲突。公开演示见 `examples/delta-r2-io-plan.json`，仅包含合成信号。

依据厂商 `DELTA_IA-GMC_R2-EC_MdM_TC_20240830.pdf`：物理页 35–38 对应印刷页 2-24–2-27；物理页 107、113 对应 5-30、5-36。原始文件哈希与逐项页码保存在 profile。手册说明 R2-EC0902 系列，订货后缀 D0 与实物版本的对应关系仍待确认。

`tests/test_delta_io.py` 验证四端口通道边界、双模块同名端子区分及非法配方拒绝。`tests/test_mcp_bootstrap.py` 经真实 stdio 初始化、列工具及调用规划入口，去除模型 API key；CAD 检测和启动连接被 mock，属于协议验证，不是 CAD 联调。

私有资料目录的 `work/delta-ingest-20260925/mcp-io-plan.json` 另保存两条普通示教器信号的实际 stdio 回执；两个模块的分配、PNP 选择均为建议，供电未冻结。八份源文件哈希复核一致。

## 返回值与使用边界

每条记录保留模块、端口、端子、公共端、6000h/6200h 对象和子索引，以及来源页码。字节内位仅作为待在线核实的候选。

`global_plc_address` 和 `process_image_offset` 始终为 null，`ready_for_drawing`、`submitted`、`cad_contacted` 均为 false。规划成功不表示可以接线或已生成 Electrical 图纸。

本工具不调用 AutoCAD API，不替代原生 Electrical 插入工具。暂不把草案转换为批量绘图配方；需先取得准确 ESI、实物版本和 NC50 建站映射，再完成专用 PLC 符号、连接、保存重开和报表验收。普通规划入口拒绝声明为安全功能的信号，但不自动判定信号的实际安全用途。
