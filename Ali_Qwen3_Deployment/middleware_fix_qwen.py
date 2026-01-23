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
# trust_env=False: 禁止读取系统代理环境变量 (HTTP_PROXY 等)，确保请求直接发送给局域网/本地 vLLM
client = httpx.AsyncClient(timeout=600.0, trust_env=False)

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
    # 我们稍后会在这里注入工具定义，所以这里只提取原始 system
    system_content = claude_body.get("system", "")
    if system_content:
        openai_messages.append({
            "role": "system",
            "content": system_content
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
                # 暂时忽略 image
            
            openai_messages.append({"role": role, "content": new_content})
        else:
            openai_messages.append({"role": role, "content": content})
            
    # 3. 处理 tools
    # 注意：我们不再返回 tools 列表给 vLLM API，而是返回 raw_tools 用于生成 System Prompt
    raw_tools = []
    if "tools" in claude_body:
        for tool in claude_body["tools"]:
            raw_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool["input_schema"]
            })
            
    return openai_messages, raw_tools

def generate_tool_system_prompt(tools):
    """生成 Hermes/Qwen 风格的工具定义 Prompt"""
    tools_json = json.dumps(tools, indent=2)
    prompt = f"""
You have access to the following tools:
<tools>
{tools_json}
</tools>

When you need to call a tool, please output the tool call inside <tool_code> tags.
The format should be a JSON object with "name" and "arguments" keys.
Example:
<tool_code>
{{"name": "get_weather", "arguments": {{"location": "Beijing"}}}}
</tool_code>
"""
    return prompt

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
        
        # 1. 估算 Token (80k 保护)
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
        openai_messages, raw_tools = convert_claude_messages_to_openai(body)
        
        # === 核心修正：工具 Prompt 注入 ===
        # 如果有工具，我们手动把它们注入到 System Prompt 中
        # 而不是通过 API 的 tools 参数传递 (因为 vLLM 没配 parser 会报错)
        if raw_tools:
            tool_prompt = generate_tool_system_prompt(raw_tools)
            
            # 检查 messages 里是否已经有 system 消息
            system_msg_index = -1
            for i, msg in enumerate(openai_messages):
                if msg["role"] == "system":
                    system_msg_index = i
                    break
            
            if system_msg_index >= 0:
                # 追加到现有 system 后面
                openai_messages[system_msg_index]["content"] += "\n\n" + tool_prompt
            else:
                # 插入新的 system 消息到开头
                openai_messages.insert(0, {
                    "role": "system",
                    "content": tool_prompt
                })
            
            print(f"💉 已注入 {len(raw_tools)} 个工具定义到 System Prompt")

        openai_req = {
            "model": TARGET_MODEL_NAME,
            "messages": openai_messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
            "stream": False # 强制关闭流式
        }
        
        # 注意：这里不再设置 openai_req["tools"]，完全依赖 Prompt

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
                # 不清空 content，保留思考过程
        
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
