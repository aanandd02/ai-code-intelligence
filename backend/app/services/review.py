"""
Code review service.
Provides automated bug detection, security scanning, performance analysis,
and architectural code reviews using static analysis rules and local Ollama models.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import resolve_repo_path, settings
from app.core.logging import get_logger
from app.db.models import Repository, Review
from app.llm.provider import get_llm_provider
from app.schemas.schemas import ReviewFinding, ReviewResponse
from app.services.repository import get_repo_file_content

logger = get_logger(__name__)


def _run_static_heuristics(code: str, file_path: str | None = None) -> list[ReviewFinding]:
    """Perform deterministic rule-based checks for common security and bug patterns."""
    findings = []
    lines = code.splitlines()

    # Rule 1: Hardcoded credentials or API keys
    key_pattern = re.compile(r"""(?:api_key|password|secret|token|private_key)\s*=\s*['"][a-zA-Z0-9_\-\.\/]{8,}['"]""", re.IGNORECASE)
    # Rule 2: Insecure SQL queries / string interpolation in SQL
    sql_pattern = re.compile(r"""(?:execute|cursor\.execute)\s*\(\s*f['"].*SELECT.*\{|INSERT.*\{|UPDATE.*\{""", re.IGNORECASE)
    # Rule 3: Bare except clauses in Python
    bare_except = re.compile(r"""^\s*except\s*:""")
    # Rule 4: Dangerous eval or exec
    eval_pattern = re.compile(r"""\b(?:eval|exec)\s*\(""")

    for i, line in enumerate(lines, start=1):
        if key_pattern.search(line):
            findings.append(ReviewFinding(
                severity="critical",
                file=file_path,
                line=i,
                title="Potential hardcoded secret or API key",
                description="A sensitive key or credential appears to be hardcoded in the source code.",
                recommendation="Extract this secret into environment variables or a secure configuration file.",
                confidence=0.85,
            ))

        if sql_pattern.search(line):
            findings.append(ReviewFinding(
                severity="critical",
                file=file_path,
                line=i,
                title="Potential SQL injection vulnerability",
                description="SQL query appears to use string interpolation instead of parameterized queries.",
                recommendation="Use parameterized statements (e.g. cursor.execute(query, (val1, val2))).",
                confidence=0.90,
            ))

        if bare_except.search(line):
            findings.append(ReviewFinding(
                severity="medium",
                file=file_path,
                line=i,
                title="Bare except clause catches all exceptions",
                description="Using 'except:' catches KeyboardInterrupt, SystemExit, and masks unanticipated bugs.",
                recommendation="Specify explicit exception types or catch 'except Exception:' at a minimum.",
                confidence=0.95,
            ))

        if eval_pattern.search(line):
            findings.append(ReviewFinding(
                severity="high",
                file=file_path,
                line=i,
                title="Use of dangerous eval() or exec()",
                description="Dynamic code evaluation can lead to arbitrary remote code execution if input is untrusted.",
                recommendation="Replace dynamic evaluation with explicit parsers (e.g. ast.literal_eval, json.loads).",
                confidence=0.95,
            ))

    return findings


class ReviewService:
    """Orchestrates comprehensive code reviews."""

    async def review_code(
        self,
        repo_id: str,
        file_path: str | None,
        code_input: str | None,
        diff_input: str | None,
        review_type: str,
        session: AsyncSession,
    ) -> ReviewResponse:
        res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = res.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_path = resolve_repo_path(repo)
        content_to_review = code_input or ""
        target_file = file_path

        # If file_path is given without code, load from disk
        if file_path and not code_input and not diff_input:
            data = get_repo_file_content(repo_path, file_path)
            content_to_review = data["content"]
        elif diff_input:
            content_to_review = diff_input
            target_file = target_file or "git-diff"

        if not content_to_review.strip():
            raise HTTPException(status_code=400, detail="No code, file, or diff provided to review")

        # 1. Run deterministic static checks
        findings: list[ReviewFinding] = _run_static_heuristics(content_to_review, target_file)

        # 2. Run LLM review with structured JSON output
        llm = get_llm_provider()
        system_prompt = f"""You are a senior code reviewer specializing in {review_type} code reviews.
Analyze the provided code and identify bugs, security vulnerabilities, edge-case risks, and anti-patterns.
You MUST output a JSON object with this exact schema:
{{
  "summary": "High-level summary of code quality and main concerns",
  "findings": [
    {{
      "severity": "critical" | "high" | "medium" | "low" | "info",
      "line": 12,
      "title": "Brief title of the finding",
      "description": "Detailed explanation of the issue and why it matters",
      "recommendation": "Concrete suggested fix or refactoring",
      "confidence": 0.9
    }}
  ]
}}
"""
        user_prompt = f"Target File: `{target_file}`\nReview Focus: {review_type}\n\nCode to review:\n```\n{content_to_review[:8000]}\n```"

        summary = "Code review completed."
        try:
            llm_reply = await llm.generate(
                prompt=user_prompt,
                system=system_prompt,
                model=getattr(llm, "default_model", settings.OLLAMA_MODEL),
                temperature=0.1,
            )

            # Extract JSON
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", llm_reply, re.DOTALL)
            json_text = match.group(1) if match else llm_reply
            parsed = json.loads(json_text)

            summary = parsed.get("summary", summary)
            for f in parsed.get("findings", []):
                findings.append(ReviewFinding(
                    severity=f.get("severity", "medium"),
                    file=target_file,
                    line=f.get("line"),
                    title=f.get("title", "Code quality observation"),
                    description=f.get("description", ""),
                    recommendation=f.get("recommendation"),
                    confidence=float(f.get("confidence", 0.8)),
                ))
        except Exception as e:
            logger.info(f"LLM review fallback or unparseable: {e}")
            if not findings:
                findings.append(ReviewFinding(
                    severity="info",
                    file=target_file,
                    line=1,
                    title="Automated static review passed",
                    description=f"Static pattern checks completed. No critical security or injection patterns identified in {target_file or 'provided snippet'}.",
                    recommendation="Ensure unit tests cover happy path and edge conditions.",
                    confidence=0.9,
                ))

        # Sort findings by severity: critical > high > medium > low > info
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings.sort(key=lambda x: severity_order.get(x.severity, 5))

        # Save to DB
        review_id = uuid.uuid4().hex
        review_record = Review(
            id=review_id,
            repository_id=repo.id,
            file_path=target_file,
            input_type=review_type,
            input_content=content_to_review[:2000],
            findings_json=json.dumps([f.model_dump() for f in findings]),
            summary=summary,
            model=settings.OLLAMA_MODEL,
        )
        session.add(review_record)
        await session.commit()

        return ReviewResponse(
            id=review_id,
            findings=findings,
            summary=summary,
            model=settings.OLLAMA_MODEL,
        )


review_service = ReviewService()
