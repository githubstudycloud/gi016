# LiteLLM 代理部署方案 (Claude 协议兼容)

本目录提供了一套基于 **LiteLLM** 的替代方案，用于将 Qwen3 的 OpenAI 接口转换为 Claude 兼容接口，解决 `claude-code` 等工具的兼容性问题。

## 📂 目录结构

- `setup_and_run.py`: 自动化部署脚本 (安装依赖 + 启动服务)。
- `litellm_config.yaml`: LiteLLM 配置文件，定义了模型映射和 API 转发规则。

## 🚀 快速开始

### 1. 确保 vLLM 已启动
请确保您的 Qwen3 vLLM 服务正在运行，且监听端口为 **8001**。
如果 vLLM 在其他端口，请修改 `litellm_config.yaml` 中的 `api_base`。

### 2. 运行部署脚本
在当前目录下运行以下命令：

```bash
python setup_and_run.py
```

该脚本会自动：
1. 安装 `litellm[proxy]` 及其依赖。
2. 加载 `litellm_config.yaml` 配置。
3. 在 **4000** 端口启动转换服务。

## 🔌 客户端连接配置

现在您可以使用任何支持 Claude/OpenAI 协议的客户端连接到 LiteLLM。

- **API Base URL**: `http://localhost:4000`
- **API Key**: `sk-1234` (在配置文件中定义的 master_key)
- **Model Name**: `claude-3-5-sonnet-20240620` (会自动转发给 Qwen3)

### Claude Code 示例
```bash
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-1234"
claude-code
```

## ⚙️ 配置文件说明 (`litellm_config.yaml`)

```yaml
model_list:
  - model_name: claude-3-5-sonnet-20240620  # 客户端看到的模型名
    litellm_params:
      model: openai/Qwen/Qwen3-235B-A22B-Instruct # 实际调用的后端模型 (openai/ 前缀表示通用 OpenAI 格式)
      api_base: http://localhost:8001/v1    # vLLM 地址
      api_key: sk-empty                     # vLLM Key
```
