"""
Embeddings wrapper for MentorOS.
Uses SentenceTransformers (default: all-MiniLM-L6-v2, 384 dimensions)
with automatic GPU (CUDA/RTX 4050) or CPU device selection.
"""

from typing import List, Union
import torch

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class EmbeddingModel:
    """Wrapper around SentenceTransformer for generating dense text embeddings."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = None):
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is required. Run `pip install sentence-transformers`."
            )

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=self.device)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        text = text.strip()
        if not text:
            text = " "
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate normalized embedding vectors for a batch of document texts."""
        cleaned_texts = [t.strip() if t.strip() else " " for t in texts]
        embeddings = self.model.encode(
            cleaned_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 50,
        )
        return embeddings.tolist()
