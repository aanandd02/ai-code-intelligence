"""
Tool registry and execution infrastructure for the AI Coding Agent.
Provides tool registration, schema definitions, and safe execution within repository boundaries.
"""

from dataclasses import dataclass, field
import inspect
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Tool:
    """Specification and execution handler for an agent tool."""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]


class ToolRegistry:
    """Registry holding all tools available to the AI Coding Agent."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ):
        """Decorator to register an asynchronous tool function."""
        def decorator(func: Callable[..., Awaitable[Any]]):
            self._tools[name] = Tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_tools_prompt_description(self) -> str:
        """Format all registered tools into markdown for inclusion in the agent prompt."""
        descriptions = []
        for t in self._tools.values():
            params_json = json.dumps(t.parameters, indent=2)
            descriptions.append(f"### Tool: `{t.name}`\n{t.description}\nParameters schema:\n```json\n{params_json}\n```")
        return "\n\n".join(descriptions)

    async def execute(self, name: str, repo_id: str, repo_path: Path, **kwargs: Any) -> dict[str, Any]:
        """Execute a tool safely and return structured output."""
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found. Available tools: {list(self._tools.keys())}"}

        try:
            logger.info(f"Executing tool {name} with args {kwargs}")
            # Check signature parameters
            sig = inspect.signature(tool.handler)
            call_kwargs = {}
            if "repo_id" in sig.parameters:
                call_kwargs["repo_id"] = repo_id
            if "repo_path" in sig.parameters:
                call_kwargs["repo_path"] = repo_path

            for k, v in kwargs.items():
                if k in sig.parameters:
                    call_kwargs[k] = v

            res = await tool.handler(**call_kwargs)
            return {"result": res, "success": True}
        except Exception as e:
            logger.warning(f"Error executing tool {name}: {e}")
            return {"error": str(e), "success": False}


tool_registry = ToolRegistry()
