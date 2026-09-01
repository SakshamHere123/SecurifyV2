from app.schemas.agent_schemas import RemediatedResource


def build_remediated_file(raw_blocks: dict[str, str], fixes: list[RemediatedResource]) -> str:
    """Builds the full remediated .tf file text: resources with a fix get the
    LLM's fixed_hcl block; every other resource keeps its exact original text.

    This is what makes the validator's re-scan trustworthy -- it's checking
    real, complete Terraform, not a fragment, and the only text that changed
    from the original file is text tied to an actual violation.
    """
    fixed_by_address = {f.resource: f.fixed_hcl for f in fixes}

    parts = []
    for address, original_text in raw_blocks.items():
        parts.append(fixed_by_address.get(address, original_text))

    return "\n\n".join(parts)