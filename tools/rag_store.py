"""Lightweight local RAG index for Part 2 (no paid embedding API required).

Chunks full texts, stores a TF-IDF sparse index on disk, and retrieves
top-k passages for grounded synthesis. Optional OpenAI embeddings are used
only when OPENAI_API_KEY is set and PART2_USE_OPENAI_EMBEDDINGS=1.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "were",
    "dans", "avec", "pour", "les", "des", "une", "un", "sur", "par", "de", "du",
    "la", "le", "et", "en", "to", "of", "a", "an", "is", "in", "on", "as", "by",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(text or "").lower())
    return [t for t in raw if len(t) > 2 and t not in _STOPWORDS]


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    if not counts:
        return {}
    length = sum(counts.values())
    return {term: (count / length) * idf.get(term, 0.0) for term, count in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LocalRagStore:
    """Persistable TF-IDF RAG store over study full texts / abstracts."""

    def __init__(self, persist_dir: str | Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: list[dict[str, Any]] = []
        self.idf: dict[str, float] = {}
        self.vectors: list[dict[str, float]] = []
        self.meta: dict[str, Any] = {
            "method": "local_tfidf_v1",
            "note": "Sparse lexical RAG; no external embedding API required by default.",
        }

    def build(self, records: list[dict], text_field: str = "full_text") -> dict[str, Any]:
        self.chunks = []
        docs_tokens: list[list[str]] = []
        for record in records:
            text = (record.get(text_field) or record.get("abstract") or "").strip()
            if not text:
                continue
            study_id = record.get("openalex_id") or record.get("doi") or record.get("title") or "unknown"
            title = record.get("title") or ""
            for idx, chunk in enumerate(chunk_text(text)):
                tokens = _tokens(chunk)
                self.chunks.append({
                    "chunk_id": f"{study_id}::{idx}",
                    "study_id": study_id,
                    "title": title,
                    "year": record.get("year"),
                    "doi": record.get("doi"),
                    "text": chunk,
                    "token_count": len(tokens),
                })
                docs_tokens.append(tokens)

        df = Counter()
        for tokens in docs_tokens:
            for term in set(tokens):
                df[term] += 1
        n_docs = max(len(docs_tokens), 1)
        self.idf = {term: math.log((1 + n_docs) / (1 + freq)) + 1.0 for term, freq in df.items()}
        self.vectors = [_tfidf_vector(tokens, self.idf) for tokens in docs_tokens]
        self.meta.update({
            "n_chunks": len(self.chunks),
            "n_studies": len({c["study_id"] for c in self.chunks}),
            "vocab_size": len(self.idf),
            "openai_embeddings": False,
        })

        # Optional dense embeddings when explicitly enabled.
        if os.getenv("PART2_USE_OPENAI_EMBEDDINGS", "").strip() == "1" and os.getenv("OPENAI_API_KEY"):
            self._try_openai_embeddings()

        self.save()
        return dict(self.meta)

    def _try_openai_embeddings(self) -> None:
        try:
            from langchain_openai import OpenAIEmbeddings
            emb = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
            texts = [c["text"] for c in self.chunks]
            vectors = emb.embed_documents(texts)
            path = self.persist_dir / "openai_embeddings.json"
            path.write_text(json.dumps(vectors), encoding="utf-8")
            self.meta["openai_embeddings"] = True
            self.meta["method"] = "openai_embeddings_plus_local_tfidf"
        except Exception as exc:
            self.meta["openai_embeddings_error"] = f"{type(exc).__name__}: {exc}"

    def save(self) -> None:
        (self.persist_dir / "chunks.json").write_text(
            json.dumps(self.chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.persist_dir / "idf.json").write_text(
            json.dumps(self.idf, ensure_ascii=False), encoding="utf-8"
        )
        (self.persist_dir / "vectors.json").write_text(
            json.dumps(self.vectors), encoding="utf-8"
        )
        (self.persist_dir / "meta.json").write_text(
            json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self) -> bool:
        chunks_path = self.persist_dir / "chunks.json"
        if not chunks_path.exists():
            return False
        self.chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.idf = json.loads((self.persist_dir / "idf.json").read_text(encoding="utf-8"))
        self.vectors = json.loads((self.persist_dir / "vectors.json").read_text(encoding="utf-8"))
        meta_path = self.persist_dir / "meta.json"
        if meta_path.exists():
            self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return True

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.chunks:
            if not self.load():
                return []
        qvec = _tfidf_vector(_tokens(query), self.idf)
        scored = []
        for chunk, vec in zip(self.chunks, self.vectors):
            score = _cosine(qvec, vec)
            if score <= 0:
                continue
            item = dict(chunk)
            item["score"] = round(float(score), 4)
            scored.append(item)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


def build_rag_index(records: list[dict], persist_dir: str | Path) -> dict[str, Any]:
    store = LocalRagStore(persist_dir)
    return store.build(records)


def retrieve_context(persist_dir: str | Path, query: str, top_k: int = 8) -> list[dict[str, Any]]:
    store = LocalRagStore(persist_dir)
    store.load()
    return store.retrieve(query, top_k=top_k)
