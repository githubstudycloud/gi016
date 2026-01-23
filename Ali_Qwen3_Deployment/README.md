# 阿里 Qwen3-235B 大模型部署与 Claude Code 集成指南

本指南详细说明如何部署阿里最新的 **Qwen3-235B-A22B-Instruct** 大模型，并配置其支持 **Tool Calling (工具调用)**，以及如何通过 **自定义中间件 (Middleware)** 实现与 **Claude Code** 协议的完美兼容，彻底解决 API 调用中的 **400 Bad Request** 错误及工具调用失效问题。

## 1. 模型简介与硬件要求

**模型名称**: Qwen3-235B-A22B-Instruct
**发布时间**: 2025年7月
**特点**: 
- 总参数 235B，激活参数 22B (MoE 架构)
- 卓越的代码与数学能力，超越 DeepSeek-R1 与 Grok-3
- 完美支持 Function Calling (工具调用)

**推荐硬件**:
- **显存**: 至少 300GB (推荐 4x H20 96GB 或 4x A100 80GB)
- **量化**: 强烈建议使用 FP8 格式部署以节省显存并提升速度
- **系统**: Linux (生产环境) 或 Windows (WSL2)

## 2. 环境准备

确保已安装 Python 3.10+ 和 CUDA 12.1+。

### 安装依赖
```bash
# 安装 vLLM (推理引擎)
pip install vllm>=0.7.0

# 安装 FastAPI 和 Uvicorn (用于中间件)
pip install fastapi uvicorn httpx
```

## 3. 部署 vLLM 推理服务

vLLM 是部署 Qwen 系列模型的最佳选择。

### 启动脚本 (`start_vllm.ps1`)
```powershell
# Windows/WSL 示例
python -m vllm.entrypoints.openai.api_server `
    --model Qwen/Qwen3-235B-A22B-Instruct `
    --trust-remote-code `
    --tensor-parallel-size 4 `
    --gpu-memory-utilization 0.95 `
    --max-model-len 32768 \
    --quantization fp8 \
    --port 8001
```
*注意: 我们建议将 vLLM 运行在 8001 端口，将 8000/4000 端口留给中间件或 LiteLLM。*

## 4. 核心解决方案：Claude 协议兼容中间件 (`middleware_fix_qwen.py`)

为了解决 Claude Code 无法调用工具以及 vLLM 对 Qwen 工具格式支持不完善的问题，我们开发了一个专用的 Python 中间件。

### 功能亮点
1.  **协议转换**: 将 Claude 的 `/v1/messages` 请求转换为 OpenAI 的 `/chat/completions`。
2.  **Prompt 注入**: 自动在 System Prompt 和 User Message 中注入 Qwen 官方推荐的 `<tools>` 和 `<tool_call>` XML 模板，强制模型进行工具调用。
3.  **XML 解析修复**: 能够智能解析 Qwen/Hermes 风格的 XML 输出，并将其转换为标准的 Tool Call 格式返回给 Claude Code。
4.  **400 错误修复**: 自动移除 vLLM 不支持的 `tools` 参数，改用纯 Prompt 驱动，规避 API 兼容性问题。

### 启动中间件
```bash
python middleware_fix_qwen.py
```
中间件默认监听 **4000** 端口。

## 5. 客户端连接 (Claude Code)

配置您的 Claude Code 或其他客户端连接到中间件：

- **Base URL**: `http://localhost:4000`
- **API Key**: `empty` (中间件不校验 Key)
- **Model**: `claude-3-opus-20240229` (或任意名称，中间件会自动转发给 Qwen)

### 验证部署
我们提供了一个测试脚本来验证工具调用是否正常工作：
```bash
python test_middleware_claude.py
```
如果看到 `🎉 Tool Call Detected`，说明配置成功！

## 6. 常见问题排查

**Q: 模型只聊天不调用工具？**
A: 请确保使用了最新版的 `middleware_fix_qwen.py`。新版增加了双重 Prompt 注入（System + User Reminder）和 `<tool_call>` 格式支持，能有效解决长上下文中的指令遗忘问题。

**Q: 依然报 400 错误？**
A: 检查 vLLM 是否正常运行在 8001 端口。中间件会自动处理大部分 400 错误（如 Context Limit），如果是 vLLM 报错，请查看 vLLM 控制台日志。

**Q: 如何修改 Prompt 模板？**
A: 修改 `middleware_fix_qwen.py` 中的 `generate_tool_system_prompt` 函数。目前使用的是 Qwen 2.5/3 官方推荐的 XML 格式。
