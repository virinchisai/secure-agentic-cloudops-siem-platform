"""Vector store wrapper around ChromaDB."""

from __future__ import annotations

import os
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings


CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")

# Collection names
ALERTS_COLLECTION = "alerts"
THREAT_INTEL_COLLECTION = "threat_intel"


class VectorStore:
    """Thin wrapper over ChromaDB with two collections: alerts and threat_intel."""

    def __init__(self, persist_dir: str | None = None, ephemeral: bool = False):
        if ephemeral:
            self._client = chromadb.Client()
        else:
            directory = persist_dir or CHROMA_PERSIST_DIR
            self._client = chromadb.PersistentClient(
                path=directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        self._alerts = self._client.get_or_create_collection(
            name=ALERTS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._threat_intel = self._client.get_or_create_collection(
            name=THREAT_INTEL_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str | None = None,
        collection: str = ALERTS_COLLECTION,
    ) -> str:
        """Index a document into the specified collection. Returns the doc ID."""
        col = self._get_collection(collection)
        doc_id = doc_id or str(uuid.uuid4())
        upsert_kwargs: dict[str, Any] = {"ids": [doc_id], "documents": [text]}
        if metadata:
            upsert_kwargs["metadatas"] = [metadata]
        col.upsert(**upsert_kwargs)
        return doc_id

    def search_similar(
        self,
        query: str,
        collection: str = ALERTS_COLLECTION,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the top-k most similar documents."""
        col = self._get_collection(collection)
        if col.count() == 0:
            return []

        results = col.query(
            query_texts=[query],
            n_results=min(top_k, col.count()),
        )

        out: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for i, doc_id in enumerate(ids):
            out.append({
                "id": doc_id,
                "document": documents[i] if i < len(documents) else "",
                "distance": distances[i] if i < len(distances) else None,
                "metadata": metadatas[i] if i < len(metadatas) else {},
            })

        return out

    def index_threat_intel(
        self,
        indicator: str,
        intel_type: str,
        source: str = "unknown",
        description: str = "",
        doc_id: str | None = None,
    ) -> str:
        """Index a threat intelligence indicator."""
        text = f"{intel_type}: {indicator}. {description}"
        metadata = {
            "indicator": indicator,
            "type": intel_type,
            "source": source,
        }
        return self.index_document(
            text=text,
            metadata=metadata,
            doc_id=doc_id,
            collection=THREAT_INTEL_COLLECTION,
        )

    def get_stats(self) -> dict[str, Any]:
        """Return counts for each collection."""
        return {
            "alerts_count": self._alerts.count(),
            "threat_intel_count": self._threat_intel.count(),
            "total": self._alerts.count() + self._threat_intel.count(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_collection(self, name: str):
        if name == THREAT_INTEL_COLLECTION:
            return self._threat_intel
        return self._alerts
