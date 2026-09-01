import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum, Integer, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Org(Base):
    """A company/tenant. Everything else (users, policies, scans) belongs to one org."""
    __tablename__ = "orgs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="org")
    policies = relationship("Policy", back_populates="org")
    scans = relationship("Scan", back_populates="org")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)

    org = relationship("Org", back_populates="users")


class Policy(Base):
    """A company security policy document, versioned. Admin-uploaded, feeds the RAG index."""
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=False)
    filename = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    storage_path = Column(String, nullable=False)  # where the raw file lives
    uploaded_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    org = relationship("Org", back_populates="policies")


class Scan(Base):
    """One end-to-end run: upload -> parse -> analyze -> remediate -> validate -> report."""
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ScanStatus), nullable=False, default=ScanStatus.PENDING)
    input_tf_path = Column(String, nullable=False)
    output_tf_path = Column(String, nullable=True)
    report_path = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    org = relationship("Org", back_populates="scans")
    findings = relationship("Finding", back_populates="scan")


class Finding(Base):
    """One violation found in a scan: what resource, what rule, what severity, fixed or not."""
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    scan_id = Column(UUID(as_uuid=False), ForeignKey("scans.id"), nullable=False)
    resource = Column(String, nullable=False)          # e.g. aws_s3_bucket.my_bucket
    issue = Column(Text, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    policy_reference = Column(Text, nullable=True)      # which company policy clause this maps to
    static_tool_confirmed = Column(String, nullable=True)  # e.g. "checkov: CKV_AWS_18"
    resolved = Column(String, default="false")          # "true"/"false" — kept simple for Phase 1

    scan = relationship("Scan", back_populates="findings")


class AuditLog(Base):
    """Who did what, when. Every upload, login, and scan trigger gets an entry."""
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)   # e.g. "policy_upload", "scan_triggered"
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
