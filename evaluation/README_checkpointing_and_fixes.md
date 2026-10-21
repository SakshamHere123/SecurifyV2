# What changed, and how checkpointing works

## Fix 1 -- Table V "Attempt 2" empty
Not a bug: an already-fixed ground-truth violation correctly drops out of later
retry rounds (only still-open violations get retargeted), so it can legitimately
vanish from Attempt 2's count while unrelated hallucinated violations keep the
loop going to Attempt 3. The "2" reappearing at Attempt 3 in your run suggested a
possible regression: a later attempt rewrites a resource for a DIFFERENT
violation using fresh context (not a diff), which can undo an earlier fix on
that same resource.

`eval_env.py` now snapshots the actual remediated HCL after every attempt (it
was sitting right there in the validator's temp dir already). `score_results.py`
uses those snapshots to independently verify, per attempt, whether the matched
violation was really fixed at that point -- and Table V now reports "Regressions
(fixed, then broke again)" as a real count instead of a confusing blank column.

## Fix 2 -- Table VI-b all false positives
Very likely just the 5-file sample: it happened to contain zero custom-only
planted issues, so every custom-policy-shaped detection there was automatically
scored FP. `score_results.py` now also writes `policy_detection_audit.csv` --
one row per policy-relevant detection, with the raw detection text and whether
it was scored correct. After the full run, open that file, filter to
`correct(TP) = False`, and skim a few `raw_detection_text` values against the
matching `.tf` file -- that tells you in seconds whether it's real hallucination
or a keyword-matching gap in the scorer (send me a few rows either way and I'll
confirm).

Replace your existing `eval_env.py` and `score_results.py` with the ones in this
zip (same filenames, same location) before the full run.

## Checkpointing (already built in) + a safety wrapper

`run_baselines.py` already checkpoints at file-and-baseline granularity: every
completed `(baseline, file)` pair is appended as one line to
`results/<run-name>/raw/<baseline>.jsonl` immediately after it finishes. Nothing
is held in memory waiting for the whole run to end. If the process dies --
network drop, laptop sleeps, Ctrl+C, Docker hiccup -- re-running the **exact
same command** (same `--run-name`) skips every file-baseline pair already
marked "ok" and only redoes what's missing or errored. You never restart from
zero, and you never get double-charged for finished work.

New: `run_resilient.bat` automates the "just re-run it" part, so you don't have
to babysit the terminal. From the project root:

    run_resilient.bat final --workers 2

This calls `orchestrate.py --run-name final --workers 2` through Docker; if it
exits with an error, it waits 20s and calls it again (up to 10 times), and each
retry resumes rather than restarts. If it still fails after 10 tries, it stops
and tells you to re-run by hand once the underlying issue (network, API key,
Docker) is fixed -- it'll resume from the same point.

Two more built-in safety nets worth knowing about:
* `--max-cost` (default $25) stops launching *new* tasks once estimated spend
  in that invocation passes it -- it won't blow through your $4 by accident.
* A crash mid-file never corrupts anything: a `(baseline, file)` pair is only
  written once it fully finishes, so a half-done file is simply retried, not
  double-counted.
