# 不重启 vLLM 实现工具调用修复指南

如果您无法修改 vLLM 的启动参数（例如没有服务器权限，或服务正在运行关键任务不能中断），您可以使用本目录下的 `middleware_fix_qwen.py` 脚本来“热修复”工具调用问题。

## 🎯 原理说明

**问题**：如果不加 `--tool-call-parser hermes`，Qwen3 模型会直接输出类似 `<tool_code>...</tool_code>` 的文本，而不是标准的 API 格式，导致 Claude Code 无法识别。

**解决方案**：我们在 Claude Code 和 vLLM 之间运行一个 Python 小程序（中间件）。
1. 它拦截模型的回复。
2. 用正则表达式查找 `<tool_code>`。
3. 把它“整容”成 Claude Code 能看懂的标准 JSON 格式。
4. 再发回给 Claude Code。

## 🛠️ 操作步骤

### 1. 安装依赖
我们需要安装 `fastapi` 和 `uvicorn` 来运行这个中间件。

```bash
pip install fastapi uvicorn httpx
```

### 2. 启动中间件
在终端中运行：

```bash
python middleware_fix_qwen.py
```

您会看到如下提示：
```
🚀 Qwen3 修复中间件已启动，监听端口: 4000
```

### 3. 连接 Claude Code
现在，不要连接 vLLM 的 8000 端口，而是连接这个中间件的 **4000** 端口。

**Claude Code 配置**:
*   **Base URL**: `http://localhost:4000`
*   **API Key**: `sk-1234` (任意填写)

### 4. 验证
现在尝试让 Claude Code 执行任务（如“计算 123 * 456”），中间件会自动将 Qwen3 的 XML 输出转换为工具调用，您应该能看到工具被成功触发。

## ⚠️ 局限性
*   **不支持流式输出 (Streaming)**: 为了解析完整的 XML，中间件必须等模型完全生成完一句话后才能处理。这意味着您看到的回复会有一些延迟（不是一个字一个字蹦出来的），但功能是正常的。
*   此脚本专为 **Qwen3/Hermes** 风格的 XML 设计。

---
**推荐**: 如果条件允许，**重启 vLLM 并添加正确参数** 永远是性能最好、最稳定的方案。本方案仅作为应急补救措施。
