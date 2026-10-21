# Part 3 -- scoring (Tables II-VII)

    python score_results.py --self-test        # once: proves the remediation oracle is right (446 planted -> unresolved, 353 clean -> compliant)
    python score_results.py --run-name default # after run_baselines.py finished

Docker (no extra deps, but plain `python` works too since this script only needs the standard library):

    docker compose run --rm --no-deps -v "%cd%\evaluation:/evaluation" -w /evaluation backend python score_results.py --run-name default

Writes to results/<run>/: tables.md (all tables + scoring rules), tables/*.csv, metrics.json,
per_resource_audit.csv (every planted issue: detected? claimed resolved? truly resolved?).
No API calls; re-run freely. Only files that finished OK in every baseline are scored.
