import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def run_checkov(tf_dir: str) -> dict:
    """Runs Checkov against a directory of .tf files and returns the parsed
    JSON report.

    Checkov is deterministic and rule-based -- it already knows hundreds of
    well-known misconfigurations (public S3 buckets, open security groups,
    missing encryption, over-broad IAM). Running it first means the LLM
    (added in Phase 4) never has to 'remember' these rules from scratch --
    it only has to reason about company-specific policy on top of what
    Checkov already caught.
    """
    logger.info("Running Checkov against %s", tf_dir)
    result = subprocess.run(
        ["checkov", "-d", tf_dir, "-o", "json", "--quiet", "--compact"],
        capture_output=True,
        text=True,
    )
    # Checkov exits non-zero when it finds failing checks -- that is expected
    # behavior, not a crash. We only care whether stdout has valid JSON.
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Checkov produced no valid JSON output: %s", result.stderr[:500])
        return {"error": "checkov produced no valid JSON output", "stderr": result.stderr}