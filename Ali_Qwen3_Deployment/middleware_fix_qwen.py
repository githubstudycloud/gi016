import os
import json
import re
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

# ================= 配置区域 =================
# vLLM 服务的地址 (假设它没有正确配置 --tool-call-parser)
VLLM_API_BASE = "http://localhost:8000/v1"
# 监听端口 (Claude Code 将连接这个端口)
PORT = 4000
# ===========================================

app = FastAPI()
client = httpx.AsyncClient(timeout=600.0)

def parse_hermes_xml(content):
    """
    尝试从文本中提取 Hermes 风格的 <tool_code> XML 并转换为 OpenAI 格式的 tool_calls
    """
    tool_calls = []
    
    # 正则匹配 <tool_code>...</tool_code>
    # 注意：Qwen/Hermes 有时会输出 ```xml ... ``` 或者直接 <tool_code>
    pattern = r"<tool_code>\s*(.*?)\s*</tool_code>"
    matches = re.findall(pattern, content, re.DOTALL)
    
    for i, code_str in enumerate(matches):
        try:
            # Hermes 的 tool_code 内部通常是 JSON
            # 例如: {"name": "get_weather", "arguments": {"location": "Beijing"}}
            tool_call_data = json.loads(code_str)
            
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
        # 1. 获取客户端 (Claude Code) 发送的请求
        body = await request.json()
        
        # 2. 预处理：Claude 发送的 max_tokens 可能会很大，vLLM 可能会报错
        # 也可以在这里做 drop_params 的逻辑
        if "metadata" in body:
            del body["metadata"]
        
        # 3. 转发请求给 vLLM
        # 注意：我们必须开启 stream=False 以便完整接收后解析 XML
        # 如果客户端请求 stream=True，这里会强制转为非流式处理后再返回（可能会增加首字延迟）
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
        
        # 4. 核心逻辑：检查 vLLM 是否返回了 tool_calls
        choice = result["choices"][0]
        message = choice["message"]
        content = message.get("content", "") or ""
        
        # 如果 vLLM 没解析出来 tool_calls，但内容里有 <tool_code>
        if not message.get("tool_calls") and "<tool_code>" in content:
            print(f"🔍 检测到原始 XML 工具调用，正在修补...")
            extracted_tools = parse_hermes_xml(content)
            
            if extracted_tools:
                print(f"✅ 成功提取 {len(extracted_tools)} 个工具调用")
                message["tool_calls"] = extracted_tools
                # 通常提取完工具后，content 应该置空，或者是保留思考过程
                # 这里简单起见，如果只包含工具调用代码，则清空 content
                # 实际生产中可能需要更精细的处理（保留 <think> 标签等）
                message["content"] = None 
                choice["finish_reason"] = "tool_calls"
        
        # 5. 返回给客户端
        # 如果客户端原先请求的是 stream，理论上我们需要模拟 SSE 流
        # 但为了简化，我们直接返回 JSON（大多数客户端能兼容）
        # 如果必须支持流，代码会复杂很多
        
        return result

    except Exception as e:
        print(f"❌ 代理发生错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print(f"🚀 Qwen3 修复中间件已启动，监听端口: {PORT}")
    print(f"🔗 请将 Claude Code Base URL 设置为: http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
