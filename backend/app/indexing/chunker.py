"""
AST-aware code chunker using Tree-sitter.

Parses source code into semantic chunks (functions, classes, methods, etc.)
rather than blindly splitting by character count.

Falls back to line-based chunking for unsupported languages.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.indexing.language_detector import has_tree_sitter_support

logger = get_logger(__name__)

# Try to import tree_sitter — graceful degradation if unavailable
_tree_sitter_available = False
try:
    import tree_sitter
    _tree_sitter_available = True
except ImportError:
    logger.warning("tree-sitter not installed — falling back to line-based chunking")

# Tree-sitter language packages (installed as pip packages)
_LANGUAGE_PACKAGES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "html": "tree_sitter_html",
    "css": "tree_sitter_css",
    "json": "tree_sitter_json",
    "yaml": "tree_sitter_yaml",
    "markdown": "tree_sitter_markdown",
    "bash": "tree_sitter_bash",
    "ruby": "tree_sitter_ruby",
}

# Node types that represent meaningful code structures per language
_SEMANTIC_NODES: dict[str, set[str]] = {
    "python": {
        "function_definition", "class_definition", "decorated_definition",
        "import_statement", "import_from_statement",
    },
    "javascript": {
        "function_declaration", "class_declaration", "method_definition",
        "arrow_function", "variable_declaration", "export_statement",
        "import_statement", "lexical_declaration",
    },
    "typescript": {
        "function_declaration", "class_declaration", "method_definition",
        "arrow_function", "variable_declaration", "export_statement",
        "import_statement", "interface_declaration", "type_alias_declaration",
        "enum_declaration", "lexical_declaration",
    },
    "java": {
        "class_declaration", "method_declaration", "interface_declaration",
        "constructor_declaration", "enum_declaration", "import_declaration",
    },
    "c": {
        "function_definition", "struct_specifier", "enum_specifier",
        "type_definition", "preproc_include", "declaration",
    },
    "cpp": {
        "function_definition", "class_specifier", "struct_specifier",
        "namespace_definition", "template_declaration", "preproc_include",
    },
    "go": {
        "function_declaration", "method_declaration", "type_declaration",
        "type_spec", "import_declaration",
    },
    "rust": {
        "function_item", "impl_item", "struct_item", "enum_item",
        "trait_item", "mod_item", "use_declaration", "type_item",
    },
}

# Map node types to human-readable symbol types
_SYMBOL_TYPE_MAP: dict[str, str] = {
    "function_definition": "function",
    "function_declaration": "function",
    "function_item": "function",
    "method_definition": "method",
    "method_declaration": "method",
    "class_definition": "class",
    "class_declaration": "class",
    "class_specifier": "class",
    "struct_specifier": "struct",
    "struct_item": "struct",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "enum_specifier": "enum",
    "enum_item": "enum",
    "namespace_definition": "namespace",
    "mod_item": "module",
    "impl_item": "impl",
    "trait_item": "trait",
    "type_declaration": "type",
    "type_alias_declaration": "type",
    "type_spec": "type",
    "type_item": "type",
    "type_definition": "type",
    "import_statement": "import",
    "import_from_statement": "import",
    "import_declaration": "import",
    "export_statement": "export",
    "constructor_declaration": "constructor",
    "decorated_definition": "decorated",
    "arrow_function": "function",
    "variable_declaration": "variable",
    "lexical_declaration": "variable",
    "declaration": "declaration",
    "template_declaration": "template",
    "preproc_include": "include",
    "use_declaration": "import",
}


@dataclass
class CodeChunk:
    """Represents a semantic code chunk extracted from a source file."""
    content: str
    file_path: str  # repo-relative
    language: str | None
    symbol_name: str | None
    symbol_type: str | None
    start_line: int
    end_line: int
    parent_symbol: str | None = None
    content_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]


_loaded_languages: dict[str, object] = {}
_parsers: dict[str, object] = {}


def _get_parser(language: str):
    """Get or create a tree-sitter parser for the given language."""
    if not _tree_sitter_available:
        return None

    if language in _parsers:
        return _parsers[language]

    pkg_name = _LANGUAGE_PACKAGES.get(language)
    if not pkg_name:
        return None

    try:
        import importlib
        mod = importlib.import_module(pkg_name)

        # tree-sitter-language packages expose language(), language_typescript(), or language_tsx()
        lang_func = getattr(mod, "language", None)
        if lang_func is None and pkg_name == "tree_sitter_typescript":
            lang_func = getattr(mod, "language_typescript", None) or getattr(mod, "language_tsx", None)

        if lang_func is None:
            logger.warning(f"No language function found in {pkg_name}")
            return None

        ts_language = tree_sitter.Language(lang_func())
        parser = tree_sitter.Parser(ts_language)
        _parsers[language] = parser
        _loaded_languages[language] = ts_language
        return parser
    except ImportError:
        logger.debug(f"Tree-sitter language package not installed: {pkg_name}")
        return None
    except Exception as e:
        logger.warning(f"Failed to load tree-sitter parser for {language}: {e}")
        return None


def _extract_symbol_name(node, source_bytes: bytes, language: str) -> str | None:
    """Extract the name of a symbol from an AST node."""
    # Look for identifier/name children
    name_fields = ["name", "declarator", "pattern"]
    for field_name in name_fields:
        child = node.child_by_field_name(field_name)
        if child:
            # For declarators, dig deeper to find the identifier
            if child.type in ("function_declarator", "pointer_declarator", "init_declarator"):
                inner = child.child_by_field_name("declarator") or child.child_by_field_name("name")
                if inner:
                    return source_bytes[inner.start_byte:inner.end_byte].decode("utf-8", errors="replace")
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")

    # Fallback: look for the first identifier child
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")

    return None


def _get_parent_symbol(node) -> str | None:
    """Get the name of the parent symbol, if any."""
    parent = node.parent
    while parent:
        if parent.type in _SYMBOL_TYPE_MAP:
            name_node = parent.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8", errors="replace") if hasattr(name_node, 'text') else None
        parent = parent.parent
    return None


def chunk_with_tree_sitter(
    content: str,
    file_path: str,
    language: str,
    max_chunk_size: int | None = None,
) -> list[CodeChunk]:
    """
    Parse source code with Tree-sitter and extract semantic chunks.

    Args:
        content: Source code text
        file_path: Repo-relative file path
        language: Programming language
        max_chunk_size: Maximum chunk size in characters

    Returns:
        List of CodeChunk objects representing semantic code units
    """
    max_chunk_size = max_chunk_size or settings.MAX_CHUNK_SIZE
    parser = _get_parser(language)

    if parser is None:
        return chunk_by_lines(content, file_path, language, max_chunk_size)

    try:
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        semantic_types = _SEMANTIC_NODES.get(language, set())
        if not semantic_types:
            return chunk_by_lines(content, file_path, language, max_chunk_size)

        chunks = []
        lines = content.split("\n")

        # Collect top-level semantic nodes
        def collect_semantic_nodes(node, depth=0):
            """Collect semantic nodes, preferring top-level ones."""
            if node.type in semantic_types and depth <= 2:
                chunks.append(_node_to_chunk(node, source_bytes, lines, file_path, language))
                # Don't recurse into this node's children for top-level chunking
                return
            for child in node.children:
                collect_semantic_nodes(child, depth + 1)

        collect_semantic_nodes(root)

        # If we got no semantic nodes, fall back to line chunking
        if not chunks:
            return chunk_by_lines(content, file_path, language, max_chunk_size)

        # Handle remaining code (imports, global statements, etc.)
        # that don't fall into semantic nodes
        covered_ranges = set()
        for chunk in chunks:
            for line in range(chunk.start_line, chunk.end_line + 1):
                covered_ranges.add(line)

        uncovered_lines = []
        current_block_start = None
        for i, line in enumerate(lines, 1):
            if i not in covered_ranges and line.strip():
                if current_block_start is None:
                    current_block_start = i
            else:
                if current_block_start is not None:
                    uncovered_content = "\n".join(lines[current_block_start - 1:i - 1])
                    if uncovered_content.strip():
                        chunks.append(CodeChunk(
                            content=uncovered_content,
                            file_path=file_path,
                            language=language,
                            symbol_name=None,
                            symbol_type="module",
                            start_line=current_block_start,
                            end_line=i - 1,
                        ))
                    current_block_start = None

        if current_block_start is not None:
            uncovered_content = "\n".join(lines[current_block_start - 1:])
            if uncovered_content.strip():
                chunks.append(CodeChunk(
                    content=uncovered_content,
                    file_path=file_path,
                    language=language,
                    symbol_name=None,
                    symbol_type="module",
                    start_line=current_block_start,
                    end_line=len(lines),
                ))

        # Sort by start line
        chunks.sort(key=lambda c: c.start_line)

        # Split oversized chunks
        final_chunks = []
        for chunk in chunks:
            if len(chunk.content) > max_chunk_size:
                final_chunks.extend(
                    _split_large_chunk(chunk, max_chunk_size)
                )
            else:
                final_chunks.append(chunk)

        return final_chunks

    except Exception as e:
        logger.warning(f"Tree-sitter parsing failed for {file_path}: {e}")
        return chunk_by_lines(content, file_path, language, max_chunk_size)


def _node_to_chunk(
    node, source_bytes: bytes, lines: list[str],
    file_path: str, language: str,
) -> CodeChunk:
    """Convert a tree-sitter node to a CodeChunk."""
    start_line = node.start_point[0] + 1  # 1-indexed
    end_line = node.end_point[0] + 1

    content = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    symbol_name = _extract_symbol_name(node, source_bytes, language)
    symbol_type = _SYMBOL_TYPE_MAP.get(node.type, node.type)
    parent_symbol = _get_parent_symbol(node)

    return CodeChunk(
        content=content,
        file_path=file_path,
        language=language,
        symbol_name=symbol_name,
        symbol_type=symbol_type,
        start_line=start_line,
        end_line=end_line,
        parent_symbol=parent_symbol,
    )


def _split_large_chunk(chunk: CodeChunk, max_size: int) -> list[CodeChunk]:
    """Split an oversized chunk into smaller pieces along line boundaries."""
    lines = chunk.content.split("\n")
    sub_chunks = []
    current_lines = []
    current_size = 0
    current_start = chunk.start_line

    for i, line in enumerate(lines):
        line_size = len(line) + 1  # +1 for newline
        if current_size + line_size > max_size and current_lines:
            sub_chunks.append(CodeChunk(
                content="\n".join(current_lines),
                file_path=chunk.file_path,
                language=chunk.language,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=current_start,
                end_line=current_start + len(current_lines) - 1,
                parent_symbol=chunk.parent_symbol,
            ))
            current_start = chunk.start_line + i
            current_lines = [line]
            current_size = line_size
        else:
            current_lines.append(line)
            current_size += line_size

    if current_lines:
        sub_chunks.append(CodeChunk(
            content="\n".join(current_lines),
            file_path=chunk.file_path,
            language=chunk.language,
            symbol_name=chunk.symbol_name,
            symbol_type=chunk.symbol_type,
            start_line=current_start,
            end_line=current_start + len(current_lines) - 1,
            parent_symbol=chunk.parent_symbol,
        ))

    return sub_chunks


def chunk_by_lines(
    content: str,
    file_path: str,
    language: str | None,
    max_chunk_size: int | None = None,
    overlap_lines: int | None = None,
) -> list[CodeChunk]:
    """
    Fallback chunker that splits by line count when Tree-sitter isn't available.
    Tries to split at blank lines for better boundaries.
    """
    max_chunk_size = max_chunk_size or settings.MAX_CHUNK_SIZE
    overlap = overlap_lines if overlap_lines is not None else settings.CHUNK_OVERLAP_LINES
    lines = content.split("\n")

    # If the whole file fits in one chunk, return it
    if len(content) <= max_chunk_size:
        return [CodeChunk(
            content=content,
            file_path=file_path,
            language=language,
            symbol_name=None,
            symbol_type="module",
            start_line=1,
            end_line=len(lines),
        )]

    # Split into chunks at reasonable boundaries
    chunks = []
    chunk_lines = []
    chunk_size = 0
    chunk_start = 1

    for i, line in enumerate(lines):
        line_size = len(line) + 1
        if chunk_size + line_size > max_chunk_size and chunk_lines:
            chunks.append(CodeChunk(
                content="\n".join(chunk_lines),
                file_path=file_path,
                language=language,
                symbol_name=None,
                symbol_type="module",
                start_line=chunk_start,
                end_line=chunk_start + len(chunk_lines) - 1,
            ))
            # Overlap
            overlap_start = max(0, len(chunk_lines) - overlap)
            chunk_lines = chunk_lines[overlap_start:]
            chunk_size = sum(len(l) + 1 for l in chunk_lines)
            chunk_start = chunk_start + len(chunk_lines) - overlap
            chunk_lines.append(line)
            chunk_size += line_size
        else:
            chunk_lines.append(line)
            chunk_size += line_size

    if chunk_lines:
        chunks.append(CodeChunk(
            content="\n".join(chunk_lines),
            file_path=file_path,
            language=language,
            symbol_name=None,
            symbol_type="module",
            start_line=chunk_start,
            end_line=chunk_start + len(chunk_lines) - 1,
        ))

    return chunks
