"""
Mathematical utility functions for sample test repository.
"""

def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


class Calculator:
    """Simple stateful calculator."""

    def __init__(self, initial_value: float = 0.0):
        self.value = initial_value

    def add(self, n: float) -> float:
        self.value += n
        return self.value

    def reset(self) -> None:
        self.value = 0.0
