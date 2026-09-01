from openai import OpenAI

from app.core.config import settings

_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# gpt-4o-mini: cheap enough to call per-resource, strong enough at structured
# reasoning over code + policy text. Swap to "gpt-4o" here later if accuracy
# on tricky cases needs it -- every agent goes through this one function,
# so upgrading the model later is a one-line change, not a rewrite.
CHAT_MODEL = "gpt-4o-mini"


def call_structured(system_prompt: str, user_prompt: str, response_model):
    """Calls the OpenAI chat API and forces the reply into the exact shape of
    `response_model` (a Pydantic class), using OpenAI's Structured Outputs
    feature -- not "ask nicely for JSON and hope it parses."

    This matters specifically because Securify is a pipeline: the analyzer's
    output becomes the remediation agent's input, which becomes the
    validator's input. If any agent returned free text, the next agent
    would have no reliable way to read it. If the model can't produce a
    valid instance of the schema, this raises an exception instead of
    silently handing bad data downstream.
    """
    completion = _client.beta.chat.completions.parse(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_model,
    )
    return completion.choices[0].message.parsed