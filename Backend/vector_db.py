import os
import logging
from typing import Any, Dict, List
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger("uvicorn")


class QdrantStorage:
    def __init__(self, collection_name: str = "bis_documents"):
        self.collection_name = collection_name
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            # Persistent on-disk vector store in local directory
            storage_path = os.getenv("QDRANT_STORAGE_PATH", os.path.join(os.path.dirname(__file__), "qdrant_storage"))
            os.makedirs(storage_path, exist_ok=True)
            self.client = QdrantClient(path=storage_path)

        self._ensure_collection()

    def _ensure_collection(self, vector_size: int = 1536):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection '{self.collection_name}' (dim={vector_size})")

    def upsert(self, ids: List[str], vecs: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        points = [
            models.PointStruct(
                id=ids[i],
                vector=vecs[i],
                payload=payloads[i],
            )
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vec: List[float], k: int = 5) -> Dict[str, List[str]]:
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vec,
                limit=k,
            ).points
        except Exception as e:
            logger.warning(f"Error querying Qdrant: {e}")
            return {"contexts": [], "sources": []}

        contexts = []
        sources = []
        for r in results:
            text = r.payload.get("text", "")
            source = r.payload.get("source", "BIS Document")
            if text:
                contexts.append(text)
            if source and source not in sources:
                sources.append(source)

        return {"contexts": contexts, "sources": sources}
