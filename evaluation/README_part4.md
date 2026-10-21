# Part 4 -- orchestration (run everything with one command)

    python orchestrate.py --check                   # sanity checks only, no API calls, no money spent
    python orchestrate.py --limit 5                  # smoke test: baselines -> scoring
    python orchestrate.py --run-name final           # full run: all 5 baselines, all 400 files, then scoring

Docker, from the project root:

    docker compose run --rm --no-deps -v "%cd%\evaluation:/evaluation" -w /evaluation backend python orchestrate.py --check
    docker compose run --rm --no-deps -v "%cd%\evaluation:/evaluation" -w /evaluation backend python orchestrate.py --run-name final

`--check` verifies: ground_truth.json + .tf files exist, the backend is found, OPENAI_API_KEY is set
(when any baseline besides B1 is requested), and `checkov` is on PATH -- all before spending anything.
Any flag it doesn't recognize (`--workers`, `--max-cost`, `--start`, `--baselines`, ...) is passed
straight through to run_baselines.py, so `orchestrate.py --run-name final --workers 2 --max-cost 15`
works. `--skip-run` re-scores an existing run without touching the API. Parts 2 and 3 still work
standalone (run_baselines.py / score_results.py) if you want more control over either step.

## Full workflow, start to finish

1. `python generate_corpus.py` (Part 1) -- already done; produced `corpus/` + `ground_truth.json`. Re-run with `--seed` to regenerate a different corpus of the same size.
2. Upload `custom_policy.md` via the Admin panel so the real RAG index has it (only needed once).
3. `python orchestrate.py --check`
4. `python orchestrate.py --limit 5` -- look at `results/default/tables.md`, confirm it's sane.
5. `python orchestrate.py --run-name final` -- the real run. Resumable; re-run the same command if it stops partway (network error, rate limit, Ctrl-C).
6. Send me `results/final/metrics.json` (and `tables.md` if you want me to sanity-check numbers) -- I'll turn it into a formatted Word document matching the table layout you were shown originally, with real numbers and the scoring-rules footnotes.

## What's true about this evaluation, for your Methods section

* Corpus: 400 procedurally generated Terraform files, planted violations from a fixed injector library, ground truth correct by construction and cross-checked against a real Checkov run (0 misses on the 254 Checkov-detectable labels).
* Baselines B1-B5 call the project's own, unmodified functions (`analyze_resources`, `remediate_violations`, `run_scan_pipeline`, `run_checkov`); only routing/observation is added, never new logic.
* Detection scoring matches by resource + issue-keyword, not by `policy_reference` (the policy is short enough to be one retrieval chunk, so it would match everything).
* Remediation success is judged by an independent, deterministic oracle re-reading the fixed HCL -- not by any baseline's own "resolved" claim. Table IV exists precisely to show how often B2-B4's self-reported claim disagrees with that oracle.
* Two versions of the false-positive-sensitive tables (II, VI) are produced: strict and scoped. Report which one and why (see README_part3.md).
