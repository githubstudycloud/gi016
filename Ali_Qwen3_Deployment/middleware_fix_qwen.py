import os
import json
import re
import uvicorn
import httpx
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ================= 用户配置区域 =================
# 您的 vLLM 服务地址
VLLM_API_BASE = "http://localhost:8001/v1"

# 中间件监听端口
PORT = 4000

# 您的自定义模型名称 (在这里写死)
TARGET_MODEL_NAME = "Qwen/Qwen3-235B-A22B-Instruct" 

# vLLM 的 API Key (在这里写死)
VLLM_API_KEY = "empty"

# 上下文限制 (80k)
MAX_CONTEXT_TOKENS = 80000 
# ===========================================

app = FastAPI()
client = httpx.AsyncClient(timeout=600.0)

def estimate_tokens(text):
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

def convert_claude_messages_to_openai(claude_body):
    """将 Claude 格式的 messages 请求转换为 OpenAI 格式"""
    openai_messages = []
    
    # 1. 处理 system prompt
    if "system" in claude_body:
        openai_messages.append({
            "role": "system",
            "content": claude_body["system"]
        })
        
    # 2. 处理 messages 列表
    for msg in claude_body.get("messages", []):
        role = msg["role"]
        content = msg["content"]
        
        # Claude 的 content 可能是列表（包含 text 或 image）
        if isinstance(content, list):
            new_content = ""
            for part in content:
                if part.get("type") == "text":
                    new_content += part.get("text", "")
                # 暂时忽略 image，因为 vLLM OpenAI 接口通常需要 URL 或 base64
                # 如果需要支持多模态，这里需要更复杂的转换
            
            openai_messages.append({"role": role, "content": new_content})
        else:
            openai_messages.append({"role": role, "content": content})
            
    # 3. 处理 tools
    tools = []
    if "tools" in claude_body:
        for tool in claude_body["tools"]:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["input_schema"] # Claude input_schema -> OpenAI parameters
                }
            })
            
    return openai_messages, tools

def convert_openai_response_to_claude(openai_resp):
    """将 OpenAI 格式的响应转换为 Claude 格式"""
    choice = openai_resp["choices"][0]
    message = choice["message"]
    
    claude_content = []
    stop_reason = "end_turn"
    
    # 1. 处理文本内容
    if message.get("content"):
        claude_content.append({
            "type": "text",
            "text": message["content"]
        })
        
    # 2. 处理工具调用
    if message.get("tool_calls"):
        stop_reason = "tool_use"
        for tool_call in message["tool_calls"]:
            claude_content.append({
                "type": "tool_use",
                "id": tool_call["id"],
                "name": tool_call["function"]["name"],
                "input": json.loads(tool_call["function"]["arguments"])
            })
            
    return {
        "id": openai_resp["id"],
        "type": "message",
        "role": "assistant",
        "content": claude_content,
        "model": TARGET_MODEL_NAME,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": openai_resp["usage"]["prompt_tokens"],
            "output_tokens": openai_resp["usage"]["completion_tokens"]
        }
    }

# 拦截 Claude 的核心路由
@app.post("/v1/messages")
@app.post("/messages")
async def proxy_claude_messages(request: Request):
    try:
        body = await request.json()
        print("📨 收到 Claude 协议请求 (/v1/messages)")
        
        # 1. 估算 Token (简单保护)
        # 这里只估算 messages 里的文本长度
        total_chars = 0
        if "system" in body:
             total_chars += len(body["system"])
        for msg in body.get("messages", []):
            if isinstance(msg["content"], str):
                total_chars += len(msg["content"])
        
        if (total_chars // 3) > MAX_CONTEXT_TOKENS:
             return JSONResponse(
                content={
                    "type": "error",
                    "error": {
                        "type": "invalid_request_error",
                        "message": f"Context limit reached! Please run /compact."
                    }
                },
                status_code=400
            )

        # 2. 协议转换: Claude -> OpenAI
        openai_messages, tools = convert_claude_messages_to_openai(body)
        
        openai_req = {
            "model": TARGET_MODEL_NAME, # 使用硬编码的模型名
            "messages": openai_messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
            "stream": False # 强制关闭流式，以便修复工具调用
        }
        
        if tools:
            openai_req["tools"] = tools
            openai_req["tool_choice"] = "auto"

        # 3. 发送给 vLLM (OpenAI 接口)
        print(f"🚀 转发给 vLLM (模型: {TARGET_MODEL_NAME})...")
        response = await client.post(
            f"{VLLM_API_BASE}/chat/completions",
            json=openai_req,
            headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
            timeout=600.0
        )
        
        if response.status_code != 200:
            print(f"❌ vLLM 报错: {response.text}")
            return JSONResponse(content={"error": "vLLM error"}, status_code=response.status_code)
            
        openai_result = response.json()
        
        # 4. 检查并修复 XML 工具调用
        choice = openai_result["choices"][0]
        content = choice["message"].get("content", "") or ""
        
        if "<tool_code>" in content:
            print(f"🛠️ 捕获到 XML 工具调用，正在修复...")
            extracted_tools = parse_hermes_xml(content)
            if extracted_tools:
                choice["message"]["tool_calls"] = extracted_tools
                # Claude 协议允许 tool_use 和 text 同时存在，所以不需要清空 content
                # 但为了整洁，如果只有工具调用，我们可以把 XML 从 content 里去掉
                # 这里简单起见，保留 content (作为思考过程) 也是可以的
        
        # 5. 协议转换: OpenAI -> Claude
        claude_response = convert_openai_response_to_claude(openai_result)
        
        print("✅ 响应成功返回")
        return JSONResponse(content=claude_response)

    except Exception as e:
        print(f"❌ 严重错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print(f"🚀 Claude 协议兼容层已启动")
    print(f"🎯 目标模型: {TARGET_MODEL_NAME}")
    print(f"🔑 API Key: {VLLM_API_KEY}")
    print(f"📡 监听端口: {PORT} (请配置 Claude Code Base URL 为 http://localhost:{PORT})")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
