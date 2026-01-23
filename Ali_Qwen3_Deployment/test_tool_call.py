import openai
import json
import os

# 配置客户端指向 LiteLLM (模拟 Claude 协议) 或者直接指向 vLLM (OpenAI 协议)
# 这里演示直接连接 vLLM 的 OpenAI 兼容接口，验证工具调用是否正常
# 如果要测试 Claude 协议，请将 base_url 改为 http://localhost:4000 (LiteLLM)

client = openai.OpenAI(
    api_key="sk-empty",
    base_url="http://localhost:8000/v1"
)

# 定义一个简单的工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

model_name = "Qwen/Qwen3-235B-A22B-Instruct"

print(f"Testing model: {model_name}...")

try:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": "What's the weather like in Hangzhou today?"}
        ],
        tools=tools,
        tool_choice="auto",
    )

    print("\nResponse:")
    print(response.choices[0].message)

    # 检查是否触发了工具调用
    if response.choices[0].message.tool_calls:
        print("\n✅ Tool Call Successful!")
        for tool_call in response.choices[0].message.tool_calls:
            print(f"Function: {tool_call.function.name}")
            print(f"Arguments: {tool_call.function.arguments}")
    else:
        print("\n❌ Tool Call Failed (Model did not choose to use tool).")

except Exception as e:
    print(f"\n❌ API Error: {e}")
    print("If you see a 400 error, check server logs for schema validation issues.")
