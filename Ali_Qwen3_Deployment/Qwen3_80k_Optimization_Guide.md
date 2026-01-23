# Qwen3 80k 上下文最优配置指南

本文档针对 **80k (81920 tokens)** 上下文限制的环境，提供从后端 (vLLM) 到前端 (Claude Code) 的全链路优化配置方案。

## 1. 核心问题说明

**Claude Code 的机制**:
Claude Code 客户端默认认为它连接的是 Claude 3.5 Sonnet，因此它会假设服务器支持 **200k** 上下文。如果您的实际限制是 **80k**，当对话历史过长时，Claude Code 依然会尝试发送超长请求，导致 vLLM 后端报错 (OOM) 或崩溃。

**解决方案**:
由于无法直接修改 Claude Code 的内部配置文件，我们采用 **“中间件拦截 + 主动瘦身”** 的策略。

---

## 2. 后端 vLLM 最优配置 (启动参数)

为了确保在 80k 负载下稳定运行，请更新您的启动脚本，重点关注以下参数：

```powershell
python -m vllm.entrypoints.openai.api_server `
    --model "您的模型路径" `
    --max-model-len 81920 `        # 【关键】强制限制最大长度为 80k
    --gpu-memory-utilization 0.95 `
    --enable-chunked-prefill `     # 【推荐】开启分块预填充，防止长 Prompt 瞬间爆显存
    --max-num-batched-tokens 81920 ` # 允许处理的最大批次 token
    --enable-auto-tool-choice `
    --quantization fp8 `
    --port 8001
```

*   **`--max-model-len 81920`**: 这是物理防线，确保 vLLM 不会尝试分配超过此限制的 KV Cache。
*   **`--enable-chunked-prefill`**: 处理 80k 上下文时，如果没有这个参数，首字延迟会极高，甚至直接 OOM。

---

## 3. 中间件保护配置

我们已更新 `middleware_fix_qwen.py`，增加了**流量卫士**功能。

### 新功能：自动拦截
脚本现在会实时估算 Claude Code 发送的请求长度。
*   **阈值**: 80,000 Tokens (可修改 `MAX_CONTEXT_TOKENS` 变量)
*   **行为**: 如果请求超过阈值，脚本会直接拦截，不会发给 vLLM（保护显存），并返回如下错误给 Claude Code：
    > `Context limit reached! ... Please run '/compact' in Claude Code to clear history.`

### 如何启用
无需额外操作，重新运行脚本即可：

```powershell
python middleware_fix_qwen.py
```

---

## 4. Claude Code 使用技巧 (用户侧)

既然硬件限制是 80k，您需要养成以下使用习惯来保持“高性能”：

### A. 定期使用 `/compact`
这是 Claude Code 的官方命令，用于压缩对话历史。
*   **何时使用**: 当中间件报错提示 Context limit reached 时，或者您感觉回复变慢时。
*   **作用**: 它会将之前的长对话总结为一个摘要，释放大量 Context 空间，同时保留核心记忆。

### B. 使用 `/clear` (慎用)
*   **作用**: 清空所有历史，重新开始。
*   **何时使用**: 开始一个全新的无关任务时。

### C. 避免一次性读取超大文件
*   尽量不要一次性 `/add` 几十个文件或几万行的代码库。
*   使用 `grep` 或特定文件名来精确查找上下文。

---

## 5. 总结：最优配置清单

| 组件 | 配置项 | 值 | 说明 |
| :--- | :--- | :--- | :--- |
| **vLLM** | `--max-model-len` | `81920` | 物理显存限制 |
| **vLLM** | `--enable-chunked-prefill` | `True` | 优化长文性能 |
| **中间件** | `MAX_CONTEXT_TOKENS` | `80000` | 应用层熔断保护 |
| **Claude Code** | Base URL | `http://localhost:4000` | 连接中间件 |
| **操作习惯** | 定期命令 | `/compact` | 主动释放空间 |

遵循此配置，您可以在 80k 的限制下获得最流畅的体验，同时避免显存溢出导致的崩溃。
