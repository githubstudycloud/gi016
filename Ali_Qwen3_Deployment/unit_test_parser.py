
import json
import re
import ast
import os

# Copying the function from middleware_fix_qwen.py for testing
def parse_hermes_xml(content):
    print(f"Testing content: {content!r}")
    tool_calls = []
    
    pattern = r"<(tool_code|tool_call)>\s*(?:```json)?\s*(.*?)\s*(?:```)?\s*</\1>"
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        pattern_lazy = r"<(tool_code|tool_call)>\s*(?:```json)?\s*(.*?)\s*(?:```)?\s*$"
        matches = re.findall(pattern_lazy, content, re.DOTALL | re.IGNORECASE)

    for i, (tag_name, code_str) in enumerate(matches):
        print(f"  Match {i}: Tag={tag_name}, Content={code_str!r}")
        try:
            clean_json = code_str.strip()
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.IGNORECASE)
            clean_json = re.sub(r"\s*```$", "", clean_json)
            clean_json = clean_json.strip()
            
            if not clean_json: continue

            tool_call_data = None
            
            # Strategy 1: JSON
            try:
                tool_call_data = json.loads(clean_json)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: AST (Single quotes)
            if tool_call_data is None:
                try:
                    tool_call_data = ast.literal_eval(clean_json)
                except:
                    pass
            
            # Strategy 3: Regex for {...}
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
            
            # Case 1: {"tool": "bash", "command": "ls"} -> {"name": "bash", "arguments": {"command": "ls"}}
            if "name" not in tool_call_data and "tool" in tool_call_data:
                print(f"  ⚠️ Adapting 'tool' field: {clean_json}")
                tool_name = tool_call_data.pop("tool")
                if "arguments" not in tool_call_data:
                     tool_call_data = {
                         "name": tool_name,
                         "arguments": tool_call_data
                     }
                else:
                    tool_call_data["name"] = tool_name

            # Case 2: {"function": "bash", ...}
            if "name" not in tool_call_data and "function" in tool_call_data:
                 print(f"  ⚠️ Adapting 'function' field: {clean_json}")
                 tool_call_data["name"] = tool_call_data.pop("function")
            
            if tool_call_data:
                print(f"  ✅ Parsed: {tool_call_data}")
                tool_calls.append(tool_call_data)
            else:
                print(f"  ❌ Failed to parse: {clean_json}")

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            
    return tool_calls

# Test Cases
test_cases = [
    # 1. Standard Valid JSON
    """<tool_call>
    {"name": "test", "arguments": {"x": 1}}
    </tool_call>""",
    
    # 2. Single Quotes (Python dict)
    """<tool_code>
    {'name': 'test_py', 'arguments': {'x': 1}}
    </tool_code>""",
    
    # 3. Dirty text around JSON
    """<tool_call>
    Here is the tool call:
    {
        "name": "test_dirty",
        "arguments": {}
    }
    </tool_call>""",
    
    # 4. Markdown block
    """<tool_call>
    ```json
    {"name": "test_md", "arguments": {}}
    ```
    </tool_call>""",
    
    # 5. Broken JSON (should fail but handle gracefully)
    """<tool_call>
    {name: invalid}
    </tool_call>""",

    # 6. Non-standard "tool" + "command" format
    """<tool_call>
    {"tool": "bash", "command": "ls -la"}
    </tool_call>""",

    # 7. Non-standard "function" format
    """<tool_call>
    {"function": "get_weather", "arguments": {"location": "Beijing"}}
    </tool_call>"""
]

print("=== Running Unit Tests ===")
for t in test_cases:
    print("-" * 20)
    parse_hermes_xml(t)
