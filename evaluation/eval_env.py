"""
eval_env.py -- lets the evaluation harness drive the REAL Securify backend
code without modifying a single file under backend/.

What this module does (all at runtime, in-process, nothing on disk in backend/):

  1. Finds the backend folder and puts it on sys.path, so `import app...` works
     whether you run from the Docker backend container (/app) or a local venv.
  2. Loads your .env (for OPENAI_API_KEY) and points DATABASE_URL at a throwaway
     in-memory SQLite, so the harness physically cannot write to your real DB.
  3. Installs a handful of small monkey-patches (see install_patches):
       - capture token usage per LLM call  (backend normally writes it to Postgres)
       - redirect the FAISS index to evaluation/.eval_store  (backend hardcodes /app/storage)
       - a per-run switch that turns RAG retrieval on/off  (used for the B2/B3 ablations)
       - trace hooks around the controller's remediate/validate steps  (per-attempt data for Table V)
  4. Ingests the custom policy document into an isolated eval-only FAISS index,
     using the same extract -> chunk -> embed -> add_chunks functions the
     /policy/upload endpoint uses.

Patches only OBSERVE or SWITCH; none of them changes what the agents' prompts,
schemas, models, or logic do.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ORG_ID = "eval-org"  # isolated tenant id used only by the evaluation's FAISS index

# Per-task context. ContextVars (not globals) so several files can be
# processed concurrently in worker threads without their data mixing.
usage_sink: contextvars.ContextVar = contextvars.ContextVar("eval_usage_sink", default=None)
trace_sink: contextvars.ContextVar = contextvars.ContextVar("eval_trace_sink", default=None)
stage_var: contextvars.ContextVar = contextvars.ContextVar("eval_stage", default="unknown")
rag_enabled: contextvars.ContextVar = contextvars.ContextVar("eval_rag_enabled", default=True)


@contextmanager
def stage(name: str):
    """Labels LLM calls made inside the block (used for calls the backend
    itself makes without an agent label, e.g. the remediation agent)."""
    tok = stage_var.set(name)
    try:
        yield
    finally:
        stage_var.reset(tok)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def find_backend() -> Path:
    override = os.environ.get("SECURIFY_BACKEND")
    candidates = [Path(override)] if override else []
    candidates += [EVAL_DIR.parent / "backend", Path("/app")]
    for c in candidates:
        if (c / "app" / "services" / "ai_analyzer.py").exists():
            return c
    raise RuntimeError(
        "Could not find the Securify backend. Expected ../backend next to the "
        "evaluation folder (or /app inside the backend container). You can also "
        "set SECURIFY_BACKEND=<path to backend folder>."
    )


def bootstrap(require_openai_key: bool = True) -> Path:
    backend = find_backend()
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    try:
        from dotenv import load_dotenv
        for p in (EVAL_DIR / ".env", backend.parent / ".env", backend / ".env"):
            if p.exists():
                load_dotenv(p, override=False)  # never overrides real env vars
    except ImportError:
        pass  # python-dotenv is in requirements.txt; if absent, rely on real env vars

    # Safety belt: nothing in the evaluation path should touch Postgres.
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    if require_openai_key and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Put it in your project .env (the same one "
            "docker-compose uses) or export it in this shell."
        )
    return backend


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

_patched = False


def install_patches(store_dir: Path) -> None:
    global _patched
    if _patched:
        return

    from app.services import ai_analyzer, controller_agent, llm_client, vector_store

    # 1) FAISS index location -- backend hardcodes /app/storage/faiss.
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    vector_store.STORAGE_DIR = str(store_dir)

    # 2) Token/cost capture. llm_client.call_structured calls _record_usage()
    #    after every LLM call and (in production) writes a Postgres row. We
    #    swap it for a function that appends to the current task's usage list,
    #    reusing the backend's own _cost_usd pricing.
    def _capture_usage(agent, model, usage):
        sink = usage_sink.get()
        if sink is None:
            return
        label = stage_var.get() if agent == "unknown" else agent
        sink.append({
            "agent": label,
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": llm_client._cost_usd(model, usage.prompt_tokens, usage.completion_tokens),
        })

    llm_client._record_usage = _capture_usage

    # 3) RAG on/off switch. The Analyzer calls retrieve_relevant_policy() once
    #    per resource. With the switch off it gets [] back, which the Analyzer's
    #    own code renders as "none retrieved" -- i.e. exactly what "no RAG" means.
    original_retrieve = ai_analyzer.retrieve_relevant_policy

    def _retrieve(org_id, query_text, top_k=5):
        if not rag_enabled.get():
            return []
        chunks = original_retrieve(org_id, query_text, top_k=top_k)
        trace = trace_sink.get()
        if trace is not None:
            trace.setdefault("retrieval", []).append({
                "n_chunks": len(chunks),
                "scores": [round(c.get("score", 0.0), 4) for c in chunks],
            })
        return chunks

    ai_analyzer.retrieve_relevant_policy = _retrieve

    # 4) Trace hooks on the controller loop (used only for B5). Each wrapper
    #    calls the original function unchanged and records what happened.
    orig_analyze = controller_agent.analyze_resources
    orig_remediate = controller_agent.remediate_violations
    orig_validate = controller_agent.validate_remediation

    def _analyze(org_id, resources, static_findings):
        t = time.perf_counter()
        try:
            return orig_analyze(org_id, resources, static_findings)
        finally:
            trace = trace_sink.get()
            if trace is not None:
                trace["analysis_s"] = trace.get("analysis_s", 0.0) + time.perf_counter() - t

    def _remediate(resources, violations):
        trace = trace_sink.get()
        entry = {
            "attempt": (len(trace["attempts"]) + 1) if trace is not None else 0,
            "n_targets": len(violations),
            "targets": [{"resource": v.resource, "issue": v.issue} for v in violations],
        }
        t = time.perf_counter()
        with stage("remediation"):
            try:
                return orig_remediate(resources, violations)
            finally:
                entry["remediation_s"] = round(time.perf_counter() - t, 4)
                if trace is not None:
                    trace["attempts"].append(entry)

    def _validate(tf_dir, original_violations):
        t = time.perf_counter()
        out = orig_validate(tf_dir, original_violations)
        trace = trace_sink.get()
        if trace is not None and trace["attempts"]:
            a = trace["attempts"][-1]
            a["validation_s"] = round(time.perf_counter() - t, 4)
            a["statuses"] = [
                {"resource": f.resource, "issue": f.issue, "claimed_resolved": bool(f.resolved)}
                for f in out.findings
            ]
            a["n_resolved"] = sum(1 for f in out.findings if f.resolved)
            a["all_resolved"] = bool(out.all_resolved)
            a["validator_summary"] = out.summary
            # Snapshot the actual remediated HCL AS IT STOOD after this
            # attempt (tf_dir still holds it; run_scan_pipeline deletes it
            # right after this call returns). Lets Part 3 independently
            # verify, per attempt, whether a SPECIFIC ground-truth violation
            # was really fixed at that point -- not just at the final file --
            # which is what you need to tell "fixed early, correctly dropped
            # from later retries" apart from "fixed, then regressed when a
            # later attempt rewrote the same resource for a different issue".
            try:
                main_tf = Path(tf_dir) / "main.tf"
                a["remediated_tf_snapshot"] = main_tf.read_text(encoding="utf-8")
            except OSError:
                a["remediated_tf_snapshot"] = None
        return out

    controller_agent.analyze_resources = _analyze
    controller_agent.remediate_violations = _remediate
    controller_agent.validate_remediation = _validate

    # 5) Harden the OpenAI clients for a long batch run: generous timeout and
    #    more automatic retries on 429 / 5xx. (Model, prompts and parameters
    #    are untouched.)
    from app.services import embeddings
    for mod in (llm_client, embeddings):
        try:
            mod._client = mod._client.with_options(timeout=120.0, max_retries=6)
        except Exception:
            pass

    _patched = True


# ---------------------------------------------------------------------------
# Policy ingestion (RAG index for the evaluation)
# ---------------------------------------------------------------------------

def ensure_policy_indexed(policy_path: Path, store_dir: Path) -> dict:
    """Builds the eval-only FAISS index from the custom policy document, the
    same way POST /policy/upload does (extract_text -> chunk_text -> embed_texts
    -> add_chunks). Skips the (paid) embedding call if the index already
    matches this exact file."""
    policy_path = Path(policy_path)
    store_dir = Path(store_dir)
    raw = policy_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()

    marker = store_dir / "policy.sha256"
    meta_file = store_dir / f"{ORG_ID}_meta.json"
    if marker.exists() and meta_file.exists() and marker.read_text().strip() == sha:
        n_chunks = len(json.loads(meta_file.read_text()))
        n_words = len(policy_path.read_text(encoding="utf-8", errors="ignore").split())
        return {"policy_file": policy_path.name, "sha256": sha, "n_chunks": n_chunks,
                "n_words": n_words, "reused_existing_index": True}

    from app.services.embeddings import embed_texts
    from app.services.policy_ingest import chunk_text, extract_text
    from app.services.vector_store import add_chunks

    shutil.rmtree(store_dir, ignore_errors=True)
    store_dir.mkdir(parents=True, exist_ok=True)

    text = extract_text(str(policy_path))
    chunks = chunk_text(text)
    if not chunks:
        raise RuntimeError(f"No extractable text in policy file {policy_path}")
    vectors = embed_texts(chunks)
    add_chunks(ORG_ID, chunks, vectors, policy_id="eval-policy",
               filename=policy_path.name, version=1)
    marker.write_text(sha)
    return {"policy_file": policy_path.name, "sha256": sha, "n_chunks": len(chunks),
            "n_words": len(text.split()), "reused_existing_index": False}
