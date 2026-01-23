# 启动 vLLM 服务器
# 请确保已安装 vllm: pip install vllm
# 显存需求提示: Qwen3-235B-A22B (FP8) 需要约 250GB+ 显存，建议使用 4xH100 或 4xH20

# 设置 CUDA 可见设备 (根据实际情况修改)
$env:CUDA_VISIBLE_DEVICES="0,1,2,3"

# 启动命令
# --enable-auto-tool-choice: 允许模型自动决定是否调用工具
# --max-model-len: 设置最大上下文长度，Qwen3 支持很长，但受限于显存
# --tensor-parallel-size: GPU 数量
python -m vllm.entrypoints.openai.api_server `
    --model Qwen/Qwen3-235B-A22B-Instruct `
    --trust-remote-code `
    --tensor-parallel-size 4 `
    --gpu-memory-utilization 0.95 `
    --max-model-len 32768 \
    --enable-auto-tool-choice \
    --tool-call-parser hermes `
    --quantization fp8 \`
    --port 8000 `
    --served-model-name Qwen/Qwen3-235B-A22B-Instruct
