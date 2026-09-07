import logging

from app.schemas.agent_schemas import AnalyzerOutput
from app.services.llm_client import call_structured
from app.services.retrieval import retrieve_relevant_policy

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM_PROMPT = """You are a cloud security analyst reviewing Terraform \
infrastructure code for a specific company. You are given, for each resource:
1. The parsed Terraform resource and its attributes
2. Findings from a deterministic static analysis tool (Checkov) that already ran
3. Relevant excerpts from the company's own security policy documents, retrieved \
specifically for that resource

Your job:
- Identify every real security violation, combining what the static tool already \
found with anything you can add by reasoning against the company's specific policy text.
- For each violation, set policy_reference to the EXACT retrieved policy excerpt it \
violates -- never invent policy text that was not given to you. If no retrieved \
excerpt applies, leave policy_reference empty.
- If a violation was already confirmed by the static tool, copy its identifier into \
static_tool_confirmed exactly as given (e.g. "checkov:CKV_AWS_18").
- Do not report a violation for a resource that has no real issue -- only report \
genuine problems, not speculative ones.
- Assign severity honestly: critical/high for things like public exposure or missing \
encryption on sensitive data; medium/low for weaker best-practice gaps.
"""


def _build_resource_context(resource: dict, static_findings: list[dict], org_id: str) -> str:
    """Builds the LLM's context block for ONE resource: its own static findings,
    plus policy chunks retrieved specifically for it.

    Querying per-resource (instead of once for the whole file) matters: it
    means a company's S3-encryption policy gets retrieved for the S3 bucket,
    not for an unrelated security group sitting three resources below it.
    """
    resource_findings = [f for f in static_findings if f.get("resource") == resource["address"]]

    query = f"{resource['type']} {resource['name']} " + " ".join(
        f.get("issue", "") for f in resource_findings
    )
    policy_chunks = retrieve_relevant_policy(org_id, query, top_k=3)

    lines = [
        f"Resource: {resource['address']}",
        f"HCL attributes: {resource['attributes']}",
        "Static tool findings for this resource:",
    ]
    if resource_findings:
        for f in resource_findings:
            lines.append(f"  - [{f.get('severity')}] {f.get('issue')} ({f.get('static_tool_confirmed')})")
    else:
        lines.append("  - none")

    lines.append("Relevant company policy excerpts:")
    if policy_chunks:
        for chunk in policy_chunks:
            lines.append(f"  - (from {chunk['filename']} v{chunk['version']}): {chunk['text']}")
    else:
        lines.append("  - none retrieved")

    return "\n".join(lines)


def analyze_resources(org_id: str, resources: list[dict], static_findings: list[dict]) -> AnalyzerOutput:
    """The Analyzer agent. One structured-output LLM call covering every resource
    in the file, each with its own static findings + retrieved policy context
    attached. Returns a validated AnalyzerOutput -- a real violation list, not
    prose to be scraped later.
    """
    resource_blocks = [_build_resource_context(r, static_findings, org_id) for r in resources]
    user_prompt = "\n\n---\n\n".join(resource_blocks)

    logger.info("Calling Analyzer LLM for %d resource(s)", len(resources))
    return call_structured(
        system_prompt=ANALYZER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=AnalyzerOutput,
        agent="analyzer",
    )