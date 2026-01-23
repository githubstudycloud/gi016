import requests
import json
import sys

# Middleware address
API_URL = "http://localhost:4000/v1/messages"

def test_claude_tool_call():
    print(f"🚀 Testing Middleware at {API_URL}...")
    
    # Claude-style request body
    payload = {
        "model": "claude-3-opus-20240229", # Client might send this, middleware ignores/logs it but uses TARGET_MODEL_NAME internally
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "What is the weather in Shanghai today?"}
        ],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        ]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Response Received:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Check for tool usage
            content = result.get("content", [])
            has_tool = False
            for item in content:
                if item.get("type") == "tool_use":
                    has_tool = True
                    print(f"\n🎉 Tool Call Detected: {item.get('name')} -> {item.get('input')}")
            
            if not has_tool:
                print("\n⚠️ Response is text-only (Tool call failed).")
                # Print raw text to see if XML leaked
                for item in content:
                    if item.get("type") == "text":
                        print(f"Text: {item.get('text')}")
        else:
            print(f"\n❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Connection Failed: {e}")
        print("Make sure middleware_fix_qwen.py is running on port 4000.")

if __name__ == "__main__":
    test_claude_tool_call()
