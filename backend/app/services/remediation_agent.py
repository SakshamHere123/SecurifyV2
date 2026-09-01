from app.schemas.agent_schemas import RemediationOutput, Violation
from app.services.llm_client import call_structured

REMEDIATION_SYSTEM_PROMPT = """You are a Terraform security engineer. You are given, \
for each resource that has confirmed violations:
1. The resource's current HCL attributes
2. The specific violations found against it, each with the company policy \
requirement it breaks (when one was found)

Your job:
- Produce a corrected HCL resource block for EVERY resource you are given -- \
each one must fully resolve all listed violations for that resource.
- Only modify what is necessary to fix the listed violations. Do not rewrite \
unrelated attributes, rename the resource, or change its type.
- The output must be syntactically valid HCL that could directly replace the \
original resource block in the .tf file. Format nested blocks properly: each \
block (e.g. `rule { ... }`, `apply_server_side_encryption_by_default { ... }`) \
must open on its own line and its contents indented on separate lines -- never \
write nested blocks collapsed onto a single line, as that fails to parse correctly. Format it like standard `terraform fmt` \
output: every nested block (e.g. `rule { ... }`, `ingress { ... }`) must start \
on its own line, never inline on the same line as its parent block's opening brace.
- In `explanation`, briefly state what changed and which violation(s) it fixes -- \
this text is shown to the end user in the final report, so write it for a human, \
not for a machine.
- If a violation's policy requirement conflicts with what would normally be a \
sane default, follow the company policy -- it takes precedence.
"""


def _resources_by_address(resources: list[dict]) -> dict[str, dict]:
    return {r["address"]: r for r in resources}


def _build_remediation_context(resource: dict, resource_violations: list[Violation]) -> str:
    lines = [
        f"Resource: {resource['address']}",
        f"Resource type: {resource['type']}",
        f"Current HCL attributes: {resource['attributes']}",
        "Violations to fix:",
    ]
    for v in resource_violations:
        lines.append(f"  - [{v.severity.value}] {v.issue}")
        if v.policy_reference:
            lines.append(f"    Policy requirement: {v.policy_reference}")
    return "\n".join(lines)


def remediate_violations(resources: list[dict], violations: list[Violation]) -> RemediationOutput:
    """The Remediation agent. Groups violations by resource (so a resource with
    no violations never appears here and never gets touched), then asks the
    LLM for a corrected HCL block per affected resource.
    """
    resources_by_addr = _resources_by_address(resources)

    violations_by_resource: dict[str, list[Violation]] = {}
    for v in violations:
        violations_by_resource.setdefault(v.resource, []).append(v)

    if not violations_by_resource:
        # Nothing to fix -- don't waste an LLM call on an empty violation list
        return RemediationOutput(fixes=[])

    blocks = []
    for address, resource_violations in violations_by_resource.items():
        resource = resources_by_addr.get(address)
        if resource is None:
            # The analyzer referenced a resource address we have no parsed
            # data for (shouldn't normally happen) -- skip it rather than
            # send the LLM a block it can't act on.
            continue
        blocks.append(_build_remediation_context(resource, resource_violations))

    user_prompt = "\n\n---\n\n".join(blocks)

    return call_structured(
        system_prompt=REMEDIATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=RemediationOutput,
    )