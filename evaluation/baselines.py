"""
baselines.py -- the five pipelines compared in the evaluation (B1-B5).

IMPORTANT: import this module only AFTER eval_env.bootstrap() has run, because
it imports the real Securify backend (`app.services.*`).

Design rules
------------
* Every pipeline reuses the backend's real functions -- parse_terraform_file,
  run_checkov, analyze_resources, remediate_violations, build_remediated_file,
  run_scan_pipeline. Prompts, schemas, model, and logic are the project's own.
* The ONLY differences between B2, B3, B4 and B5 are the ablation switches
  below (what context the Analyzer sees, and how "resolved" is decided).
* Runners never see the ground truth. They output raw detections + raw
  remediation artifacts; scoring is done separately (Part 3).

    id  name                     Checkov -> LLM   RAG policy   Remediation        "Resolved?" decided by
    --  -----------------------  ---------------  -----------  -----------------  ---------------------------
    B1  Checkov only             (is the tool)    no           none               n/a
    B2  LLM only                 no               no           1 pass             LLM self-assessment
    B3  Checkov + LLM            yes              no           1 pass             LLM self-assessment
    B4  Checkov + RAG + LLM      yes              yes          1 pass             LLM self-assessment
    B5  Securify (full)          yes              yes          controller loop    independent Checkov re-scan
                                                               (<=3 attempts)

Known limitation of B2: the Analyzer prompt is unchanged, so with no Checkov
findings it sees "Static tool findings: none" (rather than "tool not run").
That is the closest ablation possible without editing the project's prompt.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pydantic import BaseModel

from eval_env import ORG_ID, stage

from app.services.ai_analyzer import analyze_resources
from app.services.controller_agent import run_scan_pipeline
from app.services.findings import normalize_checkov_findings
from app.services.llm_client import call_structured
from app.services.parser import extract_raw_resource_blocks, parse_terraform_file
from app.services.reconstruct import build_remediated_file
from app.services.remediation_agent import remediate_violations
from app.services.static_scan import run_checkov


@dataclass(frozen=True)
class BaselineConfig:
    id: str
    name: str
    uses_checkov: bool
    uses_rag: bool
    mode: str  # "static_only" | "llm_single_pass" | "securify_pipeline"


BASELINES = {
    "B1": BaselineConfig("B1", "Checkov", False, False, "static_only"),
    "B2": BaselineConfig("B2", "LLM Only", False, False, "llm_single_pass"),
    "B3": BaselineConfig("B3", "Checkov + LLM", True, False, "llm_single_pass"),
    "B4": BaselineConfig("B4", "Checkov + RAG + LLM", True, True, "llm_single_pass"),
    "B5": BaselineConfig("B5", "Securify", True, True, "securify_pipeline"),
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

@contextmanager
def _timed(trace: dict, key: str):
    t = time.perf_counter()
    try:
        yield
    finally:
        trace[key] = trace.get(key, 0.0) + (time.perf_counter() - t)


def _sev(value) -> str:
    return str(getattr(value, "value", value)).lower()


def _prepare(tmp_dir: str):
    """Same parse steps scan_service.run_scan_job performs."""
    tf = sorted(Path(tmp_dir).glob("*.tf"))[0]
    parsed = parse_terraform_file(str(tf))
    raw_blocks = extract_raw_resource_blocks(str(tf))
    return parsed["resources"], raw_blocks


def _checkov(tmp_dir: str, trace: dict):
    """The backend's own run_checkov + normalize_checkov_findings."""
    with _timed(trace, "checkov_s"):
        raw = run_checkov(tmp_dir)
    if not isinstance(raw, dict) or "results" not in raw:
        detail = raw.get("error") if isinstance(raw, dict) else f"unexpected {type(raw).__name__} output"
        stderr = (raw.get("stderr", "") if isinstance(raw, dict) else "")[:300]
        raise RuntimeError(f"Checkov produced no usable output: {detail} {stderr}")
    findings = normalize_checkov_findings(raw)
    parsing_errors = raw.get("summary", {}).get("parsing_errors", 0)
    return findings, parsing_errors


def _detection(resource, issue, severity, policy_reference, static_tool_confirmed, source) -> dict:
    return {
        "resource": resource,
        "issue": issue,
        "severity": _sev(severity),
        "policy_reference": policy_reference,
        "static_tool_confirmed": static_tool_confirmed,
        "source": source,  # "checkov" (rule-based) or "llm" (Analyzer output)
    }


def _det_from_violation(v) -> dict:
    """v is a pydantic Violation (B2-B4) or the dict run_scan_pipeline returns (B5)."""
    g = (lambda k: getattr(v, k, None)) if not isinstance(v, dict) else (lambda k: v.get(k))
    return _detection(g("resource"), g("issue"), g("severity"),
                      g("policy_reference"), g("static_tool_confirmed"), "llm")


def _fix_dicts(fixes) -> List[dict]:
    out = []
    for f in fixes:
        d = f if isinstance(f, dict) else f.model_dump()
        out.append({"resource": d["resource"], "explanation": d["explanation"], "fixed_hcl": d["fixed_hcl"]})
    return out


# ---------------------------------------------------------------------------
# B1 -- Checkov only
# ---------------------------------------------------------------------------

def run_b1(cfg: BaselineConfig, tmp_dir: str, trace: dict) -> dict:
    findings, parsing_errors = _checkov(tmp_dir, trace)
    detections = [
        _detection(f["resource"], f["issue"], f["severity"], None, f["static_tool_confirmed"], "checkov")
        for f in findings
    ]
    return {
        "detections": detections,
        "checkov_findings": findings,
        "checkov_parsing_errors": parsing_errors,
        "resource_count": None,
        "remediation": None,
    }


# ---------------------------------------------------------------------------
# B2 / B3 / B4 -- single-pass LLM pipelines with LLM self-assessment
# ---------------------------------------------------------------------------

class _SelfAssessItem(BaseModel):
    index: int
    resolved: bool


class SelfAssessOutput(BaseModel):
    findings: List[_SelfAssessItem]


SELF_ASSESS_SYSTEM_PROMPT = """You are reviewing Terraform security fixes. For each \
numbered violation you are given the corrected HCL for the affected resource (and, when \
available, the company policy requirement the violation breaks).

For every violation, decide by reading the corrected HCL whether the violation is now \
fully resolved. Answer resolved=false if the fix is missing, incomplete, or you cannot \
tell. Return exactly one entry per violation, using the same index you were given."""


def _self_assess(violations, fixes) -> List[dict]:
    """The validation step used by B2-B4: ask an LLM 'did the fix work?'.
    No tool is run -- this is precisely the 'LLM grading its own homework'
    design that Securify's independent Checkov re-scan replaces."""
    fixed_by_addr = {f.resource: f.fixed_hcl for f in fixes}
    lines = []
    for i, v in enumerate(violations):
        lines += [f"Violation #{i}", f"Resource: {v.resource}", f"Issue: {v.issue}"]
        if v.policy_reference:
            lines.append(f"Policy requirement: {v.policy_reference}")
        hcl = fixed_by_addr.get(v.resource)
        if hcl:
            lines += ["Corrected HCL for this resource:", hcl]
        else:
            lines.append("No corrected HCL was produced for this resource.")
        lines.append("")

    out = call_structured(
        system_prompt=SELF_ASSESS_SYSTEM_PROMPT,
        user_prompt="\n".join(lines),
        response_model=SelfAssessOutput,
        agent="self_assessment",
    )
    by_index = {f.index: f.resolved for f in out.findings}
    return [
        {
            "resource": v.resource,
            "issue": v.issue,
            "claimed_resolved": bool(by_index.get(i, False)),
            "answered": i in by_index,
        }
        for i, v in enumerate(violations)
    ]


def run_llm_single_pass(cfg: BaselineConfig, tmp_dir: str, trace: dict) -> dict:
    resources, raw_blocks = _prepare(tmp_dir)

    static_findings, parsing_errors = [], 0
    if cfg.uses_checkov:
        static_findings, parsing_errors = _checkov(tmp_dir, trace)

    # (RAG on/off was already set for this task by run_baselines via eval_env.rag_enabled)
    with _timed(trace, "analysis_s"):
        analyzer_output = analyze_resources(ORG_ID, resources, static_findings)
    violations = analyzer_output.violations
    detections = [_det_from_violation(v) for v in violations]

    remediation = None
    if violations:
        with stage("remediation"), _timed(trace, "remediation_s"):
            rem = remediate_violations(resources, violations)
        remediated_tf = build_remediated_file(raw_blocks, rem.fixes)

        with _timed(trace, "self_assessment_s"):
            claimed = _self_assess(violations, rem.fixes)

        remediation = {
            "method": "single_pass_llm_self_assessment",
            "remediated_tf": remediated_tf,
            "fixes": _fix_dicts(rem.fixes),
            "claimed_status": claimed,
            "attempts": [{
                "attempt": 1,
                "n_targets": len(violations),
                "n_resolved": sum(1 for c in claimed if c["claimed_resolved"]),
            }],
            "retry_count": 1,
            "all_resolved": all(c["claimed_resolved"] for c in claimed),
        }

    return {
        "detections": detections,
        "checkov_findings": static_findings,
        "checkov_parsing_errors": parsing_errors,
        "resource_count": len(resources),
        "remediation": remediation,
    }


# ---------------------------------------------------------------------------
# B5 -- Securify: the project's real pipeline
# ---------------------------------------------------------------------------

def run_securify(cfg: BaselineConfig, tmp_dir: str, trace: dict) -> dict:
    """Runs exactly what the Celery worker's run_scan_job runs: parse ->
    Checkov -> run_scan_pipeline (Analyzer -> Remediation <-> Validator loop).
    Only the database rows and the PDF report are skipped -- neither affects
    detection or remediation."""
    resources, raw_blocks = _prepare(tmp_dir)
    static_findings, parsing_errors = _checkov(tmp_dir, trace)

    t0 = time.perf_counter()
    result = run_scan_pipeline(
        org_id=ORG_ID,
        resources=resources,
        static_findings=static_findings,
        raw_blocks=raw_blocks,
        on_step=lambda s: trace["steps"].append({"step": s, "t": round(time.perf_counter() - t0, 3)}),
    )

    detections = [_det_from_violation(v) for v in result["violations"]]

    remediation = None
    if result["violations"]:
        claimed = [
            {"resource": f["resource"], "issue": f["issue"], "claimed_resolved": bool(f["resolved"])}
            for f in result["findings_status"]
        ]
        remediation = {
            "method": "controller_loop_checkov_rescan",
            "remediated_tf": result["remediated_tf"],
            "fixes": _fix_dicts(result["fixes"]),
            "claimed_status": claimed,
            "attempts": trace["attempts"],  # per-attempt targets + validator statuses (from eval_env hooks)
            "retry_count": result["retry_count"],
            "all_resolved": bool(result["all_resolved"]),
            "validator_summary": result["validator_summary"],
        }

    return {
        "detections": detections,
        "checkov_findings": static_findings,
        "checkov_parsing_errors": parsing_errors,
        "resource_count": len(resources),
        "remediation": remediation,
    }


RUNNERS = {
    "static_only": run_b1,
    "llm_single_pass": run_llm_single_pass,
    "securify_pipeline": run_securify,
}
