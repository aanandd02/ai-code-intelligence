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
    Supports multi-module / monorepos (e.g. backend/ and frontend/).
    """
    repo_path = repo_path.resolve()
    detected_frameworks: set[str] = set()
    config_files: list[str] = []
    entry_points: list[str] = []
    source_files: list[str] = []

    # 1. Inspect top-level directories
    try:
        top_dirs = [d.name for d in repo_path.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name not in {"node_modules", "venv", "__pycache__", "dist", "build"}]
    except Exception as e:
        logger.warning(f"Error inspecting repo path {repo_path}: {e}")
        return {"frameworks": [], "config_files": [], "top_directories": [], "entry_points": [], "source_files": [], "structure": {}}

    # 2. Check for common configuration files across root and key subdirectories
    common_configs = [
        "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Makefile",
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "setup.py", "vite.config.ts",
    ]

    search_dirs = [repo_path] + [repo_path / d for d in top_dirs]
    for d in search_dirs:
        for cfg in common_configs:
            cfg_path = d / cfg
            if cfg_path.exists():
                rel_cfg = str(cfg_path.relative_to(repo_path))
                if rel_cfg not in config_files:
                    config_files.append(rel_cfg)

                # Parse package.json for frameworks
                if cfg == "package.json":
                    try:
                        data = json.loads(cfg_path.read_text(errors="ignore"))
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                        for dep in deps:
                            for fw, sigs in FRAMEWORK_SIGNATURES.items():
                                if dep.lower() in [s.lower() for s in sigs]:
                                    detected_frameworks.add(fw)
                    except Exception:
                        pass

                # Parse requirements.txt for frameworks
                if cfg == "requirements.txt":
                    try:
                        text = cfg_path.read_text(errors="ignore").lower()
                        for fw, sigs in FRAMEWORK_SIGNATURES.items():
                            if any(s.lower() in text for s in sigs):
                                detected_frameworks.add(fw)
                    except Exception:
                        pass

                # Parse pyproject.toml for frameworks
                if cfg == "pyproject.toml":
                    try:
                        text = cfg_path.read_text(errors="ignore").lower()
                        for fw, sigs in FRAMEWORK_SIGNATURES.items():
                            if any(s.lower() in text for s in sigs):
                                detected_frameworks.add(fw)
                    except Exception:
                        pass

    # 3. Check for key entry points across repo
    candidate_entries = [
        "main.py", "app/main.py", "backend/app/main.py", "src/main.py",
        "src/main.tsx", "src/App.tsx", "frontend/src/main.tsx", "frontend/src/App.tsx",
        "index.ts", "src/index.ts", "index.js", "src/index.js",
        "backend/app/api/repositories.py", "backend/app/services/chat.py",
    ]
    for ce in candidate_entries:
        if (repo_path / ce).exists() and ce not in entry_points:
            entry_points.append(ce)

    # 4. Collect file manifest using discover_files
    try:
        from app.indexing.file_discovery import discover_files
        discovered = list(discover_files(repo_path))
        # Keep high-value source files (.py, .ts, .tsx, .js, .jsx, .sql, .html, .css, .json, .yaml, .yml)
        valuable_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".html", ".css", ".yaml", ".yml"}
        for f in discovered:
            p = f["path"]
            if Path(p).suffix.lower() in valuable_exts:
                source_files.append(p)
    except Exception as e:
        logger.warning(f"Error generating file manifest: {e}")

    return {
        "top_directories": sorted(top_dirs),
        "config_files": sorted(config_files),
        "entry_points": sorted(entry_points),
        "frameworks": sorted(list(detected_frameworks)),
        "source_files": sorted(source_files),
    }


def generate_repo_summary_text(repo_name: str, repo_path: Path, languages: list[str] | None = None) -> str:
    """
    Format repository structure into a clean, comprehensive markdown block for LLM prompts.
    """
    analysis = analyze_repository_structure(repo_path)
    lang_str = ", ".join(languages) if languages else "Not yet detected"
    fw_str = ", ".join(analysis["frameworks"]) if analysis["frameworks"] else "Standard library / custom"
    dirs_str = ", ".join(analysis["top_directories"]) if analysis["top_directories"] else "Root only"
    configs_str = ", ".join(analysis["config_files"]) if analysis["config_files"] else "None found"
    entries_str = ", ".join(analysis["entry_points"]) if analysis["entry_points"] else "Not specified"

    files = analysis.get("source_files", [])
    if files:
        # Format top files as a clean tree/list
        display_files = files[:60]
        files_text = "\n".join(f"  - `{f}`" for f in display_files)
        if len(files) > 60:
            files_text += f"\n  - *(and {len(files) - 60} more files)*"
    else:
        files_text = "  *(No source files indexed yet)*"

    return f"""### Repository Overview & File Manifest: {repo_name}
- **Primary Languages**: {lang_str}
- **Detected Frameworks & Tools**: {fw_str}
- **Key Directories**: {dirs_str}
- **Key Modules & Entry Points**: {entries_str}
- **Configuration Files**: {configs_str}
- **Repository Source Files ({len(files)} total files)**:
{files_text}
"""
