from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Org, UserRole
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


class AdminSignupRequest(BaseModel):
    org_name: str
    email: EmailStr
    password: str


class EmployeeSignupRequest(BaseModel):
    org_id: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    org_id: str
    email: EmailStr
    password: str


def _org_or_404(db: Session, org_id: str) -> Org:
    org = db.query(Org).filter(Org.id == org_id).first()
    if not org:
        # Deliberately the same wording a bad password would get -- an
        # attacker probing random Org IDs shouldn't be able to tell a
        # nonexistent org apart from a real one with a typo'd ID.
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/auth/admin/signup")
def admin_signup(payload: AdminSignupRequest, db: Session = Depends(get_db)):
    """Creates a brand new org AND its first user in one step, who becomes
    that org's admin. This is the ONLY way a new org comes into existence --
    there is no separate "create an org" endpoint. The returned org_id is
    what the admin then shares with their team so employees can join via
    /auth/employee/signup.
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
        "org_name": org.name,
        "user_id": user.id,
        "role": user.role,
    }


@router.post("/auth/employee/signup")
def employee_signup(payload: EmployeeSignupRequest, db: Session = Depends(get_db)):
    """Joins an EXISTING org as a regular (non-admin) user, given the Org ID
    the admin shared. This is the piece that was missing entirely before:
    previously there was no way to add a second person to an org at all --
    every signup created a brand new org.

    Deliberately self-service (no admin approval step) -- that's a
    reasonable tradeoff for a project at this scale, and the Org ID itself
    is the gate: you can't join an org you don't know the ID of. Always
    creates role=USER; there is no way to self-signup as admin into an
    existing org, which is what keeps policy uploads admin-controlled.
    """
    org = _org_or_404(db, payload.org_id)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, org_id=org.id, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": org.id,
        "org_name": org.name,
        "user_id": user.id,
        "role": user.role,
    }


def _login(payload: LoginRequest, db: Session, required_role: UserRole):
    """Shared logic for both login endpoints below. Checks org_id, email,
    password, AND role all at once -- every check fails with the exact
    same 'Invalid organization ID, email, or password' message, whichever
    one was actually wrong. That's deliberate: an admin-login attempt with
    a correct employee password would otherwise reveal "right credentials,
    wrong portal," which tells an attacker (or a confused employee) more
    than they should learn from a single error message. It also means an
    employee's credentials simply do not work on the admin login page at
    all, and an admin's don't work on the employee page -- not just
    "redirected," genuinely rejected by the API itself.
    """
    org = db.query(Org).filter(Org.id == payload.org_id).first()
    user = db.query(User).filter(User.email == payload.email).first()

    generic_error = HTTPException(
        status_code=401, detail="Invalid organization ID, email, or password"
    )

    if not org or not user:
        raise generic_error
    if user.org_id != org.id:
        raise generic_error
    if not verify_password(payload.password, user.hashed_password):
        raise generic_error
    if user.role != required_role:
        raise generic_error

    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": user.org_id,
        "org_name": org.name,
        "user_id": user.id,
        "role": user.role,
    }


@router.post("/auth/admin/login")
def admin_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Only succeeds for a user who is genuinely an admin of the given org."""
    return _login(payload, db, required_role=UserRole.ADMIN)


@router.post("/auth/employee/login")
def employee_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Only succeeds for a user who is a regular (non-admin) member of the
    given org -- an admin's own credentials will NOT work here, by design.
    """
    return _login(payload, db, required_role=UserRole.USER)
