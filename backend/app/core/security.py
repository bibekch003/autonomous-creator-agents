"""Password hashing, session tokens and a small in-process rate limiter.

Choices worth knowing:
* PBKDF2-HMAC-SHA256 from the standard library. No bcrypt/argon2 wheel to compile on
  Windows, no C toolchain, and it is a recognised KDF (NIST SP 800-132) when the
  iteration count is high. Passwords are never stored or logged in plain text.
* Opaque session tokens in an HttpOnly cookie, stored server-side so a logout or a
  password change can revoke them immediately. No JWT in localStorage (XSS-readable).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from app.core.config import settings

ALGORITHM = "pbkdf2_sha256"
_SALT_BYTES = 16


def hash_password(password: str, *, iterations: int | None = None) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    iters = iterations or settings.password_iterations
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return f"{ALGORITHM}${iters}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, digest_hex = stored.split("$")
        if algo != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), int(iters_s))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_fingerprint(token: str) -> str:
    """Sessions are stored by hash, so a database leak does not hand over live sessions."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Rate limiting (in-process; a single worker. Swap for Redis when you scale out.)
# ---------------------------------------------------------------------------
_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit_hit(key: str, *, limit: int | None = None, window: int | None = None) -> bool:
    """Return True when the caller is over the limit."""
    limit = limit or settings.max_login_attempts
    window = window or settings.login_window_seconds
    now = time.monotonic()
    bucket = _buckets[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    bucket.append(now)
    return len(bucket) > limit


def rate_limit_reset(key: str) -> None:
    _buckets.pop(key, None)
