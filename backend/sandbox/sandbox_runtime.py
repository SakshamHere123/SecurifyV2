"""Runs entirely inside the isolated `securify-sandbox` container -- never
in the main backend/worker process. Reads the uploaded .tf file from
/input (mounted read-only), runs the same parsing + Checkov logic Phase 2
established, and writes the combined result to /output/result.json
(the only writable path in this container).

Deliberately duplicates parse_terraform_file() / extract_raw_resource_blocks()
from app/services/parser.py rather than importing that module. The sandbox
image intentionally does NOT install the FastAPI app, SQLAlchemy, or the
OpenAI SDK -- it has no reason to ever be able to see OPENAI_API_KEY or
DATABASE_URL, and a smaller image means a smaller attack surface for
whatever an uploaded .tf file might try to trigger. The tradeoff is real,
though: if parser.py's parsing logic changes, this file needs the same
change made here too -- there's no shared import to keep them in sync
automatically.
"""
import json
import os
import re
import subprocess
import sys

import hcl2

INPUT_DIR = "/input"
OUTPUT_PATH = "/output/result.json"


def parse_terraform_file(file_path: str) -> dict:
    with open(file_path, "r") as f:
        raw = hcl2.load(f)

    resources = []
    for resource_block in raw.get("resource", []):
        for resource_type, instances in resource_block.items():
            for resource_name, attrs in instances.items():
                resources.append({
                    "type": resource_type,
                    "name": resource_name,
                    "address": f"{resource_type}.{resource_name}",
                    "attributes": attrs,
                })

    return {"resource_count": len(resources), "resources": resources}


def extract_raw_resource_blocks(file_path: str) -> dict:
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


def run_checkov(tf_dir: str) -> dict:
    result = subprocess.run(
        ["checkov", "-d", tf_dir, "-o", "json", "--quiet", "--compact"],
        capture_output=True,
        text=True,
    )
    # Checkov exits non-zero when it finds failing checks -- expected, not
    # a crash. Only care whether stdout parses as JSON.
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "checkov produced no valid JSON output", "stderr": result.stderr}


def main() -> None:
    tf_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".tf")]
    if not tf_files:
        with open(OUTPUT_PATH, "w") as f:
            json.dump({"error": "no .tf file found in /input"}, f)
        sys.exit(1)

    # The pipeline hands the sandbox exactly one .tf file per scan today.
    input_path = os.path.join(INPUT_DIR, tf_files[0])

    result = {
        "parsed": parse_terraform_file(input_path),
        "raw_blocks": extract_raw_resource_blocks(input_path),
        "checkov_raw": run_checkov(INPUT_DIR),
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
