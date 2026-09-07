import glob
import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.logging_config import current_scan_id
from app.db.models import Finding, Scan, ScanStatus
from app.db.session import SessionLocal
from app.services.controller_agent import run_scan_pipeline
from app.services.diff_builder import build_scan_diffs
from app.services.findings import normalize_checkov_findings
from app.services.parser import extract_raw_resource_blocks, parse_terraform_file
from app.services.report_generator import generate_report_pdf
from app.services.static_scan import run_checkov

logger = logging.getLogger(__name__)
SCAN_STORAGE_DIR = "/app/storage/scans"


def create_pending_scan(db: Session, org_id: str, user_id: str, filename: str, file_bytes: bytes) -> Scan:
    """Creates the Scan row and saves the uploaded file to durable storage,
    then returns immediately -- it does NOT run the pipeline.
    """
    scan = Scan(org_id=org_id, user_id=user_id, status=ScanStatus.PENDING, input_tf_path="")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    scan_dir = os.path.join(SCAN_STORAGE_DIR, scan.id)
    input_dir = os.path.join(scan_dir, "input")
    os.makedirs(input_dir, exist_ok=True)

    input_path = os.path.join(input_dir, filename)
    with open(input_path, "wb") as f:
        f.write(file_bytes)

    scan.input_tf_path = input_path
    db.commit()
    db.refresh(scan)
    return scan


def run_scan_job(scan_id: str) -> None:
    """Runs the actual pipeline for an already-created scan. This is the
    function the Celery worker calls.
    """
    current_scan_id.set(scan_id)
    logger.info("Scan job started")

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.warning("Scan job started but scan_id no longer exists in DB")
            return

        def report_step(step: str):
            """Persists the pipeline's current step immediately."""
            scan.current_step = step
            db.commit()

        scan.status = ScanStatus.RUNNING
        report_step("parsing")

        input_path = scan.input_tf_path
        input_dir = os.path.dirname(input_path)
        scan_dir = os.path.dirname(input_dir)
        output_dir = os.path.join(scan_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(input_path)

        # Run parsing directly in worker environment
        tf_files = glob.glob(os.path.join(input_dir, "*.tf"))
        target_tf_file = tf_files[0] if tf_files else input_path

        parsed = parse_terraform_file(target_tf_file) if os.path.exists(target_tf_file) else {"resource_count": 0, "resources": []}
        raw_blocks = extract_raw_resource_blocks(target_tf_file) if os.path.exists(target_tf_file) else {}
        logger.info("Parsed %d resources", parsed.get("resource_count", 0))

        report_step("static_analysis")
        checkov_raw = run_checkov(input_dir)
        static_findings = normalize_checkov_findings(checkov_raw)
        logger.info("Checkov found %d static findings", len(static_findings))

        result = run_scan_pipeline(
            org_id=scan.org_id,
            resources=parsed["resources"],
            static_findings=static_findings,
            raw_blocks=raw_blocks,
            on_step=report_step,
        )

        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as f:
            f.write(result["remediated_tf"] or "")

        findings_list = _build_findings_list(result)
        _persist_findings(db, scan.id, findings_list)

        scan.output_tf_path = output_path
        scan.retry_count = result["retry_count"]
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()

        diffs = build_scan_diffs(input_path, output_path)
        report_path = os.path.join(output_dir, "report.pdf")
        generate_report_pdf(
            output_path=report_path,
            scan={"scan_id": scan.id, "status": scan.status.value, "retry_count": scan.retry_count},
            findings=findings_list,
            diffs=diffs,
        )
        scan.report_path = report_path
        scan.current_step = "done"

        db.commit()
        logger.info(
            "Scan job completed: status=%s retries=%d all_resolved=%s",
            scan.status.value, scan.retry_count, result["all_resolved"],
        )

    except Exception:
        db.rollback()
        logger.exception("Scan job failed")
        failed_scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if failed_scan:
            failed_scan.status = ScanStatus.FAILED
            db.commit()
        raise
    finally:
        db.close()


def _build_findings_list(result: dict) -> list[dict]:
    resolved_by_key = {
        (f["resource"], f["issue"]): f["resolved"] for f in result.get("findings_status", [])
    }

    findings = []
    for v in result["violations"]:
        findings.append({
            "resource": v["resource"],
            "issue": v["issue"],
            "severity": v["severity"],
            "policy_reference": v.get("policy_reference"),
            "static_tool_confirmed": v.get("static_tool_confirmed"),
            "resolved": resolved_by_key.get((v["resource"], v["issue"]), False),
        })
    return findings


def _persist_findings(db: Session, scan_id: str, findings_list: list[dict]) -> None:
    for f in findings_list:
        db.add(Finding(
            scan_id=scan_id,
            resource=f["resource"],
            issue=f["issue"],
            severity=f["severity"],
            policy_reference=f["policy_reference"],
            static_tool_confirmed=f["static_tool_confirmed"],
            resolved="true" if f["resolved"] else "false",
        ))