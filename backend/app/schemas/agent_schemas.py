from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------- Analyzer agent output ----------

class Violation(BaseModel):
    resource: str = Field(..., description="Terraform resource address, e.g. aws_s3_bucket.my_bucket")
    issue: str = Field(..., description="Plain-language description of the security issue")
    severity: Severity
    policy_reference: Optional[str] = Field(
        None, description="Which retrieved company policy clause this violates, if any"
    )
    static_tool_confirmed: Optional[str] = Field(
        None, description="e.g. checkov:CKV_AWS_18 -- set only if a static tool also flagged this resource"
    )


class AnalyzerOutput(BaseModel):
    violations: List[Violation]


# ---------- Remediation agent output ----------

class RemediatedResource(BaseModel):
    resource: str = Field(..., description="Terraform resource address this fix applies to")
    fixed_hcl: str = Field(..., description="The corrected HCL block for just this resource")
    explanation: str = Field(..., description="Plain-language explanation of what changed and why")


class RemediationOutput(BaseModel):
    fixes: List[RemediatedResource]


# ---------- Validator agent output ----------

class ValidatorFindingStatus(BaseModel):
    resource: str
    issue: str
    resolved: bool
    remaining_severity: Optional[Severity] = None


class ValidatorOutput(BaseModel):
    all_resolved: bool
    findings: List[ValidatorFindingStatus]
    summary: str