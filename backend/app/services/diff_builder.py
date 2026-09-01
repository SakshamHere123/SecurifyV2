import difflib

from app.services.parser import extract_raw_resource_blocks


def build_scan_diffs(input_tf_path: str, output_tf_path: str) -> list[dict]:
    """Builds a per-resource diff by comparing the original and remediated
    .tf files on disk.

    Deliberately file-based rather than working off the in-memory
    RemediatedResource list from the pipeline run: this way a diff can be
    regenerated for ANY past scan just from its stored file paths, not only
    the one that's currently executing. Resources whose text is identical
    in both files are skipped entirely -- the diff view should only ever
    show what actually changed, matching the containment guarantee from
    the Remediation agent (Part 3 of Phase 4).
    """
    original_blocks = extract_raw_resource_blocks(input_tf_path)
    remediated_blocks = extract_raw_resource_blocks(output_tf_path)

    diffs = []
    for address, original_text in original_blocks.items():
        remediated_text = remediated_blocks.get(address, original_text)
        if remediated_text == original_text:
            continue
        diffs.append({
            "resource": address,
            "lines": _line_diff(original_text, remediated_text),
        })
    return diffs


def _line_diff(original: str, fixed: str) -> list[dict]:
    """Line-by-line diff via difflib's SequenceMatcher, returned as a list of
    {type, content} entries instead of unified-diff text.

    Why structured instead of text: a frontend diff viewer (Phase 6) and a
    PDF report (Part 3, next) both need to color lines -- green for added,
    red for removed. Handing them {"type": "added", "content": "..."} means
    they just switch on `type`; handing them '+'/'-' prefixed text would
    mean re-parsing a text format just to get back to this same information.
    """
    original_lines = original.splitlines()
    fixed_lines = fixed.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, fixed_lines)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in original_lines[i1:i2]:
                result.append({"type": "unchanged", "content": line})
        elif tag == "delete":
            for line in original_lines[i1:i2]:
                result.append({"type": "removed", "content": line})
        elif tag == "insert":
            for line in fixed_lines[j1:j2]:
                result.append({"type": "added", "content": line})
        elif tag == "replace":
            for line in original_lines[i1:i2]:
                result.append({"type": "removed", "content": line})
            for line in fixed_lines[j1:j2]:
                result.append({"type": "added", "content": line})

    return result