from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hashes a password with bcrypt. bcrypt includes its own random salt
    per hash automatically -- two users with the same password get
    completely different hashed_password values, so the stored hashes
    alone can never reveal that two accounts share a password.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Checks a plaintext password against a stored bcrypt hash. We NEVER
    decrypt the hash to compare -- bcrypt hashing is one-way by design --
    we re-hash the attempt with the same salt (embedded in `hashed`) and
    compare the results.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, org_id: str, role: str) -> str:
    """Issues a JWT containing exactly what every downstream endpoint needs
    to enforce access control: WHO the caller is (sub), WHICH org they
    belong to (org_id), and WHAT they're allowed to do (role).

    Putting org_id in the token itself -- not trusting an org_id the client
    sends in the request -- is what turns multi-tenancy from "a convention
    everyone has to remember" into "the server can't be tricked into
    reading the wrong org's data." Part 2 wires this up.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "org_id": org_id, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verifies the token's signature and expiry, returns its claims.
    Raises jwt.PyJWTError (caught by the auth dependency in Part 2) if the
    token is expired, malformed, or signed with a different secret --
    i.e. if it wasn't genuinely issued by this server.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])