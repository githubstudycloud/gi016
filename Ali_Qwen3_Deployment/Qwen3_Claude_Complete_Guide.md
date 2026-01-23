# Qwen3 + Claude Code 完美集成终极指南

本文档汇集了解决 **自定义模型名**、**vLLM 400 错误**、**80k 上下文限制**、**局域网代理问题** 的完整解决方案。通过使用特制的中间件，我们实现了 Claude Code 与 Qwen3 (vLLM) 的无缝对接。

## 🌟 核心架构

*   **客户端**: Claude Code (默认连接 Port 4000)
*   **中间件**: `middleware_fix_qwen.py` (运行在 Port 4000)
    *   负责协议转换 (Claude `/v1/messages` <-> OpenAI `/chat/completions`)
    *   负责 **Prompt 注入** (将工具定义注入 System Prompt，绕过 vLLM 参数校验)
    *   负责 **80k 流量熔断** (保护显存)
    *   负责 **XML 解析** (提取 Qwen 的 `<tool_code>`)
*   **服务端**: vLLM (运行在 Port 8001)
    *   加载自定义名称的模型
    *   无需配置 `--tool-call-parser`

---

## 🛠️ 1. 准备工作

确保安装了 Python 环境及中间件依赖：

```powershell
pip install fastapi uvicorn httpx
```

## 🚀 2. 启动中间件 (核心步骤)

我们已经将所有复杂逻辑封装在 `Ali_Qwen3_Deployment/middleware_fix_qwen.py` 中。

**脚本功能亮点**:
1.  **自动修复 400 错误**: 拦截并删除 vLLM 不支持的 `tools` 参数，改为通过 System Prompt 告诉模型如何使用工具。
2.  **硬编码配置**: 自动指向 `http://localhost:8001`，使用密钥 `empty`，模型名锁定为 `Qwen/Qwen3-235B-A22B-Instruct`。
3.  **代理绕过**: 强制直连局域网，不走系统代理 (VPN)。
4.  **80k 保护**: 如果请求超过 80,000 token，直接拦截并提示清理。

**启动命令**:

```powershell
cd D:\11\Ali_Qwen3_Deployment
python middleware_fix_qwen.py
```

*看到 `🚀 Claude 协议兼容层已启动` 即表示成功。*

## 🔌 3. 启动 Claude Code

打开一个新的 PowerShell 窗口，配置环境变量并启动：

```powershell
# 1. 指向中间件端口 (4000)
$env:ANTHROPIC_BASE_URL="http://localhost:4000"

# 2. 任意填写 API Key (中间件不验证，但 Claude Code 需要非空值)
$env:ANTHROPIC_API_KEY="sk-1234"

# 3. 启动
claude-code
```

## 💡 使用技巧与故障排除

### Q: 为什么之前的配置会报 400 错误？
**A**: vLLM 在未配置 `--tool-call-parser` 时，如果接收到 API 请求中的 `tools` 字段，会直接抛出 400 错误。我们的中间件现在会**“偷梁换柱”**：它把工具定义从 API 参数里拿出来，写成一段文本（System Prompt）塞给模型。这样 vLLM 以为只是在进行普通对话，从而接受了请求。

### Q: 提示 "Context limit reached" 怎么办？
**A**: 这意味着您的对话历史即将撑爆 80k 显存限制。请在 Claude Code 中输入 `/compact` 命令来压缩历史记录。

### Q: 模型能看到我之前的工具调用结果吗？
**A**: 能。中间件会将 Claude 格式的历史记录（`tool_use`, `tool_result`）转换为 Hermes 风格的 XML 对话（`<tool_code>`, `<tool_output>`），模型能完美理解之前的上下文。

### Q: 局域网连接超时？
**A**: 中间件已内置 `trust_env=False`，它会忽略您的系统代理设置。请确保 vLLM 服务确实运行在 8001 端口，且防火墙允许连接。

---
**维护记录**:
- 2026-01-23: 添加 System Prompt 工具注入逻辑，彻底修复 vLLM 400 错误。
- 2026-01-23: 禁用 httpx 代理继承，解决局域网连接问题。
- 2026-01-23: 添加 `/v1/messages` 原生支持与 80k 熔断保护。
