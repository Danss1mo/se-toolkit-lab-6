# Task 1 — Call an LLM from Code

## LLM Provider
- **Provider**: OpenRouter
- **Model**: `qwen/qwen-2.5-coder-32b-instruct`
- **API base**: `https://openrouter.ai/api/v1`

## Agent Structure
- Reads config from `.env.agent.secret`
- Takes question as CLI argument
- Sends request to LLM API
- Outputs JSON with `answer` and `tool_calls: []`

## Why OpenRouter?
- Stable, fast, 1000 free requests/day
- No GPU needed
