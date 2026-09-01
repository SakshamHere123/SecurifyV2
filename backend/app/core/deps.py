import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_access_token

bearer_scheme = HTTPBearer()


class CurrentUser:
    """A plain container for what we trust about the caller, extracted from
    a verified token -- not a DB model, just the claims. Endpoints use
    current_user.org_id / .user_id / .role instead of accepting those as
    request parameters.
    """
    def __init__(self, user_id: str, org_id: str, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Decodes and verifies the bearer token on every protected request.

    This is the dependency that makes org_id/role trustworthy everywhere
    else in the app. From this point on, no endpoint should accept an
    org_id, user_id, or role from the request body or query params --
    they come from here instead, because THIS value was extracted from a
    token this server itself signed, not from whatever the client claims
    in a form field.
    """
    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(user_id=claims["sub"], org_id=claims["org_id"], role=claims["role"])


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Extra gate for admin-only endpoints (policy upload, user management).
    Layered on top of get_current_user rather than duplicating its logic --
    any endpoint using this dependency automatically also gets
    authentication (you can't check a role you never verified) for free.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user