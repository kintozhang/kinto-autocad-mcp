# COM 中断检查与恢复

默认工具 `recover_cad_interruption` 分 inspect / release 两步。不重放旧调用、不保存或关闭图纸、不撤销对象，也不把失败操作改成成功。

1. 先查看 `get_execution_diagnostics` 与操作/工程回执，确认已执行的步骤。
2. 明确当前 DWG 完整路径及 AutoCAD HWND，调用 `recover_cad_interruption(action="inspect", expected_drawing_path=..., expected_instance_hwnd=...)`。
3. 工具独占检查会话锁；仍有工作进程、CAD不空闲、活动图错误、未保存图纸或不支持的对象类型都会拒绝。读取两次模型空间对象与磁盘哈希，保存 snapshot_id 和 operation_id。
4. 操作者核对该快照和部分执行结果，确认后调用 action="release"，传入同一目标和返回的两个ID。工具重新读取并逐项比对；任何变化要求重新 inspect。
5. release 仅解除对**新操作**的限制。失败操作仍为 partial_or_unknown，不能直接重跑创建、插入或接线。应按对象和回执从未执行步骤继续，必要时恢复备份到独立目录。

快照和解锁凭据保存在 `%LOCALAPPDATA%/KintoAutoCADMCP/recovery/`。当前仅支持块、直线、单行文字、多行文字（MText）、圆的模型空间快照；复杂实体、未保存现场、非标准手工脚本锁需单独核查，不能强制解锁。

本轮同时修复：

- PDF打印前的只读预检失败返回 preflight_rejected/submitted=false，不再误触发中断锁。开始打印后的失败仍保留隔离。
- 工作进程先保存实际工具结果，再校验活动上下文；COM上下文读取失败不会丢掉工具返回的部分执行证据。
- LISP完成回执后的文档名读回支持有界重读；只重读元数据，绝不再次发送已提交命令。

本流程减少人工清理锁文件的需要，但不是任意图纸自动回滚，也不能证明控制系统安全或正式设计正确。


2026-09-27：真实电缆父子引用会生成MText，恢复快照增加其内容、位置、文字高度/宽度、旋转、附着点、方向和样式。已在失败PDF副本上完成inspect/release；原图哈希保持一致。仍拒绝其他未知实体，不替代未保存现场的人工核查。


2026-09-27：传感器共享分支的Electrical自动布线生成跨线圆弧与标注多段线，恢复快照新增AcDbArc和轻量AcDbPolyline。记录圆弧中心/半径/起止角/法向/厚度、多段线顶点/凸度/逐段宽度/闭合/标高/法向/厚度；几何变化仍拒绝release。两次完整只读快照的子进程上限调整为60秒，超时仍保持隔离。失败批次仍不得重放。
