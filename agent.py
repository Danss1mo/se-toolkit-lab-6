#!/usr/bin/env python
"""
Simple CLI agent that calls an LLM and returns JSON.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

if not API_KEY or not API_BASE or not MODEL:
    print("Missing LLM config in .env.agent.secret", file=sys.stderr)
    sys.exit(1)


def ask_llm(question: str) -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7,
    }

    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions", json=payload, headers=headers, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        return {"answer": answer, "tool_calls": []}
    except Exception as e:
        print(f"LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py 'Your question'", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    result = ask_llm(question)
    print(json.dumps(result, ensure_ascii=False))
