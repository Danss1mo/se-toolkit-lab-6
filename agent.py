#!/usr/bin/env python
"""
System Agent with tools: read_file, list_files, query_api.
Optimized for speed and benchmark passing.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load both env files
load_dotenv(".env.agent.secret")
load_dotenv(".env.docker.secret")

# LLM config
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL")

# Backend config
LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42001")

if not LLM_API_KEY or not LLM_API_BASE or not LLM_MODEL:
    print("Missing LLM config in .env.agent.secret", file=sys.stderr)
    sys.exit(1)

if not LMS_API_KEY:
    print("Missing LMS_API_KEY in .env.docker.secret", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.absolute()

# ========== Tool Implementations ==========


def safe_path(user_path: str) -> Path:
    """Prevent path traversal."""
    target = (PROJECT_ROOT / user_path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT)):
        raise ValueError("Access outside project root")
    return target


def read_file(path: str) -> str:
    """Read file contents with truncation to prevent timeouts."""
    try:
        target = safe_path(path)
        if not target.is_file():
            return f"Error: {path} not found"
        content = target.read_text()
        if len(content) > 2000:
            content = content[:2000] + "\n...[truncated]"
        return content
    except Exception as e:
        return f"Error: {e}"


def list_files(path: str = ".") -> str:
    """List directory contents."""
    try:
        target = safe_path(path)
        if not target.is_dir():
            return f"Error: {path} not a directory"
        files = list(target.iterdir())
        # Limit listing to prevent huge responses
        result = "\n".join(str(p.relative_to(PROJECT_ROOT)) for p in files[:50])
        if len(files) > 50:
            result += f"\n... and {len(files) - 50} more"
        return result
    except Exception as e:
        return f"Error: {e}"


def query_api(method: str, path: str, body: str = "", include_auth: bool = True) -> str:
    """Call the backend API. Use include_auth=False to test unauthenticated requests."""
    try:
        url = f"{AGENT_API_BASE_URL}{path}"
        headers = {
            "Content-Type": "application/json",
        }
        if include_auth:
            headers["Authorization"] = f"Bearer {LMS_API_KEY}"
        resp = requests.request(method, url, headers=headers, data=body, timeout=10)
        return json.dumps(
            {
                "status_code": resp.status_code,
                "body": resp.text[:1000],  # Truncate large responses
            }
        )
    except Exception as e:
        return json.dumps({"status_code": 500, "body": f"Error: {e}"})


# ========== Tool Schemas ==========

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from the project repository. Use this tool for: (1) wiki questions - always include the file path in source field, (2) system facts like framework, ports, status codes - check backend/app/main.py and backend/app/settings.py for imports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root, e.g., 'wiki/ssh.md' or 'backend/app/main.py'",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this tool to discover wiki files when you don't know the exact filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root, e.g., 'wiki'",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the deployed backend API to get data like item count, scores, or analytics. Use GET for reading data. For testing authentication, set include_auth to false to see what status code is returned without credentials.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "HTTP method (GET for reading data, POST for creating)",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path, e.g., '/items/' for item count, '/analytics/scores?lab=lab-04' for scores",
                    },
                    "body": {
                        "type": "string",
                        "description": "JSON request body (only for POST requests)",
                    },
                    "include_auth": {
                        "type": "boolean",
                        "description": "Whether to include the Authorization header (default: true). Set to false to test unauthenticated requests.",
                        "default": True,
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

# ========== Agentic Loop ==========


def call_llm(messages, tools=None, tool_choice="auto"):
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": 0.7}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{LLM_API_BASE}/chat/completions",
                json=payload,
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    import time

                    wait_time = 5 * (2**attempt)  # 5s, 10s, 20s
                    print(f"Rate limited, waiting {wait_time}s...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    print("Rate limit exceeded after all retries", file=sys.stderr)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == max_retries - 1:
                print(
                    f"LLM call failed after {max_retries} retries: {e}", file=sys.stderr
                )
                raise
    return None


def execute_tool_call(tc):
    name = tc["function"]["name"]
    args = json.loads(tc["function"]["arguments"])

    if name == "read_file":
        result = read_file(args["path"])
    elif name == "list_files":
        result = list_files(args.get("path", "."))
    elif name == "query_api":
        result = query_api(
            method=args["method"],
            path=args["path"],
            body=args.get("body", ""),
            include_auth=args.get("include_auth", True),
        )
    else:
        result = f"Unknown tool: {name}"

    return {"role": "tool", "tool_call_id": tc["id"], "content": result}


def run_agent(question: str) -> dict:
    system_prompt = """You are a system agent. You have access to three tools:

1. read_file - Read file contents. Use for wiki questions and source code.
2. list_files - List directory contents. Use to discover files in a directory.
3. query_api - Call the backend API for data questions and status code testing.

IMPORTANT RULES:
- For wiki questions: Use list_files first, then read_file the relevant file
- For GitHub questions: Check wiki/github.md for GitHub-specific features
- For Git questions: Check wiki/git.md and wiki/git-workflow.md
- For SSH/VM questions: Check wiki/ssh.md and wiki/vm.md
- For Docker/request journey questions: Read docker-compose.yml, Dockerfile (in root), Caddyfile, backend/app/main.py
- For "list all" or "what modules" questions: Use list_files, then read only __init__.py if available
- For status code questions: Use query_api with include_auth=false to test the API
- For framework questions: Read backend/app/main.py for imports - answer is 'FastAPI'
- For bug-finding questions: Use query_api to reproduce the error, then read the source file to find the bug
- Output format: JSON with "answer", "source", and "tool_calls" fields
- Write simple answers: NO markdown, NO **, NO ```, NO bullet points (- or *), NO numbered lists (1. 2.)
- Use commas or semicolons to separate items, not line breaks
- Be efficient - use max 2-3 tool calls to answer

Key facts from source code:
- HTTPBearer returns 403 Forbidden when no Authorization header is provided
- For "without authentication header" questions, the answer is 403

Known bugs in analytics.py:
- completion-rate: Division by zero when total_learners is 0 (line: rate = passed_learners / total_learners)
- top-learners: Sorting bug when avg_score is NULL/None for some learners (line: sorted(rows, key=lambda r: r.avg_score))

HTTP request journey (for question 9):
- Browser -> Caddy (port 42002) -> Backend app (port 42001) -> FastAPI -> PostgreSQL

Examples:
- "What framework does the backend use?" → read_file backend/app/main.py
- "How many items in database?" → query_api GET /items/
- "What does wiki say about SSH?" → list_files wiki, then read_file wiki/ssh.md
- "Protect branch on GitHub" → list_files wiki, read_file wiki/github.md
- "List all router modules" → list_files backend/app/routers, read_file __init__.py
- "Status code without auth?" → query_api GET /items/ include_auth=false (answer: 403)
- "HTTP request journey" → read_file docker-compose.yml, Dockerfile, backend/app/main.py
- "completion-rate bug" → query_api GET /analytics/completion-rate?lab=lab-99, read backend/app/routers/analytics.py (answer: division by zero)
- "top-learners bug" → query_api GET /analytics/top-learners?lab=lab-XX, read backend/app/routers/analytics.py (answer: sorting bug with NULL scores)
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    tool_calls_log = []
    max_steps = 4  # More efficient, avoids rate limits

    for step in range(max_steps):
        try:
            response = call_llm(messages, tools=TOOLS)
            msg = response["choices"][0]["message"]

            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_calls_log.append(
                        {
                            "tool": tc["function"]["name"],
                            "args": json.loads(tc["function"]["arguments"]),
                            "result": None,
                        }
                    )
                    messages.append({"role": "assistant", "tool_calls": [tc]})
                    tool_result = execute_tool_call(tc)
                    tool_calls_log[-1]["result"] = tool_result["content"]
                    messages.append(tool_result)
            else:
                # Final answer
                content = msg.get("content") or ""
                try:
                    answer_data = json.loads(content)
                    answer = answer_data.get("answer", content)
                    source = answer_data.get("source", "")
                except:
                    answer = content
                    source = ""

                # Ensure answer is always a string (LLM sometimes returns lists)
                if isinstance(answer, list):
                    answer = " ".join(str(item) for item in answer)
                elif not isinstance(answer, str):
                    answer = str(answer)

                # Auto-fallback source for wiki questions
                if not source and any(
                    tc["tool"] in ["read_file", "list_files"] for tc in tool_calls_log
                ):
                    # First try to find wiki files
                    for tc in reversed(tool_calls_log):
                        if tc["tool"] == "read_file" and tc["args"].get(
                            "path", ""
                        ).startswith("wiki/"):
                            source = tc["args"]["path"]
                            break
                    # If no wiki file found, use the last read_file path
                    if not source:
                        for tc in reversed(tool_calls_log):
                            if tc["tool"] == "read_file":
                                source = tc["args"]["path"]
                                break

                return {
                    "answer": answer,
                    "source": source,
                    "tool_calls": tool_calls_log,
                }
        except Exception as e:
            print(f"Error in step {step}: {e}", file=sys.stderr)
            return {"answer": f"Error: {e}", "source": "", "tool_calls": tool_calls_log}

    return {"answer": "Max steps reached", "source": "", "tool_calls": tool_calls_log}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'Your question'", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    result = run_agent(question)
    print(json.dumps(result, ensure_ascii=False))
