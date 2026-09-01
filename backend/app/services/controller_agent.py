import os
import shutil
import tempfile

from app.schemas.agent_schemas import RemediatedResource
from app.services.ai_analyzer import analyze_resources
from app.services.remediation_agent import remediate_violations
from app.services.validator_agent import validate_remediation
from app.services.reconstruct import build_remediated_file

MAX_RETRIES = 3


def _merge_fixes(
    old_fixes: list[RemediatedResource], new_fixes: list[RemediatedResource]
) -> list[RemediatedResource]:
    """Keeps the latest fix per resource address. A retry's new attempt at
    fixing a resource replaces the previous attempt for that SAME resource --
    it never stacks on top of it, since each remediation call gets the full
    original resource context, not a diff of the last attempt.
    """
    merged = {f.resource: f for f in old_fixes}
    for f in new_fixes:
        merged[f.resource] = f
    return list(merged.values())


def run_scan_pipeline(
    org_id: str,
    resources: list[dict],
    static_findings: list[dict],
    raw_blocks: dict[str, str],
) -> dict:
    """The Controller agent. Runs Analyzer once, then loops Remediation ->
    Validator up to MAX_RETRIES times, each retry narrowed to only the
    violations the validator confirmed are still open. Stops as soon as
    everything is resolved, or once retries run out -- whichever comes first.
    """
    analyzer_output = analyze_resources(org_id, resources, static_findings)
    violations = analyzer_output.violations

    if not violations:
        return {
            "violations": [],
            "fixes": [],
            "findings_status": [],
            "validator_summary": "No violations found -- nothing to remediate.",
            "all_resolved": True,
            "retry_count": 0,
            "remediated_tf": None,
        }

    remaining_violations = violations
    fixes: list[RemediatedResource] = []
    validator_result = None
    attempts_used = 0

    for attempt in range(MAX_RETRIES):
        attempts_used = attempt + 1

        remediation_output = remediate_violations(resources, remaining_violations)
        fixes = _merge_fixes(fixes, remediation_output.fixes)

        tmp_dir = tempfile.mkdtemp(prefix="securify_validate_")
        try:
            remediated_text = build_remediated_file(raw_blocks, fixes)
            with open(os.path.join(tmp_dir, "main.tf"), "w") as f:
                f.write(remediated_text)

            # Validate against ALL original violations each round, not just
            # this round's targets -- guards against a "fix" that resolves
            # one issue but reintroduces another.
            validator_result = validate_remediation(tmp_dir, violations)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if validator_result.all_resolved:
            break

        remaining_violations = [
            v for v in violations
            if any(
                fs.resource == v.resource and fs.issue == v.issue and not fs.resolved
                for fs in validator_result.findings
            )
        ]
        if not remaining_violations:
            # Nothing left the validator flagged as unresolved -- stop even
            # if all_resolved wasn't literally True (edge case safety net).
            break

    return {
        "violations": [v.model_dump() for v in violations],
        "fixes": [f.model_dump() for f in fixes],
        "findings_status": [f.model_dump() for f in validator_result.findings] if validator_result else [],
        "validator_summary": validator_result.summary if validator_result else "",
        "all_resolved": validator_result.all_resolved if validator_result else False,
        "retry_count": attempts_used,
        "remediated_tf": build_remediated_file(raw_blocks, fixes),
    }