import os
import shutil
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Scan, Finding
from app.core.deps import get_current_user, CurrentUser
from app.services.parser import parse_terraform_file, extract_raw_resource_blocks
from app.services.static_scan import run_checkov
from app.services.findings import normalize_checkov_findings
from app.services.ai_analyzer import analyze_resources
from app.services.remediation_agent import remediate_violations
from app.services.controller_agent import run_scan_pipeline
from app.services.scan_service import create_and_run_scan
from app.services.diff_builder import build_scan_diffs

router = APIRouter()


def _get_owned_scan(db: Session, scan_id: str, current_user: CurrentUser) -> Scan:
    """Fetches a scan AND enforces org isolation in one place, reused by
    every endpoint below that operates on an existing scan_id.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan or scan.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/scan/analyze")
async def analyze_terraform(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
    if not file.filename.endswith(".tf"):
        raise HTTPException(status_code=400, detail="Only .tf files are accepted")

    tmp_dir = tempfile.mkdtemp(prefix="securify_scan_")
    tf_path = os.path.join(tmp_dir, file.filename)

    try:
        with open(tf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        parsed = parse_terraform_file(tf_path)
        checkov_raw = run_checkov(tmp_dir)
        findings = normalize_checkov_findings(checkov_raw)

        return {
            "resource_count": parsed["resource_count"],
            "resources": parsed["resources"],
            "findings": findings,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/scan/analyze-ai")
async def analyze_terraform_with_ai(
    file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)
):
    if not file.filename.endswith(".tf"):
        raise HTTPException(status_code=400, detail="Only .tf files are accepted")

    tmp_dir = tempfile.mkdtemp(prefix="securify_scan_")
    tf_path = os.path.join(tmp_dir, file.filename)

    try:
        with open(tf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        parsed = parse_terraform_file(tf_path)
        checkov_raw = run_checkov(tmp_dir)
        static_findings = normalize_checkov_findings(checkov_raw)

        analyzer_output = analyze_resources(current_user.org_id, parsed["resources"], static_findings)

        return {
            "resource_count": parsed["resource_count"],
            "static_findings": static_findings,
            "ai_violations": analyzer_output.model_dump()["violations"],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/scan/remediate-ai")
async def analyze_and_remediate(
    file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)
):
    if not file.filename.endswith(".tf"):
        raise HTTPException(status_code=400, detail="Only .tf files are accepted")

    tmp_dir = tempfile.mkdtemp(prefix="securify_scan_")
    tf_path = os.path.join(tmp_dir, file.filename)

    try:
        with open(tf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        parsed = parse_terraform_file(tf_path)
        checkov_raw = run_checkov(tmp_dir)
        static_findings = normalize_checkov_findings(checkov_raw)

        analyzer_output = analyze_resources(current_user.org_id, parsed["resources"], static_findings)
        remediation_output = remediate_violations(parsed["resources"], analyzer_output.violations)

        return {
            "ai_violations": analyzer_output.model_dump()["violations"],
            "fixes": remediation_output.model_dump()["fixes"],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/scan/run")
async def run_full_scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not file.filename.endswith(".tf"):
        raise HTTPException(status_code=400, detail="Only .tf files are accepted")

    file_bytes = await file.read()
    scan = create_and_run_scan(
        db,
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        filename=file.filename,
        file_bytes=file_bytes,
    )

    return {
        "scan_id": scan.id,
        "status": scan.status,
        "retry_count": scan.retry_count,
        "output_tf_path": scan.output_tf_path,
    }


@router.get("/scans")
def list_scans(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """Lists every scan for the caller's org, newest first, with a quick
    resolved/total findings count per scan so the dashboard's history table
    can render without a separate request per row.

    Org-wide (not filtered to just the caller's own scans) -- like policies,
    scan history is a team-visible thing, consistent with "any teammate can
    see what's already been audited," not a private per-user log.
    """
    scans = db.query(Scan).filter(Scan.org_id == current_user.org_id).order_by(Scan.created_at.desc()).all()

    results = []
    for scan in scans:
        findings = db.query(Finding).filter(Finding.scan_id == scan.id).all()
        total = len(findings)
        resolved = sum(1 for f in findings if f.resolved == "true")
        results.append({
            "scan_id": scan.id,
            "status": scan.status,
            "retry_count": scan.retry_count,
            "created_at": scan.created_at,
            "completed_at": scan.completed_at,
            "filename": os.path.basename(scan.input_tf_path) if scan.input_tf_path else None,
            "total_findings": total,
            "resolved_findings": resolved,
        })
    return results


@router.get("/scan/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    scan = _get_owned_scan(db, scan_id, current_user)
    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

    return {
        "scan_id": scan.id,
        "status": scan.status,
        "retry_count": scan.retry_count,
        "input_tf_path": scan.input_tf_path,
        "output_tf_path": scan.output_tf_path,
        "report_path": scan.report_path,
        "created_at": scan.created_at,
        "completed_at": scan.completed_at,
        "findings": [
            {
                "resource": f.resource,
                "issue": f.issue,
                "severity": f.severity,
                "policy_reference": f.policy_reference,
                "static_tool_confirmed": f.static_tool_confirmed,
                "resolved": f.resolved,
            }
            for f in findings
        ],
    }


@router.get("/scan/{scan_id}/diff")
def get_scan_diff(
    scan_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
):
    scan = _get_owned_scan(db, scan_id, current_user)
    if not scan.output_tf_path:
        raise HTTPException(status_code=400, detail="This scan has no remediated output to diff against")

    diffs = build_scan_diffs(scan.input_tf_path, scan.output_tf_path)
    return {"scan_id": scan.id, "diffs": diffs}


@router.get("/scan/{scan_id}/download/tf")
def download_remediated_tf(
    scan_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
):
    scan = _get_owned_scan(db, scan_id, current_user)
    if not scan.output_tf_path or not os.path.exists(scan.output_tf_path):
        raise HTTPException(status_code=404, detail="No remediated Terraform file available for this scan")

    return FileResponse(
        path=scan.output_tf_path,
        media_type="application/octet-stream",
        filename=os.path.basename(scan.output_tf_path),
    )


@router.get("/scan/{scan_id}/download/report")
def download_report(
    scan_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
):
    scan = _get_owned_scan(db, scan_id, current_user)
    if not scan.report_path or not os.path.exists(scan.report_path):
        raise HTTPException(status_code=404, detail="No report available for this scan")

    return FileResponse(
        path=scan.report_path,
        media_type="application/pdf",
        filename=f"securify-report-{scan.id}.pdf",
    )