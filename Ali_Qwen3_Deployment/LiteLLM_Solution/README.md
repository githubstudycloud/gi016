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
  # 1. 本地转发示例
  - model_name: claude-3-5-sonnet-20240620
    litellm_params:
      model: openai/Qwen/Qwen3-235B-A22B-Instruct
      api_base: http://localhost:8001/v1

  # 2. 局域网远程转发示例 (新增)
  - model_name: qwen-235b
    litellm_params:
      model: openai/Qwen/Qwen3-235B-A22B-Instruct
      # ⚠️ 修改此处 IP 为实际服务器地址
      api_base: http://192.168.1.X:8001/v1
      api_key: empty
```

## 📝 常见操作

### 修改远程服务器 IP
打开 `litellm_config.yaml`，找到 `qwen-235b` 部分，将 `api_base` 中的 `192.168.1.X` 修改为您实际的局域网 IP 地址。

### 重启服务
修改配置后，必须重启服务才能生效：
1. 在终端按 `Ctrl+C` 停止服务。
2. 运行 `python setup_and_run.py` 重新启动。
