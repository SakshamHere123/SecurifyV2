import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, JSON, Float
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
    __tablename__ = "policies"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=False)
    filename = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    storage_path = Column(String, nullable=False)
    uploaded_by = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    org = relationship("Org", back_populates="policies")


class Scan(Base):
    __tablename__ = "scans"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ScanStatus), nullable=False, default=ScanStatus.PENDING)
    current_step = Column(String, nullable=True)  # e.g. "parsing", "analyzing", "remediating" -- polled by the frontend
    input_tf_path = Column(String, nullable=False)
    output_tf_path = Column(String, nullable=True)
    report_path = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    org = relationship("Org", back_populates="scans")
    findings = relationship("Finding", back_populates="scan")
    llm_usage = relationship("LLMUsage", back_populates="scan")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    scan_id = Column(UUID(as_uuid=False), ForeignKey("scans.id"), nullable=False)
    resource = Column(String, nullable=False)
    issue = Column(Text, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    policy_reference = Column(Text, nullable=True)
    static_tool_confirmed = Column(String, nullable=True)
    resolved = Column(String, default="false")
    scan = relationship("Scan", back_populates="findings")


class LLMUsage(Base):
    """One row per structured-output LLM call (Analyzer, Remediation).
    Written by llm_client.call_structured right after each call returns,
    tagged with whichever scan is current in that worker process -- see
    current_scan_id in logging_config.py, the same mechanism Part 3 uses
    to tag log lines, reused here so scan_id doesn't need to be threaded
    through every agent function signature just for cost tracking.
    """
    __tablename__ = "llm_usage"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    scan_id = Column(UUID(as_uuid=False), ForeignKey("scans.id"), nullable=False)
    agent = Column(String, nullable=False)  # "analyzer" | "remediation"
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    scan = relationship("Scan", back_populates="llm_usage")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("orgs.id"), nullable=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)