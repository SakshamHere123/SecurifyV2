from app.services.embeddings import embed_texts
from app.services.vector_store import search


def retrieve_relevant_policy(org_id: str, query_text: str, top_k: int = 5) -> list[dict]:
    """Given text describing a Terraform resource (plus its static findings),
    embeds it and returns the top-k most relevant policy chunks for that org.

    This is the exact function the Analyzer agent will call in Phase 4 --
    for each resource + finding, it retrieves relevant policy context before
    asking the LLM to reason about it.
    """
    [vector] = embed_texts([query_text])
    return search(org_id, vector, top_k=top_k)