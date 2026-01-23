# 阿里 Qwen3-235B 大模型部署与 Claude Code 集成指南

本指南详细说明如何部署阿里最新的 **Qwen3-235B-A22B-Instruct** 大模型，并配置其支持 **Tool Calling (工具调用)**，以及如何通过 **LiteLLM** 实现与 **Claude Code** 协议的兼容，彻底解决 API 调用中的 **400 Bad Request** 错误。

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

# 安装 LiteLLM (协议转换网关)
pip install litellm[proxy]
```

## 3. 部署 vLLM 推理服务

vLLM 是部署 Qwen 系列模型的最佳选择，支持高效的 MoE 推理和 OpenAI 兼容接口。

### 启动脚本 (`start_vllm.ps1`)
```powershell
# Windows/WSL 示例
python -m vllm.entrypoints.openai.api_server `
    --model Qwen/Qwen3-235B-A22B-Instruct `
    --trust-remote-code `
    --tensor-parallel-size 4 `
    --gpu-memory-utilization 0.95 `
    --max-model-len 32768 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes `
    --quantization fp8 \
    --port 8000
```
*注意: 必须指定 `--tool-call-parser hermes`，因为 Qwen3 使用 Hermes 风格的工具调用格式。*

## 4. 配置 LiteLLM 支持 Claude Code 协议

**Claude Code** (以及许多支持 Claude 的客户端) 使用 Anthropic 的 API 格式。为了让 Qwen3 能够被这些工具调用，我们需要使用 LiteLLM 搭建一个转换网关。

### 为什么会出现 400 错误？
1. **协议不匹配**: 客户端发送 Anthropic 格式的 `tools`，但服务器期望 OpenAI 格式。
2. **并发工具调用**: Claude Code 可能会并行请求执行多个工具，但部分推理后端处理顺序有误。
3. **Token 溢出**: 默认上下文窗口设置过小。

### 解决方案：LiteLLM 配置文件 (`config/litellm_config.yaml`)

创建 `litellm_config.yaml`：

```yaml
model_list:
  - model_name: claude-3-5-sonnet-20240620  # 伪装成 Claude 3.5 Sonnet
    litellm_params:
      model: openai/Qwen/Qwen3-235B-A22B-Instruct
      api_base: http://localhost:8000/v1
      api_key: sk-empty
      # 强制参数转换
      drop_params: true 

general_settings:
  master_key: sk-1234
  # 解决 400 错误的核心：自动修正工具调用格式
  drop_params: true
```

### 启动 LiteLLM
```bash
litellm --config config/litellm_config.yaml --port 4000
```

## 5. 客户端连接 (Claude Code)

现在，您的 Qwen3 模型可以通过 LiteLLM 在端口 4000 上以 Anthropic 协议访问。

如果您的客户端支持设置 Base URL (如 Cursor, VSCode 插件):
- **Base URL**: `http://localhost:4000`
- **Model**: `claude-3-5-sonnet-20240620`
- **API Key**: `sk-1234`

如果使用 `claude-code` CLI 工具：
您可能需要设置环境变量来重定向请求（取决于工具的具体实现），或者在代码中拦截。
```bash
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-1234"
claude-code
```

## 6. 常见问题排查

**Q: 依然报 400 错误？**
A: 检查 vLLM 后台日志。
- 如果显示 `context length exceeded` -> 调大 vLLM 的 `--max-model-len`。
- 如果显示 `Invalid tool_choice` -> 在 vLLM 启动参数中移除或更换 `--tool-call-parser`。
- 确保 LiteLLM 版本是最新的，它对 Qwen 的 Function Calling 转换有专门优化。

## 7. 更多文档资源

*   [📘 新手详细部署教程 (vLLM + LiteLLM)](./Qwen3_Claude_Integration_Guide_Beginner.md): 如果您是第一次部署，请从这里开始。包含详细的参数解释和步骤。
*   [🔧 无需重启 vLLM 的修复方案](./Qwen3_No_Restart_Fix_Guide.md): 如果您无法修改 vLLM 启动参数（无法添加 hermes parser），请参考此文档使用 Python 中间件进行热修复。
