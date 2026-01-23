
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
    </tool_call>"""
]

print("=== Running Unit Tests ===")
for t in test_cases:
    print("-" * 20)
    parse_hermes_xml(t)
