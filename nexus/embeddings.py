from __future__ import annotations

import os
from pathlib import Path
from threading import Lock


DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


class EmbeddingError(RuntimeError):
    pass


class LocalEmbeddingProvider:
    """Lazy, CPU-local multilingual embeddings backed by FastEmbed/ONNX."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        *,
        cache_dir: str | None = None,
        threads: int | None = None,
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads
        self._model = None
        self._lock = Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=self.cache_dir,
                        threads=self.threads,
                        lazy_load=True,
                    )
        return self._model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return [
                vector.astype("float32", copy=False).tolist()
                for vector in self._get_model().passage_embed(texts)
            ]
        except Exception as error:
            raise EmbeddingError("Local embedding generation failed.") from error

    def embed_query(self, text: str) -> list[float]:
        try:
            vector = next(iter(self._get_model().query_embed(text)))
            return vector.astype("float32", copy=False).tolist()
        except Exception as error:
            raise EmbeddingError("Local query embedding failed.") from error


def embedding_provider_from_env():
    if os.getenv("NEXUS_RAG_EMBEDDINGS_ENABLED", "0") != "1":
        return None
    cache = os.getenv("NEXUS_RAG_EMBEDDING_CACHE", "").strip() or None
    if cache:
        Path(cache).mkdir(parents=True, exist_ok=True)
    threads_value = os.getenv("NEXUS_RAG_EMBEDDING_THREADS", "").strip()
    threads = int(threads_value) if threads_value else None
    if threads is not None and not 1 <= threads <= 64:
        raise ValueError("NEXUS_RAG_EMBEDDING_THREADS must be between 1 and 64.")
    return LocalEmbeddingProvider(
        os.getenv("NEXUS_RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        cache_dir=cache,
        threads=threads,
    )
