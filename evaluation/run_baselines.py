#!/usr/bin/env python3
"""
run_baselines.py -- runs baselines B1-B5 over the generated corpus and saves
RAW results (one JSON record per baseline x file). Scoring against the ground
truth is a separate step (Part 3), so you can re-score without re-spending
API money.

Typical usage (see README_part2.md for the Docker command):

    python run_baselines.py --limit 5                 # cheap smoke test first
    python run_baselines.py                           # full run, all 5 baselines, all files
    python run_baselines.py --baselines B1            # Checkov only (free, no API key)
    python run_baselines.py --baselines B4,B5 --run-name default   # add/repair baselines later

Re-running the same command RESUMES: files already recorded as "ok" are skipped.
Use a different --run-name for a fresh, separate run.

Output:  evaluation/results/<run-name>/
    run_config.json          model, policy hash, Checkov version, settings (for the paper's Methods section)
    raw/B1.jsonl ... B5.jsonl  one record per file: detections, remediation artifacts, tokens, latency
    run_summary.json         operational summary (success counts, latency, tokens, cost) -- NOT accuracy metrics
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import eval_env  # noqa: E402  (must come before anything that imports `app`)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_latest(path: Path) -> dict:
    """file -> most recent record. Later lines win, so a re-run of a failed
    file supersedes its earlier error line; a half-written last line from a
    crash is ignored."""
    latest = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                latest[rec["file"]] = rec
    return latest


def _tool_version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().splitlines()[-1]
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(HERE / "corpus"))
    ap.add_argument("--policy", default=str(HERE / "custom_policy.md"))
    ap.add_argument("--baselines", default="B1,B2,B3,B4,B5", help="comma-separated subset of B1..B5")
    ap.add_argument("--start", type=int, default=0, help="skip the first N files of the corpus")
    ap.add_argument("--limit", type=int, default=None, help="only run N files (after --start)")
    ap.add_argument("--workers", type=int, default=3,
                    help="parallel tasks. Lower to 1-2 if you hit OpenAI 429s; use 1 for cleanest latency numbers")
    ap.add_argument("--run-name", default="default")
    ap.add_argument("--max-attempts", type=int, default=2,
                    help="tries per baseline x file before recording an error (transient API/parse failures)")
    ap.add_argument("--max-cost", type=float, default=25.0,
                    help="stop launching new tasks once estimated LLM spend in THIS invocation passes this many USD")
    ap.add_argument("--force", action="store_true",
                    help="resume into an existing run even if model / policy file changed (mixes data; not recommended)")
    args = ap.parse_args()

    baseline_ids = [b.strip().upper() for b in args.baselines.split(",") if b.strip()]
    unknown = [b for b in baseline_ids if b not in {"B1", "B2", "B3", "B4", "B5"}]
    if unknown:
        ap.error(f"unknown baseline(s): {unknown}")
    need_llm = any(b != "B1" for b in baseline_ids)
    need_rag = any(b in ("B4", "B5") for b in baseline_ids)

    # ---- environment + real backend -------------------------------------
    try:
        backend = eval_env.bootstrap(require_openai_key=need_llm)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 2

    store_dir = HERE / ".eval_store" / "faiss"
    eval_env.install_patches(store_dir)
    import baselines  # noqa: E402  (imports the real app.* modules)
    from app.services import controller_agent, llm_client

    # ---- corpus ---------------------------------------------------------
    corpus_dir = Path(args.corpus)
    all_files = sorted(corpus_dir.glob("file_*.tf"))
    if not all_files:
        print(f"ERROR: no file_*.tf found in {corpus_dir}")
        return 2
    files = all_files[args.start:]
    if args.limit is not None:
        files = files[: args.limit]

    # ---- policy index (RAG) --------------------------------------------
    policy_info = None
    if need_rag:
        print("Indexing custom policy for RAG (one embedding call)...")
        policy_info = eval_env.ensure_policy_indexed(Path(args.policy), store_dir)
        print(f"  policy: {policy_info['policy_file']}  words={policy_info['n_words']}  chunks={policy_info['n_chunks']}"
              f"{'  (reused existing index)' if policy_info['reused_existing_index'] else ''}")
        if policy_info["n_chunks"] == 1:
            print("  NOTE: the whole policy fits in ONE chunk, so retrieval returns the entire policy for every "
                  "resource. B4/B5 vs B3 then measures 'having the policy in the prompt', not retrieval selectivity.")

    # ---- run directory + config ----------------------------------------
    run_dir = HERE / "results" / args.run_name
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "run_config.json"
    chat_model = llm_client.CHAT_MODEL
    if config_path.exists():
        prev = json.loads(config_path.read_text(encoding="utf-8"))
        changed = []
        if prev.get("chat_model") != chat_model:
            changed.append(f"chat_model {prev.get('chat_model')} -> {chat_model}")
        if policy_info and prev.get("policy") and prev["policy"].get("sha256") != policy_info["sha256"]:
            changed.append("policy file contents changed")
        if changed and not args.force:
            print(f"ERROR: run '{args.run_name}' was created with different settings ({'; '.join(changed)}).")
            print("       Use a new --run-name (recommended) or pass --force to mix them.")
            return 2
        prev.setdefault("resumed_utc", []).append(_utcnow())
        config = prev
    else:
        import openai
        config = {
            "created_utc": _utcnow(),
            "run_name": args.run_name,
            "corpus_dir": str(corpus_dir),
            "corpus_files_total": len(all_files),
            "chat_model": chat_model,
            "embedding_model": "text-embedding-3-small",
            "controller_max_retries": controller_agent.MAX_RETRIES,
            "retrieval_top_k": 3,   # hardcoded in ai_analyzer._build_resource_context
            "policy_chunking": {"chunk_size_words": 250, "overlap_words": 50},  # policy_ingest.chunk_text defaults
            "policy": policy_info,
            "checkov_version": _tool_version(["checkov", "--version"]),
            "openai_sdk_version": openai.__version__,
            "baseline_definitions": {
                b: {"name": c.name, "checkov_to_llm": c.uses_checkov, "rag": c.uses_rag, "mode": c.mode}
                for b, c in baselines.BASELINES.items()
            },
        }
    config["last_invocation"] = {"utc": _utcnow(), "baselines": baseline_ids, "workers": args.workers,
                                 "files_in_scope": len(files), "backend_path": str(backend)}
    config_path.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")

    # ---- what still needs doing ----------------------------------------
    latest = {b: load_latest(raw_dir / f"{b}.jsonl") for b in baseline_ids}
    tasks = [(b, f) for f in files for b in baseline_ids if latest[b].get(f.name, {}).get("status") != "ok"]
    print(f"Run '{args.run_name}': {len(files)} files x {len(baseline_ids)} baselines "
          f"-> {len(tasks)} task(s) to run ({len(files) * len(baseline_ids) - len(tasks)} already done)")
    if not tasks:
        print("Nothing to do.")
    lock = threading.Lock()
    state = {"done": 0, "ok": 0, "err": 0, "skipped": 0, "cost": 0.0}

    # ---- one baseline x file --------------------------------------------
    def execute(baseline_id: str, tf_path: Path) -> dict | None:
        cfg = baselines.BASELINES[baseline_id]
        runner = baselines.RUNNERS[cfg.mode]
        discarded, last_err = [], None

        for attempt in range(1, args.max_attempts + 1):
            with lock:
                if state["cost"] >= args.max_cost:
                    return None  # over budget: leave undone so a later run can finish it
            usage, trace = [], {"steps": [], "attempts": []}
            toks = [
                (eval_env.usage_sink, eval_env.usage_sink.set(usage)),
                (eval_env.trace_sink, eval_env.trace_sink.set(trace)),
                (eval_env.rag_enabled, eval_env.rag_enabled.set(cfg.uses_rag)),
                (eval_env.stage_var, eval_env.stage_var.set("unknown")),
            ]
            try:
                with tempfile.TemporaryDirectory(prefix="securify_eval_") as tmp:
                    shutil.copy(tf_path, tmp)
                    t0 = time.perf_counter()
                    body = runner(cfg, tmp, trace)
                    latency = time.perf_counter() - t0
                return {
                    "baseline": baseline_id,
                    "file": tf_path.name,
                    "status": "ok",
                    "error": None,
                    "n_attempts": attempt,
                    "latency_s": round(latency, 4),
                    "stage_timings_s": _stage_timings(trace),
                    "llm_calls": len(usage),
                    "llm_usage": usage,
                    "discarded_usage": discarded,   # spend from failed attempts (not in llm_usage)
                    "retrieval": trace.get("retrieval", []),
                    "pipeline_steps": trace["steps"],
                    "remediation_performed": body.get("remediation") is not None,
                    "finished_utc": _utcnow(),
                    **body,
                }
            except Exception as e:  # noqa: BLE001 -- we want every failure recorded, not a crash
                last_err = f"{type(e).__name__}: {str(e)[:500]}"
                discarded.extend(usage)
                if attempt < args.max_attempts:
                    time.sleep(3 * attempt)
            finally:
                for var, tok in reversed(toks):
                    var.reset(tok)

        return {
            "baseline": baseline_id, "file": tf_path.name, "status": "error", "error": last_err,
            "n_attempts": args.max_attempts, "llm_usage": [], "discarded_usage": discarded,
            "finished_utc": _utcnow(),
        }

    def _finish(rec: dict | None, baseline_id: str, tf_path: Path, total: int) -> None:
        with lock:
            if rec is None:
                state["skipped"] += 1
                return
            with (raw_dir / f"{baseline_id}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
            state["done"] += 1
            state["ok" if rec["status"] == "ok" else "err"] += 1
            cost = sum(u["cost_usd"] for u in rec.get("llm_usage", [])) + \
                   sum(u["cost_usd"] for u in rec.get("discarded_usage", []))
            state["cost"] += cost
            tag = f"{rec['latency_s']:.1f}s" if rec["status"] == "ok" else f"ERROR {rec['error'][:90]}"
            print(f"[{state['done']}/{total}] {baseline_id} {tf_path.name} {rec['status']:<5} {tag}  "
                  f"(run spend ~${state['cost']:.3f})", flush=True)

    # ---- execute --------------------------------------------------------
    t_start = time.perf_counter()
    if tasks:
        ex = ThreadPoolExecutor(max_workers=max(1, args.workers))
        futures = {ex.submit(execute, b, f): (b, f) for b, f in tasks}
        try:
            for fut in as_completed(futures):
                b, f = futures[fut]
                _finish(fut.result(), b, f, len(tasks))
        except KeyboardInterrupt:
            print("\nInterrupted -- finished tasks are saved. Re-run the same command to resume.")
            ex.shutdown(wait=False, cancel_futures=True)
            return 130
        ex.shutdown(wait=True)

    if state["skipped"]:
        print(f"\nStopped early: estimated spend passed --max-cost ({args.max_cost} USD). "
              f"{state['skipped']} task(s) not run; re-run (optionally with a higher --max-cost) to finish.")

    # ---- operational summary -------------------------------------------
    summary = build_summary(raw_dir, baseline_ids, [f.name for f in files], baselines.BASELINES)
    summary["invocation_wall_clock_s"] = round(time.perf_counter() - t_start, 1)
    (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print_summary(summary)
    print(f"\nRaw results: {raw_dir}")
    return 0


def _stage_timings(trace: dict) -> dict:
    t = {k: round(trace[k], 4) for k in ("checkov_s", "analysis_s", "remediation_s", "self_assessment_s") if k in trace}
    if trace.get("attempts"):  # B5: per-attempt timings recorded by the eval_env hooks
        t["remediation_s"] = round(sum(a.get("remediation_s", 0.0) for a in trace["attempts"]), 4)
        t["validation_s"] = round(sum(a.get("validation_s", 0.0) for a in trace["attempts"]), 4)
    return t


def build_summary(raw_dir: Path, baseline_ids: list[str], file_names: list[str], defs: dict) -> dict:
    out = {"generated_utc": _utcnow(), "note": "Operational summary only. Detection/remediation accuracy is computed in Part 3.",
           "baselines": {}}
    for b in baseline_ids:
        latest = load_latest(raw_dir / f"{b}.jsonl")
        recs = [latest[f] for f in file_names if f in latest]
        ok = [r for r in recs if r["status"] == "ok"]
        lat = [r["latency_s"] for r in ok]
        all_usage = [u for r in recs for u in r.get("llm_usage", [])]
        disc = [u for r in recs for u in r.get("discarded_usage", [])]
        out["baselines"][b] = {
            "name": defs[b].name,
            "files_in_scope": len(file_names),
            "ok": len(ok),
            "errors": sum(1 for r in recs if r["status"] == "error"),
            "not_run": len(file_names) - len(recs),
            "mean_latency_s": round(statistics.mean(lat), 3) if lat else None,
            "median_latency_s": round(statistics.median(lat), 3) if lat else None,
            "mean_llm_calls_per_file": round(statistics.mean(r["llm_calls"] for r in ok), 3) if ok else None,
            "mean_input_tokens_per_file": round(sum(u["prompt_tokens"] for u in all_usage) / len(ok), 1) if ok else None,
            "mean_output_tokens_per_file": round(sum(u["completion_tokens"] for u in all_usage) / len(ok), 1) if ok else None,
            "total_cost_usd": round(sum(u["cost_usd"] for u in all_usage), 5),
            "wasted_cost_failed_attempts_usd": round(sum(u["cost_usd"] for u in disc), 5),
        }
    return out


def print_summary(summary: dict) -> None:
    print("\n=== Operational summary (accuracy metrics come in Part 3) ===")
    print(f"{'':4}{'name':<22}{'ok':>5}{'err':>5}{'todo':>6}{'lat(s)':>9}{'calls':>7}{'cost($)':>10}")
    for b, s in summary["baselines"].items():
        lat = f"{s['mean_latency_s']:.1f}" if s["mean_latency_s"] is not None else "-"
        calls = f"{s['mean_llm_calls_per_file']:.1f}" if s["mean_llm_calls_per_file"] is not None else "-"
        print(f"{b:<4}{s['name']:<22}{s['ok']:>5}{s['errors']:>5}{s['not_run']:>6}{lat:>9}{calls:>7}{s['total_cost_usd']:>10.4f}")


if __name__ == "__main__":
    sys.exit(main())
