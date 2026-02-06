# GLM-4V (vLLM) & LiteLLM 多模型支持指南

本文档详细说明如何使用 vLLM 部署支持图像识别的 GLM-4 模型（GLM-4V），以及如何配置 LiteLLM 以支持 Claude、OpenAI (Codex) 和 Gemini 模型。

## 1. vLLM 部署 GLM-4V (开启图片支持)

GLM-4 的多模态版本通常为 `THUDM/glm-4v-9b`。在 vLLM 中启用图片支持关键在于选择正确的模型版本并开启信任远程代码。

### 1.1 环境准备
确保已安装最新版本的 vLLM：
```bash
pip install --upgrade vllm
```

### 1.2 启动命令
使用以下命令启动 GLM-4V 模型服务。注意 `--trust-remote-code` 是必须的，因为 GLM-4V 的模型架构代码在 HuggingFace 仓库中。

```bash
# 启动 GLM-4V-9B
python -m vllm.entrypoints.openai.api_server \
    --model THUDM/glm-4v-9b \
    --trust-remote-code \
    --dtype auto \
    --max-model-len 8192 \
    --enforce-eager \
    --limit-mm-per-prompt image=1
```

**参数说明：**
- `--model THUDM/glm-4v-9b`: 指定 GLM-4V 模型。
- `--trust-remote-code`: 允许执行模型仓库中的自定义代码（GLM-4V 必需）。
- `--enforce-eager`: 部分多模态模型在 vLLM 中可能需要 eager 模式（视 vLLM 版本而定，如果遇到 CUDA Graph 错误请加上此参数）。
- `--limit-mm-per-prompt image=1`: 限制每个 Prompt 的图片数量（可选，视显存情况调整）。

### 1.3 验证图片支持
服务启动后（默认端口 8000），可以使用 OpenAI 客户端格式发送带图片的请求：

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="THUDM/glm-4v-9b",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "这张图片里有什么？"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
        ]
    }]
)
print(response.choices[0].message.content)
```

---

## 2. LiteLLM 配置 (支持 Claude, Codex, Gemini)

LiteLLM 充当统一的 API 网关，将标准 OpenAI 格式的请求转换为各家厂商（Anthropic, Google, etc.）的 API 调用。

### 2.1 安装 LiteLLM
```bash
pip install 'litellm[proxy]'
```

### 2.2 配置文件 (`litellm_config.yaml`)
创建一个配置文件，映射不同的模型别名。

**注意：**
- **Claude Code**: 对应 Anthropic 的 Claude 系列（如 `claude-3-5-sonnet`）。
- **Codex**: OpenAI 的 Codex 模型（`code-davinci-002`）已停止服务，现在建议使用 `gpt-4o` 或 `gpt-3.5-turbo` 进行代码生成。配置中我们可以将别名 `codex` 指向 `gpt-4o`。
- **Gemini CLI**: 对应 Google 的 Gemini 模型（如 `gemini-1.5-pro`）。

```yaml
model_list:
  # 1. Claude Support (Anthropic)
  - model_name: claude-code
    litellm_params:
      model: claude-3-5-sonnet-20240620
      api_key: os.environ/ANTHROPIC_API_KEY

  # 2. Codex Support (Mapped to GPT-4o)
  - model_name: codex
    litellm_params:
      model: gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  # 3. Gemini CLI Support (Google Vertex/AI Studio)
  - model_name: gemini-cli
    litellm_params:
      model: gemini/gemini-1.5-pro
      api_key: os.environ/GEMINI_API_KEY
      safety_settings:
        - category: HARM_CATEGORY_HARASSMENT
          threshold: BLOCK_NONE
        - category: HARM_CATEGORY_HATE_SPEECH
          threshold: BLOCK_NONE

  # 4. Local GLM-4V (via vLLM)
  - model_name: glm-4v
    litellm_params:
      model: openai/THUDM/glm-4v-9b
      api_base: http://localhost:8000/v1
      api_key: EMPTY
```

### 2.3 设置环境变量
在启动 LiteLLM 前，需要设置各家的 API Key：

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:OPENAI_API_KEY = "sk-..."
$env:GEMINI_API_KEY = "AIza..."
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."
```

### 2.4 启动 LiteLLM Proxy
```bash
litellm --config litellm_config.yaml --port 4000
```

### 2.5 使用示例
现在你可以使用统一的 OpenAI 接口（端口 4000）来调用这些模型：

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-1234" # LiteLLM 默认允许任意 Key，除非设置了 master key
)

# 调用 Claude (通过别名 claude-code)
resp = client.chat.completions.create(model="claude-code", messages=[{"role": "user", "content": "写一个 Python Hello World"}])
print("Claude:", resp.choices[0].message.content)

# 调用 Codex (GPT-4o)
resp = client.chat.completions.create(model="codex", messages=[{"role": "user", "content": "写一个二分查找"}])
print("Codex:", resp.choices[0].message.content)

# 调用 Gemini
resp = client.chat.completions.create(model="gemini-cli", messages=[{"role": "user", "content": "解释量子纠缠"}])
print("Gemini:", resp.choices[0].message.content)
```

## 3. 总结
- **vLLM**: 用于本地部署高性能的 GLM-4V 模型，需开启 `--trust-remote-code`。
- **LiteLLM**: 用于聚合管理云端模型（Claude, Gemini, OpenAI）和本地模型（vLLM），提供统一接口，方便在代码助手或 CLI 工具中切换后端。
