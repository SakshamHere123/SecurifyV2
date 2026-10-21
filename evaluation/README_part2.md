# Securify evaluation -- Part 2: baseline runners (B1-B5)

Nothing under `backend/` is modified. These files run the project's real
functions and save RAW results; scoring against the ground truth is Part 3.

| file | role |
|---|---|
| `eval_env.py` | finds the backend, isolates DB/FAISS, installs observe-only patches (token capture, RAG on/off switch, controller trace hooks), indexes `custom_policy.md` |
| `baselines.py` | the five pipelines (B1 Checkov, B2 LLM only, B3 Checkov+LLM, B4 Checkov+RAG+LLM, B5 Securify) |
| `run_baselines.py` | CLI: runs baselines x corpus, parallel, resumable, writes `results/<run-name>/` |

## Run it (Docker -- same environment as your app; needs no db/redis)

From the project root (`D:\Projects\Securify\securify`):

    cmd:         docker compose run --rm --no-deps -v "%cd%\evaluation:/evaluation" -w /evaluation backend python run_baselines.py --limit 5
    PowerShell:  docker compose run --rm --no-deps -v "${PWD}\evaluation:/evaluation" -w /evaluation backend python run_baselines.py --limit 5

Do the `--limit 5` smoke test first (a few cents). Then drop `--limit` for the full run.
Re-running the same command resumes; use a new `--run-name` for a fresh run.

Useful flags: `--baselines B1` (free, no API key) | `--workers 1` (cleanest latency) |
`--max-cost 10` | `--start 100 --limit 50` | `--run-name final`

## Output (`evaluation/results/<run-name>/`)

* `run_config.json` -- model, embedding model, policy sha256 + chunk count, Checkov/OpenAI SDK versions, controller retry limit (put these in Methods)
* `raw/B1.jsonl` ... `raw/B5.jsonl` -- one JSON line per file:
  `detections[]` (resource, issue, severity, policy_reference, static_tool_confirmed, source),
  `checkov_findings[]`, `remediation` (remediated_tf, fixes, claimed_status, per-attempt trace),
  `latency_s`, `stage_timings_s`, `llm_usage[]` (per call: agent, tokens, cost), `retrieval[]`, `status`/`error`
* `run_summary.json` -- success counts, latency, tokens, cost (operational only)

If a file appears twice in a jsonl (an error re-run), the LAST line wins.

## Things to know before quoting numbers

* Runners never see `ground_truth.json`.
* B2 uses the unchanged Analyzer prompt, so it sees "Static tool findings: none" rather than "not run".
* B2-B4 remediate once and ask an LLM "did it work?" (`self_assessment` calls). B5 uses the project's controller loop with the independent Checkov re-scan. "Claimed" resolved != truly resolved; Part 3 checks the remediated files independently.
* `custom_policy.md` is ~140 words = 1 chunk, so RAG returns the whole policy for every resource.
* With `--workers > 1`, latency includes some contention. Use `--workers 1` on a subset for clean latency figures.
* `llm_usage` is what the backend's own `_cost_usd` prices (gpt-4o-mini rates in `llm_client.py`); embedding cost (a few tokens per resource) is not counted.
