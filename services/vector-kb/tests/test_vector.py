"""Tests for the vector store."""

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.store import VectorStore


def _fresh_store() -> VectorStore:
    """Create a truly isolated ephemeral store by using unique collection names."""
    client = chromadb.Client(
        ChromaSettings(anonymized_telemetry=False, allow_reset=True)
    )
    client.reset()

    store = VectorStore.__new__(VectorStore)
    store._client = client
    store._alerts = client.get_or_create_collection(
        name="alerts", metadata={"hnsw:space": "cosine"}
    )
    store._threat_intel = client.get_or_create_collection(
        name="threat_intel", metadata={"hnsw:space": "cosine"}
    )
    return store


class TestVectorStore:
    def setup_method(self):
        self.store = _fresh_store()

    def test_index_and_search_alerts(self):
        self.store.index_document(
            text="Brute force SSH login attempt from 192.168.1.100",
            metadata={"label": "brute-force", "score": 0.85},
            doc_id="alert-001",
        )
        self.store.index_document(
            text="Normal user login from known IP",
            metadata={"label": "normal", "score": 0.1},
            doc_id="alert-002",
        )

        results = self.store.search_similar(
            "SSH brute force attack", collection="alerts", top_k=2
        )

        assert len(results) == 2
        assert results[0]["id"] == "alert-001"  # closest match
        assert "distance" in results[0]
        assert "metadata" in results[0]

    def test_index_threat_intel(self):
        doc_id = self.store.index_threat_intel(
            indicator="evil.example.com",
            intel_type="domain",
            source="abuse-ch",
            description="Known C2 domain for botnet",
        )
        assert doc_id is not None

        results = self.store.search_similar(
            "command and control domain", collection="threat_intel"
        )
        assert len(results) == 1
        assert results[0]["metadata"]["indicator"] == "evil.example.com"

    def test_stats(self):
        assert self.store.get_stats()["total"] == 0

        self.store.index_document(
            text="Alert 1", metadata={"type": "test"}, doc_id="a1"
        )
        self.store.index_document(
            text="Alert 2", metadata={"type": "test"}, doc_id="a2"
        )
        self.store.index_threat_intel(indicator="1.2.3.4", intel_type="ip")

        stats = self.store.get_stats()
        assert stats["alerts_count"] == 2
        assert stats["threat_intel_count"] == 1
        assert stats["total"] == 3

    def test_search_empty_collection(self):
        results = self.store.search_similar("anything", collection="alerts")
        assert results == []

    def test_upsert_overwrites(self):
        self.store.index_document(text="Version 1", metadata={"v": "1"}, doc_id="doc-x")
        self.store.index_document(
            text="Version 2 updated", metadata={"v": "2"}, doc_id="doc-x"
        )

        stats = self.store.get_stats()
        assert stats["alerts_count"] == 1  # upsert, not duplicate
