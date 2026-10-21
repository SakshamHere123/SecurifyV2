"""
Corpus generator for the Securify evaluation.

Produces:
  corpus/file_0001.tf, file_0002.tf, ... file_NNNN.tf
  corpus/ground_truth.json   -- exact label for every resource in every file

Each file gets 1-3 resources, each resource independently rolled as
"vulnerable" (with one randomly chosen injected issue) or "clean" -- clean
resources are the true-negative pool: a good baseline should NOT flag them.

Usage:
    python generate_corpus.py --count 400 --seed 42
"""

import argparse
import json
import os
import random

from vulnerability_library import INJECTOR_FAMILIES

FAMILY_NAMES = list(INJECTOR_FAMILIES.keys())
VULNERABLE_RATE = 0.55  # ~55% of resources get an injected issue, ~45% are clean


def _unique_name(base: str, used: set) -> str:
    name = base
    i = 2
    while name in used:
        name = f"{base}_{i}"
        i += 1
    used.add(name)
    return name


def generate_file(file_index: int, used_names: set) -> dict:
    """Builds one .tf file's worth of resources and returns its ground truth."""
    num_resources = random.choice([1, 2, 2, 3])  # weighted toward 2
    blocks = []
    resources_gt = []

    for _ in range(num_resources):
        family_name = random.choice(FAMILY_NAMES)
        family = INJECTOR_FAMILIES[family_name]
        name = _unique_name(f"{family_name}_{file_index}", used_names)

        if random.random() < VULNERABLE_RATE:
            injector = random.choice(family["vulnerable"])
            hcl, issue = injector(name)
        else:
            hcl, issue = family["clean"](name)

        blocks.append(hcl)

        # Extract the resource address (type.name) straight from the HCL's
        # own first line, so the ground truth's address can never drift
        # out of sync with what's actually in the file.
        first_line = hcl.strip().splitlines()[0]
        resource_type = first_line.split('"')[1]
        resource_name = first_line.split('"')[3]
        address = f"{resource_type}.{resource_name}"

        resources_gt.append({"address": address, "issue": issue})

    file_text = "\n\n".join(blocks) + "\n"
    return {"file_text": file_text, "resources": resources_gt}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=400, help="number of .tf files to generate")
    parser.add_argument("--seed", type=int, default=42, help="random seed, for a reproducible corpus")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "corpus"))
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    manifest = {}
    used_names = set()
    total_planted = 0
    total_checkov_detectable = 0
    total_policy_relevant = 0
    total_clean_resources = 0

    for i in range(1, args.count + 1):
        result = generate_file(i, used_names)
        filename = f"file_{i:04d}.tf"

        with open(os.path.join(args.output_dir, filename), "w") as f:
            f.write(result["file_text"])

        manifest[filename] = result["resources"]

        for r in result["resources"]:
            if r["issue"] is None:
                total_clean_resources += 1
            else:
                total_planted += 1
                if r["issue"]["checkov_detectable"]:
                    total_checkov_detectable += 1
                if r["issue"]["policy_relevant"]:
                    total_policy_relevant += 1

    with open(os.path.join(args.output_dir, "ground_truth.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {args.count} files in {args.output_dir}")
    print(f"  Total resources:            {total_planted + total_clean_resources}")
    print(f"  Planted violations:         {total_planted}")
    print(f"    - Checkov-detectable:     {total_checkov_detectable}")
    print(f"    - Custom-policy-relevant: {total_policy_relevant}")
    print(f"  Clean resources (TN pool):  {total_clean_resources}")


if __name__ == "__main__":
    main()
