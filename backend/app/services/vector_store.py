import json
import os

import faiss
import numpy as np

from app.services.embeddings import EMBEDDING_DIM

STORAGE_DIR = "/app/storage/faiss"


def _index_path(org_id: str) -> str:
    return os.path.join(STORAGE_DIR, f"{org_id}.index")


def _meta_path(org_id: str) -> str:
    return os.path.join(STORAGE_DIR, f"{org_id}_meta.json")


def _load_index(org_id: str):
    os.makedirs(STORAGE_DIR, exist_ok=True)
    path = _index_path(org_id)
    if os.path.exists(path):
        return faiss.read_index(path)
    # IndexFlatIP = exact search via inner product on normalized vectors,
    # which is equivalent to cosine similarity. Fine at project scale
    # (thousands of chunks); a system with millions of chunks would swap
    # this for an approximate-nearest-neighbor index instead.
    return faiss.IndexFlatIP(EMBEDDING_DIM)


def _load_meta(org_id: str) -> list[dict]:
    path = _meta_path(org_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def _save_meta(org_id: str, meta: list[dict]):
    with open(_meta_path(org_id), "w") as f:
        json.dump(meta, f)


def add_chunks(
    org_id: str,
    chunks: list[str],
    vectors: list[list[float]],
    policy_id: str,
    filename: str,
    version: int,
):
    """Adds a policy's chunk vectors to that org's FAISS index.

    This function IS the multi-tenancy boundary in the RAG layer: one index
    file per org_id, on disk, never shared or merged. There is no query
    parameter that could accidentally search across orgs -- the file itself
    only contains that org's data.
    """
    index = _load_index(org_id)
    meta = _load_meta(org_id)

    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)  # normalize so inner product behaves like cosine similarity
    index.add(arr)

    for chunk in chunks:
        meta.append({
            "policy_id": policy_id,
            "filename": filename,
            "version": version,
            "text": chunk,
        })

    faiss.write_index(index, _index_path(org_id))
    _save_meta(org_id, meta)


def search(org_id: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    """Searches the org's index, returning chunks ONLY from each policy's
    latest version. Older versions stay in the index (so a scan from last
    month can still be traced back to the policy text that applied then)
    but never surface for new retrieval -- that's the versioning rule from
    the architecture doc, enforced at query time instead of by deleting data.
    """
    index = _load_index(org_id)
    meta = _load_meta(org_id)

    if index.ntotal == 0:
        return []

    latest_version: dict[str, int] = {}
    for m in meta:
        latest_version[m["filename"]] = max(latest_version.get(m["filename"], 0), m["version"])

    arr = np.array([query_vector], dtype="float32")
    faiss.normalize_L2(arr)

    # Over-fetch so filtering out stale versions doesn't leave us short of top_k
    scores, indices = index.search(arr, top_k * 3)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1 or idx >= len(meta):
            continue
        m = meta[idx]
        if m["version"] != latest_version[m["filename"]]:
            continue
        results.append({**m, "score": float(score)})
        if len(results) >= top_k:
            break

    return results