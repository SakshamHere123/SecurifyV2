from app.schemas.agent_schemas import ValidatorOutput, ValidatorFindingStatus, Violation
from app.services.static_scan import run_checkov
from app.services.findings import normalize_checkov_findings


def validate_remediation(tf_dir: str, original_violations: list[Violation]) -> ValidatorOutput:
    """The Validator agent. Re-runs Checkov -- the SAME deterministic tool
    from Phase 2 -- against the reconstructed, remediated file.

    This function deliberately makes NO LLM call. The architecture's whole
    point here is "don't trust the remediation agent's opinion of itself" --
    an LLM grading its own homework is not validation. Re-running a
    deterministic scanner and diffing the results is.
    """
    checkov_raw = run_checkov(tf_dir)

    parsing_errors = checkov_raw.get("summary", {}).get("parsing_errors", 0)
    if parsing_errors:
        # The remediated file failed to parse as valid HCL at all -- this is
        # a harder failure than "violation still present." Zero findings from
        # a broken parse looks identical to zero findings from a clean file,
        # so without this check a syntax-broken fix would be misreported as
        # "all resolved." Treat every violation as unresolved instead, so the
        # controller retries remediation rather than reporting false success.
        findings_status = [
            ValidatorFindingStatus(
                resource=v.resource, issue=v.issue, resolved=False, remaining_severity=v.severity
            )
            for v in original_violations
        ]
        return ValidatorOutput(
            all_resolved=False,
            findings=findings_status,
            summary="Remediated Terraform failed to parse as valid HCL -- treating all violations as unresolved.",
        )

    new_findings = normalize_checkov_findings(checkov_raw)

    still_flagged_checks = {
        f["static_tool_confirmed"] for f in new_findings if f.get("static_tool_confirmed")
    }
    still_flagged_resources = {f["resource"] for f in new_findings}

    findings_status = []
    for v in original_violations:
        if v.static_tool_confirmed:
            # We know the exact Checkov rule that originally confirmed this
            # violation -- resolved means that specific rule no longer fires.
            resolved = v.static_tool_confirmed not in still_flagged_checks
        else:
            # LLM-only finding, no static rule to check against. Conservative
            # fallback: resolved only if the resource has no findings left at all.
            resolved = v.resource not in still_flagged_resources

        findings_status.append(ValidatorFindingStatus(
            resource=v.resource,
            issue=v.issue,
            resolved=resolved,
            remaining_severity=None if resolved else v.severity,
        ))

    all_resolved = all(f.resolved for f in findings_status)
    resolved_count = sum(1 for f in findings_status if f.resolved)

    if not findings_status:
        summary = "No violations were found to validate."
    else:
        summary = f"{resolved_count}/{len(findings_status)} violations resolved after remediation."
        if not all_resolved:
            summary += " Remaining issues will be sent back to the remediation agent for another attempt."

    return ValidatorOutput(all_resolved=all_resolved, findings=findings_status, summary=summary)