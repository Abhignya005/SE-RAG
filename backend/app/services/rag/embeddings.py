import hashlib
import math
import os
import re

from google import genai


def _fallback_embedding(text: str, dimensions: int = 128) -> list[float]:
    """Small deterministic embedding for local/mock deployments."""
    vector = [0.0] * dimensions
    tokens = re.findall(r"[A-Za-z0-9_]+", text)
    tokens.extend(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", text))
    for token in (item.lower() for item in tokens):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


def embed_text(text: str) -> list[float]:
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        return _fallback_embedding(text)
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=os.getenv("AI_EMBEDDING_MODEL", "text-embedding-004"),
            contents=text,
        )
        return list(response.embeddings[0].values)
    except Exception:
        return _fallback_embedding(text)
