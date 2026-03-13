#!/usr/bin/env python
"""
Documentation Agent with tools: read_file, list_files.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

if not API_KEY or not API_BASE or not MODEL:
    print("Missing LLM config in .env.agent.secret", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.absolute()

def safe_path(user_path: str) -> Path:
    """Prevent path traversal."""
    target = (PROJECT_ROOT / user_path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        raise ValueError("Access outside project root")
    return target

def read_file(path: str) -> str:
    """Read file contents."""
    try:
        target = safe_path(path)
        if not target.is_file():
            return f"Error: {path} not found"
        return target.read_text()
    except Exception as e:
        return f"Error: {e}"

def list_files(path: str = ".") -> str:
    """List directory contents."""
    try:
        target = safe_path(path)
        if not target.is_dir():
            return f"Error: {path} not a directory"
        return "\n".join(str(p.relative_to(PROJECT_ROOT)) for p in target.iterdir())
    except Exception as e:
        return f"Error: {e}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path"}
                },
                "required": ["path"]
            }
        }
    }
]

def call_llm(messages, tools=None, tool_choice="auto"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    resp = requests.post(f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def execute_tool_call(tc):
    name = tc["function"]["name"]
    args = json.loads(tc["function"]["arguments"])
    if name == "read_file":
        result = read_file(args["path"])
    elif name == "list_files":
        result = list_files(args.get("path", "."))
    else:
        result = f"Unknown tool: {name}"
    return {
        "role": "tool",
        "tool_call_id": tc["id"],
        "content": result
    }

def run_agent(question: str) -> dict:
    system_prompt = """You are a documentation agent. Use list_files to discover wiki files, then read_file to find answers. 
Always include the source file path and section anchor in the final answer. Respond in JSON format with answer and source fields."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    tool_calls_log = []
    max_steps = 10

    for _ in range(max_steps):
        response = call_llm(messages, tools=TOOLS)
        msg = response["choices"][0]["message"]

        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tool_calls_log.append({
                    "tool": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                    "result": None  # will fill after execution
                })
                messages.append({"role": "assistant", "tool_calls": [tc]})
                tool_result = execute_tool_call(tc)
                tool_calls_log[-1]["result"] = tool_result["content"]
                messages.append(tool_result)
        else:
            # Final answer
            content = msg["content"]
            try:
                # Try to parse as JSON
                answer_data = json.loads(content)
                answer = answer_data.get("answer", content)
                source = answer_data.get("source", "")
            except:
                answer = content
                source = ""
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }

    return {"answer": "Max steps reached", "source": "", "tool_calls": tool_calls_log}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'Your question'", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    result = run_agent(question)
    print(json.dumps(result, ensure_ascii=False))
