import logging

from openai import OpenAI

from app.core.config import settings
from app.core.logging_config import current_scan_id
from app.db.session import SessionLocal
from app.db.models import LLMUsage

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# gpt-4o-mini: cheap enough to call per-resource, strong enough at structured
# reasoning over code + policy text. Swap to "gpt-4o" here later if accuracy
# on tricky cases needs it -- every agent goes through this one function,
# so upgrading the model later is a one-line change, not a rewrite.
CHAT_MODEL = "gpt-4o-mini"

# USD per 1M tokens, keyed by model -- so upgrading CHAT_MODEL later doesn't
# silently mis-price usage. An unrecognized model logs a warning and records
# $0 rather than guessing at a rate. Update these if OpenAI's pricing changes.
PRICING_PER_MILLION_TOKENS = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = PRICING_PER_MILLION_TOKENS.get(model)
    if not rates:
        logger.warning("No pricing entry for model %s -- recording cost as $0", model)
        return 0.0
    return (prompt_tokens / 1_000_000) * rates["input"] + (completion_tokens / 1_000_000) * rates["output"]


def _record_usage(agent: str, model: str, usage) -> None:
    """Persists one LLMUsage row for this call, tagged with whichever scan
    is current in this worker process (current_scan_id -- the same
    ContextVar Part 3's logging uses) and which agent made the call.

    Opens its own short-lived session rather than accepting one as a
    parameter, same reasoning as scan_service.run_scan_job: this runs
    inside a Celery worker process with no request-scoped session to
    reuse. Failures here are logged and swallowed, never raised --losing
    a cost-tracking row must never fail the actual scan.
    """
    scan_id = current_scan_id.get()
    if scan_id == "-":
        logger.warning("No scan_id in context -- skipping LLM usage record for %s call", agent)
        return

    db = SessionLocal()
    try:
        db.add(LLMUsage(
            scan_id=scan_id,
            agent=agent,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=_cost_usd(model, usage.prompt_tokens, usage.completion_tokens),
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record LLM usage for %s call", agent)
    finally:
        db.close()


def call_structured(system_prompt: str, user_prompt: str, response_model, agent: str = "unknown"):
    """Calls the OpenAI chat API and forces the reply into the exact shape of
    `response_model` (a Pydantic class), using OpenAI's Structured Outputs
    feature -- not "ask nicely for JSON and hope it parses."

    This matters specifically because Securify is a pipeline: the analyzer's
    output becomes the remediation agent's input, which becomes the
    validator's input. If any agent returned free text, the next agent
    would have no reliable way to read it. If the model can't produce a
    valid instance of the schema, this raises an exception instead of
    silently handing bad data downstream.

    agent: short label ("analyzer", "remediation") identifying which
    pipeline stage made this call. Recorded alongside token/cost usage
    (Phase 7 Part 4) so a scan's cost breakdown can be shown per agent,
    not just as one opaque total.
    """
    completion = _client.beta.chat.completions.parse(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_model,
    )

    if completion.usage:
        _record_usage(agent, CHAT_MODEL, completion.usage)

    return completion.choices[0].message.parsed
