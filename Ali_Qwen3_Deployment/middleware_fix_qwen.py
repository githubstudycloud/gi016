import os
import json
import re
import uvicorn
import httpx
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ================= 用户配置区域 =================
# 您的 vLLM 服务地址 (根据您的描述，端口是 8001)
VLLM_API_BASE = "http://localhost:8001/v1"

# 中间件监听端口
PORT = 4000

# 上下文限制配置 (单位: Token)
# Claude Code 默认认为模型有 200k，但您的硬件限制是 80k (81920)
# 我们在这里设置一个安全阈值，如果请求超过这个值，直接拦截并提示用户清理上下文
MAX_CONTEXT_TOKENS = 80000 

# 自动获取模型名称 (None = 自动从 vLLM 获取)
ACTUAL_MODEL_NAME = None 
# ===========================================

app = FastAPI()
client = httpx.AsyncClient(timeout=600.0)

async def get_running_model_name():
    """自动从 vLLM 获取当前运行的模型名称"""
    global ACTUAL_MODEL_NAME
    if ACTUAL_MODEL_NAME:
        return ACTUAL_MODEL_NAME
    
    try:
        print(f"🔍 正在连接 {VLLM_API_BASE}/models 获取模型名称...")
        resp = await client.get(f"{VLLM_API_BASE}/models")
        if resp.status_code == 200:
            data = resp.json()
            model_id = data["data"][0]["id"]
            print(f"✅ 检测到 vLLM 正在运行模型: {model_id}")
            ACTUAL_MODEL_NAME = model_id
            return model_id
    except Exception as e:
        print(f"⚠️ 无法自动获取模型名称: {e}")
        return "Qwen/Qwen3-235B-A22B-Instruct"

def estimate_tokens(text):
    """粗略估算 Token 数 (1 token ≈ 3-4 字符)"""
    # 这是一个保守估算，确保安全
    return len(text) // 3

def parse_hermes_xml(content):
    """尝试从文本中提取 Hermes 风格的 <tool_code> XML"""
    tool_calls = []
    pattern = r"<tool_code>\s*(.*?)\s*</tool_code>"
    matches = re.findall(pattern, content, re.DOTALL)
    
    for i, code_str in enumerate(matches):
        try:
            clean_json = re.sub(r"^```json\s*|\s*```$", "", code_str.strip(), flags=re.IGNORECASE)
            tool_call_data = json.loads(clean_json)
            tool_calls.append({
                "id": f"call_{i}_{os.urandom(4).hex()}",
                "type": "function",
                "function": {
                    "name": tool_call_data.get("name"),
                    "arguments": json.dumps(tool_call_data.get("arguments", {}))
                }
            })
        except json.JSONDecodeError:
            print(f"⚠️ 解析工具调用 JSON 失败: {code_str}")
            continue
    return tool_calls

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def proxy_chat(request: Request):
    try:
        body = await request.json()
        
        # === 新增：上下文长度保护 ===
        # 提取所有消息内容并估算长度
        total_chars = 0
        if "messages" in body:
            for msg in body["messages"]:
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    # 处理多模态或其他复杂格式
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            total_chars += len(part["text"])
        
        estimated_tokens = estimate_tokens(" " * total_chars) # Hacky way to reuse function
        # 更直接的计算
        estimated_tokens = total_chars // 3

        if estimated_tokens > MAX_CONTEXT_TOKENS:
            print(f"⚠️ 请求过长！估算 Tokens: {estimated_tokens} > 限制: {MAX_CONTEXT_TOKENS}")
            # 返回一个特定的错误，提示用户使用 /compact
            error_msg = (
                f"Context limit reached! Estimated {estimated_tokens} tokens (Limit: {MAX_CONTEXT_TOKENS}). "
                "Please run '/compact' in Claude Code to clear history."
            )
            return JSONResponse(
                content={
                    "error": {
                        "message": error_msg,
                        "type": "context_length_exceeded",
                        "code": 400
                    }
                },
                status_code=400
            )
        # ============================

        target_model = await get_running_model_name()
        if target_model:
            body["model"] = target_model
        
        if "metadata" in body:
            del body["metadata"]
        
        original_stream = body.get("stream", False)
        body["stream"] = False 
        
        response = await client.post(
            f"{VLLM_API_BASE}/chat/completions",
            json=body,
            headers={"Authorization": "Bearer sk-empty"}
        )
        
        if response.status_code != 200:
            return JSONResponse(content=response.json(), status_code=response.status_code)
            
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            message = choice["message"]
            content = message.get("content", "") or ""
            
            if "<tool_code>" in content:
                print(f"🛠️ 检测到原始 XML，正在进行格式转换...")
                extracted_tools = parse_hermes_xml(content)
                if extracted_tools:
                    print(f"✅ 成功提取 {len(extracted_tools)} 个工具调用")
                    message["tool_calls"] = extracted_tools
                    message["content"] = None 
                    choice["finish_reason"] = "tool_calls"
        
        return result

    except Exception as e:
        print(f"❌ 代理发生严重错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.on_event("startup")
async def startup_event():
    await get_running_model_name()

if __name__ == "__main__":
    print(f"🚀 Qwen3 专用修复中间件 (80k保护版) 已启动")
    print(f"🛡️ 上下文限制: {MAX_CONTEXT_TOKENS} tokens")
    print(f"📡 连接 vLLM 地址: {VLLM_API_BASE}")
    print(f"👉 请配置 Claude Code 使用: http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
