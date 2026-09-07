import logging
import os
import shutil
import tempfile

from app.schemas.agent_schemas import RemediatedResource
from app.services.ai_analyzer import analyze_resources
from app.services.remediation_agent import remediate_violations
from app.services.validator_agent import validate_remediation
from app.services.reconstruct import build_remediated_file

logger = logging.getLogger(__name__)
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
    on_step=None,
) -> dict:
    """The Controller agent. Runs Analyzer once, then loops Remediation ->
    Validator up to MAX_RETRIES times, each retry narrowed to only the
    violations the validator confirmed are still open. Stops as soon as
    everything is resolved, or once retries run out -- whichever comes first.

    on_step: optional callback invoked with a short string ("analyzing",
    "remediating", "validating") at each real stage transition. This is
    what makes Phase 7's progress polling genuinely live rather than a
    guess -- the caller (the Celery worker) persists whatever this reports
    directly onto the Scan row.
    """
    def _report(step: str):
        if on_step:
            on_step(step)

    _report("analyzing")
    analyzer_output = analyze_resources(org_id, resources, static_findings)
    violations = analyzer_output.violations
    logger.info("Analyzer found %d violations", len(violations))

    if not violations:
        logger.info("No violations -- skipping remediation/validation entirely")
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
        logger.info(
            "Remediation attempt %d/%d for %d remaining violation(s)",
            attempts_used, MAX_RETRIES, len(remaining_violations),
        )

        _report("remediating")
        remediation_output = remediate_violations(resources, remaining_violations)
        fixes = _merge_fixes(fixes, remediation_output.fixes)

        tmp_dir = tempfile.mkdtemp(prefix="securify_validate_")
        try:
            remediated_text = build_remediated_file(raw_blocks, fixes)
            with open(os.path.join(tmp_dir, "main.tf"), "w") as f:
                f.write(remediated_text)

            _report("validating")
            # Validate against ALL original violations each round, not just
            # this round's targets -- guards against a "fix" that resolves
            # one issue but reintroduces another.
            validator_result = validate_remediation(tmp_dir, violations)
            logger.info("Validator (attempt %d): %s", attempts_used, validator_result.summary)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        if validator_result.all_resolved:
            logger.info("All violations resolved after %d attempt(s)", attempts_used)
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

    if validator_result and not validator_result.all_resolved:
        logger.warning(
            "Retries exhausted (%d/%d) -- %d violation(s) still unresolved",
            attempts_used, MAX_RETRIES, len(remaining_violations),
        )

    return {
        "violations": [v.model_dump() for v in violations],
        "fixes": [f.model_dump() for f in fixes],
        "findings_status": [f.model_dump() for f in validator_result.findings] if validator_result else [],
        "validator_summary": validator_result.summary if validator_result else "",
        "all_resolved": validator_result.all_resolved if validator_result else False,
        "retry_count": attempts_used,
        "remediated_tf": build_remediated_file(raw_blocks, fixes),
    }