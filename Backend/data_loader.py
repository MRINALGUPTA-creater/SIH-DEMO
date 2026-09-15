import os
import math
import hashlib
import logging
from typing import List
from pypdf import PdfReader

logger = logging.getLogger("uvicorn")


def load_and_chunk_pdf(pdf_path: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return []

    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            full_text += f"\n[Page {i + 1}]\n" + text

        if not full_text.strip():
            return []

        # Chunk text
        chunks = []
        start = 0
        while start < len(full_text):
            end = start + chunk_size
            chunk = full_text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - chunk_overlap

        return chunks
    except Exception as e:
        logger.error(f"Failed to read/chunk PDF {pdf_path}: {e}")
        return []


def _fallback_embedding(text: str, dim: int = 1536) -> List[float]:
    """Deterministic normalized pseudo-embedding for testing or offline environments."""
    vec = [0.0] * dim
    for i, word in enumerate(text.lower().split()):
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0 / (1.0 + (i * 0.01))

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    else:
        vec[0] = 1.0
    return vec


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and not api_key.startswith("sk-mock") and len(api_key) > 20:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            # Batch in chunks of 50
            results = []
            for i in range(0, len(texts), 50):
                batch = texts[i:i+50]
                res = client.embeddings.create(input=batch, model="text-embedding-3-small")
                results.extend([item.embedding for item in res.data])
            return results
        except Exception as e:
            logger.warning(f"OpenAI embedding call failed ({e}). Falling back to local embedding.")

    # Fallback when no active API key
    return [_fallback_embedding(t) for t in texts]
