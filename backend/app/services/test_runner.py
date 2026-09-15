"""
Safe test execution service.
Validates test commands against a strict security allowlist, executes in subprocesses
with timeouts, and captures test runner outputs.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
import shlex
import time
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import resolve_repo_path, settings
from app.core.logging import get_logger
from app.db.models import Repository, TestRun
from app.schemas.schemas import TestRunResponse

logger = get_logger(__name__)

# Strict allowlist of permissible test binaries and subcommands
ALLOWED_TEST_PREFIXES = [
    "pytest",
    "python -m pytest",
    "python3 -m pytest",
    "npm test",
    "npm run test",
    "npx vitest",
    "npx jest",
    "go test",
    "cargo test",
]


def _validate_test_command(command: str) -> list[str]:
    """
    Validate command against injection attacks and ensure it starts with an allowlisted prefix.
    """
    cmd = command.strip()

    # Block shell operators and metacharacters
    disallowed_patterns = [";", "&&", "||", "|", "`", "$(", "$", ">", "<", "\n", "\r", "&"]
    for char in disallowed_patterns:
        if char in cmd:
            raise HTTPException(
                status_code=400,
                detail=f"Disallowed command operator or metacharacter: '{char}'",
            )

    matched = any(cmd == prefix or cmd.startswith(prefix + " ") for prefix in ALLOWED_TEST_PREFIXES)
    if not matched:
        raise HTTPException(
            status_code=400,
            detail=f"Command is not an allowlisted test runner. Allowed prefixes: {ALLOWED_TEST_PREFIXES}",
        )

    return shlex.split(cmd)


def _detect_default_test_command(repo_path: Path) -> str:
    """Auto-detect the default test command for the repository."""
    if (repo_path / "pytest.ini").exists() or (repo_path / "conftest.py").exists() or (repo_path / "tests").exists():
        return "pytest"
    if (repo_path / "package.json").exists():
        return "npm test"
    if (repo_path / "Cargo.toml").exists():
        return "cargo test"
    if (repo_path / "go.mod").exists():
        return "go test ./..."
    return "pytest"


class TestRunnerService:
    """Executes test suites safely within repository workspace."""

    async def run_tests(
        self,
        repo_id: str,
        custom_command: str | None,
        file_path: str | None,
        session: AsyncSession,
    ) -> TestRunResponse:
        res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = res.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_path = resolve_repo_path(repo)
        if not repo_path.is_dir():
            raise HTTPException(status_code=400, detail="Repository directory does not exist")

        command_str = custom_command or _detect_default_test_command(repo_path)
        if file_path:
            command_str = f"{command_str} {file_path}"

        argv = _validate_test_command(command_str)
        run_id = uuid.uuid4().hex

        logger.info(f"Executing test command: {argv} in {repo_path}")
        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0,
            )
            duration = round(time.time() - start_time, 2)
            exit_code = process.returncode

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            status = "passed" if exit_code == 0 else "failed"

        except asyncio.TimeoutError:
            duration = 60.0
            exit_code = -1
            stdout = ""
            stderr = "Test execution timed out after 60 seconds."
            status = "error"
        except FileNotFoundError as e:
            duration = 0.0
            exit_code = -1
            stdout = ""
            stderr = f"Test runner executable not found on system: {e}"
            status = "error"
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            exit_code = -1
            stdout = ""
            stderr = f"Execution error: {e}"
            status = "error"

        # Save record in DB
        test_record = TestRun(
            id=run_id,
            repository_id=repo.id,
            command=command_str,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            status=status,
        )
        session.add(test_record)
        await session.commit()

        return TestRunResponse(
            id=run_id,
            command=command_str,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            status=status,
        )


test_runner_service = TestRunnerService()
