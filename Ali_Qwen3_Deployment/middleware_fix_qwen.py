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

# 中间件监听端口 (Claude Code 将连接这个端口)
# 保持 4000 不变，这样方便配置
PORT = 4000

# 自动获取模型名称
# 如果设置为 None，脚本启动时会自动去 vLLM 查询正在运行的模型名称
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
            # 获取第一个模型的 ID
            model_id = data["data"][0]["id"]
            print(f"✅ 检测到 vLLM 正在运行模型: {model_id}")
            ACTUAL_MODEL_NAME = model_id
            return model_id
    except Exception as e:
        print(f"⚠️ 无法自动获取模型名称: {e}")
        return "Qwen/Qwen3-235B-A22B-Instruct" # 默认回退值

def parse_hermes_xml(content):
    """
    尝试从文本中提取 Hermes 风格的 <tool_code> XML 并转换为 OpenAI 格式的 tool_calls
    """
    tool_calls = []
    
    # 匹配 <tool_code>...</tool_code>
    pattern = r"<tool_code>\s*(.*?)\s*</tool_code>"
    matches = re.findall(pattern, content, re.DOTALL)
    
    for i, code_str in enumerate(matches):
        try:
            # 有时候模型会在 JSON 外面包一层 markdown 代码块，如 ```json ... ```
            # 需要清洗掉
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
        # 1. 获取客户端 (Claude Code) 发送的请求
        body = await request.json()
        
        # 2. 修正模型名称
        # Claude Code 会发送 "claude-3-5-sonnet..."，我们需要把它改成 vLLM 实际运行的模型名
        target_model = await get_running_model_name()
        if target_model:
            body["model"] = target_model
        
        # 3. 清理不支持的参数 (防止 400 错误)
        if "metadata" in body:
            del body["metadata"]
        
        # 4. 强制关闭流式输出
        # 为了能完整解析 XML，我们必须拦截整个响应，不能流式传输
        original_stream = body.get("stream", False)
        body["stream"] = False 
        
        # 5. 转发请求给 vLLM (端口 8001)
        response = await client.post(
            f"{VLLM_API_BASE}/chat/completions",
            json=body,
            headers={"Authorization": "Bearer sk-empty"}
        )
        
        if response.status_code != 200:
            print(f"❌ vLLM 返回错误: {response.status_code} - {response.text}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
            
        result = response.json()
        
        # 6. 核心逻辑：检查并修复工具调用
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            message = choice["message"]
            content = message.get("content", "") or ""
            
            # 如果内容里包含 <tool_code>，说明模型想调用工具但 vLLM 没解析出来
            if "<tool_code>" in content:
                print(f"🛠️ 检测到原始 XML，正在进行格式转换...")
                extracted_tools = parse_hermes_xml(content)
                
                if extracted_tools:
                    print(f"✅ 成功提取 {len(extracted_tools)} 个工具调用")
                    message["tool_calls"] = extracted_tools
                    # 按照 OpenAI 规范，如果是工具调用，content 通常为 null
                    # 或者保留 <think> 标签的内容
                    message["content"] = None 
                    choice["finish_reason"] = "tool_calls"
        
        return result

    except Exception as e:
        print(f"❌ 代理发生严重错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.on_event("startup")
async def startup_event():
    # 启动时预先获取一次模型名称
    await get_running_model_name()

if __name__ == "__main__":
    print(f"🚀 Qwen3 专用修复中间件已启动")
    print(f"📡 连接 vLLM 地址: {VLLM_API_BASE}")
    print(f"👂 本地监听端口: {PORT}")
    print(f"👉 请配置 Claude Code 使用: http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
