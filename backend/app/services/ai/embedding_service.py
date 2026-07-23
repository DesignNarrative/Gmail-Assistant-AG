from typing import List
import logging
import os

logger = logging.getLogger(__name__)

# Cache directory inside container (persists across restarts via volume)
CACHE_DIR = "/app/.fastembed_cache"
MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384-dim, ~130MB, fast & accurate

_model = None

def get_embedding_model():
    """Lazy-load the fastembed model (downloads once, cached on disk)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        os.makedirs(CACHE_DIR, exist_ok=True)
        logger.info(f"Loading embedding model {MODEL_NAME} (downloads once ~130MB if not cached)...")
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
        logger.info("Embedding model loaded successfully.")
    return _model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate 384-dimensional embeddings for a list of text strings.
    Returns list of float vectors.
    """
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]

def generate_single_embedding(text: str) -> List[float]:
    """Generate embedding for a single text string."""
    result = generate_embeddings([text])
    return result[0] if result else []
