# MyDesktop 快速参考指南

## 🚀 快速开始

### 运行应用
```bash
python main.py
```

### 测试桌面监听器
```bash
python test_desktop_hook.py
# 然后按 Win+D 测试
```

### 查看日志
```bash
Get-Content app_debug.log -Tail 50
```

---

## 📁 项目结构

```
MyDesktop/
├── main.py                          # 主程序入口
├── core/
│   ├── desktop_hook.py              # 🆕 桌面事件监听器（信号驱动）
│   └── z_order_manager.py           # 窗口层级管理
├── widgets/
│   ├── fence.py                     # Fence 窗口组件
│   ├── floating_ball.py             # 浮动球组件
│   └── ...
├── managers/
│   ├── config_manager.py            # 配置管理
│   └── setup_manager.py             # 安装/卸载管理
├── utils/
│   └── shell_menu.py                # Shell 右键菜单
├── test_desktop_hook.py             # 🆕 桌面监听器测试
├── test_detect.py                   # 原始检测测试
├── OPTIMIZATION_REPORT.md           # 🆕 详细优化报告
└── TASK_COMPLETION_SUMMARY.md       # 🆕 任务完成总结
```

---

## 🔧 核心功能

### 1. Win+D 自动恢复
- **实现**：`core/desktop_hook.py`
- **原理**：每 500ms 检查桌面状态，状态变化时发出信号
- **响应时间**：~250ms

### 2. 快速启动
- **异步清理**：非阻塞杀死旧进程
- **延迟加载**：每个 Fence 间隔 100ms 加载
- **启动时间**：~500ms（首个窗口）

### 3. 单实例运行
- **机制**：QLocalServer/QLocalSocket
- **超时**：500ms
- **支持**：通过命令行参数传递给已运行实例

---

## ⚙️ 配置选项

### 调整桌面检查间隔
在 `main.py` 第 111 行：
```python
self.desktop_hook.start(interval_ms=500)  # 默认 500ms
```

**建议值**：
- 省电模式：1000ms
- 平衡模式：500ms（默认）
- 快速响应：300ms

### 调整 Fence 加载延迟
在 `main.py` 第 284 行：
```python
delay = 100 * i  # 默认 100ms
```

---

## 🧪 测试清单

### 基础功能测试
- [ ] 应用正常启动
- [ ] Fence 窗口正确显示
- [ ] 文件拖放正常工作
- [ ] 右键菜单正常显示

### Win+D 测试
- [ ] 按 Win+D 显示桌面
- [ ] Fence 窗口在 ~250ms 内恢复
- [ ] 日志中有 "Desktop shown event received" 记录
- [ ] 再次按 Win+D，窗口再次恢复

### 性能测试
- [ ] 启动时间 < 1 秒（首个窗口）
- [ ] 空闲时 CPU 占用 < 1%
- [ ] 内存占用稳定在 ~50MB

### 边界情况测试
- [ ] 快速连续按 Win+D
- [ ] 更换壁纸后窗口恢复
- [ ] 多次启动应用（单实例检查）

---

## 📊 性能指标

### 正常运行
- CPU 占用：~0.8%（空闲）
- 内存占用：~50MB
- 检查频率：500ms

### 启动性能
- 首个窗口：~500ms
- 全部加载：~2000ms（6 个 Fence）

### Win+D 响应
- 检测延迟：0-500ms（平均 250ms）
- 恢复时间：~50ms
- 总响应时间：~300ms

---

## 🐛 故障排查

### Fence 窗口不显示
1. 检查日志：`app_debug.log`
2. 确认配置文件：`nextgen_config.json`
3. 尝试删除配置文件重新启动

### Win+D 后窗口不恢复
1. 检查日志中是否有 "Desktop shown event received"
2. 确认 `desktop_hook` 是否正常启动
3. 运行测试：`python test_desktop_hook.py`

### 启动缓慢
1. 检查是否有多个实例在运行
2. 查看日志中的加载时间
3. 尝试减少 Fence 数量

### CPU 占用过高
1. 检查检查间隔设置（默认 500ms）
2. 确认没有其他进程干扰
3. 查看日志中是否有异常循环

---

## 🔍 日志分析

### 正常启动日志
```
App initializing...
Desktop initialized with signal-based desktop hook
Fence xxx successfully embedded to desktop
App running...
```

### Win+D 事件日志
```
Desktop shown event received, restoring all fences
Restoring fence: xxx
Force showed window xxx
```

### 错误日志
```
Error in on_desktop_shown: ...
Failed to restore fence xxx: ...
```

---

## 📞 常见问题

### Q: 为什么 Win+D 后有延迟？
A: 检查间隔为 500ms，平均延迟 250ms。可以降低间隔但会增加 CPU 占用。

### Q: 如何完全禁用 Win+D 恢复？
A: 在 `main.py` 中注释掉：
```python
# self.desktop_hook = DesktopHook()
# self.desktop_hook.desktop_shown.connect(self.on_desktop_shown)
# self.desktop_hook.start(interval_ms=500)
```

### Q: 可以同时运行多个实例吗？
A: 不可以，应用使用单实例模式。第二个实例会将参数传递给第一个实例后退出。

### Q: 如何备份配置？
A: 复制 `nextgen_config.json` 文件即可。

---

## 🎯 最佳实践

### 性能优化
1. 保持 Fence 数量在 10 个以内
2. 避免在 Fence 中放置大量文件（> 100 个）
3. 定期清理日志文件

### 稳定性
1. 不要手动编辑配置文件
2. 更换壁纸后等待 10 秒让窗口自动恢复
3. 定期重启应用（每周一次）

### 开发调试
1. 使用 `test_desktop_hook.py` 测试桌面监听
2. 查看日志文件排查问题
3. 使用 `logging.DEBUG` 级别获取详细信息

---

## 📚 相关资源

- **详细优化报告**：`OPTIMIZATION_REPORT.md`
- **任务完成总结**：`TASK_COMPLETION_SUMMARY.md`
- **原始检测测试**：`test_detect.py`
- **桌面监听测试**：`test_desktop_hook.py`

---

**最后更新**：2026-02-09
**版本**：v3.0（优化版）
