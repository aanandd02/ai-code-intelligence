"""
Unit tests for security controls: path traversal protection and command safety.
"""

from pathlib import Path
import pytest
from fastapi import HTTPException

from app.core.security import validate_path_containment
from app.services.test_runner import _validate_test_command


def test_path_containment_valid():
    base = Path("/Users/aanandd/coding/AI-Projects").resolve()
    target = "ai-code-intelligence/backend/app/main.py"
    resolved = validate_path_containment(base, target)
    assert resolved.exists() or str(resolved).startswith(str(base))


def test_path_containment_blocks_traversal():
    base = Path("/Users/aanandd/coding/AI-Projects/ai-code-intelligence").resolve()
    traversal_path = "../../etc/passwd"

    with pytest.raises(HTTPException) as exc_info:
        validate_path_containment(base, traversal_path)

    assert exc_info.value.status_code == 403


def test_validate_test_command_allowlisted():
    assert _validate_test_command("pytest") == ["pytest"]
    assert _validate_test_command("pytest tests/ -v") == ["pytest", "tests/", "-v"]
    assert _validate_test_command("npm test") == ["npm", "test"]
    assert _validate_test_command("go test ./...") == ["go", "test", "./..."]


def test_validate_test_command_blocks_arbitrary_commands():
    with pytest.raises(HTTPException):
        _validate_test_command("cat /etc/passwd")

    with pytest.raises(HTTPException):
        _validate_test_command("rm -rf /")

    with pytest.raises(HTTPException):
        _validate_test_command("pytest; rm -rf .")

    with pytest.raises(HTTPException):
        _validate_test_command("pytest && curl evil.com")
