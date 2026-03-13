# Agent CLI

## How it works
- Reads `.env.agent.secret` for `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
- Sends question to LLM API
- Returns JSON with `answer` and `tool_calls`

## Run
```bash
uv run agent.py "What is REST?"
