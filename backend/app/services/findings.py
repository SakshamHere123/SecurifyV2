from typing import Any


def normalize_checkov_findings(checkov_output: dict) -> list[dict[str, Any]]:
    """Converts Checkov's raw JSON report into Securify's internal finding shape:
    resource, issue, severity, static_tool_confirmed.

    This matters beyond Phase 2: in Phase 4 the AI analyzer agent will output
    findings in this exact same shape. Normalizing both sources to one schema
    now means the report generator (Phase 5) never has to special-case
    'was this a Checkov finding or an LLM finding' -- it just merges the list.
    """
    findings = []
    failed_checks = checkov_output.get("results", {}).get("failed_checks", [])

    for check in failed_checks:
        findings.append({
            "resource": check.get("resource"),
            "issue": check.get("check_name"),
            "severity": _map_severity(check.get("severity")),
            "static_tool_confirmed": f"checkov:{check.get('check_id')}",
            "guideline": check.get("guideline"),
        })

    return findings


def _map_severity(checkov_severity: str | None) -> str:
    # Checkov leaves severity null on some checks (usually best-practice ones,
    # not hard failures). Default to "medium" so nothing silently vanishes
    # from the report instead of being ranked.
    if not checkov_severity:
        return "medium"
    return checkov_severity.lower()
