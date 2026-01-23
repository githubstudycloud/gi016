# Qwen3 自定义部署新手操作指南 (端口 8001 版)

本指南专门针对以下场景：
1.  **自定义模型名称**：您运行的不是默认的 Qwen 名字。
2.  **自定义端口**：您的 vLLM 运行在 **8001** 端口。
3.  **无 Hermes 解析器**：您的 vLLM 没有配置 `--tool-call-parser hermes`，会导致模型吐出 XML 代码而不是工具调用。

我们将使用一个“全能修复脚本”来自动处理所有这些问题。

## 🛠️ 第一步：环境准备

请确保您已安装 Python。打开终端（PowerShell 或 CMD），输入以下命令安装必要的运行库：

```powershell
pip install fastapi uvicorn httpx
```

## 🚀 第二步：启动修复脚本

我们已经为您准备好了脚本 `middleware_fix_qwen.py`。这个脚本不仅会修复工具调用，还会**自动检测**您在 8001 端口运行的模型名称，所以您不需要手动修改代码。

在终端中运行：

```powershell
cd D:\11\Ali_Qwen3_Deployment
python middleware_fix_qwen.py
```

**启动成功的标志**：
您会看到类似下面的输出：
```text
🚀 Qwen3 专用修复中间件已启动
📡 连接 vLLM 地址: http://localhost:8001/v1
✅ 检测到 vLLM 正在运行模型: your-custom-model-name
👂 本地监听端口: 4000
```
*请保持这个窗口开启，不要关闭。*

## 🔌 第三步：配置 Claude Code

现在，我们要告诉 Claude Code 连接这个修复脚本（端口 4000），而不是直接连接 vLLM。

### 方式 1: 直接在命令行启动 (推荐)

打开一个新的 PowerShell 窗口，运行：

```powershell
# 设置连接地址为修复脚本的端口 4000
$env:ANTHROPIC_BASE_URL="http://localhost:4000"

# API Key 随便填，因为本地模型不验证
$env:ANTHROPIC_API_KEY="sk-1234"

# 启动 Claude Code
claude-code
```

### 方式 2: 如果您使用 VSCode 插件

在插件设置中：
*   **Base URL**: `http://localhost:4000`
*   **API Key**: `sk-1234`
*   **Model**: `claude-3-5-sonnet-20240620` (保持默认即可，修复脚本会自动把它替换成您的自定义模型名)

## ❓ 常见问题

**Q: 为什么 Claude Code 回复有点慢？**
A: 因为修复脚本需要等待模型把整句话（包括 XML 代码）全部生成完，才能进行解析和修复。所以它不支持“流式输出”（打字机效果），这是正常的。

**Q: 脚本报错 "Connection refused"？**
A: 请检查您的 vLLM 服务是否确实运行在 8001 端口。您可以在浏览器访问 `http://localhost:8001/v1/models` 看看是否有响应。

**Q: 模型疯狂输出 XML 代码 `<tool_code>` 但不执行工具？**
A: 这正是这个脚本要解决的问题。请确认您连接的是端口 **4000** (修复脚本)，而不是 8001。
