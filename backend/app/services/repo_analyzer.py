"""
Repository structural and architectural analyzer.
Detects project type, frameworks, key configuration files, and directory organization
to construct a high-signal repository map for the LLM.
"""

import json
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

FRAMEWORK_SIGNATURES: dict[str, list[str]] = {
    "FastAPI": ["fastapi", "from fastapi import", "import fastapi"],
    "Flask": ["flask", "from flask import", "import flask"],
    "Django": ["django", "django.urls", "manage.py"],
    "React": ["react", "react-dom", "react/jsx-runtime"],
    "Vite": ["vite", "vite.config.ts", "vite.config.js"],
    "Next.js": ["next", "next.config.js", "next.config.mjs"],
    "Vue": ["vue", "createApp", "@vitejs/plugin-vue"],
    "Tailwind CSS": ["tailwindcss", "@tailwindcss"],
    "Express": ["express", "require('express')", "from 'express'"],
    "PyTest": ["pytest", "pytest.ini"],
    "Jest / Vitest": ["vitest", "jest"],
    "Docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "SQLAlchemy": ["sqlalchemy", "create_async_engine", "DeclarativeBase"],
    "Qdrant": ["qdrant-client", "qdrant"],
}


def analyze_repository_structure(repo_path: Path) -> dict[str, Any]:
    """
    Inspect repo root and configuration files to build a structural profile.
    """
    repo_path = repo_path.resolve()
    detected_frameworks: set[str] = set()
    config_files: list[str] = []
    entry_points: list[str] = []

    # 1. Inspect top-level files
    try:
        top_files = [f.name for f in repo_path.iterdir() if f.is_file()]
        top_dirs = [d.name for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    except Exception as e:
        logger.warning(f"Error inspecting repo path {repo_path}: {e}")
        return {"frameworks": [], "config_files": [], "structure": {}}

    # 2. Check for common configuration files
    common_configs = [
        "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile",
        "Dockerfile", "docker-compose.yml", ".env.example", "setup.py",
    ]
    for cfg in common_configs:
        if (repo_path / cfg).exists():
            config_files.append(cfg)

    # 3. Check for frameworks in config files
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for dep in deps:
                for fw, sigs in FRAMEWORK_SIGNATURES.items():
                    if dep.lower() in [s.lower() for s in sigs]:
                        detected_frameworks.add(fw)
        except Exception:
            pass

    req_txt = repo_path / "requirements.txt"
    if req_txt.exists():
        try:
            text = req_txt.read_text(errors="ignore").lower()
            for fw, sigs in FRAMEWORK_SIGNATURES.items():
                if any(s.lower() in text for s in sigs):
                    detected_frameworks.add(fw)
        except Exception:
            pass

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(errors="ignore").lower()
            for fw, sigs in FRAMEWORK_SIGNATURES.items():
                if any(s.lower() in text for s in sigs):
                    detected_frameworks.add(fw)
        except Exception:
            pass

    # 4. Check for key entry points
    candidate_entries = [
        "main.py", "app/main.py", "src/main.py", "index.ts", "src/index.ts",
        "src/main.tsx", "src/App.tsx", "index.js", "src/index.js",
    ]
    for ce in candidate_entries:
        if (repo_path / ce).exists():
            entry_points.append(ce)

    return {
        "top_directories": sorted(top_dirs),
        "config_files": sorted(config_files),
        "entry_points": sorted(entry_points),
        "frameworks": sorted(list(detected_frameworks)),
    }


def generate_repo_summary_text(repo_name: str, repo_path: Path, languages: list[str] | None = None) -> str:
    """
    Format repository structure into a clean markdown block for LLM prompts.
    """
    analysis = analyze_repository_structure(repo_path)
    lang_str = ", ".join(languages) if languages else "Not yet detected"
    fw_str = ", ".join(analysis["frameworks"]) if analysis["frameworks"] else "Standard library / custom"
    dirs_str = ", ".join(analysis["top_directories"]) if analysis["top_directories"] else "Root only"
    configs_str = ", ".join(analysis["config_files"]) if analysis["config_files"] else "None found"
    entries_str = ", ".join(analysis["entry_points"]) if analysis["entry_points"] else "Not specified"

    return f"""### Repository Overview: {repo_name}
- **Primary Languages**: {lang_str}
- **Detected Frameworks & Tools**: {fw_str}
- **Key Directories**: {dirs_str}
- **Configuration Files**: {configs_str}
- **Probable Entry Points**: {entries_str}
"""
