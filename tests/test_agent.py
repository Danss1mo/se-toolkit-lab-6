import subprocess
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

def test_agent_returns_json():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert "answer" in output
    assert "tool_calls" in output

def test_agent_uses_read_file_for_wiki():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What does the wiki say about SSH?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert any(tc["tool"] == "read_file" for tc in output["tool_calls"])
    assert "source" in output
    assert "wiki" in output.get("source", "")

def test_agent_uses_list_files_for_wiki():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert any(tc["tool"] == "list_files" for tc in output["tool_calls"])

def test_agent_uses_read_file_for_framework():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What framework does the backend use?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert any(tc["tool"] == "read_file" for tc in output["tool_calls"])

def test_agent_uses_query_api_for_item_count():
    result = subprocess.run(
        ["uv", "run", "agent.py", "How many items are in the database?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert any(tc["tool"] == "query_api" for tc in output["tool_calls"])
    assert "answer" in output