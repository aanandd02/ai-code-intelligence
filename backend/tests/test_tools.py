"""
Unit tests for agent tools.
"""

from pathlib import Path
import pytest

from app.agents.tool_registry import tool_registry
import app.tools  # noqa: F401


@pytest.mark.asyncio
async def test_tool_registry_lists_all_tools():
    tool_names = [t.name for t in tool_registry.list_tools()]
    expected = [
        "list_files", "read_file", "semantic_search",
        "grep_search", "find_symbol", "git_status", "git_diff", "git_log",
    ]
    for exp in expected:
        assert exp in tool_names, f"Missing tool: {exp}"


@pytest.mark.asyncio
async def test_list_files_tool():
    repo_path = Path("/Users/aanandd/coding/AI-Projects/ai-code-intelligence").resolve()
    res = await tool_registry.execute(
        name="list_files",
        repo_id="test_id",
        repo_path=repo_path,
        directory="backend/app",
        extension=".py",
    )
    assert res["success"] is True
    files = res["result"]
    assert len(files) > 0
    assert any("main.py" in f for f in files)


@pytest.mark.asyncio
async def test_read_file_tool():
    repo_path = Path("/Users/aanandd/coding/AI-Projects/ai-code-intelligence").resolve()
    res = await tool_registry.execute(
        name="read_file",
        repo_id="test_id",
        repo_path=repo_path,
        file_path="backend/app/main.py",
        start_line=1,
        end_line=20,
    )
    assert res["success"] is True
    assert "FastAPI" in res["result"]


@pytest.mark.asyncio
async def test_grep_search_tool():
    repo_path = Path("/Users/aanandd/coding/AI-Projects/ai-code-intelligence").resolve()
    res = await tool_registry.execute(
        name="grep_search",
        repo_id="test_id",
        repo_path=repo_path,
        pattern="app.main:app",
    )
    assert res["success"] is True
    matches = res["result"]
    assert isinstance(matches, list)
