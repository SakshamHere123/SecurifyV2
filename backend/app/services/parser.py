from typing import Any

import hcl2


def parse_terraform_file(file_path: str) -> dict[str, Any]:
    """Parses a single .tf file into a structured dict of resources.

    We use python-hcl2 instead of regex/string matching because Terraform's
    HCL syntax has nested blocks, lists, maps, and references -- a regex
    'catches' the common cases and silently mis-parses the rest. hcl2 gives
    us a real parse tree so every resource block is captured correctly.
    """
    with open(file_path, "r") as f:
        raw = hcl2.load(f)

    resources = []
    for resource_block in raw.get("resource", []):
        # Each resource_block looks like:
        # {"aws_s3_bucket": {"my_bucket": {...attributes...}}}
        for resource_type, instances in resource_block.items():
            for resource_name, attrs in instances.items():
                resources.append({
                    "type": resource_type,
                    "name": resource_name,
                    "address": f"{resource_type}.{resource_name}",
                    "attributes": attrs,
                })

    return {
        "resource_count": len(resources),
        "resources": resources,
    }


def extract_raw_resource_blocks(file_path: str) -> dict[str, str]:
    """Extracts each resource's EXACT original text (via brace matching, not
    regex-only) rather than its parsed attributes.

    Why we need this in addition to parse_terraform_file(): hcl2 gives us
    structured attributes, but structured data can't be written back out as
    perfectly-valid HCL for the resources the LLM never touched. Keeping the
    original raw text for untouched resources -- and only swapping in the
    LLM's fixed_hcl for resources that actually had a violation -- means the
    validator's re-scan runs against real, guaranteed-valid HCL everywhere
    except the parts that were deliberately changed.
    """
    import re

    with open(file_path, "r") as f:
        content = f.read()

    blocks: dict[str, str] = {}
    pattern = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*{')

    for match in pattern.finditer(content):
        resource_type, resource_name = match.group(1), match.group(2)
        address = f"{resource_type}.{resource_name}"

        brace_start = content.index("{", match.end() - 1)
        depth = 0
        i = brace_start
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1

        blocks[address] = content[match.start():i + 1]

    return blocks