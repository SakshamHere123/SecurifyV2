#!/usr/bin/env python3
"""
orchestrate.py -- Part 4. One command that runs Part 2 (baselines) then Part 3
(scoring), with sanity checks before spending any API money. Parts 2 and 3
still work standalone; this just chains them and stops at the first failure.

    python orchestrate.py --check                 # sanity checks only, no run
    python orchestrate.py --limit 5                # smoke test: baselines + scoring
    python orchestrate.py                          # full run: all baselines, all files, then scoring
    python orchestrate.py --run-name final --baselines B1,B2,B3,B4,B5

Any flag not recognized here (e.g. --workers, --max-cost, --start) is passed
straight through to run_baselines.py. Scoring (score_results.py) always runs
with default settings after; run it again by hand for different --bootstrap etc.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(corpus: Path, policy: Path, need_llm: bool) -> list[str]:
    problems = []
    if not (corpus / "ground_truth.json").exists():
        problems.append(f"no ground_truth.json in {corpus} (run generate_corpus.py first)")
    n_tf = len(list(corpus.glob("file_*.tf")))
    if n_tf == 0:
        problems.append(f"no file_*.tf in {corpus}")
    if not policy.exists():
        problems.append(f"policy file not found: {policy}")
    try:
        sys.path.insert(0, str(HERE))
        import eval_env
        backend = eval_env.find_backend()
        print(f"  backend found: {backend}")
    except Exception as e:
        problems.append(f"backend not found: {e}")
    if need_llm:
        import os
        if not os.environ.get("OPENAI_API_KEY"):
            for p in (HERE / ".env", HERE.parent / ".env"):
                if p.exists() and "OPENAI_API_KEY" in p.read_text():
                    break
            else:
                problems.append("OPENAI_API_KEY not set and not found in a .env file")
    if shutil.which("checkov") is None:
        problems.append("checkov not on PATH (should be present in the backend Docker image)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(HERE / "corpus"))
    ap.add_argument("--policy", default=str(HERE / "custom_policy.md"))
    ap.add_argument("--baselines", default="B1,B2,B3,B4,B5")
    ap.add_argument("--run-name", default="default")
    ap.add_argument("--check", action="store_true", help="run sanity checks and exit, no API calls")
    ap.add_argument("--skip-run", action="store_true", help="only re-score an existing run (skip Part 2 entirely)")
    args, passthrough = ap.parse_known_args()

    corpus, policy = Path(args.corpus), Path(args.policy)
    baseline_ids = [b.strip().upper() for b in args.baselines.split(",") if b.strip()]
    need_llm = any(b != "B1" for b in baseline_ids)

    print("=== Sanity checks ===")
    problems = check(corpus, policy, need_llm)
    if problems:
        print("FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 2
    print("  OK\n")
    if args.check:
        return 0

    if not args.skip_run:
        print(f"=== Part 2: running baselines {baseline_ids} (run-name={args.run_name}) ===")
        cmd = [sys.executable, str(HERE / "run_baselines.py"),
               "--corpus", str(corpus), "--policy", str(policy),
               "--baselines", args.baselines, "--run-name", args.run_name, *passthrough]
        print("  $", " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"run_baselines.py exited {rc} -- stopping before scoring. Re-run this same command to resume.")
            return rc
    else:
        print("=== Part 2 skipped (--skip-run) ===")

    print(f"\n=== Part 3: scoring run '{args.run_name}' ===")
    rc = subprocess.call([sys.executable, str(HERE / "score_results.py"),
                          "--run-name", args.run_name, "--corpus", str(corpus)])
    if rc != 0:
        return rc

    run_dir = HERE / "results" / args.run_name
    print(f"\nDone. Results in {run_dir}")
    print(f"  -> {run_dir / 'tables.md'}")
    print(f"  -> {run_dir / 'metrics.json'}  (send this file back to build a formatted Word doc)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
