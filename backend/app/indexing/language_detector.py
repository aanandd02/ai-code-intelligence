"""
Language detection based on file extension.
Maps file extensions to programming language identifiers.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)

# Extension → language mapping
EXTENSION_MAP: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    # JavaScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    # TypeScript
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    # Java
    ".java": "java",
    # C
    ".c": "c",
    ".h": "c",
    # C++
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".hh": "cpp",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # JSON
    ".json": "json",
    ".jsonc": "json",
    # YAML
    ".yml": "yaml",
    ".yaml": "yaml",
    # Markdown
    ".md": "markdown",
    ".mdx": "markdown",
    ".markdown": "markdown",
    # HTML
    ".html": "html",
    ".htm": "html",
    # CSS
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    # Shell
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    # SQL
    ".sql": "sql",
    # Dockerfile
    "Dockerfile": "dockerfile",
    # TOML
    ".toml": "toml",
    # INI / Config
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    # XML
    ".xml": "xml",
    ".xsl": "xml",
    ".xslt": "xml",
    # Ruby
    ".rb": "ruby",
    # PHP
    ".php": "php",
    # Swift
    ".swift": "swift",
    # Kotlin
    ".kt": "kotlin",
    ".kts": "kotlin",
    # Scala
    ".scala": "scala",
    # R
    ".r": "r",
    ".R": "r",
    # Makefile
    "Makefile": "makefile",
    # Proto
    ".proto": "protobuf",
}

# Filename → language mapping (for files without extensions)
FILENAME_MAP: dict[str, str] = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "Rakefile": "ruby",
    "Gemfile": "ruby",
    "Pipfile": "toml",
    ".gitignore": "gitignore",
    ".dockerignore": "dockerignore",
    ".env": "dotenv",
    ".env.example": "dotenv",
    "requirements.txt": "pip-requirements",
    "setup.py": "python",
    "setup.cfg": "ini",
    "pyproject.toml": "toml",
    "package.json": "json",
    "tsconfig.json": "json",
    "Cargo.toml": "toml",
    "go.mod": "gomod",
    "go.sum": "gosum",
}

# Languages that Tree-sitter can parse (for AST-aware chunking)
TREE_SITTER_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "c",
    "cpp",
    "go",
    "rust",
    "html",
    "css",
    "json",
    "yaml",
    "markdown",
    "bash",
    "ruby",
}


def detect_language(file_path: str) -> str | None:
    """Detect the programming language from a file path."""
    from pathlib import Path

    p = Path(file_path)
    filename = p.name
    extension = p.suffix.lower()

    # Try filename match first
    if filename in FILENAME_MAP:
        return FILENAME_MAP[filename]

    # Then extension match
    if extension in EXTENSION_MAP:
        return EXTENSION_MAP[extension]

    return None


def has_tree_sitter_support(language: str | None) -> bool:
    """Check if a language has Tree-sitter grammar support."""
    return language in TREE_SITTER_LANGUAGES


def get_language_stats(files: list[dict]) -> dict[str, int]:
    """Count files per language."""
    stats: dict[str, int] = {}
    for f in files:
        lang = detect_language(f["path"])
        if lang:
            stats[lang] = stats.get(lang, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: -x[1]))
