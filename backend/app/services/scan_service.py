import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Scan, Finding, ScanStatus
from app.services.parser import parse_terraform_file, extract_raw_resource_blocks
from app.services.static_scan import run_checkov
from app.services.findings import normalize_checkov_findings
from app.services.controller_agent import run_scan_pipeline
from app.services.diff_builder import build_scan_diffs
from app.services.report_generator import generate_report_pdf

SCAN_STORAGE_DIR = "/app/storage/scans"


def create_and_run_scan(db: Session, org_id: str, user_id: str, filename: str, file_bytes: bytes) -> Scan:
    """Runs the full Phase 4 pipeline AND persists it properly:

    1. Creates the Scan row FIRST (status=pending) -- so even if something
       crashes mid-pipeline, there's a durable record that a scan was
       attempted, not silence.
    2. Saves the uploaded file to durable per-scan storage.
    3. Runs parse -> Checkov -> Controller (Analyzer/Remediation/Validator loop).
    4. Writes the corrected .tf, builds the diff, generates the PDF report,
       and creates one Finding row per violation.
    5. Marks the scan completed -- or failed, with the partial record kept,
       if anything raised.
    """
    scan = Scan(org_id=org_id, user_id=user_id, status=ScanStatus.PENDING, input_tf_path="")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    scan_dir = os.path.join(SCAN_STORAGE_DIR, scan.id)
    input_dir = os.path.join(scan_dir, "input")
    output_dir = os.path.join(scan_dir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    input_path = os.path.join(input_dir, filename)
    with open(input_path, "wb") as f:
        f.write(file_bytes)

    scan.input_tf_path = input_path
    scan.status = ScanStatus.RUNNING
    db.commit()

    try:
        parsed = parse_terraform_file(input_path)
        raw_blocks = extract_raw_resource_blocks(input_path)
        checkov_raw = run_checkov(input_dir)
        static_findings = normalize_checkov_findings(checkov_raw)

        result = run_scan_pipeline(
            org_id=org_id,
            resources=parsed["resources"],
            static_findings=static_findings,
            raw_blocks=raw_blocks,
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

        db.commit()
        db.refresh(scan)
        return scan

    except Exception:
        scan.status = ScanStatus.FAILED
        db.commit()
        raise


def _build_findings_list(result: dict) -> list[dict]:
    """Flattens the controller's violations + findings_status into one plain
    list of dicts -- the shared shape both Postgres persistence AND the PDF
    report are built from, so the two can never silently drift apart.
    """
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