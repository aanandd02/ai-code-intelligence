"""
Code search tools: semantic vector search, grep search, and symbol lookup.
"""

from pathlib import Path
import re
from typing import Any

from sqlalchemy import select

from app.agents.tool_registry import tool_registry
from app.db.database import async_session_factory
from app.db.models import Chunk
from app.indexing.file_discovery import discover_files
from app.retrieval.search import semantic_search


@tool_registry.register(
    name="semantic_search",
    description="Find relevant code snippets using semantic natural language vector search.",
    parameters={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing the desired logic or feature",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
            },
            "language": {
                "type": "string",
                "description": "Optional programming language filter (e.g. 'python')",
            },
        },
    },
)
async def semantic_search_tool(
    repo_id: str,
    query: str,
    top_k: int = 5,
    language: str | None = None,
) -> list[dict[str, Any]]:
    res = await semantic_search(
        repo_id=repo_id,
        query=query,
        top_k=top_k,
        language=language,
    )
    return [
        {
            "file_path": r.file_path,
            "symbol": f"{r.symbol_type}:{r.symbol_name}" if r.symbol_name else None,
            "lines": f"{r.start_line}-{r.end_line}",
            "snippet": r.content[:300],
            "score": r.score,
        }
        for r in res.results
    ]


@tool_registry.register(
    name="grep_search",
    description="Perform exact string or regex search across all source files in the repository.",
    parameters={
        "type": "object",
        "required": ["pattern"],
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text substring or regex pattern to find",
            },
            "is_regex": {
                "type": "boolean",
                "description": "Whether pattern is a regular expression (default false)",
            },
            "max_matches": {
                "type": "integer",
                "description": "Max number of line matches to return (default 25)",
            },
        },
    },
)
async def grep_search_tool(
    repo_path: Path,
    pattern: str,
    is_regex: bool = False,
    max_matches: int = 25,
) -> list[dict[str, Any]]:
    results = []
    flags = 0
    try:
        compiled = re.compile(pattern if is_regex else re.escape(pattern), flags)
    except Exception as e:
        return [{"error": f"Invalid regex pattern: {e}"}]

    for f in discover_files(repo_path, max_files=500):
        abs_p = Path(f["abs_path"])
        try:
            content = abs_p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            if compiled.search(line):
                results.append({
                    "file_path": f["path"],
                    "line": line_num,
                    "content": line.strip()[:180],
                })
                if len(results) >= max_matches:
                    return results

    return results


@tool_registry.register(
    name="find_symbol",
    description="Locate definitions of a specific function, class, method, or variable in the repository.",
    parameters={
        "type": "object",
        "required": ["symbol_name"],
        "properties": {
            "symbol_name": {
                "type": "string",
                "description": "Name of the symbol (e.g. 'calculateTotal', 'UserRepository')",
            },
        },
    },
)
async def find_symbol_tool(
    repo_id: str,
    symbol_name: str,
) -> list[dict[str, Any]]:
    async with async_session_factory() as session:
        query = select(Chunk).where(
            Chunk.repository_id == repo_id,
            Chunk.symbol_name.ilike(f"%{symbol_name}%"),
        ).limit(10)
        res = await session.execute(query)
        chunks = res.scalars().all()

        return [
            {
                "symbol_name": c.symbol_name,
                "symbol_type": c.symbol_type,
                "file_path": c.file.path if c.file else "unknown",
                "start_line": c.start_line,
                "end_line": c.end_line,
                "preview": c.content[:200],
            }
            for c in chunks
        ]
