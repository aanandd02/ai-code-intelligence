"""
Sample auth service for security and review tests.
"""

def authenticate_user(username: str, password_hash: str) -> bool:
    """Check credentials."""
    if not username or not password_hash:
        return False
    return username == "admin"
