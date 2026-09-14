"""
Unit tests for AST-aware code chunker.
Verifies semantic extraction of functions, classes, and fallback splitting.
"""

from app.indexing.chunker import chunk_by_lines, chunk_with_tree_sitter


def test_chunk_python_functions_and_classes():
    code = """
def calculate_tax(amount: float, rate: float = 0.2) -> float:
    \"\"\"Calculate sales tax.\"\"\"
    return amount * rate


class InvoiceProcessor:
    \"\"\"Process customer invoices.\"\"\"

    def __init__(self, currency: str = "USD"):
        self.currency = currency

    def process(self, invoice_id: str) -> bool:
        return True
"""
    chunks = chunk_with_tree_sitter(code, "billing.py", "python")
    assert len(chunks) >= 2

    # Check function chunk
    func_chunk = next((c for c in chunks if c.symbol_name == "calculate_tax"), None)
    assert func_chunk is not None
    assert func_chunk.symbol_type == "function"
    assert "return amount * rate" in func_chunk.content

    # Check class chunk
    class_chunk = next((c for c in chunks if c.symbol_name == "InvoiceProcessor"), None)
    assert class_chunk is not None
    assert class_chunk.symbol_type == "class"


def test_chunk_javascript():
    code = """
function parseToken(raw) {
    return raw.split('.')[1];
}

class TokenValidator {
    validate(token) {
        return Boolean(token);
    }
}
"""
    chunks = chunk_with_tree_sitter(code, "token.js", "javascript")
    assert len(chunks) >= 2
    symbols = [c.symbol_name for c in chunks]
    assert "parseToken" in symbols or "TokenValidator" in symbols


def test_chunk_by_lines_fallback():
    lines = [f"line {i}: content item" for i in range(1, 101)]
    code = "\n".join(lines)

    chunks = chunk_by_lines(code, "data.txt", "text", max_chunk_size=500, overlap_lines=2)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.content) <= 600
        assert c.start_line <= c.end_line


def test_content_hash_stability():
    code = "def foo(): return 42"
    chunks1 = chunk_with_tree_sitter(code, "foo.py", "python")
    chunks2 = chunk_with_tree_sitter(code, "foo.py", "python")

    assert len(chunks1) == len(chunks2)
    assert chunks1[0].content_hash == chunks2[0].content_hash
