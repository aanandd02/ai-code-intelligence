"""
Context builder for repository-aware LLM conversations.
Assembles system directives, repository architecture metadata,
retrieved semantic code snippets, and conversational history within token budgets.
"""

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.schemas import Citation, SearchResult
from app.services.repo_analyzer import generate_repo_summary_text

logger = get_logger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are AI Code Intelligence Agent, an expert repository-aware software engineer and coding assistant.
You are running integrated directly inside the user's project with full semantic visibility into their codebase.

Your key directives:
1. ALWAYS ground your answers in the provided codebase context, architecture manifest, and code snippets.
2. ALWAYS cite the relevant file path and line numbers when referencing code (e.g., `backend/app/main.py:10-25`).
3. You ALREADY have the repository architecture, file manifest, and code context. NEVER ask the user to share the file tree, run `git ls-files`, or paste code files — you are already running inside their codebase!
4. If the user asks a broad question (e.g., "Find potential bugs in the code", "Explain the architecture", "Where is auth handled?"):
   - Directly analyze the files, entry points, and code snippets provided in your context.
   - Walk through the relevant modules, identify concrete strengths, potential bugs, edge cases, or architecture trade-offs.
   - Provide concrete, production-quality fixes or code examples.
5. Format your output using clean, beautifully structured GitHub Flavored Markdown with headings, bullet points, and syntax-highlighted code blocks.

{repo_summary}
"""


class ContextBuilder:
    """Constructs prompt contexts with semantic grounding and citation extraction."""

    def __init__(self, max_tokens: int | None = None):
        self.max_tokens = max_tokens or settings.MAX_CONTEXT_TOKENS

    def build_system_prompt(
        self,
        repo_name: str,
        repo_path: Path,
        languages: list[str] | None = None,
    ) -> str:
        """Build the grounded system prompt with repo metadata."""
        from app.core.config import resolve_host_path
        resolved = resolve_host_path(str(repo_path)) or repo_path
        summary = generate_repo_summary_text(repo_name, resolved, languages)
        return SYSTEM_PROMPT_TEMPLATE.format(repo_summary=summary)

    def format_code_snippets(
        self,
        snippets: list[SearchResult],
        char_budget: int = 12000,
    ) -> tuple[str, list[Citation]]:
        """
        Format retrieved code snippets into a markdown block and extract structured citations.
        """
        if not snippets:
            return "No specific isolated code snippets matched. Use the repository overview and file manifest to answer.", []

        formatted_parts = ["### Relevant Code Snippets:"]
        citations: list[Citation] = []
        current_chars = 0

        for s in snippets:
            symbol_info = f" ({s.symbol_type}: {s.symbol_name})" if s.symbol_name else ""
            header = f"\n#### File: `{s.file_path}` (lines {s.start_line}-{s.end_line}){symbol_info}"
            lang = s.language or "text"
            block = f"{header}\n```{lang}\n{s.content}\n```\n"

            if current_chars + len(block) > char_budget:
                formatted_parts.append("\n*(Additional snippets omitted to respect context limits)*")
                break

            formatted_parts.append(block)
            current_chars += len(block)

            citations.append(
                Citation(
                    file_path=s.file_path,
                    start_line=s.start_line,
                    end_line=s.end_line,
                    symbol_name=s.symbol_name,
                    content=s.content[:300] + "..." if len(s.content) > 300 else s.content,
                )
            )

        return "\n".join(formatted_parts), citations

    def assemble_user_prompt(
        self,
        user_message: str,
        snippets_text: str,
    ) -> str:
        """Combine retrieved code context with user query."""
        return f"""{snippets_text}

---
### User Question:
{user_message}

Please provide an accurate, grounded, and helpful response based on the code above."""
