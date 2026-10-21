#!/usr/bin/env python3
"""
score_results.py -- Part 3. Turns raw baseline results (Part 2) + ground truth (Part 1)
into Tables II-VII. No API calls, no Checkov: re-run it as often as you like.

    python score_results.py --self-test            # validate the remediation oracle on the corpus (run this first)
    python score_results.py --run-name default     # score a run -> results/<run>/metrics.json, tables.md, tables/*.csv

Scoring rules (all deterministic, all written down in tables.md so they can go in your Methods):
  * Unit = resource. Positive = resource with a planted violation; negative = clean resource.
  * A detection MATCHES a planted issue if it is on that resource (an aws_s3_bucket_public_access_block
    named <bucket>_pab counts as its bucket) and its `issue` text contains one of the issue's match_keywords.
    Keywords shared with a sibling issue type (e.g. 0.0.0.0/0 for SSH vs RDP) and generic ones
    (iam/open/storage) are ignored so the right issue is matched. `policy_reference` is NOT used for matching
    (with a 1-chunk policy it contains every clause).
  * TP = planted issue matched; FN = not matched; FP = clean resource with any detection (+ detections on
    resources that do not exist); TN = clean resource with none.  "strict" counts ANY detection on a clean
    resource; "scoped" only counts detections that match some issue type of that resource family, so generic
    best-practice findings outside the planted taxonomy (e.g. S3 versioning) are not held against a baseline.
  * Remediation truth comes from an independent oracle (deterministic HCL checks per issue type) applied to the
    remediated file -- NOT from any baseline's own claim. A fix that deletes the resource or unbalances braces fails.
  * Only files that finished OK in ALL scored baselines are used, so every column covers the same files.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BL = ["B1", "B2", "B3", "B4", "B5"]
NAMES = {"B1": "B1: Checkov", "B2": "B2: LLM Only", "B3": "B3: Checkov + LLM",
         "B4": "B4: Checkov + RAG + LLM", "B5": "B5: Securify"}

# ----------------------------------------------------------------------------- HCL text helpers
def strip_comments(t: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", t)

def match_brace(text: str, open_idx: int) -> int:
    d = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{": d += 1
        elif text[i] == "}":
            d -= 1
            if d == 0: return i
    return len(text) - 1

def resource_blocks(text: str) -> dict:
    text = strip_comments(text)
    out = {}
    for m in re.finditer(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*{', text):
        out[f"{m.group(1)}.{m.group(2)}"] = text[m.start(): match_brace(text, m.end() - 1) + 1]
    return out

def nested(block: str, name: str) -> list:
    out = []
    for m in re.finditer(rf"\b{name}\s*{{", block):
        out.append(block[m.start(): match_brace(block, m.end() - 1) + 1])
    return out

def related(blocks: dict, rtype: str, bucket_addr: str) -> list:
    return [b for a, b in blocks.items() if a.startswith(rtype + ".") and bucket_addr in b]

def ports_open(block: str, port: int) -> bool:
    b = block
    for e in nested(block, "egress"): b = b.replace(e, "")
    for g in (nested(b, "ingress") or [b]):
        if "0.0.0.0/0" not in g and "::/0" not in g: continue
        proto = re.search(r'protocol\s*=\s*"([^"]+)"', g)
        fp, tp = re.search(r"from_port\s*=\s*(-?\d+)", g), re.search(r"to_port\s*=\s*(-?\d+)", g)
        if proto and proto.group(1) == "-1": return True
        if fp and tp and int(fp.group(1)) <= port <= int(tp.group(1)): return True
    return False

# ----------------------------------------------------------------------------- remediation oracle
# Each checker returns True when the resource is COMPLIANT for that issue (i.e. the issue is resolved).
def _kms(b): return "sse_algorithm" in b and "kms" in b.lower()
def c_s3_enc(b, addr, allb): return _kms(b) or any(_kms(x) for x in related(allb, "aws_s3_bucket_server_side_encryption_configuration", addr))
def c_s3_log(b, addr, allb): return bool(re.search(r"\blogging\s*{", b)) or bool(related(allb, "aws_s3_bucket_logging", addr))
def c_s3_pub(b, addr, allb):
    pabs = related(allb, "aws_s3_bucket_public_access_block", addr)
    keys = ("block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets")
    return any(all(re.search(rf"{k}\s*=\s*true", p) for k in keys) for p in pabs)
def c_s3_tag(b, addr, allb): return bool(re.search(r'CostCenter"?\s*[=:]\s*"[^"]+"', b))
def c_sg_ssh(b, addr, allb): return not ports_open(b, 22)
def c_sg_rdp(b, addr, allb): return not ports_open(b, 3389)
def c_sg_desc(b, addr, allb):
    m = re.search(r'description\s*=\s*"([^"]*)"', b)
    return bool(m and re.match(r"^[\w-]+: \S.*$", m.group(1)))
def c_iam_wild(b, addr, allb):
    a = re.search(r'["\']?Action["\']?\s*[:=]\s*\[?\s*"\*"', b)
    r = re.search(r'["\']?Resource["\']?\s*[:=]\s*\[?\s*"\*"', b)
    return not (a and r)
def c_iam_admin(b, addr, allb):
    m = re.search(r'\bname\s*=\s*"([^"]+)"', b)
    return not (m and m.group(1).startswith("admin-")) or bool(re.search(r'ApprovedBy"?\s*[:=]\s*"[^"]+"', b))
def c_rds_pub(b, addr, allb):
    return bool(re.search(r"storage_encrypted\s*=\s*true", b)) and not re.search(r"publicly_accessible\s*=\s*true", b)
def c_rds_region(b, addr, allb):
    m = re.search(r'availability_zone\s*=\s*"([^"]+)"', b)
    return (not m) or m.group(1).startswith(("us-east-1", "us-west-2"))

CHECKERS = {
    "s3_no_encryption": c_s3_enc, "s3_no_logging": c_s3_log, "s3_public_access": c_s3_pub,
    "s3_missing_costcenter_tag": c_s3_tag, "sg_open_ssh": c_sg_ssh, "sg_open_rdp": c_sg_rdp,
    "sg_bad_description": c_sg_desc, "iam_wildcard_action_resource": c_iam_wild,
    "iam_admin_role_unapproved": c_iam_admin, "rds_public_unencrypted": c_rds_pub,
    "rds_unapproved_region": c_rds_region,
}

def truly_resolved(remediated_tf, addr: str, issue_id: str) -> bool:
    if not remediated_tf: return False
    if remediated_tf.count("{") != remediated_tf.count("}"): return False  # broken HCL
    allb = resource_blocks(remediated_tf)
    if addr not in allb: return False  # deleting the resource is not a fix
    return CHECKERS[issue_id](allb[addr], addr, allb)

# ----------------------------------------------------------------------------- taxonomy + matching
STOP = {"iam", "open", "storage"}

def build_taxonomy(gt: dict):
    tax = {}
    for rs in gt.values():
        for r in rs:
            i = r["issue"]
            if i:
                tax[i["issue_id"]] = {"rtype": i["resource_type"], "kws": [k.lower() for k in i["match_keywords"]],
                                      "policy": i["policy_relevant"], "checkov": i["checkov_detectable"]}
    by_type = defaultdict(list)
    for iid, t in tax.items(): by_type[t["rtype"]].append(iid)
    for iid, t in tax.items():
        others = {k for o in by_type[t["rtype"]] if o != iid for k in tax[o]["kws"]}
        kws = [k for k in t["kws"] if k not in STOP] or t["kws"]
        t["match_kws"] = [k for k in kws if k not in others] or kws
    return tax, by_type

def kw_hit(text: str, kw: str) -> bool:
    return re.search(rf"(?<!\d){kw}(?!\d)", text) is not None if kw.isdigit() else kw in text

def matches(text: str, iid: str, tax: dict) -> bool:
    t = (text or "").lower()
    return any(kw_hit(t, k) for k in tax[iid]["match_kws"])

def canon(addr):
    if addr and addr.startswith("aws_s3_bucket_public_access_block.") and addr.endswith("_pab"):
        return "aws_s3_bucket." + addr.split(".", 1)[1][:-4]
    return addr

# ----------------------------------------------------------------------------- per-file scoring
def score_file(rec, gt_res, tax, by_type):
    dets = defaultdict(list)
    for i, d in enumerate(rec["detections"]): dets[canon(d["resource"])].append((i, d))
    known = {r["address"] for r in gt_res}
    phantom = sum(len(v) for a, v in dets.items() if a not in known)
    rows = []
    for r in gt_res:
        addr, issue = r["address"], r["issue"]
        rtype = addr.split(".")[0]
        ds = dets.get(addr, [])
        row = {"address": addr, "planted": issue["issue_id"] if issue else None, "n_dets": len(ds), "pairs": []}
        if issue:
            iid = issue["issue_id"]
            hit = [(i, d) for i, d in ds if matches(d["issue"], iid, tax)]
            row.update(detected=bool(hit), det=hit[0][1] if hit else None)
        else:
            row["flag_strict"] = bool(ds)
            row["flag_scoped"] = any(matches(d["issue"], t, tax) for _, d in ds for t in by_type[rtype])
        for t in by_type[rtype]:  # (resource, issue-type) pairs surfaced -- for Table VI
            if tax[t]["policy"] and any(matches(d["issue"], t, tax) for _, d in ds):
                row["pairs"].append((t, bool(issue and issue["issue_id"] == t)))
        rows.append(row)
    return rows, phantom

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)

def pct(x): return f"{100 * x:.2f}%"

def boot_ci(items, stat, n=1000, seed=7):
    rnd = random.Random(seed); vals = []
    for _ in range(n):
        vals.append(stat([items[rnd.randrange(len(items))] for _ in items]))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n)]

# ----------------------------------------------------------------------------- IO
def load_latest(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try: r = json.loads(line)
                except json.JSONDecodeError: continue
                out[r["file"]] = r
    return out

def md(header, rows):
    s = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    return s + "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows) + "\n"

# ----------------------------------------------------------------------------- self-test
def self_test(corpus: Path) -> int:
    gt = json.load(open(corpus / "ground_truth.json"))
    tax, by_type = build_taxonomy(gt)
    bad, n_pl, n_cl = [], 0, 0
    for fn, rs in gt.items():
        text = (corpus / fn).read_text(encoding="utf-8"); allb = resource_blocks(text)
        for r in rs:
            addr = r["address"]; rtype = addr.split(".")[0]
            if r["issue"]:
                n_pl += 1
                if truly_resolved(text, addr, r["issue"]["issue_id"]): bad.append((fn, addr, "planted issue judged RESOLVED"))
            else:
                n_cl += 1
                for iid in by_type[rtype]:
                    if iid == "s3_public_access": continue  # only meaningful when a public-access-block exists
                    if not CHECKERS[iid](allb[addr], addr, allb): bad.append((fn, addr, f"clean resource judged NON-compliant for {iid}"))
    print(f"Oracle self-test on {len(gt)} files: {n_pl} planted (must all be unresolved), {n_cl} clean (must all be compliant)")
    print("PASS" if not bad else f"FAIL: {len(bad)} disagreement(s)")
    for b in bad[:15]: print("  ", b)
    return 0 if not bad else 1

# ----------------------------------------------------------------------------- main scoring
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-name", default="default")
    ap.add_argument("--corpus", default=str(HERE / "corpus"))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--bootstrap", type=int, default=1000, help="resamples for 95%% CIs (0 = skip)")
    a = ap.parse_args()
    corpus = Path(a.corpus)
    if a.self_test: return self_test(corpus)

    run = HERE / "results" / a.run_name
    gt = json.load(open(corpus / "ground_truth.json"))
    tax, by_type = build_taxonomy(gt)
    cfg = json.load(open(run / "run_config.json")) if (run / "run_config.json").exists() else {}
    data = {b: load_latest(run / "raw" / f"{b}.jsonl") for b in BL}
    bls = [b for b in BL if data[b]]
    if not bls: print("No raw results found."); return 2
    ok = [{f for f, r in data[b].items() if r["status"] == "ok"} for b in bls]
    files = sorted(set.intersection(*ok) & set(gt))
    excluded = len(set(gt) & set().union(*[set(data[b]) for b in bls])) - len(files)
    print(f"Scoring {len(files)} files common to {bls} ({excluded} excluded: error/missing in some baseline)")
    if not files: return 2

    M, audit = {}, []
    for b in bls:
        c = dict(tp=0, fp_s=0, fp_c=0, tn_s=0, tn_c=0, fn=0, phantom=0, pos=0, neg=0)
        per_file = []; tgt = ok_fix = 0
        cl = dict(CR=0, HAL=0, CU=0, IU=0); att = defaultdict(int); iters = []
        pol = {"all": dict(pos=0, tp=0, fp=0), "custom": dict(pos=0, tp=0, fp=0)}
        lat, calls, tin, tout, cost = [], [], [], [], []
        for f in files:
            rec = data[b][f]; rows, ph = score_file(rec, gt[f], tax, by_type)
            fc = dict(tp=0, fp=ph, fn=0, tn=0, tgt=0, fixed=0)
            c["phantom"] += ph; c["fp_s"] += ph
            rem = rec.get("remediation")
            claimed = {(x["resource"], x["issue"]): x["claimed_resolved"] for x in (rem or {}).get("claimed_status", [])}
            attempts = (rem or {}).get("attempts", [])
            if rem: iters.append(rem.get("retry_count", 1))
            for r in rows:
                if r["planted"]:
                    c["pos"] += 1; iid = r["planted"]; t = tax[iid]
                    for key, ok_t in (("all", t["policy"]), ("custom", t["policy"] and not t["checkov"])):
                        if ok_t: pol[key]["pos"] += 1; pol[key]["tp"] += r["detected"]
                    if r["detected"]:
                        c["tp"] += 1; fc["tp"] += 1
                    else:
                        c["fn"] += 1; fc["fn"] += 1
                    audit_row = [b, f, r["address"], iid, r["detected"], "", "", "", ""]
                    if r["detected"] and rem and b != "B1":
                        d = r["det"]; truth = truly_resolved(rem["remediated_tf"], r["address"], iid)
                        cl_ = bool(claimed.get((d["resource"], d["issue"]), False))
                        tgt += 1; fc["tgt"] += 1; ok_fix += truth; fc["fixed"] += truth
                        cl["CR" if cl_ and truth else "HAL" if cl_ else "IU" if truth else "CU"] += 1
                        # Per-attempt truth, from the snapshot taken right after that attempt's
                        # validation step (falls back to "was it still a target" when no
                        # snapshot is present, e.g. results scored before this patch).
                        per_attempt_truth = []
                        for at in attempts:
                            snap = at.get("remediated_tf_snapshot")
                            if snap is not None:
                                per_attempt_truth.append(truly_resolved(snap, r["address"], iid))
                            else:
                                targeted = any(x["resource"] == d["resource"] and x["issue"] == d["issue"] for x in at.get("targets", []))
                                per_attempt_truth.append(None if targeted else True)  # None = "still being worked on"
                        for i_, v_ in enumerate(per_attempt_truth):
                            if v_ is False or v_ is None:
                                att[i_ + 1] += 1  # "still open" at this attempt -- only meaningful count now
                        regressed = any(
                            per_attempt_truth[i_] and per_attempt_truth[i_ + 1] is False
                            for i_ in range(len(per_attempt_truth) - 1)
                        )
                        if regressed: c["regressions"] = c.get("regressions", 0) + 1
                        audit_row[5:] = [cl_, truth, regressed, per_attempt_truth]
                    audit.append(audit_row)
                else:
                    c["neg"] += 1
                    c["fp_s"] += r["flag_strict"]; c["tn_s"] += not r["flag_strict"]
                    c["fp_c"] += r["flag_scoped"]; c["tn_c"] += not r["flag_scoped"]
                    fc["fp"] += r["flag_strict"]; fc["tn"] += not r["flag_strict"]
                for t_, correct in r["pairs"]:
                    tt = tax[t_]
                    if not correct:
                        pol["all"]["fp"] += 1
                        if not tt["checkov"]: pol["custom"]["fp"] += 1
            per_file.append(fc)
            u = rec["llm_usage"]
            lat.append(rec["latency_s"]); calls.append(rec["llm_calls"])
            tin.append(sum(x["prompt_tokens"] for x in u)); tout.append(sum(x["completion_tokens"] for x in u))
            cost.append(sum(x["cost_usd"] for x in u))
        M[b] = dict(c=c, per_file=per_file, tgt=tgt, fixed=ok_fix, cl=cl, att=dict(att), iters=iters, pol=pol,
                    lat=lat, calls=calls, tin=tin, tout=tout, cost=cost)

    def f1_of(items):
        tp = sum(i["tp"] for i in items); fp = sum(i["fp"] for i in items); fn = sum(i["fn"] for i in items)
        return prf(tp, fp, fn)[2]
    def rate_of(items):
        t = sum(i["tgt"] for i in items); return sum(i["fixed"] for i in items) / t if t else 0.0

    T = {}; hdr = ["Metric"] + [NAMES[b] for b in bls]
    for mode, fpk, tnk in (("strict", "fp_s", "tn_s"), ("scoped", "fp_c", "tn_c")):
        rows = {k: [] for k in ("True Positives (TP)", "False Positives (FP)", "False Negatives (FN)", "True Negatives (TN)",
                                "Precision", "Recall", "F1-Score", "False-Positive Rate")}
        for b in bls:
            c = M[b]["c"]; tp, fp, fn, tn = c["tp"], c[fpk], c["fn"], c[tnk]
            p, r, f1 = prf(tp, fp, fn)
            for k, v in zip(rows, (tp, fp, fn, tn, pct(p), pct(r), pct(f1), pct(fp / (fp + tn) if fp + tn else 0))): rows[k].append(v)
        T[f"II_{mode}"] = (hdr, [[k] + v for k, v in rows.items()])
    if a.bootstrap:
        ci = []
        for b in bls:
            lo, hi = boot_ci(M[b]["per_file"], f1_of, a.bootstrap); ci.append(f"[{pct(lo)}, {pct(hi)}]")
        T["II_strict"][1].append(["F1 95% CI (bootstrap over files)"] + ci)

    hdr2 = ["Metric"] + [NAMES[b] for b in bls if b != "B1"]; llm = [b for b in bls if b != "B1"]
    r3 = [["Target Violations (planted issues detected)"] + [M[b]["tgt"] for b in llm],
          ["Successfully Remediated (oracle-verified)"] + [M[b]["fixed"] for b in llm],
          ["Unresolved Violations"] + [M[b]["tgt"] - M[b]["fixed"] for b in llm],
          ["Remediation Success Rate"] + [pct(M[b]["fixed"] / M[b]["tgt"] if M[b]["tgt"] else 0) for b in llm]]
    if a.bootstrap:
        r3.append(["Success Rate 95% CI"] + ["[%s, %s]" % tuple(pct(x) for x in boot_ci([i for i in M[b]["per_file"] if i["tgt"]], rate_of, a.bootstrap)) for b in llm])
    T["III"] = (hdr2, r3)

    def agree(b):
        c = M[b]["cl"]; n = sum(c.values()); return pct((c["CR"] + c["CU"]) / n if n else 0)
    T["IV"] = (hdr2, [
        ["Validation Approach"] + ["Independent Checkov re-scan" if b == "B5" else "LLM self-assessment" for b in llm],
        ["Correctly Resolved (claimed resolved, truly resolved)"] + [M[b]["cl"]["CR"] for b in llm],
        ["Incorrectly Marked Resolved (false 'resolved' claims)"] + [M[b]["cl"]["HAL"] for b in llm],
        ["Correct Unresolved Identification"] + [M[b]["cl"]["CU"] for b in llm],
        ["Incorrect Unresolved Identification"] + [M[b]["cl"]["IU"] for b in llm],
        ["Validation Agreement"] + [agree(b) for b in llm]])

    T["V"] = (["Baseline", "Still Open After Attempt 1", "...After Attempt 2", "...After Attempt 3",
              "Unresolved After Limit (truth)", "Regressions (fixed, then broke again)", "Avg. Iterations / File"],
              [[NAMES[b]] + (["—"] * 6 if b == "B1" else
                             [M[b]["att"].get(k, 0) for k in (1, 2, 3)] + [M[b]["tgt"] - M[b]["fixed"],
                              M[b]["c"].get("regressions", 0),
                              f"{statistics.mean(M[b]['iters']):.2f}" if M[b]["iters"] else "—"]) for b in bls])

    for key, title in (("all", "all policy-relevant"), ("custom", "custom-only (invisible to Checkov)")):
        rows = [[f"Policy Violations in Corpus ({title})"] + [M[b]["pol"][key]["pos"] for b in bls],
                ["Total Detections Surfaced"] + [M[b]["pol"][key]["tp"] + M[b]["pol"][key]["fp"] for b in bls],
                ["Correct Detections (TP)"] + [M[b]["pol"][key]["tp"] for b in bls],
                ["False Detections (FP)"] + [M[b]["pol"][key]["fp"] for b in bls],
                ["Policy Detection Recall"] + [pct(M[b]["pol"][key]["tp"] / M[b]["pol"][key]["pos"] if M[b]["pol"][key]["pos"] else 0) for b in bls],
                ["Policy Detection Precision"] + [pct(M[b]["pol"][key]["tp"] / (M[b]["pol"][key]["tp"] + M[b]["pol"][key]["fp"]) if M[b]["pol"][key]["tp"] + M[b]["pol"][key]["fp"] else 0) for b in bls]]
        T[f"VI_{key}"] = (hdr, rows)

    mean = statistics.mean
    T["VII"] = (hdr, [
        ["Mean Latency / File"] + [f"{mean(M[b]['lat']):.2f} s" for b in bls],
        ["Median Latency / File"] + [f"{statistics.median(M[b]['lat']):.2f} s" for b in bls],
        ["Avg. LLM Calls / File"] + [f"{mean(M[b]['calls']):.2f}" for b in bls],
        ["Avg. Input Tokens / File"] + [f"{mean(M[b]['tin']):,.0f}" for b in bls],
        ["Avg. Output Tokens / File"] + [f"{mean(M[b]['tout']):,.0f}" for b in bls],
        ["Avg. Total Tokens / File"] + [f"{mean(M[b]['tin']) + mean(M[b]['tout']):,.0f}" for b in bls],
        ["Estimated Cost / File"] + [f"${mean(M[b]['cost']):.4f}" for b in bls]])

    titles = {"II_strict": "TABLE II-a. Detection performance (STRICT: any finding on a clean resource is a false positive)",
              "II_scoped": "TABLE II-b. Detection performance (SCOPED: only findings inside the planted issue taxonomy count as false positives)",
              "III": "TABLE III. Remediation success (oracle-verified, over planted issues each baseline detected)",
              "IV": "TABLE IV. Validation mechanism reliability (claimed status vs oracle truth)",
              "V": "TABLE V. Remediation iteration dynamics (planted issues targeted per attempt)",
              "VI_all": "TABLE VI-a. Custom-policy enforcement (all policy-relevant issues)",
              "VI_custom": "TABLE VI-b. Custom-policy enforcement (clauses Checkov cannot know: CostCenter tag, SG description format, admin- role approval, approved regions)",
              "VII": "TABLE VII. Computational and economic resource utilization"}
    note = (f"Run `{a.run_name}` | model {cfg.get('chat_model')} | {len(files)} files scored ({sum(M[bls[0]]['c'][k] for k in ('pos','neg'))} resources: "
            f"{M[bls[0]]['c']['pos']} planted, {M[bls[0]]['c']['neg']} clean) | policy chunks {(cfg.get('policy') or {}).get('n_chunks')} | "
            f"workers {(cfg.get('last_invocation') or {}).get('workers')} (latency includes concurrency effects)\n\n"
            "Scoring rules: see the docstring of score_results.py. Phantom detections (on resources that do not exist) counted as FP: "
            + ", ".join(f"{b}={M[b]['c']['phantom']}" for b in bls) + "\n")
    (run / "tables").mkdir(exist_ok=True)
    with (run / "tables.md").open("w", encoding="utf-8") as fh:
        fh.write(f"# Securify evaluation results\n\n{note}\n")
        for k, (h, rows) in T.items():
            fh.write(f"## {titles[k]}\n\n{md(h, rows)}\n")
            with (run / "tables" / f"table_{k}.csv").open("w", newline="", encoding="utf-8") as cf:
                w = csv.writer(cf); w.writerow(h); w.writerows(rows)
    with (run / "per_resource_audit.csv").open("w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf); w.writerow(["baseline", "file", "resource", "planted_issue", "detected",
                                        "claimed_resolved", "truly_resolved", "regressed", "per_attempt_truth"])
        w.writerows(audit)

    policy_rows = []
    for b in bls:
        for f in files:
            rec = data[b][f]; rows, _ = score_file(rec, gt[f], tax, by_type)
            dets = defaultdict(list)
            for d in rec["detections"]: dets[canon(d["resource"])].append(d)
            for r in rows:
                rtype = r["address"].split(".")[0]
                for t_ in by_type[rtype]:
                    if not tax[t_]["policy"]: continue
                    for d in dets.get(r["address"], []):
                        if matches(d["issue"], t_, tax):
                            correct = bool(r["planted"] == t_)
                            policy_rows.append([b, f, r["address"], t_, correct, d["issue"], d.get("policy_reference")])
    with (run / "policy_detection_audit.csv").open("w", newline="", encoding="utf-8") as cf:
        w = csv.writer(cf)
        w.writerow(["baseline", "file", "resource", "matched_issue_type", "correct(TP)", "raw_detection_text", "policy_reference_cited"])
        w.writerows(policy_rows)
    json.dump({"files_scored": len(files), "tables": {k: {"header": h, "rows": r} for k, (h, r) in T.items()},
               "counts": {b: M[b]["c"] for b in bls}}, open(run / "metrics.json", "w", encoding="utf-8"), indent=2)
    print(f"Wrote {run/'tables.md'}, metrics.json, tables/*.csv, per_resource_audit.csv")
    print(open(run / "tables.md", encoding="utf-8").read())
    return 0

if __name__ == "__main__":
    sys.exit(main())
