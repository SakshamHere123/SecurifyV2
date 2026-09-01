from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Org, UserRole
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


class SignupRequest(BaseModel):
    org_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Creates a brand new org AND its first user in one step, who becomes
    that org's admin. This is the ONLY way an org can come into existence
    from here on -- it replaces Phase 3/5's unauthenticated /org and /user
    endpoints, which anyone could hit to create orgs or users with no
    password at all. Delete those two files; this is what they become.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    org = Org(name=payload.org_name)
    db.add(org)
    db.commit()
    db.refresh(org)

    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, org_id=org.id, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": org.id,
        "user_id": user.id,
        "role": user.role,
    }


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Verifies credentials, issues a fresh token. Deliberately returns the
    SAME 'Invalid email or password' message whether the email doesn't
    exist or the password is wrong -- distinguishing the two would let an
    attacker enumerate which emails have accounts on the system.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": user.org_id,
        "user_id": user.id,
        "role": user.role,
    }