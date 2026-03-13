# Task 2 — The Documentation Agent

## Tool Schemas
- `read_file(path)` — reads file from project root
- `list_files(path)` — lists directory contents

## Agentic Loop
1. Send question + tool definitions to LLM
2. If LLM returns `tool_calls` → execute, append results as `tool` role, repeat (max 10)
3. If LLM returns text → final answer

## Security
- Prevent path traversal (`../`)
- Resolve paths relative to project root

## Output
- `answer`: final text
- `source`: wiki section reference
- `tool_calls`: array of all calls made
