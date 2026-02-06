# GLM-4.7（离线 vLLM）+ LiteLLM：本地模型接入 Claude Code / Codex CLI / Gemini CLI

你现在部署的是 **GLM-4.7（文本模型，不是 GLM-4V）**，这意味着：
- **图片支持无法“开启”**：vLLM 的参数只能“承载模型能力”，不能把纯文本模型变成多模态模型。
- 如果你确实要图片输入，必须换成 **GLM-4V / GLM-4.1V 等多模态权重**（见本文附录）。

本文目标：在 **离线部署的 vLLM（8000）** 前面加一层 **LiteLLM Proxy（4000）**，让 3 个终端 CLI 都通过同一个入口访问你的 **本地 GLM-4.7**。

## 0. 你将得到的架构

- vLLM（离线模型目录）提供 OpenAI 兼容接口：`http://127.0.0.1:8000/v1`
- LiteLLM Proxy 作为统一入口：
  - OpenAI 兼容：`http://127.0.0.1:4000/v1/chat/completions`
  - Anthropic Messages（给 Claude Code 用）：`http://127.0.0.1:4000/v1/messages`
- 三个 CLI 只需要改环境变量/配置文件，把请求打到 4000

## 1. vLLM 离线启动 GLM-4.7（文本）

### 1.1 准备离线模型目录

假设你的离线模型在：
- `D:\models\glm-4.7`

该目录通常包含（示例）：
- `config.json`
- `tokenizer.json` / `tokenizer.model`
- `*.safetensors`

### 1.2 启动 vLLM OpenAI Server（Windows PowerShell）

```powershell
$ModelDir = "D:\models\glm-4.7"

python -m vllm.entrypoints.openai.api_server `
  --model $ModelDir `
  --served-model-name "glm-4.7" `
  --host 0.0.0.0 `
  --port 8000 `
  --dtype auto `
  --max-model-len 8192
```

如果你是多卡，按需加：

```powershell
  --tensor-parallel-size 2
```

### 1.3 验证 vLLM 是否可用

```powershell
curl http://127.0.0.1:8000/v1/models
```

你应该能看到返回里包含 `glm-4.7`（或你指定的 `served-model-name`）。

## 2. 安装并启动 LiteLLM Proxy（把 GLM-4.7 作为“真实后端模型”）

### 2.1 安装

```powershell
pip install "litellm[proxy]"
```

### 2.2 写 LiteLLM 配置（关键：三套“别名”都指向同一个本地 vLLM）

把下面内容保存为任意路径，例如：
- `D:\11\GLM4_LiteLLM_Guide\litellm_config.yaml`

```yaml
model_list:
  - model_name: glm-4.7
    litellm_params:
      model: openai/glm-4.7
      api_base: http://127.0.0.1:8000/v1
      api_key: EMPTY

  # 给 Claude Code 用的“外观模型名”（Claude Code 往往会带它自己的默认模型名）
  # 你也可以换成自己 Claude Code 实际选用/默认的模型名
  - model_name: claude-code
    litellm_params:
      model: openai/glm-4.7
      api_base: http://127.0.0.1:8000/v1
      api_key: EMPTY

  # 给 Codex CLI 用的“外观模型名”
  - model_name: codex
    litellm_params:
      model: openai/glm-4.7
      api_base: http://127.0.0.1:8000/v1
      api_key: EMPTY
```

如果你希望对外暴露时加一层认证（推荐），加上 master key：

```yaml
general_settings:
  master_key: "sk-litellm-local-only"
```

### 2.3 启动 LiteLLM Proxy

```powershell
litellm --config D:\11\GLM4_LiteLLM_Guide\litellm_config.yaml --host 0.0.0.0 --port 4000
```

### 2.4 验证 LiteLLM（OpenAI 兼容）

```powershell
curl http://127.0.0.1:4000/v1/models
```

以及发一条 chat：

```powershell
curl http://127.0.0.1:4000/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer sk-anything" `
  -d '{"model":"glm-4.7","messages":[{"role":"user","content":"用一句话介绍你自己"}]}'
```

## 3. 三个 CLI 怎么指向 LiteLLM（都用本地 GLM-4.7）

下面都以 Windows PowerShell 为例。

### 3.1 Codex CLI → LiteLLM（OpenAI 兼容）

Codex CLI 走 OpenAI 兼容接口，直接指向 LiteLLM 即可：

```powershell
$env:OPENAI_BASE_URL = "http://127.0.0.1:4000/v1"
$env:OPENAI_API_KEY  = "sk-litellm-local-only"  # 如果你没配 master_key，这里随便写
```

运行 Codex CLI 时，选择/指定模型为：
- `glm-4.7`（推荐，最直观）
- 或 `codex`（如果你的 CLI 固定用 codex 名称）

### 3.2 Claude Code → LiteLLM（Anthropic Messages /v1/messages）

Claude Code 默认走 Anthropic 的 Messages API。LiteLLM Proxy 支持 `/v1/messages`，所以需要把 Claude Code 的 Anthropic endpoint 改到 LiteLLM：

```powershell
$env:ANTHROPIC_BASE_URL   = "http://127.0.0.1:4000"
$env:ANTHROPIC_AUTH_TOKEN = "sk-litellm-local-only"  # 对应 LiteLLM master_key；没配则随便写
```

模型名建议在 Claude Code 内切到：
- `glm-4.7`
- 或 `claude-code`（与上面 litellm_config.yaml 的 alias 对应）

如果 Claude Code 固定使用某个 Claude 模型名（例如 UI 里默认的那一个），就把 `litellm_config.yaml` 里 `model_name` 改成它实际发过来的名字，同样映射到 `openai/glm-4.7` 即可。

### 3.3 Gemini CLI → 现实情况与可行方案

Gemini CLI 通常走 **Gemini 原生接口**，不是 OpenAI `/v1/chat/completions`，也不是 Anthropic `/v1/messages`。

因此：**仅靠 LiteLLM（OpenAI/Anthropic 兼容）无法让“官方 Gemini CLI”直接连到你的 vLLM 本地模型。**

可行方案只有两类：
- 方案 A（推荐）：用任何“OpenAI 兼容”的 CLI 来替代 Gemini CLI，把 `base_url` 指向 LiteLLM（本质上你已经有 Codex CLI 了）。
- 方案 B（需要额外适配层）：在 Gemini CLI 和 LiteLLM 之间加一个“Gemini API ↔ OpenAI ChatCompletions”的转换服务，把 Gemini CLI 的请求转换为 OpenAI 请求，再转发到 `http://127.0.0.1:4000/v1/chat/completions`。

如果你坚持要做方案 B，我建议先抓包/打印 Gemini CLI 实际调用的 URL 与请求体，再按它用到的最小 API 面实现一个轻量适配器。

## 4. 常见问题（你这套离线方案最容易踩的坑）

- vLLM 返回的 `model` 名和 CLI 指定的 `model` 不一致：优先用 `--served-model-name` 统一，再在 LiteLLM 里做 alias。
- Claude Code 只认 Anthropic Messages：必须走 `ANTHROPIC_BASE_URL`，而不是 `OPENAI_BASE_URL`。
- 并发多个终端访问：vLLM + LiteLLM 天然支持并发；真正瓶颈在显存、`max-model-len`、以及 `--gpu-memory-utilization`（需要时再调）。

## 附录：如果未来你要图片输入，应该怎么做

要图片支持，必须换多模态权重（例如 GLM-4V）。vLLM 的启动形态会不同，并且通常需要 `--trust-remote-code` 以及多模态限制参数（例如每次 prompt 允许的图片数量）。
