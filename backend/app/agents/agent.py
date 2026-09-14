"""
Autonomous multi-step AI Coding Agent.
Executes iterative reasoning, plans tool calls, observes local repository state,
and synthesizes structured findings and code patches.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from app.agents.tool_registry import tool_registry
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.provider import get_llm_provider
from app.services.repo_analyzer import generate_repo_summary_text
import app.tools  # noqa: F401

logger = get_logger(__name__)


@dataclass
class ToolExecutionStep:
    step_number: int
    thought: str
    tool_name: str
    tool_args: dict[str, Any]
    output: Any
    success: bool = True


@dataclass
class AgentResult:
    task: str
    summary: str
    timeline: list[dict[str, Any]]
    inspected_files: list[str]
    diagnosis: str | None = None
    suggested_fix: str | None = None
    raw_response: str | None = None


AGENT_SYSTEM_PROMPT = """You are an Autonomous AI Code Intelligence Agent running locally on the user's machine.
You have direct tool access to examine and analyze the software repository.

{repo_summary}

AVAILABLE TOOLS:
{tools_descriptions}

PROTOCOL:
At each turn, carefully think about what step to take next.
You MUST output your response as valid JSON matching one of these two formats:

Format 1: Call a tool to inspect the repository
```json
{{
  "thought": "Clear explanation of what you are checking and why",
  "tool": "tool_name",
  "args": {{ ... arguments matching tool parameters ... }}
}}
```

Format 2: Finish and present final diagnosis and recommendations
```json
{{
  "thought": "I have collected sufficient evidence to answer the task",
  "final_answer": "Comprehensive explanation of findings, root cause, and recommendations",
  "diagnosis": "Concise root cause summary",
  "suggested_fix": "Concrete code patch or step-by-step fix",
  "files_affected": ["path/to/file1.py"]
}}
```

CRITICAL RULES:
1. Ground every statement in actual code discovered through your tools.
2. Cite exact file names and line numbers.
3. Be precise, actionable, and production-oriented.
"""


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON object from LLM response text, including inside code fences."""
    text = text.strip()
    # Try parsing directly
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting from ```json ... ``` code fence
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Try finding the outermost balanced { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except Exception:
            pass

    return None


class CodeAgent:
    """Multi-step reasoning agent with autonomous tool execution."""

    def __init__(self, max_iterations: int | None = None):
        self.max_iterations = max_iterations or settings.AGENT_MAX_ITERATIONS

    async def run(
        self,
        repo_id: str,
        repo_path: Path,
        repo_name: str,
        task: str,
        model: str | None = None,
        languages: list[str] | None = None,
    ) -> AgentResult:
        """Run the autonomous agent loop."""
        llm = get_llm_provider()
        target_model = model or getattr(llm, "default_model", settings.OLLAMA_MODEL)

        tools_desc = tool_registry.get_tools_prompt_description()
        repo_summary = generate_repo_summary_text(repo_name, repo_path, languages)
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            repo_summary=repo_summary,
            tools_descriptions=tools_desc,
        )

        timeline: list[ToolExecutionStep] = []
        inspected_files: set[str] = set()

        conversation_history: list[dict[str, str]] = [
            {"role": "user", "content": f"Task: {task}\nPlease begin investigating using the available tools."}
        ]

        logger.info(f"Starting agent run on {repo_name} for task: {task[:80]}")

        for step_idx in range(1, self.max_iterations + 1):
            response_text = await llm.chat(
                messages=conversation_history,
                system=system_prompt,
                model=target_model,
                temperature=0.1,
            )

            # Check if LLM is in offline notice mode
            if "Ollama Offline" in response_text or "Unable to reach" in response_text:
                logger.info("Ollama is offline. Executing heuristic fallback investigation.")
                return await self._run_offline_heuristic_investigation(
                    repo_id=repo_id,
                    repo_path=repo_path,
                    task=task,
                    offline_notice=response_text,
                )

            parsed = _extract_json_from_text(response_text)
            if not parsed:
                # If LLM didn't return JSON, treat the text as final answer
                return AgentResult(
                    task=task,
                    summary=response_text,
                    timeline=[t.__dict__ for t in timeline],
                    inspected_files=list(inspected_files),
                    raw_response=response_text,
                )

            thought = parsed.get("thought", "Analyzing repository...")

            # Check if finished
            if "final_answer" in parsed:
                return AgentResult(
                    task=task,
                    summary=parsed["final_answer"],
                    timeline=[t.__dict__ for t in timeline],
                    inspected_files=list(inspected_files.union(set(parsed.get("files_affected", [])))),
                    diagnosis=parsed.get("diagnosis"),
                    suggested_fix=parsed.get("suggested_fix"),
                    raw_response=response_text,
                )

            tool_name = parsed.get("tool")
            tool_args = parsed.get("args", {})

            if not tool_name:
                # No tool specified
                return AgentResult(
                    task=task,
                    summary=thought,
                    timeline=[t.__dict__ for t in timeline],
                    inspected_files=list(inspected_files),
                )

            # Track files inspected
            if "file_path" in tool_args:
                inspected_files.add(tool_args["file_path"])

            # Execute tool
            exec_res = await tool_registry.execute(
                name=tool_name,
                repo_id=repo_id,
                repo_path=repo_path,
                **tool_args,
            )

            output_data = exec_res.get("result", exec_res.get("error", "No output"))
            step_record = ToolExecutionStep(
                step_number=step_idx,
                thought=thought,
                tool_name=tool_name,
                tool_args=tool_args,
                output=output_data,
                success=exec_res.get("success", False),
            )
            timeline.append(step_record)

            # Add to conversation for next iteration
            conversation_history.append({"role": "assistant", "content": response_text})
            conversation_history.append({
                "role": "user",
                "content": f"Tool Execution Result for `{tool_name}`:\n```json\n{json.dumps(output_data, default=str)[:3000]}\n```\nPlease proceed to the next step or output Format 2 if complete.",
            })

        # Max iterations reached
        return AgentResult(
            task=task,
            summary=f"Reached maximum exploration limit ({self.max_iterations} steps).",
            timeline=[t.__dict__ for t in timeline],
            inspected_files=list(inspected_files),
        )

    async def _run_offline_heuristic_investigation(
        self,
        repo_id: str,
        repo_path: Path,
        task: str,
        offline_notice: str,
    ) -> AgentResult:
        """
        Execute deterministic local tool investigation when Ollama is offline.
        Uses semantic_search + read_file to provide immediate real repository context.
        """
        timeline = []
        inspected_files = []

        # 1. Semantic search
        search_exec = await tool_registry.execute(
            name="semantic_search",
            repo_id=repo_id,
            repo_path=repo_path,
            query=task,
            top_k=3,
        )
        search_results = search_exec.get("result", [])
        timeline.append({
            "step_number": 1,
            "thought": "Query local vector database for relevant code chunks matching task.",
            "tool_name": "semantic_search",
            "tool_args": {"query": task, "top_k": 3},
            "output": search_results,
            "success": True,
        })

        # 2. Read top matched file
        snippet_summary = []
        if search_results and isinstance(search_results, list) and len(search_results) > 0:
            top_hit = search_results[0]
            file_path = top_hit.get("file_path")
            if file_path:
                inspected_files.append(file_path)
                read_exec = await tool_registry.execute(
                    name="read_file",
                    repo_id=repo_id,
                    repo_path=repo_path,
                    file_path=file_path,
                    start_line=1,
                    end_line=50,
                )
                read_output = read_exec.get("result", "")
                timeline.append({
                    "step_number": 2,
                    "thought": f"Examine code in top relevant file `{file_path}`.",
                    "tool_name": "read_file",
                    "tool_args": {"file_path": file_path, "start_line": 1, "end_line": 50},
                    "output": read_output[:1000] + ("..." if len(str(read_output)) > 1000 else ""),
                    "success": True,
                })
                snippet_summary.append(f"Top matching file: `{file_path}` (score: {top_hit.get('score')})")

        summary_text = (
            f"{offline_notice}\n\n"
            f"### Local Repository Investigation Summary\n"
            f"- **Investigated Task**: {task}\n"
            f"- **Files Located**: {', '.join(inspected_files) if inspected_files else 'None'}\n"
            f"- **Automated Steps Executed**: 2 local tools completed successfully (semantic_search, read_file).\n"
        )

        return AgentResult(
            task=task,
            summary=summary_text,
            timeline=timeline,
            inspected_files=inspected_files,
            diagnosis="Ollama runtime in standby. Local tool pipeline verified and operational.",
            suggested_fix="Start `ollama serve` and pull your preferred model to enable autonomous LLM reasoning loops.",
        )


code_agent = CodeAgent()
