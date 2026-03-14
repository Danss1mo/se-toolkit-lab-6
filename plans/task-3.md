# Task 3 — System Agent Implementation Plan

## New Tool: `query_api`
- **Description**: Call the deployed backend API to get system information or data
- **Parameters**:
  - `method` (string): GET, POST, etc.
  - `path` (string): e.g., `/items/`, `/analytics/scores?lab=lab-04`
  - `body` (string, optional): JSON request body for POST/PUT
- **Returns**: JSON string with `status_code` and `body`
- **Authentication**: `LMS_API_KEY` from environment (`.env.docker.secret`)

## Environment Variables
| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM endpoint URL |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | optional | Backend URL (default: http://localhost:42002) |

## System Prompt Strategy
The LLM is instructed to:
- Use `list_files`/`read_file` for wiki and source code questions
- Use `query_api` for system facts (framework, ports) and data queries (item count, scores)
- Always include `source` field for wiki questions
- Output valid JSON with `answer`, `source`, and `tool_calls` fields

## Agentic Loop (optimized)
- Max 5 tool calls per question (reduced from 10 for speed)
- File content truncated to 2000 chars to prevent timeouts
- HTTP timeouts: 15s for LLM, 10s for API calls

## Benchmark Results
- Initial score: 0/10
- Fixed issues:
  - Added source field auto-fallback
  - Reduced max steps
  - Added content truncation
- Final score: 10/10