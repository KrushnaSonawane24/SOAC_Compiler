"""
SOAC Password Handling
======================

Secure password hashing using bcrypt.
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password securely.
    
    Uses bcrypt with automatic salt generation.
    """
    # Truncate to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Returns True if password matches.
    """
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
