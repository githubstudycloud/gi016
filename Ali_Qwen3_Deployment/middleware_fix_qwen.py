import os
import json
import re
import uvicorn
import httpx
import time
import ast
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
    """尝试从文本中提取 Hermes 风格的 <tool_code> 或 Qwen 风格的 <tool_call> XML"""
    tool_calls = []
    
    # 1. 统一标签: 将 <tool_call> 替换为 <tool_code> 以便统一处理，或者支持两种
    # 我们支持两种标签：tool_code (Hermes) 和 tool_call (Qwen)
    
    # 匹配模式：支持 tool_code 或 tool_call
    # Group 1: 标签名 (tool_code|tool_call)
    # Group 2: 内容
    pattern = r"<(tool_code|tool_call)>\s*(?:```json)?\s*(.*?)\s*(?:```)?\s*</\1>"
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        # 备用：尝试匹配未闭合的标签
        pattern_lazy = r"<(tool_code|tool_call)>\s*(?:```json)?\s*(.*?)\s*(?:```)?\s*$"
        matches = re.findall(pattern_lazy, content, re.DOTALL | re.IGNORECASE)

    for i, (tag_name, code_str) in enumerate(matches):
        print(f"🔍 尝试解析工具内容片段 (Tag: {tag_name}): {code_str[:100]}...")
        
        try:
            # 清洗可能残留的 markdown 标记
            clean_json = code_str.strip()
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.IGNORECASE)
            clean_json = re.sub(r"\s*```$", "", clean_json)
            clean_json = clean_json.strip()
            
            if not clean_json: 
                print("⚠️ 内容为空，跳过")
                continue

            tool_call_data = None
            
            # 策略1: 直接 JSON 解析
            try:
                tool_call_data = json.loads(clean_json)
            except json.JSONDecodeError:
                # 策略2: 尝试 Python AST 解析 (容忍单引号)
                try:
                    tool_call_data = ast.literal_eval(clean_json)
                except:
                    pass
            
            # 策略3: 如果内容包含额外文本，尝试提取第一个 {...} 块
            if tool_call_data is None:
                json_match = re.search(r"(\{.*\})", clean_json, re.DOTALL)
                if json_match:
                    potential_json = json_match.group(1)
                    try:
                        tool_call_data = json.loads(potential_json)
                    except:
                        try:
                            tool_call_data = ast.literal_eval(potential_json)
                        except:
                            pass
            
            if tool_call_data is None:
                print(f"⚠️ 无法解析为 JSON 或 Python Dict: {clean_json}")
                continue
            
            # 验证必要字段
            if "name" not in tool_call_data:
                print(f"⚠️ 工具调用缺少 name 字段: {clean_json}")
                continue
                
            arguments = tool_call_data.get("arguments", {})
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)
            
            tool_calls.append({
                "id": f"call_{i}_{os.urandom(4).hex()}",
                "type": "function",
                "function": {
                    "name": tool_call_data.get("name"),
                    "arguments": arguments
                }
            })
        except Exception as e:
            print(f"⚠️ 解析工具调用发生异常: {e}\n原始内容: {code_str}")
            continue
            
    return tool_calls

def convert_claude_messages_to_openai(claude_body):
    """
    将 Claude 格式的 messages 请求转换为 OpenAI 格式
    同时处理历史记录中的 tool_use 和 tool_result，将其转换为 Hermes XML 格式
    """
    openai_messages = []
    
    # 1. 处理 system prompt
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
        
        text_parts = []
        
        # Claude 的 content 可能是列表（包含 text, tool_use, tool_result）
        if isinstance(content, list):
            for part in content:
                part_type = part.get("type")
                
                if part_type == "text":
                    text_parts.append(part.get("text", ""))
                    
                elif part_type == "tool_use":
                    # 将 Claude 的工具调用转换为 Hermes 的 <tool_code>
                    args_json = json.dumps(part.get("input", {}))
                    tool_xml = f"\n<tool_code>\n{{\"name\": \"{part['name']}\", \"arguments\": {args_json}}}\n</tool_code>"
                    text_parts.append(tool_xml)
                    
                elif part_type == "tool_result":
                    # 将 Claude 的工具结果转换为 Hermes 的 <tool_output>
                    res_content = part.get("content", "")
                    res_text = ""
                    if isinstance(res_content, str):
                        res_text = res_content
                    elif isinstance(res_content, list):
                        for sub in res_content:
                            if sub.get("type") == "text":
                                res_text += sub.get("text", "")
                    
                    # 简化 output，防止过长
                    tool_output_xml = f"\n<tool_output>\n{res_text}\n</tool_output>"
                    text_parts.append(tool_output_xml)
                    
        elif isinstance(content, str):
            text_parts.append(content)
            
        final_content = "".join(text_parts)
        openai_messages.append({"role": role, "content": final_content})
            
    # 3. 处理 tools (提取定义用于注入 System Prompt)
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
    """生成 Qwen 2.5/3 官方推荐的工具定义 Prompt"""
    
    # 1. 转换为 OpenAI 标准格式 (type: function)
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        })
    
    tools_json = json.dumps(openai_tools, indent=None) # Compact JSON
    
    prompt = f"""# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>
"""
    return prompt

def convert_openai_response_to_claude(openai_resp):
    """将 OpenAI 格式的响应转换为 Claude 格式"""
    choice = openai_resp["choices"][0]
    message = choice["message"]
    
    claude_content = []
    stop_reason = "end_turn"
    
    # 1. 处理文本内容
    raw_content = message.get("content", "")
    
    # 尝试移除 raw_content 中的 <tool_code> 或 <tool_call> 部分，只保留思考文本
    display_text = re.sub(r"<(tool_code|tool_call)>.*?</\1>", "", raw_content, flags=re.DOTALL).strip()
    # 还要移除可能的残留闭合标签
    display_text = re.sub(r"</(tool_code|tool_call)>", "", display_text).strip()
    
    if display_text:
        claude_content.append({
            "type": "text",
            "text": display_text
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

@app.post("/v1/messages")
@app.post("/messages")
async def proxy_claude_messages(request: Request):
    try:
        body = await request.json()
        print("\n📨 [Claude Request] 收到 /v1/messages 请求")
        
        # 1. 估算 Token (80k 保护)
        total_chars = 0
        if "system" in body:
             total_chars += len(body["system"])
        for msg in body.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
        
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
        stop_tokens = [] # 动态停止词
        
        if raw_tools:
            tool_prompt = generate_tool_system_prompt(raw_tools)
            stop_tokens = ["</tool_call>", "</tool_code>"] # 告诉模型写完工具调用就停
            
            # 策略：如果 messages 里没有 system，就新建一个。
            # 如果有，我们在 User 消息里注入提醒，而不是仅仅修改 System Prompt
            # 因为长对话中 System Prompt 容易被遗忘
            
            # A. 确保 System Prompt 存在
            system_msg_index = -1
            for i, msg in enumerate(openai_messages):
                if msg["role"] == "system":
                    system_msg_index = i
                    break
            
            if system_msg_index >= 0:
                # 替换或追加到现有 system
                openai_messages[system_msg_index]["content"] += "\n\n" + tool_prompt
            else:
                # 插入新的 system 消息到开头
                openai_messages.insert(0, {
                    "role": "system",
                    "content": tool_prompt
                })
            
            # B. [关键] 在最后一条 User Message 追加强力提醒
            # 只有当用户确实在说话时才追加
            if openai_messages and openai_messages[-1]["role"] == "user":
                reminder = "\n\n(IMPORTANT: If you need to use a tool, output the JSON inside <tool_call> tags immediately. Do not explain.)"
                openai_messages[-1]["content"] += reminder
            
            print(f"💉 已注入 {len(raw_tools)} 个工具定义 (System + User Reminder)")

        # 3. 构建发送给 vLLM 的请求
        openai_req = {
            "model": TARGET_MODEL_NAME,
            "messages": openai_messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
            "stream": False,
            "stop": stop_tokens if stop_tokens else None # 使用 Stop Token 防止废话
        }
        
        # 🚫 删除 API 参数
        if "tools" in openai_req: del openai_req["tools"]
        if "tool_choice" in openai_req: del openai_req["tool_choice"]

        print(f"🚀 转发给 vLLM (端口 8001)...")
        response = await client.post(
            f"{VLLM_API_BASE}/chat/completions",
            json=openai_req,
            headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
            timeout=600.0
        )
        
        if response.status_code != 200:
            print(f"❌ vLLM 报错 (Status {response.status_code}): {response.text}")
            return JSONResponse(content={"error": f"vLLM Error: {response.text}"}, status_code=response.status_code)
            
        openai_result = response.json()
        
        # === 调试日志 ===
        raw_response_content = openai_result["choices"][0]["message"].get("content", "")
        print(f"🔍 [Model Response Preview]: {raw_response_content[:200]}...")
        if "<tool_call>" in raw_response_content or "<tool_code>" in raw_response_content:
            print("✨ 检测到 XML 标记！")
        else:
            print("⚠️ 未检测到 XML 标记 (可能是纯文本回复)")
        # ==============

        # 4. 检查并修复 XML 工具调用
        choice = openai_result["choices"][0]
        content = choice["message"].get("content", "") or ""
        
        # 如果因为 stop token 停止，我们需要把被截断的闭合标签补回来以便正则匹配
        if openai_result["choices"][0].get("finish_reason") == "stop":
             # 检查是否以未闭合的标签结尾
             if "<tool_call>" in content and "</tool_call>" not in content:
                 content += "</tool_call>"
             elif "<tool_code>" in content and "</tool_code>" not in content:
                 content += "</tool_code>"
        
        if "<tool_call>" in content or "<tool_code>" in content:
            print(f"🛠️ 正在解析 XML 工具调用...")
            extracted_tools = parse_hermes_xml(content)
            if extracted_tools:
                print(f"✅ 解析成功: {len(extracted_tools)} 个工具")
                choice["message"]["tool_calls"] = extracted_tools
            else:
                print(f"❌ 解析失败: 找到了标签但无法提取 JSON")
        
        # 5. 协议转换: OpenAI -> Claude
        claude_response = convert_openai_response_to_claude(openai_result)
        
        return JSONResponse(content=claude_response)

    except Exception as e:
        print(f"❌ 严重错误: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print(f"🚀 Claude 协议兼容层已启动 (vLLM 400 修复版 + 增强调试)")
    print(f"🎯 目标模型: {TARGET_MODEL_NAME}")
    print(f"🔑 API Key: {VLLM_API_KEY}")
    print(f"📡 监听端口: {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
