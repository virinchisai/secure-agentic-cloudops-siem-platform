"""Vector Knowledge Base — semantic search over alerts and threat intelligence."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.store import VectorStore

# ---------------------------------------------------------------------------
# Lifespan: initialise the vector store once
# ---------------------------------------------------------------------------

_store: VectorStore | None = None


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        persist = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")
        ephemeral = os.getenv("CHROMA_EPHEMERAL", "").lower() in ("1", "true", "yes")
        _store = VectorStore(persist_dir=persist, ephemeral=ephemeral)
    return _store


@asynccontextmanager
async def lifespan(application: FastAPI):
    _get_store()  # eagerly create on startup
    yield


app = FastAPI(title="vector-kb", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class IndexRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Document text to index")
    metadata: dict[str, Any] = Field(default_factory=dict)
    doc_id: str | None = None
    collection: str = Field(
        default="alerts", description="Target collection: alerts | threat_intel"
    )


class IndexResponse(BaseModel):
    doc_id: str
    collection: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collection: str = Field(default="alerts")
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResponse(BaseModel):
    query: str
    collection: str
    results: list[dict[str, Any]]


class ThreatIntelRequest(BaseModel):
    indicator: str = Field(
        ..., min_length=1, description="IOC value (IP, domain, hash, …)"
    )
    intel_type: str = Field(..., description="Type: ip, domain, hash, url, email")
    source: str = Field(default="unknown")
    description: str = Field(default="")
    doc_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    store = _get_store()
    stats = store.get_stats()
    return {"status": "ok", "service": "vector-kb", "indexed": stats["total"]}


@app.get("/stats")
def stats():
    store = _get_store()
    return store.get_stats()


@app.post("/index", response_model=IndexResponse)
def index_document(req: IndexRequest):
    """Index a document/alert into the vector store."""
    store = _get_store()
    valid_collections = ("alerts", "threat_intel")
    if req.collection not in valid_collections:
        raise HTTPException(
            status_code=400, detail=f"collection must be one of {valid_collections}"
        )

    doc_id = store.index_document(
        text=req.text,
        metadata=req.metadata,
        doc_id=req.doc_id,
        collection=req.collection,
    )
    return IndexResponse(doc_id=doc_id, collection=req.collection)


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """Semantic search for similar alerts or threat intel."""
    store = _get_store()
    results = store.search_similar(
        query=req.query,
        collection=req.collection,
        top_k=req.top_k,
    )
    return SearchResponse(query=req.query, collection=req.collection, results=results)


@app.post("/index-threat-intel", response_model=IndexResponse)
def index_threat_intel(req: ThreatIntelRequest):
    """Index a threat intelligence indicator."""
    store = _get_store()
    doc_id = store.index_threat_intel(
        indicator=req.indicator,
        intel_type=req.intel_type,
        source=req.source,
        description=req.description,
        doc_id=req.doc_id,
    )
    return IndexResponse(doc_id=doc_id, collection="threat_intel")
