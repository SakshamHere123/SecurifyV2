import os
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Policy
from app.core.deps import get_current_user, require_admin, CurrentUser
from app.services.policy_ingest import extract_text, chunk_text
from app.services.embeddings import embed_texts
from app.services.vector_store import add_chunks
from app.services.retrieval import retrieve_relevant_policy

router = APIRouter()

STORAGE_DIR = "/app/storage/policies"
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}


@router.post("/policy/upload")
async def upload_policy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Admin uploads a company security policy document. It gets saved,
    versioned, chunked, embedded, and added to the org's FAISS index.
    """
    org_id = current_user.org_id

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, Markdown, or .txt files are accepted")

    existing = (
        db.query(Policy)
        .filter(Policy.org_id == org_id, Policy.filename == file.filename)
        .order_by(Policy.version.desc())
        .first()
    )
    version = (existing.version + 1) if existing else 1

    org_dir = os.path.join(STORAGE_DIR, org_id)
    os.makedirs(org_dir, exist_ok=True)
    storage_path = os.path.join(org_dir, f"v{version}_{file.filename}")

    with open(storage_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    policy = Policy(org_id=org_id, filename=file.filename, version=version, storage_path=storage_path)
    db.add(policy)
    db.commit()
    db.refresh(policy)

    text = extract_text(storage_path)
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No extractable text found in this document")

    vectors = embed_texts(chunks)
    add_chunks(org_id, chunks, vectors, policy_id=policy.id, filename=file.filename, version=version)

    return {
        "policy_id": policy.id,
        "filename": file.filename,
        "version": version,
        "chunks_indexed": len(chunks),
    }


@router.get("/policy/search")
async def search_policy(query: str, top_k: int = 5, current_user: CurrentUser = Depends(get_current_user)):
    """Any authenticated user can query their OWN org's policy index."""
    results = retrieve_relevant_policy(current_user.org_id, query, top_k=top_k)
    return {"query": query, "results": results}


@router.get("/policies")
def list_policies(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """Lists every policy version uploaded for the caller's org, newest
    version first per filename. Read-only, so any authenticated org member
    can see what policies exist -- only uploading (POST /policy/upload)
    is admin-gated, since viewing isn't a sensitive action but changing
    what the AI is grounded in should be.
    """
    policies = (
        db.query(Policy)
        .filter(Policy.org_id == current_user.org_id)
        .order_by(Policy.filename, Policy.version.desc())
        .all()
    )
    return [
        {
            "policy_id": p.id,
            "filename": p.filename,
            "version": p.version,
            "created_at": p.created_at,
        }
        for p in policies
    ]
